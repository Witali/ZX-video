"""Check saved object identities and host wire data without resuming playback.

This deliberately does not rebuild a disk or run native CPU/Fuse proofs.
The two pending release checks stay pending after this archival validation.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import sys


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(input_root):
    base = Path(__file__).resolve().parent
    evidence = base / 'evidence'
    manifest = json.loads((evidence / 'manifest.json').read_bytes())
    expected = {r['path'] for r in manifest['measured_objects']}
    actual = {p.relative_to(evidence).as_posix() for p in evidence.rglob('*')
              if p.is_file() and p != evidence / 'manifest.json'}
    assert expected == actual, 'Archive inventory differs'
    for record in manifest['measured_objects']:
        path = evidence / record['path']
        assert path.stat().st_size == record['bytes'], record['path']
        assert digest(path) == record['sha256'], record['path']
    toolkit = base.parents[1]
    for snapshot in (evidence / 'current-source').glob('*.py'):
        current = toolkit / snapshot.name
        # Git normalizes tracked Python endings; LFS preserves the stopped
        # Windows source bytes exactly. Compare text without changing either.
        assert current.read_text(encoding='utf-8') == snapshot.read_text(encoding='utf-8'), snapshot.name
        ast.parse(current.read_text(encoding='utf-8'), filename=str(current))
    for source in base.glob('*.py'):
        ast.parse(source.read_text(encoding='utf-8'), filename=str(source))
    sys.path.insert(0, str(toolkit))
    import numpy as np
    from native_modeplane import decode_check
    original = np.load(input_root / 'toolkit/analysis/native_lineart/evidence/work/native-states.npy')
    checks = {}
    summary = json.loads((evidence / 'summary.json').read_bytes())
    mismatches = []
    for name, trial in summary['trials'].items():
        folder = evidence / 'session' / name
        metadata = json.loads((folder / 'metadata.json').read_bytes())
        assert digest(folder / 'candidate.trd') == metadata['trd_sha256'] == trial['trd_sha256']
        frames = np.load(folder / 'states.npz')['states']
        if name == 'stored-compat':
            sampling = json.loads((folder / 'sampling.json').read_bytes())
            assert np.array_equal(frames, original[sampling['source_indices']])
        else:
            assert np.array_equal(frames, original)
        representation = json.loads((folder / 'representation.json').read_bytes())
        checks[name] = decode_check((folder / 'codebook.raw').read_bytes(),
                                   frames, 0, len(frames), representation['rows'])
        timing = folder / 'timing.json'
        if timing.exists():
            report = json.loads(timing.read_bytes())
            if report['trd_sha256'] != metadata['trd_sha256']:
                mismatches.append(name)
    assert mismatches == ['modeplane'], mismatches
    return dict(archive_files_exact=manifest['files'], archive_bytes=manifest['bytes'],
                current_source_syntax_and_snapshots_exact=True, source_line_endings_normalized=True,
                host_wire_checks=checks, known_timing_mismatches=mismatches,
                new_playback_runs=0, release=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True,
                        help='Checkout with the frozen native-lineart input archive')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = verify(args.input_root)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result))
