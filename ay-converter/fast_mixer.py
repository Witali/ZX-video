"""Analytic proposals, then 20 complete chip renders on the original AY grid.

Estimate broadband colour and mode-specific shared levels first. Check three
period scales and three neighbouring DAC levels in each noisy mode. The seed
and pure-tone streams remain independent full-render acceptance fallbacks.
"""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import time
import numpy as np
import music_profile
import mixer_fit
import noise_colour
import spectrogram

CORE=Path(mixer_fit.__file__).parent
SCALES=(.5,1.,2.)
DELTAS=(-1,0,1)
OPTIONS=[('seed',1.,0),('tone',1.,0)]+[(mode,scale,delta)
    for mode in ('noise','mixed') for scale in SCALES for delta in DELTAS]


def choose_path(cost):
    modes=np.array([o[0] for o in OPTIONS]); scales=np.array([o[1] for o in OPTIONS])
    deltas=np.array([o[2] for o in OPTIONS])
    transition=.3*(modes[:,None]!=modes[None,:])+.1*abs(np.log2(scales[:,None]/scales[None,:]))+.12*abs(deltas[:,None]-deltas[None,:])
    previous=cost[0].copy(); history=[]
    for row in cost[1:]:
        edges=previous[:,None]+transition; best=edges.argmin(axis=0); history.append(best)
        previous=row+edges[best,np.arange(len(OPTIONS))]
    path=np.empty(len(cost),int); path[-1]=previous.argmin()
    for t in range(len(cost)-2,-1,-1): path[t]=history[t][path[t+1]]
    return path


def proposals(samples,raw,volumes,shares,carriers):
    count=len(raw); rms=np.sqrt(np.mean(samples.reshape(-1,441)**2,axis=1))
    eligible=(rms>10**(-55/20)) & ((shares>.04)|(raw[:,6]>0))
    route=np.asarray(carriers,int).copy(); route[route<0]=volumes[route<0].argmin(axis=1)
    assert np.all((route>=0)&(route<=2))
    hz=np.fft.rfftfreq(4096,1/22050); hz=hz[(hz>=50)&(hz<=8000)]; useful=hz>=150
    # The same sinc colour prior used by the component tracker. Median power
    # rejects narrow tone peaks. Only a small fixed dictionary is evaluated.
    templates=abs(np.sinc(hz[useful][None,:]/(1773450/(16*np.arange(1,32)[:,None]))))
    templates/=np.maximum(np.linalg.norm(templates,axis=1,keepdims=True),1e-20)
    periods=np.empty(count,int)
    for a in range(0,count,128):
        b=min(a+128,count); power=noise_colour.spectra_at(samples,np.arange(a,b),2048)**2
        padded=np.pad(power,((0,0),(8,8)),mode='edge')
        floor=np.median(np.lib.stride_tricks.sliding_window_view(padded,17,axis=1),axis=-1)/.7
        broad=np.minimum(power,floor)
        periods[a:b]=(np.sqrt(broad[:,useful])@templates.T).argmax(axis=1)+1
    # Retain the already fully qualified colour fit when a carrier exists.
    periods[raw[:,6]>0]=raw[raw[:,6]>0,6]
    table=music_profile.chip_levels(); tone=table[volumes[np.arange(count),route]]
    noise=np.clip(.85*rms*np.sqrt(np.clip(shares,0,1))/max(float(np.percentile(rms,98)),1e-20),0,1)
    # Minimum of 4*(M/2-T)^2+(M/sqrt(2)-N)^2 is M=(4*T+sqrt(2)*N)/3.
    targets={'noise':noise,'mixed':np.clip((4*tone+np.sqrt(2)*noise)/3,0,1)}
    levels={mode:abs(target[:,None]-table).argmin(axis=1) for mode,target in targets.items()}
    return dict(eligible=eligible,carriers=route,periods=periods,levels=levels)


def rows_for(raw,tones,route,option):
    mode,scale,delta=option
    if mode=='seed': return raw.copy()
    result=tones.copy()
    if mode=='tone': return result
    ticks=np.flatnonzero(route['eligible']); carriers=route['carriers'][ticks]
    result[ticks,6]=np.clip(np.rint(route['periods'][ticks]*scale),1,31)
    result[ticks,7]&=(63^(1<<(carriers+3))).astype(np.uint8)
    if mode=='noise': result[ticks,7]|=(1<<carriers).astype(np.uint8)
    result[ticks,8+carriers]=np.clip(route['levels'][mode][ticks]+delta,1,15)
    return result


def optimize(samples,registers,node,*,tone_volumes,noise_shares,carriers,
             work_parent=None,cache_dir=None,workers=6):
    key = mixer_fit.cache_key(samples,registers,tone_volumes,noise_shares,carriers,node) if cache_dir is not None else None
    path = Path(cache_dir)/'analytic-20'/f'{key}.json.gz' if key else None
    if path and path.exists():
        cached = json.loads(gzip.decompress(path.read_bytes()))
        result = bytes.fromhex(cached['registers'])
        if cached.get('key') == key and len(result) == len(registers) and hashlib.sha256(result).hexdigest() == cached.get('registers_sha256'):
            return result, dict(cached['info'],cache_hit=True,cache_key=key)
    result, info = _optimize(samples,registers,node,tone_volumes=tone_volumes,
        noise_shares=noise_shares,carriers=carriers,work_parent=work_parent,workers=workers)
    if path:
        path.parent.mkdir(parents=True,exist_ok=True)
        info['cache_key'] = key
        data = dict(key=key,registers=result.hex(),registers_sha256=hashlib.sha256(result).hexdigest(),info=info)
        with tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as temporary:
            temporary.write(gzip.compress(json.dumps(data).encode(),mtime=0))
            temporary_path = Path(temporary.name)
        temporary_path.replace(path)
    return result,info


