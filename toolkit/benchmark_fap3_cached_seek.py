"""Compare FAP3 cached seeks with the same-track reader; ROM is mocked."""
import argparse
import json
from pathlib import Path
from benchmark_fap3_disk import run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    rows={}
    for name,options in [('same_track',{}),('cold',dict(cached=255)),
        ('new_side',dict(cached=2)),('new_cylinder',dict(track=4,cached=3)),
        ('track_wrap',dict(sector=15)),('ring_wrap',dict(region=3,high=255)),
        ('short_retry',dict(short=True)),('seek_short_retry',dict(cached=2,short=True))]:
        old=run(fast_disk=True,**options)
        new=run(fast_disk=True,cached_seek=True,**options)
        rows[name]=dict(previous=old,current=new,delta_tstates=new['tstates']-old['tstates'])
    for track in range(160):
        for drive in range(4):
            for region in range(4):
                run(fast_disk=True,cached_seek=True,track=track,sector=15,region=region,
                    high=255,cached=track^1,drive=drive)
    report=dict(baseline_commit='9db8954',scope=__doc__,complete=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',routines=rows,
        geometry_cases=2560,rom_execution_verified=False)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n'); print(json.dumps(report,indent=2))


if __name__=='__main__': main()
