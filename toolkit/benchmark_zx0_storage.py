"""Count actual Z80 turbo-ZX0 cycles for every saved storage-probe block.

Decoder entry through RET, including source reads and history/output writes.
Default bench map: code 8000, output 6000..7FFF, input A000..DFFF, stack 9FF0.
Optional bank16 map: output C000..FFFF in bank 0, input 4000..7FFF,
code 8000, stack BFF0. This overwrites the bank-5 screen and is a CPU-only
fixture, not a proposed release placement for the compressed input.
Not a release memory map. Excludes caller setup/CALL, block-header parsing,
incremental suspension, input refill/paging, IRQ, ULA, ROM and physical disk.
"""
import argparse
import json
from pathlib import Path

from build_zxv_trd import MiniAssembler
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU
from zx0_codec import emit_decoder


def decode_block(code, payload, expected, *, layout='default8'):
    if layout not in ('default8', 'bank16'):
        raise ValueError('unknown benchmark layout')
    input_base, output_base, stack, limit = ((0xa000, 0x6000, 0x9ff0, 8192)
        if layout == 'default8' else (0x4000, 0xc000, 0xbff0, 16384))
    if len(payload) > 16384 or len(expected) > limit:
        raise ValueError('block exceeds benchmark buffers')
    cpu = CPU(b'', b'')
    for address, data in ((0x8000, code), (input_base, payload)):
        for offset, value in enumerate(data):
            cpu.write8(address + offset, value)
    cpu.pc, cpu.sp = 0x8000, stack
    cpu.set_hl(input_base)
    cpu.set_de(output_base)
    cpu.push(0x9f00)
    while cpu.pc != 0x9f00:
        if cpu.steps >= 1_000_000:
            raise RuntimeError('decoder instruction limit exceeded')
        cpu.step()
    if cpu.de() != ((output_base + len(expected)) & 65535) or cpu.sp != stack:
        raise AssertionError('wrong output pointer/stack')
    if bytes(cpu.read8(output_base + i) for i in range(len(expected))) != expected:
        raise AssertionError('Z80 output differs from source block')
    return cpu.tstates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', type=Path, required=True)
    parser.add_argument('--storage-report', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True, help='actual optimal or quick ZX0 cache directory')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline-commit', default='f3f5390',
                        help='experiment baseline, recorded without changing decoder code')
    parser.add_argument('--layout', choices=('default8', 'bank16'), default='default8')
    args = parser.parse_args()
    raw = args.raw.read_bytes()
    source = json.loads(args.storage_report.read_text())
    limit = 8192 if args.layout == 'default8' else 16384
    if not source['complete'] or sha(raw) != source['input_sha256'] or source['block_bytes'] > limit:
        raise ValueError('incomplete/mismatched storage report or oversized blocks')
    assembler = MiniAssembler(0x8000)
    emit_decoder(assembler, 'turbo')
    code = assembler.resolve()
    report = dict(scope=__doc__, baseline_commit=args.baseline_commit, input_sha256=sha(raw),
        storage_report_sha256=sha(args.storage_report.read_bytes()), decoder='ZX0 turbo',
        benchmark_layout=args.layout, max_decoded_block_bytes=limit,
        decoder_bytes=len(code), decoder_sha256=sha(code),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        complete=False, player_changed=False, integrated_player_delta_tstates=0, blocks=[])
    offset = 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for index, block in enumerate(source['blocks']):
        expected = raw[offset:offset+block['decoded_bytes']]
        offset += len(expected)
        if len(expected) != block['decoded_bytes'] or sha(expected) != block['sha256']:
            raise ValueError('raw block mismatch')
        payload = (args.cache / (block['sha256'] + '.zx0')).read_bytes()
        if len(payload) != block['zx0_bytes']:
            raise ValueError('coded block size mismatch')
        cycles = decode_block(code, payload, expected, layout=args.layout)
        report['blocks'].append(dict(index=index, raw_bytes=len(expected), compressed_bytes=len(payload),
            raw_sha256=sha(expected), compressed_sha256=sha(payload), tstates=cycles))
        if index % 25 == 0:
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print(f'Z80 verified ZX0 block {index+1}/{len(source["blocks"])}', flush=True)
    if offset != len(raw) or len(report['blocks']) != source['blocks_expected']:
        raise AssertionError('incomplete input coverage')
    report['complete'] = True
    counts = [row['tstates'] for row in report['blocks']]
    report['summary'] = dict(blocks=len(counts), raw_bytes=len(raw), total_tstates=sum(counts),
        mean_block_tstates=sum(counts)/len(counts), max_block_tstates=max(counts),
        bytes_with_headers=source['zx0_with_headers_bytes'])
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
