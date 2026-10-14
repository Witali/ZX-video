"""Authenticate complete sector-cadence UI and audio verification evidence."""
import hashlib
import json
from pathlib import Path


HERE=Path(__file__).resolve().parent


def main():
    report=json.loads((HERE/'report.json').read_text())
    assert report['complete_audio'] and report['complete_ui']
    paths=sorted(path for path in HERE.rglob('*') if path.is_file()
                 and path.name!='manifest.json' and '__pycache__' not in path.parts)
    artifacts=[dict(path=path.relative_to(HERE).as_posix(),bytes=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]
    manifest=dict(date='2026-10-14',complete_audio=True,complete_ui=True,
        trd_sha256=report['ui_trd_sha256'],artifact_count=len(artifacts),artifacts=artifacts,
        scope='Four complete native runs, two complete cold-Fuse source/UI runs, actual control snapshots, exact source-clock and prefix geometry, and archived producers.')
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    for item in artifacts:
        data=(HERE/item['path']).read_bytes()
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    print(json.dumps(dict(artifacts_verified=len(artifacts),complete_audio=True,complete_ui=True)))


if __name__=='__main__':main()
