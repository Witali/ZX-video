"""One speech-specific AY50 candidate: F0 plus fitted harmonic square waves."""
from __future__ import annotations

import numpy as np
from probe_lpc2 import AyFrame

CLOCK=1773450


def fit_weights(basis,target,floor=0.):
    """Small nonnegative least-squares fit with an audible pitch anchor."""
    gram=basis@basis.T
    corr=basis@target
    weights=np.zeros(len(basis))
    for _ in range(24):
        for j in range(len(basis)):
            value=(corr[j]-gram[j]@weights+gram[j,j]*weights[j])/max(gram[j,j],1e-20)
            weights[j]=max(floor if j==0 else 0.,value)
    return weights,float(np.sum((weights@basis-target)**2))


def square_power(periods,frequencies,window_size=256,rate=8000):
    """Hann-broadened odd-harmonic power at actual integer tone periods."""
    basis=[]
    for period in periods:
        fundamental=CLOCK/(16*int(period)); row=np.zeros(len(frequencies))
        for harmonic in range(1,int(3900/fundamental)+1,2):
            x=(frequencies-harmonic*fundamental)*window_size/rate
            peak=np.sinc(x)+.5*np.sinc(x-1)+.5*np.sinc(x+1)
            row+=(peak/harmonic)**2
        basis.append(row)
    return np.asarray(basis)


def encode(records,samples,levels,rate=8000,hop=160):
    if len(samples)!=len(records)*hop or not np.isfinite(samples).all():
        raise ValueError('complete finite PCM and aligned LPC frames required')
    frequencies=np.fft.rfftfreq(512,1/rate)
    useful=(frequencies>=70)&(frequencies<=3900)
    frequency=frequencies[useful]
    # Moderate emphasis keeps upper formants in the fitting objective.
    emphasis=(frequency/500)**.35
    rms=np.sqrt(np.mean(samples.reshape(-1,hop)**2,axis=1))
    peak=max(float(np.percentile(rms,98)),1e-12)
    window=np.hanning(256)
    frames=[]; details=[]
    for i,record in enumerate(records):
        level=min(.9,.85*rms[i]/peak)
        pitch=float(record['pitch_hz'])
        if record['energy']==0 or level<.002:
            frames.append(AyFrame((1,1,1),(0,0,0),0)); details.append(dict(kind='silence'))
            continue
        start=i*hop+hop//2-128
        segment=np.zeros(256); lo=max(0,start); hi=min(len(samples),start+256)
        segment[lo-start:hi-start]=samples[lo:hi]
        power=abs(np.fft.rfft(segment*window,512))[useful]**2
        if record['mode'] not in (1,2) or not 70<=pitch<=500:
            # Preserve consonant timing; the one shared noise source has no
            # resonant filter. Fit its period rather than its centroid alone.
            noise=np.arange(1,32)
            templates=np.sinc(frequency[None,:]/(CLOCK/(16*noise[:,None])))**2
            target=np.sqrt(power)*emphasis
            templates=np.sqrt(templates)*emphasis
            score=templates@target/np.maximum(np.linalg.norm(templates,axis=1),1e-12)
            period=int(noise[np.argmax(score)])
            v=int(np.argmin(abs(levels-level)))
            frames.append(AyFrame((1,1,1),(0,v,0),period))
            details.append(dict(kind='noise',mode=record['mode'],noise_period=period))
            continue
        harmonics=np.arange(1,min(24,int(3500/pitch))+1)
        periods=np.clip(np.rint(CLOCK/(16*pitch*harmonics)),1,4095).astype(int)
        basis=square_power(periods,frequency)*emphasis
        target=power*emphasis
        target/=max(float(np.linalg.norm(target)),1e-20)
        # Preserve the tracked fundamental, but let two harmonic generators
        # fill spectral regions that its fixed odd-partial series misses.
        floor=.01*float(target.sum())/max(float(basis[0].sum()),1e-20)
        selected=[0]
        weights,_=fit_weights(basis[selected],target,floor)
        for _ in range(2):
            options=[]
            for j in range(1,len(periods)):
                if j in selected: continue
                trial=selected+[j]; w,loss=fit_weights(basis[trial],target,floor)
                options.append((loss,j,w))
            _,chosen,weights=min(options,key=lambda row:row[0]); selected.append(chosen)
        weights,_=fit_weights(basis[selected],target,floor)
        amplitudes=np.sqrt(weights)
        amplitudes*=level/max(float(np.linalg.norm(amplitudes)),1e-20)
        volumes=np.argmin(abs(levels[None,:]-amplitudes[:,None]),axis=1)
        volumes[0]=max(1,volumes[0])
        chosen=periods[selected]
        frames.append(AyFrame(tuple(map(int,chosen)),tuple(map(int,volumes)),0))
        details.append(dict(kind='voiced',mode=record['mode'],lpc_pitch_hz=pitch,
            actual_fundamental_hz=CLOCK/(16*int(chosen[0])),harmonic_indices=harmonics[selected].tolist(),
            periods=chosen.tolist(),volumes=volumes.tolist()))
    return frames,details
