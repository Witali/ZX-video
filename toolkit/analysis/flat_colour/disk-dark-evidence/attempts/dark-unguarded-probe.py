"""Complete accuracy/transport test of source-matched dark line-art fills."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
import lineart_colour as line
import five_level_dither as five
from cell_palette_quality import averaged
from guarded_cb46 import representation
from convert_cb41 import pack_blocks
from probe_adaptive_block_codecs import ExternalCodec
from build_fap3_trd import sha
from build_zxv_trd import render_spectrum_screen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True);p.add_argument('--output', type=Path, required=True)
    p.add_argument('--frames', type=int, default=977);p.add_argument('--lzsa', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():raise ValueError('output must be new')
    args.output.mkdir(parents=True);saved = np.load(args.input)
    sources = saved['source'][:args.frames];baseline = saved['states'][:args.frames]
    states = [];rows = [];image = np.zeros((96, 128, 3), np.uint8)
    for i, active in enumerate(sources):
        image[12:84] = active
        state = line.encode(image, dark_fills=True);states.append(np.frombuffer(state, np.uint8))
        old = averaged(baseline[i]);new = averaged(state)
        old_error = np.mean((old-image)**2, axis=-1);new_error = np.mean((new-image)**2, axis=-1)
        changed = np.any(new != old, axis=-1)
        assert (new_error <= old_error).all() and (new_error[changed] < old_error[changed]).all()
        lines = line.source_lines(image);old_fills = line.source_fills(image)
        fills = line.source_fills(image, dark_fills=True)
        added = (fills == 0) & (old_fills != 0);added[:12] = added[84:] = False
        mandatory = lines | (old_fills == 0) | (np.ptp(old, axis=-1) > 0) | (fills == 7)
        assert np.array_equal(new[mandatory], old[mandatory]), f'mandatory source pixels changed in frame {i}'
        np.testing.assert_array_equal(new[fills == 0], np.zeros((int((fills == 0).sum()), 3)))
        assert set(np.unique(five.unpack_levels(state[:3840]))) <= {0, 4}
        rows.append(dict(frame=i, changed_samples=int(changed.sum()), additional_dark_samples=int(added.sum()),
            rgb_mse_before=float(old_error[12:84].mean()),rgb_mse_after=float(new_error[12:84].mean())))
        if i % 100 == 0:print(f'image {i}/{len(sources)}: changed {sum(r["changed_samples"] for r in rows)}', flush=True)
    states = np.array(states)
    np.savez_compressed(args.output/'states.npz', source=sources, baseline=baseline, dark=states)
    report = dict(frames=len(sources), complete_image_contracts=True,
        changed_samples=sum(r['changed_samples'] for r in rows),changed_frames=sum(r['changed_samples']>0 for r in rows),
        additional_dark_samples=sum(r['additional_dark_samples'] for r in rows),
        mean_rgb_mse_before=float(np.mean([r['rgb_mse_before'] for r in rows])),
        mean_rgb_mse_after=float(np.mean([r['rgb_mse_after'] for r in rows])),frames_detail=rows,
        producer_sha256=sha((ROOT/'toolkit/lineart_colour.py').read_bytes().replace(b'\r\n', b'\n')))
    (args.output/'images.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    indices = (98, 154, 259, 300, 506, 792)
    panel = Image.new('RGB', (1536, len(indices)*312), '#181818');draw = ImageDraw.Draw(panel)
    for row, i in enumerate(indices):
        image[12:84] = sources[i]
        pictures = (image.repeat(2, 0).repeat(2, 1), render_spectrum_screen(*five.expand(baseline[i])),render_spectrum_screen(*five.expand(states[i])))
        for col, (label, picture) in enumerate(zip(('Source', 'Previous line drawing', 'Source-matched dark fills'), pictures)):
            draw.text((col*512+8, row*312+4), f'{i/10:.1f}s {label}', fill='white')
            panel.paste(Image.fromarray(picture[24:168]).resize((512, 288), Image.Resampling.NEAREST), (col*512, row*312+24))
    panel.save(args.output/'comparison.png')
    codec = ExternalCodec('lzsa2', args.lzsa, args.lzsa, 'existing project encoder')
    cache = args.output/'cache';cache.mkdir();sizes = {}
    for name, frames in (('baseline', baseline), ('dark', states)):
        print(f'encoding {name}', flush=True);result = representation(frames, 0, len(frames))
        stream, blocks = pack_blocks(result['raw'], codec, cache)
        (args.output/(name+'.raw')).write_bytes(result['raw']);(args.output/(name+'.stream')).write_bytes(stream)
        sizes[name] = dict(raw_bytes=len(result['raw']),stream_bytes=len(stream),blocks=blocks,
            raw_sha256=sha(result['raw']),stream_sha256=sha(stream),rows=result['rows'],proof=result['dynamic_proof'])
        print(f'{name}: {len(stream)} bytes', flush=True)
    (args.output/'compression.json').write_text(json.dumps(dict(scope='Complete matched CB46/LZSA2 transport including dictionary and block headers, exact host screens/in-place LZSA2 roundtrips; complete native release qualification remains separate.',
        sizes=sizes,stream_delta_bytes=sizes['dark']['stream_bytes']-sizes['baseline']['stream_bytes']), indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'frames_detail'}, indent=2), flush=True)


if __name__ == '__main__':main()
