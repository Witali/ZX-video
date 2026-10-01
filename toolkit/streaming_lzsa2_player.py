"""Guarded sector-prefix LZSA2 using the existing demand queue and four slots.

Stream bytes, in-place allocation, AY and physical disk service stay unchanged.
Only explicit decoder EOF publishes a completed slot. This optional installer
precedes the compressed-sector cache, which then wraps the same producer.
"""
from copy import deepcopy

from build_fap3_trd import sha
from inplace_streaming_core import input_prefix
import resumable_lzsa2
import streaming_slot_queue as queue


def install(banks,m,*,direct_header=False):
    if not m.get('four_video_slots',{}).get('enabled') or m['cell_codebook']['wire']!='CB46':
        raise ValueError('streaming LZSA2 requires four-slot CB46')
    if m.get('compressed_sector_cache') or m.get('streaming_input'):
        raise ValueError('install streaming LZSA2 before sector cache, once')
    def bank(at):return 5 if at<0x8000 else 2 if at<0xc000 else 7
    def read(at):return banks[bank(at)][at&16383]
    def put(at,data):
        if (at&16383)+len(data)>16384:raise ValueError('cross-bank streaming patch')
        banks[bank(at)][at&16383:(at&16383)+len(data)]=data
    oldz,oldq,oldp=[deepcopy(m[k]) for k in ('decoder_labels','queue_labels','producer_labels')]
    oldlayout=m['lzsa2']['layout']
    zregions,z,layout=resumable_lzsa2.build(core=oldz['start'],
        core_limit=m['cell_codebook']['memory']['fixed_kernel'][0],streaming=True,direct_header=direct_header)
    pregions,p,prows=input_prefix(z,m['disk_labels'],elapsed_fields=m['player_labels']['elapsed_fields'],
        origin=layout['prefix_end'],patch_guards=True)
    qregions,q,qrows=queue.build(z,p,len(m['blocks']),demand_decode=True,defer_while_buffered=True)
    if q['step']!=oldq['step'] or q['prefill']!=oldq['prefill'] or p['end']!=oldp['end']:
        raise ValueError('public entry or producer state moved')
    if any(read(at) for at in range(oldlayout['prefix_end'],p['prefix_end'])):
        raise ValueError('streaming prefix expansion is occupied')
    if any(read(at) for at in range(oldlayout['core_end'],layout['core_end'])):
        raise ValueError('streaming core expansion is occupied')
    # Newly generated producer still has the three-slot admission constant.
    pregions=[(at,b'\xfe\x04'+data[2:] if at==p['begin'] else data) for at,data in pregions]
    next(r for r in prows if r['address']==p['begin'])['instruction']='CP 4'
    blobs={at:bytearray(data) for at,data in qregions};patches=[]
    def patch(at,before,after,reason,t=10):
        owner=next(base for base,data in blobs.items() if base<=at<base+len(data));offset=at-owner
        assert bytes(blobs[owner][offset:offset+len(before)])==before and len(before)==len(after)
        blobs[owner][offset:offset+len(before)]=after
        patches.append(dict(address=at,before_hex=before.hex(),code_hex=after.hex(),reason=reason,tstates=t))
    hooks=m['resident_audio']['hooks']
    patch(q['step'],b'\x3a'+q['phase'].to_bytes(2,'little'),
        b'\xcd'+hooks['queue_service'].to_bytes(2,'little'),'retain AY and drive service',17)
    for row in qrows:
        if row['address']==q['step']:
            row.update(instruction='CALL audio and drive service',tstates=17)
        replacement={'LD HL,E000':(0x21,0xe000,0xc000),'LD DE,E000':(0x11,0xe000,0xc000),
            'LD DE,2000':(0x11,0x2000,0x4000),'LD BC,2000':(0x01,0x2000,0x4000)}.get(row['instruction'])
        if replacement:
            op,before,after=replacement
            patch(row['address'],bytes([op])+before.to_bytes(2,'little'),
                bytes([op])+after.to_bytes(2,'little'),'in-place C000h output')
            row['instruction']=row['instruction'].replace('E000','C000').replace('2000','4000')
    qregions=[(at,bytes(data)) for at,data in blobs.items()]
    regions=zregions+pregions+qregions
    spans=[(at,at+len(data)) for at,data in regions]
    remap={oldz[k]:z[k] for k in ('fatal','begin','slice_until','slice_output','slice_target',
        'slice_caller_sp','slice_decoder_sp','block_length','block_end','block_stored','input_pointer')}
    remap.update({oldq[k]:q[k] for k in oldq if isinstance(oldq[k],int) and k in q})
    external=[];retained=[]
    for pc,row in sorted({r['address']:r for r in m['slot_queue_instruction_listing']}.items()):
        if any(lo<=pc<hi for lo,hi in spans) or row.get('phase')=='cold_init':continue
        op,name,offset=read(pc),row['instruction'],None
        if name.startswith('LD '):
            if op in (1,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a):offset=1
            if op in (0xdd,0xfd) and read(pc+1) in (0x21,0x22,0x2a):offset=2
            if op==0xed and read(pc+1) in (0x43,0x4b,0x53,0x5b,0x73,0x7b):offset=2
        if name.startswith(('CALL ','JP ')) and op in (0xc3,0xc2,0xca,0xd2,0xda,0xcd,0xc4,0xcc,0xd4,0xdc):offset=1
        if offset is not None:
            old=read(pc+offset)+256*read(pc+offset+1);new=remap.get(old,old)
            if new!=old:
                put(pc+offset,new.to_bytes(2,'little'))
                external.append(dict(address=pc,operand_address=pc+offset,old=old,new=new,
                    tstates=row['tstates'],delta_tstates=0))
        retained.append(row)
    if (sum(r['old']==oldq['take'] for r in external)!=4
            or not any(r['address']==hooks['queue_service']+3 and r['new']==q['phase'] for r in external)):
        raise ValueError(('packet or AY queue reference was not remapped',external))
    for at,data in regions:put(at,data)
    put(0xa200,bytes(read(at) for at in range(0x6100,0x6200)))
    listing=layout['instruction_listing']+prows+qrows
    m['slot_queue_instruction_listing']=retained+listing
    m['decoder_labels']=z;m['producer_labels']=p;m['queue_labels']=q
    m['decoder_end']=layout['core_end'];m['player_labels']['zx0_fatal']=z['fatal']
    m['lzsa2']['previous_layout']=deepcopy(oldlayout)
    m['lzsa2'].update(layout=layout,regions=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in zregions],
        decoder_bytes=layout['code_bytes'],streaming=True)
    m['inplace_video'].update(producer_listing=prows,regions=[dict(address=at,code_hex=data.hex()) for at,data in pregions],
        shared_tail_saved_before_decode=False,shared_tail_saved_before_eof=True)
    m['demand_decode']=dict(helper_start=queue.DEMAND,helper_end=q['demand_end'],
        queue_bytes=q['end']-queue.CODE,helper_bytes=q['demand_end']-queue.DEMAND,background_quantum=256,extra_stream_bytes=0)
    m['streaming_input']=dict(enabled=True,codec='lzsa2',input_wait_phase=3,completion_flag=z['finished'],
        previous_queue_labels=oldq,external_operands=external,queue_adjustments=patches,listing=listing,
        regions=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in regions],
        decoder_bytes_before=oldlayout['code_bytes'],decoder_bytes_after=layout['code_bytes'],
        prefix_end=p['prefix_end'],extra_stream_bytes=0,extra_output_copies=0,
        maximum_sectors_per_input_step=1,header_guard_bytes=32,entire_literal_run_guarded=True,
        defer_prefix_while_completed_slots_available=True,
        **(dict(direct_header_guard=True) if direct_header else {}),
        scope='Instruction listings count deterministic CPU only; full physical timing requires Fuse')
