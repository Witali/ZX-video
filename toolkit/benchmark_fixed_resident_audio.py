"""Count every native AY tick of the selected volumes with old/shared models."""
import argparse
import json
from pathlib import Path

from benchmark_resident_audio_z80 import Harness
from build_fap3_trd import sha
from convert_video import write_json


def measure(data,fixed,*,fixed_tail=False):
    h=Harness(data,paging=True,batch=31,fixed=fixed,single_bank=6 if fixed_tail else 4,fixed_tail=fixed_tail);calls=[];consumer=0
    while h.consumed<len(h.records):
        cycles,count=h.fill_wrapped();assert count>0
        calls.append(dict(tstates=cycles,ticks=count))
        for _ in range(count):consumer+=h.consume()
    h.finish()
    return dict(records=len(h.records),initial=h.initial.hex(),records_sha256=sha(b''.join(h.records)),
        init_tstates=h.init_tstates,fill_tstates=sum(v['tstates'] for v in calls),
        consumer_tstates=consumer,refills=calls,all_records_and_ay_exact=True,
        fixed_bytes=h.build.get('fixed_bytes'),payload_bytes=h.build.get('payload_bytes'),
        bank6_reserved_bytes=h.build.get('bank6_reserved_bytes'),
        compiled=h.build if fixed else dict(bank_bytes=[s['image_bytes'] for s in h.build['segments']]))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',action='append',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--fixed-tail',action='store_true',help='compare bank-6 plus fixed tail against the bank-spanning shared model')
    a=p.parse_args();rows=[]
    for path in a.input:
        data=path.read_bytes();before=measure(data,a.fixed_tail);after=measure(data,True,fixed_tail=a.fixed_tail)
        for key in ('records','initial','records_sha256','consumer_tstates'):assert before[key]==after[key]
        rows.append(dict(input=path.name,input_sha256=sha(data),before=before,after=after,
            fill_delta_tstates=after['fill_tstates']-before['fill_tstates']))
        write_json(a.output,dict(complete=len(rows)==len(a.input),release=False,scope=__doc__,parts=rows,
            real_irqs_or_disk_measured=False))
        print(json.dumps(dict(part=path.name,ticks=after['records'],fill_before=before['fill_tstates'],
            fill_after=after['fill_tstates'],fixed_bytes=after['fixed_bytes'],bank6_tail=after['bank6_reserved_bytes'])),flush=True)


if __name__=='__main__':main()
