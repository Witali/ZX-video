"""Archive the complete CB41 window playback proof without claiming a release."""
import argparse,gzip,hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parent


def sha(data):return hashlib.sha256(data).hexdigest()


def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('work','output','evidence'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--extra-evidence',nargs=2,action='append',default=[],metavar=('NAME','PATH'))
    for name in ('transport','independent','baseline-transport','baseline-profile'):
        p.add_argument('--'+name,type=Path)
    a=p.parse_args();read=lambda name:json.loads((a.work/name).read_bytes())
    b,m,c,t,s=[read(name+'.json') for name in ('build','metadata','cpu','timing','captures')]
    image=(a.work/'candidate.trd').read_bytes();digest=sha(image)
    assert all(r['complete'] for r in (b,c,t,s))
    assert digest==b['trd_sha256']==t['trd_sha256']==s['trd_sha256']
    assert sha((a.work/'metadata.json').read_bytes())==t['integrated_bootstrap_metadata_sha256']
    assert c['all_native_screens_exact'] and c['all_progress_steps_exact'] and s['full_screens_exact']
    count=m['frames'];first=m['frame_start'];end=m['frame_end_exclusive']
    assert len(s['screens'])==t['frames']==count and end-first==count
    assert not t['errors'] and not t['audio_underruns'] and t['ay_records_exact']
    assert not t['ay_record_field_gaps'] and not t['ay_record_field_duplicates']
    assert t['progress_100_percent']
    assert t['runtime_sectors_checked']==m['video_sectors']
    for record in (b,s):
        for name,h in record['source_sha256_lf'].items():
            assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==h,name
    a.evidence.mkdir(parents=True,exist_ok=True);archives={}
    files={name:a.work/name for name in ('build.json','metadata.json','cpu.json','timing.json','timing.trace.txt',
           'timing.debugger.txt','timing.stderr.txt','captures.json')}
    prior=a.work/'initial-build-before-progress-fix.json'
    if prior.exists():files[prior.name]=prior
    comparison_inputs=(a.transport,a.independent,a.baseline_transport,a.baseline_profile)
    if any(comparison_inputs):
        assert all(comparison_inputs),'supply all four comparison reports'
        for name,path in zip(('transport.json','independent.json','baseline-transport.json','baseline-profile.json'),comparison_inputs):
            files[name]=path
    for name,path in a.extra_evidence:
        if Path(name).name!=name or name in files:raise ValueError('invalid/duplicate evidence name')
        files[name]=Path(path)
    for name,path in files.items():
        raw=path.read_bytes();packed=gzip.compress(raw,mtime=0)
        dest=name.replace('/','-')+'.gz';(a.evidence/dest).write_bytes(packed)
        archives[name]=dict(file=dest,sha256=sha(packed),raw_sha256=sha(raw))
    traces={p.name:p.read_bytes().decode() for p in sorted((a.work/'captures').glob('*.txt'))}
    assert len(traces)==2*count
    for screen in s['screens']:
        stem='frame-'+str(screen['frame'])
        assert sha(traces[stem+'.trace.txt'].encode())==screen['trace_sha256']
        assert sha(traces[stem+'.debugger.txt'].encode())==screen['debugger_sha256']
    raw=json.dumps(traces,sort_keys=True).encode();packed=gzip.compress(raw,mtime=0)
    (a.evidence/'captures-traces.json.gz').write_bytes(packed)
    archives['capture_traces']=dict(file='captures-traces.json.gz',sha256=sha(packed),raw_sha256=sha(raw))
    pubs=t['publications'];span=pubs[-1]['tstate']-pubs[0]['tstate'];field=70908
    intervals=[q['tstate']-p['tstate'] for p,q in zip(pubs,pubs[1:])]
    six_fields=all(q['field']-p['field']==6 for p,q in zip(pubs,pubs[1:]))
    passed=six_fields and not t['nominal_late_frames'] and not t['bad_actual_intervals']
    before=sum(r['end_tstate']<=pubs[0]['tstate'] for r in t['reads'])
    crossing=sum(r['start_tstate']<pubs[0]['tstate']<r['end_tstate'] for r in t['reads'])
    report=dict(complete=True,release=False,goal_achieved=False,date='2026-09-30',baseline_commit=b['baseline_commit'],
        scope=f'Independently cold-booted {count}-frame CB41 fixture, source states {first}..{end-1}. Not full-movie or multi-volume proof.',
        trd_sha256=digest,frames=count,full_screens_compared_bytes=s['compared_bytes'],
        exact_deadlines_verified=passed,all_intervals_six_fields=six_fields,
        fps=(len(pubs)-1)*field*50/span,publication_span_tstates=span,
        nominal_late_frames=t['nominal_late_frames'],max_late_fields=t['max_late_fields'],late_runs=t['late_runs'],
        actual_phase_tstates=[min(t['actual_phase_tstates']),max(t['actual_phase_tstates'])],
        actual_interval_tstates=[min(intervals),max(intervals)],bad_actual_intervals=t['bad_actual_intervals'],
        ay_ticks=t['ay_ticks'],ay_records_exact=True,ay_field_gaps=0,ay_field_duplicates=0,audio_underruns=0,
        progress_100_percent=True,dirty_ram_boot_exact=b['cold']['dirty_ram_boot_exact'],
        video_bytes=b['video_bytes'],video_sectors=b['video_sectors'],used_sectors=b['used_sectors'],
        runtime_sectors_checked=t['runtime_sectors_checked'],
        sectors_read_after_first_publication=sum(r['start_tstate']>=pubs[0]['tstate'] for r in t['reads']),
        sectors_complete_before_first_publication=before,sectors_crossing_first_publication=crossing,
        elapsed_timing=t['elapsed_timing'],new_instruction_stages=c['new_instruction_stages'],
        new_instruction_tstates=c['new_instruction_tstates'],memory=m['cell_codebook']['memory'],
        startup_book_transposition_tstates=54028,
        cycle_scope='Instruction-table CPU with mocked disk and host-selected screen in CPU test; actual Fuse timing/IRQ/ROM/ULA is separate.',
        decision=('Retain verified fixture. Proceed to the complete authorized movie edit and generic converter integration with independently bootable volumes.'
                  if passed else 'Retain timing failure evidence. Profile the missed deadlines before expanding this candidate.'),
        limitations=[f'Only {count} frames, book learned on this fixture',f'{before} of {m["video_sectors"]} runtime video sectors complete before the first publication',
                     'Full movie, three-disk capacity and generic converter integration remain unverified'],
        archives=archives,source_sha256_lf=dict(b['source_sha256_lf'],**s['source_sha256_lf']))
    if all(comparison_inputs):
        tr,ind,previous,old=[json.loads(path.read_bytes()) for path in comparison_inputs]
        assert all(r['complete'] for r in (tr,ind,previous,old))
        assert tr['raw_sha256']==ind['raw_sha256']==b['cell_raw_sha256']
        assert tr['stream_sha256']==ind['stream_sha256']
        assert tr['native']==previous['native'],'decoder changed between component profiles'
        assert old['raw_sha256']==m['raw_sha256'] and first==0 and old['ay_ticks']==count*6
        assert previous['stream_sha256']==old['stream_sha256'] and previous['raw_sha256']==old['video_sha256']
        native=sum(v for k,v in c['new_instruction_stages'].items() if k not in ('schedule','cb41_packet','book_load'))
        report['comparison']=dict(baseline='Same complete saved fixture with borrowed-literal FAP3 player',
            previous_video_bytes=old['unchanged_video_bytes'],video_bytes=b['video_bytes'],
            video_delta=b['video_bytes']-old['unchanged_video_bytes'],previous_sectors=old['unchanged_video_sectors'],
            video_sectors=b['video_sectors'],previous_fps=old['fps'],previous_late_frames=old['missed_nominal_deadlines'],
            previous_decoder_tstates=previous['decoder_tstates'],decoder_tstates=tr['decoder_tstates'],
            decoder_delta=tr['decoder_tstates']-previous['decoder_tstates'],
            previous_producer_tstates=previous['producer_tstates'],producer_tstates=tr['producer_tstates'],
            producer_delta=tr['producer_tstates']-previous['producer_tstates'],
            previous_frame_component_tstates=old['frame_cpu']['frame_tstates'],native_frame_tstates=native,
            frame_component_delta=native-old['frame_cpu']['frame_tstates'],
            frame_comparison_caveat='Old includes reconstruction/paging; new is native draw only. Real playback above includes all delivery costs.',
            blocks=len(tr['blocks']),maximum_slice_tstates=max(x for row in tr['blocks'] for x in row['slice_tstates']),
            independent_interrupts=ind['injected_interrupts'],unavailable_interrupt_events=ind['unavailable_interrupt_events'])
    report['source_sha256_lf'][Path(__file__).name]=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    save(a.output,report)
    print(json.dumps({k:report[k] for k in ('fps','nominal_late_frames','ay_ticks','full_screens_compared_bytes','used_sectors','goal_achieved')}))


if __name__=='__main__':main()
