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
                 '; ABI: HL=input, DE=output; AF/BC/DE/HL are working registers; uses caller stack.',
                 '; Standard can run in ROM; Turbo patches its offset and requires writable code.',
                 '; Counts exclude IRQ/ULA/disk. Preserve working registers in interrupt handlers.', '']
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
                    lines.append(f'; {namespace}_{name}: {ROUTINES[name]}')
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
