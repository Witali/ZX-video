"""Authenticate this completed control and its separate ideal-clock comparison."""
import argparse
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');a=p.parse_args()
    manifest=HERE/'manifest.json'
    if a.verify:
        saved=json.loads(manifest.read_bytes())
        for name,row in saved['artifacts'].items():
            blob=(ROOT/name).read_bytes()
            assert len(blob)==row['bytes'] and hashlib.sha256(blob).hexdigest()==row['sha256'],name
        print(f"Verified {len(saved['artifacts'])} artifacts")
        return
    files=sorted(f for f in (HERE/'qualified').rglob('*') if f.is_file())
    files += [ROOT/'ZX-audiobook-mulaw-test.trd']
    artifacts={str(f.relative_to(ROOT)).replace('\\','/'):dict(bytes=f.stat().st_size,
               sha256=hashlib.sha256(f.read_bytes()).hexdigest()) for f in files}
    manifest.write_text(json.dumps(dict(complete=True,artifacts=artifacts),indent=2)+'\n',encoding='utf-8')
    print(f'Archived {len(artifacts)} artifacts')


if __name__=='__main__':main()
