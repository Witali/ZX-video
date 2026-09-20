"""Keep packet CPU, mask storage and whole-clock evidence distinct."""
import argparse
import json
from pathlib import Path
import hashlib

from summarize_gray_cells import clock_result
from bulk_frame_stream import read_packet
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('raw','packet','baseline','density','early','combined','storage','density-storage','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    names=('packet','baseline','density','early','combined','storage','density_storage')
    reports={k:json.loads(getattr(args,k).read_text(encoding='utf-8')) for k in names}
    packet=reports['packet']; old=reports['baseline']; raw=args.raw.read_bytes()
    if not packet['complete'] or packet['checked_frames']!=4221: raise ValueError('incomplete packet benchmark')
    if hashlib.sha256(raw).hexdigest()!=packet['raw_sha256'] or packet['raw_sha256']!=old['raw_sha256']:
        raise ValueError('different original stream')
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3'); packets=[]
    for _ in range(count): packets.append(read_packet(r,stored_guards=False)[1])
    r.end()
    clocks={k:reports[k] for k in ('baseline','density','early','combined')}
    common=min(v['checked']['publish'] for v in clocks.values())
    rows=[]
    for name,report in clocks.items():
        if not report.get('complete') and not report.get('failure'):
            raise ValueError('clock still running or result lacks a terminal failure: '+name)
        for key in ('states_sha256','frames_requested','lookahead','packet_ahead','unrolled_copy','unrolled_cache','attribute_groups','attribute_flags','gray_cells'):
            if report[key]!=old[key]: raise ValueError('different clock mode '+key)
        expected_early=name in ('early','combined')
        expected_storage=reports['density_storage' if name in ('density','combined') else 'storage']
        if bool(report.get('early_ay'))!=expected_early: raise ValueError('wrong early AY mode')
        if not expected_storage['complete'] or expected_storage['input_sha256']!=report['raw_sha256']:
            raise ValueError('different storage input')
        size=sum(v['zx0_bytes']+4 for v in expected_storage['blocks'])
        if size!=report['compressed_bytes']: raise ValueError('different size')
        row=clock_result(name,report,common)
        row.update(compressed_bytes=size,foreground_stages=report['foreground_stages'],
            parser_bytes=report['packet_labels']['end']-0xdc00,
            parser_end=report['packet_labels']['end'])
        index=report['checked']['packet']
        if index<count:
            d=packets[index]
            row['next_unfinished_packet']=dict(index=index,payload_bytes=len(d['payload']),
                ay_bytes=sum(map(len,d['ticks'])),coded_bytes=d['coded_bytes'],literal_bytes=d['literal_bytes'])
        rows.append(row)
    stages={name:packet['variants'][name]['stages'] for name in ('before','after')}
    result=dict(scope=__doc__,baseline_commit='c829610',complete=True,release=False,all_frames_requested=count,
        packet_stage_complete=True,checked_packets=packet['checked_frames'],
        manually_verified_ay_ticks=packet['verified_manual_ay_ticks'],packet_stages=stages,
        packet_total_tstates={name:packet['variants'][name]['tstates'] for name in stages},
        packet_stage_deltas={k:stages['after'].get(k,0)-stages['before'].get(k,0)
            for k in sorted(stages['before'].keys()|stages['after'].keys())},
        parser_only_delta_per_frame=83,parser_code_delta_bytes=16,new_framebuffer_bytes=0,
        sound_bytes_changed=False,common_publications=common,clocks=rows,
        full_movie_cadence_verified=False,physical_disk_verified=False,ula_verified=False,
        limitations=['Packet benchmark drains AY manually and omits reconstruction/rendering.',
            'Clock foreground totals include different amounts of future work; do not infer full-movie speedup.',
            'Compressed sizes include block headers, not assembled disk volumes.'],
        inputs={k:dict(file=getattr(args,k).name,sha256=hashlib.sha256(getattr(args,k).read_bytes()).hexdigest()) for k in names})
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('clocks','inputs','limitations')},indent=2))


if __name__=='__main__': main()
