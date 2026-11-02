"""Verify the final instrumental film, adapted from the production skill's QA.

There is no narration, so language is zxx (no linguistic content) and no
invented speech captions are required. Audio is checked in stereo per scene.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def run(command):
    return subprocess.run(command, check=True, capture_output=True)


def audio(path):
    data = run(['ffmpeg', '-v', 'error', '-i', str(path), '-map', '0:a:0', '-vn',
        '-ac', '2', '-ar', '24000', '-c:a', 'pcm_f32le', '-f', 'f32le', '-']).stdout
    return np.frombuffer(data, '<f4').reshape(-1, 2)


def verify(film, timeline_path, reference, output):
    info = json.loads(run(['ffprobe', '-v', 'error', '-show_format', '-show_streams',
                          '-show_chapters', '-of', 'json', str(film)]).stdout)
    timeline = json.loads(timeline_path.read_text())
    video = next(s for s in info['streams'] if s['codec_type'] == 'video')
    sound = next(s for s in info['streams'] if s['codec_type'] == 'audio')
    seconds = timeline['duration_seconds']
    assert (video['width'], video['height'], video['r_frame_rate']) == (1920, 1080, '50/1')
    assert int(video['nb_frames']) == timeline['frames']
    assert abs(float(video['duration']) - seconds) < .001
    assert sound['channels'] == 2 and sound['tags']['language'] == 'zxx'
    assert abs(float(sound['duration']) - seconds) < .05
    assert len(info['chapters']) == len(timeline['scenes'])
    for chapter, scene in zip(info['chapters'], timeline['scenes']):
        assert abs(float(chapter['start_time']) - scene['start']) < .002
        assert abs(float(chapter['end_time']) - scene['start'] - scene['duration']) < .002
    packets = {}
    for stream in ('v:0', 'a:0'):
        rows = json.loads(run(['ffprobe', '-v', 'error', '-select_streams', stream,
            '-show_packets', '-show_entries', 'packet=dts_time', '-of', 'json', str(film)]).stdout)['packets']
        differences = np.diff([float(row['dts_time']) for row in rows])
        assert np.all(differences > 0)
        assert differences.max() < (.021 if stream == 'v:0' else .06)
        packets[stream] = dict(count=len(rows), max_dts_step=float(differences.max()))
    print('Frame count, duration, stereo, chapters and packet clocks passed.', flush=True)
    full = run(['ffmpeg', '-v', 'error', '-xerror', '-i', str(film),
                '-map', '0:v:0', '-map', '0:a:0', '-f', 'null', '-'])
    assert not full.stderr.strip()
    actual, original = audio(film), audio(reference)
    assert abs(len(actual) - len(original)) < 1024
    comparisons = []
    for scene in timeline['scenes']:
        begin = round(scene['start'] * 24000)
        end = min(len(actual), len(original), round((scene['start'] + scene['duration']) * 24000))
        a, b = actual[begin:end], original[begin:end]
        rms = np.sqrt(np.mean(b*b, axis=0))
        correlations = []
        for channel in range(2):
            if rms[channel] < 1e-6:
                assert np.sqrt(np.mean(a[:, channel]**2)) < .002
                correlations.append(None)
            else:
                correlation = float(np.corrcoef(a[:, channel], b[:, channel])[0, 1])
                assert correlation > .985, (scene['id'], channel, correlation)
                correlations.append(correlation)
        comparisons.append(dict(scene=scene['id'], rms=rms.tolist(), correlations=correlations))
    assert np.max(abs(actual)) < 1
    output.mkdir(parents=True, exist_ok=True)
    # Final encoded frames, not source PNGs: opening, loading, both songs,
    # transition, later artwork and ending all appear on the review sheet.
    points = [1, 5, 12, 23.5, 45, 72, 103, 148, 190,
              timeline['scenes'][3]['start'] + .5, 280, 330, seconds - 2]
    tiles = []
    for index, moment in enumerate(points):
        path = output / f'frame-{index:02d}.png'
        run(['ffmpeg', '-v', 'error', '-y', '-ss', str(moment), '-i', str(film),
             '-frames:v', '1', '-update', '1', str(path)])
        image = Image.open(path).convert('RGB').resize((480, 270), Image.Resampling.NEAREST)
        tile = Image.new('RGB', (480, 298), '#171c24')
        tile.paste(image, (0, 28))
        ImageDraw.Draw(tile).text((10, 7), f'{int(moment)//60:02d}:{int(moment)%60:02d}', fill='white')
        tiles.append(tile)
    sheet = Image.new('RGB', (480 * 3, 298 * 5), '#090d13')
    for index, tile in enumerate(tiles):
        sheet.paste(tile, ((index % 3) * 480, (index // 3) * 298))
    sheet.save(output / 'contact-sheet.jpg', quality=94)
    report = dict(sha256=hashlib.sha256(film.read_bytes()).hexdigest(),
        bytes=film.stat().st_size, duration_seconds=seconds, frames=timeline['frames'],
        resolution=[1920, 1080], fps=50, audio_channels=2, language='zxx',
        packets=packets, scene_audio=comparisons, full_decode='passed',
        narration=False, captions='Not applicable: instrumental demo, no speech.',
        publication='Not uploaded. Awaiting user review.')
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('film', type=Path)
    parser.add_argument('--timeline', type=Path, required=True)
    parser.add_argument('--reference-audio', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    verify(args.film, args.timeline, args.reference_audio, args.output)
