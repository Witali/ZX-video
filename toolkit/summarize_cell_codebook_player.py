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
    a=p.parse_args();read=lambda name:json.loads((a.work/name).read_bytes())
    b,m,c,t,s=[read(name+'.json') for name in ('build','metadata','cpu','timing','captures')]
    image=(a.work/'candidate.trd').read_bytes();digest=sha(image)
    assert all(r['complete'] for r in (b,c,t,s))
    assert digest==b['trd_sha256']==t['trd_sha256']==s['trd_sha256']
    assert sha((a.work/'metadata.json').read_bytes())==t['integrated_bootstrap_metadata_sha256']
    assert c['all_native_screens_exact'] and c['all_progress_steps_exact'] and s['full_screens_exact']
    assert len(s['screens'])==t['frames']==m['frames']==64
    assert not t['errors'] and not t['audio_underruns'] and t['ay_records_exact']
    assert not t['ay_record_field_gaps'] and not t['ay_record_field_duplicates']
    assert not t['nominal_late_frames'] and not t['bad_actual_intervals'] and t['progress_100_percent']
    assert t['runtime_sectors_checked']==m['video_sectors']
    for record in (b,s):
        for name,h in record['source_sha256_lf'].items():
            assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==h,name
    a.evidence.mkdir(parents=True,exist_ok=True);archives={}
    files=['build.json','metadata.json','cpu.json','timing.json','timing.trace.txt','timing.debugger.txt',
           'timing.stderr.txt','captures.json','initial-build-before-progress-fix.json']
    for name in files:
        raw=(a.work/name).read_bytes();packed=gzip.compress(raw,mtime=0)
        dest=name.replace('/','-')+'.gz';(a.evidence/dest).write_bytes(packed)
        archives[name]=dict(file=dest,sha256=sha(packed),raw_sha256=sha(raw))
    traces={p.name:p.read_bytes().decode() for p in sorted((a.work/'captures').glob('*.txt'))}
    assert len(traces)==128
    for screen in s['screens']:
        stem='frame-'+str(screen['frame'])
        assert sha(traces[stem+'.trace.txt'].encode())==screen['trace_sha256']
        assert sha(traces[stem+'.debugger.txt'].encode())==screen['debugger_sha256']
    raw=json.dumps(traces,sort_keys=True).encode();packed=gzip.compress(raw,mtime=0)
    (a.evidence/'captures-traces.json.gz').write_bytes(packed)
    archives['capture_traces']=dict(file='captures-traces.json.gz',sha256=sha(packed),raw_sha256=sha(raw))
    pubs=t['publications'];span=pubs[-1]['tstate']-pubs[0]['tstate'];field=70908
    intervals=[q['tstate']-p['tstate'] for p,q in zip(pubs,pubs[1:])]
    assert all(q['field']-p['field']==6 for p,q in zip(pubs,pubs[1:]))
    report=dict(complete=True,release=False,goal_achieved=False,date='2026-09-30',baseline_commit='d77b8ad',
        scope='Independently cold-booted 64-frame CB41 window, source states 128..191. Not full-movie or sustained multi-volume proof.',
        trd_sha256=digest,frames=64,full_screens_compared_bytes=s['compared_bytes'],
        fps=(len(pubs)-1)*field*50/span,publication_span_tstates=span,
        nominal_late_frames=t['nominal_late_frames'],max_late_fields=t['max_late_fields'],late_runs=t['late_runs'],
        actual_phase_tstates=[min(t['actual_phase_tstates']),max(t['actual_phase_tstates'])],
        actual_interval_tstates=[min(intervals),max(intervals)],bad_actual_intervals=t['bad_actual_intervals'],
        ay_ticks=t['ay_ticks'],ay_records_exact=True,ay_field_gaps=0,ay_field_duplicates=0,audio_underruns=0,
        progress_100_percent=True,dirty_ram_boot_exact=b['cold']['dirty_ram_boot_exact'],
        video_bytes=b['video_bytes'],video_sectors=b['video_sectors'],used_sectors=b['used_sectors'],
        runtime_sectors_checked=t['runtime_sectors_checked'],
        sectors_read_after_first_publication=sum(r['start_tstate']>=pubs[0]['tstate'] for r in t['reads']),
        elapsed_timing=t['elapsed_timing'],new_instruction_stages=c['new_instruction_stages'],
        new_instruction_tstates=c['new_instruction_tstates'],memory=m['cell_codebook']['memory'],
        startup_book_transposition_tstates=54028,
        cycle_scope='Instruction-table CPU with mocked disk and host-selected screen in CPU test; actual Fuse timing/IRQ/ROM/ULA is separate.',
        decision='Retain independent CB41 test disk. The entire selected window meets exact six-field deadlines with exact pixels and AY. Expand to the full 192-frame fixture to test sustained disk delivery, then the edited movie; keep five brightness levels and independently bootable volumes.',
        limitations=['Only 64 frames, book learned on this window','130 of 166 runtime video sectors arrive before the first publication',
                     'Full movie, three-disk capacity and generic converter integration remain unverified'],
        archives=archives,source_sha256_lf=dict(b['source_sha256_lf'],**s['source_sha256_lf']))
    report['source_sha256_lf'][Path(__file__).name]=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))
    save(a.output,report)
    print(json.dumps({k:report[k] for k in ('fps','nominal_late_frames','ay_ticks','full_screens_compared_bytes','used_sectors','goal_achieved')}))


if __name__=='__main__':main()
