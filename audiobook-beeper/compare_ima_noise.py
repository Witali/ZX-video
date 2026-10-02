"""Compare matched-level PDM noise and idle tones using complete Fuse schedules."""
import argparse,gzip,json,subprocess
from pathlib import Path
import numpy as np
from build_pdm import reconstruct,write_wav,RATE
from ima_codec import decode
from verify_ima import reference
from verify_pdm import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before',type=Path,required=True);p.add_argument('--after',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True);args=p.parse_args()
    old_packed=gzip.decompress((args.before/'soundtrack.ima.gz').read_bytes())
    rows=[]
    def filtered(signal):
        raw=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
            '-af','highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2','-ar','44100','-f','f32le','-'],
            input=signal.astype('<f4').tobytes(),capture_output=True,check=True).stdout
        return np.frombuffer(raw,'<f4').astype(float)
    for name,folder,packed in [('before',args.before,old_packed),('balanced_same_level',args.after,old_packed),
                              ('balanced_louder',args.after,gzip.decompress((args.after/'soundtrack.ima.gz').read_bytes()))]:
        meta=json.loads((folder/'player.json').read_bytes())
        if name=='before':
            # Archived six-slot reference before the page/bank-tail revision.
            pcm,_=decode(packed);u8=((pcm.astype(np.int32)+32768)>>8).astype(np.uint8)
            weights=np.full(len(pcm),6);end=0
            for s in meta['sections']:end+=s['bytes'];weights[2*end-2]=10
            levels=np.repeat(u8,weights);n=len(levels)
            summed=np.cumsum(levels,dtype=np.int64)+128
            rawbits=(summed//256-np.r_[0,summed[:-1]//256]).astype(np.uint8)
            bits=np.r_[np.zeros(3,dtype=np.uint8),rawbits[:-3]]
        else:
            _,_,levels,bits,n=reference(packed,meta);levels=levels[:n];bits=bits[:n]
        times=np.frombuffer(gzip.decompress((folder/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:n+1]
        a=filtered(reconstruct(np.r_[np.zeros(3),levels[:-3]/256],times))
        b=filtered(reconstruct(bits,times))
        selection=slice(4410,-4410);ref=a[selection];signal=b[selection]
        # Synthetic midscale tests PDM idle tones without source recording noise.
        idle=np.r_[np.zeros(3,dtype=np.uint8),((np.arange(n-3)+1)%2).astype(np.uint8)]
        quiet=filtered(reconstruct(idle,times))[4410:-4410]
        count=min(44100*8,len(quiet));window=np.hanning(count)
        spectrum=abs(np.fft.rfft(quiet[:count]*window))*2/window.sum()
        frequencies=np.fft.rfftfreq(count,1/44100)
        band=(frequencies>=1000)&(frequencies<=8000)
        index=np.flatnonzero(band)[np.argmax(spectrum[band])]
        row=dict(name=name,pdm_snr_db=float(10*np.log10(np.mean(ref**2)/np.mean((signal-ref)**2))),
                 correlation=float(np.corrcoef(ref,signal)[0,1]),signal_rms=float(np.sqrt(np.mean(ref**2))),
                 error_rms=float(np.sqrt(np.mean((signal-ref)**2))),idle_rms=float(np.sqrt(np.mean(quiet**2))),
                 largest_idle_tone_hz=float(frequencies[index]),largest_idle_tone_dbfs=float(20*np.log10(max(spectrum[index],1e-20))))
        rows.append(row)
        # Match listening loudness: the comparison must not win just by being louder.
        target_rms=.15;gain=target_rms/max(np.sqrt(np.mean(ref**2)),1e-12)
        peak=float(np.max(abs(b*gain)));row['comparison_gain']=gain
        row['peak_at_matched_rms']=peak
        # Common later attenuation prevents clipping while retaining the RMS match.
        if name!='balanced_same_level':np.save(args.after/f'.comparison-{name}.npy',b*gain)
    before=np.load(args.after/'.comparison-before.npy');after=np.load(args.after/'.comparison-balanced_louder.npy')
    gain=min(1.,.9/max(np.max(abs(before)),np.max(abs(after))))
    write_wav(args.after/'noise-before-preview.wav',before*gain)
    write_wav(args.after/'noise-after-preview.wav',after*gain)
    for name in ('before','balanced_louder'):(args.after/f'.comparison-{name}.npy').unlink()
    report=dict(complete=True,rows=rows,common_listening_attenuation=gain,
        pdm_snr_improvement_db=rows[2]['pdm_snr_db']-rows[0]['pdm_snr_db'],
        code_only_snr_improvement_db=rows[1]['pdm_snr_db']-rows[0]['pdm_snr_db'],
        largest_idle_tone_reduction_db=rows[0]['largest_idle_tone_dbfs']-rows[1]['largest_idle_tone_dbfs'],
        scope='measured Fuse schedules, modeled first-order PDM; same reconstruction filter; not physical speaker or listener evidence',
        matched_level_scope='same compressed source in before and balanced_same_level; louder variant includes peak limiting',
        filter='70 Hz HP, two 4.5 kHz two-pole LPs',excluded_edge_seconds=.1)
    save(args.after/'noise-comparison.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':main()
