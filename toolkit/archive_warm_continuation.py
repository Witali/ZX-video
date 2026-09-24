"""Archive exact full Fuse evidence and EOF RAM provenance for the warm probe."""
import argparse
import json
from pathlib import Path
from build_fap3_trd import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source','summary','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();summary=json.loads(a.summary.read_text())
    if not summary['complete']:raise ValueError('incomplete summary')
    a.output.mkdir(parents=True,exist_ok=True);index=[]
    for row in summary['volumes']:
        name=f'fuse_part{row["part"]:02}.json';path=a.source/name
        blob=path.read_bytes();data=json.loads(blob)
        if sha(blob)!=row['report_sha256'] or not data['complete'] or data['trd_sha256']!=row['trd_sha256']:
            raise ValueError('evidence mismatch')
        compact=(json.dumps(data,separators=(',',':'))+'\n').encode()
        (a.output/name).write_bytes(compact)
        index.append(dict(file=name,sha256=sha(compact),original_report_sha256=sha(blob),
            frames=data['frames'],ay_ticks=data['ay_ticks'],runtime_sectors=data['runtime_sectors_checked'],
            eof_ram_sha256=data['warm_ram_sha256']))
    (a.output/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(index),flush=True)


if __name__=='__main__':main()
