"""Build and validate direct packet playback on the complete unchanged source."""
import argparse,gzip,json,subprocess,sys
from pathlib import Path
import numpy as np
from direct_player import HERE,prepare
from verify_direct import reference,intervals
from verify_packet import native_check,fuse_check
from verify_pcm import save
from build_packet import finish


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path)
    p.add_argument('--fuse',required=True,type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--finish-only',action='store_true');a=p.parse_args();out=a.output.resolve()
    if not a.finish_only:
        if out.exists() and any(out.iterdir()):p.error('output must be empty')
        prepare(out);meta=json.loads((out/'player.json').read_bytes())
        packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
        save(out/'native.json',native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed,reference,intervals))
        save(out/'fuse.json',fuse_check(a.fuse,out,meta,packed,False,reference,intervals))
        subprocess.run([sys.executable,str(HERE/'record_pcm.py'),str(out),'--fuse',str(a.fuse),
                        '--output',str(out/'sound-128'),'--machine','128'],check=True)
    report=finish(out,a.ffmpeg,reference,intervals)
    report['date']='2026-10-03'
    rate=report['fuse']['average_pcm_rate_hz'];snr=report['render']['total_snr_db']
    timeline=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[::16]
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
                              measured_total_snr_db=snr,snr_at_least_20_db=snr>=20,
                              physical_hardware_tested=False)
    save(out/'report.json',report);print(json.dumps(report['acceptance']),flush=True)


if __name__=='__main__':main()
