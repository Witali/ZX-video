"""Audit complete packet-copy costs separately from incomplete video timing."""
import argparse
from hashlib import sha256
import json
from pathlib import Path

from assess_frame_jitter import assess
from stream_reader_z80 import copy_tstates


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','reader','output'): p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(); paths=(args.before,args.after,args.reader)
    old,new,reader=[json.loads(path.read_text(encoding='utf-8')) for path in paths]
    if len({r['raw_sha256'] for r in (old,new,reader)})!=1: raise ValueError('different stream')
    if old['states_sha256']!=new['states_sha256'] or old['packet_ahead']!=new['packet_ahead']:
        raise ValueError('different frame/schedule inputs')
    if not reader['complete'] or not new['unrolled_copy']: raise ValueError('reader experiment incomplete')
    if old['compressed_bytes']!=new['compressed_bytes'] or new['compressed_bytes']!=reader['compressed_bytes']:
        raise ValueError('different compressed bytes')
    common=min(old['checked']['publish'],new['checked']['publish'])
    trials=[]
    for path,r in zip(paths,(old,new,reader)):
        trial=dict(report=path.name,sha256=sha256(path.read_bytes()).hexdigest(),complete=r['complete'])
        if 'publications' in r:
            trial.update(checked=r['checked'],failure=r.get('failure'),timing=assess(r['publications']),
                common_timing=assess(r['publications'][:common]),on_time_phase_tstates=r['timing']['on_time_phase_range_tstates'],
                foreground_tstates=r['foreground_tstates'],irq_tstates=r['irq_tstates'])
        trials.append(trial)
    sizes=[len(bytes.fromhex(next(x['code_hex'] for x in r['code_regions'] if x['base']==0xdb00))) for r in (old,new)]
    report=dict(scope=__doc__,complete=False,release=False,common_publications=common,
        compressed_stream_delta_bytes=0,reader_bytes_before=sizes[0],reader_bytes_after=sizes[1],
        reader_code_delta_bytes=sizes[1]-sizes[0],copy_before_tstates=reader['copy_before_tstates'],
        copy_after_tstates=reader['copy_after_tstates'],copy_delta_tstates=reader['copy_delta_tstates'],
        copy_saving_percent=-100*reader['copy_delta_tstates']/reader['copy_before_tstates'],
        formula='old=21*n-5; new=48+16*n+18*ceil(n/32), for positive n',
        examples=[dict(bytes=n,before=copy_tstates(n),after=copy_tstates(n,unrolled=True),
            delta=copy_tstates(n,unrolled=True)-copy_tstates(n)) for n in (1,2,16,32,256,4704,8192)],
        disk_delivery_verified=False,ula_verified=False,trials=trials)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='trials'},indent=2))


if __name__=='__main__': main()
