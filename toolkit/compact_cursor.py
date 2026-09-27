"""Update only the low byte of the compact tile cursor within a stripe.

Tiles start at even columns 0..30; an ordinary tile adds two and a no-op
run ends no later than column 32. Neither operation carries into the high
byte. The existing stripe transition still advances the full address.
Replacements retain all instruction-region lengths and public labels.
Flags and temporary HL/DE differ locally; each successor overwrites them
before use. No compressed bytes, extra RAM or stack storage are required.
"""
from build_fap3_trd import sha


def build(read8, instructions, labels):
    rows = {r['address']: r for r in instructions}
    target = labels['target']
    operand = list(target.to_bytes(2, 'little'))
    ordinary = labels['tile_done']
    skipped = [r['address'] for r in rows.values()
               if labels['scan_done'] <= r['address'] < labels['scan_check']
               and r['instruction'] == 'LD HL,(target)']
    if len(skipped) != 1:
        raise ValueError('expected one ordinary no-op scanner target advance')
    patches = []
    for name, start, expected, body, old_t, new_t in (
        ('tile', ordinary, [0x2a, *operand, 0x2c, 0x2c, 0x22, *operand],
         [('LD A,(target)', [0x3a, *operand], 13), ('ADD A,2', [0xc6, 2], 7),
          ('LD (target),A', [0x32, *operand], 13)], 40, 33),
        ('noop_run', skipped[0], [0x2a, *operand, 0x79, 0x87, 0x5f, 0x16, 0, 0x19, 0x22, *operand],
         [('LD HL,target byte', [0x21, *operand], 10), ('LD A,C', [0x79], 4),
          ('ADD A,A', [0x87], 4), ('ADD A,(HL)', [0x86], 7), ('LD (HL),A', [0x77], 7),
          ('JP cursor continuation', [0xc3, *((skipped[0] + 12).to_bytes(2, 'little'))], 10)], 62, 42),
    ):
        before = bytes(read8(start+i) for i in range(len(expected)))
        if before != bytes(expected):
            raise ValueError(('unexpected cursor code', name, hex(start), before.hex()))
        end = start + len(expected)
        old_rows = [rows[pc] for pc in sorted(rows) if start <= pc < end]
        if sum(r['tstates'] for r in old_rows) != old_t:
            raise ValueError('baseline cursor timing differs')
        code = bytearray()
        listing = []
        for instruction, data, ticks in body:
            listing.append(dict(address=start+len(code), instruction=instruction,
                                tstates=ticks, phase='reconstruct', stage=rows[start]['stage']))
            code.extend(data)
        if sum(r['tstates'] for r in listing) != new_t or len(code) > len(expected):
            raise ValueError('replacement cursor size/timing differs')
        # The no-op JP skips two old bytes; they are cleared, not executed.
        code.extend(bytes(len(expected)-len(code)))
        patches.append(dict(name=name, start=start, end=end, before_hex=before.hex(),
            code_hex=code.hex(), code_sha256=sha(code), listing=listing,
            baseline_tstates=old_t, tstates=new_t, delta_tstates=new_t-old_t))
    return dict(patches=patches, target=target, extra_code_bytes=0, extra_stack_bytes=0,
        extra_ram_bytes=0, compressed_stream_delta_bytes=0,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')


def install_stage(h):
    """Install on a constructed CPU fixture, after optional relocation/inlining."""
    c = h.cpu
    c.guarding = False
    result = build(c.read8, h.instructions.values(), h.recon)
    for patch in result['patches']:
        for i, value in enumerate(bytes.fromhex(patch['code_hex'])):
            c.write8(patch['start'] + i, value)
        for pc in list(h.instructions):
            if patch['start'] <= pc < patch['end']:
                del h.instructions[pc]
        h.instructions.update({r['address']: r for r in patch['listing']})
    return result


def delta(counts):
    return -7 * counts['tile'] - 20 * counts['noop_run']
