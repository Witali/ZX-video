"""Archive the borrowed-literal experiment and verify full Fuse captures."""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import numpy as np
import disk_layout
from build_fap3_trd import sha
from capture_five_level_fuse import capture
from disk_progress_z80 import reference_screen
from five_level_dither import expand


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('work','fuse','states','evidence','output','trd'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--capture-only',action='store_true')
    a=p.parse_args();work=a.work/'captures';work.mkdir(exist_ok=True)
    m=json.loads((a.work/'metadata.json').read_bytes());image=a.work/'candidate.trd'
    assert sha(image.read_bytes())==m['trd_sha256']
    with np.load(a.states,allow_pickle=False) as saved:states=saved['five_states']
    captures=[]
    for i in (0,1,63,64,128,191):
        screen,row=capture(a.fuse,image,m,i,work)
        assert screen==reference_screen(b''.join(expand(states[i].tobytes())),i,m['frames']),i
        (work/f'frame-{i}.scr').write_bytes(screen)
        captures.append(dict(row,compared_bytes=len(screen),mismatches=0))
    (a.work/'captures.json').write_text(json.dumps(captures,indent=2)+'\n',encoding='utf-8',newline='\n')
    if a.capture_only:return
    t=json.loads((a.work/'timing.json').read_bytes());cpu=json.loads((a.work/'cpu.json').read_bytes())
    b=json.loads((a.work/'build.json').read_bytes());old=json.loads(Path('toolkit/lzsa2_stage_profile.json').read_bytes())
    assert b['complete'] and cpu['complete'] and t['complete'] and not t['errors'] and not t['failure']
    assert cpu['metadata_sha256']==sha((a.work/'metadata.json').read_bytes())==t['integrated_bootstrap_metadata_sha256']
    assert t['trd_sha256']==b['trd_sha256']==m['trd_sha256']
    assert t['frames']==192 and t['ay_ticks']==1152 and t['runtime_sectors_checked']==606
    assert t['ay_records_exact'] and not any(t[k] for k in ('audio_underruns','ay_record_field_gaps','ay_record_field_duplicates'))
    assert sha((a.work/'timing.trace.txt').read_bytes())==t['trace_sha256']
    assert cpu['video_sha256']==m['borrowed_literals']['video_sha256']
    blob=image.read_bytes();start=m['video_start_sector']
    stream=b''.join(blob[(start+n)*256:(start+n+1)*256] for n in
        disk_layout.positions(m['video_sectors'],start%16))[:m['video_bytes']]
    assert sha(stream)==old['stream_sha256']
    span=t['publications'][-1]['tstate']-t['publications'][0]['tstate']
    assert span<old['publication_span_tstates']
    a.evidence.mkdir(parents=True,exist_ok=True);evidence=[]
    files=[(a.work/n,n) for n in ('metadata.json','build.json','cpu.json','timing.json','timing.trace.txt','timing.debugger.txt','captures.json')]
    files += [(path,path.name) for path in sorted(work.iterdir()) if path.suffix in ('.scr','.txt')]
    for path,name in files:
        raw=path.read_bytes();blob=gzip.compress(raw,mtime=0);(a.evidence/(name+'.gz')).write_bytes(blob)
        evidence.append(dict(file=name+'.gz',sha256=sha(blob),raw_sha256=sha(raw)))
    sources=('borrowed_literals.py','verify_borrowed_literals.py','build_row_lzsa.py','summarize_borrowed_literals.py')
    result=dict(complete=True,release=False,baseline_commit='dacb24f',
        trd_sha256=m['trd_sha256'],raw_sha256=m['raw_sha256'],video_sha256=cpu['video_sha256'],stream_sha256=sha(stream),
        unchanged_video_bytes=m['video_bytes'],unchanged_video_sectors=m['video_sectors'],used_sectors=m['used_sectors'],
        fps=(m['frames']-1)*70908*50/span,baseline_fps=old['fps'],publication_span_tstates=span,
        baseline_publication_span_tstates=old['publication_span_tstates'],elapsed_delta_tstates=span-old['publication_span_tstates'],
        missed_nominal_deadlines=t['nominal_late_frames'],baseline_missed_nominal_deadlines=old['missed_nominal_deadlines'],
        max_late_fields=t['max_late_fields'],baseline_max_late_fields=old['max_late_fields'],
        bad_actual_intervals=t['bad_actual_intervals'],late_runs=t['late_runs'],ay_ticks=t['ay_ticks'],ay_exact=True,
        borrowed_packets_cpu_fixture=cpu['copy']['borrowed_packets'],copied_bytes_saved_cpu_fixture=cpu['copy']['copied_bytes_saved'],
        copy_cpu={k:cpu['copy'][k] for k in ('baseline_tstates','tstates','delta_tstates')},
        frame_cpu={k:cpu[k] for k in ('baseline_frame_tstates','frame_tstates','frame_delta_tstates')},
        component_net_delta_tstates=cpu['estimated_component_net_delta_tstates'],edge_cases=len(cpu['copy']['edges']),
        generated=m['borrowed_literals'],captures=captures,evidence=evidence,
        source_sha256_lf={n:sha((Path('toolkit')/n).read_bytes().replace(b'\r\n',b'\n')) for n in sources},
        decision='Adopt as opt-in host-validated fragment-only transport. Keep general player support; both timing gates still fail.')
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    shutil.copyfile(image,a.trd)
    print(json.dumps({k:result[k] for k in ('fps','baseline_fps','elapsed_delta_tstates','missed_nominal_deadlines','max_late_fields','component_net_delta_tstates')}))


if __name__=='__main__':main()
