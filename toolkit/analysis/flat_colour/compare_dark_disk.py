"""Full native references, source contracts, quiet-motion metrics and preview."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import wave
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[3];sys.path.insert(0, str(ROOT/'toolkit'))
import lineart_colour as line
from cell_palette_quality import averaged
from build_zxv_trd import render_spectrum_screen
import five_level_dither as five
from build_fap3_trd import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path);p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--image-cache', type=Path, required=True);p.add_argument('--ffmpeg', type=Path, required=True)
    args = p.parse_args();build = args.build
    manifest = json.loads((build/'conversion.json').read_bytes())
    assert manifest['complete'] and manifest['timing_verified'] and manifest['lineart_dark_fills']
    assert manifest['colour_policy'] == 'lineart' and len(manifest['volumes']) == 1
    volume = manifest['volumes'][0];count = manifest['frames']
    native = np.load(build/'work'/Path(volume['file']).stem/'states.npz')['states']
    prepared = np.load(build/'work/five-states.npy')
    saved = np.load(args.image_cache/'states.npz');source = saved['source'];baseline = saved['baseline']
    np.testing.assert_array_equal(prepared, saved['dark'])
    np.testing.assert_array_equal(np.fromfile(build/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3), source)
    np.testing.assert_array_equal(np.fromfile(args.baseline/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3), source)
    assert count == len(source) == len(native) == len(baseline) == 977
    assert (build/'work/ay.bin').read_bytes() == (args.baseline/'work/ay.bin').read_bytes()
    with wave.open(str(build/'work/audio-preview.wav'), 'rb') as current, wave.open(str(args.baseline/'work/audio-preview.wav'), 'rb') as old:
        assert current.getparams() == old.getparams()
        assert current.readframes(current.getnframes()) == old.readframes(old.getnframes())
    image = np.zeros((96, 128, 3), np.uint8);rows = [];previous = None
    temporal = dict(quiet_samples=0, rgb_before_sum=0., rgb_after_sum=0., chroma_before_sum=0., chroma_after_sum=0.)
    for i, active in enumerate(source):
        image[12:84] = active
        old = averaged(baseline[i]);new = averaged(native[i])
        np.testing.assert_array_equal(new, averaged(prepared[i]))
        old_error = np.mean((old-image)**2, -1);new_error = np.mean((new-image)**2, -1)
        changed = np.any(new != old, -1)
        assert (new_error <= old_error).all() and (new_error[changed] < old_error[changed]).all()
        lines = line.source_lines(image);fills = line.source_fills(image, dark_fills=True)
        assert np.array_equal(new[lines], np.zeros((int(lines.sum()), 3)))
        old_colour = np.ptp(old, -1) > 0;np.testing.assert_array_equal(new[old_colour], old[old_colour])
        coloured = np.ptp(new, -1) > 0;np.testing.assert_array_equal(new[coloured], line.COLOURS[fills[coloured]])
        black = np.all(new == 0, -1);black[:12] = black[84:] = False
        assert (lines[black] | (fills[black] == 0)).all()
        assert set(np.unique(five.unpack_levels(native[i][:3840]))) <= {0, 4}
        row = dict(frame=i, changed_samples=int(changed.sum()), coloured_samples=int(coloured.sum()),
            rgb_mse_before=float(old_error[12:84].mean()), rgb_mse_after=float(new_error[12:84].mean()))
        if previous is not None:
            prev_source, prev_old, prev_new = previous
            quiet = np.max(np.abs(active.astype(float)-prev_source), -1) <= 4
            delta = active.astype(float)-prev_source
            residuals = [old[12:84]-prev_old-delta, new[12:84]-prev_new-delta]
            temporal['quiet_samples'] += int(quiet.sum())
            for name, residual in zip(('before', 'after'), residuals):
                temporal['rgb_'+name+'_sum'] += float(np.mean(residual[quiet]**2, -1).sum())
                chroma = residual @ np.array([[1., 0.], [-1., -1.], [0., 1.]])
                temporal['chroma_'+name+'_sum'] += float(np.mean(chroma[quiet]**2, -1).sum())
        previous = active.astype(float), old[12:84].copy(), new[12:84].copy();rows.append(row)
    denominator = max(1, temporal.pop('quiet_samples'))
    temporal = dict(quiet_source_max_component_delta=4, quiet_samples=denominator,
        **{key.replace('_sum', '_mse'):value/denominator for key,value in temporal.items()})
    old_conversion = json.loads((args.baseline/'conversion.json').read_bytes())
    result = dict(complete=True, full_native_qualified=True, frames=count,
        every_changed_pixel_strictly_closer_to_original=True, every_source_line_black=True,
        every_existing_coloured_pixel_exact=True, every_black_or_colour_fill_source_matched=True,
        no_dither=True, entire_original_rgb_and_ay_and_model_wav_exact=True,
        rgb_mse_before=float(np.mean([r['rgb_mse_before'] for r in rows])),
        rgb_mse_after=float(np.mean([r['rgb_mse_after'] for r in rows])),
        changed_samples=sum(r['changed_samples'] for r in rows), temporal=temporal, frames_detail=rows,
        source_sha256=sha(source.tobytes()), prepared_states_sha256=sha(prepared.tobytes()),
        used_sectors_before=old_conversion['volumes'][0]['used_sectors'], used_sectors_after=volume['used_sectors'],
        compressed_stream_bytes_before=(args.baseline/'work'/Path(old_conversion['volumes'][0]['file']).stem/'codebook.stream').stat().st_size,
        compressed_stream_bytes_after=(build/'work'/Path(volume['file']).stem/'codebook.stream').stat().st_size,
        scope='Exact full native references and original-source per-pixel accuracy/quiet-motion metrics. RGB MSE is an image-model diagnostic, not a photographic/semantic quality percentage.')
    (build/'accuracy-comparison.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    command = [str(args.ffmpeg), '-v', 'error', '-nostdin', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '768x168', '-framerate', '10', '-i', 'pipe:0', '-i', str(build/'work/audio-preview.wav'),
        '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '128k', '-t', str(count/10), '-movflags', '+faststart', str(build/'accuracy-comparison.mp4')]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for i in range(count):
            panel = Image.new('RGB', (768, 168), '#181818');draw = ImageDraw.Draw(panel)
            pictures = (source[i].repeat(2, 0).repeat(2, 1), render_spectrum_screen(*five.expand(baseline[i]))[24:168],
                render_spectrum_screen(*five.expand(native[i]))[24:168])
            for col, (label, pixels) in enumerate(zip(('Source', 'Previous line drawing', 'Matched dark fills'), pictures)):
                panel.paste(Image.fromarray(pixels), (col*256, 24));draw.text((col*256+4, 4), f'{i/10:.1f}s {label}', fill='white')
            process.stdin.write(np.asarray(panel, np.uint8).tobytes())
    finally:process.stdin.close()
    if process.wait():raise RuntimeError('comparison preview failed')
    print(json.dumps({k:v for k,v in result.items() if k != 'frames_detail'}, indent=2))


if __name__ == '__main__':main()
