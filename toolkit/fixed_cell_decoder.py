"""Pin the existing LZSA2 core after retiring the unused legacy renderer.

Build-time relocation only. Public cold entries/state stay fixed; opcode
timings and producer bytes are checked against the previous placement.
"""
from build_fap3_trd import sha
import inplace_slot_input_z80 as producer
import resumable_lzsa2


def install(read,put,m,origin=0x8d74,limit=0x8e80):
    old=m['decoder_labels'];old_layout=m['lzsa2']['layout']
    if old['start']==origin:return
    old_regions=[(r['address'],bytes.fromhex(r['code_hex'])) for r in m['lzsa2']['regions']]
    for at,data in old_regions:
        if bytes(read(at+i) for i in range(len(data)))!=data:raise ValueError('old LZSA2 bytes differ')
    regions,z,layout=resumable_lzsa2.build(core=origin,core_limit=limit)
    for key in ('begin','slice_until','fatal','slice_output','slice_target','slice_caller_sp',
                'slice_decoder_sp','block_length','block_end','block_stored','input_pointer'):
        if z[key]!=old[key]:raise ValueError('relocation moved a public decoder entry/state')
    if [r['tstates'] for r in layout['instruction_listing']]!=[r['tstates'] for r in old_layout['instruction_listing']]:
        raise ValueError('relocation changed instruction timing')
    pregions,p,_=producer.build(z,m['disk_labels'],elapsed_fields=m['player_labels']['elapsed_fields'])
    if p!=m['producer_labels']:raise ValueError('relocation changed producer state')
    for at,data in pregions:
        if bytes(read(at+i) for i in range(len(data)))!=data:raise ValueError('producer needs an unexpected core reference patch')
    # The caller guarantees the CB44/46 renderer replaces the legacy kernel.
    # Clear the entire reclaimed gap so streaming expansion sees real free RAM.
    retired=bytes(read(at) for at in range(0x8000,limit))
    put(0x8000,bytes(limit-0x8000))
    for at,data in old_regions:put(at,bytes(len(data)))
    for at,data in regions:put(at,data)
    m['cell_core_relocation']=dict(old_origin=old['start'],old_end=old_layout['core_end'],
        new_origin=origin,new_end=layout['core_end'],retired_gap_sha256=sha(retired),
        instruction_delta_tstates=0,producer_bytes_unchanged=True,public_entries_unchanged=True,
        instruction_tstates_before=[r['tstates'] for r in old_layout['instruction_listing']],
        instruction_tstates_after=[r['tstates'] for r in layout['instruction_listing']])
    m['decoder_labels']=z;m['decoder_end']=layout['core_end']
    m['lzsa2']['layout']=layout
    m['lzsa2']['regions']=[dict(address=at,code_hex=data.hex(),sha256=sha(data)) for at,data in regions]
