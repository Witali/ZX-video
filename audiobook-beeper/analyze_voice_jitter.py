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
from verify_direct import reference,expand_samples,sample_positions
from pdm_player import CPU_CLOCK


def analyze(out,ffmpeg,loop=0):
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    pcm,_,levels,bits=reference(packed,cycles=loop+1,model=meta.get('model'),idle_pairs=meta.get('loop_idle_pairs',0));n=len(pcm);count=meta.get('outputs_per_cycle',n*16)
    bits=bits[loop*count:(loop+1)*count]
    t=np.frombuffer(gzip.decompress((out/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[loop*count:(loop+1)*count+1]
    t=t-t[0]
    sample_t=t[sample_positions(meta)];ideal=np.linspace(0,int(t[-1]),n+1)
    jitter=(sample_t-ideal)/CPU_CLOCK
    with wave.open(str(out/'source-preview.wav'),'rb') as w:source=np.frombuffer(w.readframes(w.getnframes()),'u1')
    fixed_edges=ideal;fixed_values=source/256
    reference_rate=meta.get('compensated_reference_rate_hz')
    if reference_rate:
        # Explicit encoder-selected original clock, never fitted to the output.
        # A phase-lock filler lengthens only the already silent loop boundary.
        period=CPU_CLOCK/reference_rate
        segments=int(np.ceil(t[-1]/period))
        fixed_edges=np.r_[np.arange(segments)*period,t[-1]]
        fixed_values=np.pad(source/256,(0,max(0,segments-n)),constant_values=.5)[:segments]
    signals={'output':reconstruct(bits[:count],t),
             'source_warped':reconstruct(expand_samples(meta,source)/256,t),
             'source_fixed':reconstruct(fixed_values,fixed_edges)}
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
    report=dict(scope=__doc__,loop_index=loop,source_samples=n,source_rate_hz=8000,actual_mean_rate_hz=n*CPU_CLOCK/t[-1],
                uniform_reference_rate_hz=reference_rate or n*CPU_CLOCK/t[-1],
                reference_clock='Explicit encoder-selected original rate; zero-padded silent loop tail' if reference_rate else 'Measured mean rate',
                warped_clock_total_snr_db=ratio(warped,output-warped),
                fixed_mean_clock_total_snr_db=ratio(fixed,output-fixed),
                clock_only_snr_db=ratio(fixed,warped-fixed),filter=FILTER,
                jitter_seconds=dict(minimum=float(jitter.min()),maximum=float(jitter.max()),
                                    mean=float(jitter.mean()),standard_deviation=float(jitter.std()),peak_to_peak=float(np.ptp(jitter))),
                jitter_line_amplitude_seconds=amplitudes,folded_field_jitter_seconds=folded.tolist(),speed_windows=windows,
                physical_hardware_tested=False)
    prefix='' if loop==0 else f'loop-{loop+1}-'
    (out/(prefix+'voice-jitter.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    write_wav(out/(prefix+'uniform-clock-source-preview.wav'),filtered['source_fixed'])
    write_wav(out/(prefix+'warped-clock-source-preview.wav'),filtered['source_warped'])
    write_wav(out/(prefix+'clock-aware-output-preview.wav'),filtered['output'])
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--loop',type=int,choices=(0,1),default=0)
    a=p.parse_args();report=analyze(a.directory,a.ffmpeg,a.loop)
    print(json.dumps({k:v for k,v in report.items() if k!='folded_field_jitter_seconds'}),flush=True)


if __name__=='__main__':main()
