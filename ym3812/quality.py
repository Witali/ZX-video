"""Independent spectral/rhythm proxies and WAV output; not listening scores."""
import wave
import numpy as np
import ay_fidelity as ay


def features(samples, rate, fps, count):
    magnitude, rms = ay.spectra(samples, rate, fps, count, window_size=8192)
    frequency = np.fft.rfftfreq(16384, 1/rate)
    pitches = 69+12*np.log2(np.maximum(frequency, 1e-9)/440)
    bands = np.arange(28, 109)
    weights = np.maximum(0, 1-np.abs(pitches[:, None]-bands[None, :]))
    energy = magnitude*magnitude @ weights
    chroma = np.zeros((count, 12))
    for i,note in enumerate(bands): chroma[:, note%12] += energy[:, i]
    return np.sqrt(energy), np.sqrt(chroma), rms


def compare(reference, candidate):
    mask = reference[2] > 10**(-55/20)
    def cosine(a, b):
        return np.sum(a*b, axis=1)/np.maximum(np.linalg.norm(a,axis=1)*np.linalg.norm(b,axis=1), 1e-15)
    def correlation(a, b):
        if np.sum(mask)<2 or np.std(a[mask])<1e-10 or np.std(b[mask])<1e-10: return 0.0
        return float(np.corrcoef(a[mask], b[mask])[0,1])
    ref_db = 20*np.log10(np.maximum(reference[2], 1e-6))
    out_db = 20*np.log10(np.maximum(candidate[2], 1e-6))
    def mean_cosine(a,b): return float(np.mean(cosine(a,b)[mask])) if np.any(mask) else 0.0
    return dict(semitone_spectral_cosine=mean_cosine(reference[0],candidate[0]),
                chroma_cosine=mean_cosine(reference[1],candidate[1]),
                loudness_correlation=correlation(ref_db,out_db),
                rhythm_onset_f1=match_onsets(onsets(reference[0]),onsets(candidate[0]))['f1'],
                onsets=match_onsets(onsets(reference[0]),onsets(candidate[0])),
                evaluated_frames=int(np.sum(mask)))


def onsets(bands):
    """Positive spectral flux peaks; fixed detector for both recordings."""
    scale=max(float(np.percentile(np.max(bands,axis=1),95))*.05,1e-12)
    flux=np.maximum(0,np.diff(np.log1p(bands/scale),axis=0)).mean(axis=1)
    flux=np.r_[0,flux]
    threshold=np.median(flux)+1.5*np.median(np.abs(flux-np.median(flux)))
    result=[]
    for i in range(1,len(flux)-1):
        if flux[i]>max(threshold,.02) and flux[i]>flux[i-1] and flux[i]>=flux[i+1]:
            if not result or i-result[-1]>=2: result.append(i)
    return result


def match_onsets(reference, candidate, tolerance=1):
    """One-to-one ordered matching within one update (120 ms at 25/3 Hz)."""
    i=j=matched=0
    while i<len(reference) and j<len(candidate):
        if abs(reference[i]-candidate[j])<=tolerance:
            matched+=1;i+=1;j+=1
        elif reference[i]<candidate[j]:i+=1
        else:j+=1
    return dict(reference=len(reference),candidate=len(candidate),matched=matched,
                precision=matched/max(1,len(candidate)),recall=matched/max(1,len(reference)),
                f1=2*matched/max(1,len(reference)+len(candidate)))


def write_wav(path, samples, rate):
    pcm=np.clip(np.rint(samples*32767),-32768,32767).astype('<i2')
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(rate)
        stream.writeframes(pcm.tobytes())
