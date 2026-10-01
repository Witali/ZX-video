"""Replay saved AY comparisons through the checked Z80 resident decoder/consumer."""
import argparse
import json
from pathlib import Path

import ay_huffman_stream
import ay_interrupt
from benchmark_resident_audio_z80 import Harness, word
from build_long_video_trd import AyFrame
import pipelined_frame_z80 as video
import resident_audio_z80 as resident


def profile(raw):
    frames = [AyFrame.deserialize(raw[i:i+9]) for i in range(0, len(raw), 9)]
    records = ay_interrupt.encode_ticks(frames)
    coded, _ = ay_huffman_stream.encode(records)
    harness = Harness(coded, batch=31, paging=True)
    harness.cpu.port_7ffd = 0x17
    harness.cpu.write8(video.SHADOW, 0x17)
    calls, consumer = [], []
    while harness.consumed < len(records):
        elapsed, emitted = harness.fill_wrapped()
        assert emitted == min(31, len(records)-harness.consumed)
        calls.append(elapsed)
        for _ in range(emitted):
            consumer.append(harness.consume())
    harness.finish()
    assert not word(harness.cpu, harness.audio['audio_underruns'])
    payload = resident.tables(coded)[3]
    writes = sum(r[0] for r in records)
    # Instruction-table formula used by benchmark_resident_audio_z80.measure().
    expected = (109*len(calls)+789*len(records)+137*writes+
        71*harness.build['input_bits']+17*sum(v.bit_count() for v in payload)+32*len(payload)+
        harness.bridge['overhead_tstates']*len(calls))
    # Partial final batch: taken JR NZ (+5), LD HL,(remaining) 16,
    # LD A,H 4, OR L 4, taken JR Z 12 = 41 T beyond a full batch.
    if len(records) % 31:
        expected += 41
    assert sum(calls) == expected, (sum(calls), expected)
    return dict(ticks=len(frames), coded_bytes=len(coded), bank_image_bytes=harness.build['image_bytes'],
        register_writes=writes, init_tstates=harness.init_tstates,
        producer_with_paging_tstates=sum(calls), consumer_tstates=sum(consumer),
        producer_and_consumer_tstates=sum(calls)+sum(consumer),
        maximum_consumer_tick_tstates=max(consumer), maximum_31_tick_fill_tstates=max(calls),
        all_register_states_exact=True, all_producer_instruction_timings_checked=True,
        consumer_instruction_formula_checked=True, guarded_memory_writes=True,
        producer_independent_instruction_formula_checked=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source = json.loads((args.probe/'report.json').read_text())
    report = dict(scope='Isolated resident decoder, paging wrapper and AY consumer. Dirty RAM boot. '
        'No video, real-time FIFO scheduling, IRQ wrapper, ULA contention, TR-DOS or physical disk latency.',
        batch_ticks=31, windows=[])
    for window in source['windows']:
        directory = args.probe/f'{window["start_seconds"]:g}s'
        variants = {name: profile((directory/f'{name}.ay').read_bytes()) for name in ('before', 'after')}
        record = dict(start_seconds=window['start_seconds'], **variants)
        record['delta_total_tstates'] = (variants['after']['producer_and_consumer_tstates']-
                                         variants['before']['producer_and_consumer_tstates'])
        report['windows'].append(record)
        print(json.dumps(record), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
