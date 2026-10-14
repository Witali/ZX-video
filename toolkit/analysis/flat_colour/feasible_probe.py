"""Complete-input image contracts and real CB46/LZSA2 size for feasible fills."""
import argparse
import json
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
import lineart_colour as line
import lineart_feasible as feasible
from cell_palette_quality import averaged
from guarded_cb46 import representation
from convert_cb41 import pack_blocks
from probe_adaptive_block_codecs import ExternalCodec
from build_fap3_trd import sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--frames', type=int, default=977)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lzsa', type=Path, required=True)
    parser.add_argument('--pack-only', action='store_true')
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()) and not args.pack_only:parser.error('output must be empty')
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter();saved = np.load(args.input)
    sources = saved['source'][:args.frames]
    baseline = saved['states'][:args.frames]
    variants = [];rows = [];image = np.zeros((96, 128, 3), np.uint8)
    if args.pack_only:
        cached = np.load(args.output/'states.npz')
        np.testing.assert_array_equal(cached['source'], sources)
        np.testing.assert_array_equal(cached['baseline'], baseline)
        variants = list(cached['feasible'])
        rows = json.loads((args.output/'images.json').read_bytes())['per_frame']
    for i, source in (enumerate(sources) if not args.pack_only else []):
        image[12:84] = source
        np.testing.assert_array_equal(np.frombuffer(line.encode(image), np.uint8), baseline[i])
        state = feasible.encode(image);variants.append(np.frombuffer(state, np.uint8))
        old = averaged(baseline[i].tobytes());new = averaged(state)
        old_error = np.mean((old-image)**2, axis=-1);new_error = np.mean((new-image)**2, axis=-1)
        changed = np.any(old != new, axis=-1)
        assert (new_error <= old_error).all()
        assert (new_error[changed] < old_error[changed]).all()
        lines = line.source_lines(image);fills = line.source_fills(image)
        mandatory = lines | (fills == 0) | (fills == 7)
        np.testing.assert_array_equal(new[mandatory], old[mandatory])
        rows.append(dict(frame=i, changed_samples=int(changed.sum()),
            squared_error_saved=float((old_error-new_error).sum()),
            rgb_mse_before=float(old_error[12:84].mean()),rgb_mse_after=float(new_error[12:84].mean())))
        if i % 100 == 0:print(f'image {i}/{len(sources)}: changed {sum(r["changed_samples"] for r in rows)}', flush=True)
    variants = np.array(variants)
    np.savez_compressed(args.output/'states.npz', source=sources, baseline=baseline, feasible=variants)
    report = dict(frames=len(sources), every_frame_source_contracts=True,
        changed_samples=sum(r['changed_samples'] for r in rows),changed_frames=sum(r['changed_samples']>0 for r in rows),
        mean_rgb_mse_before=float(np.mean([r['rgb_mse_before'] for r in rows])),
        mean_rgb_mse_after=float(np.mean([r['rgb_mse_after'] for r in rows])),per_frame=rows)
    (args.output/'images.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    codec = ExternalCodec('lzsa2', args.lzsa, args.lzsa, 'existing project encoder')
    (args.output/'cache').mkdir(exist_ok=True)
    sizes = {}
    for name, frames in (('baseline', baseline), ('feasible', variants)):
        print(f'encoding {name}', flush=True)
        result = representation(frames, 0, len(frames))
        stream, blocks = pack_blocks(result['raw'], codec, args.output/'cache')
        (args.output/(name+'.raw')).write_bytes(result['raw'])
        (args.output/(name+'.stream')).write_bytes(stream)
        sizes[name] = dict(raw_bytes=len(result['raw']), stream_bytes=len(stream), blocks=blocks,
            raw_sha256=sha(result['raw']),stream_sha256=sha(stream),rows=result['rows'],
            proof=result['dynamic_proof'])
        print(f'{name}: {len(stream)} bytes', flush=True)
    (args.output/'compression.json').write_text(json.dumps(dict(scope='Complete matched frames with actual CB46 packets, static cell dictionary and LZSA2 block headers. Exact host screen and LZSA2 roundtrips; no new native timing or complete disk allocation claim.',
        sizes=sizes, stream_delta_bytes=sizes['feasible']['stream_bytes']-sizes['baseline']['stream_bytes'],
        elapsed_seconds=time.perf_counter()-started), indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'per_frame'}, indent=2), flush=True)


if __name__ == '__main__':main()
