"""Resume full faithful-colour/AY-square preparation from hashed RGB caches.

Video and audio components can run independently. Finalization requires both;
this is source preparation, never a playback or release assertion.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import time

import numpy as np

import ay_fidelity as ay
import ay_interrupt
from build_long_video_trd import AyFrame
from convert_video import write_json
import faithful_colour as colour
import five_level_dither as five
from prepare_cell_codebook_movie import file_sha, sha
from verify_cell_codebook_movie import independent_screen


def prepare_video(args, base):
    previous = None
    chunks, quality = [], []
    started = time.monotonic()
    for chunk in base['chunks']:
        source = args.prepared.parent/chunk['file']
        if file_sha(source) != chunk['sha256']:
            raise ValueError('source RGB chunk changed')
        target = args.output/chunk['file']
        info = target.with_suffix('.json')
        if target.exists() and info.exists():
            record = json.loads(info.read_bytes())
            if file_sha(target) != record['sha256']:
                raise ValueError('refined chunk cache changed')
            with np.load(target, allow_pickle=False) as cached:
                previous = cached['last_attrs'].copy()
        else:
            with np.load(source, allow_pickle=False) as cached:
                images = cached['images'].copy()
                mapping = cached['source_frames'].copy()
                old = cached['five_states'].copy()
            frames, rows = [], []
            for local, image in enumerate(images):
                state = colour.encode(image, previous, luma_guard='cell')
                previous = np.frombuffer(state[3840:], np.uint8).copy()
                screen = independent_screen(state)
                if screen != b''.join(five.expand(state)):
                    raise AssertionError('independent host screen differs')
                errors = colour.errors(image, state)
                old_errors = colour.errors(image, old[local])
                rows.append(dict(frame=chunk['start']+local, source_frame=int(mapping[local]),
                    screen_sha256=sha(screen),
                    rgb_mse=float(errors['rgb'][12:84].mean()),
                    luma_mse=float(errors['luma'][12:84].mean()),
                    physical_rgb_mse=float(errors['physical_rgb'][12:84].mean()),
                    old_rgb_mse=float(old_errors['rgb'][12:84].mean()),
                    unique_rows=len(set(map(int, five.unpack_words(state[:3840]).ravel())))))
                frames.append(np.frombuffer(state, np.uint8))
            np.savez_compressed(target, images=images, five_states=np.stack(frames),
                                source_frames=mapping, last_attrs=previous)
            record = dict(start=chunk['start'], end=chunk['end'], sha256=file_sha(target), quality=rows)
            write_json(info, record)
        chunks.append(dict(start=record['start'], end=record['end'], file=target.name, sha256=record['sha256']))
        quality.extend(record['quality'])
        print(f'Faithful colour {record["end"]}/{base["frames"]}, {time.monotonic()-started:.1f}s', flush=True)
    report = dict(complete=True, chunks=chunks, quality=quality,
        all_monochrome_rgb_and_cell_luma_guards_passed=True,
        independent_host_screens_exact=True, palette_history='continuous over the complete retained edit',
        maximum_frame_rows=max(q['unique_rows'] for q in quality),
        mean_rgb_mse=float(np.mean([q['rgb_mse'] for q in quality])),
        old_mean_rgb_mse=float(np.mean([q['old_rgb_mse'] for q in quality])))
    write_json(args.output/'video.json', report)


def prepare_audio(args, base):
    if (args.output/'audio.json').exists():
        report = json.loads((args.output/'audio.json').read_bytes())
        for name, expected in report['files'].items():
            if file_sha(args.output/name) != expected:
                raise ValueError('refined audio cache changed')
        print('Reusing complete refined audio', flush=True)
        return
    rate, hz = 22050, 50
    source_pcm = args.output/'source.f32'
    command = [str(args.ffmpeg.resolve()), '-v', 'error', '-nostdin', '-y', '-i', str(args.source.resolve()),
        '-map', '0:a:0', '-ac', '1', '-ar', str(rate), '-f', 'f32le', str(source_pcm.resolve())]
    subprocess.run(command, check=True)
    source = np.fromfile(source_pcm, '<f4')
    timeline = base['contract']['timeline']
    fps = Fraction(*timeline['frame_rate'])
    pieces, cursor = [], 0
    for lo, hi in timeline['remove_frames']:
        first, last = round(Fraction(lo, 1)/fps*rate), round(Fraction(hi, 1)/fps*rate)
        pieces.append(source[cursor:first]); cursor = last
    pieces.append(source[cursor:])
    retained = np.concatenate(pieces)
    count = base['frames']*base['contract']['frame_fields']
    expected = count*rate//hz
    if len(retained) > expected:
        raise ValueError('audio tail exceeds video; do not truncate')
    samples = np.pad(retained.astype(float), (0, expected-len(retained)))
    np.save(args.output/'edited-pcm.npy', samples.astype('<f4'))
    print(f'Analysing complete edited audio: {count} AY ticks', flush=True)
    magnitude, rms = ay.spectra(samples, rate, hz, count)
    print('Fitting pitches, harmonics and discrete AY registers', flush=True)
    p, v, paths, noise, explained, fit = ay.arrange_for_chip(magnitude, rms, rate)
    del magnitude
    frames = [AyFrame(tuple(map(int, pp)), tuple(map(int, vv)), int(nn)) for pp, vv, nn in zip(p,v,noise)]
    sound = b''.join(f.serialize() for f in frames)
    registers = b''.join(map(ay_interrupt.registers, frames))
    (args.output/'audio.bin').write_bytes(sound)
    (args.output/'registers.bin').write_bytes(registers)
    np.savez_compressed(args.output/'audio-analysis.npz', periods=p, volumes=v, noise=noise,
                        paths=paths, rms=rms, explained=explained)
    import compare_ay_fidelity as metrics
    rendered = ay.render(frames, hz, rate)
    metrics.write_wav(args.output/'audio-preview.wav', rendered, rate)
    checks = []
    for start in (0, 60, 170, 430, 488, 498):
        end = min(start+8, expected/rate)
        lo, hi = round(start*rate), round(end*rate)
        ticks = round((end-start)*hz)
        checks.append(dict(start_seconds=start, ticks=ticks,
            metrics=metrics.compare(metrics.features(samples[lo:hi],rate,hz,ticks),
                                    metrics.features(rendered[lo:hi],rate,hz,ticks))))
    report = dict(complete=True, ay_ticks=count, update_rate_hz=hz, chip_fit=fit,
        mix='FFmpeg mono downmix', source_pcm_samples=len(source), retained_pcm_samples=len(retained),
        padded_silent_samples=expected-len(retained), source_duration_seconds=len(source)/rate,
        ay_sha256=sha(sound), ay_registers_sha256=sha(registers), original_audio_preserved_exact=False,
        user_authorized_audio_retune=True, timeline=timeline, command=command, quality_windows=checks,
        files={name:file_sha(args.output/name) for name in
               ('audio.bin','registers.bin','audio-analysis.npz','audio-preview.wav','edited-pcm.npy')})
    write_json(args.output/'audio.json', report)
    print(f'Prepared {count} AY ticks, including the complete post-credit tail', flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared','source','ffmpeg','output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--component', choices=('video','audio','finish','all'), default='all')
    args = p.parse_args()
    base = json.loads(args.prepared.read_bytes())
    if not base['complete'] or file_sha(args.source) != base['contract']['source_sha256']:
        raise ValueError('incomplete preparation or wrong source video')
    args.output.mkdir(parents=True, exist_ok=True)
    contract = dict(base['contract'], quantizer='faithful_colour cell guard',
        faithful_colour_parameters=colour.PARAMETERS,
        parent_preparation_sha256=file_sha(args.prepared), original_audio_preserved_exact=False,
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('faithful_colour.py','ay_fidelity.py','ay_square_fit.py','prepare_refined_av.py')})
    contract_path = args.output/'contract.json'
    if contract_path.exists() and json.loads(contract_path.read_bytes()) != contract:
        raise ValueError('cache contract changed; use a new output directory')
    write_json(contract_path, contract)
    if args.component in ('video','all'): prepare_video(args, base)
    if args.component in ('audio','all'): prepare_audio(args, base)
    if args.component in ('finish','all'):
        video = json.loads((args.output/'video.json').read_bytes())
        audio = json.loads((args.output/'audio.json').read_bytes())
        if not video['complete'] or not audio['complete']: raise ValueError('components are incomplete')
        report = dict(complete=True, release=False, contract=contract, frames=base['frames'],
            chunks=video['chunks'], quality=video['quality'], ay_ticks=audio['ay_ticks'],
            ay_sha256=audio['ay_sha256'], ay_registers_sha256=audio['ay_registers_sha256'],
            source_frames=base['source_frames'], source_frame_map_sha256=base['source_frame_map_sha256'],
            first_source_frame=base['first_source_frame'], last_source_frame=base['last_source_frame'],
            joins=base['joins'], decoded_source=base['decoded_source'],
            original_audio_preserved_exact=False, user_authorized_audio_retune=True,
            actual_playback_measured=False, disk_capacity_measured=False)
        write_json(args.output/'preparation.json', report)
        print('Refined A/V preparation complete', flush=True)


if __name__ == '__main__': main()
