"""Move the hot half-row LDI body into unused fixed bank-2 code space.

The 33-byte body costs a CALL/RET (+27 T per copied half-row) but avoids
bank-5 opcode contention for the sixteen LDIs. The half-row controller is
repacked, so no extra skip JP is executed. Existing maps/streams stay exact.
"""
import numpy as np
import half_row_cache as half


def copy_tstates(pairs):
    values = np.asarray(pairs, dtype=np.uint8).reshape(24, 2)
    return half.copy_tstates(values)+108*int((values.sum(axis=1)==1).sum())


def build(recon, *, cache_page=0xa4):
    regions, labels, rows = half.build(recon, cache_page=cache_page)
    original = next(code for at, code in regions if at==half.HALF)
    start = labels['row']+1
    if original[start-half.HALF:start-half.HALF+32] != b'\xed\xa0'*16:
        raise ValueError('half-row LDI sequence differs')
    helper = recon['cache_copy']+14
    if helper+33>recon['cache_copy_rows']:
        raise ValueError('no room for uncontended half-row body')
    call = b'\xcd'+helper.to_bytes(2, 'little')
    code = bytearray(original[:start-half.HALF]+call+original[start-half.HALF+32:])
    jump = next(r['address'] for r in rows if r['instruction']=='DJNZ row')
    new_jump = jump-29
    displacement = labels['row']-(new_jump+2)
    if not -128<=displacement<=127 or code[new_jump-half.HALF]!=0x10:
        raise ValueError('row loop relocation differs')
    code[new_jump-half.HALF+1] = displacement&255
    listing = []
    for row in rows:
        at = row['address']
        if not half.HALF<=at<labels['half_end'] or start<=at<start+32:
            continue
        listing.append(dict(row, address=at-29 if at>=start+32 else at, phase='uncontended_half_copy'))
    listing.append(dict(address=start, instruction='CALL uncontended half-row body', tstates=17,
                        phase='uncontended_half_copy'))
    listing += [dict(address=helper+2*i, instruction='LDI half-row byte', tstates=16,
                     phase='uncontended_half_copy') for i in range(16)]
    listing.append(dict(address=helper+32, instruction='RET half-row body', tstates=10,
                        phase='uncontended_half_copy'))
    return dict(enabled=True, helper=helper, helper_end=helper+33,
        controller=half.HALF, controller_end=half.HALF+len(code), previous_controller_end=labels['half_end'],
        previous_controller_hex=original.hex(), regions=[
            dict(address=half.HALF, code_hex=(bytes(code)+bytes(29)).hex()),
            dict(address=helper, code_hex=(b'\xed\xa0'*16+b'\xc9').hex())], listing=listing,
        previous_row_body_tstates=256, row_body_tstates=283, row_body_delta_tstates=27,
        partial_group_delta_tstates=108, extra_stack_bytes=2,
        compressed_stream_delta_bytes=0, packet_parser_delta_tstates=0,
        controller_code_bytes=len(code), previous_controller_code_bytes=len(original),
        helper_code_bytes=33, net_executed_code_growth_bytes=4,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        timing_excludes=['IRQ', 'ULA', 'TR-DOS ROM', 'disk latency'])


def apply(read8, put, recon, *, cache_page=0xa4):
    report = build(recon, cache_page=cache_page)
    original = bytes.fromhex(report['previous_controller_hex'])
    if bytes(read8(half.HALF+i) for i in range(len(original)))!=original:
        raise ValueError('expected installed half-row controller')
    if any(read8(i) for i in range(report['helper'], report['helper_end'])):
        raise ValueError('uncontended helper space is occupied')
    for region in report['regions']: put(region['address'], bytes.fromhex(region['code_hex']))
    return report


def install(read8, put, m):
    if not m.get('half_row_cache', {}).get('enabled'):
        raise ValueError('requires installed half-row player')
    report = apply(read8, put, m['cached_huffman_lookahead']['implementation']['labels'])
    m['slot_queue_instruction_listing'] = [r for r in m['slot_queue_instruction_listing']
        if not report['controller']<=r['address']<report['previous_controller_end']]+report['listing']
    m['uncontended_half_copy'] = report
    return report


def install_stage(h):
    """Use after the existing half-row frame-stage installer."""
    c = h.cpu; c.guarding = False
    # The host-fed fixture never executes packet parsing. Match the actual
    # player's retired-selector bytes before checking the new allocation.
    base, end = h.recon['cache_copy'], h.recon['cache_copy_rows']
    tail = b'\xed\xa0'*5+b'\xc9'+bytes(end-base-14)
    for i, value in enumerate(tail): c.write8(base+3+i, value)
    def put(at, code):
        for i, value in enumerate(code): c.write8(at+i, value)
    report = apply(c.read8, put, h.recon)
    for pc in list(h.instructions):
        if report['controller']<=pc<report['previous_controller_end']: del h.instructions[pc]
    for row in report['listing']:
        h.instructions[row['address']] = dict(row, phase='reconstruct', stage='uncontended_half_copy')
    return report
