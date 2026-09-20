"""Compare complete cache/storage measurements and partial IRQ playback.

Copy costs exclude parsing/ZX0/screen output, IRQ, ULA and disk. Sector
counts round one continuous compressed stream; they are not TRD layouts.
"""
import argparse
import hashlib
import json
from pathlib import Path

from assess_frame_jitter import assess,FIELD


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('copy','probe','baseline-storage','halves-storage','quarters-storage','before','after','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args()
    sources={k:json.loads(getattr(args,k.replace('-','_')).read_text(encoding='utf-8')) for k in
        ('copy','probe','baseline-storage','halves-storage','quarters-storage','before','after')}
    cpu,probe=sources['copy'],sources['probe']; before,after=sources['before'],sources['after']
    if not cpu['complete'] or not probe['complete'] or cpu['raw_sha256']!=probe['raw_sha256']:
        raise ValueError('copy/probe source mismatch or incomplete')
    if len({r['raw_sha256'] for r in (cpu,probe,before,after)})!=1 or len({r['states_sha256'] for r in (cpu,probe,before,after)})!=1:
        raise ValueError('movie source mismatch')
    if before['compressed_bytes']!=after['compressed_bytes'] or not after['unrolled_cache']:
        raise ValueError('stream or option mismatch')
    base=sources['baseline-storage']; storage=[]
    for name,width in (('baseline-storage',32),('halves-storage',16),('quarters-storage',8)):
        row=sources[name]
        expected=cpu['raw_sha256'] if width==32 else probe['variants'][str(width)]['sha256']
        if not row['complete'] or row['input_sha256']!=expected: raise ValueError('wrong ZX0 report')
        if row['encoder_sha256']!=base['encoder_sha256'] or row['encoder_mode']!=base['encoder_mode'] or row['block_bytes']!=8192:
            raise ValueError('different compression settings')
        size=row['zx0_with_headers_bytes']; old=base['zx0_with_headers_bytes']
        storage.append(dict(columns=width,raw_bytes=row['input_bytes'],zx0_with_headers_bytes=size,delta_bytes=size-old,
            continuous_stream_sectors=(size+255)//256,delta_continuous_stream_sectors=(size+255)//256-(old+255)//256,
            trd_layout_verified=False))
    costs={name:{k:r[k] for k in ('tstates','delta_tstates','change_percent','code_bytes','code_end','free_before_renderer','map_bytes')}
        for name,r in cpu['variants'].items()}
    common=min(before['checked']['publish'],after['checked']['publish']); clocks=[]
    for name,r in (('before',before),('after',after)):
        pubs=r['publications']; first_time=pubs[0]['tstates']; first_field=pubs[0]['fields']
        clocks.append(dict(name=name,complete=r['complete'],checked=r['checked'],failure=r.get('failure'),
            played_ay_ticks=r['played_ay_ticks'],timing=assess(pubs),common_timing=assess(pubs[:common]),
            on_time_out_phase_tstates=r['timing']['on_time_phase_range_tstates'],
            foreground_tstates=r['foreground_tstates'],irq_tstates=r['irq_tstates'],
            missed_nominal_frames=[dict(index=i,late_fields=v['fields']-first_field-6*i,
                actual_out_phase_tstates=v['tstates']-first_time-6*i*FIELD)
                for i,v in enumerate(pubs) if v['fields']!=first_field+6*i]))
    report=dict(scope=__doc__,complete=False,release=False,copy_probe_complete=True,storage_complete=True,
        source_frames=cpu['checked_frames'],baseline_copy_tstates=cpu['baseline_tstates'],copy_variants=costs,
        storage=storage,common_publications=common,clocks=clocks,
        compressed_stream_delta_bytes_for_unrolled=0,disk_delivery_verified=False,ula_verified=False,
        halves_full_player_verified=False,quarters_z80_implemented=False,
        inputs={k:dict(file=getattr(args,k.replace('-','_')).name,
            sha256=hashlib.sha256(getattr(args,k.replace('-','_')).read_bytes()).hexdigest()) for k in sources})
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('inputs','clocks')},indent=2))


if __name__=='__main__': main()
