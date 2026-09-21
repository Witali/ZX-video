"""Count the interleaved FAP3 cursor and verify all physical sector IDs."""
import argparse
import json
from pathlib import Path
from benchmark_fap3_disk import run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True); args=p.parse_args()
    rows=[]
    for sector in range(16):
        old=run(fast_disk=True,cached_seek=True,sector=sector)
        new=run(fast_disk=True,cached_seek=True,sector=sector,interleaved=True)
        rows.append(dict(sector=sector,previous=old,current=new,
            delta_tstates=new['tstates']-old['tstates']))
    for track in range(160):
        for region in range(4):
            for sector in range(16):
                run(fast_disk=True,cached_seek=True,interleaved=True,track=track,
                    sector=sector,region=region,high=255,cached=track^1)
    report=dict(baseline_commit='5ddc5a0',complete=True,scope=__doc__,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        excludes='ROM, disk latency, IRQ and ULA',routines=rows,geometry_cases=10240)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__': main()
