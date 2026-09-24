"""Paired complete-frame CPU samples; partial samples cannot certify a movie.

Input is unchanged FAP3. Compares native/compact RAM and AY through cpu_profile,
which executes the complete player with ideal delivery. Separate full Fuse
measurements include the disk and ULA; do not combine the two time totals.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from run_deferred_disk import ReadThroughBuilder
from profile_fap3 import cpu_profile


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','states','zx0','cache','report'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--read-cache',type=Path,action='append',default=[])
    p.add_argument('--ranges',default='62:94,408:440,1269:1301,2159:2191,2334:2366,2919:2951,3195:3227,3838:3870')
    args=p.parse_args(); raw=args.raw.read_bytes()
    with np.load(args.states,allow_pickle=False) as saved:states=saved['states']
    ranges=[tuple(map(int,s.split(':'))) for s in args.ranges.split(',')]
    if any(len(pair)!=2 or not 0<=pair[0]<pair[1]<=len(states) for pair in ranges):p.error('invalid ranges')
    report=dict(complete=False,full_movie=False,release=False,baseline_commit='80ab9d9',
        raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),ideal_disk=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',ranges=[])
    args.report.parent.mkdir(parents=True,exist_ok=True)
    def save():args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    builders=[]
    for inline in (False,True):
        b=ReadThroughBuilder(raw,states,args.zx0.resolve(),args.cache,inline_matches=inline)
        b.read_cache=args.read_cache;builders.append(b)
    save()
    for start,end in ranges:
        pair=[]
        for b in builders:
            print(f'CPU inline={b.inline_matches}, frames {start}..{end-1}',flush=True)
            data=cpu_profile(b,start,end)
            # Full executed histogram is kept for the separate 379-block
            # benchmark. These records keep per-frame stages and publications.
            for key in ('instruction_listing','instruction_histogram','irq_instruction_histogram'):data.pop(key)
            pair.append(data)
        old,new=pair
        row=dict(start=start,end=end,baseline=old,inline=new,
            foreground_delta=new['foreground_tstates']-old['foreground_tstates'],
            old_missed=sum(p['late_fields']>0 for p in old['publications']),
            new_missed=sum(p['late_fields']>0 for p in new['publications']))
        report['ranges'].append(row);save()
        print(json.dumps({k:row[k] for k in ('start','end','foreground_delta','old_missed','new_missed')}),flush=True)
    report['complete']=True;save()


if __name__=='__main__':main()
