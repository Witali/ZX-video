"""Reproduce bounded mode/level comparisons on the maintained recordings."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import numpy as np

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE))
from engine import encode
from ay_format import registers
import mixer_fit
import noise_colour
import quality
import spectrogram
import spectral_patterns
from music_player import build_disk
from verify_preview import extract_player, native_check


def sha(data):
    return hashlib.sha256(data).hexdigest()


def decode(ffmpeg, source, start, duration):
    return np.frombuffer(subprocess.check_output([str(ffmpeg), '-v', 'error', '-nostdin',
        '-ss', str(start), '-t', str(duration), '-i', str(source), '-ac', '1',
        '-ar', '22050', '-f', 'f32le', '-']), '<f4').astype(float)


def render(node, output, raw):
    (output/'registers.gz').write_bytes(gzip.compress(raw, mtime=0))
    subprocess.run([str(node), str(HERE/'render_ym2149.js'), str(output/'registers.gz'),
                    str(output/'chip.f32'), '50', str(output/'chip-render.json')], check=True)
    samples = noise_colour.downsample(np.fromfile(output/'chip.f32', '<f4').astype(float))
    (output/'chip.f32').unlink()
    return samples


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--node', required=True)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--only', nargs='*')
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = []
    music = args.source_root/'audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg'
    speech_report = args.source_root/'ay-converter/analysis/o_henry/evidence/release/report.json'
    speech = Path(json.loads(speech_report.read_bytes())['source'])
    cases.extend([('entertainer', music, 0), ('o-henry', speech, 8)])
    for start in (60, 170, 430):
        cases.append((f'movie-{start}', args.source_root/f'toolkit/ay_square_fit_evidence/{start}s/analysis.npz', start))
    report_path = args.output/'results.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else dict(
        date='2026-10-13', baseline_commit='3002f6a7', duration_per_case_seconds=8,
        update_rate_hz=50, quantum_ms=20, cases={},
        scope='Complete bounded excerpts and native two-loop register checks; not full-film timing, physical hardware or perceptual acceptance.')
    for name, source, start in cases:
        if args.only and name not in args.only:
            continue
        if source.suffix == '.npz':
            with np.load(source) as cached:
                samples = cached['pcm'].astype(float)
            lo = 50
        else:
            before = min(1, start)
            samples = decode(args.ffmpeg, source, start-before, 9+before)
            lo = round(before*50)
        out = args.output/name
        out.mkdir(exist_ok=True)
        np.savez_compressed(out/'input.npz', pcm=samples.astype('<f4'), start_tick=lo, ticks=400)
        original = samples[lo*441:(lo+400)*441]
        if len(original) != 400*441:
            raise ValueError('incomplete source excerpt')
        reference = spectrogram.features(original)
        case = dict(source=str(source), source_sha256=sha(source.read_bytes()),
                    source_start_seconds=start, source_pcm_sha256=sha(samples.astype('<f4').tobytes()),
                    source_context_start_tick=lo, duration_seconds=8, ticks=400, variants={})
        signals = {'original': original}
        for profile in ('legacy', 'music', 'auto'):
            directory = out/profile
            directory.mkdir(exist_ok=True)
            spectral_patterns.reset()
            begin = time.perf_counter()
            frames, fit = encode(samples, args.node, directory, profile=profile, start_tick=lo, ticks=400)
            elapsed = time.perf_counter()-begin
            packed = b''.join(f.serialize() for f in frames)
            raw = b''.join(registers(f) for f in frames)
            (directory/'soundtrack.ay9.gz').write_bytes(gzip.compress(packed, mtime=0))
            (directory/'analysis.json').write_text(json.dumps(fit, indent=2)+'\n', encoding='utf-8')
            audio = render(args.node, directory, raw)
            signals[profile] = audio
            measures = spectrogram.compare(reference, spectrogram.features(audio))
            record = dict(stft=measures, encode_seconds=elapsed,
                          register_sha256=sha(raw), modes=mixer_fit.mode_counts(np.frombuffer(raw,np.uint8).reshape(-1,11)),
                          spectral_pattern_cache=fit['spectral_pattern_cache'])
            if profile == 'auto':
                disk, meta = build_disk(raw, title=name, assembly_dir=directory/'assembly')
                (directory/'audio-preview.trd').write_bytes(disk)
                (directory/'player.json').write_text(json.dumps(meta, indent=2)+'\n', encoding='utf-8')
                verification = native_check(extract_player(disk), meta, raw)
                record['native'] = verification
                record['mixer_fit'] = fit['automatic_mixer_fit']
                (directory/'native.json').write_text(json.dumps(verification, indent=2)+'\n', encoding='utf-8')
            case['variants'][profile] = record
            print(json.dumps(dict(case=name, profile=profile, seconds=elapsed,
                log_mae={k:v['log_magnitude_mae_db'] for k,v in measures.items()}, modes=record['modes'])), flush=True)
        rms = {k:float(np.sqrt(np.mean(v*v))) for k,v in signals.items()}
        target = min(.1, *(.9*rms[k]/max(float(np.max(abs(v))),1e-12) for k,v in signals.items()))
        for name_signal, audio in signals.items():
            quality.write_wav(out/f'{name_signal}.wav', audio*target/max(rms[name_signal],1e-12), 22050)
        case['equal_rms_preview'] = target
        report['cases'][name] = case
        report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    report['complete_requested_cases'] = len(report['cases']) == 5
    report_path.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
