"""Install the input-suspending queue after the verified base player patches."""
from copy import deepcopy
from build_fap3_trd import sha
import bulk_frame_z80 as packet
import streaming_slot_input as producer
import streaming_slot_queue as queue
import streaming_zx0_layout as decoder


def install(read8,put,m,h):
    if (not m.get('bank2_zx0',{}).get('enabled') or
        not m.get('inline_huffman_patches',{}).get('enabled') or
        m.get('packet_prefix_guard',{}).get('enabled') or m.get('ready_packet_guard',{}).get('enabled')):
        raise ValueError('streaming input requires the bank-2/inline-Huffman base without packet guards')
    oldz,oldq=deepcopy(m['decoder_labels']),deepcopy(m['queue_labels'])
    zregions,z,layout=decoder.build()
    pregions,p,prows=producer.build(z,m['disk_labels'],layout['helper_end'])
    qregions,q,qrows=queue.build(z,p,len(m['blocks']),demand_decode=True)
    if q['step']!=oldq['step'] or q['prefill']!=oldq['prefill']:
        raise ValueError('retained clock/AY/mask-init entry addresses changed')
    if (m['inline_huffman_patches']['redirect_address']+3!=decoder.ORIGIN or
        h.frame.recon['attributes']!=decoder.LIMIT or read8(decoder.LIMIT)!=0xc9):
        raise ValueError('retired bank-2 body boundaries changed')
    if any(read8(i) for i in range(decoder.HELPERS,p['prefix_end'])):
        raise ValueError('streaming helper RAM is not free')
    if q['end']>0xe180 or q['demand_end']>0xe300 or p['prefix_end']>0x7d50:
        raise ValueError('streaming queue/producer exceeds its reservation')
    # Rebuild source instruction addresses, then patch only retained references
    # to queue entries or decoder data/fatal. New queue/producer/bridge regions
    # already contain their own final operands. Do not scan operand bytes.
    _,_,_,packet_rows=packet.build(oldz,oldq,h.frame.w,h.frame.draw,m['compiled_masks']['labels'],h.audio,
        stored_guards=False,separate_prepare='idle',page_entry=0x9780)
    rows={r['address']:r for r in m['slot_queue_instruction_listing']+packet_rows}
    rows.update({pc:r for pc,r in h.frame.instructions.items() if pc<0xc000})
    remap={oldz[name]:z[name] for name in ('fatal','slice_output','slice_target',
        'slice_caller_sp','slice_decoder_sp','block_length','block_end','block_stored','input_pointer')}
    remap.update({oldq[name]:q[name] for name in ('take','step','prefill')})
    regions=zregions+pregions+qregions
    spans=[(at,at+len(data)) for at,data in regions]
    spans.append((decoder.ORIGIN,decoder.LIMIT))
    patches=[]
    for pc,row in sorted(rows.items()):
        if any(lo<=pc<hi for lo,hi in spans) or row.get('phase')=='cold_init':continue
        op=read8(pc);name=row['instruction'];offset=None
        if name.startswith('LD ') and op in (0x01,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a):offset=1
        if name.startswith('LD ') and op in (0xdd,0xfd) and read8(pc+1) in (0x21,0x22,0x2a):offset=2
        if name.startswith('LD ') and op==0xed and read8(pc+1) in (0x43,0x4b,0x53,0x5b,0x73,0x7b):offset=2
        if name.startswith(('CALL ','JP ')) and op in (0xc3,0xc2,0xca,0xd2,0xda,0xcd,0xc4,0xcc,0xd4,0xdc):offset=1
        if offset is None:continue
        old=read8(pc+offset)+256*read8(pc+offset+1);new=remap.get(old,old)
        if old==new:continue
        put(pc+offset,new.to_bytes(2,'little'))
        patches.append(dict(address=pc,operand_address=pc+offset,instruction=name,old=old,new=new,
            baseline_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
    if sum(p['old']==oldq['take'] for p in patches)!=2:raise ValueError('packet take references not found')
    put(decoder.ORIGIN,bytes(decoder.LIMIT-decoder.ORIGIN))
    for at,data in regions:put(at,data)
    report=dict(enabled=True,layout=layout,external_operands=patches,
        regions=[dict(address=at,bytes=len(data),code_hex=data.hex(),sha256=sha(data)) for at,data in regions],
        queue_labels=q,producer_labels=p,decoder_labels=z,input_wait_phase=3,completion_flag=z['finished'],
        read_step_max_sectors=1,extra_stream_bytes=0,extra_output_copies=0,
        prefix_wrapper_bytes=p['prefix_end']-layout['helper_end'])
    m['pre_streaming_bank2_zx0']=m['bank2_zx0']
    m['bank2_zx0']=dict(layout,kind='streaming-inline',enabled=True)
    m.update(decoder_labels=z,queue_labels=q,producer_labels=p,
        slot_queue_instruction_listing=[r for r in m['slot_queue_instruction_listing']
            if r.get('phase') not in ('slot_queue','slot_bridge','direct_slot_input')]+prows+qrows,
        inline_literals=dict(enabled=True,zx0_only=True,literal_input_guard_delta_tstates=33,
            compressed_stream_delta_bytes=0,source_module='streaming_inline_zx0.py'),
        demand_decode=dict(helper_start=queue.DEMAND,helper_end=q['demand_end'],queue_bytes=q['end']-queue.CODE,
            helper_bytes=q['demand_end']-queue.DEMAND,extra_stream_bytes=0,background_quantum=256))
    m['player_labels']['zx0_fatal']=z['fatal']
    return report
