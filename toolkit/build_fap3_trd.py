"""Build independently bootable experimental FAP3/ZX0 volumes.

Uses the existing packets, Huffman tables, exact compact checkpoints and
AY register history. Only ZX0 blocks touching a volume boundary change.
No cadence/release claim is made by this builder; validate real disk I/O
and all displayed frames separately in Fuse.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile

import numpy as np

from build_zxv_trd import TrdFile, build_boot_basic
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


def sha(data): return hashlib.sha256(data).hexdigest()
def sectors(data): return (len(data)+255)//256
def padded(data): return data+bytes((-len(data))%256)


class Builder:
    def __init__(self, raw, states, zx0, cache, *, fast_disk=False, cached_seek=False, cold_track=False):
        self.raw, self.states, self.zx0, self.cache = raw, states, zx0, cache
        self.cache.mkdir(parents=True,exist_ok=True)
        self.memo = {}
        self.ends=None
        self.fast_disk=fast_disk
        self.cached_seek=cached_seek
        self.cold_track=cold_track
        r=Reader(raw)
        _,_,count,self.mapping,self.tables=read_header(r,magic=b'FAP3')
        if len(states)!=count: raise ValueError('state/frame count differs')
        self.offsets=[r.pos]; self.ay=[bytes(11)]
        state=bytearray(11)
        for _ in range(count):
            _,detail=read_packet(r,stored_guards=False)
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

    def stream(self, start, end):
        lo,hi=self.offsets[start],self.offsets[end]
        result=bytearray(); blocks=[]
        while lo<hi:
            stop=min(hi,(lo//8192+1)*8192)
            raw=self.raw[lo:stop]; payload=self.compress(raw)
            result+=struct.pack('<HH',len(raw),len(payload))+payload
            blocks.append(dict(raw_start=lo,raw_end=stop,decoded_bytes=len(raw),zx0_bytes=len(payload),sha256=sha(raw)))
            lo=stop
        return bytes(result),blocks

    def ram(self, start, end, next_sector, remaining):
        h=Harness(bytes(4),self.tables,self.mapping,end-start,ring_start=0,
            bulk=True,zero_copy=True,stored_guards=False,skip_noop_runs=True,
            constant_attribute_borders=True,skip_black_borders=True,skip_static_stripes=True,
            token_boundaries=True,pipelined=True,progress_frames=end-start,packet_ahead='idle',
            unrolled_copy=True,unrolled_cache=True,attribute_groups=True,attribute_flags=True,
            gray_cells=True,sparse_patches=True,disk_refill_entry=disk.DISK)
        clock=Clock(h,[],lookahead=True)
        if clock.labels['end']>disk.DRIVER: raise ValueError('clock/driver overlap')
        cpu=h.cpu
        if start: cpu.banks[5][0x2400:0x3300]=self.states[start-1].tobytes()
        for bank,frame in ((5,start-1),(7,start-2)):
            if frame>=0:
                screen=display_screen(self.states[frame].tobytes(),black_borders=True)
                cpu.banks[bank][:6912]=progress.reference_screen(screen,0,end-start)
        # The last bootstrap operation fills the ring using ordinary C=5.
        # Its last track remains selected when runtime playback starts.
        initial_track=(next_sector-1)//16 if self.cached_seek and not self.cold_track else 255
        code, dl, listing=disk.build_disk(next_sector,remaining,fast_disk=self.fast_disk,
            cached_seek=self.cached_seek,initial_track=initial_track)
        for i,value in enumerate(code+bytes(256-len(code))): cpu.write8(0xa100+i,value)
        code,next_loader=disk.build_next_loader()
        for i,value in enumerate(code): cpu.write8(disk.LOAD_NEXT+i,value)
        seek_labels={}
        if self.cached_seek:
            if next_loader['end']>disk.CACHED_SEEK: raise ValueError('next loader overlaps cached seek')
            code,seek_labels,seek_listing=disk.build_cached_seek(dl)
            for i,value in enumerate(code): cpu.write8(disk.CACHED_SEEK+i,value)
            listing+=seek_listing
        code,driver=disk.build_driver(h,clock.labels,self.ay[start],has_next=end<len(self.states))
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
        sections=[]
        for bank,address,length,buffer in layout:
            data=bytes(cpu.banks[bank][address&0x3fff:(address&0x3fff)+length])
            packed=self.compress(data)
            capacity=6912 if buffer==0x4000 else 4608
            if len(padded(packed))>capacity: raise ValueError(f'startup section too large: {bank}/{address:x}: {len(packed)}')
            sections.append(dict(bank=bank,address=address,buffer=buffer,sectors=sectors(packed),
                decoded_bytes=len(data),compressed_bytes=len(packed),sha256=sha(data),data=padded(packed)))
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
        return sections,dict(player_labels=labels,decoder_labels=h.z,disk_labels=dl,
            seek_labels=seek_labels,
            initial_cached_track=initial_track,
            packet_labels=h.p,clock_labels=clock.labels,audio_labels=h.audio,next_loader_labels=next_loader,
            native_ready_pcs=[row['address']+3 for row in clock.listing
                if row['instruction'] in ('CALL native zero','CALL draw_compact')],
            disk_instruction_listing=listing,reconstruction_bytes=len(h.frame.recon_code),
            decoder_end=h.z['end'],clock_end=clock.labels['end'],driver_end=driver['end'])

    def volume(self, start, end, part):
        stream,blocks=self.stream(start,end)
        ns=sectors(stream); video_sector=64
        boot=build_boot_basic()
        if self.ends is None: raise ValueError('set the complete volume boundaries before building')
        series=self.raw+struct.pack('<'+'H'*len(self.ends),*self.ends)
        disk_id=b'FAP3ZXV1'+bytes.fromhex(sha(series))[:6]+struct.pack('<H',part)
        next_id=disk_id[:14]+struct.pack('<H',part+1)
        for attempt in range(8):
            sections,metadata=self.ram(start,end,video_sector+min(256,ns),max(0,ns-256))
            for s in sections: s['sector']=0
            player,_=disk.build_bootstrap(sections,video_sector,ns,next_id=next_id)
            files=[TrdFile('boot','B',boot,basic_variables_offset=len(boot),autostart_line=10),
                TrdFile('PLAYER','C',player,start=0x6000)]
            if calculate_file_start(files[:1])!=(1,1) or len(player)!=1024:
                raise ValueError('next-volume loader requires PLAYER at sector 17, four sectors')
            track,sector=calculate_file_start(files); position=track*16+sector
            for s in sections: s['sector']=position; position+=s['sectors']
            if position==video_sector: break
            video_sector=position
        else: raise ValueError('bootstrap size did not converge')
        player,boot_labels=disk.build_bootstrap(sections,video_sector,ns,next_id=next_id)
        files[1]=TrdFile('PLAYER','C',player,start=0x6000)
        files.extend(TrdFile(f'INIT{i}','C',s['data']) for i,s in enumerate(sections))
        files.extend(TrdFile(f'VIDEO{i:03}','C',chunk) for i,chunk in enumerate(
            padded(stream)[p:p+65280] for p in range(0,len(padded(stream)),65280)))
        used=video_sector-16+ns
        metadata.update(part=part,frame_start=start,frame_end_exclusive=end,frames=end-start,
            fast_disk=self.fast_disk,cached_seek=self.cached_seek,required_trdos_sha256=disk.TRDOS_503_SHA256 if self.fast_disk else None,
            duration_seconds=(end-start)*3/25,video_bytes=len(stream),video_sectors=ns,
            video_start_sector=video_sector,used_sectors=used,free_sectors=2544-used,
            raw_sha256=sha(self.raw),states_sha256=sha(self.states.tobytes()),
            pixel_changes=False,ay_changes=False,fps='25/3',ay_hz=50,release=False,
            timing_verified=False,disk_delivery_verified=False,
            bootstrap_labels=boot_labels,blocks=blocks,
            sections=[{k:v for k,v in s.items() if k!='data'} for s in sections],disk_id_hex=disk_id.hex(),
            has_next=end<len(self.states),next_part=part+1 if end<len(self.states) else None,
            disk_change='automatic poll of series fingerprint and volume ordinal in reserved system sector 15')
        if used>2544: return None,metadata
        image,directory,stats=place_files(files,f'FAP3-{part:02}')
        image=bytearray(image); image[15*256:15*256+16]=disk_id; image=bytes(image)
        metadata.update(directory=directory,stats=stats,trd_sha256=sha(image))
        return image,metadata


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
    p.add_argument('--trdos-rom',type=Path,help='Required ROM hash check for --fast-disk')
    args=p.parse_args()
    if not 1<=args.volumes<=255: p.error('--volumes must be between 1 and 255')
    if args.cached_seek and not args.fast_disk: p.error('--cached-seek requires --fast-disk')
    if args.cold_track and not args.cached_seek: p.error('--cold-track requires --cached-seek')
    if args.fast_disk and (not args.trdos_rom or sha(args.trdos_rom.read_bytes())!=disk.TRDOS_503_SHA256):
        p.error('--fast-disk requires the verified TR-DOS 5.03 ROM')
    with np.load(args.states,allow_pickle=False) as saved: states=saved['states']
    b=Builder(args.raw.read_bytes(),states,args.zx0.resolve(),args.cache.resolve(),fast_disk=args.fast_disk,
        cached_seek=args.cached_seek,cold_track=args.cold_track)
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
