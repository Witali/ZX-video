"""Conservatively restore original packets when a host transform exceeds budgets.

Each iteration freezes all frame packets touching a failed ORIGINAL block.
Replan physical attribute histories before measuring again; mixing already
encoded alternatives would be unsafe because removed writes affect history.
The monotonic frozen set terminates at the original stream in the worst case.
No player, image, audio, dictionary, frame rate or disk-image changes.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_fap3_trd import sha
from convert_video import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('metadata','lzsa','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    m=json.loads(a.metadata.read_bytes())
    frozen=set();rounds=[]
    for index in range(m['frames']+1):
        folder=a.output/f'round{index:02d}'
        freeze_file=a.output/'frozen-frames.json'
        write_json(freeze_file,sorted(frozen))
        command=[sys.executable,str(Path(__file__).with_name('probe_invisible_attributes.py')),
            '--metadata',str(a.metadata),'--lzsa',str(a.lzsa),'--output',str(folder),
            '--fit-cpu-budget','--frozen-frames',str(freeze_file)]
        subprocess.run(command,check=True)
        result=json.loads((folder/'report.json').read_bytes())
        failed=[b['index'] for b in result['blocks'] if not b['budget_met']]
        rounds.append(dict(index=index,folder=folder.name,failed_blocks=failed,
            frozen_frames=len(frozen),bytes=result['stream_bytes_after'],
            decoder_tstates=result['decoder_tstates_after'],removed=result['removed_attribute_writes']))
        report=dict(complete=not failed,release=False,scope=__doc__,rounds=rounds,
            metadata_sha256=sha(a.metadata.read_bytes()),selected=folder.name if not failed else None,
            source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
        write_json(a.output/'report.json',report)
        if not failed:
            print(json.dumps(report),flush=True)
            return
        previous=len(frozen)
        for block in failed:
            lo,hi=m['blocks'][block]['raw_start'],m['blocks'][block]['raw_end']
            frozen.update(d['frame'] for d in result['details']
                if d['original_raw_start']<hi and d['original_raw_end']>lo)
        if len(frozen)==previous:
            raise AssertionError('unchanged blocks still exceed their original budgets')
    raise AssertionError('monotonic restoration did not terminate')


if __name__=='__main__':main()
