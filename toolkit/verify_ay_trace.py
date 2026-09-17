"""Verify every AY update actually executed by Fuse against the encoded stream."""
import argparse
import hashlib
import json
from pathlib import Path

import ay_interrupt
import build_long_video_trd as video


def verify(timing, frames):
    expected=ay_interrupt.encode_ticks(frames)
    ticks=timing['audio_ticks'];writes=timing['audio_writes']
    if len(ticks)!=len(frames):raise AssertionError(f'{len(ticks)} ticks instead of {len(frames)}')
    if not ticks or any(a>=b for a,b in zip(ticks,ticks[1:])):
        raise AssertionError('empty or non-increasing tick timestamps')
    if any(a['tstate']>=b['tstate'] for a,b in zip(writes,writes[1:])):
        raise AssertionError('non-increasing write timestamps')
    cursor=0;empty=0;registers=bytearray(11)
    for index,(end,record,frame) in enumerate(zip(ticks,expected,frames)):
        actual=[]
        while cursor<len(writes) and writes[cursor]['tstate']<=end:
            event=writes[cursor];actual.append((event['register'],event['value']))
            registers[event['register']]=event['value'];cursor+=1
        wanted=list(zip(record[1::2],record[2::2]))
        if actual!=wanted:raise AssertionError(f'AY writes at tick {index}: {actual} != {wanted}')
        if registers!=ay_interrupt.registers(frame):raise AssertionError(f'AY registers at tick {index}')
        if not wanted:empty+=1
    if cursor!=len(writes):raise AssertionError('writes after last tick')
    intervals=[(b-a)*1000/timing['clock_hz'] for a,b in zip(ticks,ticks[1:])]
    return dict(ticks=len(ticks),verified_register_writes=len(writes),unchanged_ticks_without_io=empty,
                interval_min_ms=min(intervals,default=None),interval_mean_ms=sum(intervals)/len(intervals) if intervals else None,
                interval_max_ms=max(intervals,default=None),intervals_over_25ms=sum(x>25 for x in intervals),
                interval_scope='end of each handler; differing numbers of writes slightly move the trace point')


def verify_build(metadata,timing,raw):
    if len(timing)!=len(metadata['volumes']):raise AssertionError('missing or extra volume trace')
    if len(raw)!=metadata['frames']*6*9:raise AssertionError('audio length differs from video')
    if hashlib.sha256(raw).hexdigest()!=metadata['audio_source']['sha256']:
        raise AssertionError('audio hash differs from build')
    frames=[video.AyFrame.deserialize(raw[i:i+9]) for i in range(0,len(raw),9)]
    results=[];next_frame=0
    for volume,trace in zip(metadata['volumes'],timing):
        if volume['frame_start']!=next_frame:raise AssertionError('gap or overlap between volumes')
        first,last=volume['frame_start']*6,volume['frame_end']*6
        result=verify(trace,frames[first:last]);result['frame_start']=volume['frame_start'];results.append(result)
        next_frame=volume['frame_end']
    if next_frame!=metadata['frames']:raise AssertionError('incomplete video coverage')
    return dict(ticks=sum(r['ticks'] for r in results),volumes=results,
                continuous_single_disk=len(results)==1)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path)
    p.add_argument('--source',type=Path,required=True,help='raw nine-byte states at 50 Hz')
    p.add_argument('--timing',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    metadata=json.loads((args.build/'build_metadata.json').read_text())
    timing=json.loads(args.timing.read_text())
    raw=args.source.read_bytes()
    report=verify_build(metadata,timing,raw)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
