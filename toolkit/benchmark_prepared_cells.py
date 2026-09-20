"""Execute B2 native consumption for every movie frame and compare old output.

Host supplies already reconstructed B2 records. The Z80 consumer handles
banked reads, split windows, staging and direct hidden-screen writes.
Production, AY/header consumption, queue scheduling, disk and ULA are NOT
included. No frame-rate or playable-release claim follows from this test.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from bulk_frame_stream import read_packet
from probe_spatial_contexts import read_header
from probe_motion_entropy import Reader
from probe_lossless_layouts import sha
from prepared_cells_harness import Harness
import prepared_cells_z80 as machine


def write_report(path,report):
    """Keep the per-frame audit complete without 100k lines of JSON layout."""
    prefix=json.dumps({k:v for k,v in report.items() if k!='frames'},indent=2)
    rows=',\n'.join('    '+json.dumps(row) for row in report['frames'])
    path.write_text(prefix[:-2]+',\n  "frames": [\n'+rows+'\n  ]\n}\n',encoding='utf-8')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('states','raw','baseline','output'): p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--unrolled-staging',action='store_true')
    args=p.parse_args(); raw=args.raw.read_bytes(); old=json.loads(args.baseline.read_text())
    with np.load(args.states,allow_pickle=False) as f: states=f['states']
    if not old['complete'] or old['raw_sha256']!=sha(raw) or old['states_sha256']!=sha(states.tobytes()):
        raise ValueError('baseline source mismatch')
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    if count!=len(states) or count!=len(old['frames']): raise ValueError('frame counts differ')
    h=Harness(unrolled_staging=args.unrolled_staging); rows=[]
    report=dict(scope=__doc__,baseline_commit='2b3b4ce',complete=False,release=False,
        player_changed=False,integrated_player_delta_tstates=0,raw_sha256=sha(raw),states_sha256=sha(states.tobytes()),
        source_baseline=args.baseline.name,frames_expected=count,frame_rate_verified=False,
        producer_implemented=False,ay_scheduler_verified=False,ula_verified=False,disk_delivery_verified=False,
        compressed_stream_delta_bytes=0,unrolled_staging=args.unrolled_staging,code_bytes=len(h.code),labels=h.labels,code_hex=h.code.hex(),
        instruction_listing=h.listing,timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        old_formula_adjustment_for_two_atomic_page_calls=186,
        memory=dict(code=[machine.CODE,h.labels['end']],stage=[machine.STAGE,machine.STAGE+128],
            map=[machine.MASK,machine.MASK+90],queue_banks=[3,4],queue_bytes=2*machine.RING_BANK_BYTES,
            disk_ring_proposed_banks=[0,1],disk_ring_proposed_bytes=32768,
            management_reserve_bytes=2048,screen_banks=[5,7],huffman_bank=6),frames=rows)
    def save():
        report['checked_frames']=len(rows)
        write_report(args.output,report)
    try:
        for i,state in enumerate(states):
            _,packet=read_packet(r,stored_guards=False)
            native=packet['payload'][packet['coded_offset']-80:packet['coded_offset']]
            prefix=2+sum(map(len,packet['ticks']))
            # Prefix is not consumed by this CPU substage; retain its ring
            # occupancy to exercise the same wrap positions a full B2 has.
            h.cursor=(h.cursor+prefix)%(2*machine.RING_BANK_BYTES)
            row=h.run(state.tobytes(),native,i)
            if row['baseline_tstates']!=old['frames'][i]['stages']['output']+186:
                raise AssertionError(('old output scope differs',i,row['baseline_tstates'],old['frames'][i]['stages']['output']))
            row['record_bytes']=row['body_bytes']+prefix; rows.append(row)
            if i%100==0: save(); print(f'Prepared-cell Z80 verified {i+1}/{count}',flush=True)
        r.end()
        report['instruction_histogram']=[dict(address=a,tstates=t,count=n) for (a,t),n in sorted(h.histogram.items())]
        total=sum(row['tstates'] for row in rows); baseline=sum(row['baseline_tstates'] for row in rows)
        if sum(v['tstates']*v['count'] for v in report['instruction_histogram'])!=total: raise AssertionError('histogram differs')
        by_bank={}
        for bank in (5,7):
            group=[v for v in rows if v['target_bank']==bank]; a=sum(v['tstates'] for v in group); b=sum(v['baseline_tstates'] for v in group)
            by_bank[str(bank)]=dict(frames=len(group),tstates=a,baseline_tstates=b,delta_tstates=a-b,change_percent=100*(a-b)/b)
        report.update(complete=True,summary=dict(total_tstates=total,baseline_tstates=baseline,delta_tstates=total-baseline,
            change_percent=100*(total-baseline)/baseline,mean_tstates=total/count,max_tstates=max(v['tstates'] for v in rows),
            by_bank=by_bank,prepared_record_bytes=sum(v['record_bytes'] for v in rows),mean_record_bytes=sum(v['record_bytes'] for v in rows)/count))
    except Exception as exc:
        report['failure']=repr(exc); save(); raise
    save(); print(json.dumps(report['summary'],indent=2),flush=True)


if __name__=='__main__': main()
