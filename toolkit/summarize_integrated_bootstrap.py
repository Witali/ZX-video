"""Archive complete real-bootstrap Fuse runs; distinguish capacity from cadence."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from summarize_uncontended_frame import metrics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fresh','directory'):p.add_argument('--'+key,type=Path)
    p.add_argument('--build',type=Path,default=Path('toolkit/integrated_bootstrap_build.json'))
    p.add_argument('--evidence',type=Path,default=Path('toolkit/integrated_bootstrap_evidence'))
    p.add_argument('--output',type=Path,default=Path('toolkit/integrated_bootstrap_summary.json'))
    p.add_argument('--baseline',type=Path,default=Path('toolkit/combined_uncontended_evidence'))
    a=p.parse_args();built=json.loads(a.build.read_bytes())
    if not built['complete'] or len(built['volumes'])!=3:raise ValueError('incomplete build')
    files=[];volumes=[]
    if a.fresh:
        if not a.directory:raise ValueError('metadata directory required')
        a.evidence.mkdir(parents=True,exist_ok=True)
        for part in (1,2,3):
            path=a.fresh/f'part{part:02}.json';r=json.loads(path.read_bytes())
            meta=(a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
            if sha(meta)!=r['integrated_bootstrap_metadata_sha256']:raise ValueError('metadata differs')
            canonical=(json.dumps(r,indent=2)+'\n').encode('utf-8')
            for name,blob in ((path.name,canonical),(f'part{part:02}.metadata.json',meta)):
                dest=a.evidence/name;dest.write_bytes(blob);files.append(dict(file=name,sha256=sha(blob)))
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                blob=path.with_suffix(suffix).read_bytes()
                if sha(blob)!=r[key]:raise ValueError('trace differs')
                name=path.stem+suffix+'.gz';packed=gzip.compress(blob,mtime=0)
                (a.evidence/name).write_bytes(packed)
                files.append(dict(file=name,sha256=sha(packed),uncompressed_sha256=sha(blob)))
    else:files=json.loads(a.output.read_bytes())['evidence']
    for f in files:
        blob=(a.evidence/f['file']).read_bytes()
        if sha(blob)!=f['sha256']:raise ValueError('archive changed')
        if 'uncompressed_sha256' in f and sha(gzip.decompress(blob))!=f['uncompressed_sha256']:
            raise ValueError('trace archive corrupt')
    for b in built['volumes']:
        part=b['part'];path=a.evidence/f'part{part:02}.json';r=json.loads(path.read_bytes())
        old_path=a.baseline/path.name;old=json.loads(old_path.read_bytes())
        m=json.loads((a.evidence/f'part{part:02}.metadata.json').read_bytes())
        if m.get('bank2_zx0')!=r.get('bank2_zx0') or m.get('bank2_zx0')!=b.get('bank2_zx0'):
            raise ValueError('ZX0 relocation metadata differs')
        if (not b['fits'] or not b['dirty_ram_boot_exact'] or not b['compressed_stream_exact'] or
            b['used_sectors']>2544 or not r['complete'] or r['errors'] or r['failure'] or
            r['trd_sha256']!=b['trd_sha256'] or not r['ay_records_exact'] or
            not r['trace_nonce_exact'] or r['fast_read_retries'] or not r['progress_100_percent'] or
            not r['integrated_slot_queue'] or r['debugger_installed_bytes'] or
            r['runtime_sectors_checked']!=b['video_sectors'] or r['frames']!=m['frames'] or
            r['ay_ticks']!=6*m['frames'] or r['pixel_sample_offsets']!=old['pixel_sample_offsets']):
            raise ValueError(('incomplete or different measurement',part))
        pubs=r['publications'];offsets=[v['tstate']-pubs[0]['tstate']-6*i*70908 for i,v in enumerate(pubs)]
        if (offsets!=r['actual_phase_tstates'] or r['frames']!=len(pubs) or
            r['nominal_late_frames']!=sum(v['late_fields']>0 for v in pubs)):
            raise ValueError('publication aggregate mismatch')
        script=gzip.decompress((a.evidence/f'part{part:02}.debugger.txt.gz').read_bytes()).decode()
        if any(line.startswith('se ') and line[3:].split(' ',1)[0].isdigit() for line in script.splitlines()):
            raise ValueError('debugger RAM writes in real bootstrap measurement')
        volumes.append(dict(part=part,trd_sha256=b['trd_sha256'],used_sectors=b['used_sectors'],
            free_sectors=b['free_sectors'],baseline=metrics(old),integrated=metrics(r),
            baseline_report_sha256=sha(old_path.read_bytes()),bootstrap_tstates=r['elapsed_timing']['bootstrap_tstates']))
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors',
          'read_service_tstates','seek_service_tstates','publication_span_tstates','bad_actual_intervals')
    totals={mode:{k:sum(v[mode][k] for v in volumes) for k in keys} for mode in ('baseline','integrated')}
    result=dict(complete=True,release=False,build_report_sha256=sha(a.build.read_bytes()),volumes=volumes,totals=totals,
        baseline_evidence=str(a.baseline),
        capacity_verified=True,independent_cold_boot_verified=True,debugger_installed_bytes=0,
        physical_drive_verified=False,full_fuse_pixel_comparison=False,fuse_samples_per_frame=80,
        initial_disk_and_irq_phases_not_matched=True,
        nominal_schedule_met=all(v['integrated']['nominal_late_frames']==0 and v['integrated']['max_actual_deviation_tstates']<=64 for v in volumes),
        fallback_met=all(v['integrated']['actual_out_over_one_field']==0 and v['integrated']['bad_actual_intervals']==0 for v in volumes),
        ay_schedule_met=all(v['integrated']['audio_underruns']==0 for v in volumes),evidence=files)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(totals=totals,fps=[v['integrated']['fps'] for v in volumes],
                         recovered=[v['integrated']['recovered_late_runs'] for v in volumes])),flush=True)


if __name__=='__main__':main()
