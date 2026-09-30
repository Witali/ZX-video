"""Archive the bounded LZSA2 comparison and verify selected full Fuse screens."""
import argparse,gzip,json,shutil
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from capture_five_level_fuse import capture
from disk_progress_z80 import reference_screen
from five_level_dither import expand


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('baseline','candidate','states','fuse','trd','evidence','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True);archives=[];variants=[]
    def archive(path,name):
        raw=path.read_bytes();blob=gzip.compress(raw,mtime=0);filename=name+'.gz'
        (a.evidence/filename).write_bytes(blob)
        archives.append(dict(file=filename,sha256=sha(blob),raw_sha256=sha(raw)))
    for name,work,cpu_file in (('fast_zx0',a.baseline,'transport.json'),('lzsa2',a.candidate,'cpu.json')):
        m=json.loads((work/'metadata.json').read_text());t=json.loads((work/'timing.json').read_text())
        c=json.loads((work/cpu_file).read_text());profile=json.loads((work/'profile.json').read_text())
        if not c['complete'] or not t['complete'] or t['errors'] or t['trd_sha256']!=m['trd_sha256']:
            raise ValueError('incomplete or mismatched evidence')
        pubs=t['publications'];intervals=np.diff([v['tstate'] for v in pubs]);fields=np.diff([v['field'] for v in pubs])
        sound=t['ay_records_exact'] and not (t['audio_underruns'] or t['ay_record_field_gaps'] or t['ay_record_field_duplicates'])
        variants.append(dict(variant=name,trd_sha256=m['trd_sha256'],frames=m['frames'],
            video_bytes=m['video_bytes'],video_sectors=m['video_sectors'],used_sectors=m['used_sectors'],
            decoder_tstates=c['decoder_tstates'],producer_tstates=c['producer_tstates'],
            total_transport_tstates=c['total_tstates'],
            disk_windows_elapsed_tstates=sum(v['tstates'] for v in t['reads']),
            seek_windows_elapsed_tstates=sum(v['tstates'] for v in t['seek_calls']),
            elapsed_stages={k:v['elapsed']['total'] for k,v in profile['stages'].items()},
            fps=(len(pubs)-1)*70908*50/(pubs[-1]['tstate']-pubs[0]['tstate']),
            missed_deadlines=t['nominal_late_frames'],max_late_fields=t['max_late_fields'],late_runs=t['late_runs'],
            actual_out_over_one_field=t['actual_out_over_one_field'],bad_intervals=t['bad_actual_intervals'],
            interval_ms=dict(min=float(intervals.min()/70908*20),mean=float(intervals.mean()/70908*20),max=float(intervals.max()/70908*20)),
            nominal_pass=bool(sound and not t['nominal_late_frames'] and np.all(fields==6) and max(map(abs,t['actual_phase_tstates']))<=64),
            fallback_pass=bool(sound and t['max_late_fields']<=1 and not t['actual_out_over_one_field'] and not t['bad_actual_intervals']
                and all(v['recovered_at'] is not None for v in t['late_runs'])),
            ay_exact=bool(sound),ay_ticks=t['ay_ticks'],pixel_samples_per_frame=t['pixel_samples_per_frame'],
            checked_sectors=t['runtime_sectors_checked']))
        for file in ('metadata.json',cpu_file,'timing.json','profile.json'):
            archive(work/file,f'{name}-{file}')
    with np.load(a.states,allow_pickle=False) as data:five=data['five_states']
    work=a.candidate/'captures';work.mkdir(exist_ok=True);captures=[]
    for index in (0,1,63,64,128,191):
        screen,row=capture(a.fuse,a.candidate/'candidate.trd',m,index,work)
        expected=reference_screen(b''.join(expand(five[index].tobytes())),index,m['frames'])
        if screen!=expected:raise AssertionError(('full screen mismatch',index))
        (work/f'frame-{index}.scr').write_bytes(screen);captures.append(dict(row,compared_bytes=len(screen),mismatches=0))
        for ext in ('scr','trace.txt','debugger.txt'):archive(work/f'frame-{index}.{ext}',f'frame-{index}.{ext}')
    for file in ('build.json','probe.json','video.stream','video.raw','timing.trace.txt','timing.debugger.txt',
                 'pre-fix-cpu.json','pre-fix-timing.json','pre-fix-metadata.json','edges/edges.json'):
        archive(a.candidate/file,file.replace('/','-'))
    archive(a.baseline/'video.raw','fap3-video.raw')
    shutil.copyfile(a.candidate/'candidate.trd',a.trd)
    before,after=variants
    result=dict(complete=True,release=False,baseline_commit='c6b8475',scope=__doc__,variants=variants,captures=captures,
        selected_image=a.trd.name,selected_trd_sha256=sha(a.trd.read_bytes()),
        decoder_delta_tstates=after['decoder_tstates']-before['decoder_tstates'],
        total_transport_delta_tstates=after['total_transport_tstates']-before['total_transport_tstates'],
        compressed_byte_delta=after['video_bytes']-before['video_bytes'],archives=archives,
        decision='Retain optional measured faster transport; default remains ZX0. Neither timing gate passes.',
        limitations='192-frame montage only; unchanged 172-entry row dictionary. Token yields are not a bounded-duration preemption. No whole-movie capacity or cadence claim.',
        timing_assumptions='CPU: fixed 256-byte demands, mocked ROM and frozen service clock, no IRQ/ULA. Fuse: physical disk/ROM, IRQ/ULA and actual publication OUTs. Rates normalized to 50 Hz; never add CPU and elapsed totals.',
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in (
            'resumable_lzsa2.py','lzsa2_stream.py','lzsa2_row_player.py','build_row_lzsa.py','benchmark_row_lzsa.py',
            'test_row_lzsa.py','probe_row_lzsa.py','profile_row_transport.py','summarize_row_lzsa.py')})
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k in ('complete','selected_image','decoder_delta_tstates','total_transport_delta_tstates','compressed_byte_delta')}))


if __name__=='__main__':main()
