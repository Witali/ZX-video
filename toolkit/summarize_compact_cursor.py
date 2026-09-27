"""Archive and audit complete compact-cursor playback against the HL baseline.

The complete frame CPU fixture is separate from Fuse's emulated disk and
delivery measurements. Historical baseline source pins are retained as historical;
current build, CPU and analysis sources are checked. IRQ/disk starting
phases are not matched. A separate replay executes every actual queue call.
Fuse compares 80 sampled screen bytes per frame; the CPU
fixture independently compares both complete screens and compact data.
"""
import argparse
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_integrated_timing import analyze, stats
from summarize_fast_return_irq import rom_invariants
from summarize_transfer_prefetch import audio_analysis, first_late_window
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent


def pins(mapping):
    for name,digest in mapping.items():
        if sha((ROOT/name).read_bytes()) != digest: raise ValueError(('source changed',name))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('fuse','directory','cpu'): p.add_argument('--'+name,type=Path)
    a = p.parse_args()
    evidence = ROOT/'compact_cursor_evidence'
    output = ROOT/'compact_cursor_summary.json'
    baseline_path = ROOT/'hl_mask_reader_summary.json'
    baseline = json.loads(baseline_path.read_bytes())
    build_path = ROOT/'compact_cursor_build.json'
    frame_path = ROOT/'compact_cursor_cpu.json'
    old_frame_path = ROOT/'frame_hotspot_profile.json'
    build = json.loads(build_path.read_bytes())
    frame = json.loads(frame_path.read_bytes())
    old_frame = json.loads(old_frame_path.read_bytes())
    if (not build['complete'] or not frame['complete'] or frame['checked_frames'] != 4221 or
            not frame['full_compact_and_both_native_exact'] or
            frame['model_sha256'] != sha(old_frame_path.read_bytes())):
        raise ValueError('incomplete/different build or frame CPU fixture')
    for data in (build,frame): pins(data['source_sha256'])
    pins(frame['baseline_sources'])
    for old,new,built in zip(old_frame['volumes'],frame['volumes'],build['volumes'],strict=True):
        if (old['part'] != new['part'] or new['part'] != built['part'] or
                old['raw_sha256'] != new['raw_sha256'] or
                dict(new['patches'],enabled=True) != built['compact_cursor']):
            raise ValueError('frame fixture differs from installed code')
        for before,after in zip(old['frames'],new['frames'],strict=True):
            if (before['frame'] != after['frame'] or before['tstates'] != after['baseline_tstates'] or
                    after['tstates']-before['tstates'] != after['delta_tstates'] or
                    after['delta_tstates'] != -7*after['ordinary_tiles']-20*after['noop_runs']):
                raise ValueError('frame CPU delta differs')
        for key in ('baseline_tstates','tstates','delta_tstates','ordinary_tiles','noop_runs'):
            if sum(f[key] for f in new['frames']) != new[key]: raise ValueError('CPU volume sum differs')
    for key in ('baseline_tstates','tstates','delta_tstates','ordinary_tiles','noop_runs'):
        if sum(v[key] for v in frame['volumes']) != frame[key]: raise ValueError('CPU total differs')

    files = [v for v in baseline['evidence'] if v['file'].startswith('hl_')]
    if a.fuse:
        if a.directory is None or a.cpu is None: raise ValueError('all fresh paths required')
        evidence.mkdir(exist_ok=True)
        cpu_raw = a.cpu.read_bytes()
        packed = gzip.compress(cpu_raw,mtime=0)
        (evidence/'cursor_cpu.json.gz').write_bytes(packed)
        files.append(dict(directory=evidence.name,file='cursor_cpu.json.gz',sha256=sha(packed),uncompressed_sha256=sha(cpu_raw)))
        for part in (1,2,3):
            stem = f'part{part:02}'
            blobs = {stem+suffix:(a.fuse/(stem+suffix)).read_bytes()
                     for suffix in ('.json','.debugger.txt','.trace.txt')}
            blobs[stem+'.metadata.json'] = (a.directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
            for name,raw in blobs.items():
                name = 'cursor_'+name+'.gz'
                packed = gzip.compress(raw,mtime=0)
                (evidence/name).write_bytes(packed)
                files.append(dict(directory=evidence.name,file=name,sha256=sha(packed),uncompressed_sha256=sha(raw)))
    else:
        previous = json.loads(output.read_bytes())
        pins(previous['source_sha256'])
        for path,key in ((baseline_path,'baseline_summary_sha256'),(build_path,'build_sha256'),(frame_path,'frame_cpu_sha256')):
            if sha(path.read_bytes()) != previous[key]: raise ValueError(('saved report changed',key))
        files = previous['evidence']
    for f in files:
        packed = (ROOT/f['directory']/f['file']).read_bytes()
        if sha(packed) != f['sha256'] or sha(gzip.decompress(packed)) != f['uncompressed_sha256']:
            raise ValueError(('archive differs',f['file']))

    def blob(name):
        f = next(v for v in files if v['file']==name)
        return gzip.decompress((ROOT/f['directory']/name).read_bytes())

    cpus = {v:json.loads(blob(v+'_cpu.json.gz')) for v in ('hl','cursor')}
    for c in cpus.values():
        if (not c['complete'] or c['frames']!=4221 or
                c['source_sha256']!=sha((ROOT/'replay_queue_calls.py').read_bytes())):
            raise ValueError('incomplete/different queue CPU replay')
    volumes = []
    for part in (1,2,3):
        volume = dict(part=part)
        for variant,reference in (('hl',old_frame['volumes'][part-1]),('cursor',frame['volumes'][part-1])):
            stem = f'{variant}_part{part:02}'
            raw = blob(stem+'.json.gz')
            r = json.loads(raw)
            meta = blob(stem+'.metadata.json.gz')
            m = json.loads(meta)
            cpu = cpus[variant]['volumes'][part-1]
            if (not r['complete'] or r['failure'] or r['errors'] or not r['trace_nonce_exact'] or
                    not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes'] or
                    r['fast_read_retries'] or not m['independently_bootable'] or
                    r['frames'] != m['frames'] or r['frames'] != reference['checked_frames'] or
                    r['ay_ticks'] != 6*m['frames'] or r['native_frames_sampled'] != m['frames'] or
                    r['pixel_samples_per_frame'] != 80 or r['runtime_sectors_checked'] != m['video_sectors'] or
                    r['trd_sha256'] != m['trd_sha256'] or sha(meta) != r['integrated_bootstrap_metadata_sha256'] or
                    cpu['trd_sha256']!=m['trd_sha256'] or cpu['trace_report_sha256']!=sha(raw)):
                raise ValueError(('incomplete or different playback',variant,part))
            if len(r['queue_call_events'])!=2*len(cpu['calls']): raise ValueError('queue call count differs')
            for call,begin,end in zip(cpu['calls'],r['queue_call_events'][::2],r['queue_call_events'][1::2]):
                if (call['start']!=begin['tstate'] or call['end']!=end['tstate'] or
                        sum(call['cpu_stages'].values())!=call['cpu_tstates']):
                    raise ValueError('queue CPU call differs')
            for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
                if sha(blob(stem+suffix+'.gz')) != r[key]: raise ValueError('trace differs')
            if any(line.startswith('se ') and line[3:].split(' ',1)[0].isdigit()
                   for line in blob(stem+'.debugger.txt.gz').decode().splitlines()):
                raise ValueError('debugger RAM patch')
            irq = audit(r,m)
            irq.pop('actual_phase_tstates')
            profile = analyze(r,m,reference)
            worst = sorted(profile.pop('frames'),key=lambda x:x['work_elapsed'],reverse=True)[:12]
            volume[variant] = dict(metrics(r),irq=irq,rom=rom_invariants(r,True),
                used_sectors=m['used_sectors'],video_start_sector=m['video_start_sector'],
                ay_record_field_gaps=r['ay_record_field_gaps'],ay_record_field_duplicates=r['ay_record_field_duplicates'],
                actual_late_indices=[i for i,t in enumerate(r['actual_phase_tstates']) if t>64],
                trd_sha256=m['trd_sha256'],rom_sha256=r['rom_sha256'],
                first_actual_late_window=first_late_window(r,actual=True),
                audio_wait=audio_analysis(r,cpu),queue_cpu_stages=cpu['cpu_stages'],queue_calls=len(cpu['calls']),
                stream_sha256=cpu['stream_sha256'],
                delivery_profile=profile,worst_work_frames=worst,
                read_service=stats([v['tstates'] for v in r['reads']]),
                seek_service=stats([v['tstates'] for v in r['seek_calls']]))
            if variant=='cursor':
                b = build['volumes'][part-1]
                if (m['trd_sha256'] != b['trd_sha256'] or not b['dirty_ram_boot_exact'] or
                        not b['compressed_stream_exact'] or not m['compact_cursor']['enabled'] or
                        b['stream_sha256'] != baseline['volumes'][part-1]['hl']['stream_sha256'] or
                        b['stream_sha256'] != cpu['stream_sha256']):
                    raise ValueError('build differs from original stream')
        for key,value in baseline['volumes'][part-1]['hl'].items():
            if key in volume['hl'] and value != json.loads(json.dumps(volume['hl'][key])):
                raise ValueError(('baseline analysis differs',key))
        volumes.append(volume)
    keys = ('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors',
            'publication_span_tstates','bad_actual_intervals')
    totals = {v:{k:sum(r[v][k] for r in volumes) for k in keys} for v in ('hl','cursor')}
    for v in totals:
        totals[v].update(actual_late_frames=sum(len(r[v]['actual_late_indices']) for r in volumes),
            missing_irq_fields=sum(len(r[v]['irq']['missing_irq_fields']) for r in volumes),
            queue_and_ay_wait_cpu=sum(r[v]['audio_wait']['queue_and_full_wait_cpu'] for r in volumes))
    sources = ('summarize_compact_cursor.py','compact_cursor.py','test_compact_cursor.py',
        'verify_integrated_bootstrap.py','measure_fap3_fuse.py','measure_integrated_bootstrap.py',
        'audit_irq_fields.py','summarize_uncontended_frame.py','summarize_transfer_prefetch.py',
        'summarize_fast_return_irq.py','profile_integrated_timing.py','replay_queue_calls.py',
        'bank2_zx0.py','bank_local_zx0.py','slot_queue_z80.py','direct_slot_input_z80.py',
        'fast_return_irq.py','test_slot_queue.py','benchmark_direct_slot_input.py','benchmark_partial_slots.py')
    result = dict(complete=True,release=False,scope=__doc__,baseline_code_commit='074e1e7',
        task_base_commit='b3f33fc',evidence=files,baseline_summary_sha256=sha(baseline_path.read_bytes()),
        build_sha256=sha(build_path.read_bytes()),frame_cpu_sha256=sha(frame_path.read_bytes()),
        source_sha256={name:sha((ROOT/name).read_bytes()) for name in sources},volumes=volumes,totals=totals,
        deterministic_frame_cpu={k:frame[k] for k in ('baseline_tstates','tstates','delta_tstates','ordinary_tiles','noop_runs')},
        deterministic_timing_excludes=['ZX0','packet copies','queue','AY/IRQ','ULA','ROM','physical disk latency'],
        capacity_met=all(v['cursor']['used_sectors']<=2544 for v in volumes),compressed_streams_exact=True,
        video_sector_layout_unchanged=all(v['hl']['video_start_sector']==v['cursor']['video_start_sector'] for v in volumes),
        phases_matched=False,new_queue_cpu_replay=True,full_pixel_comparison_in_cpu_fixture=True,
        full_pixel_comparison_in_fuse=False,pixel_samples_per_frame=80,physical_drive_verified=False,
        other_video_verified=False,nominal_schedule_met=totals['cursor']['actual_late_frames']==0,
        fallback_met=all(v['cursor']['max_actual_deviation_tstates']<=70908+64 and not v['cursor']['bad_actual_intervals'] for v in volumes),
        ay_continuity_met=totals['cursor']['audio_underruns']==0 and totals['cursor']['missing_irq_fields']==0 and
            all(not v['cursor']['ay_record_field_gaps'] and not v['cursor']['ay_record_field_duplicates'] for v in volumes))
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(totals,indent=2),flush=True)


if __name__ == '__main__':
    main()
