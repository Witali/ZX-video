"""Experimental real TRD integration: three video slots and resident AYH1.

Keeps the existing renderers, exact video fields, 50-Hz ISR and six-field
schedule. The legacy integrated builder remains unchanged. All patches
check the old machine code; new runtime code is loaded by the bootstrap.
"""
import struct

from ay_huffman_stream import encode as encode_audio
from build_fap3_trd import padded, sectors, sha, player_harness
from build_zxv_trd import MiniAssembler, TrdFile
from bulk_frame_stream import read_packet
import bulk_frame_z80 as packet
from integrated_bootstrap import Builder as PreviousBuilder
from measure_volume_huffman import identify
from pipelined_frame_z80 import helpers, PAGE, SHADOW
from probe_motion_entropy import Reader
from probe_startup_tables import undifference
import resident_audio_z80 as resident
from zx0_codec import decompress

HELPERS = 0xdb20
SEGMENT_HOOKS = 0x78a0


def service(audio, refill, *, threshold=24):
    """Preserve all registers; no bank change when at least threshold queued."""
    if not 6 <= threshold <= 26: raise ValueError('threshold must leave six FIFO slots')
    a, rows = MiniAssembler(audio['audio_enqueue_six']), []
    e,n = helpers(a,rows,'resident_audio_service')
    a.label('service')
    e('PUSH AF',[0xf5],11); e('PUSH HL',[0xe5],11)
    n('LD HL,read index',0x21,audio['audio_read_index'],10)
    n('LD A,(write index)',0x3a,audio['audio_write_index'],13)
    e('SUB (HL)',[0x96],7); e('AND 31',[0xe6,31],7)
    e('CP threshold',[0xfe,threshold],7); e('POP HL',[0xe1],10)
    rows.append(dict(address=a.pc,instruction='JR C,refill',tstates=[7,12],phase='resident_audio_service'))
    a.rel8(0x38,'refill')
    e('POP AF',[0xf1],10); e('RET',[0xc9],10)
    a.label('refill'); e('POP AF',[0xf1],10)
    n('JP refill bridge',0xc3,refill,10)
    return a.resolve(),dict(a.labels),rows


def bank_helpers(audio, queue, service_entry, *, frame_entries=None):
    a, rows = MiniAssembler(HELPERS), []
    e,n = helpers(a,rows,'resident_audio_hooks')
    for name, source in (('queue_service',queue['phase']),('drain_service',audio['audio_enabled'])):
        a.label(name); n('CALL audio service',0xcd,service_entry,17)
        n('LD A,original source',0x3a,source,13); e('RET',[0xc9],10)
    a.label('advance_slot')
    e('INC A',[0x3c],4); e('CP 3',[0xfe,3],7)
    e('RET C',[0xd8],[5,11]); e('XOR A',[0xaf],4); e('RET',[0xc9],10)
    for name,target in (frame_entries or {}).items():
        a.label(name);n('CALL audio service',0xcd,service_entry,17)
        n('JP original frame entry',0xc3,target,10)
    a.label('end')
    if a.pc > 0xdc00: raise ValueError('audio hooks overlap video packet code')
    return a.resolve(),dict(a.labels),rows


