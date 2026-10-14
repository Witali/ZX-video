"""Authenticate the consolidated YM3812 layout without rewriting evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def digest(path, normalize=False):
    data = path.read_bytes()
    if normalize:
        data = data.replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    layout = json.loads((HERE / 'layout.json').read_bytes())
    paths = set()
    for entry in layout['entries']:
        path = ROOT / entry['new']
        assert path.resolve().is_relative_to(HERE) and path not in paths, path
        paths.add(path)
        assert digest(path, entry['normalize_lf']) == entry['sha256'], path
        if path.suffix != '.md':
            assert entry['source_sha256'] == entry['sha256'], path
        if entry['action'] == 'move':
            assert not (ROOT / entry['old']).exists(), entry['old']
    # Each evidence report's artifact names are relative to its own directory.
    # Producer identities remain historical; the move does not rebase reports.
    manifests = 0
    for folder in (HERE / 'analysis/ym3812', HERE / 'analysis/ym3812_clicks', HERE / 'analysis/ym3812_sea_foam'):
        for path in folder.rglob('*.json'):
            report = json.loads(path.read_bytes())
            if not isinstance(report, dict):
                continue
            for name, expected in report.get('artifacts_sha256', {}).items():
                assert digest(path.parent / name) == expected, (path, name)
            if report.get('artifacts_sha256'):
                manifests += 1
    links = 0
    for path in HERE.rglob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' in target or target.startswith('#'):
                continue
            assert (path.parent / target.split('#')[0]).exists(), (path, target)
            links += 1
    result = dict(complete=True, date='2026-10-14', moved=layout['moved'],
                  dependency_copies=layout['dependency_copies'], files_checked=len(paths),
                  archived_artifact_manifests_checked=manifests,
                  local_documentation_links_checked=links,
                  all_producer_and_evidence_bytes_unchanged=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
