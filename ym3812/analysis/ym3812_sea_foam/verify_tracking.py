"""Independently decode every retained full-song VGM and recover exact PCM."""
import argparse
import gzip
import importlib.metadata
import json
from pathlib import Path
import sys
import wave
import numpy as np
import ymfm

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
import experimental_ym3812 as opl
import grouped_ym3812 as grouped
from support import save
from test_experimental_ym3812 import audit


def pcm(path, samples):
    with wave.open(str(path), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()) == (1, 2, 44100, samples)
        return w.readframes(samples)


def check(folder, report):
    for name, expected in report['artifacts_sha256'].items(): assert opl.sha((folder / name).read_bytes()) == expected, name
    for name, expected in report['producer_sources_sha256_lf'].items(): assert opl.sha((CORE / name).read_bytes().replace(b'\r\n', b'\n')) == expected, name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tests', type=Path, required=True)
    args = parser.parse_args(); evidence = HERE / 'tracking-evidence'
    report = json.loads((evidence / 'report.json').read_bytes()); check(evidence, report)
    assert report['complete'] and report['selected']['name'] == 'soft52'
    assert report['selected']['admitted'] and report['target_rate_hz'] == 50 and report['all15_trials_retained']
    assert importlib.metadata.version('ymfm-py') == '0.2.0'
    assert opl.sha(next(Path(ymfm.__file__).parent.glob('*.pyd')).read_bytes()) == report['native_core_sha256']
    old = HERE / 'evidence'; before = json.loads((old / 'report.json').read_bytes()); check(old, before)
    assert report['source_sha256'] == opl.sha((old / 'reference.wav').read_bytes())
    assert report['global_playback_gain'] == before['global_playback_gain']
    with np.load(old / 'controls.npz') as saved: original = {k: saved[k] for k in saved.files}
    assert grouped.export(original)[0] == (old / 'ym3812.vgm').read_bytes()
    results = []
    for section in ('phase1', 'gates', 'groups', 'local', 'soft48', 'soft52'):
        folder = evidence / section; phase = json.loads((folder / 'report.json').read_bytes()); check(folder, phase)
        mod_tl = phase.get('modulator_tl', 40)
        opl.PATCHES[7]['mod_tl'] = mod_tl; opl.PATCHES[21]['mod_tl'] = mod_tl
        for trial in phase['trials']:
            path = folder / trial['name']
            with np.load(path / 'controls.npz') as stored: controls = {k: stored[k] for k in stored.files}
            data = (path / 'ym3812.vgm').read_bytes()
            assert gzip.decompress((path / 'ym3812.vgz').read_bytes()) == data
            regenerated, writes = (grouped.export if phase.get('grouped_export', False) else opl.smooth_vgm)(controls)
            assert data == regenerated and writes == trial['writes']
            checked = audit(data, controls)
            raw, samples, parsed = opl.replay(data)
            assert samples == 3969000 and len(raw) == 4474431 and parsed == writes
            audio = opl.playback(raw, samples) * report['global_playback_gain']
            assert int(np.sum(abs(raw) >= 1)) == trial['native_clipping_samples'] == 0
            assert int(np.sum(abs(audio) >= 1)) == trial['clipping_samples'] == 0
            expected = np.clip(np.rint(audio * 32767), -32768, 32767).astype('<i2').tobytes()
            assert expected == pcm(path / 'ym3812-preview.wav', samples)
            results.append(dict(section=section, name=trial['name'], **checked, native_samples=len(raw), output_samples=samples,
                                commands_and_every_pcm_sample_exact=True, native_sha256=opl.sha(raw.tobytes())))
            print(json.dumps(dict(stage='independent_full_tracking_replay', name=trial['name'], fields=4500)), flush=True)
    assert len(results) == 15
    selected = evidence / 'soft52/soft52'
    for name in ('controls.npz', 'tracking.npz', 'ym3812.vgm', 'ym3812.vgz', 'ym3812-preview.wav'):
        assert (evidence / name).read_bytes() == (selected / name).read_bytes()
    assert pcm(evidence / 'before-after.wav', 181 * 44100) == pcm(old / 'ym3812-preview.wav', 3969000) + bytes(88200) + pcm(evidence / 'ym3812-preview.wav', 3969000)
    spans = json.loads((HERE / 'beep-evidence/report.json').read_bytes())['exposed_synthetic_lines']['strongest3_second_spans']
    for index, (start, end) in enumerate(spans, 1):
        pieces = []
        for source in (old / 'comparison-source.wav', old / 'ym3812-preview.wav', evidence / 'ym3812-preview.wav'):
            with wave.open(str(source), 'rb') as w:
                w.setpos(round(start * 44100)); pieces.append(w.readframes(132300))
        assert pcm(evidence / f'span-{index}-source-old-new.wav', 485100) == bytes(88200).join(pieces)
    tests = args.tests.read_text(encoding='utf-8'); assert 'Ran 14 tests' in tests and tests.rstrip().endswith('OK')
    (evidence / 'tests.log').write_bytes(args.tests.read_bytes())
    save(evidence / 'verification.json', dict(complete=True, date='2026-10-14', streams=results, full_fields=67500,
         all15_complete_independent_commands_and_pcm_replays_exact=True, historical_export_all4500_fields_byte_exact=True,
         selected_all_quality_and_additional_low_frequency_guards_pass=True, selected_no_clipping=True,
         exact181_second_comparison=True, exact_four_source_old_new_excerpts=True, unit_tests=14, unit_tests_pass=True,
         verification_source_sha256_lf=opl.sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
         artifacts_sha256={str(p.relative_to(evidence)).replace('\\', '/'): opl.sha(p.read_bytes()) for p in sorted(evidence.rglob('*')) if p.is_file() and p.name != 'verification.json'}))
    print(json.dumps(dict(complete=True, streams=15, fields=67500, tests=14, selected='soft52')), flush=True)


if __name__ == '__main__': main()
