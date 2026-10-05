"""Same-payload ideal-clock controls; these do not execute on the Spectrum."""
import argparse
import hashlib
from pathlib import Path
import sys
import wave

import numpy as np

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]))
sys.path.insert(0,str(HERE.parent/'xlaw-pc'))
from stream_model import modulate
from convert_mulaw_audio import filter_signal
from assess_snr import ratio
from build_pdm import write_wav
from g711_codec import decode
from verify_pdm import save


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True);a=p.parse_args();out=a.input
    payload=(out/'soundtrack.mulaw').read_bytes()
    with wave.open(str(out/'source-preview.wav'),'rb') as w:
        assert (w.getnchannels(),w.getsampwidth(),w.getframerate())==(1,2,8000)
        pcm=np.frombuffer(w.readframes(w.getnframes()),'<i2')
    rows=[]
    for slots in (8,16):
        times=np.arange(len(payload)*slots+1)*3546900/(8000*slots)
        ref=filter_signal((pcm.astype(float)+32768)/65536,times[::slots],a.ffmpeg,768000)
        for order in (1,2):
            stats=None
            if order==1:
                area=32768+np.cumsum(np.repeat(decode(payload,'mulaw').astype(np.int64)+32768,slots))
                bits=np.diff(np.r_[0,area//65536]).astype('u1')
            else:bits,stats=modulate(payload,'mulaw',slots)
            signal=filter_signal(bits,times,a.ffmpeg,768000)
            row=dict(order=order,pdm_hz=8000*slots,snr_db=ratio(ref[4410:-4410],signal[4410:-4410]-ref[4410:-4410]),
                     exact_sd2_state=stats,z80_executable=False)
            rows.append(row);print(row,flush=True)
            if order==2 and slots==16:write_wav(out/'pc-only-sd2-128-preview.wav',signal*.5)
    save(out/'pc-comparison.json',dict(complete=True,scope=__doc__,rows=rows,
         payload_sha256=hashlib.sha256(payload).hexdigest(),source_samples=len(pcm),
         integration_rate_hz=768000,filter='same float64 70/4500/4500 Hz filter as real-player scoring',
         no_delay_or_gain_fitting=True,physical_hardware_measured=False))


if __name__=='__main__':main()
