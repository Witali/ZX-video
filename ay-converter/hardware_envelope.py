"""Fit one shared running hardware envelope against complete chip feedback.

AY12 carries R11/R12 plus R13 restart actions. 255 is an omitted R13 write.
Envelope-only oscillator proposals use the chip's Boolean gates held high;
they are nonlinear DAC ramps, not ideal triangle waves. Preserve all 50-Hz
states while allowing the chip envelope to run between them.
"""
import gzip
import json
from pathlib import Path
import subprocess
import tempfile
import numpy as np
import noise_colour
from simulation_refine import Objective

HERE = Path(__file__).resolve().parent
CLOCK = 1773450


def extend(registers):
    raw=np.frombuffer(registers,np.uint8).reshape(-1,11)
    rows=np.zeros((len(raw),14),np.uint8);rows[:,:11]=raw;rows[:,13]=255
    return rows


def ramp_blocks(rows, scale=1.):
    """Fit linear envelope-counter ramps to tracked logarithmic DAC levels.

    The YM model has 32 steps at clock/(8*period). Rising ramps may start near
    rest; falling ramps must start near the top because the chip cannot load
    an arbitrary envelope level. Stop routing at the segment end. One global
    generator forbids overlapping independently shaped voices.
    """
    choices=[];n=len(rows)
    for channel in range(3):
        values=rows[:,8+channel].astype(int)
        active=(values>0)&((rows[:,7]&(1<<channel))==0)
        start=0
        while start<n-2:
            if not active[start]: start+=1;continue
            direction=1 if values[start]<=6 else -1 if values[start]>=14 else 0
            if not direction: start+=1;continue
            end=start+1
            while end<min(n,start+16) and active[end] and direction*(values[end]-values[end-1])>=0:
                end+=1
            if end-start<3 or abs(values[end-1]-values[start])<3:
                start+=1;continue
            indices=2*values[start:end]+1
            slope=float(np.polyfit(np.arange(len(indices))+.5,indices,1)[0])
            if direction*slope<=.3: start+=1;continue
            period=int(np.clip(round(.02*CLOCK/(8*abs(slope))*scale),1,65535))
            shape=13 if direction>0 else 9
            choices.append(dict(start=start,end=end,channel=channel,period=period,shape=shape,
                priority=float(abs(indices[-1]-indices[0])*np.max(values[start:end]))))
            start=end
    selected=[];occupied=np.zeros(n,bool)
    for block in sorted(choices,key=lambda b:b['priority'],reverse=True):
        if not occupied[block['start']:block['end']].any():
            selected.append(block);occupied[block['start']:block['end']]=True
    return sorted(selected,key=lambda b:b['start'])


def oscillator_blocks(rows, shape):
    """Estimate envelope-wave periods from the tracked tonal fundamental.

    A full saw ramp has 32 YM steps (256 chip clocks per period); triangle
    has two ramps (512). The period integer grid can be much coarser than
    the ordinary tone generator. Full rendering decides whether it is useful.
    """
    blocks=[];n=len(rows);start=0
    while start<n:
        audible=[c for c in range(3) if rows[start,8+c]>=12 and not rows[start,7]&(1<<c)]
        if not audible:start+=1;continue
        channel=max(audible,key=lambda c:int(rows[start,8+c]))
        tone=int(rows[start,channel*2])+(int(rows[start,channel*2+1])<<8)
        period=int(np.clip(round(tone/(32 if shape in (10,14) else 16)),1,65535))
        end=start+1
        while end<n and end<start+25 and rows[end,8+channel]>=12 and not rows[end,7]&(1<<channel):
            current=int(rows[end,channel*2])+(int(rows[end,channel*2+1])<<8)
            if round(current/(32 if shape in (10,14) else 16))!=period:break
            end+=1
        if end-start>=3:
            blocks.append(dict(start=start,end=end,channel=channel,period=period,shape=shape,
                oscillator=True,priority=1.))
        start=end
    return blocks


