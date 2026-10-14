"""Suppress source-unsupported high partials with real sine-carrier OPL2 writes.

The original experiment and generic exporter remain byte reproducible. This
opt-in experiment changes the silent initial operator setup and carrier TL
targets; the fixed playback filter/gain and all frequencies remain unchanged.
"""
import argparse
import gzip
import json
from pathlib import Path
import struct
import sys
import time
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
sys.path.insert(0, str(CORE / 'analysis/ym3812_clicks'))
import experimental_ym3812 as opl
import experimental_six_voice as six
import quality
from analyze import diagnostic, plot, read
from compare import register_perturbations
from simulation_refine import spectra, tick_rms
from support import save
from test_experimental_ym3812 import audit as original_audit


def pure_vgm(controls):
    """Use additive connection and a non-attacking modulator envelope.

    C0=1 removes phase modulation independently of modulator attenuation.
    AR=0 on the reset modulator leaves it at the silent envelope level. Only
    the real sine carrier sounds; waveform/DAC quantization remains native.
    Change silent initial writes only, retaining every timed bus slot.
    """
    data, writes = opl.smooth_vgm(controls)
    altered = bytearray(data)
    pos = 256; changed = set()
    mod_ar = {0x60 + int(mod) for mod in opl.MOD_OFFSETS}
    connections = set(range(0xc0, 0xc9))
    while altered[pos] == 0x5a:
        address = altered[pos + 1]
        if address in mod_ar | connections:
            altered[pos + 2] = 0 if address in mod_ar else 1
            changed.add(address)
        pos += 3
    assert changed == mod_ar | connections
    return bytes(altered), writes


def audit(data, controls):
    """Independently verify the added operator settings and original targets."""
    canonical = bytearray(data); pos = 256; elapsed = 0; found = set()
    mod_ar = {0x60 + int(mod) for mod in opl.MOD_OFFSETS}
    connections = set(range(0xc0, 0xc9))
    while pos < len(data):
        command = data[pos]; pos += 1
        if command == 0x66: break
        if command == 0x5a:
            address, value = data[pos:pos + 2]
            if address in mod_ar | connections:
                assert elapsed == 0 and address not in found
                assert value == (0 if address in mod_ar else 1)
                found.add(address)
                # Restore only independently checked initial bytes for the
                # pre-existing target/timing auditor. All timed writes remain.
                canonical[pos + 1] = 0xf0 if address in mod_ar else 0
            pos += 2
        elif command == 0x61:
            elapsed += struct.unpack_from('<H', data, pos)[0]; pos += 2
        elif 0x70 <= command <= 0x7f: elapsed += (command & 15) + 1
        else: raise AssertionError('non-OPL command')
    assert found == mod_ar | connections
    return dict(original_audit(bytes(canonical), controls), additive_sine_and_silent_modulator=True)


def cap_high_controls(source, observed, controls, strength):
    """Attenuate only high carriers exceeding the local source spectrum.

    Compare both aligned512/2048 Hann windows around each actual carrier.
    A +/-2-bin maximum tolerates pitch quantization and leakage. Require the
    excess on both scales; allow1.5 dB. Blend in from1800 to3000 Hz and cap
    correction at12 dB. Raise real TL codes only; never change low tones,
    pitch, key state, source gain or playback filtering.
    """
    count = opl.validate(controls)
    if len(source) != count * 441 or len(observed) != len(source): raise ValueError('aligned whole fields required')
    if not np.isfinite(strength) or not 0 <= strength <= 1: raise ValueError('strength must be0..1')
    if not np.isfinite(source).all() or not np.isfinite(observed).all(): raise ValueError('nonfinite audio')
    if not np.isin(controls['patch'], [0, 14]).all(): raise ValueError('sine targets required')
    multiplier = np.array([p['car_mul'] for p in opl.PATCHES])[controls['patch']]
    frequency = controls['fnum'] * 2. ** controls['block'] * multiplier * opl.NATIVE_RATE / 2 ** 20
    excess = []
    for size in (512, 2048):
        a = spectra(source, np.arange(count), size)
        b = spectra(observed, np.arange(count), size)
        indices = np.rint(frequency * size * 2 / opl.RATE).astype(int)[..., None] + np.arange(-2, 3)
        indices = np.clip(indices, 0, a.shape[1] - 1)
        wanted = a[np.arange(count)[:, None, None], indices].max(axis=2)
        actual = b[np.arange(count)[:, None, None], indices].max(axis=2)
        floor = np.maximum(a.max(axis=1)[:, None] * .003, 1e-12)
        excess.append(np.maximum(20 * np.log10(np.maximum(actual, floor) / np.maximum(wanted, floor)) - 1.5, 0))
    correction = np.minimum(excess[0], excess[1])
    correction *= np.clip((frequency - 1800) / 1200, 0, 1) * strength
    steps = np.rint(np.minimum(correction, 12) / .75).astype(int)
    steps[controls['level'] == 64] = 0
    result = {key: value.copy() for key, value in controls.items()}
    result['level'] = np.where(controls['level'] == 64, 64,
                               np.minimum(controls['level'].astype(int) + steps, 63)).astype(np.uint8)
    return result


