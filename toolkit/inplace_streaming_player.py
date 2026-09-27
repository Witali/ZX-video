"""Optional sector-streaming integration after resident AY and drive maintenance.

Reuse identical 15872-byte ZX0 blocks and the three in-place slots. The
previous builders stay unchanged, so their archived code remains reproducible.
"""
from copy import deepcopy

from build_fap3_trd import sha, padded, sectors
from inplace_keepalive_player import Builder as PreviousBuilder
import inplace_streaming_core as core
import streaming_slot_queue as queue


def install(read8,put,m):
    if (not m['inplace_keepalive']['enabled'] or not m['resident_audio']['foreground_audio']
            or not m['hl_mask_reader']['enabled'] or m.get('streaming_input')):
        raise ValueError('requires the complete-input in-place keepalive player')
    oldz,oldq,oldp=[deepcopy(m[k]) for k in ('decoder_labels','queue_labels','producer_labels')]
    zregions,z,layout=core.decoder()
    pregions,p,prows=core.input_prefix(z,m['disk_labels'],elapsed_fields=m['player_labels']['elapsed_fields'],
        origin=layout['helper_end'])
    qregions,q,qrows=queue.build(z,p,len(m['blocks']),demand_decode=True)
    if (q['step']!=oldq['step'] or q['prefill']!=oldq['prefill'] or
            p['last_read_field']!=oldp['last_read_field'] or p['end']!=oldp['end']):
        raise ValueError('retained public entries or drive-maintenance state moved')
    if any(read8(at) for at in range(core.streaming.HELPERS,p['prefix_end'])):
        raise ValueError('streaming helper space is not free')
    blobs={at:bytearray(data) for at,data in qregions};changed=[];removed=set();added=[]
    def patch(at,before,after,ticks,new_ticks,reason):
        owner=next(base for base,data in blobs.items() if base<=at<base+len(data))
        buf=blobs[owner];offset=at-owner
        if bytes(buf[offset:offset+len(before)])!=before or len(before)!=len(after):
            raise ValueError(('unexpected queue patch',hex(at),reason))
        buf[offset:offset+len(before)]=after
        changed.append(dict(address=at,previous_hex=before.hex(),code_hex=after.hex(),
            previous_tstates=ticks,tstates=new_ticks,reason=reason))
    # Same resident audio/drive hooks and three-slot rotation as the baseline.
    hooks=m['resident_audio']['hooks']
    patch(q['step'],b'\x3a'+q['phase'].to_bytes(2,'little'),b'\xcd'+hooks['queue_service'].to_bytes(2,'little'),
        13,17,'retain audio and drive service')
    added.append(dict(address=q['step'],instruction='CALL audio and drive service',tstates=17,phase='slot_queue'))
    removed.add(q['step'])
    for row in qrows:
        at=row['address'];name=row['instruction']
        if name=='CP 4':patch(at,b'\xfe\x04',b'\xfe\x03',7,7,'three video slots');row['instruction']='CP 3'
        replacement={'LD HL,E000':(0x21,0xe000,0xc000),'LD DE,E000':(0x11,0xe000,0xc000),
            'LD DE,2000':(0x11,0x2000,0x4000),'LD BC,2000':(0x01,0x2000,0x4000)}.get(name)
        if replacement:
            op,before,after=replacement
            patch(at,bytes([op])+before.to_bytes(2,'little'),bytes([op])+after.to_bytes(2,'little'),10,10,'in-place output origin')
            row['instruction']=name.replace('E000','C000').replace('2000','4000')
    for lo,hi in ((q['block_ready'],q['worked']),(q['release'],q['retained'])):
        sites=[r['address'] for r in qrows if lo<=r['address']<hi and r['instruction']=='INC A']
        if len(sites)!=1:raise ValueError('slot advance layout changed')
        at=sites[0]
        patch(at,b'\x3c\xe6\x03',b'\xcd'+hooks['advance_slot'].to_bytes(2,'little'),11,17,
            'existing helper adds 22/30 T; total cursor advance 39/47 T')
        removed.update((at,at+1))
        added.append(dict(address=at,instruction='CALL advance three-slot cursor',tstates=17,phase='slot_queue'))
    if len(changed)!=10:raise ValueError(('unexpected queue patch count',len(changed)))
    qregions=[(at,bytes(data)) for at,data in blobs.items()]
    qrows=[r for r in qrows if r['address'] not in removed]+added
    regions=zregions+pregions+qregions
    spans=[(at,at+len(data)) for at,data in regions]
    spans.append((core.streaming.ORIGIN,core.streaming.LIMIT))
    remap={oldz[k]:z[k] for k in ('fatal','slice_output','slice_target','slice_caller_sp',
        'slice_decoder_sp','block_length','block_end','block_stored','input_pointer')}
    remap.update({oldq[k]:q[k] for k in oldq if isinstance(oldq[k],int) and k in q})
    external=[];retained=[]
    # Only known instruction operands can be references. Never scan data bytes.
    rows={r['address']:r for r in m['slot_queue_instruction_listing']}
    for pc,row in sorted(rows.items()):
        if any(lo<=pc<hi for lo,hi in spans) or row.get('phase')=='cold_init':continue
        op=read8(pc);name=row['instruction'];offset=None
        if name.startswith('LD ') and op in (0x01,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a):offset=1
        if name.startswith('LD ') and op in (0xdd,0xfd) and read8(pc+1) in (0x21,0x22,0x2a):offset=2
        if name.startswith('LD ') and op==0xed and read8(pc+1) in (0x43,0x4b,0x53,0x5b,0x73,0x7b):offset=2
        if name.startswith(('CALL ','JP ')) and op in (0xc3,0xc2,0xca,0xd2,0xda,0xcd,0xc4,0xcc,0xd4,0xdc):offset=1
        if offset is not None:
            old=read8(pc+offset)+256*read8(pc+offset+1);new=remap.get(old,old)
            if old!=new:
                put(pc+offset,new.to_bytes(2,'little'))
                external.append(dict(address=pc,operand_address=pc+offset,instruction=name,old=old,new=new,
                    previous_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
        retained.append(row)
    if (sum(r['old']==oldq['take'] for r in external)!=2
            or not any(r['address']==hooks['queue_service']+3 and r['new']==q['phase'] for r in external)):
        raise ValueError('packet consumer or AY queue-service reference was not remapped')
    put(core.streaming.ORIGIN,bytes(core.streaming.LIMIT-core.streaming.ORIGIN))
    for at,data in regions:put(at,data)
    # Bootstrap restores this low bridge from the cold overlay after decoding.
    put(0xa200,bytes(read8(i) for i in range(0x6100,0x6200)))
    report=dict(enabled=True,layout=layout,external_operands=external,queue_adjustments=changed,
        regions=[dict(address=at,bytes=len(data),code_hex=data.hex(),sha256=sha(data)) for at,data in regions],
        decoder_labels=z,producer_labels=p,queue_labels=q,input_wait_phase=3,completion_flag=z['finished'],
        read_step_max_sectors=1,extra_stream_bytes=0,extra_output_copies=0,
        previous_decoder_bytes=m['bank2_zx0']['code_bytes'],decoder_bytes=layout['code_bytes'],
        prefix_wrapper_bytes=p['prefix_end']-layout['helper_end'],previous_queue_labels=oldq,
        source_module='inplace_streaming_player.py')
    m['pre_streaming_bank2_zx0']=m['bank2_zx0'];m['bank2_zx0']=dict(layout,kind='inplace-streaming-inline')
    m['pre_streaming_inplace_video']=deepcopy(m['inplace_video'])
    m['inplace_video'].update(shared_tail_saved_before_decode=False,shared_tail_saved_before_eof=True,
        producer_bytes=sum(len(b) for _,b in pregions),producer_listing=prows,
        regions=[dict(address=at,code_hex=data.hex()) for at,data in pregions],patches=[],
        decoder_and_queue_instruction_delta_tstates=None,producer_timing_requires_execution=True)
    m.update(decoder_labels=z,producer_labels=p,queue_labels=q,streaming_input=report,
        slot_queue_instruction_listing=retained+prows+qrows,decoder_end=z['end'],
        inline_literals=dict(enabled=True,zx0_only=True,literal_input_guard_delta_tstates=33,
            compressed_stream_delta_bytes=0,source_module='streaming_inline_zx0.py'),
        demand_decode=dict(helper_start=queue.DEMAND,helper_end=q['demand_end'],queue_bytes=q['end']-queue.CODE,
            helper_bytes=q['demand_end']-queue.DEMAND,extra_stream_bytes=0,background_quantum=256))
    m['player_labels']['zx0_fatal']=z['fatal']


class Builder(PreviousBuilder):
    def ram(self,start,end,next_sector,remaining):
        sections,m=super().ram(start,end,next_sector,remaining);banks=self.expected_banks
        def bank_at(at):return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at):return banks[bank_at(at)][at&16383]
        def put(at,data):
            if (at&16383)+len(data)>16384:raise ValueError('cross-bank streaming patch')
            banks[bank_at(at)][at&16383:(at&16383)+len(data)]=data
        install(read8,put,m);result=[]
        for section in sections:
            at=section['address']&16383;raw=bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw)==section['sha256']:result.append(section);continue
            if section.get('startup_delta'):raise ValueError('unexpected table modification')
            coded=self.compress(raw)
            result.append(dict(section,data=padded(coded),compressed_bytes=len(coded),sectors=sectors(coded),sha256=sha(raw)))
        return result,m
