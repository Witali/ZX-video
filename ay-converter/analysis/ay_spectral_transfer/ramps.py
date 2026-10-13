"""Full timed-command transition diagnostics and separate subframe DAC probe."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys
import wave
import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE)); sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
import timed_ay
import quality
from analyze import read, diagnostic, plot
from support import sha, save


def replay(data, node, folder):
    folder.mkdir(parents=True, exist_ok=True)
    packed = gzip.compress(data, mtime=0); (folder / 'commands.gz').write_bytes(packed)
    subprocess.run([node, str(CORE / 'render_timed_ay.js'), str(folder / 'commands.gz'),
                    str(folder / 'audio.f32'), str(folder / 'steps.json')], check=True)
    audio = np.fromfile(folder / 'audio.f32', '<f4').astype(float)
    return audio, json.loads((folder / 'steps.json').read_bytes()), len(packed)


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--node', default='node'); args = parser.parse_args()
    if args.output.exists(): raise ValueError('new output directory required')
    args.output.mkdir(parents=True); old = CORE / 'analysis/o_henry/evidence/compact30'
    source = read(old / 'original-preview.wav'); gain = json.loads((old / 'report.json').read_bytes())['fixed_preview_calibration']
    raw = gzip.decompress((old / 'registers.gz').read_bytes()); results = []
    settings = [('timed-baseline', raw, 14, 0.)]
    # Diagnose the actual DAC jumps of the stage2/3 choices on the same
    # serial bus model, excluding ordinary oscillator fronts.
    for name, relative in (('bands', 'stage2/bands512'), ('continuity', 'stage3/continuity0.1')):
        registers = gzip.decompress((HERE / 'evidence' / relative / 'registers.gz').read_bytes())
        settings.append((name, registers, 11, 0.))
    settings += [(f'ramp{ms:g}', raw, 14, ms) for ms in (2., 4., 8.)]
    for name, registers, width, ms in settings:
        folder = args.output / name; data = timed_ay.stream(registers, width, ms)
        audited = timed_ay.audit(data, registers); audio, steps, size = replay(data, args.node, folder)
        second, *_ = replay(data, args.node, folder / 'independent-replay')
        assert np.array_equal(audio, second) and len(audio) == 1323000
        audio *= gain; quality.write_wav(folder / 'ay-preview.wav', audio, 44100)
        details = diagnostic(source, read(folder / 'ay-preview.wav'))
        entry = dict(name=name, gain=gain, transition_ms=ms, register_bytes=width, commands_gzip_bytes=size,
                     commands_sha256=sha(data), registers_sha256=sha(registers), all_1500_states=audited,
                     steps=steps, diagnostics=details, peak=float(abs(audio).max()),
                     clipping_samples=int((abs(audio) >= 1).sum()), replay_exact=True,
                     wave_sha256=sha((folder / 'ay-preview.wav').read_bytes()))
        results.append(entry); save(folder / 'report.json', entry)
        print(json.dumps(dict(name=name, objective=details['metrics']['objective_db'],
                             level_mae=details['metrics']['level_mae_db'], dac_steps=steps['instant_dac_step_squared_sum'],
                             writes=steps['writes'], size=size)), flush=True)
    baseline = results[0]; ramps = results[3:]
    # Additional scheduling is justified only by a substantial reduction of
    # command steps while retaining spectral/dynamic guards. Do not infer
    # subjective click elimination or qualify a nonexistent native scheduler.
    for entry in ramps:
        entry['dac_step_energy_reduction'] = 1 - entry['steps']['instant_dac_step_squared_sum'] / baseline['steps']['instant_dac_step_squared_sum']
        good = entry['clipping_samples'] == 0 and entry['dac_step_energy_reduction'] >= .25
        good &= entry['diagnostics']['metrics']['objective_db'] <= baseline['diagnostics']['metrics']['objective_db'] + .15
        good &= entry['diagnostics']['metrics']['level_mae_db'] <= baseline['diagnostics']['metrics']['level_mae_db'] + .2
        good &= all(entry['diagnostics']['unpooled'][s]['magnitude_cosine'] >= baseline['diagnostics']['unpooled'][s]['magnitude_cosine'] - .005 for s in ('512', '2048', '8192'))
        entry['transition_probe_eligible'] = bool(good)
    eligible = [r for r in ramps if r['transition_probe_eligible']]
    selected = min(eligible, key=lambda t: t['diagnostics']['metrics']['objective_db']) if eligible else baseline
    versions = [('Serial current AY baseline', read(args.output / baseline['name'] / 'ay-preview.wav')),
                ('Nominal4-ms real DAC ramp', read(args.output / 'ramp4/ay-preview.wav'))]
    plot(source, versions, args.output / 'spectrogram-full.png')
    plot(source, versions, args.output / 'spectrogram-detail.png', baseline['diagnostics']['worst_interval_seconds'])
    segments = []
    for name in (baseline['name'], 'ramp4'):
        with wave.open(str(args.output / name / 'ay-preview.wav'), 'rb') as stream:
            assert stream.getnframes() == 1323000; segments.append(stream.readframes(1323000))
    pcm = segments[0] + bytes(88200) + segments[1]
    with wave.open(str(args.output / 'before-after.wav'), 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(44100); stream.writeframes(pcm)
    save(args.output / 'report.json', dict(complete=True, date='2026-10-13', fields=1500, seconds=30,
        selected_transition_probe=selected['name'], selected_50hz_encoder='baseline', trials=results,
        serial_bus_spacing_us=1e6/44100, exact21_99us_z80_bus_model=False,
        source_reference_sha256=sha((old / 'original-preview.wav').read_bytes()), same_calibration=True,
        physical_chip_fuse_native_scheduler_verified=False, no_source_pcm_in_synthesis=True,
        limitations='Model-only commands on nominal50-Hz frames; serial writes approximated at44.1 kHz. Shared-envelope/routing changes excluded from ramps. No native player consumes AYE1. No perceptual click elimination claim.',
        producers_sha256_lf={p.name: sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in
            (CORE / 'timed_ay.py', CORE / 'render_timed_ay.js', Path(__file__))}))


if __name__ == '__main__': main()
