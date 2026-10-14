"""Hash the initial UI experiment evidence, including unsuccessful attempts."""
import hashlib
import json
from pathlib import Path


HERE=Path(__file__).resolve().parent


def main():
    paths=sorted(path for path in HERE.rglob('*') if path.is_file()
                 and path.name!='manifest.json' and '__pycache__' not in path.parts)
    artifacts=[dict(path=path.relative_to(HERE).as_posix(),bytes=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths]
    manifest=dict(date='2026-10-14',accepted_ui=False,complete_audio=True,
        trd_sha256='55216119144fdb4e574bb3525b496d15c528b6f1a826da39c5070c3f57be9e1d',
        artifact_count=len(artifacts),artifacts=artifacts,
        scope='Initial FRAMES-based loading animation experiment, including complete source clocks and explicitly unsuccessful captures. No subsequent repair evidence.')
    (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    for item in artifacts:
        data=(HERE/item['path']).read_bytes()
        assert len(data)==item['bytes'] and hashlib.sha256(data).hexdigest()==item['sha256']
    print(json.dumps(dict(artifacts_verified=len(artifacts),complete_audio=True,complete_ui=False)))


if __name__=='__main__':main()
