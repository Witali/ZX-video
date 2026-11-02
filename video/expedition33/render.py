"""Render a review-only 1080p film from an authenticated native Fuse recording."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import wave
import numpy as np
from cards import create

HERE = Path(__file__).resolve().parent
FPS = 50
NATIVE_FPS = 3546900 / 70908


def run(command):
    subprocess.run(command, check=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(capture, decoded, output, *, audio=None, filename='Expedition-33-ZX-Spectrum-Demo.mp4'):
    output.mkdir(parents=True, exist_ok=True)
    work = output / 'materials/work'
    work.mkdir(parents=True, exist_ok=True)
    cfg = json.loads((HERE / 'project.json').read_text(encoding='utf-8'))
    source = json.loads((capture / 'capture.json').read_text())
    info = json.loads(((audio.parent if audio else decoded) / 'decoded.json').read_text())
    assert not source['preview_only'] and source['trd_sha256'] == cfg['disk_sha256']
    assert sha(capture / 'capture.fmf') == source['movie_sha256']
    starts = source['track_starts']
    assert [r[2] for r in starts] == [0, 1, 0]
    assert [r[0] - starts[0][0] for r in starts] == [0, 11254, 19140]
    rate = info['sample_rate']
    chunks = {frame: (offset, count) for frame, offset, count in info['chunks']}

    def samples(stamp):
        frame, t = stamp[:2]
        offset, count = chunks[frame]
        return offset + round(count * t / 70908)

    # Keep the final real loading seconds and both whole tracks at actual
    # speed. Only video presentation is sampled onto a conventional 50 Hz CFR;
    # the original 50.021 Hz capture and all musical samples remain available.
    cut = starts[0][0] - round(cfg['loading_seconds'] * NATIVE_FPS)
    # Fuse flushes sound on complete ULA fields. The final partial field
    # contains the next loop's startup, so finish at its boundary instead.
    start_sample = chunks[cut][0]
    stop_sample = chunks.get(starts[2][0], (info['audio_samples'], 0))[0]
    # Fuse's PCM accumulator is the master for an audiovisual recording. In
    # this build its mean field length differs slightly from the nominal B
    # movie tag. Use the actual captured samples instead of cutting/stretching
    # the soundtrack to a rounded nominal video duration.
    complete_fields = max(chunks) + 1
    samples_per_field = info['audio_samples'] / complete_fields
    phase_error = max(abs(offset - frame * samples_per_field)
                      for frame, offset, count in info['chunks'])
    assert phase_error < 1.1, 'Nonlinear source audio clock needs explicit per-field mapping'
    demo_seconds = (stop_sample - start_sample) / rate
    demo_frames = math.ceil(demo_seconds * FPS)
    opening_frames = cfg['opening_seconds'] * FPS
    ending_frames = cfg['ending_seconds'] * FPS
    total_frames = opening_frames + demo_frames + ending_frames
    total_seconds = total_frames / FPS
    with wave.open(str(audio or decoded / 'native.wav'), 'rb') as wav:
        assert wav.getnchannels() == 2 and wav.getsampwidth() == 2
        wav.setpos(start_sample)
        pcm = np.frombuffer(wav.readframes(stop_sample - start_sample), '<i2').reshape(-1, 2)
    # Only round the final silent tail to a 50 fps frame. Do not stretch audio.
    demo_samples = round(demo_frames / FPS * rate)
    assert abs(demo_samples - len(pcm)) < rate / FPS
    full = np.zeros((round(total_seconds * rate), 2), dtype='<i2')
    offset = cfg['opening_seconds'] * rate
    full[offset:offset + len(pcm)] = pcm
    raw = work / 'soundtrack-original.wav'
    with wave.open(str(raw), 'wb') as wav:
        wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate)
        wav.writeframes(full.tobytes())
    # Two-pass whole-film loudness normalization preserves the actual stereo
    # mix. Do not normalize individual scenes or alter relative voice levels.
    first = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(raw), '-af',
        'loudnorm=I=-16:TP=-1.5:LRA=20:print_format=json', '-f', 'null', '-'],
        capture_output=True, check=True)
    stderr = first.stderr.decode(errors='replace')
    measures = json.loads(stderr[stderr.rfind('{'):stderr.rfind('}') + 1])
    normal = (f'loudnorm=I=-16:TP=-1.5:LRA=20:measured_I={measures["input_i"]}'
        f':measured_TP={measures["input_tp"]}:measured_LRA={measures["input_lra"]}'
        f':measured_thresh={measures["input_thresh"]}:offset={measures["target_offset"]}'
        ':linear=true:print_format=json')
    reference = work / 'soundtrack.wav'
    run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-af', normal,
         '-ar', str(rate), '-c:a', 'pcm_s16le', str(reference)])
    create(work)
    lumiere = cfg['opening_seconds'] + (samples(starts[0]) - start_sample) / rate
    alicia = cfg['opening_seconds'] + (samples(starts[1]) - start_sample) / rate
    boundaries = [0, cfg['opening_seconds'], round(lumiere * FPS) / FPS,
                  round(alicia * FPS) / FPS, (opening_frames + demo_frames) / FPS,
                  total_seconds]
    names = [('opening', 'Expedition 33 for ZX Spectrum'), ('loading', 'Native TRD loading'),
             ('lumiere', 'Lumiere'), ('alicia', 'Alicia'), ('ending', 'Play the demo')]
    scenes = [dict(id=ident, title=title, start=start, duration=round(stop - start, 6),
                   frames=round((stop - start) * FPS))
              for (ident, title), start, stop in zip(names, boundaries, boundaries[1:])]
    timeline = dict(scenes=scenes, native_fps=NATIVE_FPS, source_start_field=cut,
        capture_pcm_fps=rate / samples_per_field, capture_clock_phase_error_samples=phase_error,
        source_end_stamp=[starts[2][0], 0], source_seconds=demo_seconds,
        demo_frames=demo_frames, frames=total_frames, duration_seconds=total_seconds,
        unnormalized_channel_rms=[float(x) for x in np.sqrt(np.mean(pcm.astype(float)**2, axis=0))],
        original_clipped_samples=int(np.sum((pcm == 32767) | (pcm == -32768))),
        normalization=measures, source=source,
        audio_source={k:v for k,v in info.items() if k not in ('chunks', 'exact_native_artwork_matches')})
    (work / 'timeline.json').write_text(json.dumps(timeline, indent=2) + '\n')
    metadata = [';FFMETADATA1', 'title=' + cfg['title'],
                'comment=Native Spectrum 128 demo captured in Fuse; local review copy.']
    for scene in scenes:
        metadata.extend(['[CHAPTER]', 'TIMEBASE=1/1000', f'START={round(scene["start"] * 1000)}',
            f'END={round((scene["start"] + scene["duration"]) * 1000)}', 'title=' + scene['title']])
    (work / 'chapters.txt').write_text('\n'.join(metadata) + '\n', encoding='utf-8')
    video_filter = (f'[0:v]trim=end_frame={opening_frames},setpts=PTS-STARTPTS,'
        'fade=t=in:d=0.4,fade=t=out:st=3.6:d=0.4,setsar=1[o];'
        f'[1:v]trim=start_frame={cut},setpts=N*{samples_per_field:.12f}/{rate}/TB,fps=50,'
        f'trim=end_frame={demo_frames},scale=1920:1080:flags=neighbor,setsar=1[d];'
        f'[2:v]trim=end_frame={ending_frames},setpts=PTS-STARTPTS,'
        'fade=t=in:d=0.4,fade=t=out:st=3.4:d=0.6,setsar=1[e];'
        '[o][d][e]concat=n=3:v=1:a=0,format=rgb24,'
        'scale=iw:ih:flags=neighbor:in_range=pc:out_range=tv:out_color_matrix=bt709,'
        'format=yuv420p[v]')
    film = output / filename
    command = ['ffmpeg', '-v', 'warning', '-y', '-loop', '1', '-framerate', '50',
        '-i', str(work / 'opening.png'), '-i', str(decoded / 'native-lossless.mkv'),
        '-loop', '1', '-framerate', '50', '-i', str(work / 'ending.png'),
        '-i', str(reference), '-i', str(work / 'chapters.txt'), '-filter_complex', video_filter,
        '-map', '[v]', '-map', '3:a:0', '-map_metadata', '4', '-map_chapters', '4',
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '15', '-r', '50',
        '-profile:v', 'high', '-level:v', '4.2', '-color_primaries', 'bt709',
        '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv',
        '-c:a', 'aac', '-b:a', '320k',
        '-metadata:s:a:0', 'language=zxx', '-metadata:s:a:0', 'title=Instrumental AY stereo',
        '-movflags', '+faststart', str(film)]
    (work / 'render-command.json').write_text(json.dumps(command, indent=2) + '\n')
    print('Rendering complete playlist:', total_frames, 'frames,', total_seconds, 'seconds', flush=True)
    run(command)
    shutil.copy2(work / 'thumbnail.png', output / 'thumbnail.png')
    (output / 'title.txt').write_text(cfg['title'] + '\n', encoding='utf-8')
    chapters = '\n'.join(f'{int(s["start"])//60:02d}:{int(s["start"])%60:02d} {s["title"]}'
        for s in scenes if s['id'] not in ('loading', 'ending'))
    description = f'''Play the demo in your browser — our online ZX Spectrum emulator:
{cfg['demo_url']}
Играть в нашем онлайн-эмуляторе ZX Spectrum — ссылка выше.

Download the independently bootable TRD disk image:
{cfg['disk_url']}
Source code: {cfg['repository_url']}

I made this ZX Spectrum demo as my small tribute to the creators of the original Clair Obscur: Expedition 33. Thank you for the world, music and imagery that inspired me to make it.

Expedition 33 Demo for ZX Spectrum 128: Lumière and Alicia arranged for the AY-3-8912, with 18 native 256×192 illustrations and petal/mosaic transitions.

{chapters}

Original game by Sandfall Interactive, published by Kepler Interactive. Original music by Lorien Testard and Alice Duport-Percier. The illustrations are AI-assisted interpretations compiled to genuine Spectrum screens; each 8×8 attribute cell uses two legal colors. The soundtrack is a three-channel AY arrangement.

Title font: Cinzel (SIL Open Font License).

--- Русский ---

Это моя попытка отдать дань уважения создателям оригинальной Clair Obscur: Expedition 33. Спасибо за мир, музыку и образы, которые вдохновили меня на это демо.

Expedition 33 Demo для ZX Spectrum 128: обе композиции, Lumière и Alicia, целиком в аранжировке для AY-3-8912, 18 картинок в настоящем разрешении Spectrum 256×192 и переходы с рассыпанием на лепестки.

Картинки созданы с помощью ИИ и переведены в штатный экранный формат Spectrum с двумя цветами на каждую ячейку 8×8. Музыка звучит на трёх каналах AY.

Онлайн-эмулятор, TRD для скачивания и исходный код доступны по ссылкам в начале описания. Авторы оригинальной игры — Sandfall Interactive, издатель — Kepler Interactive; оригинальная музыка — Lorien Testard и Alice Duport-Percier.

#ZXSpectrum #Expedition33 #Chiptune
'''
    (output / 'description.txt').write_text(description, encoding='utf-8')
    (output / 'REVIEW.txt').write_text('LOCAL REVIEW ONLY. Not uploaded or published.\n'
        'Wait for the user to approve this exact finished video before any YouTube upload.\n')
    snapshot = output / 'materials/project'
    snapshot.mkdir(parents=True, exist_ok=True)
    for path in HERE.iterdir():
        if path.is_file():
            shutil.copy2(path, snapshot / path.name)
    (output / 'materials/work/capture.json').write_text(json.dumps(source, indent=2) + '\n')
    print(json.dumps(dict(file=str(film), seconds=total_seconds, frames=total_frames,
                          bytes=film.stat().st_size, sha256=sha(film)), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--decoded', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--audio', type=Path, help='Optional synchronized WAV and decoded.json from website Ayumi')
    parser.add_argument('--filename', default='Expedition-33-ZX-Spectrum-Demo.mp4')
    args = parser.parse_args()
    render(args.capture, args.decoded, args.output, audio=args.audio, filename=args.filename)
