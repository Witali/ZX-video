"""Summarise verified frame timing and pinpoint any intervals over 125 ms."""
import argparse
import json
from pathlib import Path


def summarize(metadata,traces):
    if len(metadata['volumes'])!=len(traces):raise ValueError('missing volume trace')
    volumes=[]
    for volume,trace in zip(metadata['volumes'],traces):
        late=[]
        for index,tstates in enumerate(trace['frame_interval_tstates']):
            if tstates*1000/trace['clock_hz']<=125:continue
            prepared=trace['frame_prepared_timestamps'][index]
            previous,shown=trace['frame_timestamps'][index:index+2]
            reads=[cycles*1000/trace['clock_hz'] for frame,cycles in
                   zip(trace['rom_call_entry_frames'],trace['rom_call_tstates']) if frame==index]
            late.append(dict(frame=volume['frame_start']+index+1,
                interval_ms=tstates*1000/trace['clock_hz'],
                preparation_since_previous_flip_ms=(prepared-previous)*1000/trace['clock_hz'],
                after_preparation_ms=(shown-prepared)*1000/trace['clock_hz'],
                decode_fields=trace['decode_fields'][index],rom_intervals_ms=reads))
        volumes.append(dict(frames=volume['frames'],frame_start=volume['frame_start'],
            maximum_ms=trace['frame_interval_max_ms'],mean_ms=trace['frame_interval_mean_ms'],
            fps=trace['measured_fps'],late_frames=late))
    return dict(frames=sum(v['frames'] for v in volumes),volumes=volumes,
                intervals_over_125ms=sum(len(v['late_frames']) for v in volumes))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--timing',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    result=summarize(json.loads((args.build/'build_metadata.json').read_text()),json.loads(args.timing.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
