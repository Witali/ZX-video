"""Experimental positional no-op tags dispatched through the fast-fragment call.

Only interior stripes are tagged. A tag 128+k replaces the first zero in a
maximal run of k unchanged tiles; the remaining vector bytes stay zero.
Masks, pixels, audio and packet lengths are unchanged. This is a different
runtime format and must never be sent to an unpatched player.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha
from probe_fast_noop_scan import frame_runs, scanner_tstates
from vector_run_stream import decode_vectors

CODE, LIMIT = 0x7c31, 0x7d50


def encode(vectors, masks, minimum=4):
    if len(vectors) != 192 or len(masks) != 384 or any(v > 88 for v in vectors):
        raise ValueError('one untagged vector/mask frame required')
    if not 1 <= minimum <= 16:
        raise ValueError('minimum must be 1..16')
    out = bytearray(vectors)
    for first in range(16, 176, 16):
        i = first
        while i < first+16:
            if vectors[i] or masks[2*i] or masks[2*i+1]:
                i += 1
                continue
            begin = i
            while i < first+16 and not (vectors[i] or masks[2*i] or masks[2*i+1]):
                i += 1
            if i-begin >= minimum:
                out[begin] = 128+i-begin
    if decode_vectors(bytes(out), masks, inplace=True)[0] != vectors:
        raise AssertionError('tag roundtrip differs')
    return bytes(out)


def cycle_counts(vectors, masks, minimum=4):
    """Instruction-table prediction, validated by paired native execution."""
    # Edge stripes may be explicitly cleared, so use only the interior runs.
    inside = bytes(16)+vectors[16:176]+bytes(16)
    runs, _ = frame_runs(inside, bytes(32)+masks[32:352]+bytes(32))
    chosen = [(k, kind) for k, kind in runs if k >= minimum]
    fast = sum(85 <= v <= 88 for v in vectors)
    old = sum(scanner_tstates(k, kind, True)-20 for k, kind in chosen)
    new = sum(308 if kind == 'end' else 318 for _, kind in chosen)
    return dict(runs=len(chosen), skipped_tiles=sum(k for k, _ in chosen),
        fast_fragments=fast, baseline_run_tstates=old, run_tstates=new,
        fragment_dispatch_delta_tstates=17*fast,
        delta_tstates=new-old+17*fast)


def build(read8, instructions, labels):
    if not all(k in labels for k in ('fast_tile', 'fast_fragment', 'scan_check')):
        raise ValueError('requires fast fragments and the no-op scanner')
    if 'raw_intra_tile' in labels:
        raise ValueError('raw-intra high bits conflict with run tags')
    at, dest = labels['fast_tile'], labels['fast_fragment']
    before = b'\xcd'+dest.to_bytes(2, 'little')
    if bytes(read8(at+i) for i in range(3)) != before or at+3 != labels['tile_done']:
        raise ValueError('unexpected fast-fragment call/return layout')
    a, rows = MiniAssembler(CODE), []
    def e(name, data, ticks):
        rows.append(dict(address=a.pc, instruction=name, tstates=ticks,
                         phase='reconstruct', stage='tagged_noop_control'))
        a.emit(*data)
    def n(name, op, value, ticks):
        e(name, bytes([op])+value.to_bytes(2, 'little'), ticks)
    e('CP run tag', [0xfe,128], 7)
    n('JP C,fast_fragment', 0xda, dest, 10)
    e('AND run length', [0xe6,31], 7); e('LD C,A', [0x4f], 4)
    e('LD B,0', [0x06,0], 7)
    # Tile entry already advanced HL and vectors by one. No other routine
    # has run yet, so recover the start without a memory load.
    e('DEC HL', [0x2b], 6); e('ADD HL,BC', [0x09], 11)
    n('LD (vectors),HL', 0x22, labels['vectors'], 16)
    e('ADD A,A', [0x87], 4); e('LD E,A', [0x5f], 4); e('LD D,0', [0x16,0], 7)
    n('LD HL,(bitmap_masks)', 0x2a, labels['bitmap_masks'], 16)
    e('ADD HL,DE', [0x19], 11); n('LD (bitmap_masks),HL', 0x22, labels['bitmap_masks'], 16)
    # Compact tile offsets are even 0..30; even a full run ends at 32.
    n('LD HL,target byte', 0x21, labels['target'], 10)
    e('ADD A,(HL)', [0x86], 7); e('LD (HL),A', [0x77], 7)
    n('LD HL,tiles_left', 0x21, labels['tiles_left'], 10)
    e('LD A,(HL)', [0x7e], 7); e('SUB C', [0x91], 4); e('LD (HL),A', [0x77], 7)
    # Bypass tile_done: all k tiles have already been accounted for.
    # POP and JP preserve the flags from SUB. The outer frame return stays.
    e('POP HL (discard fragment return)', [0xe1], 10)
    n('JP Z,stripe_done', 0xca, labels['stripe_done'], 10)
    n('JP tile', 0xc3, labels['tile'], 10)
    code = a.resolve()
    if a.pc > LIMIT or any(read8(CODE+i) for i in range(len(code))):
        raise ValueError('tag helper space is not free')
    hook = b'\xcd'+CODE.to_bytes(2, 'little')
    source = next(r for r in instructions if r['address'] == at)
    return dict(origin=CODE, end=a.pc, helper_bytes=len(code), code_hex=code.hex(),
        code_sha256=sha(code), hook_address=at, before_hex=before.hex(), hook_hex=hook.hex(),
        listing=rows+[dict(source, instruction='CALL tagged run or fast fragment')],
        extra_stack_bytes=0, extra_state_bytes=0,
        baseline_fast_call_tstates=17, fast_call_tstates=17,
        fast_fragment_delta_tstates=17, run_end_tstates=308, run_continue_tstates=318,
        baseline_run_tstates={'end':'74*k+192', 'vector':'74*k+258', 'patch':'74*k+258'},
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        timing_excludes=['IRQ', 'ULA', 'ROM', 'disk delivery', 'outer frame stages'])


def install_stage(h):
    c = h.cpu; c.guarding = False
    report = build(c.read8, h.instructions.values(), h.recon)
    for at, key in ((CODE, 'code_hex'), (report['hook_address'], 'hook_hex')):
        for i, value in enumerate(bytes.fromhex(report[key])): c.write8(at+i, value)
    h.instructions.update({r['address']:r for r in report['listing']})
    return report
