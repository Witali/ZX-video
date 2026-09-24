"""Save complete per-frame/AY/sector evidence without generated TRD images."""
import argparse
import hashlib
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','summary','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); report=json.loads(args.summary.read_text(encoding='utf-8'))
    if not report['complete']: raise ValueError('refuse to archive partial experiment as complete')
    index=[]
    for variant in report['variants']:
        if not variant['complete']: raise ValueError('partial variant')
        for row in variant['volumes']:
            path=args.source/row['full_report']; data=json.loads(path.read_text(encoding='utf-8'))
            if not (data['complete'] and data['frames']==row['frames'] and data['ay_records_exact']
                    and data['trd_sha256']==row['trd_sha256'] and not data['errors']):
                raise ValueError('evidence does not match summary')
            target=args.output/row['full_report']; target.parent.mkdir(parents=True,exist_ok=True)
            blob=(json.dumps(data,separators=(',',':'))+'\n').encode('utf-8')
            target.write_bytes(blob)
            if json.loads(target.read_bytes())!=data: raise AssertionError('archive changed evidence')
            index.append(dict(file=str(target.relative_to(args.output)).replace('\\','/'),
                sha256=hashlib.sha256(blob).hexdigest(),frames=data['frames'],ay_ticks=data['ay_ticks'],
                checked_runtime_sectors=data['runtime_sectors_checked']))
    (args.output/'index.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(reports=len(index),frames=sum(r['frames'] for r in index),
        output=str(args.output)),indent=2))


if __name__=='__main__': main()