def apply_blocks(base, blocks):
    result=base.copy()
    for block in blocks:
        start,end,channel=block['start'],block['end'],block['channel']
        result[start:end,8+channel]=16
        result[start:end,11]=block['period']&255;result[start:end,12]=block['period']>>8
        result[start,13]=block['shape']
        if block.get('oscillator'):
            result[start:end,7]|=(1<<channel)|(1<<(channel+3))
    # Period writes after a segment keep its last value. They do not restart
    # the envelope; only explicitly encoded shape writes can do that.
    period=0
    for row in result:
        if row[11] or row[12]:period=int(row[11])+(int(row[12])<<8)
        row[11]=period&255;row[12]=period>>8
    return result


def optimize(samples,registers,node,*,work_parent=None,calibration_gain=None):
    samples=np.asarray(samples,float);base=extend(registers)
    if len(samples)!=len(base)*441 or not np.isfinite(samples).all():raise ValueError('expected aligned PCM')
    if not samples.any():return registers,dict(skipped='silent source',selected=False,register_bytes=11)
    objective=Objective(samples);history=[];evaluated=0
    with tempfile.TemporaryDirectory(prefix='ay-envelope-',dir=work_parent) as directory:
        root=Path(directory)
        def render(rows):
            nonlocal evaluated
            evaluated+=1
            (root/'registers.gz').write_bytes(gzip.compress(rows.tobytes(),mtime=0))
            subprocess.run([str(node),str(HERE/'render_ym2149.js'),str(root/'registers.gz'),
                str(root/'audio.f32'),'50',str(root/'render.json'),'14'],check=True)
            audio=np.fromfile(root/'audio.f32','<f4').astype(float)
            return noise_colour.downsample(audio),float(abs(audio).max())
        audio,peak=render(base)
        gain=calibration_gain if calibration_gain is not None else min(
            float(np.sqrt(np.mean(samples**2)/max(np.mean(audio**2),1e-20))),.95/max(peak,1e-12))
        baseline,baseline_local=objective.measure(audio*gain,per_tick=True)
        best=baseline;result=base;winner='fixed';best_blocks=[]
        proposals=[(f'ramps-{scale}',ramp_blocks(base,scale)) for scale in (.8,1.,1.2)]
        proposals += [(f'wave-{shape}',oscillator_blocks(base,shape)) for shape in (8,12,14)]
        for name,blocks in proposals:
            if not blocks:continue
            candidate=apply_blocks(base,blocks);observed,peak=render(candidate)
            measure,local=objective.measure(observed*gain,per_tick=True)
            # Evaluate complete segments with 8192-window influence on each
            # boundary; never splice half of a running envelope ramp.
            kept=[block for block in blocks if local[max(0,block['start']-9):min(len(base),block['end']+9)].mean()
                < baseline_local[max(0,block['start']-9):min(len(base),block['end']+9)].mean()-1e-4]
            if not kept:
                history.append(dict(proposal=name,proposed_blocks=len(blocks),kept_blocks=0,metrics=measure));continue
            if len(kept)!=len(blocks):
                candidate=apply_blocks(base,kept);observed,peak=render(candidate)
                measure=objective.measure(observed*gain)
            admissible=peak*gain<=.999
            improved=admissible and measure['objective_db']<best['objective_db']-1e-6
            history.append(dict(proposal=name,proposed_blocks=len(blocks),kept_blocks=len(kept),
                peak=peak*gain,admissible=admissible,improved_current_best=improved,metrics=measure))
            print(json.dumps(dict(stage='hardware_envelope',proposal=name,blocks=len(kept),
                objective_db=measure['objective_db'],accepted=improved)),flush=True)
            if improved:result,best,winner,best_blocks=candidate,measure,name,kept
        selected=winner!='fixed'
    import chip_model
    info=dict(model='shared_running_hardware_envelope_feedback_v1',selected=selected,
        target_chip=chip_model.current(),envelope_level_codes=32 if chip_model.current()=='YM2149' else 16,
        register_bytes=14 if selected else 11,packed_state_bytes=12 if selected else 9,
        fixed_model_gain=float(gain),baseline=baseline,final=best,final_decision=winner,
        candidates_rendered=evaluated,history=history,blocks=best_blocks,
        envelope_channel_ticks=int(np.count_nonzero(result[:,8:11]&16)) if selected else 0,
        shape_restarts=int(np.count_nonzero(result[:,13]!=255)) if selected else 0,
        shared_generators=1,phase_continues_between_fields=True,
        no_per_field_restart=True,shape_write_sentinel=255,
    limitations='One shared nonlinear DAC envelope: 16 AY or 32 YM level codes. Bounded proposals and coarse frequency grid; not an ideal triangle or independent channel envelopes.')
    if selected:
        refined,ramps=add_ramps(samples,registers,result.tobytes(),node,work_parent=work_parent,calibration_gain=gain)
        info['ramp_followup']=ramps
        if ramps['selected']:
            result=np.frombuffer(refined,np.uint8).reshape(-1,14)
            info.update(final=ramps['final'],final_decision=winner+' + '+ramps['final_decision'],
                blocks=best_blocks+ramps['blocks'],
                envelope_channel_ticks=int(np.count_nonzero(result[:,8:11]&16)),
                shape_restarts=int(np.count_nonzero(result[:,13]!=255)))
    return (result.tobytes() if selected else registers),info


