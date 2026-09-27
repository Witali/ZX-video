"""CPU prototype: load a motion target directly into alternate HL.

Install after the two-byte Huffman cache, before inlining/compact cursors.
Relayout the fixed reconstruction tail by three bytes and relocate all
listed references. This deliberately does not patch an existing TRD:
bank-2 ZX0 placement and bootstrap compression need separate integration.
"""
from build_fap3_trd import sha


def build(read8, instructions, labels):
    rows = {r['address']: r for r in instructions}
    target, end = labels['target'], labels['end']
    candidates = [pc for pc, r in rows.items()
                  if labels['motion'] <= pc < labels['predict_0']
                  and r['instruction'] == 'LD HL,(target)']
    if len(candidates) != 1 or 'lookahead_refresh' not in labels:
        raise ValueError('requires unrolled motion and two-byte Huffman cache')
    start = candidates[0]
    operand = target.to_bytes(2, 'little')
    if bytes(read8(start+i) for i in range(3)) != b'\x2a'+operand:
        raise ValueError('unexpected common target load')
    # Phases 2/6 no longer return the old target in primary HL. Every
    # existing caller immediately invokes patches, which reloads HL.
    reload = b'\x2a'+labels['bitmap_masks'].to_bytes(2, 'little')
    if bytes(read8(labels['patches']+i) for i in range(3)) != reload:
        raise ValueError('patch entry must overwrite primary HL')
    callers = [pc for pc, r in rows.items() if r['instruction'] in ('CALL motion','CALL NZ,motion')]
    following = b'\xcd'+labels['patches'].to_bytes(2, 'little')
    if not callers or any(bytes(read8(pc+3+i) for i in range(3)) != following for pc in callers):
        raise ValueError('unverified live primary-HL motion caller')
    edits = {start: (3, [])}
    edits[labels['predict_0']] = (0, [('LD HL,(target)', b'\x2a'+operand, 16)])
    for phase in (2, 4, 6):
        pc = labels[f'predict_{phase}']
        if bytes(read8(pc+i) for i in range(4)) != b'\xe5\xd9\xe1\xd9':
            raise ValueError(('unexpected alternate-HL setup', phase))
        edits[pc] = (4, [('EXX (direct target)', b'\xd9', 4),
                        ('LD HL,(target)', b'\x2a'+operand, 16),
                        ('EXX', b'\xd9', 4)])
    if end+3 > labels['lookahead_refresh'] or any(read8(pc) for pc in range(end, end+3)):
        raise ValueError('three free bytes required before lookahead helper')

    def moved(pc):
        if not start <= pc <= end:
            return pc
        # A label at an insertion addresses the inserted instruction.
        return pc + sum(sum(len(b) for _, b, _ in body)-length
                        for at, (length, body) in edits.items() if at < pc)

    new_labels = {name: moved(pc) for name, pc in labels.items()}
    new_target = new_labels['target']
    code = bytearray()
    new_rows, removed, inserted = [], set(), []
    cursor = start
    for at, (length, body) in sorted(edits.items()):
        code.extend(read8(pc) for pc in range(cursor, at))
        for name, blob, ticks in body:
            row = dict(rows[at], address=start+len(code), instruction=name, tstates=ticks)
            if name == 'LD HL,(target)': blob = b'\x2a'+new_target.to_bytes(2, 'little')
            new_rows.append(row)
            inserted.append(dict(row, code_hex=blob.hex()))
            code.extend(blob)
        removed.update(pc for pc in rows if at <= pc < at+length)
        cursor = at+length
    code.extend(read8(pc) for pc in range(cursor, end))
    if len(code) != end-start+3:
        raise AssertionError('unexpected motion layout growth')
    new_rows.extend(dict(r, address=moved(pc)+(3 if pc == labels['predict_0'] else 0))
                    for pc, r in rows.items() if pc not in removed)
    if len({r['address'] for r in new_rows}) != len(new_rows):
        raise AssertionError('instruction overlap after motion relayout')
    external, fixups = {}, []

    def put(pc, blob):
        for i, value in enumerate(blob):
            if start <= pc+i < end+3: code[pc+i-start] = value
            else: external[pc+i] = value

    absolute = {0xc3, 0xc2, 0xca, 0xd2, 0xda, 0xe2, 0xea, 0xf2, 0xfa,
                0xcd, 0xc4, 0xcc, 0xd4, 0xdc, 0xe4, 0xec, 0xf4, 0xfc}
    for pc, row in sorted(rows.items()):
        if pc in removed or pc >= 0xc000: continue
        after_pc = moved(pc)+(3 if pc == labels['predict_0'] else 0)
        op, name, offset = read8(pc), row['instruction'], None
        if name.startswith('LD '):
            if op in (0x01, 0x11, 0x21, 0x31, 0x22, 0x2a, 0x32, 0x3a): offset = 1
            if op in (0xdd, 0xfd) and read8(pc+1) in (0x21, 0x22, 0x2a): offset = 2
            if op == 0xed and read8(pc+1) in (0x43, 0x4b, 0x53, 0x5b, 0x63, 0x6b, 0x73, 0x7b): offset = 2
        if op in absolute and name.startswith(('JP ', 'CALL ')): offset = 1
        if offset is not None:
            before = read8(pc+offset)+256*read8(pc+offset+1)
            after = moved(before)
            if after != before:
                put(after_pc+offset, after.to_bytes(2, 'little'))
                fixups.append(dict(address=after_pc, instruction=name, before=before, after=after))
        if op in (0x10, 0x18, 0x20, 0x28, 0x30, 0x38) and name.startswith(('JR ', 'DJNZ ')):
            displacement = int.from_bytes(bytes([read8(pc+1)]), 'little', signed=True)
            before = pc+2+displacement
            after = moved(before)
            new_displacement = after-after_pc-2
            if not -128 <= new_displacement <= 127: raise ValueError('relative branch overflow')
            if new_displacement != displacement:
                put(after_pc+1, bytes([new_displacement & 255]))
                fixups.append(dict(address=after_pc, instruction=name, before=before, after=after))
    return dict(start=start, old_end=end, end=end+3, code_hex=code.hex(),
        code_sha256=sha(code), external_bytes=sorted(external.items()), labels=new_labels,
        listing=sorted(new_rows, key=lambda r:r['address']), inserted=inserted, fixups=fixups,
        baseline_target=target, target=new_target, code_growth_bytes=3,
        baseline_setup_tstates=45, setup_tstates=24, nonzero_delta_tstates=-21,
        phase_zero_delta_tstates=0, clear_tile_delta_tstates=0,
        temporary_stack_bytes_before=2, temporary_stack_bytes=0,
        primary_hl_dead_after_phases=[2,6], verified_motion_callers=callers,
        compressed_stream_delta_bytes=0, new_trds_built=False,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


def install_stage(h):
    """Install on a fresh frame fixture, before bank-aware inline listings."""
    c = h.cpu
    c.guarding = False
    old_labels = h.recon
    result = build(c.read8, h.instructions.values(), old_labels)
    for i, value in enumerate(bytes.fromhex(result['code_hex'])): c.write8(result['start']+i, value)
    for pc, value in result['external_bytes']: c.write8(pc, value)
    c.state_regions = [(result['labels']['state'], result['labels']['end'])
                       if (lo, hi) == (old_labels['state'], old_labels['end']) else (lo, hi)
                       for lo, hi in c.state_regions]
    h.recon = result['labels']
    h.instructions = {r['address']: r for r in result['listing']}
    return result
