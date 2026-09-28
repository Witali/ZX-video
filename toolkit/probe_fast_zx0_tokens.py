"""Measure lossless short-match removal with the installed Fast ZX0 decoder.

Each candidate executes as an isolated 256-byte-demand block. In-place
placement is proved for all 256 stream offsets. CPU excludes ROM/IRQ/ULA,
full queue scheduling and physical disk latency. Selection is a heuristic
with a measured disk-byte charge, not a publication-deadline proof.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import struct

from benchmark_adaptive_zx0 import choose_cpu, stream_capacity
from benchmark_faster_zx0 import fixture, inputs
from benchmark_inplace_streaming import finish
from build_fap3_trd import sha
from inplace_zx0 import layout, trace
from probe_adaptive_block_codecs import geometry
import zx0_speed

ROOT = Path(__file__).parent
THRESHOLDS = (0, 2, 3, 4, 5, 6, 8)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, default=ROOT/'fast_zx0_tokens_probe.json')
    p.add_argument('--cache', type=Path, default=ROOT.parent/'.tmp/fast-zx0-token-cache')
    p.add_argument('--limit', type=int, help='Smoke blocks per disk; never complete')
    args = p.parse_args()
    if args.output.exists(): p.error('refuse to overwrite evidence')
    if args.limit is not None and args.limit < 1: p.error('positive limit required')
    args.cache.mkdir(parents=True, exist_ok=True); args.output.parent.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((ROOT/'faster_zx0_cpu.json').read_bytes())
    playback = json.loads((ROOT/'fast_zx0_player_summary.json').read_bytes())
    built = json.loads((ROOT/'fast_zx0_player_build.json').read_bytes())
    result = dict(complete=False, release=False, scope=__doc__, baseline_commit='2881667',
        thresholds=list(THRESHOLDS), player_instruction_delta_tstates=0, volumes=[])
    histogram = Counter()
    def save(): args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    save()
    try:
        for source, original_stream, blocks in inputs():
            part = source['part']; before = playback['volumes'][part-1]['fast']
            native = baseline['volumes'][part-1]['variants']['fast']['blocks']
            start = built['volumes'][part-1]['video_start_sector']
            capacity = stream_capacity(start)
            # Observed service includes ROM, IRQ, ULA and emulated drive.
            # Round upward; actual selected-sector costs must be measured later.
            disk_charge = (before['read_service_tstates']+before['seek_service_tstates']+
                           before['runtime_sectors']*256-1)//(before['runtime_sectors']*256)
            v = dict(part=part, stream_sha256=sha(original_stream), baseline_bytes=len(original_stream),
                capacity_bytes=capacity, spare_bytes=capacity-len(original_stream),
                video_start_sector=start, disk_charge_tstates_per_byte=disk_charge, blocks=[])
            result['volumes'].append(v)
            for index, (payload, raw) in enumerate(blocks[:args.limit]):
                variants = {}; seen = {}
                row = dict(index=index, raw_sha256=sha(raw), decoded_bytes=len(raw), variants=variants)
                v['blocks'].append(row)
                for threshold in THRESHOLDS:
                    name = f'min{threshold}'
                    packed = payload if not threshold else zx0_speed.rewrite(payload, threshold)
                    digest = sha(packed)
                    if digest in seen:
                        variants[name] = dict(variants[seen[digest]], reuses=seen[digest]); continue
                    seen[digest] = name
                    exact, proof = trace(packed, limit=len(raw))
                    if exact != raw: raise AssertionError('changed decoded bytes')
                    plans = [layout(len(packed), len(raw), proof['minimum_input_start'], offset) for offset in range(256)]
                    worst = min(x['slack_bytes'] for x in plans)
                    path = args.cache/(digest+'.zx0')
                    if path.exists() and path.read_bytes() != packed: raise AssertionError('cache collision')
                    path.write_bytes(packed)
                    option = dict(bytes=len(packed)+4, payload_sha256=digest, cache_file=path.name,
                        all_offsets_fit=all(x['sector_aligned_fits'] for x in plans),
                        minimum_slack_bytes=worst, overlap_proof=proof, executed=False)
                    variants[name] = option
                    if not option['all_offsets_fit']: continue
                    stream = struct.pack('<HH', len(raw), len(packed))+packed
                    h, decoder_layout = fixture(stream, 32, 'fast')
                    actual = h.block(packed, raw, 0)
                    summary = finish(h)
                    if threshold == 0 and actual['decoder_tstates'] != native[index]['decoder_tstates']:
                        raise AssertionError(('baseline CPU differs', part, index))
                    for i in summary['decoder_instruction_histogram']:
                        histogram[i['pc'], i['opcode_hex'], i['tstates']] += i['count']
                    option.update(executed=True, decoder_tstates=actual['decoder_tstates'],
                        slice_tstates=actual['slice_tstates'], max_slice_tstates=max(actual['slice_tstates']),
                        sectors=actual['sectors'], exact=actual['exact'],
                        decoder_instruction_table_checked=summary['decoder_instruction_table_checked'])
                    result['decoder_layout'] = decoder_layout
                if index % 8 == 0:
                    save(); print(f'disk {part}: {index+1}/{len(blocks)} token variants exact', flush=True)
            if args.limit is None:
                v['selections'] = {}
                baseline_cpu = sum(r['variants']['min0']['decoder_tstates'] for r in v['blocks'])
                for label, price in (('cpu_only', 0), ('disk_charged', disk_charge), ('double_disk_charge', 2*disk_charge)):
                    options = [[dict(name=name, bytes=o['bytes'], tstates=o['decoder_tstates']+price*o['bytes'])
                        for name, o in r['variants'].items() if o['executed'] and 'reuses' not in o] for r in v['blocks']]
                    picked = choose_cpu(options, capacity)
                    names = picked.pop('selected_codecs')
                    objective = picked.pop('decoder_tstates')
                    ticks = sum(r['variants'][name]['decoder_tstates'] for r, name in zip(v['blocks'], names, strict=True))
                    v['selections'][label] = dict(picked, selected=names, disk_charge_tstates_per_byte=price,
                        estimated_objective_tstates=objective, decoder_tstates=ticks,
                        delta_decoder_tstates=ticks-baseline_cpu, delta_bytes=picked['stream_bytes']-len(original_stream),
                        **geometry(picked['stream_bytes'], start))
                print(json.dumps(dict(part=part, selections={n:{k:x for k,x in s.items() if k!='selected'}
                    for n,s in v['selections'].items()})), flush=True)
            save()
        result['complete'] = args.limit is None
    except Exception as exc: result['failure'] = repr(exc); raise
    finally:
        result['decoder_instruction_histogram'] = [dict(pc=pc, opcode_hex=op, tstates=t, count=n)
            for (pc,op,t),n in sorted(histogram.items())]
        names = ('probe_fast_zx0_tokens.py', 'zx0_speed.py', 'faster_zx0.py', 'benchmark_faster_zx0.py',
            'benchmark_adaptive_zx0.py', 'benchmark_inplace_slot.py', 'benchmark_inplace_streaming.py',
            'inplace_zx0.py', 'zx0_codec.py', 'probe_adaptive_block_codecs.py')
        result['source_sha256_lf'] = {n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in names}
        result['references'] = {n:sha((ROOT/n).read_bytes()) for n in
            ('fast_zx0_player_build.json', 'fast_zx0_player_summary.json', 'faster_zx0_cpu.json')}
        save()


if __name__ == '__main__': main()
