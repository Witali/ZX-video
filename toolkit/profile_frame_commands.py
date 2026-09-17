"""Profile drawing of one exact released frame, with nominal Z80 T-states."""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from assess_single_disk import read_build
from benchmark_player_relocation import fixture
from test_packet_lookahead import word


def profile(build, frame):
    meta, blocks, _, _, _ = read_build(build)
    index = 0
    for block in blocks:
        offset = 0
        while offset < len(block):
            size = struct.unpack_from('<H', block, offset)[0]
            packet = block[offset + 2:offset + 2 + size]
            offset += 2 + size
            if index == frame:
                end = 0
                for _ in range(6):
                    end += 1 + 2 * packet[end]
                return profile_commands(build, packet[end:])
            index += 1
    raise ValueError('frame outside build')


def profile_commands(build, commands):
    cpu, labels, _, pointer = fixture(build)
    cpu.write8(labels['update_base'], 0x40)
    word(cpu, labels, 'attr_base', 0x5800)
    for i, value in enumerate(commands):
        cpu.write8(pointer + i, value)
    cpu.pc = labels['command_loop']; cpu.ix = pointer; cpu.push(0x5F00)
    rows = []; current = None
    entries = {labels[name]: name for name in labels if name.startswith('command_') and name != 'command_loop'}
    while cpu.pc != 0x5F00:
        if cpu.pc in entries or cpu.pc == labels.get('rle_row_from_hl'):
            if current is not None:
                current['tstates'] = cpu.tstates - current.pop('start')
            current = dict(command=entries.get(cpu.pc, 'rle_row_from_hl'), start=cpu.tstates)
            rows.append(current)
        if cpu.pc == labels['command_loop'] and current is not None and 'start' in current:
            current['tstates'] = cpu.tstates - current.pop('start'); current = None
        cpu.step()
        if cpu.steps > 1000000:
            raise AssertionError('drawing did not terminate')
    counts = Counter(); cycles = Counter()
    for row in rows:
        counts[row['command']] += 1
        cycles[row['command']] += row['tstates']
    return dict(command_bytes=len(commands), routines=dict(counts), tstates=dict(cycles),
                total_routine_tstates=sum(cycles.values()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path)
    p.add_argument('--frame', type=int, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = profile(args.build, args.frame)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
