"""Measure mixed bank-6 filtering, keeping inline executable bytes unfiltered."""
import argparse
import json
from pathlib import Path
from build_fap3_trd import Builder,sha,sectors
from probe_startup_tables import difference,undifference
from zx0_codec import decompress


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('build-report','cache','zx0','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();baseline=json.loads(a.build_report.read_bytes())
    b=Builder.__new__(Builder);b.memo={};b.cache=a.cache;b.zx0=a.zx0.resolve()
    report=[]
    for v in baseline['volumes']:
        s=v['sections'][0]
        blob=(a.cache/(s.get('storage_sha256',s['sha256'])+'.zx0')).read_bytes()
        raw=decompress(blob,limit=16384)
        if s.get('startup_delta'):raw=undifference(raw)
        if sha(raw)!=s['sha256']:raise ValueError('wrong source bank')
        storage=difference(raw[:0x2c00])+raw[0x2c00:0x3000]+difference(raw[0x3000:])
        restored=undifference(storage[:0x2c00])+storage[0x2c00:0x3000]+undifference(storage[0x3000:])
        if restored!=raw:raise AssertionError('mixed filter roundtrip')
        packed=b.compress(storage)
        report.append(dict(part=v['part'],baseline_bytes=s['compressed_bytes'],bytes=len(packed),
            sectors=sectors(packed),roundtrip_exact=True,storage_sha256=sha(storage),raw_sha256=sha(raw)))
    a.output.write_text(json.dumps(dict(offline_only=True,variants=report),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report))


if __name__=='__main__':main()
