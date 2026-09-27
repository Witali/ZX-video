"""Experimental two-byte Huffman input cache, retaining existing code addresses.

B keeps (IX), E keeps (IX+1). The short path holds its result in AF' while
advancing the input. Long codes and frame/chunk setup refresh both bytes.
Motion phases 2/4/6 use alternate HL instead of alternate DE, at identical
T-states, so E survives between Huffman calls. IRQ must preserve AF' and
both register sets. Two readable lookahead bytes are required, including
for an empty input; values are arbitrary. The current release packet ABI
only promises one. This module does not change that ABI or build a release.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha

HELPER = 0x8fc0
LIMIT = 0x9000


def build(read8, instructions, labels, *, frame=False):
    rows = {r['address']: r for r in instructions}
    start, end = labels['bitmap'], labels['long']
    if 'cache_short_refresh' not in labels or 'cache_long_refresh' not in labels:
        raise ValueError('requires cached carry-Huffman')
    if labels['end'] > HELPER:
        raise ValueError('no fixed RAM for lookahead helpers')
    if frame and ('literal_source' not in labels or 'raw_intra' in labels
                  or not all(f'predict_{p}' in labels for p in (0, 2, 4, 6))):
        raise ValueError('requires split literals and unrolled motion without raw intra')
    a, listing, moved = MiniAssembler(start), [], {}

    def emit(name, blob, ticks, source):
        listing.append(dict(source, address=a.pc, instruction=name, tstates=ticks))
        a.emit(*blob)

    pcs = sorted(pc for pc in rows if start <= pc < end)
    replacements = {'LD L,(IX+1)': [('LD L,E (cached lookahead)', b'\x6b', 4)],
        'LD E,(HL)': [('LD A,(HL)', b'\x7e', 7), ("EX AF,AF' (hold symbol)", b'\x08', 4)],
        'LD B,(IX+0)': [('LD B,E (advance cache)', b'\x43', 4), ('LD E,(IX+1)', b'\xdd\x5e\x01', 19)],
        'LD A,E': [("EX AF,AF' (return symbol)", b'\x08', 4)]}
    expected = {'LD L,(IX+1)': b'\xdd\x6e\x01', 'LD E,(HL)': b'\x5e',
                'LD B,(IX+0)': b'\xdd\x46\x00', 'LD A,E': b'\x7b'}
    replaced = []
    for pc, nxt in zip(pcs, pcs[1:]+[end]):
        row = rows[pc]
        blob = bytes(read8(i) for i in range(pc, nxt))
        moved[pc] = a.pc
        a.label(f'old_{pc}')
        if row['instruction'] in replacements:
            name = row['instruction']
            if blob != expected[name]: raise ValueError(('unexpected prefix bytes', row))
            for name2, data, ticks in replacements[name]: emit(name2, data, ticks, row)
            replaced.append(name)
        elif blob[0] in (0x18, 0x20, 0x28, 0x30, 0x38):
            target = pc+2+int.from_bytes(blob[1:], 'little', signed=True)
            if not start <= target <= end: raise ValueError('external short-path branch')
            listing.append(dict(row, address=a.pc))
            a.rel8(blob[0], f'old_{target}')
        else:
            emit(row['instruction'], blob, row['tstates'], row)
    a.label(f'old_{end}')
    if a.pc != end or sorted(replaced) != sorted(replacements):
        raise ValueError('short-path layout or replacements differ')
    regions = [(start, a.resolve())]
    removed = [(start, end)]
    new_labels = {name: moved.get(pc, pc) for name, pc in labels.items()}
    # The fallback only needs the saved rank's high byte. PUSH AF saves A
    # directly instead of moving the rank to B and pushing BC. POP AF later
    # recovers it before SLA B supplies the next bit's flags. Same four bytes
    # and 25 T as INC IX; LD B,E; PUSH BC, with no trampoline penalty.
    if bytes(read8(end+i) for i in range(4)) != b'\xdd\x23\x43\xc5':
        raise ValueError('unexpected long-rank save')
    regions.append((end, b'\x08\xdd\x23\xf5'))
    removed.append((end, end+4))
    for pc, name, ticks in ((end, "EX AF,AF' (recover rank)", 4),
                            (end+1, 'INC IX', 10), (end+3, 'PUSH AF (save rank)', 11)):
        listing.append(dict(rows[end], address=pc, instruction=name, tstates=ticks))
    a = MiniAssembler(HELPER)
    context = dict(phase='reconstruct', stage='huffman') if frame else {}
    a.label('lookahead_refresh')
    emit('LD B,(IX+0)', b'\xdd\x46\x00', 19, context)
    emit('LD E,(IX+1)', b'\xdd\x5e\x01', 19, context)
    emit('RET', b'\xc9', 10, context)
    if a.pc > LIMIT: raise ValueError('lookahead helpers overlap renderer')
    if any(read8(pc) for pc in range(HELPER, a.pc)):
        raise ValueError('lookahead helper RAM is not empty')
    regions.append((HELPER, a.resolve()))
    new_labels.update(a.labels)
    init_rows = [r for pc, r in rows.items()
                 if pc >= labels['frame' if frame else 'chunk']
                 and r['instruction'] == ('LD B,(IX+0) (cache input)' if frame else 'LD B,(IX+0)')]
    if len(init_rows) != 1: raise ValueError('expected exactly one cache initialization')
    redirects = [
        (labels['cache_long_refresh'], b'\xdd\x46\x00', 'JP lookahead refresh', 0xc3, a.labels['lookahead_refresh'], 10),
        (init_rows[0]['address'], b'\xdd\x46\x00', 'CALL lookahead refresh', 0xcd, a.labels['lookahead_refresh'], 17),
    ]
    for pc, before, name, opcode, target, ticks in redirects:
        if bytes(read8(pc+i) for i in range(len(before))) != before:
            raise ValueError(('unexpected redirect bytes', hex(pc)))
        regions.append((pc, bytes([opcode, *target.to_bytes(2, 'little')])))
        removed.append((pc, pc+len(before)))
        listing.append(dict(rows[pc], instruction=name, tstates=ticks))
    motion = []
    if frame:
        # Only instructions while the alternate register set is selected
        # change. The primary cache input pointer remains DE.
        changes = {'POP DE': ('POP HL', 0xd1, 0xe1),
                   'LD (DE),A': ('LD (HL),A', 0x12, 0x77),
                   'INC E': ('INC L', 0x1c, 0x2c),
                   'LD A,E': ('LD A,L', 0x7b, 0x7d),
                   'LD E,A': ('LD L,A', 0x5f, 0x6f)}
        for phase in (2, 4, 6):
            lo = labels[f'predict_{phase}']
            hi = labels.get(f'predict_{phase+2}', labels['clear_tile'])
            alternate = False
            count = 0
            for pc in sorted(pc for pc in rows if lo <= pc < hi):
                row = rows[pc]
                if row['instruction'] == 'EXX':
                    alternate = not alternate
                elif alternate:
                    name = row['instruction']
                    if name == 'ADD A,31': continue
                    if name not in changes: raise ValueError(('unexpected alternate motion use', row))
                    renamed, before, after = changes[name]
                    if read8(pc) != before: raise ValueError('motion opcode differs')
                    regions.append((pc, bytes([after])))
                    removed.append((pc, pc+1))
                    listing.append(dict(row, instruction=renamed))
                    motion.append(dict(address=pc, before=before, after=after,
                                       tstates=row['tstates'], delta_tstates=0))
                    count += 1
            if alternate or count != 39:
                raise ValueError(('motion register audit differs', phase, count, alternate))
    full_rows = [r for pc, r in rows.items() if not any(lo <= pc < hi for lo, hi in removed)] + listing
    return dict(regions=[dict(address=pc, code_hex=blob.hex(), sha256=sha(blob)) for pc, blob in regions],
        listing=full_rows, labels=new_labels, motion_changes=motion,
        extra_code_bytes=7, extra_stack_bytes=2, helper_origin=HELPER, helper_end=a.pc,
        required_readable_lookahead_bytes=2, stream_delta_bytes=0,
        per_frame_setup_delta_tstates=46, short_inside_delta_tstates=-11,
        short_cross_delta_tstates=-7, long_delta_tstates=18,
        note='Setup CALL needs two stack bytes; helpers and motion changes preserve IRQ state.',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


def install_frame(h):
    """Install before inline patches; packet lookahead remains caller-owned."""
    c = h.cpu
    c.guarding = False
    report = build(c.read8, h.instructions.values(), h.recon, frame=True)
    for region in report['regions']:
        for i, value in enumerate(bytes.fromhex(region['code_hex'])):
            c.write8(region['address']+i, value)
    h.recon.update(report['labels'])
    h.instructions = {r['address']: r for r in report['listing']}
    return report


def delta(short_inside, short_cross, long):
    return 46-11*short_inside-7*short_cross+18*long
