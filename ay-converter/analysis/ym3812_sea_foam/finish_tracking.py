"""Select and archive the complete coherent song under all saved content guards."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import wave
import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE)); sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
import experimental_ym3812 as opl
import experimental_six_voice as six
from analyze import read, plot
from support import save


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', type=Path, required=True)
    parser.add_argument('--soft48', type=Path, required=True)
    parser.add_argument('--soft52', type=Path, required=True)
    args = parser.parse_args()
    evidence = HERE / 'tracking-evidence'
    if (evidence / 'report.json').exists(): raise ValueError('completed archive already exists')
    for name, folder in (('local', args.local), ('soft48', args.soft48), ('soft52', args.soft52)):
        if (evidence / name).exists(): raise ValueError('trial archive already exists')
        report = json.loads((folder / 'report.json').read_bytes()); assert report['complete']
        for relative, expected in report['artifacts_sha256'].items(): assert opl.sha((folder / relative).read_bytes()) == expected, relative
        for relative, expected in report['producer_sources_sha256_lf'].items(): assert opl.sha((CORE / relative).read_bytes().replace(b'\r\n', b'\n')) == expected, relative
        shutil.copytree(folder, evidence / name)
    old = HERE / 'evidence'; source = six.read_reference(old / 'reference.wav')
    power = abs(np.fft.rfft(source)) ** 2; hz = np.fft.rfftfreq(len(source), 1 / opl.RATE)
    source_low_fraction = float(power[hz < 50].sum() / power.sum())
    # Additional strict content guard after the stronger FM variants revealed
    # low-frequency envelope/mean modulation not covered by the50-Hz STFT floor.
    low_limit = source_low_fraction + .0002
    candidates = []; reports = []
    for section in ('phase1', 'gates', 'groups', 'local', 'soft48', 'soft52'):
        report = json.loads((evidence / section / 'report.json').read_bytes()); reports.append(report)
        for trial in report['trials']:
            candidates.append(dict(section=section, name=trial['name'], original_admitted=trial['admitted'],
                low_frequency_content_guard=trial['diagnostics']['sub_50hz_power_fraction'] <= low_limit,
                admitted=trial['admitted'] and trial['diagnostics']['sub_50hz_power_fraction'] <= low_limit,
                objective_db=trial['diagnostics']['metrics']['objective_db'],
                sub50=trial['diagnostics']['sub_50hz_power_fraction']))
    eligible = [t for t in candidates if t['admitted']]; assert eligible
    chosen = min(eligible, key=lambda t: t['objective_db']); assert chosen['name'] == 'soft52'
    folder = evidence / chosen['section'] / chosen['name']
    selected = json.loads((folder / 'report.json').read_bytes())
    for name in ('controls.npz', 'tracking.npz', 'ym3812.vgm', 'ym3812.vgz', 'ym3812-preview.wav'):
        shutil.copyfile(folder / name, evidence / name)
    before = read(old / 'ym3812-preview.wav'); after = read(evidence / 'ym3812-preview.wav')
    plot(source, [('Original YM3812 baseline', before), ('Coherent source-supported YM3812', after)], evidence / 'spectrogram-full.png')
    spans = json.loads((HERE / 'beep-evidence/report.json').read_bytes())['exposed_synthetic_lines']['strongest3_second_spans']
    plot(source, [('Original YM3812 baseline', before), ('Coherent source-supported YM3812', after)], evidence / 'spectrogram-detail.png', spans[0])
    full = []
    for path in (old / 'ym3812-preview.wav', evidence / 'ym3812-preview.wav'):
        with wave.open(str(path), 'rb') as w: full.append(w.readframes(w.getnframes()))
    with wave.open(str(evidence / 'before-after.wav'), 'wb') as w:
        w.setparams((1, 2, 44100, 0, 'NONE', 'not compressed')); w.writeframes(full[0] + bytes(88200) + full[1])
    for index, (start, end) in enumerate(spans, 1):
        chunks = []
        for path in (old / 'comparison-source.wav', old / 'ym3812-preview.wav', evidence / 'ym3812-preview.wav'):
            with wave.open(str(path), 'rb') as w:
                w.setpos(round(start * 44100)); chunks.append(w.readframes(round((end - start) * 44100)))
        with wave.open(str(evidence / f'span-{index}-source-old-new.wav'), 'wb') as w:
            w.setparams((1, 2, 44100, 0, 'NONE', 'not compressed')); w.writeframes(bytes(88200).join(chunks))
    previous = json.loads((old / 'report.json').read_bytes())
    result = dict(complete=True, date='2026-10-14', seconds=90, fields=4500, selected=chosen,
        selected_metrics=selected, candidates=candidates, all15_trials_retained=len(candidates) == 15,
        source_below50_power_fraction=source_low_fraction, additional_below50_limit=low_limit,
        baseline=previous['trials'][1]['diagnostics'], modulator_tl=52,
        global_playback_gain=previous['global_playback_gain'], fitting_gain=previous['fitting_gain'],
        source_sha256=opl.sha((old / 'reference.wav').read_bytes()), native_core_sha256=previous['native_core_sha256'],
        target_rate_hz=50, source_pcm_in_output=False, output_filter_unchanged=True,
        physical_chip_or_z80_player_qualified=False, verification_stored_separately=True,
        producer_sources_sha256_lf={str(p.relative_to(CORE)).replace('\\', '/'): opl.sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in
            (Path(__file__), CORE / 'coherent_ym3812.py', CORE / 'grouped_ym3812.py', HERE / 'tracking_local.py', HERE / 'tracking_soft.py')},
        artifacts_sha256={str(p.relative_to(evidence)).replace('\\', '/'): opl.sha(p.read_bytes()) for p in sorted(evidence.rglob('*')) if p.is_file()})
    assert result['all15_trials_retained']
    save(evidence / 'report.json', result)
    print(json.dumps(dict(complete=True, selected=chosen, low_limit=low_limit, trials=15)), flush=True)


if __name__ == '__main__': main()
