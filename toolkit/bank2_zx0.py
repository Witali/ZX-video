"""Compatibility import for the reusable ZX0 library."""
import codec_libraries  # Locate source packages in repository checkouts.
from zx0.split_bank2 import *

def install_decoder(h):
    """Standalone CPU harness: retain its guards, change all mutable labels."""
    regions,labels,report=build();c=h.cpu;c.guarding=False
    h.code=b''.join(data for _,data in regions);h.labels=labels;c.labels=labels
    c.patched={labels[n] for n in ('slice_high_operand','slice_low_operand','slice_equal_branch',
                                 'match_high_operand','match_low_operand','match_equal_branch')}
    c.patched.update((labels['dzx0t_last_offset']+1,labels['dzx0t_last_offset']+2))
    for i in range(report['old_origin'],report['old_end']):c.write8(i,0x76)
    for address,data in regions:
        for i,value in enumerate(data):c.write8(address+i,value)
    return report


def install_player(read8,put,m,h):
    """Patch actual assembled references only, after the inline redirect exists."""
    if not m['inline_huffman_patches'].get('enabled'):
        return dict(enabled=False,reason='inline Huffman unavailable')
    hp=m['inline_huffman_patches']
    origin,limit=hp['redirect_address']+3,h.frame.recon['attributes']
    regions,labels,report=build(origin=origin,limit=limit)
    if bytes(read8(hp['redirect_address']+i) for i in range(3))!=bytes.fromhex(hp['redirect_bytes']) or read8(limit)!=0xc9:
        raise ValueError('inline redirect or retained empty-mask RET differs')
    import bulk_frame_z80 as packet
    _,_,_,packet_rows=packet.build(m['decoder_labels'],m['queue_labels'],h.frame.w,h.frame.draw,
        m['compiled_masks']['labels'],h.audio,stored_guards=False,separate_prepare='idle',page_entry=0x9780)
    rows={r['address']:r for r in m['slot_queue_instruction_listing']+packet_rows}
    # Fixed frame instructions cover all retained branches into the old body.
    rows.update({pc:r for pc,r in h.frame.instructions.items() if pc<0xc000})
    changes=[];entry_checks=0
    for pc,row in sorted(rows.items()):
        if origin<=pc<limit or row.get('phase')=='cold_init':continue
        opcode=read8(pc);name=row['instruction'];offset=None
        if name.startswith('LD ') and opcode in (0x01,0x11,0x21,0x31,0x22,0x2a,0x32,0x3a):offset=1
        if name.startswith('LD ') and opcode in (0xdd,0xfd) and read8(pc+1) in (0x21,0x22,0x2a):offset=2
        if name.startswith('LD ') and opcode==0xed and read8(pc+1) in (0x43,0x4b,0x53,0x5b,0x63,0x6b,0x73,0x7b):offset=2
        branch=opcode in (0xc3,0xc2,0xca,0xd2,0xda,0xe2,0xea,0xf2,0xfa,0xcd,0xc4,0xcc,0xd4,0xdc,0xe4,0xec,0xf4,0xfc)
        if branch and name.startswith(('CALL ','JP ')):offset=1
        if offset is None:continue
        before=read8(pc+offset)+256*read8(pc+offset+1)
        if branch:
            entry_checks+=1
            if origin<=before<limit:raise ValueError(('live branch enters retired body',hex(pc),hex(before)))
        if report['old_origin']<=before<report['old_end']:
            if before not in m['decoder_labels'].values():raise ValueError(('unrecognized ZX0 reference',hex(pc),hex(before)))
            after=origin+before-report['old_origin']
            put(pc+offset,after.to_bytes(2,'little'))
            changes.append(dict(address=pc,operand_address=pc+offset,instruction=name,old_operand=before,new_operand=after,
                baseline_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
    for address,data in regions:put(address,data)
    put(report['old_origin'],bytes(report['old_end']-report['old_origin']))
    report.update(external_operands=changes,external_branch_checks=entry_checks)
    m['decoder_labels']=labels;m['player_labels']['zx0_fatal']=labels['fatal']
    return report
