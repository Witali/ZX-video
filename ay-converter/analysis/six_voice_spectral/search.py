"""Bounded full-excerpt spectral fitting trials on the unchanged six-voice model."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np

CORE=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(CORE))
import experimental_six_voice as synth
import noise_colour
import quality
from simulation_refine import Objective


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--dc-compensated',action='store_true')
    parser.add_argument('--window-size',type=int,default=2048,choices=(512,1024,1536,2048))
    parser.add_argument('--weight',type=float)
    parser.add_argument('--band-peaks',type=int,default=4)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    baseline=CORE/'analysis/six_voice_clicks/evidence'
    source=baseline/'reference.wav'
    samples=synth.read_reference(source)
    options=json.loads((baseline/'report.json').read_bytes())['render_options']
    if args.dc_compensated:options['compensate_dc']=True
    objective=Objective(samples)
    templates=synth.dictionary(args.window_size)
    trials=[]
    settings=((0.,0),(.5,4),(1.,4)) if args.dc_compensated else ((.5,4),(1.,4),(1.5,4),(1.,0))
    if args.weight is not None:settings=((args.weight,args.band_peaks),)
    for exponent,bands in settings:
        name=f'weight-{exponent:g}-bands-{bands}'
        target=args.output/name
        target.mkdir(exist_ok=True)
        started=time.perf_counter()
        controls,gain=synth.fit(samples,templates,spectral_weight_exponent=exponent,band_peak_count=bands)
        controls,audio,feedback=synth.feedback(samples,controls,gain,objective,render_options=options)
        np.savez_compressed(target/'controls.npz',**controls)
        quality.write_wav(target/'preview.wav',audio,44100)
        result=dict(name=name,spectral_weight_exponent=exponent,band_peak_count=bands,
                    analysis_window=args.window_size,
                    metrics=feedback['final'],feedback=feedback,peak=float(abs(audio).max()),
                    clipping_samples=int((abs(audio)>=1).sum()),elapsed_seconds=time.perf_counter()-started)
        (target/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
        trials.append(result)
        print(json.dumps(dict(trial=result)),flush=True)
        (args.output/'trials.json').write_text(json.dumps(dict(date='2026-10-13',source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            render_options=options,trials=trials),indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
