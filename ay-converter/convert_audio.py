"""Audio -> shared automatic AY50 synthesis -> looping TRD and previews.

Offers automatic mixer fitting and the preserved music/legacy profiles.
This is a three-voice arrangement,
not PCM playback or a waveform-transparent codec. Optional Fuse verification
checks every register/field and captures the actual emulator sound in one run.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
from ay_format import registers as frame_registers
import quality
import spectrogram
from support import save, sha
from music_player import build_disk, MAX_TICKS, MAX_ENVELOPE_TICKS


def convert(args):
    source = args.input.resolve(strict=True)
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('output must be a new or empty directory')
    rate = 22050
    maximum=MAX_ENVELOPE_TICKS if getattr(args,'profile','auto')=='auto' else MAX_TICKS
    limit = maximum/50 if args.duration is None else min(args.duration, maximum/50)
    before = min(args.start, 1.)
    command = [str(args.ffmpeg), '-v', 'error', '-nostdin', '-ss', str(args.start-before),
               '-i', str(source), '-t', str(limit+before+1), '-map', '0:a:0',
               '-vn', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']
    from audio_input import probe_filter
    mono,downmix=probe_filter(source,args.ffmpeg)
    if mono:command[-1:-1]=['-af',mono]
    samples = np.frombuffer(subprocess.run(command, capture_output=True, check=True).stdout, '<f4').astype(float)
    if not np.isfinite(samples).all():
        raise ValueError('nonfinite source samples')
    first = round(before*rate)
    ticks = min(math.floor(limit*50+1e-8), max(0, (len(samples)-first)//441))
    if ticks < 1:
        raise ValueError('at least 20 ms of audio is required after --start')
    duration = ticks/50
    out.mkdir(parents=True, exist_ok=True)
    print(json.dumps(dict(stage='analyse', ticks=ticks, duration_seconds=duration)), flush=True)
    from engine import encode
    profile = getattr(args, 'profile', 'auto')
    frames, fit = encode(samples, args.node, out, profile=profile,
        start_tick=round(before*50), ticks=ticks, noise_fit=getattr(args,'noise_fit','chip'),
        mixer_search=getattr(args,'mixer_search','fast'),chip=getattr(args,'chip','AY-3-8910'),
        dynamics=getattr(args,'dynamics','compact'))
    assert len(frames) == ticks
    packed = b''.join(f.serialize() for f in frames)
    registers = b''.join(frame_registers(f) for f in frames)
    width=fit['register_bytes_per_state']
    packed_name='soundtrack.ay12.gz' if width==14 else 'soundtrack.ay9.gz'
    (out/packed_name).write_bytes(gzip.compress(packed, mtime=0))
    (out/'registers.gz').write_bytes(gzip.compress(registers, mtime=0))
    print(json.dumps(dict(stage='assemble', register_bytes=len(registers))), flush=True)
    disk, metadata = build_disk(registers, title=args.title or source.stem,
                                loop=not args.once, assembly_dir=out/'assembly',register_bytes=width)
    (out/'audio-preview.trd').write_bytes(disk)
    save(out/'player.json', metadata)
    # Ayumi supplies the shared noise generator, chip DAC levels, continuous
    # phases and mono mixing. No original source signal is mixed into its output.
    subprocess.run([str(args.node), str(HERE/'render_ym2149.js'), str(out/'registers.gz'),
                    str(out/'chip.f32'), '50', str(out/'chip-render.json'),str(width),
                    'YM' if fit['target_chip']=='YM2149' else 'AY'], check=True)
    rendered = np.frombuffer((out/'chip.f32').read_bytes(), '<f4').astype(float)
    assert len(rendered) == ticks*882 and np.isfinite(rendered).all()
    original = samples[first:first+ticks*441]
    levels = [float(np.sqrt(np.mean(s*s))) for s in (original, rendered)]
    target = min(.12, *(0.9*r/max(float(np.max(abs(s))), 1e-12)
                       for s, r in zip((original, rendered), levels)))
    if profile == 'auto':
        import pcm_levels
        prepared,_=pcm_levels.process(samples,round(before*50),ticks,dynamics=getattr(args,'dynamics','compact'))
        original=prepared[first:first+ticks*441]
        quality.write_wav(out/'original-preview.wav', original, rate)
        quality.write_wav(out/'ay-preview.wav', rendered*fit['simulation_feedback']['fixed_model_gain'], 44100)
        target = None
    else:
        quality.write_wav(out/'original-preview.wav', original*target/max(levels[0], 1e-12), rate)
        quality.write_wav(out/'ay-preview.wav', rendered*target/max(levels[1], 1e-12), 44100)
    downsampled = np.frombuffer(subprocess.run([str(args.ffmpeg), '-v', 'error', '-nostdin',
        '-f', 'f32le', '-ar', '44100', '-ac', '1', '-i', str(out/'chip.f32'),
        '-ar', str(rate), '-f', 'f32le', '-'], capture_output=True, check=True).stdout, '<f4').astype(float)
    metrics = quality.compare(quality.features(original, rate, 10, (ticks+4)//5),
                              quality.features(downsampled, rate, 10, (ticks+4)//5))
    stft = spectrogram.compare(spectrogram.features(original), spectrogram.features(downsampled))
    (out/'chip.f32').unlink()
    producers = [*sorted(HERE.glob('*.py')), HERE/'ay-player.asm',
                 HERE/'render_ym2149.js', HERE/'render_noise_candidates.js', HERE/'render_mixer_candidates.js', HERE/'vendor/ayumi-js/ayumi.js']
    with source.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(complete=True, preview_only=True, source=str(source), source_sha256=source_hash,
        title=args.title or source.stem, start_seconds=args.start, requested_duration_seconds=args.duration,
        duration_seconds=duration, duration_grid_seconds=.02, ticks=ticks,
        maximum_duration_seconds=maximum/50, update_rate_hz=50, loop_playback=not args.once,
        analysis_sample_rate_hz=rate, source_mix=downmix['method'],
        profile=profile, sound_quantum_ms=20,
        mode=('automatic tone/noise/mixed AY synthesis' if profile == 'auto' else
              'note-oriented music AY synthesis' if profile == 'music' else
              'unchanged refined movie square-aware AY synthesis'), square_fit=fit,
        noise_ticks=fit.get('noise_ticks',sum(bool(f.noise_period) for f in frames)),
        analysis_context_before_seconds=before,
        analysis_context_after_seconds=(len(samples)-first-ticks*441)/rate,
        packed_bytes=len(packed), register_bytes=len(registers), registers_sha256=sha(registers),
        packed_format='AY12 with hardware-envelope actions' if width==14 else 'AY9 extended six-bit mixer' if profile != 'legacy' else 'AY9 legacy noise-only B',
        preview_model=fit['target_chip']+' Ayumi, three tones, one shared noise generator, equal mono sum',
        target_chip=fit['target_chip'],
        downmix=downmix,dynamics=getattr(args,'dynamics','compact'),
        metrics=metrics, metrics_scope='spectral, pitch-class, loudness and rhythm proxies; not waveform SNR or listening acceptance',
        spectrogram_metrics=stft,
        spectrogram_scope='50..8000 Hz linear bins, global equal RMS, no time warp or pitch alignment; common source-relative -60 dB floor; 20-ms hop',
        equal_rms_preview=target, original_source_not_mixed_into_synthesis=True,
        fixed_preview_calibration=fit.get('simulation_feedback',{}).get('fixed_model_gain'),
        high_rate_pcm_volume_output=False, disk_timing_verified=False, hardware_tested=False,
        producer_sources_sha256_lf={p.relative_to(HERE).as_posix():sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in producers},
        artifacts={p.relative_to(out).as_posix():dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                   for p in sorted(out.rglob('*')) if p.is_file()})
    save(out/'report.json', report)
    if args.fuse:
        print(json.dumps(dict(stage='verify_and_record_fuse', cycles=1 if args.once else 2)), flush=True)
        subprocess.run([sys.executable, str(HERE/'verify_preview.py'), str(out),
                        '--fuse', str(args.fuse), '--record'], check=True)
        report = json.loads((out/'report.json').read_bytes())
    print(json.dumps(dict(complete=True, duration_seconds=duration, metrics=metrics,
                          disk_timing_verified=report['disk_timing_verified'], output=str(out))), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--start', type=float, default=0.)
    parser.add_argument('--duration', type=float, help='retain the interval that fits RAM: auto at most 140.4 s, music/legacy 178.68 s')
    parser.add_argument('--title', help='short player-screen title; defaults to the input filename')
    parser.add_argument('--once', action='store_true', help='stop and mute at EOF instead of looping')
    parser.add_argument('--profile', choices=('legacy', 'music', 'auto'), default='auto',
                        help='auto fits tone/noise/mixed modes at 50 Hz; music retains the preceding chip-noise fit; legacy reproduces the original analyser')
    parser.add_argument('--noise-fit',choices=('chip','heuristic'),default='chip',
                        help='music profile only: fit noise colour with Ayumi (default), or reproduce the preceding heuristic')
    parser.add_argument('--mixer-search',choices=('fast','full'),default='fast',
                        help='auto: 20 analytic candidates (default) or 374 reference candidates; both use chip feedback')
    parser.add_argument('--chip',choices=('AY-3-8910','YM2149'),default='AY-3-8910',
                        help='physical DAC/envelope model for all fitting and previews (default: AY-3-8910)')
    parser.add_argument('--dynamics',choices=('compact','original'),default='compact',
                        help='auto: smooth bounded compression (default) or preserve original dynamics')
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    parser.add_argument('--node', default=shutil.which('node'))
    parser.add_argument('--fuse', type=Path, help='also verify every output field and capture normal Fuse audio')
    args = parser.parse_args()
    if not math.isfinite(args.start) or args.start < 0 or abs(args.start*50-round(args.start*50)) > 1e-8:
        parser.error('--start must be nonnegative and a multiple of 20 ms')
    if args.duration is not None and (not math.isfinite(args.duration) or args.duration < .02):
        parser.error('--duration must be at least 20 ms')
    if not args.ffmpeg or not args.node:
        parser.error('FFmpeg and Node.js are required; pass --ffmpeg and --node if not on PATH')
    convert(args)


if __name__ == '__main__':
    main()
