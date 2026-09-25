"""Build independently bootable experimental FAP3/ZX0 volumes.

Uses the existing packets, Huffman tables, exact compact checkpoints and
AY register history. Optional cold bitmaps replace the two native checkpoints
with zero bitmaps and force complete output of the first two frames.
The separate warm_continuation experiment requires the preceding volume's
RAM and is not the default independently bootable format.
No cadence/release claim is made by this builder; validate real disk I/O
and all displayed frames separately in Fuse.
"""
import argparse
from bisect import bisect_right
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

import numpy as np

from build_zxv_trd import TrdFile, build_boot_basic, basic_line
from build_streaming_trd import place_files, calculate_file_start
from bulk_frame_stream import read_packet
from frame_output_pipeline import display_screen
from frame_stream_harness import Harness
from pipelined_frame_harness import Clock
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
import disk_progress_z80 as progress
import fap3_disk_z80 as disk
import zx0_codec
import disk_layout


def sha(data): return hashlib.sha256(data).hexdigest()
def sectors(data): return (len(data)+255)//256
def padded(data): return data+bytes((-len(data))%256)


def volume_id(raw, ends, part):
    # Retain existing fingerprints; longer generic sources need 32-bit ends.
    wide=any(end>65535 for end in ends)
    series=raw+(b'ENDS32' if wide else b'')+struct.pack('<'+('I' if wide else 'H')*len(ends),*ends)
    return b'FAP3ZXV1'+bytes.fromhex(sha(series))[:6]+struct.pack('<H',part)


def player_harness(ring, tables, mapping, frames, *, disk_reader=True,inline_matches=False,fast_noop_scan=False,irq_safe_paging=False,static_cache_borders=False,carry_huffman=False,register_fragments=False,cached_huffman_byte=False):
    """Shared current player options for disk assembly and instruction profiling."""
    return Harness(ring,tables,mapping,frames,ring_start=0,
        bulk=True,zero_copy=True,stored_guards=False,skip_noop_runs=True,
        constant_attribute_borders=True,skip_black_borders=True,skip_static_stripes=True,
        token_boundaries=True,pipelined=True,progress_frames=frames,packet_ahead='idle',
        unrolled_copy=True,unrolled_cache=True,attribute_groups=True,attribute_flags=True,
        gray_cells=True,sparse_patches=True,disk_refill_entry=disk.DISK if disk_reader else None,inline_matches=inline_matches,
        fast_noop_scan=fast_noop_scan,irq_safe_paging=irq_safe_paging,static_cache_borders=static_cache_borders,carry_huffman=carry_huffman,register_fragments=register_fragments,cached_huffman_byte=cached_huffman_byte)


