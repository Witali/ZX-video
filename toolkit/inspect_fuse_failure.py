"""Locate a failed Fuse breakpoint in its volume and source timeline."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--volume',type=int,required=True)
    p.add_argument('--trace',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();meta=json.loads((args.build/'build_metadata.json').read_text())
    volume=meta['volumes'][args.volume-1]
    numbers=[int(line.strip(),0) for line in args.trace.read_text(errors='replace').splitlines()
             if re.fullmatch(r'(?:0x[0-9a-fA-F]+|-?\d+)',line.strip())]
    if len(numbers)%2:raise ValueError('incomplete trace pairs')
    events=list(zip(numbers[::2],numbers[1::2]))
    frames=[t for e,t in events if e==101];ticks=[t for e,t in events if e==143]
    pc=next(t for e,t in reversed(events) if e==197)
    labels=[name for name,value in meta['player_labels'].items() if value==pc]
    report=dict(volume=args.volume,trd_sha256=hashlib.sha256((args.build/volume['trd_name']).read_bytes()).hexdigest(),
        failure_pc=pc,failure_labels=labels,visible_frames=len(frames),completed_audio_ticks=len(ticks),
        last_visible_source_frame=volume['frame_start']+len(frames)-1,
        next_source_frame=volume['frame_start']+len(frames),
        recent_frame_intervals_ms=[(b-a)/3546.9 for a,b in zip(frames[-11:-1],frames[-10:])],
        scope='Fuse breakpoint failure; ROM/ULA/IRQ/disk included in wall time')
    first=volume['frame_start'];near=[]
    for block in volume['blocks']:
        last=first+block['frames']
        if first<=report['next_source_frame'] and last>=report['last_visible_source_frame']:
            near.append(dict(first=first,last=last,**block))
        first=last
    report['nearby_blocks']=near
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
