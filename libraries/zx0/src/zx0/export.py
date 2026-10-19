"""Export generated absolute Z80 regions as a standalone assembly include."""
import json
from pathlib import Path
from ._z80 import sha


ROUTINES = {
    'begin': 'Start a new block after configuring input_pointer, block_end and slice_target.',
    'slice_begin': 'Switch to the private stack and start decoding the current block.',
    'slice_until': 'Resume until the output target; token boundaries can overshoot it.',
    'slice_resume': 'Restore the suspended decoder stack and live working registers.',
    'slice_yield': 'Save the continuation and restore the caller stack before returning.',
    'slice_finished': 'Verify the exact output end, then return on the caller stack.',
    'slice_sync_target': 'Patch high/low output comparisons while the decoder is suspended.',
    'DecompressZX0': 'Fast ZX0 v2 bit/gamma decoder with shared literal and match boundaries.',
    'dzx0_turbo': 'ZX0 v2 turbo decoder; HL=input, DE=output, AF holds the bit reservoir.',
    'dzx0_standard': 'ZX0 v2 compact decoder; HL=input, DE=output; uses the caller stack.',
    'dzx0_mega': 'One-shot bit-phase-expanded ZX0 v2; HL=input, DE=output; AF/BC/HL/DE clobbered. Resident source/history required; writable offset, caller stack.',
    'dzx0m_literals0': 'Refill the bit reservoir and select phase-specific literal Elias paths; BC carries the exact word count.',
    'dzx0m_last_offset': 'Patched negative previous offset; forward LDIR/LDI preserves overlapping history, then restores the source pointer.',
    'dzx0m_new_offset0': 'Decode the inverted offset MSB and test the format EOF before fetching its LSB.',
    'input_check': 'Wait before reading an unavailable page; the bit carry stays live.',
    'literal_split': 'Split literals at input-page boundaries without repeating the output check.',
    'state': 'Mutable words/flags. Keep state and self-modifying operands in writable RAM.',
}


def export(directory, regions, labels, metadata, *, namespace='zx0'):
    """Write decoder.asm, metadata.json, license and one binary per region.

    The include uses ORG/DB and namespaced EQU labels, so it needs no Python
    at application build time. Assemble at the recorded addresses; regenerate
    when relocating. It contains bytes of the adapted decoder, not upstream
    assembly accidentally bypassing the coroutine/streaming improvements.
    """
    if not namespace.isidentifier() or not namespace.isascii():
        raise ValueError('namespace must be an ASCII identifier')
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    lines = ['; Generated adapted ZX0 v2 decoder. See LICENSE; Einar Saukas, spke, uniabis.',
             '; Code and patched operands require writable RAM. Counts exclude IRQ/ULA/disk.',
             '; Preserve decoder registers in IRQ handlers, including AF/AF\' when used.',
             '; Coroutine targets are minimums; retain source and complete output history.',
             '; Configure input_pointer/block_end/slice_target before begin; private SP is saved.', '']
    if 'input_pointer' not in labels:
        lines = ['; Generated forward ZX0 v2 decoder. See LICENSE; Einar Saukas.',
                 '; ABI: HL=input, DE=output; AF/BC/DE/HL clobbered; uses caller stack. Resident source/history required.',
                 '; Standard can run in ROM; the other profiles patch offsets and require writable code.',
                 '; Counts exclude IRQ/ULA/disk. Preserve working registers in interrupt handlers.', '']
    if metadata.get('fast_jumps'):
        lines += ['; Optional unconditional JR -> JP: 12 -> 10 T per execution, +1 byte/site.',
                  '; Conditional branches, register/flag ownership and the caller ABI are unchanged.', '']
    for name, address in sorted(labels.items()):
        if name.isidentifier():
            lines.append(f'{namespace}_{name} equ ${address:04x}')
    for index, (address, blob) in enumerate(regions):
        lines += ['', f'org ${address:04x}', f'; Region {index}: {len(blob)} bytes.']
        points = {address, address + len(blob)}
        for name, target in labels.items():
            if name in ROUTINES and address <= target < address + len(blob):
                points.add(target)
        ordered = sorted(points)
        for lo, hi in zip(ordered, ordered[1:]):
            for name, target in labels.items():
                if target == lo and name in ROUTINES:
                    description=ROUTINES[name]
                    if metadata.get('one_shot') and name=='DecompressZX0':
                        description='Resident Fast ZX0 v2; bit/gamma decoder, writable offset, no boundaries, IX preserved.'
                    lines.append(f'; {namespace}_{name}: {description}')
            for offset in range(lo - address, hi - address, 16):
                part = blob[offset:min(offset + 16, hi - address)]
                lines.append('db ' + ','.join(f'${value:02x}' for value in part))
        (directory / f'region-{index}-{address:04x}.bin').write_bytes(blob)
    (directory / 'decoder.asm').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    report = dict(metadata, labels=labels,
                  regions=[dict(address=at, bytes=len(blob), sha256=sha(blob)) for at, blob in regions])
    (directory / 'metadata.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    (directory / 'LICENSE').write_bytes(Path(__file__).with_name('LICENSE').read_bytes())
    return report
