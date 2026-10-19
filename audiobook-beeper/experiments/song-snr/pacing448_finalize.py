"""Independently audit and index the completed, unaccepted448-T experiment."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np


ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'evidence'
GROUPS = ('pacing448-cli', 'pacing448-control', 'pacing448-execution',
          'pacing448-player', 'pacing448-spectrum')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def verify_files(root, files):
    for name, item in files.items():
        path = root / name
        raw = path.read_bytes()
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], str(path)


def closed_form_clock(pulses, packed_bytes):
    """Count source ticks without calling either host/execution timeline.

    Start with packet number*448 plus a literal instruction-prefix sum.
    Every consumed256B adds14 T; bank ends replace that by243 T (+229).
    searchsorted applies an event only to timestamps after its last OUT.
    """
    core = np.array([36, 28, 28, 31, 24, 26, 22, 45,
                     22, 26, 22, 30, 31, 27, 34, 16], dtype=np.int64)
    prefix = np.r_[0, np.cumsum(core)]
    assert prefix[-1] == 448
    indices = np.arange(pulses, dtype=np.int64)
    result = (indices // 16) * 448 + prefix[indices % 16]
    pages = (2 * np.arange(256, packed_bytes + 1, 256) - 3) * 16 + 15
    result += np.searchsorted(pages, indices, side='right') * 14
    capacity = [16384]*5 + [9472] + [16384]*56
    remaining = packed_bytes
    ends = []
    for available in capacity:
        size = min(available, remaining)
        if not size:
            break
        remaining -= size
        ends.append((2*(packed_bytes-remaining)-3)*16+15)
    assert remaining == 0
    result += np.searchsorted(ends, indices, side='right') * 229
    return result


def main():
    player = EVIDENCE / 'pacing448-player'
    player_manifest = read(player / 'manifest.json')['artifacts']
    verify_files(player, {item['path']: item for item in player_manifest})
    execution = EVIDENCE / 'pacing448-execution'
    execution_manifest = read(execution / 'manifest.json')['artifact_files']
    verify_files(execution, execution_manifest)
    host = read(EVIDENCE / 'pacing448-control/report.json')
    assert host['complete'] and host['host_corpus_complete'] and len(host['rows']) == 15
    assert host['all_archived_scores_reproduced'] and not host['release_accepted']
    sealed = 0
    for row in host['rows']:
        folder = EVIDENCE / 'pacing448-control' / row['source']
        marker = read(folder / 'complete.json')
        verify_files(folder, marker['files'])
        assert marker['identity'] == row['source_identity']
        sealed += len(marker['files'])
    executed = read(execution / 'report.json')
    assert executed['complete'] and executed['complete_native_runs'] == 12
    assert executed['complete_independent_cold_fuse_runs'] == 4
    assert not executed['release_accepted'] and executed['artifact_acceptance_not_established']
    checked = []
    for row in executed['rows']:
        packed = gzip.decompress((execution / row['source'] / 'soundtrack.ima.gz').read_bytes())
        assert sha(packed) == row['identity']['packed_sha256']
        pulses = (len(packed)*2-3)*16+15
        expected = closed_form_clock(pulses, len(packed))
        for profile, proof in row['actual'].items():
            report, quality = proof['fuse'], proof['quality']
            raw = gzip.decompress((execution / row['source'] / 'verification' / profile / 'times.u32.gz').read_bytes())
            times = np.frombuffer(raw, '<u4')
            np.testing.assert_array_equal(times, expected)
            assert report['complete'] and report['bits_verified'] == pulses
            assert report['reloads'] == report['runtime_disk_reads_during_live_audio'] == 0
            assert sha(raw) == quality['relative_source_timestamps_sha256']
            checked.append(dict(source=row['source'], profile=profile, pulses=pulses,
                                all_ticks_match_closed_form=True, clock_sha256=sha(raw)))
    # Reproduce the earlier ideal449-DAC result without depending on its cache.
    old_path = 'audiobook-beeper/experiments/song-snr/evidence/encoder-audit/ideal-compensated-dac.json'
    old = json.loads(subprocess.run(['git', 'show', '5d10036c:'+old_path],
                                   check=True, capture_output=True).stdout)
    spectra = read(EVIDENCE / 'pacing448-spectrum/report.json')
    assert spectra['complete']
    original = {row['source']: row['ideal_compensated_multilevel_dac']['snr_db'] for row in old}
    for row in spectra['ideal_dac']:
        if row['ordinary_tstates'] == 449:
            assert abs(row['ideal_compensated_multilevel_dac']['snr_db']-original[row['source']]) < 1e-10
    preserved = ['ima_beam.py', 'ima_waveform_encoder.py', 'native_ima_encoder.c',
                 'native_waveform_encoder.c', 'probe_feedback_packets.py']
    diff = subprocess.run(['git', 'diff', '5d10036c', '--'] +
        ['audiobook-beeper/'+name for name in preserved], check=True, capture_output=True).stdout
    assert not diff, 'Original encoder or modulation algorithm changed'
    # The research worktree is sparse; verify the separately delivered main file.
    main_disk = Path(subprocess.run(['git', 'rev-parse', '--git-common-dir'], check=True,
        capture_output=True, text=True).stdout.strip()).resolve().parent / 'ZX-music-Sea-Foam-SNR20-RAM-auto.trd'
    delivered = sha(main_disk.read_bytes())
    assert delivered == 'b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e'
    output = EVIDENCE / 'pacing448-audit'
    output.mkdir(exist_ok=True)
    audit = dict(complete=True, date='2026-10-19', player_manifest_files=len(player_manifest),
        execution_manifest_files=len(execution_manifest), sealed_source_files=sealed,
        complete_host_sources=15, total_pcm8_samples=sum(row['source_samples'] for row in host['rows']),
        actual_clock_checks=checked, original_encoders_and_modulator_unchanged=True,
        delivered_disk_sha256=delivered, ideal449_dac_reproduces_saved_audit=True,
        goal_complete=False, release_accepted=False,
        decision='Reject unconditional448 replacement: noise/corpus regressions and inconclusive artifact controls remain. Preserve mechanism and complete evidence; keep broader goal active.')
    (output / 'audit.json').write_text(json.dumps(audit, indent=2)+'\n', encoding='utf-8')
    files = {}
    for group in GROUPS + ('pacing448-audit',):
        for path in sorted((EVIDENCE / group).rglob('*')):
            if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts:
                raw = path.read_bytes()
                files[path.relative_to(EVIDENCE).as_posix()] = dict(bytes=len(raw), sha256=sha(raw))
    (output / 'manifest.json').write_text(json.dumps(dict(complete=True, artifact_files=files), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(**audit, total_indexed_artifacts=len(files))))


if __name__ == '__main__':
    main()