def add_ramps(samples,fixed_registers,running_registers,node,*,work_parent=None,calibration_gain=1.):
    """Add disjoint slow amplitude ramps to an accepted running-wave plan.

    There remains exactly one envelope generator: skip every occupied interval.
    Fit full segments against the existing plan and re-render the combined
    register history. This permits useful timbre shaping and attack/release
    smoothing in different portions of one recording.
    """
    base=np.frombuffer(running_registers,np.uint8).reshape(-1,14).copy()
    fixed=extend(fixed_registers);objective=Objective(samples)
    occupied=np.any(base[:,8:11]&16,axis=1)
    history=[];best_blocks=[];winner='held plan';result=base
    with tempfile.TemporaryDirectory(prefix='ay-envelope-ramps-',dir=work_parent) as directory:
        root=Path(directory)
        def render(candidate):
            (root/'registers.gz').write_bytes(gzip.compress(candidate.tobytes(),mtime=0))
            subprocess.run([str(node),str(HERE/'render_ym2149.js'),str(root/'registers.gz'),
                str(root/'audio.f32'),'50',str(root/'render.json'),'14'],check=True)
            audio=np.fromfile(root/'audio.f32','<f4').astype(float)
            return noise_colour.downsample(audio)*calibration_gain,float(abs(audio).max())*calibration_gain
        audio,_=render(base);baseline,baseline_local=objective.measure(audio,per_tick=True);best=baseline
        for scale in (.8,1.,1.2):
            blocks=[b for b in ramp_blocks(fixed,scale) if not occupied[b['start']:b['end']].any()]
            if not blocks:continue
            candidate=apply_blocks(base,blocks);audio,peak=render(candidate)
            measure,local=objective.measure(audio,per_tick=True)
            kept=[b for b in blocks if local[max(0,b['start']-9):min(len(base),b['end']+9)].mean()
                < baseline_local[max(0,b['start']-9):min(len(base),b['end']+9)].mean()-1e-4]
            if not kept:continue
            if len(kept)!=len(blocks):
                candidate=apply_blocks(base,kept);audio,peak=render(candidate);measure=objective.measure(audio)
            improved=peak<=.999 and measure['objective_db']<best['objective_db']-1e-6
            name=f'disjoint ramps-{scale}'
            history.append(dict(proposal=name,blocks=len(kept),metrics=measure,improved_current_best=improved,peak=peak))
            print(json.dumps(dict(stage='envelope_ramp_followup',proposal=name,blocks=len(kept),
                objective_db=measure['objective_db'],accepted=improved)),flush=True)
            if improved:best,result,winner,best_blocks=measure,candidate,name,kept
    return result.tobytes(),dict(selected=winner!='held plan',baseline=baseline,final=best,
        final_decision=winner,history=history,blocks=best_blocks,one_shared_generator=True)
