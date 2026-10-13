"""Use AY noise only with source evidence and a measurable rendered benefit.

Tone/noise routing is a perceptual decision, not an automatic residual fill.
Keep the noise generator's period history even in muted intervals, so gating
does not unnecessarily alter the LFSR phase of subsequent effects.
"""
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import music_profile
import noise_colour
from simulation_refine import Objective

HERE=Path(__file__).resolve().parent


def active_noise(rows):
    return np.any([(rows[:,8+c]>0)&((rows[:,7]&(1<<(c+3)))==0) for c in range(3)],axis=0)


def remove_noise(rows):
    result=rows.copy();table=music_profile.chip_levels()
    for channel in range(3):
        noisy=(rows[:,8+channel]>0)&((rows[:,7]&(1<<(channel+3)))==0)
        mixed=noisy&((rows[:,7]&(1<<channel))==0)
        fixed=mixed&(rows[:,8+channel]<16)
        # Removing the Boolean noise gate doubles the tone's mean amplitude.
        # Choose the closest fixed DAC level to preserve that tonal component.
        result[fixed,8+channel]=abs(table[rows[fixed,8+channel]][:,None]*.5-table).argmin(axis=1)
        result[noisy&~mixed,8+channel]=0
    result[:,7]|=0x38
    return result


def optimize(samples,registers,node,*,noise_shares,work_parent=None,calibration_gain=None):
    samples=np.asarray(samples,float)
    rows=np.frombuffer(registers,np.uint8).reshape(-1,11).copy()
    shares=np.asarray(noise_shares,float);active=active_noise(rows)
    if len(samples)!=len(rows)*441 or shares.shape!=(len(rows),) or not np.isfinite(samples).all() or not np.isfinite(shares).all():
        raise ValueError('expected aligned PCM, registers and source noise evidence')
    if not active.any():return registers,dict(skipped='no audible noise',noise_ticks_before=0,noise_ticks_after=0)
    objective=Objective(samples);history=[]
    with tempfile.TemporaryDirectory(prefix='ay-necessary-noise-',dir=work_parent) as directory:
        root=Path(directory)
        def render(candidate):
            (root/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(),mtime=0))
            subprocess.run([str(node),str(HERE/'render_ym2149.js'),str(root/'registers.gz'),
                str(root/'audio.f32'),'50',str(root/'render.json')],check=True)
            audio=np.fromfile(root/'audio.f32','<f4').astype(float)
            return noise_colour.downsample(audio),float(abs(audio).max())
        baseline_audio,peak=render(rows)
        gain=calibration_gain if calibration_gain is not None else min(
            float(np.sqrt(np.mean(samples**2)/max(np.mean(baseline_audio**2),1e-20))),.95/max(peak,1e-12))
        baseline,with_noise=objective.measure(baseline_audio*gain,per_tick=True)
        tones=remove_noise(rows);pure_audio,_=render(tones)
        pure,without_noise=objective.measure(pure_audio*gain,per_tick=True)
        benefit=np.convolve(without_noise-with_noise,np.ones(3)/3,mode='same')
        # User preference: a residual alone cannot justify audible hiss.
        # Compare a small conservative family under explicit necessity gates.
        best=None;result=tones;selected=None
        for minimum_share,minimum_benefit in ((.2,.35),(.3,.35),(.2,.75),(.3,.75)):
            keep=active&(shares>=minimum_share)&(benefit>=minimum_benefit)
            candidate=tones.copy();candidate[keep]=rows[keep]
            audio,peak=render(candidate);measure=objective.measure(audio*gain)
            admissible=peak*gain<=.999
            proposal=dict(minimum_source_noise_share=minimum_share,minimum_rendered_benefit_db=minimum_benefit,
                noise_ticks=int(active_noise(candidate).sum()),metrics=measure,admissible=admissible)
            history.append(proposal)
            print(json.dumps(dict(stage='necessary_noise',share=minimum_share,benefit_db=minimum_benefit,
                noise_ticks=proposal['noise_ticks'],objective_db=measure['objective_db'])),flush=True)
            if admissible and (best is None or measure['objective_db']<best['objective_db']):
                best,result,selected=measure,candidate,proposal
        # All-noise-off is always physically realizable and meets the policy.
        if best is None or pure['objective_db']<best['objective_db']:
            best,result,selected=pure,tones,dict(minimum_source_noise_share=None,minimum_rendered_benefit_db=None,noise_ticks=0)
    info=dict(model='source_evidence_and_rendered_noise_necessity_v1',baseline=baseline,final=best,
        noise_ticks_before=int(active.sum()),noise_ticks_after=int(active_noise(result).sum()),
        removed_noise_ticks=int((active&~active_noise(result)).sum()),selected_policy=selected,
        fixed_model_gain=float(gain),source_evidence='tracker broadband power share',
        necessity='3-field mean of complete tone-only minus noise-enabled perceptual error',
        keep_generator_period_history=True,history=history,
        limitations='Conservative audibility policy requested after listening; ordinary spectral error can increase when weak residual noise is omitted. Not perfect source separation.')
    return result.tobytes(),info