def high_stats(source, observed):
    """Measure extra/missing bin power; band totals alone hide added tones."""
    count = len(source) // 441; result = {}; worst = np.zeros(count)
    active = tick_rms(source) > max(float(tick_rms(source).max()) * .001, 1e-9)
    for size in (512, 2048, 8192):
        hz = np.fft.rfftfreq(size * 2, 1 / opl.RATE)
        bands = {'1800-8000': (1800, 8000), '4000-8000': (4000, 8000)}
        totals = {name: np.zeros(4) for name in bands}; cos = []
        for start in range(0, count, 128):
            ticks = np.arange(start, min(count, start + 128))
            a, b = spectra(source, ticks, size), spectra(observed, ticks, size)
            low = (hz >= 50) & (hz < 1800)
            cosine = (a[:, low] * b[:, low]).sum(axis=1) / np.maximum(np.linalg.norm(a[:, low], axis=1) * np.linalg.norm(b[:, low], axis=1), 1e-20)
            cos.extend(cosine[active[ticks]])
            for name, (lo, hi) in bands.items():
                mask = (hz >= lo) & (hz <= hi)
                wanted, actual = a[:, mask] ** 2, b[:, mask] ** 2
                extra = np.maximum(actual - wanted, 0)
                totals[name] += [wanted.sum(), actual.sum(), extra.sum(), np.maximum(wanted - actual, 0).sum()]
                if size == 2048 and name == '1800-8000': worst[ticks] = extra.sum(axis=1)
        result[str(size)] = dict(low_band_cosine=float(np.mean(cos)), **{
            name: dict(power_ratio=float(values[1] / max(values[0], 1e-20)),
                       extra_power_fraction=float(values[2] / max(values[0], 1e-20)),
                       missing_power_fraction=float(values[3] / max(values[0], 1e-20))) for name, values in totals.items()})
    start = int(np.convolve(worst, np.ones(min(150, count)), 'valid').argmax()) / 50
    return dict(scales=result, worst_extra_interval_seconds=[start, min(start + 3, count / 50)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True); start = time.perf_counter()
    old = HERE / 'evidence'; previous = json.loads((old / 'report.json').read_bytes())
    for name, expected in previous['artifacts_sha256'].items(): assert opl.sha((old / name).read_bytes()) == expected, name
    source = six.read_reference(old / 'reference.wav')
    before = read(old / 'ym3812-preview.wav'); gain = previous['global_playback_gain']
    with np.load(old / 'controls.npz') as saved: original = {key: saved[key] for key in saved.files}
    assert opl.validate(original) == 4500
    guards = dict(extra_2048_reduction_min=.20, high_missing_fraction_increase_max=.04,
                  low_cosine_loss_max=.005, level_mae_increase_max_db=.20)
    baseline = dict(high=high_stats(source, before), diagnostics=previous['trials'][1]['diagnostics'])
    trials = []
    for name, strength in (('pure-sine', 0), ('cap06', .6), ('cap10', 1.)):
        controls = original if strength == 0 else cap_high_controls(source, before, original, strength)
        np.savez_compressed(args.output / (name + '.npz'), **controls)
        data, writes = pure_vgm(controls); checked = audit(data, controls)
        raw, samples, parsed = opl.replay(data)
        assert samples == 3969000 and len(raw) == 4474431 and parsed == writes
        assert not np.any(abs(raw) >= 1)
        audio = opl.playback(raw, samples) * gain
        assert not np.any(abs(audio) >= 1)
        quality.write_wav(args.output / (name + '.wav'), audio, opl.OUT_RATE)
        coded = gzip.compress(data, mtime=0); (args.output / (name + '.vgz')).write_bytes(coded)
        effects, independent = register_perturbations(data, gain); assert np.array_equal(raw, independent)
        observed = read(args.output / (name + '.wav'))
        high = high_stats(source, observed); measured = diagnostic(source, observed)
        tests = {}
        tests['extra_2048'] = high['scales']['2048']['1800-8000']['extra_power_fraction'] <= baseline['high']['scales']['2048']['1800-8000']['extra_power_fraction'] * .8
        tests['all_extra_scales'] = all(high['scales'][s]['1800-8000']['extra_power_fraction'] <= baseline['high']['scales'][s]['1800-8000']['extra_power_fraction'] for s in high['scales'])
        tests['high_missing'] = all(high['scales'][s]['1800-8000']['missing_power_fraction'] <= baseline['high']['scales'][s]['1800-8000']['missing_power_fraction'] + .04 for s in high['scales'])
        tests['low_band'] = all(high['scales'][s]['low_band_cosine'] >= baseline['high']['scales'][s]['low_band_cosine'] - .005 for s in high['scales'])
        tests['levels'] = measured['metrics']['level_mae_db'] <= baseline['diagnostics']['metrics']['level_mae_db'] + .20
        trial = dict(name=name, strength=strength, high=high, diagnostics=measured, admission=tests,
                     admitted=all(tests.values()), writes=writes, vgm_bytes=len(data), vgz_bytes=len(coded),
                     vgm_sha256=opl.sha(data), peak=float(abs(audio).max()), native_clipping_samples=0, clipping_samples=0,
                     changed_level_targets=int(np.sum(controls['level'] != original['level'])),
                     all_frequencies_keys_and_patches_unchanged=True, audit=checked, write_effects=effects,
                     complete_independent_native_replay_exact=True)
        trials.append(trial)
        print(json.dumps(dict(stage='full_overtones_trial', name=name, admitted=trial['admitted'], admission=tests,
                             high_extra=high['scales']['2048']['1800-8000']['extra_power_fraction'])), flush=True)
    eligible = [t for t in trials if t['admitted']]
    selected = min(eligible, key=lambda t: t['high']['scales']['2048']['1800-8000']['extra_power_fraction']) if eligible else None
    if selected:
        name = selected['name']; data = gzip.decompress((args.output / (name + '.vgz')).read_bytes())
        for target, source_name in (('ym3812-preview.wav', name + '.wav'), ('controls.npz', name + '.npz'), ('ym3812.vgz', name + '.vgz')):
            (args.output / target).write_bytes((args.output / source_name).read_bytes())
        (args.output / 'ym3812.vgm').write_bytes(data)
        output = read(args.output / 'ym3812-preview.wav')
        versions = [('Previous YM3812', before), ('Source-supported sine YM3812', output)]
        plot(source, versions, args.output / 'spectrogram-full.png')
        plot(source, versions, args.output / 'spectrogram-detail.png', baseline['high']['worst_extra_interval_seconds'])
        sections = []
        for path in (old / 'ym3812-preview.wav', args.output / 'ym3812-preview.wav'):
            with wave.open(str(path), 'rb') as stream: sections.append(stream.readframes(stream.getnframes()))
        with wave.open(str(args.output / 'before-after.wav'), 'wb') as stream:
            stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed')); stream.writeframes(sections[0] + bytes(88200) + sections[1])
    result = dict(complete=True, date='2026-10-14', fields=4500, seconds=90, selected=selected['name'] if selected else None,
                  previous_report_sha256=opl.sha((old / 'report.json').read_bytes()),
                  source_sha256=opl.sha((old / 'reference.wav').read_bytes()), native_core_sha256=previous['native_core_sha256'],
                  global_playback_gain=gain, output_filter_unchanged=True, source_pcm_in_output=False,
                  baseline=baseline, admission_guards=guards, trials=trials, elapsed_seconds=time.perf_counter() - start,
                  producer_sources_sha256_lf={str(Path(__file__).relative_to(CORE)).replace('\\', '/'): opl.sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n'))},
                  artifacts_sha256={p.name: opl.sha(p.read_bytes()) for p in sorted(args.output.iterdir()) if p.is_file()})
    save(args.output / 'report.json', result)
    print(json.dumps(dict(complete=True, selected=result['selected'], baseline_high_extra=baseline['high']['scales']['2048']['1800-8000']['extra_power_fraction'])), flush=True)


if __name__ == '__main__': main()
