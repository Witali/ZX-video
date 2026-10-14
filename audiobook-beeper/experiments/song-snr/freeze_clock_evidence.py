"""Freeze a focused host or complete-execution milestone with exact hashes."""
import argparse
import hashlib
import json
from pathlib import Path


def identity(path):
    data=path.read_bytes()
    return dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('--scope',choices=('host','execution'),required=True)
    p.add_argument('--pathspec',type=Path)
    a=p.parse_args();root=a.evidence.resolve();experiment=root.parent;repository=experiment.parents[2]
    selected=[]
    if a.scope=='host':
        source_files=('host.json','soundtrack.ima.gz','source-preview.wav','compensated-pcm.wav','host-actual.wav','reference.wav')
        for stage in ('clock-compensation','clock-joint'):
            report=json.loads((root/stage/'report.json').read_bytes());assert report['complete'] and len(report['rows'])==9
            selected.extend(root/stage/name for name in ('parameters.json','report.json'))
            for row in report['rows']:
                selected.extend(root/stage/row['source']/name for name in source_files)
        diagnostics=json.loads((root/'clock-diagnostics/report.json').read_bytes())
        assert diagnostics['complete'] and len(diagnostics['sources'])==9
        for folder in ('clock-diagnostics','encoder-audit'):
            selected.extend(path for path in (root/folder).rglob('*') if path.is_file())
        producers=('clock_control.py','artifact_diagnostics.py','test_artifact_diagnostics.py','freeze_clock_evidence.py')
    else:
        for stage in ('clock-compensation','clock-joint'):
            for dest in sorted((root/stage).iterdir()):
                if not dest.is_dir() or not (dest/'verification/execution.json').exists():continue
                run=json.loads((dest/'verification/execution.json').read_bytes());assert run['complete']
                selected.extend(dest/name for name in ('audio.trd','player.json'))
                selected.extend(path for folder in ('assembly','verification') for path in (dest/folder).rglob('*') if path.is_file())
            quality=root/stage/'actual-quality.json'
            if quality.exists():
                assert json.loads(quality.read_bytes())['complete'];selected.append(quality)
            selected.extend((root/stage).glob('*/pentagon*-actual.wav'))
        producers=('execute_clock.py','measure_clock.py','freeze_clock_evidence.py')
    assert all(path.is_file() for path in selected)
    manifest=root/('clock-'+a.scope+'-manifest.json')
    report=dict(complete=True,date='2026-10-14',scope=a.scope,
                artifact_files={str(path.relative_to(root)).replace('\\','/'):identity(path) for path in sorted(set(selected))},
                producers={name:identity(experiment/name) for name in producers},
                main_trd_sha256=identity(repository.parents[1]/'ZX-music-Sea-Foam-RAM-auto.trd')['sha256'])
    # In a task worktree the repository's authoritative main image is outside
    # this checkout. Preserve its immutable identity; never rewrite the image.
    assert report['main_trd_sha256']=='226388fb795ac70cfd940545a9eb73e3e81b6c7e96533dc6deb0c215257338ea'
    manifest.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    if a.pathspec:
        paths=selected+[manifest]+[experiment/name for name in producers]
        a.pathspec.write_text(''.join(str(path.relative_to(repository)).replace('\\','/')+'\n' for path in sorted(set(paths))),encoding='utf-8')
    print(json.dumps(dict(scope=a.scope,artifacts=len(report['artifact_files']),manifest=str(manifest))))


if __name__=='__main__':main()
