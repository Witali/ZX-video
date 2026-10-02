"""Compare actual PDM timing and modeled idle tones at unchanged audio level."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from build_pdm import reconstruct,RATE
from verify_pdm import save


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--before',type=Path,required=True)
    parser.add_argument('--after',type=Path,required=True)
    parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args();rows=[]
    before=gzip.decompress((args.before/'soundtrack.ima.gz').read_bytes())
    if before!=gzip.decompress((args.after/'soundtrack.ima.gz').read_bytes()):
        raise ValueError('comparison requires identical encoded audio')
    for name,directory in (('before',args.before),('after',args.after)):
        proof=json.loads((directory/'verification.json').read_bytes())['fuse']
        times=np.frombuffer(gzip.decompress((directory/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)
        slots=(len(times)-1)//2;times=times[:slots+1]
        idle=np.r_[np.zeros(3,dtype=np.uint8),((np.arange(slots-3)+1)%2).astype(np.uint8)]
        raw=subprocess.run([args.ffmpeg,'-v','error','-nostdin','-f','f32le','-ar',str(RATE),'-ac','1','-i','-',
                            '-af','highpass=f=70,lowpass=f=4500:p=2,lowpass=f=4500:p=2',
                            '-ar','44100','-f','f32le','-'],input=reconstruct(idle,times).astype('<f4').tobytes(),
                            capture_output=True,check=True).stdout
        signal=np.frombuffer(raw,'<f4').astype(float)[4410:-4410]
        count=44100*8;window=np.hanning(count)
        spectrum=abs(np.fft.rfft(signal[:count]*window))*2/window.sum()
        frequencies=np.fft.rfftfreq(count,1/44100)
        selection=np.flatnonzero((frequencies>=1000)&(frequencies<=8000))
        peak=selection[np.argmax(spectrum[selection])]
        holds=np.diff(times)
        rows.append(dict(name=name,average_pcm_rate_hz=proof['average_pcm_rate_hz'],
                         average_pdm_rate_hz=proof['average_pdm_rate_hz'],
                         native_loop_tstates=proof['native_tstates_per_cycle'],
                         additional_ula_tstates_two_loops=proof['additional_ula_tstates'],
                         fraction_exactly_73_tstates=float(np.mean(holds==73)),
                         interval_std_tstates=float(np.std(holds)),
                         idle_rms=float(np.sqrt(np.mean(signal*signal))),
                         largest_idle_tone_hz=float(frequencies[peak]),
                         largest_idle_tone_dbfs=float(20*np.log10(max(spectrum[peak],1e-20)))))
    report=dict(date='2026-10-02',same_encoded_audio=True,same_modulator=True,rc_model=False,rows=rows,
                interval_std_reduction_percent=100*(1-rows[1]['interval_std_tstates']/rows[0]['interval_std_tstates']),
                idle_tone_reduction_db=rows[0]['largest_idle_tone_dbfs']-rows[1]['largest_idle_tone_dbfs'],
                pdm_rate_change_percent=100*(rows[1]['average_pdm_rate_hz']/rows[0]['average_pdm_rate_hz']-1),
                scope='Saved full Fuse schedules; synthetic midscale PDM; same 70 Hz HP/two 4.5 kHz LPs; no speaker model',
                producer_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n',b'\n')).hexdigest())
    save(args.after/'timing-comparison.json',report);print(json.dumps(report),flush=True)


if __name__=='__main__':main()
