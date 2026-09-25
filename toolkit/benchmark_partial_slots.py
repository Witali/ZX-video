"""Execute full/partial slot consumers on all packets, with only initial prefill.

No foreground idle refill is modeled: both readers receive identical requests.
Counts CPU instructions, packet copies, paging and the producer's ROM adapters.
TR-DOS ROM execution, disk latency, IRQ/ULA and frame rendering are excluded.
This is a CPU/ownership check, not the real publication schedule.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import disk_blocks, sha
from benchmark_context_huffman import word
from benchmark_direct_slot_input import Harness as Producer
from test_slot_queue import QueueHarness


def install_copy_guard(q):
    cpu = q.cpu
    original = cpu.step
    copies = {pc for pc, row in q.instructions.items()
              if row['phase'] == 'slot_bridge' and row['instruction'] == 'LDI'}
    stats = Counter()

    def state8(name):
        return cpu.banks[7][q.q[name]-0xc000]

    def step():
        if cpu.pc in copies:
            slot = state8('read_slot')
            if cpu.port_7ffd & 7 != (0, 1, 3, 4)[slot]:
                raise AssertionError('consumer copied from wrong slot')
            if state8('count'):
                index = q.q['lengths']-0xc000+2*slot
                available = int.from_bytes(cpu.banks[7][index:index+2], 'little')
            else:
                if state8('phase') != 2 or slot != state8('write_slot'):
                    raise AssertionError('partial consumer does not own active slot')
                available = (word(cpu, q.h.decoder.labels['slice_output'])-0xe000) & 65535
                stats['active_prefix_bytes'] += 1
            if not 0xe000 <= cpu.hl() < 0xe000+available:
                raise AssertionError('consumer read a byte not yet produced')
            stats['checked_copy_bytes'] += 1
        original()

    cpu.step = step
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--max-frames', type=int, default=0, help='global smoke limit; zero means all')
    args = parser.parse_args()
    if args.max_frames < 0:
        raise ValueError('nonnegative limit required')
    report = dict(scope=__doc__, complete=False, release=False, baseline_commit='4706e96',
        source_sha256=sha(Path(__file__).read_bytes()),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', volumes=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    checked = 0
    for part in (1, 2, 3):
        meta, stream, blocks = disk_blocks(args.directory, part)
        image = (args.directory/f'ZX-video-huffman-preview_part{part:02}.trd').read_bytes()
        raw = b''.join(blob for _, blob in blocks)
        harnesses = {name: QueueHarness(Producer(image, meta['video_start_sector'], meta['video_sectors']),
                     len(blocks), partial_consumption=partial) for name, partial in (('baseline', False), ('partial', True))}
        guards = {name: install_copy_guard(h) for name, h in harnesses.items()}
        volume = dict(part=part, trd_sha256=sha(image), stream_sha256=sha(stream), raw_sha256=sha(raw),
            frame_start=meta['frame_start'], frames_expected=meta['frames'], complete=False,
            code={name: [dict(address=a, bytes=len(blob), sha256=sha(blob)) for a, blob in h.regions]
                  for name, h in harnesses.items()}, prefill={}, frames=[])
        report['volumes'].append(volume)
        for name, h in harnesses.items():
            volume['prefill'][name] = h.call(h.q['prefill'])
            if h.cpu.read8(h.q['count']) != min(4, len(blocks)):
                raise AssertionError('initial occupancy differs')
        at = 0
        for index in range(meta['frames']):
            if args.max_frames and checked >= args.max_frames:
                save()
                return
            size = struct.unpack_from('<H', raw, at)[0]
            result = dict(frame=meta['frame_start']+index, bytes=size+2)
            for name, h in harnesses.items():
                start, reads = h.cpu.tstates, len(h.cpu.reads)
                if h.take(2) != raw[at:at+2] or h.take(size) != raw[at+2:at+2+size]:
                    raise AssertionError('packet differs')
                result[name] = dict(tstates=h.cpu.tstates-start, sectors=len(h.cpu.reads)-reads)
            at += size+2
            checked += 1
            result['delta_tstates'] = result['partial']['tstates']-result['baseline']['tstates']
            volume['frames'].append(result)
            if index % 250 == 0:
                save()
                print(f'Disk {part}: paired exact packets {index+1}/{meta["frames"]}', flush=True)
        if at != len(raw):
            raise AssertionError('raw EOF differs')
        volume['summary'] = {}
        for name, h in harnesses.items():
            if (h.cpu.read8(h.q['count']) or word(h.cpu, h.q['blocks_left'])
                    or [r['sector'] for r in h.cpu.reads] != h.h.positions):
                raise AssertionError('queue EOF or disk order differs')
            if guards[name]['checked_copy_bytes'] != len(raw):
                raise AssertionError('copy guard did not cover all bytes')
            stages = Counter()
            for (pc, ticks), count in h.histogram.items():
                stages[h.instructions[pc]['phase'] if pc in h.instructions else 'local_zx0'] += ticks*count
            total = sum(t for _, t in h.calls)
            if total != sum(stages.values()):
                raise AssertionError('instruction accounting differs')
            volume['summary'][name] = dict(tstates=total, stages=dict(stages), sectors=len(h.cpu.reads),
                **guards[name], max_take_tstates=max(row[name]['tstates'] for row in volume['frames']))
        volume['complete'] = True
        save()
        print(json.dumps(dict(part=part, summary=volume['summary'])), flush=True)
    report.update(complete=True, checked_frames=checked,
        totals={name: sum(v['summary'][name]['tstates'] for v in report['volumes']) for name in ('baseline', 'partial')})
    save()


if __name__ == '__main__':
    main()
