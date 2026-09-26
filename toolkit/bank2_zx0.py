"""Move the ZX0 hot core into retired fixed Huffman-patch RAM, opcodes unchanged.

The 35-byte resumable entry remains in bank 5. All 279 remaining bytes,
including mutable state, move to bank 2. The old IRQ-safe private stack is
retained. This requires inline sparse patches in bank 6; default mode stays
unchanged when that dependency is unavailable.
"""
import bank_local_zx0 as local
from build_fap3_trd import sha

ORIGIN,LIMIT=0x8df2,0x8f09


def build():
    a=local.assemble(dynamic_input=True,inline_literals=True)
    old=a.resolve();start,end=a.labels['slice_begin'],a.labels['end']
    split=start-local.CODE
    if split!=35 or end-start!=LIMIT-ORIGIN:raise ValueError('ZX0 or retired region size changed')
    def moved(address):return address+ORIGIN-start if start<=address<=end else address
    blob=bytearray(old);absolute=[];relative=[]
    for pos,label in a.abs_fixups:
        before=a.labels[label];after=moved(before)
        if before!=after:
            blob[pos:pos+2]=after.to_bytes(2,'little')
            absolute.append(dict(operand=moved(local.CODE+pos),label=label,old=before,new=after))
    for pos,label in a.rel_fixups:
        after=moved(a.labels[label])-moved(local.CODE+pos+1)
        before=int.from_bytes(old[pos:pos+1],'little',signed=True)
        if after!=before:raise ValueError('relative branch crosses split')
        relative.append(dict(operand=moved(local.CODE+pos),target=moved(a.labels[label]),displacement=after))
    regions=[(local.CODE,bytes(blob[:split])),(ORIGIN,bytes(blob[split:]))]
    labels={key:moved(value) for key,value in a.labels.items()}
    return regions,labels,dict(enabled=True,old_origin=start,old_end=end,new_origin=ORIGIN,new_end=LIMIT,
        prefix_bytes=split,core_and_state_bytes=len(blob)-split,code_bytes=len(blob),
        old_code_sha256=sha(old),code_sha256=sha(blob),absolute_operands=absolute,relative_branches=relative,
        regions=[dict(address=address,code_hex=data.hex(),bytes=len(data),sha256=sha(data)) for address,data in regions],
        instruction_tstate_delta=0,extra_stream_bytes=0,extra_ram_bytes=0,private_stack_unchanged=True)


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
    regions,labels,report=build();hp=m['inline_huffman_patches']
    if hp['redirect_address']+3!=ORIGIN or h.frame.recon['attributes']!=LIMIT:
        raise ValueError('retired patch-body bounds differ')
    if bytes(read8(hp['redirect_address']+i) for i in range(3))!=bytes.fromhex(hp['redirect_bytes']) or read8(LIMIT)!=0xc9:
        raise ValueError('inline redirect or retained empty-mask RET differs')
    import bulk_frame_z80 as packet
    _,_,_,packet_rows=packet.build(m['decoder_labels'],m['queue_labels'],h.frame.w,h.frame.draw,
        m['compiled_masks']['labels'],h.audio,stored_guards=False,separate_prepare='idle',page_entry=0x9780)
    rows={r['address']:r for r in m['slot_queue_instruction_listing']+packet_rows}
    # Fixed frame instructions cover all retained branches into the old body.
    rows.update({pc:r for pc,r in h.frame.instructions.items() if pc<0xc000})
    changes=[];entry_checks=0
    for pc,row in sorted(rows.items()):
        if ORIGIN<=pc<LIMIT or row.get('phase')=='cold_init':continue
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
            if ORIGIN<=before<LIMIT:raise ValueError(('live branch enters retired body',hex(pc),hex(before)))
        if report['old_origin']<=before<report['old_end']:
            if before not in m['decoder_labels'].values():raise ValueError(('unrecognized ZX0 reference',hex(pc),hex(before)))
            after=ORIGIN+before-report['old_origin']
            put(pc+offset,after.to_bytes(2,'little'))
            changes.append(dict(address=pc,operand_address=pc+offset,instruction=name,old_operand=before,new_operand=after,
                baseline_tstates=row['tstates'],tstates=row['tstates'],delta_tstates=0))
    for address,data in regions:put(address,data)
    put(report['old_origin'],bytes(report['old_end']-report['old_origin']))
    report.update(external_operands=changes,external_branch_checks=entry_checks)
    m['decoder_labels']=labels;m['player_labels']['zx0_fatal']=labels['fatal']
    return report
