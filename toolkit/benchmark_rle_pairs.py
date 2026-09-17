"""Compare RLE rows and adjacent commands in two saved player binaries."""
import argparse
import json
from pathlib import Path

from benchmark_player_relocation import draw, fixture


def packet(build, data):
    cpu, labels, _, output = fixture(build)
    pointer = output + 0xFD
    cpu.pc = labels['command_loop']; cpu.ix = pointer
    cpu.push(0x5F00)
    cpu.write8(labels['update_base'], 0x40)
    cpu.banks[5][:6912] = bytes([0xA5])*6912
    for i, value in enumerate(data): cpu.write8(pointer+i, value)
    start = cpu.tstates
    while cpu.pc != 0x5F00:
        assert cpu.steps < 100000
        cpu.step()
    assert cpu.ix == pointer+len(data)
    assert cpu.sp == 0xBFF0
    return bytes(cpu.banks[5][:6912]), cpu.tstates-start


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-build', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(); rows = {}

    def record(name, fn):
        before, old = fn(args.baseline_build)
        after, new = fn(args.build)
        assert before == after, name
        rows[name] = dict(previous_tstates=old, current_tstates=new, delta=new-old)

    for n in range(1, 33):
        tail = bytes([0x80+30-n, 97]) if n < 31 else bytes([0, 97]) if n == 31 else b''
        packed = bytes([n-1])+bytes(range(n))+tail
        payload = bytes([95, len(packed)])+packed
        record(f'literal_{n}_then_fill', lambda b, p=payload: draw(b, 'command_row_rle', p))
    for n in range(2, 33):
        tail = bytes([31-n])+bytes(range(32-n)) if n < 32 else b''
        packed = bytes([0x80+n-2, 197])+tail
        payload = bytes([95, len(packed)])+packed
        record(f'repeat_{n}_then_fill', lambda b, p=payload: draw(b, 'command_row_rle', p))
    for count in (1, 2, 4):
        for kind, packed in (('literal', bytes([31])+bytes(range(32))),
                             ('repeat', bytes([158, 197]))):
            data = b''.join(bytes([5, row, len(packed)])+packed for row in range(count))+b'\0'
            record(f'{kind}_packet_{count}_rows', lambda b, p=data: packet(b, p))
    report = dict(baseline_commit='ba6cab7',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        scope='rows: command entry to command_loop; packets: first dispatch through END/RET',
        exclusions=['IRQ', 'ULA contention', 'ROM service', 'disk latency', 'scheduler'],
        assumptions='screen 4000h; row 95 for standalone commands; stream crosses a page; unchanged dither tables',
        routines=rows,
        adjacent_boundary=dict(previous_tstates=183, current_tstates=37, delta=-146),
        other_command_exit=dict(previous_tstates=35, current_tstates=61, delta=26),
        bootstrap_tstates=dict(previous=fixture(args.baseline_build)[2], current=fixture(args.build)[2]))
    report['bootstrap_tstates']['delta'] = report['bootstrap_tstates']['current']-report['bootstrap_tstates']['previous']
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in rows.items() if k.endswith('32_then_fill') or '_packet_' in k}, indent=2))


if __name__ == '__main__': main()
