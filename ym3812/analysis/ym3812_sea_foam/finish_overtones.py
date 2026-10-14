"""Archive the bounded purity/source-cap trials and select a content-preserving audition."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys
import time
import wave

import numpy as np
import ymfm

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import overtones as h
from test_overtones import oscillator, harmonic_ratio
from analyze import plot, read
from support import save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--setup', type=Path, required=True)
    parser.add_argument('--refit', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists(): raise ValueError('use a new output directory')
    args.output.mkdir(parents=True)
    reports = []
    for name, folder in (('setup', args.setup), ('refit', args.refit)):
        report = json.loads((folder / 'report.json').read_bytes()); assert report['complete']
        for relative, expected in report['artifacts_sha256'].items(): assert h.opl.sha((folder / relative).read_bytes()) == expected, relative
        for relative, expected in report['producer_sources_sha256_lf'].items(): assert h.opl.sha((h.CORE / relative).read_bytes().replace(b'\r\n', b'\n')) == expected, relative
        shutil.copytree(folder, args.output / name)
        reports.append(report)
    purity = []
    for block in (1, 3, 4, 5):
        before, after = harmonic_ratio(oscillator(False, block)), harmonic_ratio(oscillator(True, block))
        assert after < before * .001
        assert np.array_equal(oscillator(True, block), oscillator(True, block, 0))
        purity.append(dict(fnum=512, block=block, frequency_hz=512 * 2 ** block * h.opl.NATIVE_RATE / 2 ** 20,
                           previous_harmonic_power_ratio=before, pure_harmonic_power_ratio=after,
                           previous_harmonic_db=float(10 * np.log10(before)), pure_harmonic_db=float(10 * np.log10(after)),
                           reduction_db=float(10 * np.log10(before / after)), modulator_silent_even_at_tl0=True))
    save(args.output / 'purity.json', dict(method='32768 native samples, integer cycles, harmonic bins2..49 or Nyquist, no playback filter', tones=purity))
    # The initial20% aggregate-bin target rejects all six trials, including
    # otherwise useful pure-sine variants. Keep that failed outcome explicitly.
    # For the user's sine suggestion, choose a narrower oscillator-purity
    # audition: >=30-dB intrinsic harmonic reduction, reduced extra bin power
    # at every scale, and every original content/level guard still passing.
    assert not any(t['admitted'] for r in reports for t in r['trials'])
    eligible = [t for t in reports[0]['trials'] if all(v for k, v in t['admission'].items() if k != 'extra_2048')]
    assert eligible
    selected = min(eligible, key=lambda t: t['high']['scales']['2048']['4000-8000']['extra_power_fraction'])
    assert selected['name'] == 'cap10'
    name = selected['name']
    for target, source_name in (('ym3812-preview.wav', name + '.wav'), ('controls.npz', name + '.npz'), ('ym3812.vgz', name + '.vgz')):
        shutil.copyfile(args.setup / source_name, args.output / target)
    data = gzip.decompress((args.output / 'ym3812.vgz').read_bytes())
    (args.output / 'ym3812.vgm').write_bytes(data)
    source = h.six.read_reference(HERE / 'evidence/reference.wav')
    before = read(HERE / 'evidence/ym3812-preview.wav'); after = read(args.output / 'ym3812-preview.wav')
    versions = [('Previous YM3812 with residual FM', before), ('Pure sine YM3812, source-derived high TL cap', after)]
    plot(source, versions, args.output / 'spectrogram-full.png')
    plot(source, versions, args.output / 'spectrogram-detail.png', reports[0]['baseline']['high']['worst_extra_interval_seconds'])
    sections = []
    for path in (HERE / 'evidence/ym3812-preview.wav', args.output / 'ym3812-preview.wav'):
        with wave.open(str(path), 'rb') as stream:
            assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (1, 2, 44100, 3969000)
            sections.append(stream.readframes(stream.getnframes()))
    with wave.open(str(args.output / 'before-after.wav'), 'wb') as stream:
        stream.setparams((1, 2, 44100, 0, 'NONE', 'not compressed')); stream.writeframes(sections[0] + bytes(88200) + sections[1])
    tests = args.tests.read_text(encoding='utf-8'); assert 'Ran 4 tests' in tests and tests.rstrip().endswith('OK')
    shutil.copyfile(args.tests, args.output / 'tests.log')
    old = reports[0]['baseline']['high']['scales']; new = selected['high']['scales']
    result = dict(complete=True, date='2026-10-14', seconds=90, fields=4500, selected=name,
                  selection='intrinsic sine-purity audition with original content guards; aggregate20% guard not met',
                  original_aggregate_guard_met=False, original_content_level_guards_met=True,
                  all_six_trials_retained=True, purity_tones=purity, selected_metrics=selected,
                  baseline=reports[0]['baseline'], global_playback_gain=reports[0]['global_playback_gain'],
                  high_extra_reduction_percent={s: {band: 100 * (1 - new[s][band]['extra_power_fraction'] / old[s][band]['extra_power_fraction']) for band in ('1800-8000', '4000-8000')} for s in old},
                  source_pcm_in_output=False, output_filter_unchanged=True, all_frequencies_keys_patches_unchanged=True,
                  source_sha256=reports[0]['source_sha256'], native_core_sha256=reports[0]['native_core_sha256'],
                  verification_stored_separately=True, physical_chip_z80_player_qualified=False,
                  producer_sources_sha256_lf={str(p.relative_to(h.CORE)).replace('\\', '/'): h.opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in (Path(__file__), HERE / 'overtones.py', HERE / 'refit_overtones.py', HERE / 'test_overtones.py')},
                  artifacts_sha256={str(p.relative_to(args.output)).replace('\\', '/'): h.opl.sha(p.read_bytes()) for p in sorted(args.output.rglob('*')) if p.is_file()})
    save(args.output / 'report.json', result)
    print(json.dumps(dict(complete=True, selected=name, aggregate_guard=False, high_extra_reduction_percent=result['high_extra_reduction_percent'])), flush=True)


if __name__ == '__main__': main()
