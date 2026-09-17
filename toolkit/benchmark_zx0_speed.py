"""Measure short-match removal on an actual movie block using the Z80 CPU."""
import argparse
import hashlib
import json
from pathlib import Path

from assess_single_disk import read_build
from benchmark_player_relocation import fixture
from test_packet_lookahead import run, word
from test_direct_ring_input import place
import zx0_speed


def decode_cycles(build, packed, raw, pointer):
    cpu, labels, _, output = fixture(build)
    place(cpu, 1, pointer, packed)
    for key, value in dict(ring_read_region=1, ring_read_high=pointer >> 8,
            ring_read_low=pointer & 255, ahead_force=1, block_stored=0).items():
        cpu.write8(labels[key], value)
    for key, value in dict(ring_count=40, frame_length=len(packed), block_length=len(raw),
            block_end=output + len(raw), slice_output=output, slice_target=output + min(128, len(raw))).items():
        word(cpu, labels, key, value)
    start = cpu.tstates
    run(cpu, labels, 'load_block_body'); run(cpu, labels, 'slice_begin')
    for target in range(256, len(raw) + 128, 128):
        word(cpu, labels, 'slice_target', output + min(target, len(raw)))
        run(cpu, labels, 'slice_until')
    run(cpu, labels, 'direct_release')
    assert bytes(cpu.read8(output + i) for i in range(len(raw))) == raw
    return cpu.tstates - start


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path); p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--frame', type=int, required=True); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    meta, blocks, _, _, _ = read_build(args.build)
    start = 0
    for raw, block in zip(blocks, [b for v in meta['volumes'] for b in v['blocks']]):
        end = start + block['frames']
        if start <= args.frame < end:
            break
        start = end
    else: raise ValueError('frame outside movie')
    original = (args.cache / (hashlib.sha256(raw).hexdigest() + '.zx0')).read_bytes()
    rows = []
    for minimum in (0, 2, 3, 4, 6, 8):
        data = zx0_speed.rewrite(original, minimum)
        decoded, tokens = zx0_speed.parse(data); assert decoded == raw
        rows.append(dict(minimum_match=minimum, bytes=len(data), tokens=len(tokens),
            cpu_contiguous=decode_cycles(args.build, data, raw, 0xC004),
            cpu_wrapped=decode_cycles(args.build, data, raw, 0xFFF0)))
    report = dict(frame_start=start, frame_end=end, decoded_bytes=len(raw),
        decoded_sha256=hashlib.sha256(raw).hexdigest(),
        player_sha256=hashlib.sha256((args.build / 'PLAYER.C.bin').read_bytes()).hexdigest(),
        scope='load + decode in 128-byte slices + release; routine entry through RET',
        exclusions=['drawing', 'scheduler', 'IRQ', 'ULA contention', 'ROM', 'disk latency'],
        instruction_path_delta_tstates=0, variants=rows)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__': main()
