"""Save the tested assembly, runnable images and compact reproducible evidence."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def copy(source,target):
    data=source.read_bytes()
    if source.suffix!='.gz':
        data=b'\n'.join(line.rstrip(b' \t') for line in data.replace(b'\r\n',b'\n').split(b'\n'))
    target.write_bytes(data)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'build/speex-port')
    a=p.parse_args();out=a.output
    assembly=HERE/'assembly';assembly.mkdir(exist_ok=True)
    evidence=HERE/'evidence';evidence.mkdir(exist_ok=True)
    for name in ('decoder.s','filter.s','player.ihx','player.map'):
        copy(out/'pure-fast'/name,assembly/name)
    for name in ('host-report.json','source.json','primitives.json','stream-checks.json'):
        copy(out/name,evidence/name)
    for name in ('input.spxraw','reference.pcm16'):
        (evidence/(name+'.gz')).write_bytes(gzip.compress((out/name).read_bytes(),mtime=0))
    for variant in ('z80','pure-asm','pure-fast'):
        target=evidence/variant;target.mkdir(exist_ok=True)
        for name in ('player.ihx','player.map','report.json','out-times.u64.gz'):
            copy(out/variant/name,target/name)
    manifest={str(p.relative_to(HERE)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
              for d in (assembly,evidence) for p in sorted(d.rglob('*')) if p.is_file() and p.name!='manifest.json'}
    (evidence/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',newline='\n')
    print(f'Saved {len(manifest)} files; all decoder images remain non-real-time.')


if __name__=='__main__':main()
