"""Archive/verify a rejected idle-stripe experiment: full Fuse, partial CPU.

The partial CPU run is deliberately stopped after the full emulator results
reject the variant. Never promote its pixel coverage to all 4221 frames.
"""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def cpu_summary(report):
    rows=[]; previous=0
    for v in report['volumes']:
        frames=v['frames']
        if v['start'] != previous or [f['frame'] for f in frames] != list(range(v['start'],v['start']+len(frames))):
            raise AssertionError('CPU frame gap')
        previous=v['start']+len(frames)
        for f in frames:
            if f['tstates'] != sum(f['stages'].values()) or f['delta_tstates'] != f['tstates']-f['baseline_tstates']:
                raise AssertionError('CPU frame sum differs')
        rows+=frames
    return dict(complete=report['complete'],checked_frames=len(rows),
        **{key:sum(f[key] for f in rows) for key in ('baseline_tstates','tstates','delta_tstates',
           'baseline_metadata_tstates','metadata_tstates','idle_stripes','idle_inner_stripes')},
        faster_frames=sum(f['delta_tstates']<0 for f in rows),slower_frames=sum(f['delta_tstates']>0 for f in rows),
        max_regression_tstates=max(f['delta_tstates'] for f in rows),max_saving_tstates=min(f['delta_tstates'] for f in rows),
        per_volume=[dict(part=v['part'],checked_frames=len(v['frames']),
                        **{key:sum(f[key] for f in v['frames']) for key in ('baseline_tstates','tstates','delta_tstates')})
                    for v in report['volumes']])


def verify(root):
    read=lambda name:json.loads((root/name).read_bytes())
    summary=read('idle_masks_summary.json')
    for row in summary['evidence']:
        data=(root/row['file']).read_bytes()
        if sha(data)!=row['sha256']: raise AssertionError(('evidence hash',row['file']))
        if 'uncompressed_sha256' in row and sha(gzip.decompress(data))!=row['uncompressed_sha256']:
            raise AssertionError(('trace hash',row['file']))
    cpu=read('idle_masks_cpu_partial.json')
    if cpu_summary(cpu)!=summary['partial_cpu']: raise AssertionError('CPU summary differs')
    for v in summary['volumes']:
        part=v['part']; old_path=root/f'compiled_masks_evidence/part{part:02}.json'
        old,new=json.loads(old_path.read_bytes()),read(f'idle_masks_evidence/part{part:02}.json')
        if sha(old_path.read_bytes())!=v['baseline_report_sha256']: raise AssertionError('baseline hash')
        if metrics(old)!=v['baseline'] or metrics(new)!=v['idle']: raise AssertionError('Fuse metrics')
        check_fuse(old,new)
        for suffix,key in (('trace.txt','trace_sha256'),('debugger.txt','debugger_script_sha256')):
            data=gzip.decompress((root/f'idle_masks_evidence/part{part:02}.{suffix}.gz').read_bytes())
            if sha(data)!=new[key]: raise AssertionError('raw Fuse trace changed')
    for mode in ('baseline','idle'):
        for key,value in summary['totals'][mode].items():
            if value!=sum(v[mode][key] for v in summary['volumes']): raise AssertionError('Fuse total')
    if sum(v['idle']['frames'] for v in summary['volumes'])!=4221 or summary['release']:
        raise AssertionError('scope mismatch')
    print(f"Verified: all 4221 Fuse frames / three cold boots; {summary['partial_cpu']['checked_frames']} CPU pixel frames (partial).")


def check_fuse(old,new):
    for r in (old,new):
        if (not r['complete'] or not r['trace_nonce_exact'] or r['errors'] or not r['ay_records_exact']
                or r['ay_ticks']!=6*r['frames']): raise AssertionError('incomplete Fuse run')
    if (old['trd_sha256']!=new['trd_sha256'] or old['frames']!=new['frames']
            or old['runtime_sectors_checked']!=new['runtime_sectors_checked']
            or not new.get('idle_masks') or not new.get('compiled_masks') or new.get('uncontended_frame')):
        raise AssertionError('different runtime inputs or variant')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fuse',type=Path,help='Archive fresh reports; otherwise verify saved evidence')
    args=p.parse_args(); root=Path(__file__).parent
    if args.fuse:
        evidence=[]; volumes=[]; dest=root/'idle_masks_evidence'; dest.mkdir(exist_ok=True)
        def record(path,uncompressed=None):
            entry=dict(file=path.relative_to(root).as_posix(),sha256=sha(path.read_bytes()))
            if uncompressed is not None: entry['uncompressed_sha256']=sha(uncompressed)
            evidence.append(entry)
        for name in ('idle_masks_cpu_partial.json','idle_masks_v1_partial.json'): record(root/name)
        cpu=json.loads((root/'idle_masks_cpu_partial.json').read_bytes())
        for part in (1,2,3):
            source=args.fuse/f'part{part:02}.json'
            new=json.loads(source.read_bytes()); old_path=root/'compiled_masks_evidence'/source.name
            old=json.loads(old_path.read_bytes()); check_fuse(old,new)
            path=dest/source.name
            path.write_text(json.dumps(new,indent=2)+'\n',encoding='utf-8',newline='\n'); record(path)
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                data=source.with_suffix(suffix).read_bytes()
                if sha(data)!=new[key]: raise AssertionError('source trace hash')
                path=dest/(source.stem+suffix+'.gz'); path.write_bytes(gzip.compress(data,mtime=0)); record(path,data)
            volumes.append(dict(part=part,trd_sha256=new['trd_sha256'],baseline_report_sha256=sha(old_path.read_bytes()),
                                baseline=metrics(old),idle=metrics(new)))
        totals={mode:{key:sum(v[mode][key] for v in volumes) for key in
            ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','read_service_tstates',
             'seek_service_tstates','publication_span_tstates')} for mode in ('baseline','idle')}
        summary=dict(complete=True,release=False,decision='rejected',baseline_commit='8c6c9f6',scope=__doc__,
            reason='Full Fuse worsens late publications and AY underruns; the completed first-volume CPU run also costs more.',
            source_streams_and_trds_unchanged=True,compressed_stream_delta_bytes=0,
            full_cpu_pixel_comparison=False,fuse_pixel_samples_per_frame=80,full_fuse_pixel_comparison=False,
            physical_drive_verified=False,new_bootstrap_capacity_verified=False,
            nominal_schedule_met=all(v['idle']['nominal_late_frames']==0 and v['idle']['max_actual_deviation_tstates']<=64 for v in volumes),
            fallback_met=all(v['idle']['actual_out_over_one_field']==0 and v['idle']['bad_actual_intervals']==0 for v in volumes),
            initial_disk_and_irq_phases_not_matched=True,
            partial_cpu=cpu_summary(cpu),volumes=volumes,totals=totals,evidence=evidence)
        (root/'idle_masks_summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
        print(json.dumps(dict(totals=totals,partial_cpu=summary['partial_cpu'])),flush=True)
    verify(root)


if __name__=='__main__': main()
