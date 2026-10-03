"""Separate periodic sample-clock error from the existing warped-clock SNR.

The fixed-clock reference uses the measured mean rate, preserving the allowed
overall speed error but no within-frame acceleration/deceleration. No audio
correlation, fitted phase or gain is used.
"""
import argparse,gzip,json,subprocess,wave
from pathlib import Path
import numpy as np
from build_pdm import reconstruct,RATE,write_wav
from assess_snr import FILTER,ratio
from verify_direct import reference
from pdm_player import CPU_CLOCK


def analyze(out,ffmpeg):
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    pcm,_,levels,bits=reference(packed,cycles=1,model=meta.get('model'));n=len(pcm);count=n*16
    t=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:count+1]
    sample_t=t[::16];ideal=np.linspace(0,int(t[-1]),n+1)
    jitter=(sample_t-ideal)/CPU_CLOCK
    with wave.open(str(out/'source-preview.wav'),'rb') as w:source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    signals={'output':reconstruct(bits[:count],t),
             'source_warped':reconstruct(np.repeat(source,16)/256,t),
             'source_fixed':reconstruct(source/256,ideal)}
    filtered={}
    for name,signal in signals.items():
        run=subprocess.run([ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                            '-af',FILTER,'-ar','44100','-f','f32le','-'],input=signal.astype('<f4').tobytes(),capture_output=True,check=True)
        filtered[name]=np.frombuffer(run.stdout,'<f4').astype(float)
    output=filtered['output'][4410:-4410];fixed=filtered['source_fixed'][4410:-4410];warped=filtered['source_warped'][4410:-4410]
    windows=[]
    for size in (1,8,40,80,160,800):
        starts=np.arange(n-size+1);rates=size*CPU_CLOCK/(sample_t[starts+size]-sample_t[starts])
        windows.append(dict(source_samples=size,nominal_ms=size/8,min_hz=float(rates.min()),max_hz=float(rates.max())))
    # Fold the error in time into one 50-Hz field (phase origin is arbitrary).
    bins=np.floor((sample_t[:-1]%70908)*100/70908).astype(int)
    totals=np.bincount(bins,weights=jitter[:-1],minlength=100)
    folded=totals/np.maximum(1,np.bincount(bins,minlength=100))
    centered=jitter[:-1]-jitter[:-1].mean()
    amplitudes={str(hz):float(2*abs(np.mean(centered*np.exp(-2j*np.pi*hz*sample_t[:-1]/CPU_CLOCK)))) for hz in (25,50,100,150,200,250)}
    report=dict(scope=__doc__,source_samples=n,source_rate_hz=8000,actual_mean_rate_hz=n*CPU_CLOCK/t[-1],
                warped_clock_total_snr_db=ratio(warped,output-warped),
                fixed_mean_clock_total_snr_db=ratio(fixed,output-fixed),
                clock_only_snr_db=ratio(fixed,warped-fixed),filter=FILTER,
                jitter_seconds=dict(minimum=float(jitter.min()),maximum=float(jitter.max()),
                                    mean=float(jitter.mean()),standard_deviation=float(jitter.std()),peak_to_peak=float(np.ptp(jitter))),
                jitter_line_amplitude_seconds=amplitudes,folded_field_jitter_seconds=folded.tolist(),speed_windows=windows,
                physical_hardware_tested=False)
    (out/'voice-jitter.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    write_wav(out/'uniform-clock-source-preview.wav',filtered['source_fixed'])
    write_wav(out/'warped-clock-source-preview.wav',filtered['source_warped'])
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();report=analyze(a.directory,a.ffmpeg)
    print(json.dumps({k:v for k,v in report.items() if k!='folded_field_jitter_seconds'}),flush=True)


if __name__=='__main__':main()
