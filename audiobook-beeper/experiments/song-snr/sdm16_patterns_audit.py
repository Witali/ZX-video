"""Independently tie the pattern-sharing proof to the unchanged player macros.

This does not execute a disk or approve a precision implementation. It checks
every saved artifact and assembles the actual player's complete FIRST/SECOND
macro fragment at the experiment's addresses, then compares every code byte.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys


HERE = Path(__file__).resolve().parent
AUDIO = HERE.parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, default=HERE / 'evidence/sdm16-patterns')
    parser.add_argument('--output', type=Path, default=HERE / 'evidence/sdm16-patterns-audit')
    args = parser.parse_args()
    evidence, output = args.evidence.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((evidence / 'manifest.json').read_text())
    listed = set()
    for item in manifest['artifacts']:
        path = evidence / item['path']
        assert path.is_relative_to(evidence)
        assert path.stat().st_size == item['bytes'] and digest(path) == item['sha256'], path
        listed.add(item['path'])
    actual = {p.relative_to(evidence).as_posix() for p in evidence.rglob('*')
              if p.is_file() and p.name != 'manifest.json' and '__pycache__' not in p.parts}
    assert listed == actual and len(listed) == manifest['files']
    assert gzip.decompress((evidence / 'generator.py.gz').read_bytes()) == (HERE / 'sdm16_patterns.py').read_bytes()
    report = json.loads((evidence / 'report.json').read_text())
    assert report['complete'] and not report['release_accepted']
    catalogue = HERE / 'evidence/sdm16-architecture/model-b-all-pcm16-cells.npz'
    assert digest(catalogue) == report['catalogue_sha256']

    labels = next(ast.literal_eval(line) for line in (evidence / 'baseline/assembler.log').read_text().splitlines()
                  if line.startswith('{'))
    player = AUDIO / 'stream-player.asm'
    text = player.read_text()
    fragment = text[text.index('PULSE: MACRO'):text.index('\ncode_end:')]
    # Assemble the unchanged repository macros, not a second hand transcription
    # of the experiment's generator. External symbols retain the exact native
    # experiment values; neither loader nor worker participates in this audit.
    constants = dict(extended_ram=1, first_size=42, pcm_high=0x5E00,
                     page_tail_0=labels['page_tail_0'], page_tail_1=labels['page_tail_1'])
    for value in range(256):
        constants[f'first_address_{value}'] = labels.get(f'first_{value}', -1)
        constants[f'second_address_{value}'] = labels.get(f'second_{value}', -1)
    source = ('; Actual unchanged player macro fragment, independently assembled.\n' +
              ''.join(f'{key}: EQU {value}\n' for key, value in constants.items()) +
              ' ORG 0x8340\n' + fragment + '\n DEFB 165\n')
    (output / 'actual-player-patterns.asm').write_text(source, encoding='utf-8', newline='\n')
    run = subprocess.run([sys.executable, '-m', 'pyz80.pyz80', '--obj=actual-player-patterns.bin',
                          '--lstfile=actual-player-patterns.lst', 'actual-player-patterns.asm'],
                         cwd=output, capture_output=True, text=True)
    (output / 'assembler.log').write_text(run.stdout + run.stderr, encoding='utf-8')
    if run.returncode:
        raise RuntimeError(run.stdout + run.stderr)
    # pyz80 omits a final DS reservation unless a later emitted byte seals it.
    original_with_sentinel = (output / 'actual-player-patterns.bin').read_bytes()
    assert original_with_sentinel[-1] == 165
    original = original_with_sentinel[:-1]
    baseline = (evidence / 'baseline/kernel.bin').read_bytes()
    expected = baseline[labels['first_begin'] - 0x8000:labels['second_end'] - 0x8000]
    assert original == expected and len(original) == 13732
    pairs = sum(row['native_before_after_cases'] for profiles in report['verification'].values()
                for row in profiles.values())
    assert pairs == 18864
    audit = dict(complete=True, checked_artifact_files=len(listed), native_before_after_pairs=pairs,
                 actual_repository_pattern_bytes_matched=len(original),
                 actual_player_sha256=digest(player), catalogue_sha256=digest(catalogue),
                 patterns_report_sha256=digest(evidence / 'report.json'),
                 artifact_manifest_sha256=digest(evidence / 'manifest.json'),
                 frozen_generator_matches=True, actual_disk_or_ULA_execution=False,
                 full_precision_selector_implemented=False, release_accepted=False)
    (output / 'report.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    (output / 'auditor.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    items = [dict(path=p.relative_to(output).as_posix(), bytes=p.stat().st_size, sha256=digest(p))
             for p in sorted(output.rglob('*')) if p.is_file() and p.name != 'manifest.json']
    (output / 'manifest.json').write_text(json.dumps(dict(files=len(items), artifacts=items), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(audit))


if __name__ == '__main__':
    main()
