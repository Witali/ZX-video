"""Compare the saved 64-T and 52-T builds over the same source passage."""
import argparse
from pathlib import Path
import wave
import numpy as np
from verify_pdm import save


def read(path):
    with wave.open(str(path),'rb') as stream:
        assert stream.getnchannels()==1 and stream.getsampwidth()==2 and stream.getframerate()==44100
        return np.frombuffer(stream.readframes(stream.getnframes()),'<i2').astype(float)/32767


def compare(root):
    result={}
    for name,folder in (('pdm64',root/'experiments/pdm64'),('pdm52',root/'preview')):
        reference=read(folder/'original-preview.wav')[4410:445410]
        candidate=read(folder/'beeper-preview.wav')[4410:445410]
        assert len(reference)==len(candidate)==441000
        result[name]=dict(waveform_correlation=float(np.corrcoef(reference,candidate)[0,1]),
            reconstruction_snr_db=float(10*np.log10(np.mean(reference**2)/np.mean((candidate-reference)**2))))
    report=dict(source_interval_seconds=[60.1,70.1],duration_seconds=10,metrics=result,
        snr_improvement_db=result['pdm52']['reconstruction_snr_db']-result['pdm64']['reconstruction_snr_db'],
        scope='Same source interval, same 4.5 kHz reconstruction filters; not a perceptual intelligibility score')
    save(root/'comparison.json',report)
    return report


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('root',type=Path,nargs='?',default=Path(__file__).resolve().parent)
    print(json.dumps(compare(p.parse_args().root)),flush=True)
