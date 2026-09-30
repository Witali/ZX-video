"""Archive one baseline and two bounded row-index speed attempts.

Validate final full-screen captures separately from timed playback. Preserve
the exact five-level pixels and AY; a complete trace alone is not a release.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import numpy as np
from build_fap3_trd import sha
from build_five_level_test_trd import save
from capture_five_level_fuse import capture
from disk_progress_z80 import reference_screen
from five_level_dither import expand


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('baseline','small','direct','fuse','trd','evidence','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    rows=[];archives=[]
    def archive(source,name):
        blob=source.read_bytes();packed=gzip.compress(blob,mtime=0)
        (a.evidence/(name+'.gz')).write_bytes(packed)
        archives.append(dict(file=name+'.gz',sha256=sha(packed),raw_sha256=sha(blob)))
    for name,work,trace_name in (('baseline',a.baseline,'profile-trace'),('slack2',a.small,'timing'),('slack16',a.direct,'timing')):
        t=json.loads((work/(trace_name+'.json')).read_text());cpu=json.loads((work/'cpu.json').read_text())
        m=json.loads((work/'metadata.json').read_text());profile=json.loads((work/'profile.json').read_text())
        if not t['complete'] or not cpu['complete'] or t['errors'] or t['trd_sha256']!=m['trd_sha256']:
            raise ValueError('incomplete or mismatched playback')
        pubs=t['publications'];intervals=np.diff([r['tstate'] for r in pubs]);phase=t['actual_phase_tstates']
        frames=np.diff([r['field'] for r in pubs])
        integrity=t['ay_records_exact'] and not (t['audio_underruns'] or t['ay_record_field_gaps'] or t['ay_record_field_duplicates'])
        nominal=integrity and t['nominal_late_frames']==0 and np.all(frames==6) and max(map(abs,phase))<=64
        fallback=integrity and t['max_late_fields']<=1 and not t['bad_actual_intervals'] and not t['actual_out_over_one_field']
        fallback=fallback and all(r['recovered_at'] is not None for r in t['late_runs'])
        rows.append(dict(variant=name,trd_sha256=t['trd_sha256'],video_bytes=m['video_bytes'],video_sectors=m['video_sectors'],
            used_sectors=m['used_sectors'],frame_cpu_tstates=cpu['tstates'],cpu_stages=cpu['stages'],
            elapsed_stages={k:v['elapsed']['total'] for k,v in profile['stages'].items()},
            mean_fps=(len(pubs)-1)*70908*50/(pubs[-1]['tstate']-pubs[0]['tstate']),
            missed_deadlines=t['nominal_late_frames'],max_late_fields=t['max_late_fields'],late_runs=t['late_runs'],
            bad_fallback_intervals=t['bad_actual_intervals'],nominal_pass=bool(nominal),fallback_pass=bool(fallback),
            interval_ms=dict(min=float(intervals.min()/70908*20),mean=float(intervals.mean()/70908*20),max=float(intervals.max()/70908*20)),
            exact_ay=t['ay_records_exact'],ay_ticks=t['ay_ticks'],underruns=t['audio_underruns'],
            pixel_errors=len(t['errors']),full_cpu_screens_exact=cpu['full_compact_and_both_native_exact'],
            checked_runtime_sectors=t['runtime_sectors_checked']))
        sources=['cpu.json','profile.json',trace_name+'.json',trace_name+'.trace.txt',trace_name+'.debugger.txt']
        if name!='baseline':sources+=['metadata.json','video.raw','build.json']
        for source in sources:archive(work/source,name+'-'+source)
    if len({json.loads((w/'cpu.json').read_text())['states_sha256'] for w in (a.baseline,a.small,a.direct)})!=1:
        raise ValueError('pixel states changed')
    with np.load(a.baseline/'prepared.npz',allow_pickle=False) as data:five=data['five_states']
    m=json.loads((a.direct/'metadata.json').read_text());captures=[];work=a.direct/'captures';work.mkdir(exist_ok=True)
    for index in (31,64,95,128,159,191):
        screen,record=capture(a.fuse,a.direct/'candidate.trd',m,index,work)
        expected=reference_screen(b''.join(expand(five[index].tobytes())),index,m['frames'])
        if screen!=expected:raise AssertionError(('full Fuse screen mismatch',index))
        (work/f'frame-{index}.scr').write_bytes(screen);captures.append(dict(record,compared_bytes=6912,mismatches=0))
        for ext in ('scr','trace.txt','debugger.txt'):archive(work/f'frame-{index}.{ext}',f'direct-frame-{index}.{ext}')
    archive(a.direct/'tests.txt','tests.txt')
    shutil.copyfile(a.direct/'candidate.trd',a.trd)
    baseline,selected=rows[0],rows[-1]
    names=('encode_fap3.py','optimize_row_fragments.py','profile_row_cpu.py','profile_row_playback.py',
           'summarize_row_fragments.py','test_generic_converter.py')
    result=dict(complete=True,release=False,scope=__doc__,baseline_commit='78541a5',frames=192,
        states_sha256=json.loads((a.baseline/'cpu.json').read_text())['states_sha256'],variants=rows,captures=captures,
        frame_cpu_saved=baseline['frame_cpu_tstates']-selected['frame_cpu_tstates'],
        frame_cpu_saved_percent=100*(1-selected['frame_cpu_tstates']/baseline['frame_cpu_tstates']),
        video_growth_percent=100*(selected['video_bytes']/baseline['video_bytes']-1),
        fps_growth_percent=100*(selected['mean_fps']/baseline['mean_fps']-1),
        selected_image=a.trd.name,selected_trd_sha256=sha(a.trd.read_bytes()),
        decision='Optional experimental speed mode only: faster delivery, larger stream; both cadence gates still fail. Preserve default encoder.',
        measurement_limits='Frame CPU excludes packet copy, ZX0, ULA, AY/IRQ and disk. Fuse elapsed phases include them. Never add these totals. 50-Hz normalization.',
        archives=archives,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in names})
    save(a.output,result)
    print(json.dumps({k:v for k,v in result.items() if k in ('complete','release','frame_cpu_saved','frame_cpu_saved_percent','video_growth_percent','fps_growth_percent','selected_image')}))


if __name__=='__main__':main()