def _optimize(samples,registers,node,*,tone_volumes,noise_shares,carriers,
             work_parent=None,workers=6):
    started=time.perf_counter(); samples=np.asarray(samples,float)
    raw=np.frombuffer(registers,np.uint8).reshape(-1,11).copy(); count=len(raw)
    volumes=np.asarray(tone_volumes,np.uint8); shares=np.asarray(noise_shares,float)
    if not count or len(samples)!=count*441 or volumes.shape!=(count,3) or shares.shape!=(count,):
        raise ValueError('expected aligned complete 20-ms PCM and channel controls')
    if not np.isfinite(samples).all(): raise ValueError('nonfinite PCM')
    tones=raw.copy(); tones[:,6:8]=[0,0x38]; tones[:,8:]=volumes
    route=proposals(samples,raw,volumes,shares,carriers)
    ticks=np.arange(count); parts=[(a,min(a+128,count)) for a in range(0,count,128)]
    references=[[noise_colour.spectra_at(samples,ticks[a:b],size) for a,b in parts] for size in noise_colour.SIZES]
    floors=[max(max(float(p.max()) for p in ref)*.001,1e-15) for ref in references]
    with tempfile.TemporaryDirectory(prefix='ay-fast-mixer-',dir=work_parent) as directory:
        root=Path(directory)
        def render(rows,name):
            (root/f'{name}.gz').write_bytes(gzip.compress(rows.tobytes(),mtime=0))
            subprocess.run([str(node),str(CORE/'render_ym2149.js'),str(root/f'{name}.gz'),
                            str(root/f'{name}.f32'),'50',str(root/f'{name}.json')],check=True)
            audio=noise_colour.downsample(np.fromfile(root/f'{name}.f32','<f4').astype(float))
            (root/f'{name}.f32').unlink()
            assert len(audio)==len(samples) and np.isfinite(audio).all()
            return audio
        baseline=render(raw,'seed'); pure=render(tones,'tone')
        gain=float(np.sqrt(np.mean(samples**2)/max(np.mean(baseline**2),1e-20)))
        def score(audio):
            audio=audio*gain; result=np.empty(count)
            for part,(a,b) in enumerate(parts):
                errors=[]
                for size,ref,floor in zip(noise_colour.SIZES,references,floors):
                    wanted=ref[part]; observed=noise_colour.spectra_at(audio,ticks[a:b],size)
                    support=(wanted>floor)|(observed>floor)
                    error=abs(20*np.log10(np.maximum(wanted,floor)/np.maximum(observed,floor)))
                    errors.append((error*support).sum(axis=1)/np.maximum(support.sum(axis=1),1))
                result[a:b]=np.mean(errors,axis=0)
            return result
        cost=np.empty((count,len(OPTIONS))); cost[:,0]=score(baseline); cost[:,1]=score(pure)
        def evaluate(index):
            option=OPTIONS[index]; audio=render(rows_for(raw,tones,route,option),f'candidate-{index}')
            column=score(audio)
            if option[0]=='mixed': column[(volumes[np.arange(count),route['carriers']]==0)&route['eligible']]=1e6
            cost[:,index]=column
            print(json.dumps(dict(stage='fast_candidate',complete=index,option=option)),flush=True)
        with ThreadPoolExecutor(max_workers=workers) as pool: list(pool.map(evaluate,range(2,len(OPTIONS))))
        assert np.isfinite(cost).all()
        selected=choose_path(cost); proposal=raw.copy()
        for index,option in enumerate(OPTIONS):
            mask=selected==index
            if mask.any(): proposal[mask]=rows_for(raw,tones,route,option)[mask]
        proposed=render(proposal,'proposal')
        reference=spectrogram.features(samples)
        measures={name:spectrogram.compare(reference,spectrogram.features(audio))
                  for name,audio in [('seed',baseline),('tone',pure),('automatic',proposed)]}
        errors={name:float(np.mean([m['log_magnitude_mae_db'] for m in metrics.values()])) for name,metrics in measures.items()}
        decision=min(errors,key=errors.get); result={'seed':raw,'tone':tones,'automatic':proposal}[decision]
    info=dict(model='analytic_proposals_and_20_chip_candidates_v1',candidate_count=20,
        proposal_noise_period_scales=list(SCALES),shared_volume_deltas=list(DELTAS),
        analytic_shared_level='noise N; mixed (4*T+sqrt(2)*N)/3, quantized to chip DAC',
        update_rate_hz=50,quantum_ms=20,eligible_ticks=int(route['eligible'].sum()),
        final_decision=decision,final_multiresolution_log_mae_db=errors,final_metrics=measures,
        modes_before=mixer_fit.mode_counts(raw),modes_after=mixer_fit.mode_counts(result),
        changed_ticks=int(np.any(raw!=result,axis=1).sum()),native_instruction_delta_tstates=0,
        tone_periods_changed=0,component_channel_migrations=0,cache_hit=False,
        elapsed_seconds=time.perf_counter()-started,
        limitations='Analytic shortlist can miss the 374-candidate optimum; final unpooled full-render fallback guards the seed. No perceptual fidelity claim.',
        states=[dict(tick=int(t),candidate=OPTIONS[int(c)],carrier=int(route['carriers'][t]),
            candidate_error_db=float(cost[t,c]),mixer=int(result[t,7]),noise_period=int(result[t,6]),
            volumes=result[t,8:].tolist()) for t,c in enumerate(selected)])
    return result.tobytes(),info
