"""Peak calibration and bounded, smooth offline dynamic-range compression."""
import numpy as np


def spread(samples):
    rms=np.sqrt(np.mean(samples.reshape(-1,441)**2,axis=1))
    active=rms>10**(-55/20)
    db=20*np.log10(np.maximum(rms[active],1e-12))
    return dict(rms=float(np.sqrt(np.mean(samples**2))),peak=float(abs(samples).max()),
        active_ticks=int(active.sum()),p10_dbfs=float(np.percentile(db,10)) if len(db) else -240.,
        p90_dbfs=float(np.percentile(db,90)) if len(db) else -240.,
        p90_minus_p10_db=float(np.percentile(db,90)-np.percentile(db,10)) if len(db) else 0.)


def process(samples,start_tick=0,ticks=None,*,dynamics='compact'):
    if dynamics not in ('compact','original'):raise ValueError('dynamics must be compact or original')
    samples=np.asarray(samples,float)
    count=(len(samples)+440)//441;samples=np.pad(samples,(0,count*441-len(samples)))
    ticks=count-start_tick if ticks is None else ticks
    first=start_tick*441;last=(start_tick+ticks)*441
    if ticks<1 or first<0 or last>len(samples) or not np.isfinite(samples).all():raise ValueError('invalid PCM interval')
    peak=float(abs(samples[first:last]).max());initial_gain=10**(-1/20)/peak if peak else 1.
    normalized=samples*initial_gain;result=normalized.copy();curve=np.zeros(count)
    if dynamics=='compact' and peak:
        rms=np.sqrt(np.mean(normalized.reshape(-1,441)**2,axis=1))
        level=20*np.log10(np.maximum(rms,1e-12))
        wanted=np.clip((-24-level)*(1-1/2.5),-18,9)
        # Leave genuine silence untouched; taper upward gain at the noise floor.
        wanted=np.where(wanted>0,wanted*np.clip((level+65)/10,0,1),wanted)
        attack=np.exp(-.02/.01);release=np.exp(-.02/.15)
        for i in range(count):
            previous=curve[i-1] if i else wanted[0]
            alpha=attack if wanted[i]<previous else release
            curve[i]=alpha*previous+(1-alpha)*wanted[i]
        # Offline lookahead smooths upward transitions before a quiet passage.
        # It changes gain only; no source samples, attacks or timestamps move.
        future=curve.copy()
        for i in range(count-2,-1,-1):future[i]=.75*future[i]+.25*future[i+1]
        centres=(np.arange(count)+.5)*441
        gain_db=np.interp(np.arange(len(samples)),centres,future)
        result=normalized*10**(gain_db/20)
    after_peak=float(abs(result[first:last]).max())
    makeup=10**(-1/20)/after_peak if after_peak else 1.
    result*=makeup
    info=dict(method='selected-interval sample-peak calibration with bounded smooth dynamics',
        target_peak_dbfs=-1.,source_peak=peak,gain_linear=initial_gain,
        normalized_peak=float(abs(result[first:last]).max()),applied_before_analysis=True,
        same_gain_on_analysis_context=True,dynamics=dynamics,dynamics_preserved=dynamics=='original',
        compressor=dict(ratio=2.5,threshold_dbfs=-24,maximum_upward_db=9,maximum_downward_db=18,
            attack_ms=10,release_ms=150,offline_future_smoothing=True,no_time_shift=True),
        makeup_gain_linear=makeup,makeup_gain_db=float(20*np.log10(makeup)),
        source_levels=spread(samples[first:last]),processed_levels=spread(result[first:last]),
        clipping_samples=int(np.count_nonzero(abs(result[first:last])>1)),true_peak_or_lufs_normalization=False)
    return result,info
