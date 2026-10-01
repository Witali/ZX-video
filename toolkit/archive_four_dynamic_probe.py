"""Archive the selected four-volume size probe; keep capacity failure explicit."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('probe','tests','evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    report=json.loads((a.probe/'report.json').read_bytes());assert report['complete']
    assert len(report['volumes'])==4 and report['candidate_partitions_encoded']==1
    assert any(part['video_sectors']>2544 for part in report['volumes'])
    for i,part in enumerate(report['volumes'],1):
        assert sha((a.probe/f'part{i:02}.raw').read_bytes())==part['raw_sha256']
        assert sha((a.probe/f'part{i:02}.stream').read_bytes())==part['stream_sha256']
    report['source_sha256_lf']['balance_cb41_cadence.py']=sha(Path(__file__).with_name('balance_cb41_cadence.py').read_bytes().replace(b'\r\n',b'\n'))
    artifacts=[]
    for path in sorted(a.probe.glob('*'))+[a.tests]:
        if not path.is_file():continue
        raw=path.read_bytes();packed=gzip.compress(raw,mtime=0);target=a.evidence/(path.name+'.gz');target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(packed),
            raw_bytes=len(raw),archive_bytes=len(packed)))
    report.update(artifacts=artifacts,capacity_met=False,
        video_only_spare_sectors=report['available_sectors']-report['video_sectors'],
        decision='Do not build this candidate: at least one video stream alone exceeds disk capacity; sound and startup require additional space.',
        player_instruction_delta_tstates=0)
    write_json(a.output,report)
    print(json.dumps(dict(artifacts=len(artifacts),video_sectors=report['video_sectors'],capacity_met=False)))


if __name__=='__main__':main()