class Builder:
    def __init__(self, raw, states, zx0, cache, *, fast_disk=False, cached_seek=False, cold_track=False, interleaved=False,deferred_limit=0,keepalive_fields=0,frame_service=False,cold_bitmaps=False,inline_matches=False,warm_continuation=False,startup_delta=False,fast_noop_scan=False,irq_safe_paging=False,static_cache_borders=False,carry_huffman=False,register_fragments=False,cached_huffman_byte=False):
        if not 0 <= deferred_limit <= 248: raise ValueError('deferred limit must be 0..248')
        if frame_service and not keepalive_fields: raise ValueError('frame service requires keepalive clock')
        self.raw, self.states, self.zx0, self.cache = raw, states, zx0, cache
        self.cache.mkdir(parents=True,exist_ok=True)
        self.memo = {}
        self.ends=None
        self.fast_disk=fast_disk
        self.cached_seek=cached_seek
        self.cold_track=cold_track
        self.interleaved=interleaved
        self.deferred_limit=deferred_limit
        self.keepalive_fields=keepalive_fields
        self.frame_service=frame_service
        self.cold_bitmaps=cold_bitmaps
        self.inline_matches=inline_matches
        self.fast_noop_scan=fast_noop_scan
        self.static_cache_borders=static_cache_borders
        self.carry_huffman=carry_huffman
        self.register_fragments=register_fragments
        self.cached_huffman_byte=cached_huffman_byte
        if cached_huffman_byte and not carry_huffman: raise ValueError('cached byte requires carry Huffman')
        self.irq_safe_paging=irq_safe_paging
        self.warm_continuation=warm_continuation
        self.warm_immutable=None
        self.startup_delta=startup_delta
        r=Reader(raw)
        _,_,count,self.mapping,self.tables=read_header(r,magic=b'FAP3')
        if len(states)!=count: raise ValueError('state/frame count differs')
        self.offsets=[r.pos]; self.ay=[bytes(11)]; self.native_map_offsets=[]
        state=bytearray(11)
        for _ in range(count):
            _,detail=read_packet(r,stored_guards=False)
            self.native_map_offsets.append(self.offsets[-1]+2+detail['coded_offset']-80)
            for tick in detail['ticks']:
                for i in range(tick[0]): state[tick[1+2*i]]=tick[2+2*i]
            self.ay.append(bytes(state)); self.offsets.append(r.pos)
        r.end()

    def compress(self, data):
        digest=sha(data)
        if digest in self.memo: return self.memo[digest]
        file=self.cache/(digest+'.zx0')
        if file.exists(): encoded=file.read_bytes()
        else:
            with tempfile.TemporaryDirectory(dir=self.cache) as tmp:
                source=Path(tmp)/'input.raw'; output=Path(tmp)/'output.zx0'
                source.write_bytes(data)
                subprocess.run([str(self.zx0),'-f',str(source.resolve()),str(output.resolve())],
                    check=True,capture_output=True)
                encoded=output.read_bytes()
            file.write_bytes(encoded)
        if zx0_codec.decompress(encoded,limit=len(data))!=data: raise AssertionError('ZX0 roundtrip')
        self.memo[digest]=encoded
        return encoded

    def checkpoint_screen(self, frame):
        screen=display_screen(self.states[frame].tobytes(),black_borders=True)
        # Attribute-group flags still refer to n-2. Keep those attributes and
        # the compact n-1 predictor; only the native bitmaps may be discarded.
        return bytes(6144)+screen[6144:] if self.cold_bitmaps else screen

    def stream_block(self, lo, stop, start, end):
        raw=bytearray(self.raw[lo:stop])
        if self.cold_bitmaps and start:
            for offset in self.native_map_offsets[start:min(start+2,end)]:
                first,last=max(lo,offset),min(stop,offset+80)
                if first<last: raw[first-lo:last-lo]=b'\xff'*(last-first)
        return bytes(raw)

    def stream(self, start, end):
        lo,hi=self.offsets[start],self.offsets[end]
        result=bytearray(); blocks=[]
        while lo<hi:
            stop=min(hi,(lo//8192+1)*8192)
            raw=self.stream_block(lo,stop,start,end); payload=self.compress(raw)
            result+=struct.pack('<HH',len(raw),len(payload))+payload
            blocks.append(dict(raw_start=lo,raw_end=stop,decoded_bytes=len(raw),zx0_bytes=len(payload),sha256=sha(raw)))
            lo=stop
        return bytes(result),blocks

    def ram(self, start, end, next_sector, remaining):
        h=player_harness(bytes(4),self.tables,self.mapping,end-start,inline_matches=self.inline_matches,
            fast_noop_scan=self.fast_noop_scan,irq_safe_paging=self.irq_safe_paging,static_cache_borders=self.static_cache_borders,carry_huffman=self.carry_huffman,register_fragments=self.register_fragments,cached_huffman_byte=self.cached_huffman_byte)
        clock=Clock(h,[],lookahead=True,disk_idle_entry=disk.DEFERRED if self.deferred_limit else None,
            disk_due_entry=disk.DEFERRED_DUE if self.frame_service else None)
        if clock.labels['end']>disk.DRIVER: raise ValueError('clock/driver overlap')
        cpu=h.cpu
        if start: cpu.banks[5][0x2400:0x3300]=self.states[start-1].tobytes()
        for bank,frame in ((5,start-1),(7,start-2)):
            if frame>=0:
                screen=self.checkpoint_screen(frame)
                cpu.banks[bank][:6912]=progress.reference_screen(screen,0,end-start)
        # The last bootstrap operation fills the ring using ordinary C=5.
        # Its last track remains selected when runtime playback starts.
        initial_track=(next_sector-1)//16 if self.cached_seek and not self.cold_track else 255
        code, dl, listing=disk.build_disk(next_sector,remaining,fast_disk=self.fast_disk,
            cached_seek=self.cached_seek,initial_track=initial_track,interleaved=self.interleaved,deferred_limit=self.deferred_limit,
            keepalive_fields=self.keepalive_fields,elapsed_fields=h.audio['elapsed_fields'])
        for i,value in enumerate(code+bytes(256-len(code))): cpu.write8(0xa100+i,value)
        deferred_labels={}
        if self.deferred_limit:
            code,deferred_labels,deferred_rows=disk.build_deferred(dl,self.deferred_limit,
                keepalive_fields=self.keepalive_fields,elapsed_fields=h.audio['elapsed_fields'],frame_service=self.frame_service)
            for i,value in enumerate(code+bytes(256-len(code))): cpu.write8(0xa200+i,value)
            listing+=deferred_rows
        code,next_loader=disk.build_next_loader(entry=0x6003 if self.warm_continuation else 0x6000)
        for i,value in enumerate(code): cpu.write8(disk.LOAD_NEXT+i,value)
        seek_labels={}
        if self.cached_seek:
            if next_loader['end']>disk.CACHED_SEEK: raise ValueError('next loader overlaps cached seek')
            code,seek_labels,seek_listing=disk.build_cached_seek(dl)
            for i,value in enumerate(code): cpu.write8(disk.CACHED_SEEK+i,value)
            listing+=seek_listing
        code,driver=disk.build_driver(h,clock.labels,self.ay[start],has_next=end<len(self.states),deferred=bool(self.deferred_limit))
        for i,value in enumerate(code): cpu.write8(disk.DRIVER+i,value)
        for address,expected in h.frame.protected_regions:
            bank=5 if address<0x8000 else 2 if address<0xc000 else 6
            actual=bytes(cpu.banks[bank][address&16383:(address&16383)+len(expected)])
            if actual!=expected: raise ValueError(f'disk code overlaps immutable table at {address:04x}')
        # The upper fixed section loads first, using the visible screen as
        # compressed staging. Later sections reuse only the packet window.
        layout=[(6,0xc000,16384,0x4000),(2,0xa000,8192,0x4000),(2,0x8000,8192,0xa6a0),
            (7,0xc000,8192,0xa6a0),
            (5,0x4000,6912,0xa6a0),(5,0x6400,7168,0xa6a0)]
        warm_metadata={}
        reset=None
        if self.warm_continuation:
            from warm_startup import reset_ranges, encode_reset, immutable_fixed
            ranges=reset_ranges(h)
            fixed=bytes(cpu.banks[5]+cpu.banks[2])
            invariant=sha(bytes(cpu.banks[6])+immutable_fixed(fixed,ranges))
            if self.warm_immutable is not None and invariant!=self.warm_immutable:
                raise ValueError('warm volumes have different immutable tables or fixed code')
            self.warm_immutable=invariant
            warm_metadata=dict(warm_reset_ranges=ranges,warm_immutable_sha256=invariant,
                warm_compact_checkpoint_sha256=sha(self.states[start-1].tobytes()) if start else None)
            if start:
                reset=encode_reset(fixed,ranges)
                # Keep n-1 at 6400..72FF and immutable fixed code. Reset all
                # mutable cache, wrapper, ZX0 operands/state and stacks.
                layout=[(2,0xa000,8192,0x4000),(2,0x4000,len(reset),0xa6a0),
                    (7,0xc000,8192,0xa6a0),(5,0x4000,6912,0xa6a0)]
        sections=[]
        for bank,address,length,buffer in layout:
            is_reset=reset is not None and bank==2 and address==0x4000
            data=reset if is_reset else bytes(cpu.banks[bank][address&0x3fff:(address&0x3fff)+length])
            packed=self.compress(data)
            storage=data; filtered=False
            if self.startup_delta and bank==6:
                # Adjacent-byte differences are restored once at bootstrap;
                # the runtime Huffman tables and all frame packets stay exact.
                delta=bytes([data[0]])+bytes((data[i]-data[i-1])&255 for i in range(1,len(data)))
                candidate=self.compress(delta)
                if sectors(candidate)<sectors(packed):
                    packed=candidate; storage=delta; filtered=True
            capacity=6912 if buffer==0x4000 else 4608
            if len(padded(packed))>capacity: raise ValueError(f'startup section too large: {bank}/{address:x}: {len(packed)}')
            sections.append(dict(bank=bank,address=address,buffer=buffer,sectors=sectors(packed),
                decoded_bytes=len(data),compressed_bytes=len(packed),sha256=sha(data),data=padded(packed)))
            if is_reset: sections[-1]['warm_reset']=True
            if filtered: sections[-1].update(startup_delta=True,storage_sha256=sha(storage),
                baseline_compressed_bytes=len(self.compress(data)),restore_tstates=541426)
        labels=dict(driver,**{k:dl[k] for k in ('disk_full_call','disk_return')},
            publish_out=h.video['publish_out'],audio_tick_empty=h.audio['audio_tick_empty'],
            audio_tick_done=h.audio['audio_tick_done'],audio_write_loop=h.audio['audio_write_loop'],
            audio_ticks_played=h.audio['audio_ticks_played'],audio_underruns=h.audio['audio_underruns'],
            elapsed_fields=h.audio['elapsed_fields'],published=h.video['published'],
            late_fields=h.video['late_fields'],fatal=h.audio['fatal'],zx0_fatal=h.z['fatal'])
        for name in ('fast_read_enter','fast_disk_return','fast_read_retry','disk_finish'):
            if name in dl: labels[name]=dl[name]
        for name in ('seek_side_enter','seek_side_return','seek_enter','seek_return'):
            if name in seek_labels: labels[name]=seek_labels[name]
        return sections,dict(**warm_metadata,player_labels=labels,decoder_labels=h.z,disk_labels=dl,
            seek_labels=seek_labels,deferred_labels=deferred_labels,
            initial_cached_track=initial_track,
            packet_labels=h.p,clock_labels=clock.labels,audio_labels=h.audio,next_loader_labels=next_loader,
            native_ready_pcs=[row['address']+3 for row in clock.listing
                if row['instruction'] in ('CALL native zero','CALL draw_compact')],
            disk_instruction_listing=listing,reconstruction_bytes=len(h.frame.recon_code),
            decoder_end=h.z['end'],clock_end=clock.labels['end'],driver_end=driver['end'])

    def volume(self, start, end, part):
        if not 0 <= start < end <= len(self.states) or end-start > 65535//6:
            raise ValueError('volume must contain 1..10922 frames (16-bit AY counter)')
        if not 1 <= part <= 65534:
            raise ValueError('volume ordinal exceeds the disk-change format')
        stream,blocks=self.stream(start,end)
        ns=sectors(stream); video_sector=64
        boot=build_boot_basic()
        if self.ends is None: raise ValueError('set the complete volume boundaries before building')
        if self.warm_continuation:
            if part>len(self.ends) or end!=self.ends[part-1] or start!=(self.ends[part-2] if part>1 else 0):
                raise ValueError('warm volumes must use the complete declared sequential partition')
            if start:
                boot+=basic_line(40,bytes([0xf5])+b' "START WITH DISK 1"')
        disk_id=volume_id(self.raw,self.ends,part)
        if self.warm_continuation:
            # A normal set, or another warm binary/options set, must never
            # be accepted by a continuation loader with retained RAM.
            options=dict(fast_disk=self.fast_disk,cached_seek=self.cached_seek,cold_track=self.cold_track,
                interleaved=self.interleaved,deferred_limit=self.deferred_limit,keepalive_fields=self.keepalive_fields,
                frame_service=self.frame_service,cold_bitmaps=self.cold_bitmaps,inline_matches=self.inline_matches)
            if self.startup_delta: options['startup_delta']=True
            if self.fast_noop_scan: options['fast_noop_scan']=True
            if self.static_cache_borders: options['static_cache_borders']=True
            if self.carry_huffman: options['carry_huffman']=True
            if self.register_fragments: options['register_fragments']=True
            if self.cached_huffman_byte: options['cached_huffman_byte']=True
            if self.irq_safe_paging: options['irq_safe_paging']=True
            contract=b'WARM1'+json.dumps(options,sort_keys=True).encode()+self.states.tobytes()
            disk_id=volume_id(self.raw+contract,self.ends,part)
        next_id=disk_id[:14]+struct.pack('<H',part+1)
        for attempt in range(8):
            positions=list(disk_layout.positions(ns+1,video_sector%16)) if self.interleaved else list(range(ns+1))
            sections,metadata=self.ram(start,end,video_sector+positions[min(256,ns)],max(0,ns-256))
            for s in sections: s['sector']=0
            player,_=disk.build_bootstrap(sections,video_sector,ns,next_id=next_id,interleaved=self.interleaved,
                warm_set=self.warm_continuation,continuation=bool(start and self.warm_continuation))
            files=[TrdFile('boot','B',boot,basic_variables_offset=len(boot),autostart_line=10),
                TrdFile('PLAYER','C',player,start=0x6000)]
            if calculate_file_start(files[:1])!=(1,1) or len(player)!=1024:
                raise ValueError('next-volume loader requires PLAYER at sector 17, four sectors')
            track,sector=calculate_file_start(files); position=track*16+sector
            for s in sections: s['sector']=position; position+=s['sectors']
            if position==video_sector: break
            video_sector=position
        else: raise ValueError('bootstrap size did not converge')
        player,boot_labels=disk.build_bootstrap(sections,video_sector,ns,next_id=next_id,interleaved=self.interleaved,
            warm_set=self.warm_continuation,continuation=bool(start and self.warm_continuation))
        files[1]=TrdFile('PLAYER','C',player,start=0x6000)
        files.extend(TrdFile(f'INIT{i}','C',s['data']) for i,s in enumerate(sections))
        physical=disk_layout.arrange(padded(stream),video_sector%16) if self.interleaved else padded(stream)
        files.extend(TrdFile(f'VIDEO{i:03}','C',physical[p:p+65280]) for i,p in enumerate(range(0,len(physical),65280)))
        used=video_sector-16+len(physical)//256
        metadata.update(part=part,frame_start=start,frame_end_exclusive=end,frames=end-start,
            fast_disk=self.fast_disk,cached_seek=self.cached_seek,deferred_limit=self.deferred_limit,keepalive_fields=self.keepalive_fields,
            frame_service=self.frame_service,
            cold_bitmaps=self.cold_bitmaps,
            inline_matches=self.inline_matches,
            fast_noop_scan=self.fast_noop_scan,
            static_cache_borders=self.static_cache_borders,
            carry_huffman=self.carry_huffman,
            register_fragments=self.register_fragments,
            cached_huffman_byte=self.cached_huffman_byte,
            irq_safe_paging=self.irq_safe_paging,
            warm_continuation=self.warm_continuation,independently_bootable=not (start and self.warm_continuation),
            startup_delta=self.startup_delta,
            forced_native_map_frames=list(range(start,min(start+2,end))) if self.cold_bitmaps and start else [],
            required_trdos_sha256=disk.TRDOS_503_SHA256 if self.fast_disk else None,
            interleaved=self.interleaved,video_physical_sectors=len(physical)//256,
            layout_padding_sectors=len(physical)//256-ns,
            duration_seconds=(end-start)*3/25,video_bytes=len(stream),video_sectors=ns,
            video_start_sector=video_sector,used_sectors=used,free_sectors=2544-used,
            raw_sha256=sha(self.raw),states_sha256=sha(self.states.tobytes()),
            pixel_changes=False,ay_changes=False,fps='25/3',ay_hz=50,release=False,
            timing_verified=False,disk_delivery_verified=False,
            bootstrap_labels=boot_labels,bootstrap_overlay_jump_tstates=10 if 'overlay_jump' in boot_labels else 0,blocks=blocks,
            sections=[{k:v for k,v in s.items() if k!='data'} for s in sections],disk_id_hex=disk_id.hex(),
            has_next=end<len(self.states),next_part=part+1 if end<len(self.states) else None,
            disk_change='automatic poll of series fingerprint and volume ordinal in reserved system sector 15')
        if used>2544: return None,metadata
        image,directory,stats=place_files(files,f'FAP3-{part:02}')
        image=bytearray(image); image[15*256:15*256+16]=disk_id; image=bytes(image)
        metadata.update(directory=directory,stats=stats,trd_sha256=sha(image))
        return image,metadata

    def automatic_ends(self, max_frames=4096):
        """Partition by measured ZX0 bytes, then check real bootstrap/TRD sizes.

        Leave 16 sectors for checkpoint/fingerprint convergence. This is a
        bounded fit, not a proof of the smallest possible number of disks.
        """
        if getattr(self,'warm_continuation',False):
            raise ValueError('warm experiment requires explicit sequential boundaries')
        if not 1 <= max_frames <= 65535//6:
            raise ValueError('max_frames must be in 1..10922')
        weights=[0]
        for pos in range(0,len(self.raw),8192):
            weights.append(weights[-1]+4+len(self.compress(self.raw[pos:pos+8192])))
        positions=[]
        for pos in self.offsets:
            block,offset=divmod(pos,8192)
            if block==len(weights)-1: positions.append(float(weights[-1]))
            else:
                size=min(8192,len(self.raw)-block*8192)
                positions.append(weights[block]+(weights[block+1]-weights[block])*offset/size)
        self.ends=[len(self.states)]
        ends=[]; start=0
        while start<len(self.states):
            # Initial estimate reserves 32 KiB for bootstrap/checkpoint and layout.
            end=min(len(self.states),start+max_frames,
                max(start+1,bisect_right(positions,positions[start]+(2544-128)*256)-1))
            while True:
                _,meta=self.volume(start,end,len(ends)+1)
                if meta['free_sectors']>=16: break
                if end==start+1: raise ValueError('one frame and its checkpoint do not fit a TRD')
                excess=16-meta['free_sectors']
                remove=max(1,round((end-start)*excess/max(1,meta['video_sectors'])))
                end=max(start+1,end-remove)
            ends.append(end); start=end
            print(f'Planned disk {len(ends)}: {meta["frames"]} frames, {meta["free_sectors"]} free sectors',flush=True)
        self.ends=ends
        return ends


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('raw','states','zx0','cache','output'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--ends',help='exclusive frame ends, including final count')
    p.add_argument('--volumes',type=int,default=4,help='number of experimental volumes; release target remains three')
    p.add_argument('--prefix',default='ZX-video-optimized-preview')
    p.add_argument('--fast-disk',action='store_true',help='TR-DOS 5.03 same-track direct reads, normal dispatcher fallback')
    p.add_argument('--cached-seek',action='store_true',help='Known track and side changes without the full TR-DOS dispatcher; requires --fast-disk')
    p.add_argument('--cold-track',action='store_true',help='Control experiment: ignore the track already selected by bootstrap')
    p.add_argument('--interleaved',action='store_true',help='Arrange full video tracks in 1,9,2,10,... sector order')
    p.add_argument('--deferred-limit',type=int,default=0,help='Experimental idle disk reads: keep at most N-1 freed sectors pending (1..248); 0 disables')
    p.add_argument('--keepalive-fields',type=int,default=0,help='Experimental current-cylinder SEEK after idle fields; requires deferred cached reads')
    p.add_argument('--frame-service',action='store_true',help='Check overdue disk service after every published frame as well as idle waits')
    p.add_argument('--cold-bitmaps',action='store_true',help='Experimental smaller native checkpoints; redraw the first two frames of later disks')
    p.add_argument('--inline-matches',action='store_true',help='Experimental ZX0 match copies without per-match CALL/RET')
    p.add_argument('--fast-noop-scan',action='store_true',help='Experimental combined unchanged-tile checks; no extra copying')
    p.add_argument('--irq-safe-paging',action='store_true',help='Experimental restartable bank changes without DI')
    p.add_argument('--static-cache-borders',action='store_true',help='Skip virtual-row clearing when the edge stripe is unchanged')
    p.add_argument('--carry-huffman',action='store_true',help='Use carry to advance the Huffman bit position')
    p.add_argument('--register-fragments',action='store_true',help='Write repeated fragment rows directly from registers')
    p.add_argument('--startup-delta',action='store_true',help='Try adjacent-byte differences for boot tables; preserve independent boot')
    p.add_argument('--trdos-rom',type=Path,help='Required ROM hash check for --fast-disk')
    p.add_argument('--cached-huffman-byte',action='store_true',help='Cache the current Huffman byte in B; requires --carry-huffman')
    args=p.parse_args()
    if args.cached_huffman_byte and not args.carry_huffman: p.error('--cached-huffman-byte requires --carry-huffman')
    if not 1<=args.volumes<=255: p.error('--volumes must be between 1 and 255')
    if args.cached_seek and not args.fast_disk: p.error('--cached-seek requires --fast-disk')
    if args.cold_track and not args.cached_seek: p.error('--cold-track requires --cached-seek')
    if args.fast_disk and (not args.trdos_rom or sha(args.trdos_rom.read_bytes())!=disk.TRDOS_503_SHA256):
        p.error('--fast-disk requires the verified TR-DOS 5.03 ROM')
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    b=Builder(args.raw.read_bytes(),states,args.zx0.resolve(),args.cache.resolve(),fast_disk=args.fast_disk,
        cached_seek=args.cached_seek,cold_track=args.cold_track,interleaved=args.interleaved,deferred_limit=args.deferred_limit,
        keepalive_fields=args.keepalive_fields,frame_service=args.frame_service,cold_bitmaps=args.cold_bitmaps,inline_matches=args.inline_matches,
        startup_delta=args.startup_delta,fast_noop_scan=args.fast_noop_scan,irq_safe_paging=args.irq_safe_paging,static_cache_borders=args.static_cache_borders,carry_huffman=args.carry_huffman,register_fragments=args.register_fragments,cached_huffman_byte=args.cached_huffman_byte)
    if args.ends: ends=[int(n) for n in args.ends.split(',')]
    else:
        # Storage weights use the already measured global block boundaries.
        weights=[0.0]; total=0
        for i in range(0,len(b.raw),8192):
            length=len(b.raw[i:i+8192]); total+=len(b.compress(b.raw[i:i+8192]))+4; weights.append(total)
        positions=[weights[o//8192]+(weights[min(o//8192+1,len(weights)-1)]-weights[o//8192])*(o%8192)/8192
            for o in b.offsets]
        ends=[min(range(1,len(states)),key=lambda i:abs(positions[i]-total*f/args.volumes))
            for f in range(1,args.volumes)]+[len(states)]
    if ends[-1]!=len(states) or ends!=sorted(set(ends)) or ends[0]<=0: raise ValueError('invalid volume boundaries')
    b.ends=ends
    args.output.mkdir(parents=True,exist_ok=True)
    start=0; result=[]
    for part,end in enumerate(ends,1):
        print(f'Building volume {part}: frames {start}..{end-1}',flush=True)
        image,meta=b.volume(start,end,part)
        stem=f'{args.prefix}_part{part:02}'
        (args.output/(stem+'.json')).write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
        if image is not None: (args.output/(stem+'.trd')).write_bytes(image)
        result.append({k:meta[k] for k in ('part','frame_start','frame_end_exclusive','video_bytes','used_sectors','free_sectors')})
        print(json.dumps(result[-1]),flush=True); start=end
    (args.output/'volumes.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    if any(r['free_sectors']<0 for r in result): raise SystemExit('Some volumes do not fit; adjust --ends or volume count.')


if __name__=='__main__': main()