def install(read8, put, metadata, coded_audio, h, *, batch=6, foreground_audio=False):
    """Install into the already generated, cold-bootable baseline RAM image."""
    m=metadata; audio=m['audio_labels']; q=m['queue_labels']; p=m['producer_labels']
    banked=coded_audio[:4]==b'AYB1'
    if banked:
        import banked_resident_audio
        compiled=banked_resident_audio.build(coded_audio,audio,batch=batch)
    else:compiled=resident.build(coded_audio,audio,batch=batch)
    patches=[]; added=[]; removed=[]
    free=next((r for r in m['retired_fixed_code'] if r['end']-r['start']>=35),None)
    if free is None: raise ValueError('no fixed RAM for resident initializer/segment bridge')
    # The in-place producer uses 7823h..789Fh. This following fixed-RAM gap
    # ends before the old 7900h frame wrapper, and remains mapped during AY.
    segment_hooks=banked_resident_audio.hooks(SEGMENT_HOOKS,compiled,page=PAGE) if banked else None
    if banked and segment_hooks['labels']['end']>0x7900:raise ValueError('audio segment helper overlaps frame wrapper')

    def replace(address,before,after,old_ticks,new_ticks,reason):
        current=bytes(read8(address+i) for i in range(len(before)))
        if current!=before or len(before)!=len(after):
            raise ValueError(('unexpected resident integration patch',hex(address),reason,current.hex(),before.hex()))
        put(address,after)
        patches.append(dict(address=address,before_hex=before.hex(),code_hex=after.hex(),
            previous_tstates=old_ticks,tstates=new_ticks,reason=reason))
        removed.append((address,address+len(before)))

    # Reuse the old enqueue routine's fixed, uncontended RAM.
    origin=audio['audio_enqueue_six']
    guard, guard_labels, guard_rows=service(audio,0)
    refill=resident.bridge(origin+len(guard),segment_hooks['labels']['fill'] if banked else compiled['labels']['fill'],
        page=PAGE,shadow=SHADOW,bank_address=segment_hooks['labels']['active_bank'] if banked else None)
    guard,guard_labels,guard_rows=service(audio,refill['origin'])
    payload=guard+bytes.fromhex(refill['code_hex'])
    if origin+len(payload)>audio['audio_start']:
        raise ValueError('audio bridge exceeds retired enqueue routine')
    old=bytes(read8(i) for i in range(origin,audio['audio_start']))
    put(origin,payload+bytes(len(old)-len(payload)))
    retired_enqueue=dict(address=origin,bytes=len(old),sha256=sha(old))
    added+=guard_rows+refill['listing']; removed.append((origin,audio['audio_start']))

    # Initialization runs once before setup_clock, with interrupts disabled.
    init=resident.bridge(free['start'],segment_hooks['labels']['init'] if banked else compiled['labels']['init'],page=PAGE,shadow=SHADOW)
    blob=bytes.fromhex(init['code_hex'])
    if banked:
        assert len(blob)==35
        added+=segment_hooks['listing']
    if any(read8(i) for i in range(init['origin'],init['origin']+len(blob))):
        raise ValueError('initializer bridge space is not retired')
    put(init['origin'],blob); added+=init['listing']
    replace(audio['audio_init'],b'\xe5\x54\x5d',b'\xc3'+init['origin'].to_bytes(2,'little'),
            19,10,'tail call resident initializer')

    frame_entries={}
    if foreground_audio:
        frame_entries={name:m['packet_labels'][target] for name,target in
            (('frame_service','next_frame'),('prepare_service','prepare_bridge'),('draw_service','draw_bridge'))}
    code,hl,rows=bank_helpers(audio,q,guard_labels['service'],frame_entries=frame_entries)
    if banked:
        segment_code=bytes.fromhex(segment_hooks['code_hex'])
        if any(read8(SEGMENT_HOOKS+i) for i in range(len(segment_code))):
            raise ValueError('audio segment helper space is occupied')
        put(SEGMENT_HOOKS,segment_code)
    if any(read8(i) for i in range(HELPERS,HELPERS+len(code))):
        raise ValueError('retired ring-reader tail is not free')
    put(HELPERS,code); added+=rows
    for address,source,target,reason in (
            (q['step'],q['phase'],hl['queue_service'],'service AY before a disk/decode step'),
            (audio['audio_drain'],audio['audio_enabled'],hl['drain_service'],'service AY during final drain')):
        replace(address,b'\x3a'+source.to_bytes(2,'little'),b'\xcd'+target.to_bytes(2,'little'),
                13,17,reason)
        added.append(dict(address=address,instruction='CALL '+reason,tstates=17,phase='resident_audio_hooks'))

    queue_rows=m['slot_queue_instruction_listing']
    if foreground_audio:
        targets={'CALL compact zero':'frame_service','CALL compact one':'frame_service',
            'CALL reconstruct pending packet':'prepare_service','CALL native zero':'draw_service',
            'CALL draw_compact':'draw_service'}
        matched=[]
        for row in queue_rows:
            name=row['instruction']
            if m['clock_labels']['prime']<=row['address']<m['clock_labels']['end'] and name in targets:
                helper=targets[name];at=row['address']
                replace(at,b'\xcd'+frame_entries[helper].to_bytes(2,'little'),
                    b'\xcd'+hl[helper].to_bytes(2,'little'),17,17,'service AY before '+name)
                added.append(row);matched.append(name)
        # The priming call is omitted for one frame, but the (unreached)
        # play_one loop still contains its reconstruction service call.
        expected=set(targets)-({'CALL compact one'} if m['frames']==1 else set())
        if set(matched)!=expected:raise ValueError(('frame service hook layout differs',matched))
    for base,hi in ((q['step'],q['active']),(p['begin'],p['step'])):
        candidates=[r for r in queue_rows if base<=r['address']<hi and r['instruction']=='CP 4']
        if len(candidates)!=1: raise ValueError('unexpected four-slot admission check')
        row=candidates[0]
        replace(row['address'],b'\xfe\x04',b'\xfe\x03',7,7,'limit video slots to banks 0/1/3')
        added.append(dict(row,instruction='CP 3'))
    for lo,hi in ((q['block_ready'],q['worked']),(q['release'],q['retained'])):
        candidates=[r for r in queue_rows if lo<=r['address']<hi and r['instruction']=='INC A']
        if len(candidates)!=1: raise ValueError('unexpected slot cursor advance')
        at=candidates[0]['address']
        replace(at,b'\x3c\xe6\x03',b'\xcd'+hl['advance_slot'].to_bytes(2,'little'),
                11,17,'three-slot cursor: helper adds 22/30 T, total 39/47 T')
        added.append(dict(address=at,instruction='CALL advance three-slot cursor',tstates=17,phase='slot_queue'))

    _,_,labels,packet_rows=packet.build(m['decoder_labels'],q,h.frame.w,h.frame.draw,
        m['compiled_masks']['labels'],audio,stored_guards=False,separate_prepare='idle',page_entry=PAGE)
    if labels!=m['packet_labels']: raise ValueError('packet code addresses differ')
    maximum=m['cached_huffman_lookahead']['packet_contract']['maximum_payload_bytes']
    for row in packet_rows:
        at=row['address']; name=row['instruction']
        if name=='LD DE,minimum length':
            replace(at,b'\x11\x26\x01',b'\x11\x20\x01',10,10,'video-only minimum 294 -> 288')
        elif name=='LD DE,valid length range':
            replace(at,b'\x11'+(maximum-294+1).to_bytes(2,'little'),
                    b'\x11'+(maximum-288+1).to_bytes(2,'little'),10,10,'video-only packet bound')
        elif name=='CALL enqueue_six':
            replace(at,b'\xcd'+audio['audio_enqueue_six'].to_bytes(2,'little'),
                    b'\xc3'+labels['video_payload_ready'].to_bytes(2,'little'),17,10,'no muxed AY prefix')
            added.append(dict(row,instruction='JP video payload ready',tstates=10))
        else:
            added.append(row)
        if name.startswith('LD DE,') and any(lo<=at<hi for lo,hi in removed):
            added.append(row)
    for segment in compiled['segments'] if banked else [compiled]:
        put(resident.ORIGIN,bytes.fromhex(segment['image_hex']),segment['bank'])
    m['slot_queue_instruction_listing']=[r for r in queue_rows
        if not any(lo<=r['address']<hi for lo,hi in removed)]+added
    m['resident_audio']=dict(enabled=True,format='video-only FAP3 packets + resident AYH1',
        compiled=compiled,refill_bridge=refill,init_bridge=init,service_labels=guard_labels,
        service_threshold=24,service_skip_tstates=103,service_refill_prefix_tstates=108,
        foreground_audio=foreground_audio,foreground_hook_extra_tstates=27 if foreground_audio else 0,
        hooks=hl,hook_bytes=len(code),patches=patches,retired_enqueue=retired_enqueue,
        code_regions=[dict(address=origin,code_hex=payload.hex()),dict(address=HELPERS,code_hex=code.hex()),
                      dict(address=init['origin'],code_hex=blob.hex())],
        video_slot_banks=[0,1,3],video_ready_history_bytes=24576,
        packet_minimum_bytes=288,packet_maximum_bytes=maximum,stored_guards=0,readable_guards=2,
        queue_step_extra_skipped_tstates=147,queue_cursor_tstates_before=11,
        queue_cursor_tstates_after=[39,47],queue_cursor_delta_tstates=[28,36],
        packet_parser_delta_excluding_removed_enqueue_tstates=-7,
        audio_isr_changed=False)
    if banked:
        m['resident_audio'].update(format='video-only packets + two-bank AYB1',banks=[4,6],
            segment_hooks=segment_hooks,segment_boundary_ticks=compiled['segment_ticks'][0],
            global_tick_counter_preserved=True,fifo_preserved_at_boundary=True)
        m['resident_audio']['code_regions'].append(dict(address=SEGMENT_HOOKS,code_hex=segment_hooks['code_hex']))
    return compiled


