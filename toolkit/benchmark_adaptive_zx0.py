"""Select tested ZX0 tokenizations by decoder T-states within each disk budget.

Exact multiple-choice byte-budget search; this is NOT a deadline-aware planner.
CPU profiles use 256-byte output requests, with token-boundary suspension.
Only variants that can fit alongside minimum-size choices are executed.
The selected stream is then checked with the actual producer and mocked ROM.
IRQ, ULA, frame rendering, queue scheduling and physical disk latency excluded.
"""
import argparse
from collections import Counter
from itertools import accumulate
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import Harness, disk_blocks
from benchmark_direct_slot_input import Harness as ProducerHarness
import disk_layout
from probe_adaptive_block_codecs import ZX0_ONLY, geometry, sha


def stream_capacity(start, used_sectors=2544):
    """Largest whole logical-sector allocation fitting fixed bootstrap geometry."""
    logical = 0
    while geometry((logical+1)*256, start)['fixed_bootstrap_used_sectors'] <= used_sectors:
        logical += 1
    return logical*256


def choose_cpu(options, capacity):
    """Minimize additive decoder T-states; Pareto-prune bytes/cycles after each block.

    Each option has name/bytes/tstates, bytes include its four-byte header.
    Future blocks have a precomputed minimum, so impossible states are skipped.
    Equal cycle totals prefer fewer bytes; equal complete choices retain order.
    """
    minimum = [min(row['bytes'] for row in group) for group in options]
    remaining = list(accumulate(reversed(minimum)))
    remaining = list(reversed(remaining))+[0]
    states = {0: (0, ())}
    for index, group in enumerate(options):
        candidates = {}
        for used, (ticks, choices) in states.items():
            for row in group:
                size = used+row['bytes']
                cost = ticks+row['tstates']
                if size+remaining[index+1] > capacity:
                    continue
                if size not in candidates or cost < candidates[size][0]:
                    candidates[size] = (cost, choices+(row['name'],))
        states = {}
        best = float('inf')
        for used, result in sorted(candidates.items()):
            if result[0] < best:
                states[used] = result
                best = result[0]
        if not states:
            raise ValueError('no choices fit capacity')
    used, (ticks, choices) = min(states.items(), key=lambda item: (item[1][0], item[0]))
    return dict(stream_bytes=used, decoder_tstates=ticks, selected_codecs=list(choices),
                selected_counts=dict(Counter(choices)), final_pareto_states=len(states))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('storage', 'directory', 'cache', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    source = json.loads(args.storage.read_bytes())
    if not source['complete'] or not all(v['complete'] for v in source['volumes']):
        raise ValueError('complete storage probe required')
    decoder = Harness(dynamic_input=True)
    report = dict(scope=__doc__, complete=False, release=False,
        storage_report_sha256=sha(args.storage.read_bytes()),
        probe_sha256=sha(Path(__file__).read_bytes()),
        decoder_code_sha256=sha(decoder.code), decoder_code_bytes=len(decoder.code),
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        player_changed=False, player_instruction_delta_tstates=0,
        actual_publication_verified=False, physical_disk_latency_verified=False,
        fixed_bootstrap_only=True, volumes=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)

    def save():
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    for baseline in source['volumes']:
        part = baseline['part']
        meta, stream, blocks = disk_blocks(args.directory, part)
        if baseline['stream_sha256'] != sha(stream) or len(blocks) != baseline['blocks_expected']:
            raise ValueError('different input stream')
        start = meta['video_start_sector']
        capacity = stream_capacity(start)
        original_used = geometry(len(stream), start)['fixed_bootstrap_used_sectors']
        minima = [min(row['candidates'][name]['bytes']+4 for name in ZX0_ONLY
                      if row['candidates'][name]['slot_fits']) for row in baseline['blocks']]
        minimum = sum(minima)
        volume = dict(part=part, trd_sha256=meta['trd_sha256'], stream_sha256=sha(stream),
            baseline_stream_bytes=len(stream), capacity_bytes=capacity,
            budget_above_baseline_bytes=capacity-len(stream), video_start_sector=start,
            blocks_expected=len(blocks), complete=False, blocks=[])
        report['volumes'].append(volume)
        options = []
        for index, ((original, raw), row) in enumerate(zip(blocks, baseline['blocks'])):
            if sha(raw) != row['decoded_sha256'] or sha(original) != row['candidates']['zx0']['sha256']:
                raise ValueError('block mismatch')
            results = {}
            group = []
            for name in ZX0_ONLY:
                candidate = row['candidates'][name]
                size = candidate['bytes']+4
                if not candidate['slot_fits'] or minimum-minima[index]+size > capacity:
                    results[name] = dict(executed=False, reason='cannot fit even with all other smallest blocks')
                    continue
                packed = (args.cache/candidate['cache_file']).read_bytes()
                if len(packed) != candidate['bytes'] or sha(packed) != candidate['sha256']:
                    raise ValueError('candidate cache hash mismatch')
                decoder.begin(packed, raw, slot=(0, 1, 3, 4)[index % 4], screen_bit=8*(index % 2))
                for target in list(range(256, len(raw), 256))+[len(raw)]:
                    decoder.run(target)
                measured = decoder.finish()
                results[name] = dict(executed=True, bytes=size, tstates=measured['tstates'],
                    max_slice_tstates=measured['max_slice_tstates'],
                    private_stack_bytes=measured['private_stack_bytes'],
                    slices=len(measured['slices']), payload_sha256=sha(packed))
                group.append(dict(name=name, bytes=size, tstates=measured['tstates']))
            options.append(group)
            volume['blocks'].append(dict(index=index, decoded_sha256=sha(raw), variants=results))
            if index % 20 == 0:
                save()
                print(f'Disk {part}: CPU {index+1}/{len(blocks)} blocks', flush=True)
        base_ticks = sum(row['variants']['zx0']['tstates'] for row in volume['blocks'])
        volume['baseline_decoder_tstates'] = base_ticks
        volume['selections'] = {}
        for label, limit in (('no_extra_sectors', stream_capacity(start, original_used)),
                             ('full_disk_budget', capacity)):
            selected = choose_cpu(options, limit)
            selected.update(geometry(selected['stream_bytes'], start))
            selected['delta_decoder_tstates'] = selected['decoder_tstates']-base_ticks
            selected['delta_bytes'] = selected['stream_bytes']-len(stream)
            selected['capacity_bytes'] = limit
            volume['selections'][label] = selected
        save()
        # Validate the selected whole stream's carry-sector changes and paging.
        # A synthetic image is used as a CPU fixture, never saved as a release TRD.
        volume['producer_checks'] = {}
        variants = {'baseline': ['zx0']*len(blocks)}
        variants.update({label: row['selected_codecs'] for label, row in volume['selections'].items()})
        completed = {}
        for label, names in variants.items():
            if tuple(names) in completed:
                volume['producer_checks'][label] = dict(reuses=completed[tuple(names)])
                continue
            picked = [(args.cache/row['candidates'][name]['cache_file']).read_bytes()
                      for row, name in zip(baseline['blocks'], names)]
            selected_stream = b''.join(struct.pack('<HH', len(raw), len(packed))+packed
                                      for packed, (_, raw) in zip(picked, blocks))
            padded = selected_stream+bytes(-len(selected_stream) % 256)
            physical = disk_layout.arrange(padded, start % 16)
            image = bytearray(655360)
            if start*256+len(physical) > len(image):
                raise AssertionError('fixture exceeds physical disk')
            image[start*256:start*256+len(physical)] = physical
            producer = ProducerHarness(bytes(image), start, len(padded)//256)
            for index, (packed, (_, raw)) in enumerate(zip(picked, blocks)):
                result = producer.block(packed, raw, index)
                if result['decoder_tstates'] != volume['blocks'][index]['variants'][names[index]]['tstates']:
                    raise AssertionError('input alignment changed measured decoder cost')
                if index % 40 == 0:
                    print(f'Disk {part}: producer {label} {index+1}/{len(blocks)}', flush=True)
            result = producer.finish()
            result.update(stream_sha256=sha(selected_stream), stream_bytes=len(selected_stream),
                          producer_code_sha256=sha(producer.code), producer_code_bytes=len(producer.code),
                          total_cpu_tstates=result['producer_tstates']+result['decoder_tstates'])
            if label == 'baseline' and selected_stream != stream:
                raise AssertionError('baseline stream changed')
            volume['producer_checks'][label] = result
            completed[tuple(names)] = label
            save()
        volume['complete'] = True
        save()
        print(json.dumps(dict(part=part, budget=capacity-len(stream),
            selections={name:{k:v for k,v in row.items() if k != 'selected_codecs'}
                        for name, row in volume['selections'].items()},
            producer=volume['producer_checks'])), flush=True)
    report['complete'] = True
    save()


if __name__ == '__main__':
    main()
