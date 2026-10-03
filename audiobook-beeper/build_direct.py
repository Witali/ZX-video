"""Build and validate direct packet playback on the complete unchanged source."""
import argparse,gzip,json,subprocess,sys
from pathlib import Path
from functools import partial
import numpy as np
from direct_player import HERE,prepare,MEASURED_MODEL
from verify_direct import reference,intervals,sample_positions
from verify_packet import native_check,fuse_check
from verify_pcm import save
from build_packet import finish,render
from analyze_voice_jitter import analyze


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fuse',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--finish-only',action='store_true');p.add_argument('--measured-model',action='store_true')
    a=p.parse_args();out=a.output.resolve()
    if not a.finish_only:
        if out.exists() and any(out.iterdir()):p.error('output must be empty')
        prepare(out,MEASURED_MODEL if a.measured_model else None);meta=json.loads((out/'player.json').read_bytes())
        ref=partial(reference,model=meta.get('model'),idle_pairs=meta.get('loop_idle_pairs',0))
        packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
        save(out/'native.json',native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed,ref,intervals))
        save(out/'fuse.json',fuse_check(a.fuse,out,meta,packed,False,ref,intervals))
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(a.fuse),
                        '--output',str(out/'sound-128'),'--machine','128'],check=True)
    meta=json.loads((out/'player.json').read_bytes());ref=partial(reference,model=meta.get('model'),idle_pairs=meta.get('loop_idle_pairs',0))
    report=finish(out,a.ffmpeg,ref,intervals)
    report['date']='2026-10-03'
    report['second_loop_render']=render(out,a.ffmpeg,False,ref,intervals,loop=1)
    rate=report['fuse']['average_pcm_rate_hz']
    snr=min(report['render']['total_snr_db'],report['second_loop_render']['total_snr_db'])
    all_times=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
    positions=sample_positions(meta);count=meta.get('outputs_per_cycle',meta['pcm_samples']*16)
    timeline=all_times[np.r_[positions[:-1],positions+count]]
    windows=[]
    for samples in (800,8000):
        starts=np.arange(0,len(timeline)-samples,100)
        rates=samples*3546900/(timeline[starts+samples]-timeline[starts])
        windows.append(dict(source_window_seconds=samples/8000,hop_source_samples=100,
                            count=len(starts),minimum_rate_hz=float(rates.min()),maximum_rate_hz=float(rates.max()),
                            maximum_absolute_speed_error_percent=float(np.max(abs(rates/8000-1))*100),
                            every_window_within_two_percent=bool(np.all(abs(rates/8000-1)<=.02))))
    report['acceptance']=dict(source_speed_error_percent=(rate/8000-1)*100,
                              speed_within_two_percent=abs(rate/8000-1)<=.02,
                              speed_windows=windows,
                              minimum_measured_total_snr_db=snr,both_loops_snr_at_least_20_db=snr>=20,
                              physical_hardware_tested=False)
    report['voice_clock']=analyze(out,a.ffmpeg)
    report['second_loop_voice_clock']=analyze(out,a.ffmpeg,loop=1)
    report['acceptance']['fixed_mean_clock_total_snr_db']=report['voice_clock']['fixed_mean_clock_total_snr_db']
    report['acceptance']['voice_clock_quality_passes']=min(report[k]['fixed_mean_clock_total_snr_db'] for k in ('voice_clock','second_loop_voice_clock'))>=20
    save(out/'report.json',report);print(json.dumps(report['acceptance']),flush=True)


if __name__=='__main__':main()
