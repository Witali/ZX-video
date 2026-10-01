"""Archive completed host probes and their files without promoting them to releases."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('probe','evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--tests',type=Path);p.add_argument('--decision',required=True)
    a=p.parse_args();report=json.loads((a.probe/'report.json').read_bytes())
    assert report['complete'] and not report['release']
    for name,identity in report['source_sha256_lf'].items():
        assert sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))==identity,name
    a.evidence.mkdir(parents=True,exist_ok=True);artifacts=[]
    paths=sorted(path for path in a.probe.iterdir() if path.is_file())
    if a.tests:
        assert a.tests.read_text().strip().endswith('OK');paths.append(a.tests)
    for path in paths:
        data=path.read_bytes();prepacked=path.suffix=='.gz';image=path.suffix=='.trd'
        raw=gzip.decompress(data) if prepacked else data
        packed=data if prepacked or image else gzip.compress(data,mtime=0)
        target=a.evidence/(path.name if prepacked or image else path.name+'.gz');target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(packed),
            raw_bytes=len(raw),archive_bytes=len(packed)))
    report.update(artifacts=artifacts,decision=a.decision)
    write_json(a.output,report);print(json.dumps(dict(artifacts=len(artifacts),decision=a.decision)))


if __name__=='__main__':main()
