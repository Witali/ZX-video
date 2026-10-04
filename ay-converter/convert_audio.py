"""Audio -> movie-style AY50 synthesis -> looping TRD and listening previews.

Offers the preserved movie analyser and an optional music profile. This is a three-voice arrangement,
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
import ay_fidelity as ay
from ay_format import AyFrame, registers as frame_registers
import quality
import spectrogram
from support import save, sha
from music_player import build_disk, MAX_TICKS


def convert(args):
    source = args.input.resolve(strict=True)
    out = args.output.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('output must be a new or empty directory')
    rate = 22050
    limit = MAX_TICKS/50 if args.duration is None else min(args.duration, MAX_TICKS/50)
    before = min(args.start, 1.)
    command = [str(args.ffmpeg), '-v', 'error', '-nostdin', '-ss', str(args.start-before),
               '-i', str(source), '-t', str(limit+before+1), '-map', '0:a:0',
               '-vn', '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']
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
    count = (len(samples)+440)//441
    profile = getattr(args, 'profile', 'legacy')
    if profile == 'music':
        import music_profile
        periods, volumes, notes, noise, explained, fit = music_profile.convert(samples, rate)
    else:
        magnitude, rms = ay.spectra(samples, rate, 50, count)
        periods, volumes, notes, noise, explained, fit = ay.arrange_for_chip(magnitude, rms, rate)
    lo = round(before*50)
    mixers = fit.pop('mixers', [None]*len(periods))
    component_tracks = fit.pop('component_tracks', None)
    if component_tracks is not None:
        shares = fit.pop('noise_shares')
        carriers = fit.pop('noise_carriers')
        base_volumes = fit.pop('base_tone_volumes')
        states = [dict(tick=i-lo, component_ids=component_tracks[i],
                       periods=list(map(int,periods[i])), volumes=list(map(int,volumes[i])),
                       tone_volumes=base_volumes[i], mixer=int(mixers[i]),
                       noise_period=int(noise[i]), noise_share=float(shares[i]),
                       noise_channel=int(carriers[i])) for i in range(lo,lo+ticks)]
        (out/'channel-states.json.gz').write_bytes(gzip.compress(json.dumps(dict(
            quantum_ms=20,update_rate_hz=50,states=states),separators=(',',':')).encode(),mtime=0))
        fit['channel_states_file'] = 'channel-states.json.gz'
        fit['analysis_context_component_count'] = fit['component_count']
        fit['component_count'] = len({track for state in states for track in state['component_ids'] if track})
        fit['noise_ticks'] = sum(bool(state['noise_period']) for state in states)
        fit['tone_plus_noise_ticks'] = sum(bool(state['noise_period'] and state['tone_volumes'][state['noise_channel']]) for state in states)
        fit['noise_only_ticks'] = fit['noise_ticks']-fit['tone_plus_noise_ticks']
    if profile == 'music':
        # Analysis includes context; exported note intervals refer only to the
        # selected excerpt, with integer ticks and exclusive end boundaries.
        events = []
        for event in fit.pop('note_events'):
            start, end = max(lo, event['start_tick']), min(lo+ticks, event['end_tick'])
            if start < end:
                events.append(dict(event, start_tick=start-lo, end_tick=end-lo))
        save(out/'note-events.json', dict(update_rate_hz=50, quantum_ms=20,
             duration_ticks=ticks, end_tick_exclusive=True, estimated_not_ground_truth=True, events=events))
        fit['note_events_file'] = 'note-events.json'
    frames = [AyFrame(tuple(map(int,p)),tuple(map(int,v)),int(n),None if m is None else int(m))
              for p,v,n,m in zip(periods[lo:lo+ticks],volumes[lo:lo+ticks],noise[lo:lo+ticks],mixers[lo:lo+ticks])]
    assert len(frames) == ticks
    packed = b''.join(f.serialize() for f in frames)
    registers = b''.join(frame_registers(f) for f in frames)
    (out/'soundtrack.ay9.gz').write_bytes(gzip.compress(packed, mtime=0))
    (out/'registers.gz').write_bytes(gzip.compress(registers, mtime=0))
    print(json.dumps(dict(stage='assemble', register_bytes=len(registers))), flush=True)
    disk, metadata = build_disk(registers, title=args.title or source.stem,
                                loop=not args.once, assembly_dir=out/'assembly')
    (out/'audio-preview.trd').write_bytes(disk)
    save(out/'player.json', metadata)
    # Ayumi supplies the shared noise generator, chip DAC levels, continuous
    # phases and mono mixing. No original source signal is mixed into its output.
    subprocess.run([str(args.node), str(HERE/'render_ym2149.js'), str(out/'registers.gz'),
                    str(out/'chip.f32'), '50', str(out/'chip-render.json')], check=True)
    rendered = np.frombuffer((out/'chip.f32').read_bytes(), '<f4').astype(float)
    assert len(rendered) == ticks*882 and np.isfinite(rendered).all()
    original = samples[first:first+ticks*441]
    levels = [float(np.sqrt(np.mean(s*s))) for s in (original, rendered)]
    target = min(.12, *(0.9*r/max(float(np.max(abs(s))), 1e-12)
                       for s, r in zip((original, rendered), levels)))
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
                 HERE/'render_ym2149.js', HERE/'vendor/ayumi-js/ayumi.js']
    with source.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(complete=True, preview_only=True, source=str(source), source_sha256=source_hash,
        title=args.title or source.stem, start_seconds=args.start, requested_duration_seconds=args.duration,
        duration_seconds=duration, duration_grid_seconds=.02, ticks=ticks,
        maximum_duration_seconds=MAX_TICKS/50, update_rate_hz=50, loop_playback=not args.once,
        analysis_sample_rate_hz=rate, source_mix='FFmpeg mono downmix',
        profile=profile, sound_quantum_ms=20,
        mode='note-oriented music AY synthesis' if profile == 'music' else 'unchanged refined movie square-aware AY synthesis', square_fit=fit,
        noise_ticks=sum(bool(f.noise_period) for f in frames),
        analysis_context_before_seconds=before,
        analysis_context_after_seconds=(len(samples)-first-ticks*441)/rate,
        packed_bytes=len(packed), register_bytes=len(registers), registers_sha256=sha(registers),
        packed_format='AY9 extended six-bit mixer' if component_tracks is not None else 'AY9 legacy noise-only B',
        preview_model='YM2149 Ayumi, three tones, one shared noise generator, equal mono sum',
        metrics=metrics, metrics_scope='spectral, pitch-class, loudness and rhythm proxies; not waveform SNR or listening acceptance',
        spectrogram_metrics=stft,
        spectrogram_scope='50..8000 Hz linear bins, global equal RMS, no time warp or pitch alignment; common source-relative -60 dB floor; 20-ms hop',
        equal_rms_preview=target, original_source_not_mixed_into_synthesis=True,
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
    parser.add_argument('--duration', type=float, help='retain the initial interval that fits RAM, at most 178.68 s')
    parser.add_argument('--title', help='short player-screen title; defaults to the input filename')
    parser.add_argument('--once', action='store_true', help='stop and mute at EOF instead of looping')
    parser.add_argument('--profile', choices=('legacy', 'music'), default='legacy',
                        help='legacy preserves the original converter; music tracks dominant tones on persistent channels and mixes detected noise at 50 Hz')
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
