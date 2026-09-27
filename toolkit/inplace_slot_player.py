"""Install a larger decoded-packet reservoir into the resident-AY player."""
import struct
from build_fap3_trd import sha, padded, sectors
from resident_audio_player import Builder as PreviousBuilder
import bank2_zx0
import inplace_slot_input_z80 as producer
from inplace_zx0 import trace, layout


def decoder_patch(read8, put, m):
    regions, labels, _ = bank2_zx0.build()
    if labels!=m['decoder_labels']: raise ValueError('unexpected resident decoder labels')
    sites = []
    for at, code in regions:
        start = 0
        while (index:=code.find(b'\x11\x00\xe0', start))>=0:
            sites.append(at+index); start=index+3
    if len(sites)!=1: raise ValueError('unexpected ZX0 output initialization')
    at = sites[0]
    if bytes(read8(at+i) for i in range(3))!=b'\x11\x00\xe0': raise ValueError('decoder output operand changed')
    put(at, b'\x11\x00\xc0')
    return dict(address=at, previous_hex='1100e0', code_hex='1100c0',
                previous_tstates=10, tstates=10, delta_tstates=0)


def install(read8, put, m):
    if (not m['resident_audio']['foreground_audio'] or m.get('half_row_cache')
            or not m['demand_decode'] or not m['bank2_zx0']['enabled']):
        raise ValueError('requires smaller foreground resident-AY baseline with demand decode')
    old = m['producer_labels']; q = m['queue_labels']; z = m['decoder_labels']
    patches = [decoder_patch(read8, put, m)]
    regions, p, rows = producer.build(z, m['disk_labels'], elapsed_fields=m['player_labels']['elapsed_fields'])
    for at, code in regions:
        if at!=producer.CODE and any(read8(at+i) for i in range(len(code))):
            raise ValueError(('retired helper space occupied', hex(at)))
    entries = {old[k]:p[k] for k in ('begin', 'step', 'page_slot')}
    queue_rows = m['slot_queue_instruction_listing']
    old_rows = [r for r in queue_rows if old['begin']<=r['address']<old['end']]
    updated = []
    for row in queue_rows:
        at = row['address']; name = row['instruction']; before = after = None
        if old['begin']<=at<old['end']: continue
        if row.get('phase')=='slot_bridge' and name.startswith('CALL '):
            operand = read8(at+1)+256*read8(at+2)
            if operand in entries:
                before=b'\xcd'+operand.to_bytes(2, 'little'); after=b'\xcd'+entries[operand].to_bytes(2, 'little')
        if q['step']<=at<q['end'] or q['demand']<=at<q['demand_end']:
            substitutions={'LD HL,E000':(0x21,0xe000,0xc000), 'LD DE,E000':(0x11,0xe000,0xc000),
                           'LD DE,2000':(0x11,0x2000,0x4000), 'LD BC,2000':(0x01,0x2000,0x4000)}
            if name in substitutions:
                op, lo, hi = substitutions[name]
                before=bytes([op])+lo.to_bytes(2,'little'); after=bytes([op])+hi.to_bytes(2,'little')
                row=dict(row,instruction=name.replace('E000','C000').replace('2000','4000'))
        if before is not None:
            if bytes(read8(at+i) for i in range(len(before)))!=before:
                raise ValueError(('unexpected queue operand', hex(at), name))
            put(at, after)
            # The cold installer restores the bridge from this fixed-bank overlay.
            if 0x6100<=at<0x6200:
                mirror=0xa200+at-0x6100
                if bytes(read8(mirror+i) for i in range(len(before)))!=before:
                    raise ValueError('cold bridge overlay differs')
                put(mirror, after)
            patches.append(dict(address=at,previous_hex=before.hex(),code_hex=after.hex(),
                previous_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
        updated.append(row)
    if len(patches)!=11: raise ValueError(('expected decoder, four bridge and six queue substitutions',len(patches)))
    for at, code in regions: put(at, code)
    if p['end']<old['end']: put(p['end'],bytes(old['end']-p['end']))
    m['producer_labels']=p
    for key,value in list(m['player_labels'].items()):
        if value==old['fatal']: m['player_labels'][key]=p['fatal']
    m['slot_queue_instruction_listing']=updated+rows
    m['resident_audio']['video_ready_history_bytes']=3*producer.MAX_OUTPUT
    m['inplace_video']=dict(enabled=True, maximum_decoded_bytes=producer.MAX_OUTPUT, output_base=producer.OUTPUT,
        video_ready_history_bytes=3*producer.MAX_OUTPUT, carry=producer.CARRY,
        previous_producer_bytes=old['end']-old['begin'], producer_bytes=sum(len(b) for _,b in regions),
        previous_producer_listing=old_rows, producer_listing=rows, patches=patches,
        regions=[dict(address=at,code_hex=code.hex()) for at,code in regions],
        decoder_and_queue_instruction_delta_tstates=0, producer_timing_requires_execution=True,
        shared_tail_saved_before_decode=True, runtime_sector_destinations=['BC00 header/carry', 'C000..FF00 slot'],
        head_reload_after_fields=64, head_reload_uses_existing_cached_seek=True,
        elapsed_fields=m['player_labels']['elapsed_fields'],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


class Builder(PreviousBuilder):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.inplace_streams={}

    def stream(self,start,end):
        key=start,end
        if key not in self.inplace_streams:
            video,_=self.separated(start,end); stream=bytearray(); blocks=[]
            for lo in range(0,len(video),producer.MAX_OUTPUT):
                raw=video[lo:lo+producer.MAX_OUTPUT]; payload=self.compress(raw)
                exact,proof=trace(payload,limit=len(raw))
                plan=layout(len(payload),len(raw),proof['minimum_input_start'],len(stream))
                if exact!=raw or not plan['sector_aligned_fits']: raise ValueError('unsafe in-place ZX0 block; repartition required')
                blocks.append(dict(raw_start=lo,raw_end=lo+len(raw),decoded_bytes=len(raw),zx0_bytes=len(payload),
                    sha256=sha(raw),inplace_proof=proof,inplace_layout=plan))
                stream+=struct.pack('<HH',len(raw),len(payload))+payload
            self.inplace_streams[key]=bytes(stream),blocks
        return self.inplace_streams[key]

    def ram(self,start,end,next_sector,remaining):
        sections,m=super().ram(start,end,next_sector,remaining); banks=self.expected_banks
        def bank_at(at): return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at): return banks[bank_at(at)][at&16383]
        def put(at,code):
            if (at&16383)+len(code)>16384: raise ValueError('cross-bank in-place patch')
            banks[bank_at(at)][at&16383:(at&16383)+len(code)]=code
        install(read8,put,m)
        result=[]
        for section in sections:
            at=section['address']&16383
            raw=bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']: result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected lookup-table modification')
            coded=self.compress(raw)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result,m
