"""Check complete OPL2 streams, retain every trial and build listening evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import wave

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
import experimental_ym3812 as opl
import quality
from analyze import read, diagnostic, plot
from test_experimental_ym3812 import audit


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--expanded', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    args = parser.parse_args()
    target = HERE / 'evidence'
    if target.exists(): raise ValueError('archive already exists')
    target.mkdir()
    source_folder = CORE / 'analysis/six_voice_spectral/evidence'
    reference_path = source_folder / 'reference.wav'
    source = read(reference_path)
    baseline = diagnostic(source, read(source_folder / 'six-voice-preview.wav'))
    initial = json.loads((args.initial / 'report.json').read_bytes())
    expanded = json.loads((args.expanded / 'report.json').read_bytes())
    assert initial['reference_sha256'] == expanded['reference_sha256'] == sha(reference_path)
    assert opl.sha((CORE / 'experimental_ym3812.py').read_bytes().replace(b'\r\n', b'\n')) == expanded['producer_sha256_lf']
    assert opl.sha(gzip.decompress((args.initial / 'producer.py.gz').read_bytes())) == initial['producer_sha256_lf']
    trials = []
    with tempfile.TemporaryDirectory(dir=target) as temporary:
        for label, folder, report in (('mult1', args.initial, initial), ('mult12', args.expanded, expanded)):
            saved = target / 'trials' / label
            saved.mkdir(parents=True)
            shutil.copyfile(folder / 'report.json', saved / 'report.json')
            if label == 'mult1': shutil.copyfile(folder / 'producer.py.gz', saved / 'producer.py.gz')
            for mode in ('sine', 'waveforms', 'fm'):
                shutil.copyfile(folder / f'{mode}-controls.npz', saved / f'{mode}-controls.npz')
            for entry in report['trials']:
                name = entry['name']
                with np.load(folder / f"{entry['mode']}-controls.npz") as npz:
                    controls = {k: npz[k] for k in npz.files}
                assert opl.validate(controls) == 1500
                data = (folder / f'{name}.vgm').read_bytes()
                regenerated, writes = opl.vgm(controls, entry['ramp_steps'])
                assert regenerated == data and writes == entry['writes']
                register_check = audit(data, controls)
                raw, samples, _ = opl.replay(data)
                assert samples == 1323000 and len(raw) == 1491477
                audio = opl.playback(raw, samples) * entry['global_playback_gain']
                replay_path = Path(temporary) / 'replay.wav'
                quality.write_wav(replay_path, audio, 44100)
                assert replay_path.read_bytes() == (folder / f'{name}.wav').read_bytes()
                assert sha(replay_path) == entry['wave_sha256'] and opl.sha(data) == entry['vgm_sha256']
                packed = (folder / f'{name}.vgz').read_bytes()
                assert gzip.decompress(packed) == data
                shutil.copyfile(folder / f'{name}.vgz', saved / f'{name}.vgz')
                details = diagnostic(source, read(replay_path))
                # The scalar log score can reward positive-waveform harmonics
                # while ignoring low-frequency control DC. Require a usable
                # speech candidate to improve levels and dominant-partial
                # agreement on all scales, and keep sub50-Hz power below1%.
                eligible = details['sub_50hz_power_fraction'] < .01
                eligible &= details['metrics']['level_mae_db'] <= baseline['metrics']['level_mae_db']
                root_guard = True
                for size, metric in details['unpooled'].items():
                    eligible &= metric['magnitude_cosine'] >= baseline['unpooled'][size]['magnitude_cosine']
                    root_guard &= metric['sqrt_magnitude_cosine'] >= baseline['unpooled'][size]['sqrt_magnitude_cosine']
                entry = dict(entry, trial_id=label + '/' + name, diagnostics=details,
                             controls_vgm_and_full_wav_replay_exact=True,
                             all_1500_register_states=register_check,
                             dominant_partial_level_and_subsonic_guard=bool(eligible),
                             stricter_root_partial_guard=bool(eligible and root_guard),
                             temporary_original_folder=str(folder.resolve()))
                trials.append(entry)
                print(json.dumps(dict(stage='archive', trial=entry['trial_id'], eligible=bool(eligible),
                                      objective=details['metrics']['objective_db'], sub50=details['sub_50hz_power_fraction'])), flush=True)
    eligible = [t for t in trials if t['dominant_partial_level_and_subsonic_guard']]
    if not eligible: raise ValueError('no eligible listening candidate')
    selected = min(eligible, key=lambda t: t['diagnostics']['metrics']['objective_db'])
    selected_folder = Path(selected['temporary_original_folder'])
    shutil.copyfile(selected_folder / (selected['name'] + '.wav'), target / 'ym3812-preview.wav')
    shutil.copyfile(selected_folder / (selected['name'] + '.vgm'), target / 'ym3812.vgm')
    shutil.copyfile(selected_folder / (selected['name'] + '.vgz'), target / 'ym3812.vgz')
    shutil.copyfile(selected_folder / (selected['mode'] + '-controls.npz'), target / 'selected-controls.npz')
    # Retain the stronger log-only candidate too, with its explicit tradeoff.
    lowest = min(trials, key=lambda t: t['diagnostics']['metrics']['objective_db'])
    low_folder = Path(lowest['temporary_original_folder'])
    shutil.copyfile(low_folder / (lowest['name'] + '.wav'), target / 'waveforms-alternative.wav')
    shutil.copyfile(args.expanded / 'fm.wav', target / 'fm-alternative.wav')
    shutil.copyfile(reference_path, target / 'reference.wav')
    shutil.copyfile(args.tests, target / 'tests.log')
    versions = [('Accepted hypothetical six-voice model', read(source_folder / 'six-voice-preview.wav')),
                ('YM3812 nine carriers', read(target / 'ym3812-preview.wav'))]
    plot(source, versions, target / 'spectrogram-full.png')
    plot(source, versions, target / 'spectrogram-detail.png', baseline['worst_interval_seconds'])
    plot(source, [('YM3812 four-waveform alternative', read(target / 'waveforms-alternative.wav'))], target / 'waveforms-spectrogram.png')
    segments = []
    for path in (source_folder / 'six-voice-preview.wav', target / 'ym3812-preview.wav'):
        with wave.open(str(path), 'rb') as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (1, 2, 44100, 1323000)
            segments.append(stream.readframes(stream.getnframes()))
    pcm = segments[0] + bytes(88200) + segments[1]
    with wave.open(str(target / 'six-versus-ym3812.wav'), 'wb') as stream:
        stream.setnchannels(1); stream.setsampwidth(2); stream.setframerate(44100); stream.writeframes(pcm)
    with wave.open(str(target / 'six-versus-ym3812.wav'), 'rb') as stream:
        assert stream.getnframes() == 61 * 44100 and stream.readframes(stream.getnframes()) == pcm
    for entry in trials: entry.pop('temporary_original_folder')
    report = dict(complete=True, date='2026-10-13', seconds=30, fields=1500, channels=9, trials=trials,
                  selected=selected['trial_id'], lowest_log_only_trial=lowest['trial_id'],
                  selection='Lowest combined log/level score among candidates improving dominant magnitude cosine at ALL three scales and level MAE versus the six-voice baseline, with sub50-Hz power below1%.',
                  all_scale_root_partial_improvement_established=any(t['stricter_root_partial_guard'] for t in trials),
                  strict_guard_attempt='Initial archive selection required root cosine improvement too; all eight failed. Deliver the bounded chip audition with an explicitly narrower dominant-partial/level/subsonic guard; no overall-quality improvement claim.',
                  six_voice_baseline=baseline, reference_sha256=sha(reference_path),
                  all_eight_complete_streams_replayed=True, all_1500_states_each_verified=True,
                  no_source_pcm_in_stream=True, exact61_second_comparison_segments=True,
                  tests=5, listening_acceptance_pending=True, physical_chip_or_z80_verified=False,
                  emulator=expanded['emulator'], emulator_version=expanded['emulator_version'],
                  emulator_binary_sha256=expanded['emulator_binary_sha256'],
                  emulator_limitation='Pinned0.2.0 ignores waveform-select-disable gating; all exported streams explicitly keep register01h=20h, so this unused behavior does not affect these auditions.',
                  producer_sources_sha256_lf={n: opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for n, p in
                      [('experimental_ym3812.py', CORE / 'experimental_ym3812.py'),
                       ('test_experimental_ym3812.py', CORE / 'test_experimental_ym3812.py'),
                       ('archive.py', Path(__file__)), ('analyze.py', CORE / 'analysis/six_voice_spectral/analyze.py'),
                       ('quality.py', CORE / 'quality.py'), ('simulation_refine.py', CORE / 'simulation_refine.py')]})
    report['artifacts_sha256'] = {str(p.relative_to(target)).replace('\\', '/'): sha(p) for p in sorted(target.rglob('*')) if p.is_file()}
    (target / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(selected=report['selected'], lowest_log_only=report['lowest_log_only_trial'])), flush=True)


if __name__ == '__main__': main()
