"""Bounded same-control ablations and complete checks of the revised audition."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import wave
import numpy as np

HERE=Path(__file__).resolve().parent
CORE=HERE.parents[1]
sys.path.insert(0,str(CORE))
import experimental_six_voice as synth
import noise_colour
import quality
from simulation_refine import Objective
from probe import read_wav, artifacts, boundary_jumps


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--candidate',type=Path)
    args=parser.parse_args()
    old=CORE/'analysis/six_voice/evidence'
    report=json.loads((old/'report.json').read_bytes())
    gain=report['results']['selectable']['feedback']['voice_gain']
    with np.load(old/'selectable-controls.npz') as stored:
        controls={k:stored[k] for k in stored.files}
    reference=synth.read_reference(old/'reference.wav')
    objective=Objective(reference)
    settings=[('legacy',{}),('bandwidth-only',dict(output_bandwidth_hz=8000.)),
              ('aligned-only',dict(aligned_triangle=True))]
    settings += [(f'ramp-{ms:g}ms',dict(transition_ms=ms)) for ms in (2.,4.,8.)]
    settings += [(f'combined-{ms:g}ms',dict(transition_ms=ms,aligned_triangle=True,output_bandwidth_hz=8000.)) for ms in (2.,4.,8.)]
    results=[]
    with tempfile.TemporaryDirectory(dir=HERE,prefix='replay-') as temporary:
        for name,options in settings:
            audio=synth.render(controls,gain,**options)
            if name=='legacy':
                replay=Path(temporary)/'legacy.wav'
                quality.write_wav(replay,audio,44100)
                assert replay.read_bytes()==(old/'six-voice-preview.wav').read_bytes()
            entry=dict(name=name,options=options,peak=float(abs(audio).max()),
                       metrics=objective.measure(noise_colour.downsample(audio)),
                       artifacts=artifacts(audio,reference))
            results.append(entry)
            print(json.dumps(entry),flush=True)
    result=dict(date='2026-10-13',complete=True,seconds=30.,ticks=1500,
                baseline_commit='bd2a5be2',same_controls_and_gain=True,
                baseline_controls_sha256=hashlib.sha256((old/'selectable-controls.npz').read_bytes()).hexdigest(),
                reference_sha256=hashlib.sha256((old/'reference.wav').read_bytes()).hexdigest(),
                baseline_wav_replay_exact=True,baseline_boundaries=boundary_jumps(controls,gain),
                trials=results,limitations='Signal diagnostics only; no claim of subjective click elimination, ringing elimination or intelligibility.')
    if args.candidate:
        candidate_report=json.loads((args.candidate/'report.json').read_bytes())
        assert candidate_report['reference_sha256']==result['reference_sha256']
        assert candidate_report['ticks']==1500 and candidate_report['seconds']==30
        options=candidate_report['render_options']
        with np.load(args.candidate/'selectable-controls.npz') as stored:
            final_controls={k:stored[k] for k in stored.files}
        audio=synth.render(final_controls,candidate_report['results']['selectable']['feedback']['voice_gain'],**options)
        with tempfile.TemporaryDirectory(dir=HERE,prefix='candidate-replay-') as temporary:
            replay=Path(temporary)/'replay.wav'
            quality.write_wav(replay,audio,44100)
            assert replay.read_bytes()==(args.candidate/'six-voice-preview.wav').read_bytes()
        assert len(audio)==30*44100 and np.isfinite(audio).all() and abs(audio).max()<1
        result['candidate']=dict(options=options,controls_only_replay_exact=True,
            samples=len(audio),clipping_samples=int((abs(audio)>=1).sum()),peak=float(abs(audio).max()),
            metrics=objective.measure(noise_colour.downsample(audio)),artifacts=artifacts(audio,reference))
        print(json.dumps(dict(candidate=result['candidate'])),flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__=='__main__':main()
