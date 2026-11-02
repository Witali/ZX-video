"""Reproduce resident art compression with the project's pinned ZX0/LZSA CLIs.

Both adapters authenticate complete byte-exact round trips. Comparison LZSA
fixtures are not placed on the release disk. CLI binaries are local tools.
"""
import argparse
import json
import sys
from demo_assets import HERE, NAMES
from slides import picture_columns
import zx0
sys.path.insert(0,str(HERE.parent/'libraries/lzsa/src'))
import lzsa


def measure(zx0_executable,lzsa_executable):
    output=HERE/'artwork/packed'
    output.mkdir(exist_ok=True)
    rows=[]
    for name in NAMES:
        path=HERE/'artwork'/f'{name}.scr'
        if not path.exists():
            path=HERE/'artwork/proposals'/path.name
        raw=b''.join(picture_columns(path.read_bytes()))
        z=zx0.compress(raw,executable=zx0_executable)
        l=lzsa.compress(raw,executable=lzsa_executable)
        (output/f'{name}.zx0').write_bytes(z)
        (output/f'{name}.lzsa').write_bytes(l)
        rows.append(dict(name=name,raw_bytes=len(raw),zx0_bytes=len(z),lzsa_bytes=len(l)))
    report=dict(zx0_revision='ecde3a2ae05061fe06469ed46df81a33b7de7d86',
        lzsa_revision='15ee2dfe118eeb8f7683ca44f64821c3a61ca1e5',
        roundtrips_exact=True,images=rows)
    (output/'compression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(zx0_bytes=sum(r['zx0_bytes'] for r in rows),
                          lzsa_bytes=sum(r['lzsa_bytes'] for r in rows))))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--zx0',default='zx0')
    p.add_argument('--lzsa',default='lzsa')
    args=p.parse_args()
    measure(args.zx0,args.lzsa)
