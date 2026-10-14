"""Archive the stopped native-delivery experiment without rebuilding it.

Run from its worktree. Preserve session scripts and measured objects exactly,
excluding disposable ZX0 caches and Python bytecode. Existing evidence is
never overwritten. SHA256 identities distinguish old measurements from the
latest, partially verified source. No emulator or converter is launched.
"""
from pathlib import Path
import hashlib
import json
import shutil


SOURCES = (
    'cell_codebook_player.py', 'compressed_sector_cache.py',
    'fixed_resident_audio.py', 'streaming_lzsa2_player.py',
    'native_modeplane.py', 'native_modeplane_z80.py', 'stored_native_queue.py',
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(root):
    target = root / 'toolkit/analysis/native_sync/evidence'
    if target.exists():
        raise FileExistsError('Refusing to replace existing measured evidence')
    session = root / '.tmp'
    files = sorted(p for p in session.rglob('*') if p.is_file()
                   and 'zx0' not in p.relative_to(session).parts
                   and '__pycache__' not in p.relative_to(session).parts)
    for source in files:
        destination = target / 'session' / source.relative_to(session)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        assert digest(source) == digest(destination)
    for name in SOURCES:
        destination = target / 'current-source' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(root / 'toolkit' / name, destination)
    trials = {}
    for folder in ('modeplane', 'stored-modeplane', 'stored-zeros',
                   'stored-repeat', 'stored-repeat-flags', 'stored-compat'):
        base = target / 'session' / folder
        metadata = json.loads((base / 'metadata.json').read_bytes())
        result = dict(trd_sha256=digest(base / 'candidate.trd'),
                      metadata_trd_sha256=metadata['trd_sha256'],
                      used_sectors=metadata['used_sectors'],
                      frame_fields=metadata['frame_fields'],
                      video_bytes=metadata['video_bytes'], release=False)
        assert result['trd_sha256'] == result['metadata_trd_sha256']
        if (base / 'timing.json').exists():
            timing = json.loads((base / 'timing.json').read_bytes())
            result['timing'] = {k: timing[k] for k in (
                'trd_sha256', 'complete', 'frames', 'ay_ticks',
                'ay_records_exact', 'nominal_late_frames', 'max_late_fields',
                'max_actual_deviation_tstates', 'full_pixel_comparison',
                'elapsed_timing', 'late_runs')}
            result['timing_matches_saved_trd'] = (
                timing['trd_sha256'] == result['trd_sha256'])
        trials[folder] = result
    summary = dict(
        date='2026-10-14', baseline_commit='dbde780cff38c4a8bede73c325f5c1aba85f166f',
        scope='Stopped experimental native video delivery; save progress only',
        release=False, main_format_defaults_changed=False,
        progress_bar_changed=False, broad_accuracy_goal_resumed=False,
        trials=trials,
        known_mismatch='modeplane/timing.json measures eaee320c...; its later '
        'overwritten candidate/metadata are the invalid daacc928... stored '
        'reader plus LZSA stream. Preserve both identities; do not play or '
        'attribute that timing to the saved candidate.',
        pending='Latest 10-fps flags variant has cold proof only. Compatibility '
        '25/3-fps disk has full real-Fuse timing/AY plus cold proof; complete '
        'screen-byte capture and independent packet CPU replay remain pending.')
    (target / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    manifest = []
    for path in sorted(p for p in target.rglob('*') if p.is_file()):
        manifest.append(dict(path=path.relative_to(target).as_posix(),
                             bytes=path.stat().st_size, sha256=digest(path)))
    report = dict(files=len(manifest), bytes=sum(r['bytes'] for r in manifest),
                  excludes=['ZX0 executable output caches', 'Python bytecode'],
                  measured_objects=manifest)
    (target / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=report['files'], bytes=report['bytes'],
                          target=str(target))))


if __name__ == '__main__':
    save(Path.cwd())
