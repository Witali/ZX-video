"""Save bounded TRD measurements and replay evidence; never infer a timing pass.

complete means all requested observations exist. Separate exact-deadline
and fallback gates require successful image/audio/sector verification too.
"""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np
from build_fap3_trd import sha
from measure_fap3_fuse import FIELD


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('work','build','captures','evidence','output'): p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args(); b=json.loads(a.build.read_text()); c=json.loads(a.captures.read_text())
    t=json.loads((a.work/'timing.json').read_text()); m=json.loads((a.work/'metadata.json').read_text())
    if len({r['trd_sha256'] for r in (b,c,t,m)})!=1: raise ValueError('evidence belongs to different images')
    pubs=t['publications']; intervals=np.diff([v['tstate'] for v in pubs]); fields=np.diff([v['field'] for v in pubs])
    complete=bool(b['complete'] and c['complete'] and t['complete'] and len(pubs)==b['frames'])
    integrity=complete and t['audio_underruns']==0 and t['ay_record_field_gaps']==0 and t['ay_record_field_duplicates']==0
    nominal=integrity and t['nominal_late_frames']==0 and all(fields==6) and np.max(np.abs(t['actual_phase_tstates']))<=64
    fallback=integrity and t['max_late_fields']<=1 and t['actual_out_over_one_field']==0 and t['bad_actual_intervals']==0
    fallback=fallback and all(r['recovered_at'] is not None for r in t['late_runs'])
    quality=[]; n=b['contract']['window']
    for index,start in enumerate(b['contract']['starts']):
        rows=b['quality'][index*n:(index+1)*n]
        old=float(np.mean([r['four_mse'] for r in rows])); new=float(np.mean([r['five_mse'] for r in rows]))
        quality.append(dict(source_start=start,frames=n,mean_four_mse=old,mean_five_mse=new,
                            mse_reduction_percent=100*(1-new/old),worse_frames=sum(r['five_mse']>r['four_mse']+1e-9 for r in rows)))
    a.evidence.mkdir(parents=True,exist_ok=True); archives=[]
    sources=[a.work/name for name in ('metadata.json','video.raw','timing.json','timing.trace.txt','timing.debugger.txt','tests.txt')]
    for row in c['full_screen_captures']:
        for ext,key in (('scr','screen_sha256'),('trace.txt','trace_sha256'),('debugger.txt','debugger_sha256')):
            path=a.work/'captures'/f'frame-{row["frame"]}.{ext}'
            if sha(path.read_bytes())!=row[key]: raise ValueError(('capture identity differs',str(path)))
            sources.append(path)
    for source in sources:
        blob=source.read_bytes(); name=source.name+'.gz'; packed=gzip.compress(blob,mtime=0)
        (a.evidence/name).write_bytes(packed)
        archives.append(dict(file=name,bytes=len(blob),sha256=sha(blob),archive_sha256=sha(packed)))
    with np.load(a.work/'prepared.npz',allow_pickle=False) as data:
        np.savez_compressed(a.evidence/'states.npz',states=data['states'],five_states=data['five_states'])
    sources=('build_five_level_test_trd.py','row_dictionary_video.py','capture_five_level_fuse.py',
        'summarize_five_level_test.py','measure_fap3_fuse.py','encode_fap3.py','fast_zx0_player.py',
        'faster_zx0.py','bank2_zx0.py','inplace_slot_player.py','hybrid_five_level.py','five_level_dither.py',
        'build_long_video_trd.py','cell_screen_z80.py')
    result=dict(complete=complete,release=False,scope='One independent 192-frame five-level montage; entire test disk measured, not the entire movie',
        trd_sha256=b['trd_sha256'],frames=b['frames'],nominal_duration_seconds=b['duration_seconds'],
        image_bytes=b['trd_bytes'],used_file_bytes=b['used_sectors']*256,free_file_bytes=b['free_sectors']*256,
        compressed_video_bytes=b['video_bytes'],row_dictionary_entries=b['row_dictionary']['entries'],
        cadence=dict(nominal_pass=bool(nominal),fallback_pass=bool(fallback),nominal_late_frames=t['nominal_late_frames'],
            max_late_fields=t['max_late_fields'],max_lateness_ms=t['max_actual_deviation_tstates']/FIELD*20,
            actual_mean_fps_at_50hz=(len(pubs)-1)*FIELD*50/(pubs[-1]['tstate']-pubs[0]['tstate']),
            frame_interval_ms_at_50hz=dict(min=float(intervals.min()/FIELD*20),mean=float(intervals.mean()/FIELD*20),max=float(intervals.max()/FIELD*20)),
            nominal_six_field_intervals=int(sum(fields==6)),intervals=len(fields),interval_field_histogram=dict(Counter(map(int,fields))),
            late_runs=t['late_runs'],bad_fallback_intervals=t['bad_actual_intervals'],
            actual_phase_tstates=t['actual_phase_tstates'],normalization='70908 T/field, 50 fields/s; physical 128K clock differs slightly from exactly 50 Hz'),
        audio=dict(exact_ay_records=t['ay_records_exact'],ticks=t['ay_ticks'],underruns=t['audio_underruns'],
                   missing_fields=t['ay_record_field_gaps'],duplicate_fields=t['ay_record_field_duplicates'],
                   av_sync_pass=bool(nominal),waveform_fidelity_remeasured=False),
        runtime_disk=dict(checked_sectors=t['runtime_sectors_checked'],fast_read_retries=t['fast_read_retries'],
            observed_read_call_tstates=sum(r['tstates'] for r in t['reads']),
            observed_seek_call_tstates=sum(r['tstates'] for r in t['seek_calls']),
            includes='Elapsed read/seek windows include ROM, FDC/physical emulation waits and IRQs; not deterministic CPU-only counts'),
        elapsed_timing=t['elapsed_timing'],quality=dict(windows=quality,full_screen_capture_frames=[r['frame'] for r in c['full_screen_captures']],
            full_screen_compared_bytes=sum(r['compared_bytes'] for r in c['full_screen_captures']),
            full_screen_mismatched_bytes=sum(r['mismatched_bytes'] for r in c['full_screen_captures']),
            sampled_frames=t['native_frames_sampled'],sample_bytes_per_frame=t['pixel_samples_per_frame'],
            metric=c['metric'],scope='MSE against freshly scaled RGB; lossless equality against quantized five-level reference. No claim of 95% original-video fidelity.'),
        decision='Keep as a visual prototype only: pixel and AY data exact, but accumulated video delay fails both timing contracts; no release replacement.',
        archives=archives,states_archive_sha256=sha((a.evidence/'states.npz').read_bytes()),
        source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in sources})
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=complete,nominal_pass=bool(nominal),fallback_pass=bool(fallback),mean_fps=result['cadence']['actual_mean_fps_at_50hz'],quality=quality)))


if __name__=='__main__': main()