class Builder(PreviousBuilder):
    def __init__(self,*args,series_fingerprint=None,audio_batch=6,foreground_audio=False,**kwargs):
        super().__init__(*args,**kwargs)
        if (not self.bank2_zx0 or not self.cached_huffman_lookahead or self.audio_wait_prefetch
                or self.ready_packet_guard or self.packet_prefix_guard or self.streaming_input):
            raise ValueError('resident mode requires bank-2 ZX0/two-byte Huffman cache without old audio or stream guards')
        self.series_fingerprint=series_fingerprint
        self.audio_batch=audio_batch
        self.foreground_audio=foreground_audio
        self.resident_streams={}

    def separated(self,start,end):
        key=start,end
        if key not in self.resident_streams:
            r=Reader(self.stream_block(self.offsets[start],self.offsets[end],start,end))
            video=bytearray(); ticks=[]
            for _ in range(end-start):
                _,detail=read_packet(r,stored_guards=False)
                ticks.extend(detail['ticks'])
                prefix=b''.join(detail['ticks']); body=detail['payload'][len(prefix):]
                if detail['payload']!=prefix+body: raise AssertionError('mux prefix mismatch')
                video+=struct.pack('<H',len(body))+body
            r.end()
            sound,_=encode_audio(ticks,self.ay[start])
            self.resident_streams[key]=(bytes(video),sound)
        return self.resident_streams[key]

    def stream(self,start,end):
        video,_=self.separated(start,end)
        result=bytearray();blocks=[]
        for lo in range(0,len(video),8192):
            chunk=video[lo:lo+8192]; coded=self.compress(chunk)
            result+=struct.pack('<HH',len(chunk),len(coded))+coded
            blocks.append(dict(raw_start=lo,raw_end=lo+len(chunk),decoded_bytes=len(chunk),
                zx0_bytes=len(coded),sha256=sha(chunk)))
        return bytes(result),blocks

    def ram(self,start,end,next_sector,remaining):
        sections,m=super().ram(start,end,next_sector,remaining)
        banks=self.expected_banks
        def bank_at(address):return 5 if address<0x8000 else 2 if address<0xc000 else 7
        def read8(address):return banks[bank_at(address)][address&16383]
        def put(address,data,bank=None):
            at=address&16383
            if at+len(data)>16384:raise ValueError('cross-bank resident install')
            banks[bank_at(address) if bank is None else bank][at:at+len(data)]=data
        h=player_harness(bytes(4),self.tables,self.mapping,end-start,
            **{k:getattr(self,k) for k in ('inline_matches','fast_noop_scan','irq_safe_paging',
                'static_cache_borders','carry_huffman','register_fragments','cached_huffman_byte')})
        _,sound=self.separated(start,end)
        compiled=install(read8,put,m,sound,h,batch=self.audio_batch,foreground_audio=self.foreground_audio)
        # Recompress modified existing sections without changing startup order.
        changed=[]
        for s in sections:
            if sound[:4]==b'AYB1' and s['bank']==6:continue
            raw=bytes(banks[s['bank']][s['address']&16383:(s['address']&16383)+s['decoded_bytes']])
            if sha(raw)==s['sha256']:
                changed.append(s);continue
            if s.get('startup_delta'):raise ValueError('unexpected changed entropy table section')
            packed=self.compress(raw)
            changed.append(dict(s,data=padded(packed),compressed_bytes=len(packed),
                sectors=sectors(packed),sha256=sha(raw)))
        # Load bank 4 before the last section restores the visible screen.
        audio_sections=[]
        for segment in compiled.get('segments',[compiled]):
            image=bytes.fromhex(segment['image_hex']);at=0
            while at<len(image):
                length=min(8192,len(image)-at)
                while True:
                    raw=image[at:at+length];packed=self.compress(raw)
                    if len(padded(packed))<=6912:break
                    length-=256
                    if length<=0:raise ValueError('audio startup staging cannot fit')
                audio_sections.append(dict(bank=segment['bank'],address=0xc000+at,buffer=0x4000,
                    decoded_bytes=len(raw),compressed_bytes=len(packed),sectors=sectors(packed),
                    sha256=sha(raw),data=padded(packed)))
                at+=len(raw)
        result=changed[:-1]+audio_sections+changed[-1:]
        m['resident_audio']['startup_sections']=len(audio_sections)
        m['resident_audio']['coded_audio_sha256']=sha(sound)
        m['resident_audio']['coded_audio_bytes']=len(sound)
        self.expected_banks=banks
        return result,m

    def place_sections(self,sections,position):
        payload=bytearray()
        for s in sections:
            capacity=6912 if s['buffer']==0x4000 else 4608
            offset=len(payload)%256
            if (offset+s['compressed_bytes']+255)//256*256>capacity:
                payload.extend(bytes((-len(payload))%256)); offset=0
            s.update(sector=position+len(payload)//256,source_offset=offset,
                sectors=(offset+s['compressed_bytes']+255)//256)
            if s['sectors']*256>capacity:raise ValueError('resident startup section exceeds staging')
            payload.extend(s['data'][:s['compressed_bytes']])
        return [TrdFile('INIT','C',padded(bytes(payload)))],position+sectors(payload)

    def volume(self,start,end,part):
        if self.series_fingerprint is None or len(self.series_fingerprint)!=14:
            raise ValueError('resident disk set needs an explicit format-specific series fingerprint')
        image,m=super().volume(start,end,part)
        if image is not None:image=identify(image,m,self.series_fingerprint)
        return image,m
