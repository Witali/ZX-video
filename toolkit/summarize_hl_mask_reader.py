"""Verify complete three-disk HL/EXX experiment and its exact metadata CPU saving."""
import argparse
import copy
import gzip
import json
from pathlib import Path
import compiled_masks_z80 as compiled
from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_integrated_timing import analyze,stats
from summarize_fast_return_irq import rom_invariants
from summarize_transfer_prefetch import audio_analysis,first_late_window
from summarize_uncontended_frame import metrics

ROOT=Path(__file__).parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fuse','directory','cpu'):p.add_argument('--'+key,type=Path)
    a=p.parse_args();evidence=ROOT/'hl_mask_reader_evidence';output=ROOT/'hl_mask_reader_summary.json'
    baseline=json.loads((ROOT/'fast_return_irq_summary.json').read_bytes())
    files=[dict(v,directory='fast_return_irq_evidence') for v in baseline['evidence'] if v['file'].startswith('fixed_')]
    if a.fuse:
        if a.directory is None or a.cpu is None:raise ValueError('all fresh paths required')
        evidence.mkdir(exist_ok=True);blobs={'hl_cpu.json':a.cpu.read_bytes()}
        for part in (1,2,3):
            stem=f'part{part:02}'
            for suffix in ('.json','.debugger.txt','.trace.txt'):
                blobs['hl_'+stem+suffix]=(a.fuse/(stem+suffix)).read_bytes()
            blobs['hl_'+stem+'.metadata.json']=(a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
        for name,raw in blobs.items():
            packed=gzip.compress(raw,mtime=0);name+='.gz';(evidence/name).write_bytes(packed)
            files.append(dict(directory=evidence.name,file=name,sha256=sha(packed),uncompressed_sha256=sha(raw)))
    else:
        previous=json.loads(output.read_bytes());files=previous['evidence']
        for name,digest in previous['source_sha256'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('model source changed',name))
    for f in files:
        raw=(ROOT/f['directory']/f['file']).read_bytes()
        if sha(raw)!=f['sha256'] or sha(gzip.decompress(raw))!=f['uncompressed_sha256']:raise ValueError('archive changed')
    def blob(name):
        f=next(v for v in files if v['file']==name)
        return gzip.decompress((ROOT/f['directory']/name).read_bytes())
    def load(name):return json.loads(blob(name))
    build=json.loads((ROOT/'hl_mask_reader_build.json').read_bytes())
    mask=json.loads((ROOT/'hl_mask_reader_cpu.json').read_bytes())
    if not build['complete'] or not mask['complete'] or mask['checked_frames']!=4221:raise ValueError('incomplete build or metadata CPU')
    for report in (build,mask):
        for name,digest in report['source_sha256'].items():
            if sha((ROOT/name).read_bytes())!=digest:raise ValueError(('source changed',name))
    cpus={v:load(v+'_cpu.json.gz') for v in ('fixed','hl')}
    for c in cpus.values():
        if not c['complete'] or c['frames']!=4221 or c['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes()):
            raise ValueError('incomplete or different queue CPU model')
    frame_cpu=json.loads((ROOT/'inline_huffman_patches_cpu.json').read_bytes());volumes=[]
    for part in (1,2,3):
        row=dict(part=part,used_sectors=build['volumes'][part-1]['used_sectors'])
        for variant in ('fixed','hl'):
            stem=f'{variant}_part{part:02}';raw=blob(stem+'.json.gz');r=json.loads(raw)
            meta=blob(stem+'.metadata.json.gz');m=json.loads(meta);c=cpus[variant]['volumes'][part-1]
            regions,_,_,generated=compiled.build(prefill_entry=m['queue_labels']['prefill'],hl_flags=variant=='hl')
            stored={v['address']:v for v in m['slot_queue_regions']}
            for address,data in regions:
                if (stored[address]['bytes'],stored[address]['sha256'])!=(len(data),sha(data)):
                    raise ValueError('archived mask code differs from current old/new builder')
            if [dict(address=address,bytes=len(data),sha256=sha(data)) for address,data in generated]!=m['compiled_masks']['generated_regions']:
                raise ValueError('archived generated mask tables differ')
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
                not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes'] or
                r['fast_read_retries'] or r['frames']!=m['frames'] or r['ay_ticks']!=6*m['frames'] or
                r['runtime_sectors_checked']!=m['video_sectors'] or r['trd_sha256']!=m['trd_sha256'] or
                r['trd_sha256']!=c['trd_sha256'] or sha(meta)!=r['integrated_bootstrap_metadata_sha256'] or
                sha(raw)!=c['trace_report_sha256']):raise ValueError('incomplete/different evidence')
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                if sha(blob(stem+suffix+'.gz'))!=r[key]:raise ValueError('trace mismatch')
            if any(s.startswith('se ') and s[3:].split(' ',1)[0].isdigit() for s in blob(stem+'.debugger.txt.gz').decode().splitlines()):
                raise ValueError('RAM writes')
            if len(r['queue_call_events'])!=2*len(c['calls']):raise ValueError('CPU count differs')
            for call,before,after in zip(c['calls'],r['queue_call_events'][::2],r['queue_call_events'][1::2]):
                if call['start']!=before['tstate'] or call['end']!=after['tstate'] or sum(call['cpu_stages'].values())!=call['cpu_tstates']:
                    raise ValueError('CPU call differs')
            vmask=mask['volumes'][part-1]
            if vmask['stream_sha256']!=c['stream_sha256'] or vmask['checked_frames']!=m['frames']:raise ValueError('metadata CPU input differs')
            if any(f['hl_tstates']-f['baseline_tstates']!=-499 for f in vmask['frames']):raise ValueError('unexpected metadata CPU delta')
            reference=copy.deepcopy(frame_cpu['volumes'][part-1])
            if variant=='hl':
                for frame in reference['frames']:frame['tstates']-=499
            irq=audit(r,m);irq.pop('actual_phase_tstates')
            profile=analyze(r,m,reference);worst=sorted(profile.pop('frames'),key=lambda v:v['work_elapsed'],reverse=True)[:12]
            row[variant]=dict(metrics(r),irq=irq,rom=rom_invariants(r,True),
                used_sectors=m['used_sectors'],video_start_sector=m['video_start_sector'],
                ay_record_field_gaps=r['ay_record_field_gaps'],ay_record_field_duplicates=r['ay_record_field_duplicates'],
                actual_late_indices=[i for i,t in enumerate(r['actual_phase_tstates']) if t>64],
                trd_sha256=m['trd_sha256'],stream_sha256=c['stream_sha256'],
                first_actual_late_window=first_late_window(r,actual=True),
                audio_wait=audio_analysis(r,c),queue_cpu_stages=c['cpu_stages'],queue_calls=len(c['calls']),
                metadata_cpu_tstates=vmask['hl_tstates' if variant=='hl' else 'baseline_tstates'],
                delivery_profile=profile,worst_work_frames=worst,
                read_service=stats([v['tstates'] for v in r['reads']]),seek_service=stats([v['tstates'] for v in r['seek_calls']]))
            if variant=='hl' and m['trd_sha256']!=build['volumes'][part-1]['trd_sha256']:raise ValueError('build differs')
        if (row['hl']['stream_sha256']!=row['fixed']['stream_sha256'] or
            row['hl']['used_sectors']!=row['fixed']['used_sectors'] or
            row['hl']['video_start_sector']!=row['fixed']['video_start_sector']):raise ValueError('stream or layout changed')
        volumes.append(row)
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals')
    totals={variant:{key:sum(v[variant][key] for v in volumes) for key in keys} for variant in ('fixed','hl')}
    for variant in totals:
        totals[variant].update(actual_late_frames=sum(len(v[variant]['actual_late_indices']) for v in volumes),
            missing_irq_fields=sum(len(v[variant]['irq']['missing_irq_fields']) for v in volumes),
            queue_and_ay_wait_cpu=sum(v[variant]['audio_wait']['queue_and_full_wait_cpu'] for v in volumes),
            metadata_cpu=sum(v[variant]['metadata_cpu_tstates'] for v in volumes))
    report=dict(complete=True,release=False,scope=__doc__,baseline_code_commit='a758f8c',task_base_commit='1d69dbf',evidence=files,
        build_sha256=sha((ROOT/'hl_mask_reader_build.json').read_bytes()),
        metadata_cpu_sha256=sha((ROOT/'hl_mask_reader_cpu.json').read_bytes()),
        baseline_summary_sha256=sha((ROOT/'fast_return_irq_summary.json').read_bytes()),
        source_sha256={f:sha((ROOT/f).read_bytes()) for f in ('summarize_hl_mask_reader.py','compiled_masks_z80.py',
            'test_compiled_masks_z80.py','test_hl_mask_reader.py','benchmark_hl_mask_reader.py',
            'slot_queue_player.py','replay_queue_calls.py','measure_fap3_fuse.py','test_fap3_disk.py',
            'benchmark_context_huffman.py','pipelined_frame_z80.py','audit_irq_fields.py','profile_integrated_timing.py',
            'summarize_fast_return_irq.py','summarize_transfer_prefetch.py','summarize_uncontended_frame.py','inline_huffman_patches_cpu.json')},
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',volumes=volumes,totals=totals,
        frame_cpu_reference_note='Previous complete reconstruction/render CPU plus exactly measured -499 T metadata delta; other frame stages not re-executed by this benchmark.',
        deterministic_timing_excludes=['IRQ','ULA','ROM','physical disk latency'],
        capacity_met=all(v['used_sectors']<=2544 for v in volumes),compressed_streams_exact=True,video_sector_layout_unchanged=True,
        phases_matched=False,full_pixel_comparison=False,pixel_samples_per_frame=80,
        physical_drive_verified=False,other_video_verified=False,
        nominal_schedule_met=totals['hl']['actual_late_frames']==0,
        fallback_met=all(v['hl']['max_actual_deviation_tstates']<=70908+64 and not v['hl']['bad_actual_intervals'] for v in volumes),
        ay_continuity_met=totals['hl']['audio_underruns']==0 and totals['hl']['missing_irq_fields']==0 and
            all(not v['hl']['ay_record_field_gaps'] and not v['hl']['ay_record_field_duplicates'] for v in volumes))
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals,indent=2),flush=True)


if __name__=='__main__':main()
