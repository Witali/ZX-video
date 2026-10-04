"""Seven predetermined 50-Hz arrangements, including an exact legacy control."""
from pathlib import Path
import argparse
import gzip
import json
import subprocess
import sys
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE/'analysis/entertainer'))
import ay_fidelity as ay
from ay_format import AyFrame, registers
import music_profile as music
import quality
import spectrogram
from support import save, sha
from probe import decode, onset_proxy, pitch_stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'baseline', 'output', 'ffmpeg', 'node'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    samples = decode(args.ffmpeg, args.input, duration=32.128)
    ticks, rate = 1556, 22050
    original = samples[:ticks*441]
    print('Shared long/short spectral decomposition', flush=True)
    features = music.analyse(samples)
    # Use the identical long-window decomposition for the legacy control.
    ay.decompose = lambda *a, **kw: (features['amplitude'].copy(), features['explained'].copy())
    coarse_ref = quality.features(original, rate, 10, (ticks+4)//5)
    spectral_ref = spectrogram.features(original)
    onsets_ref = onset_proxy(original)
    variants = [
        ('baseline', None),
        ('held_calibrated', {}),
        ('fast_envelopes', dict(envelope_blend=.5)),
        ('transient_noise', dict(noise_policy='transients')),
        ('joint_voices', dict(joint=True)),
        ('seed_full', dict(envelope_blend=.5, noise_policy='transients')),
        ('joint_full', dict(joint=True, envelope_blend=.5, noise_policy='transients'))]
    results = {}
    for name, settings in variants:
        print('Evaluate '+name, flush=True)
        if settings is None:
            p, v, paths, noise, _, metadata = ay.arrange_for_chip(features['magnitude'], features['rms'], rate)
        else:
            p, v, paths, noise, _, metadata = music.arrange(features, **settings)
        p, v, paths, noise = (x[:ticks] for x in (p, v, paths, noise))
        raw = b''.join(registers(AyFrame(tuple(map(int,a)), tuple(map(int,b)), int(c))) for a,b,c in zip(p,v,noise))
        if name == 'baseline':
            assert raw == gzip.decompress((args.baseline/'registers.gz').read_bytes())
        out = args.output/name
        out.mkdir()
        (out/'registers.gz').write_bytes(gzip.compress(raw, mtime=0))
        save(out/'arrangement.json', metadata)
        subprocess.run([str(args.node), str(HERE/'render_ym2149.js'), str(out/'registers.gz'),
                        str(out/'chip.f32'), '50', str(out/'render.json')], check=True)
        audio = np.frombuffer((out/'chip.f32').read_bytes(), '<f4').astype(float)
        rms = max(float(np.sqrt(np.mean(audio*audio))), 1e-12)
        quality.write_wav(out/'preview.wav', audio*min(.1/rms, .9/max(abs(audio))), 44100)
        down = np.frombuffer(subprocess.run([str(args.ffmpeg), '-v','error','-nostdin',
            '-f','f32le','-ar','44100','-ac','1','-i',str(out/'chip.f32'),
            '-ar',str(rate),'-f','f32le','-'], capture_output=True, check=True).stdout, '<f4').astype(float)
        result = dict(parameters=settings, registers_sha256=sha(raw),
            metrics=quality.compare(coarse_ref, quality.features(down,rate,10,(ticks+4)//5)),
            stft=spectrogram.compare(spectral_ref, spectrogram.features(down)),
            onset_20ms=quality.match_onsets(onsets_ref, onset_proxy(down), 2),
            pitch=pitch_stats(p,v,noise,paths), noise_ticks=int(np.count_nonzero(noise)))
        results[name] = result
        save(args.output/'results.partial.json', results)
        print(json.dumps(dict(name=name, **{k: result[k] for k in ('metrics','stft','onset_20ms','noise_ticks')})), flush=True)
        (out/'chip.f32').unlink()
    report = dict(date='2026-10-04', source_sha256=sha(args.input.read_bytes()), ticks=ticks,
        duration_seconds=ticks/50, update_rate_hz=50, baseline_registers_exact=True,
        scope='Complete host renders of seven fixed variants; native/Fuse qualification is separate.',
        spectrogram_method='Linear frequency bins 50..8000 Hz, Hann windows 512/2048/8192, 2x FFT padding, 20-ms hop; global equal RMS; no time warp or frequency alignment. Log MAE uses union support above source-relative -60 dB.',
        variants=results, sources_sha256_lf={p.relative_to(HERE).as_posix():sha(p.read_bytes().replace(b'\r\n',b'\n'))
            for p in [Path(__file__), HERE/'music_profile.py', HERE/'spectrogram.py', HERE/'ay_square_fit.py']})
    save(args.output/'results.json', report)


if __name__ == '__main__':
    main()
