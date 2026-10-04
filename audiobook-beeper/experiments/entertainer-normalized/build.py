"""Normalize one shared Entertainer excerpt and build both verified PDM disks.

All gain/limiting happens before the shared PCM8 reference is made. Neither
codec may peak-normalize it again. Quality below 20 dB remains explicit.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import wave

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT/'audiobook-beeper/experiments/ima-3bit-entertainer/original.ogg'
SOURCE_SHA256 = '08dc5241de419edf9693ad20797389cb735d9b6fc06bfb6936568bb707f13077'
SAMPLES = 186752  # 23.344 s of music + 128 guard = full IMA4 RAM capacity.


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def write_wav(path, pcm):
    with wave.open(str(path), 'wb') as wav:
        wav.setparams((1, 1, 8000, 0, 'NONE', 'not compressed'))
        wav.writeframes(pcm.tobytes())


def normalize(out, ffmpeg):
    assert digest(SOURCE) == SOURCE_SHA256
    run = subprocess.run([ffmpeg, '-v', 'error', '-nostdin', '-i', str(SOURCE),
                          '-t', str(SAMPLES/8000), '-ac', '1', '-ar', '8000',
                          '-f', 'f32le', '-'], capture_output=True, check=True)
    original = np.frombuffer(run.stdout, '<f4').copy()
    assert len(original) == SAMPLES and np.all(np.isfinite(original))
    base = [ffmpeg, '-v', 'info', '-nostdin', '-f', 'f32le', '-ar', '8000', '-ac', '1', '-i', '-']
    target = 'loudnorm=I=-18:TP=-2:LRA=11:print_format=json'

    def process(samples, options, name, render=False):
        command = base+['-af', options]
        command += ['-ar', '8000', '-f', 'f32le', '-'] if render else ['-f', 'null', '-']
        result = subprocess.run(command, input=np.asarray(samples, '<f4').tobytes(),
                                capture_output=True, check=True)
        log = result.stderr.decode('utf-8', errors='replace')
        (out/(name+'.log')).write_text(log, encoding='utf-8')
        start, end = log.rfind('{'), log.rfind('}')
        if start < 0:raise ValueError('Missing FFmpeg loudness measurement')
        return result.stdout, json.loads(log[start:end+1])

    _, measured = process(original, target, 'pass1')
    options = target+':linear=true'
    for parameter, key in (('measured_I', 'input_i'), ('measured_TP', 'input_tp'),
                           ('measured_LRA', 'input_lra'), ('measured_thresh', 'input_thresh'),
                           ('offset', 'target_offset')):
        options += f':{parameter}={measured[key]}'
    data, second = process(original, options, 'pass2', render=True)
    normalized = np.frombuffer(data, '<f4').astype(float)
    assert len(normalized) == SAMPLES and np.all(np.isfinite(normalized))
    # The established encoder's headroom is retained even after resampling.
    peak = float(np.max(abs(normalized)))
    safety_gain = min(1., (109/128)/peak) if peak else 1.
    normalized *= safety_gain
    normalized[:80] *= np.linspace(0, 1, 80)
    normalized[-80:] *= np.linspace(1, 0, 80)
    rounded = np.rint(normalized*128+128)
    assert rounded.min() > 0 and rounded.max() < 255
    prepared = np.full(SAMPLES+128, 128, dtype='u1')
    prepared[:SAMPLES] = rounded.astype('u1')
    write_wav(out/'normalized-source.wav', prepared)
    _, final = process((prepared[:SAMPLES].astype(float)-128)/128, target, 'final-pcm8')
    report = dict(source=str(SOURCE.relative_to(ROOT)), source_sha256=SOURCE_SHA256,
                  retained_seconds=SAMPLES/8000, prepared_seconds=len(prepared)/8000,
                  retained_samples=SAMPLES, prepared_samples=len(prepared),
                  target_lufs=-18, target_true_peak_db=-2, target_lra=11,
                  before=measured, normalization=second, final_pcm8=final,
                  safety_gain=safety_gain, edge_fades_samples=80, silent_guard_samples=128,
                  clipped_pcm_samples=0, pcm_min=int(prepared.min()), pcm_max=int(prepared.max()),
                  pcm_sha256=hashlib.sha256(prepared.tobytes()).hexdigest(),
                  prepared_wav_sha256=digest(out/'normalized-source.wav'),
                  ffmpeg_sha256=digest(Path(ffmpeg)), builder_sha256=digest(Path(__file__)))
    save(out/'normalization.json', report)
    print(json.dumps(dict(stage='normalized', **report)), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--ffmpeg', required=True)
    parser.add_argument('--fuse', required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = normalize(out, args.ffmpeg)
    save(out/'build-status.json', dict(complete=False, normalization=report, codecs={}))
    records = {}
    for codec in ('ima3', 'ima4'):
        command = [sys.executable, str(ROOT/'audiobook-beeper/convert_audio.py'),
                   str(out/'normalized-source.wav'), '--codec', codec,
                   '--prepared-pcm', '--output', str(out/codec),
                   '--ffmpeg', args.ffmpeg, '--fuse', args.fuse]
        if codec == 'ima3':command += ['--disk-mode', 'preview']
        print(json.dumps(dict(stage='convert', codec=codec)), flush=True)
        started = time.monotonic()
        with (out/(codec+'.log')).open('wb') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
        status_path = out/codec/'report.json'
        if result.returncode not in (0, 2) or not status_path.is_file():
            raise RuntimeError(f'{codec} failed; inspect {out/(codec+".log")}')
        status = json.loads(status_path.read_bytes())
        assert status['complete']
        if result.returncode == 2:
            assert codec == 'ima3' and status['quality_gate_passed'] is False
        with wave.open(str(out/codec/'source-preview.wav'), 'rb') as wav:
            reference = wav.readframes(wav.getnframes())
        assert hashlib.sha256(reference).hexdigest() == report['pcm_sha256']
        records[codec] = dict(exit_code=result.returncode, elapsed_seconds=time.monotonic()-started,
                              same_normalized_reference=True, report=codec+'/report.json')
        save(out/'build-status.json', dict(complete=len(records)==2, normalization=report, codecs=records))
        print(json.dumps(dict(stage='built', codec=codec, **records[codec])), flush=True)


if __name__ == '__main__':main()
