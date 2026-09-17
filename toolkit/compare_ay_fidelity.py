"""Independent audio proxies and level-matched listening excerpts.

The comparison uses a longer FFT and semitone energy bands, not the harmonic
dictionary used by the encoder. These metrics are not a subjective listening
score or ground-truth note transcription.
"""
import argparse
import json
from pathlib import Path
import shutil
import wave

import numpy as np

import ay_fidelity as ay
import build_fast_sparse_trd as codec
import build_long_video_trd as video


def read_frames(build):
    screens, states, fps = codec.decode_compact_build(build/'VIDEO_full.C.bin')
    frames = [video.AyFrame.deserialize(s) for s in states]
    return screens, frames, fps


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


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input-video',type=Path,required=True)
    p.add_argument('--baseline-build',type=Path,required=True)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    p.add_argument('--excerpt-start',type=float,default=60)
    p.add_argument('--excerpt-duration',type=float,default=24)
    args=p.parse_args()
    if not args.ffmpeg:p.error('ffmpeg is required')
    old_screens,old,fps=read_frames(args.baseline_build)
    screens,new,new_fps=read_frames(args.build)
    assert screens==old_screens and fps==new_fps,'video must be byte-identical'
    rate=22050;duration=len(new)/fps
    metadata=json.loads((args.build/'build_metadata.json').read_text(encoding='utf-8'))
    source_start=metadata.get('retuned_source',{}).get('start_seconds',metadata.get('source',{}).get('start_seconds',0))
    original=video.decode_analysis_audio(args.ffmpeg,args.input_video,source_start,duration,rate,True)
    versions={'original':original,'before':ay.render(old,fps,rate),'after':ay.render(new,fps,rate)}
    reference=features(original,rate,fps,len(new))
    report=dict(scope='front-channel music; independent 8192-sample FFT semitone/chroma energy and RMS; no listening or true-note score',
                frames=len(new),video_identical=True,update_rate_hz=fps,source_start_seconds=source_start,
                preview_model='band-limited tones, continuous 17-bit LFSR noise with 4x sample averaging, nominal AY 3 dB volume steps; approximate synthesis',
                metrics={name:compare(reference,features(samples,rate,fps,len(new)))
                         for name,samples in versions.items() if name!='original'})
    # User decision, 2026-09-17: attack F1 is best effort, not a 95% gate.
    criteria=('chroma_cosine','loudness_correlation')
    report['target']=dict(threshold=.95,criteria=list(criteria),
                          passed=all(report['metrics']['after'][key]>=.95 for key in criteria),
                          onset_tolerance_seconds=1/fps,
                          rhythm=dict(metric='rhythm_onset_f1',required=False,
                                      aspirational_range=[.90,.92],
                                      measured=report['metrics']['after']['rhythm_onset_f1']),
                          meaning='engineering proxies; not 95% perceptual fidelity or true-note accuracy')
    args.output.mkdir(parents=True,exist_ok=True)
    lo=round(args.excerpt_start*rate);hi=round((args.excerpt_start+args.excerpt_duration)*rate)
    excerpts={name:samples[lo:hi] for name,samples in versions.items()}
    rms={name:float(np.sqrt(np.mean(samples*samples))) for name,samples in excerpts.items()}
    target=min(.10,*(.9*rms[name]/max(float(np.max(np.abs(samples))),1e-12)
                     for name,samples in excerpts.items()))
    for name,samples in excerpts.items():
        write_wav(args.output/f'{name}.wav',samples*target/max(rms[name],1e-12),rate)
    report['excerpt']=dict(start_seconds=args.excerpt_start,duration_seconds=args.excerpt_duration,
                           common_rms=target,note='All three listening excerpts have equal RMS loudness; disk levels are unchanged.')
    (args.output/'comparison.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
