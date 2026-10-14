"""Same-target YM3812 transition ablations, full replays and register diagnostics."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import wave

import numpy as np
import ymfm

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
sys.path.insert(0, str(CORE / 'analysis/six_voice_clicks'))
import experimental_ym3812 as opl
import quality
from analyze import read, diagnostic, plot
from probe import artifacts
from test_experimental_ym3812 import audit

GAIN = 2.3357702813587116


def register_perturbations(data, gain):
    """Compare each write with a frozen-register counterfactual at identical state.

    Clone the complete chip state before a timed write and generate one native
    sample both with and without that write. This isolates its immediate effect
    from the ordinary oscillator slope. It includes legitimate pitch/envelope
    changes, quantization and phase dependence: it is not a perceptual click
    score. Sum squared perturbations rather than average over a changing write
    count, and replay the real continuous stream independently alongside it.
    """
    chip = ymfm.YM3812(clock=opl.CLOCK); chip.reset()
    twin = ymfm.YM3812(clock=opl.CLOCK)
    pos = 0x100; time = native = 0; events = []; chunks = []
    while pos < len(data):
        op = data[pos]; pos += 1
        if op == 0x66: break
        if op == 0x5a:
            address, value = data[pos:pos + 2]; pos += 2
            if time:
                state = chip.save_state(); twin.load_state(state)
                before = opl.chip_audio(twin, 1)[0]
                twin.load_state(state); opl.register(twin, address, value)
                after = opl.chip_audio(twin, 1)[0]
                events.append((time, address, (after - before) * gain))
            opl.register(chip, address, value); continue
        if op == 0x61:
            duration = struct.unpack_from('<H', data, pos)[0]; pos += 2
        elif 0x70 <= op <= 0x7f: duration = (op & 15) + 1
        else: raise ValueError('non-register/wait command')
        time += duration; target = time * opl.CLOCK // (72 * opl.OUT_RATE)
        if target > native: chunks.append(opl.chip_audio(chip, target - native))
        native = target
    events = np.array(events)
    carrier = np.isin(events[:, 1], 0x43 + opl.MOD_OFFSETS)
    def measure(mask):
        values = events[mask, 2]
        return dict(events=len(values), sum_squared_sample_perturbation=float(values @ values),
                    maximum=float(abs(values).max()), p99=float(np.percentile(abs(values), 99)))
    last = np.zeros(time // 882)
    for when, address, value in events: last[int(when) // 882] = max(last[int(when) // 882], when % 882 + 2)
    top = np.argsort(abs(events[:, 2]))[-12:][::-1]
    result = dict(all=measure(np.ones(len(events), bool)), carrier_tl=measure(carrier), other=measure(~carrier),
                  last_bus_slot_ms_max=float(last.max() / 44.1),
                  last_bus_slot_ms_p95=float(np.percentile(last, 95) / 44.1),
                  top=[dict(seconds=float(events[i, 0] / 44100), register=int(events[i, 1]),
                            sample_perturbation=float(events[i, 2])) for i in top])
    return result, np.concatenate(chunks)


def phase_plot(entries, path):
    """Average derivative energy by frame phase, with one shared absolute scale."""
    from PIL import Image, ImageDraw, ImageFont
    image = Image.new('RGB', (1250, 540), 'white'); draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 18)
    left, top, width, height = 100, 85, 1080, 350
    values = [np.convolve(np.array(e['phase_derivative_power']), np.ones(22) / 22, 'same') for e in entries]
    peak = max(float(v.max()) for v in values) * 1.05
    draw.text((left, 20), 'Derivative power averaged over 1499 frames (0.5-ms moving average)', font=font, fill='black')
    for ms in range(0, 21, 2):
        x = left + round(width * ms / 20); draw.line((x, top, x, top + height), fill='#dddddd')
        draw.text((x - 10, top + height + 12), str(ms), font=font, fill='black')
    for fraction in (0, .25, .5, .75, 1):
        y = top + height - round(height * fraction); draw.line((left, y, left + width, y), fill='#dddddd')
        draw.text((4, y - 10), f'{peak * fraction:.5f}', font=font, fill='black')
    for index, (entry, value) in enumerate(zip(entries, values)):
        colour = ('#c64132', '#1a718e')[index]
        points = [(left + round(width * i / 882), top + height - round(height * p / peak)) for i, p in enumerate(value)]
        draw.line(points, fill=colour, width=2)
        draw.text((left + index * 400, 52), entry['name'], font=font, fill=colour)
    draw.text((left, 487), 'Milliseconds after frame boundary; includes ordinary tone energy, not a perceptual click score.', font=font, fill='black')
    image.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True); trials_dir = args.output / 'trials'; trials_dir.mkdir()
    old = CORE / 'analysis/ym3812/evidence'
    with np.load(old / 'selected-controls.npz') as saved: controls = {k: saved[k] for k in saved.files}
    source = read(old / 'reference.wav'); assert opl.validate(controls) == 1500
    trials = []
    settings = [('legacy', None), ('linear4', dict(legacy_ramp=4))]
    settings += [('cosine2', dict(transition_ms=2.)), ('cosine4', dict(transition_ms=4.)),
                 ('cosine8', dict(transition_ms=8.)), ('cosine4-unordered', dict(transition_ms=4., ordered_pitch=False)),
                 ('cosine2x4', dict(transition_ms=2., steps=4)), ('cosine4x4', dict(transition_ms=4., steps=4))]
    with tempfile.TemporaryDirectory(dir=args.output) as temporary:
        for name, options in settings:
            if options is None: data, writes = opl.vgm(controls)
            elif 'legacy_ramp' in options: data, writes = opl.vgm(controls, options['legacy_ramp'])
            else: data, writes = opl.smooth_vgm(controls, **options)
            checked = audit(data, controls); raw, samples, parsed = opl.replay(data)
            assert samples == 1323000 and len(raw) == 1491477 and parsed == writes == checked['writes']
            perturbations, second = register_perturbations(data, GAIN)
            assert np.array_equal(raw, second)
            audio = opl.playback(raw, samples) * GAIN
            assert np.isfinite(audio).all() and abs(audio).max() < 1
            path = Path(temporary) / 'trial.wav'; quality.write_wav(path, audio, 44100)
            if name == 'legacy':
                assert data == (old / 'ym3812.vgm').read_bytes()
                assert path.read_bytes() == (old / 'ym3812-preview.wav').read_bytes()
            packed = gzip.compress(data, mtime=0); assert gzip.decompress(packed) == data
            (trials_dir / (name + '.vgz')).write_bytes(packed)
            delta = np.diff(audio); phase = (delta[:1499 * 882].reshape(-1, 882) ** 2).mean(axis=0)
            entry = dict(name=name, options=options, gain=GAIN, writes=writes, vgm_bytes=len(data), vgz_bytes=len(packed),
                         vgm_sha256=opl.sha(data), wave_sha256=opl.sha(path.read_bytes()),
                         peak=float(abs(audio).max()), clipping_samples=int((abs(audio) >= 1).sum()),
                         chip_clipping_samples=int(((raw <= -1) | (raw >= 32767 / 32768)).sum()),
                         diagnostics=diagnostic(source, read(path)), artifacts=artifacts(audio, source),
                         register_perturbations=perturbations, phase_derivative_power=phase.tolist(),
                         all_1500_target_states=checked, complete_native_replay_exact=True)
            trials.append(entry)
            if name == 'cosine2':
                shutil.copyfile(path, args.output / 'ym3812-preview.wav')
                (args.output / 'ym3812.vgm').write_bytes(data)
                (args.output / 'ym3812.vgz').write_bytes(packed)
            if name == 'cosine4': shutil.copyfile(path, args.output / 'slower-transition.wav')
            print(json.dumps(dict(name=name, objective=entry['diagnostics']['metrics']['objective_db'],
                level_mae=entry['diagnostics']['metrics']['level_mae_db'],
                perturbation_energy=perturbations['all']['sum_squared_sample_perturbation'],
                bus_end_ms=perturbations['last_bus_slot_ms_max'])), flush=True)
    selected = next(t for t in trials if t['name'] == 'cosine2'); baseline = trials[0]
    ratio = selected['register_perturbations']['all']['sum_squared_sample_perturbation'] / baseline['register_perturbations']['all']['sum_squared_sample_perturbation']
    assert ratio < .25 and selected['register_perturbations']['all']['maximum'] < .25 * baseline['register_perturbations']['all']['maximum']
    assert selected['diagnostics']['metrics']['level_mae_db'] < baseline['diagnostics']['metrics']['level_mae_db'] + .2
    for size in ('512', '2048', '8192'):
        assert selected['diagnostics']['unpooled'][size]['magnitude_cosine'] >= baseline['diagnostics']['unpooled'][size]['magnitude_cosine']
    shutil.copyfile(old / 'selected-controls.npz', args.output / 'controls.npz')
    for path, expected in ((old / 'ym3812-preview.wav', baseline), (args.output / 'ym3812-preview.wav', selected)):
        assert opl.sha(path.read_bytes()) == expected['wave_sha256']
    segments = []
    for path in (old / 'ym3812-preview.wav', args.output / 'ym3812-preview.wav'):
        with wave.open(str(path), 'rb') as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (1, 2, 44100, 1323000)
            segments.append(stream.readframes(stream.getnframes()))
    pcm = segments[0] + bytes(88200) + segments[1]
    with wave.open(str(args.output / 'before-after.wav'), 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(44100); stream.writeframes(pcm)
    with wave.open(str(args.output / 'before-after.wav'), 'rb') as stream:
        assert stream.getnframes() == 61 * 44100 and stream.readframes(stream.getnframes()) == pcm
    versions = [('Previous YM3812', read(old / 'ym3812-preview.wav')),
                ('Smooth register transitions', read(args.output / 'ym3812-preview.wav'))]
    plot(source, versions, args.output / 'spectrogram-full.png')
    plot(source, versions, args.output / 'spectrogram-detail.png', baseline['diagnostics']['worst_interval_seconds'])
    phase_plot([baseline, selected], args.output / 'frame-phase.png')
    report = dict(complete=True, date='2026-10-13', seconds=30, fields=1500, selected='cosine2',
        baseline_commit='60e8bb3e', same_targets_and_global_gain=True, register_sample_perturbation_energy_reduction=1 - ratio,
        reference_sha256=opl.sha((old / 'reference.wav').read_bytes()), controls_sha256=opl.sha((old / 'selected-controls.npz').read_bytes()),
        baseline_wav_and_vgm_replay_exact=True, trials=trials, no_pcm_in_stream=True,
        selection='Observed tradeoff: ordered eight-step nominal2-ms cosine gives about80% perturbation-energy reduction and the least level/log penalty among the eight-step trials; all three dominant cosines improve. Four-ms version remains an audition alternative. No global or perceptual optimum claim.',
        limitations='Counterfactual first-native-sample effects include legitimate pitch/envelope changes and quantization. Derivative windows include ordinary tone energy. Neither proves clicks inaudible. No physical-chip/Z80/release qualification.',
        output_filter_unchanged='20-Hz AC coupling,8-kHz129-tap fractional resampling; same constant gain.',
        exact61_second_comparison=True, physical_chip_or_z80_verified=False,
        producer_sources_sha256_lf={str(p.relative_to(CORE)).replace('\\', '/'): opl.sha(p.read_bytes().replace(b'\r\n', b'\n'))
            for p in (CORE / 'experimental_ym3812.py', CORE / 'test_experimental_ym3812.py', Path(__file__))})
    import ymfm._core
    report['emulator_binary_sha256'] = opl.sha(Path(ymfm._core.__file__).read_bytes())
    report['artifacts_sha256'] = {str(p.relative_to(args.output)).replace('\\', '/'): opl.sha(p.read_bytes())
                                for p in sorted(args.output.rglob('*')) if p.is_file()}
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__': main()
