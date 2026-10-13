"""Archive the complete timed probes, target comparison and final evidence audit."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import sys
import wave
import numpy as np

HERE = Path(__file__).resolve().parent; CORE = HERE.parents[1]
sys.path.insert(0, str(CORE)); sys.path.insert(0, str(CORE / 'analysis/six_voice_spectral'))
from support import sha, save
from analyze import read, diagnostic, plot
from verify_preview import expected_registers
import timed_ay
from ramps import replay


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('ramps', 'native', 'ay-cli', 'ym-cli', 'tests'): parser.add_argument('--' + argument, type=Path, required=True)
    args = parser.parse_args(); evidence = HERE / 'evidence'; target = evidence / 'ramps'
    if target.exists(): raise ValueError('final archive already exists')
    source = read(CORE / 'analysis/o_henry/evidence/compact30/original-preview.wav')
    assert (args.ay_cli / 'ay-preview.wav').read_bytes() == (evidence / 'stage3/continuity0.1/ay-preview.wav').read_bytes()
    assert (args.ay_cli / 'registers.gz').read_bytes() == (evidence / 'stage3/continuity0.1/registers.gz').read_bytes()
    report = json.loads((args.ramps / 'report.json').read_bytes()); assert report['complete']
    target.mkdir()
    for name in ('report.json', 'before-after.wav', 'spectrogram-full.png', 'spectrogram-detail.png'):
        shutil.copyfile(args.ramps / name, target / name)
    for entry in report['trials']:
        original = args.ramps / entry['name']; saved = target / entry['name']; saved.mkdir()
        for name in ('commands.gz', 'ay-preview.wav', 'steps.json', 'report.json'): shutil.copyfile(original / name, saved / name)
        data = gzip.decompress((saved / 'commands.gz').read_bytes()); assert sha(data) == entry['commands_sha256']
        assert sha((saved / 'ay-preview.wav').read_bytes()) == entry['wave_sha256']
        assert entry['replay_exact'] and entry['all_1500_states']['all_target_states_exact']
        if entry['name'] in ('bands', 'continuity'):
            relative = 'stage2/bands512' if entry['name'] == 'bands' else 'stage3/continuity0.1'
            registers = gzip.decompress((evidence / relative / 'registers.gz').read_bytes())
        else: registers = gzip.decompress((CORE / 'analysis/o_henry/evidence/compact30/registers.gz').read_bytes())
        assert timed_ay.stream(registers, entry['register_bytes'], entry['transition_ms']) == data
        timed_ay.audit(data, registers)
        current_audio, _, _ = replay(data, 'node', original / 'current-final-replay')
        quality.write_wav(original / 'current-final-replay/replay.wav', current_audio * entry['gain'], 44100)
        assert (original / 'current-final-replay/replay.wav').read_bytes() == (saved / 'ay-preview.wav').read_bytes()
    current = (CORE / 'timed_ay.py').read_bytes().replace(b'\r\n', b'\n')
    original = current.replace(b' or steps != 8:', b':').replace(
        b"    # AYE1 is explicitly an AY probe, independent of ambient target settings.\n", b'').replace(
        b"music_profile.chip_levels('AY')", b'music_profile.chip_levels()')
    assert sha(original) == report['producers_sha256_lf']['timed_ay.py']
    (target / 'producer-timed_ay.py.gz').write_bytes(gzip.compress(original, mtime=0))
    js = (CORE / 'render_timed_ay.js').read_bytes().replace(b'\r\n', b'\n').replace(
        b'api.createChip(1773450,44100,false)', b'api.createChip()')
    assert sha(js) == report['producers_sha256_lf']['render_timed_ay.js']
    (target / 'producer-render_timed_ay.js.gz').write_bytes(gzip.compress(js, mtime=0))
    sections = []
    for name in ('timed-baseline', 'ramp4'):
        with wave.open(str(target / name / 'ay-preview.wav'), 'rb') as stream:
            sections.append(stream.readframes(stream.getnframes()))
    with wave.open(str(target / 'before-after.wav'), 'rb') as stream:
        assert stream.getnframes() == 61 * 44100
        assert stream.readframes(stream.getnframes()) == sections[0] + bytes(88200) + sections[1]
    comparison = evidence / 'ym2149'; comparison.mkdir()
    for name in ('registers.gz', 'soundtrack.ay9.gz', 'ay-preview.wav', 'report.json', 'fit-controls.npz', 'chip-render.json'):
        shutil.copyfile(args.ym_cli / name, comparison / name)
    raw = gzip.decompress((comparison / 'registers.gz').read_bytes())
    assert raw == expected_registers(gzip.decompress((comparison / 'soundtrack.ay9.gz').read_bytes()))
    ym = diagnostic(source, read(comparison / 'ay-preview.wav'))
    native = json.loads((args.native / 'report.json').read_bytes()); assert native['complete'] and native['unique_streams'] == 9
    shutil.copyfile(args.native / 'report.json', evidence / 'native-streams.json')
    shutil.copyfile(args.tests, evidence / 'tests.log')
    assert 'Ran 7 tests' in args.tests.read_text(encoding='utf-8') and args.tests.read_text(encoding='utf-8').rstrip().endswith('OK')
    for stage in ('stage1', 'stage2', 'stage3'):
        folder = evidence / stage; verification = json.loads((folder / 'verification.json').read_bytes())
        for relative, expected in verification['artifacts_sha256'].items(): assert sha((folder / relative).read_bytes()) == expected, relative
    versions = [('Current AY encoder', read(evidence / 'stage1/baseline.wav')),
                ('Direct512 (not admitted)', read(evidence / 'stage1/direct512/ay-preview.wav')),
                ('With existing feedback (not admitted)', read(evidence / 'stage3/with-existing-feedback/ay-preview.wav'))]
    interval = json.loads((evidence / 'stage1/report.json').read_bytes())['baseline']['worst_interval_seconds']
    plot(source, versions, evidence / 'comparison-full.png')
    plot(source, versions, evidence / 'comparison-detail.png', interval)
    result = dict(complete=True, date='2026-10-13', plan_milestones_complete=[1, 2, 3, 4],
        selected_50hz_encoder='unchanged current auto', new_fitting_candidates_admitted=False,
        baseline_objective_db=9.24885024271221, best_new_50hz_objective_db=9.667438611509786,
        native_unique_50hz_streams=9, native_fields_each=3000, unit_tests=7, tests_pass=True,
        independent_general_cli_registers_and_full_wav_exact=True,
        current_timed_export_all_six_streams_byte_exact=True, exact61_second_comparison=True,
        current_timed_renderer_all_six_complete_wavs_byte_exact=True,
        timed_probe_target_explicit_independent_of_environment=True,
        ym2149_same_source_gain_and_settings=ym, ym2149_not_fuse_model=True,
        timed_probe_selected=report['selected_transition_probe'], timed_probe_native_qualified=False,
        all_stage_artifact_hashes_exact=True, physical_chip_fuse_audio_release_qualified=False,
        producer_sources_sha256_lf={p.name: sha(p.read_bytes().replace(b'\r\n', b'\n')) for p in
            (CORE / 'spectral_fit.py', CORE / 'timed_ay.py', CORE / 'render_timed_ay.js', Path(__file__))},
        artifacts_sha256={str(p.relative_to(evidence)).replace('\\', '/'): sha(p.read_bytes())
                          for p in sorted(evidence.rglob('*')) if p.is_file()})
    save(evidence / 'completion.json', result)
    print(json.dumps(dict(complete=True, ym_objective=ym['metrics']['objective_db'], timed_selected=result['timed_probe_selected'], native_streams=9)))


if __name__ == '__main__': main()
