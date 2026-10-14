"""Re-export all six trials and independently recover every saved PCM sample."""
import argparse
import gzip
import importlib.metadata
import json
from pathlib import Path
import sys
import wave

import numpy as np
import ymfm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import overtones as h
from test_overtones import oscillator, harmonic_ratio
from support import save


def pcm(path, samples):
    with wave.open(str(path), 'rb') as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (1, 2, 44100, samples)
        return stream.readframes(samples)


def check_manifest(folder, report):
    for name, expected in report['artifacts_sha256'].items(): assert h.opl.sha((folder / name).read_bytes()) == expected, name
    for name, expected in report['producer_sources_sha256_lf'].items(): assert h.opl.sha((h.CORE / name).read_bytes().replace(b'\r\n', b'\n')) == expected, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    args = parser.parse_args()
    evidence = args.evidence; report = json.loads((evidence / 'report.json').read_bytes())
    assert report['complete'] and report['selected'] == 'cap10' and report['fields'] == 4500
    assert not report['original_aggregate_guard_met'] and report['original_content_level_guards_met']
    assert report['output_filter_unchanged'] and not report['source_pcm_in_output']
    old = json.loads((HERE / 'evidence/report.json').read_bytes()); check_manifest(HERE / 'evidence', old)
    assert h.opl.sha((HERE / 'evidence/reference.wav').read_bytes()) == report['source_sha256']
    assert report['global_playback_gain'] == old['global_playback_gain']
    assert importlib.metadata.version('ymfm-py') == '0.2.0'
    assert h.opl.sha(next(Path(ymfm.__file__).parent.glob('*.pyd')).read_bytes()) == report['native_core_sha256']
    check_manifest(evidence, report)
    with np.load(HERE / 'evidence/controls.npz') as stored: original = {k: stored[k] for k in stored.files}
    streams = []
    for section in ('setup', 'refit'):
        folder = evidence / section; trials = json.loads((folder / 'report.json').read_bytes())
        check_manifest(folder, trials)
        assert trials['complete'] and trials['selected'] is None
        for trial in trials['trials']:
            name = trial['name']
            with np.load(folder / (name + '.npz')) as stored: controls = {k: stored[k] for k in stored.files}
            data = gzip.decompress((folder / (name + '.vgz')).read_bytes())
            regenerated, writes = h.pure_vgm(controls)
            assert data == regenerated and writes == trial['writes']
            checked = h.audit(data, controls)
            raw, samples, parsed = h.opl.replay(data)
            assert samples == 3969000 and len(raw) == 4474431 and parsed == writes
            assert not np.any(abs(raw) >= 1)
            audio = h.opl.playback(raw, samples) * report['global_playback_gain']
            clipping = int(np.sum(abs(audio) >= 1)); assert clipping == trial['clipping_samples']
            expected = np.clip(np.rint(audio * 32767), -32768, 32767).astype('<i2').tobytes()
            assert pcm(folder / (name + '.wav'), samples) == expected
            if section == 'setup':
                for key in ('fnum', 'block', 'patch'): assert np.array_equal(controls[key], original[key])
                assert np.array_equal(controls['level'] == 64, original['level'] == 64)
                assert np.all(controls['level'] >= original['level'])
            streams.append(dict(name=name, **checked, native_samples=len(raw), output_samples=samples,
                                clipping_samples=clipping, commands_and_full_pcm_exact=True))
            print(json.dumps(dict(stage='independent_overtones_replay', name=name, clipping=clipping, fields=4500)), flush=True)
    assert len(streams) == 6 and sum(item['clipping_samples'] > 0 for item in streams) == 1
    for target, source in (('ym3812-preview.wav', 'cap10.wav'), ('controls.npz', 'cap10.npz'), ('ym3812.vgz', 'cap10.vgz')):
        assert (evidence / target).read_bytes() == (evidence / 'setup' / source).read_bytes()
    assert (evidence / 'ym3812.vgm').read_bytes() == gzip.decompress((evidence / 'ym3812.vgz').read_bytes())
    comparison = pcm(evidence / 'before-after.wav', 181 * 44100)
    assert comparison == pcm(HERE / 'evidence/ym3812-preview.wav', 3969000) + bytes(88200) + pcm(evidence / 'ym3812-preview.wav', 3969000)
    for trial in report['purity_tones']:
        before, after = harmonic_ratio(oscillator(False, trial['block'])), harmonic_ratio(oscillator(True, trial['block']))
        assert before == trial['previous_harmonic_power_ratio'] and after == trial['pure_harmonic_power_ratio']
        assert after < before * .001
    tests = args.tests.read_text(encoding='utf-8'); assert 'Ran 12 tests' in tests and tests.rstrip().endswith('OK')
    (evidence / 'all-tests.log').write_bytes(args.tests.read_bytes())
    save(evidence / 'verification.json', dict(complete=True, date='2026-10-14', streams=streams, fields_each=4500,
         all_six_complete_commands_and_wavs_independently_replayed_exact=True, source_and_previous_evidence_unchanged=True,
         selected_all_frequencies_keys_patches_preserved=True, selected_no_clipping=True,
         exact181_second_comparison=True, native_purity_four_tones_repeated_exact=True,
         original20_percent_aggregate_guard_still_not_met=True, unit_tests=12, unit_tests_pass=True,
         verification_source_sha256_lf=h.opl.sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
         artifacts_sha256={str(p.relative_to(evidence)).replace('\\', '/'): h.opl.sha(p.read_bytes()) for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'verification.json'}))
    print(json.dumps(dict(complete=True, streams=6, fields=27000, tests=12, selected_no_clipping=True)), flush=True)


if __name__ == '__main__': main()
