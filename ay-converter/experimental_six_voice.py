"""Experimental six-voice PSG with square, triangle and sine oscillators.

This is a hypothetical synthesizer, not an AY register stream. Frequency
periods, fixed-volume DAC codes and the 50-Hz control grid retain AY limits.
The six oscillator phases and one shared 17-bit noise source run continuously.
Only these controls generate output; source PCM supplies analysis targets.
The CLI uses an explicit hypothetical 4-ms transition envelope and 8-kHz
output bandwidth, with control-only DC compensation in a balanced mixer.
The original stepped model remains available for comparison.
"""
from __future__ import annotations
import argparse
from functools import lru_cache
import gzip
import hashlib
from itertools import permutations
import json
from pathlib import Path
import shutil
import time
import wave
import numpy as np
import ay_fidelity
import music_profile
import noise_colour
import psychoacoustic
import quality
from simulation_refine import Objective, spectra, tick_rms
from support import save

CLOCK=ay_fidelity.AY_CLOCK
RATE=22050;OUTPUT_RATE=44100;OVERSAMPLE=4
SHAPES=('square','triangle','sine')
VARIANCE=np.array([.25,1/12,1/8])  # AC variance of unit unipolar waves.
ORDERS=np.array(list(permutations(range(6))))
LEVELS=music_profile.chip_levels('AY')
SIZE=2048


def read_reference(path):
    """Read already prepared mono PCM16; never compress the reference twice."""
    with wave.open(str(path),'rb') as stream:
        if stream.getframerate()!=RATE or stream.getnchannels()!=1 or stream.getsampwidth()!=2:
            raise ValueError('reference must be prepared mono 22050-Hz PCM16 WAV')
        samples=np.frombuffer(stream.readframes(stream.getnframes()),'<i2').astype(float)/32768
    if not len(samples) or len(samples)%441:raise ValueError('reference must contain whole 20-ms fields')
    return samples


def dictionary(window_size=SIZE):
    """Sparse Hann spectra for every useful integer period and all shapes.

    The 17-bin main-lobe neighbourhood is evaluated analytically. Square odd
    harmonics have 1/h amplitudes, triangle 1/h^2, and sine has one partial.
    Templates approximate magnitude addition; final decisions use full audio.
    """
    if window_size not in (512,1024,1536,2048):raise ValueError('unsupported analysis window')
    hz=np.fft.rfftfreq(window_size*2,1/RATE)
    useful=(hz>=50)&(hz<=8000);bins=np.flatnonzero(useful)
    periods=np.arange(max(1,int(np.ceil(CLOCK/(16*8000)))),int(CLOCK/(16*45))+1)
    frequency=CLOCK/(16*periods)
    basis=np.zeros((3,len(periods),len(bins)),np.float32)
    offsets=np.arange(-8,9)
    for harmonic in range(1,179,2):
        centre=frequency*harmonic
        selected=np.flatnonzero(centre<8050)
        if not len(selected):break
        index=np.rint(centre[selected]/hz[1]).astype(int)[:,None]+offsets
        x=(index*hz[1]-centre[selected,None])*window_size/RATE
        kernel=abs(np.sinc(x)+.5*np.sinc(x-1)+.5*np.sinc(x+1))
        valid=(index>=bins[0])&(index<=bins[-1]);local=index-bins[0]
        rows=np.broadcast_to(selected[:,None],index.shape)[valid]
        columns=local[valid];values=kernel[valid]
        np.add.at(basis[0],(rows,columns),values*2/(np.pi*harmonic))
        np.add.at(basis[1],(rows,columns),values*4/(np.pi**2*harmonic**2))
        if harmonic==1:np.add.at(basis[2],(rows,columns),values*.5)
    noise=np.array([abs(np.sinc(hz[useful]/(CLOCK/(16*p)))) for p in range(1,32)])
    noise*=.5*np.sqrt(6/window_size)*np.sqrt(len(bins))/np.linalg.norm(noise,axis=1)[:,None]
    return periods,basis,noise.astype(np.float32),hz,useful


def noise_share(samples,ticks):
    short=spectra(samples,np.arange(ticks),512)
    hz=np.fft.rfftfreq(1024,1/RATE);band=short[:,(hz>=200)&(hz<=8000)]**2
    flatness=np.exp(np.log(np.maximum(band,1e-20)).mean(axis=1))/np.maximum(band.mean(axis=1),1e-20)
    return flatness


def fit(samples,templates,*,square_only=False,spectral_weight_exponent=0.,band_peak_count=0):
    """Sparse magnitude fit, optionally balancing strong and weak partials.

    An inverse-magnitude weight approximates root/log-spectrum distances
    without treating almost-zero FFT bins as infinitely important. The floor
    is source-only, 2.5% of each field's peak; no candidate can mask its error.
    Per-band proposals prevent the loud bass from occupying the whole global
    peak budget. Neither option changes the six-voice renderer or its clocks.
    Zero exponent/band peaks retain the original fitter.
    """
    if not np.isfinite(spectral_weight_exponent) or not 0<=spectral_weight_exponent<=2:
        raise ValueError('spectral weight exponent must be within 0..2')
    if not isinstance(band_peak_count,(int,np.integer)) or not 0<=band_peak_count<=8:
        raise ValueError('band peak count must be within 0..8')
    periods,basis,noise,hz,useful=templates;count=len(samples)//441
    analysis_size=len(hz)-1
    magnitude=np.empty((count,int(useful.sum())),np.float32)
    for start in range(0,count,128):
        end=min(count,start+128);magnitude[start:end]=spectra(samples,np.arange(start,end),analysis_size)[:,useful]
    masking=psychoacoustic.thresholds(magnitude,hz[useful])
    weights=psychoacoustic.error_weights(magnitude,magnitude,masking)
    if spectral_weight_exponent:
        peak=np.maximum(magnitude.max(axis=1),1e-12)
        relative=np.maximum(magnitude,peak[:,None]*.025)/peak[:,None]
        weights*=relative**(-spectral_weight_exponent)
    flatness=noise_share(samples,count);rms=tick_rms(samples)
    p=np.full((count,6),4095,np.uint16);s=np.zeros((count,6),np.uint8)
    modes=s.copy();amplitude=np.zeros((count,6));npd=np.full(count,16,np.uint8)
    preceding=np.full(6,4095);preceding_shape=np.zeros(6,int)
    allowed=(0,) if square_only else (0,1,2)
    for tick,target in enumerate(magnitude):
        if tick%250==0:print(json.dumps(dict(stage='six_voice_fit',variant='square' if square_only else 'selectable',tick=tick,total=count)),flush=True)
        if rms[tick]<1e-8:p[tick]=preceding;continue
        # Sub-bin peak interpolation yields clock-quantized periods, without
        # snapping speech frequencies to musical notes. Subharmonics allow a
        # single square/triangle to explain several related peaks.
        peaks=np.flatnonzero((target[1:-1]>target[:-2])&(target[1:-1]>=target[2:]))+1
        global_peaks=peaks[np.argsort(target[peaks])[-18:]]
        if band_peak_count:
            local=[]
            for low,high in ((50,800),(800,1800),(1800,3500),(3500,8001)):
                eligible=peaks[(hz[useful][peaks]>=low)&(hz[useful][peaks]<high)&(target[peaks]>target.max()*.025)]
                local.extend(eligible[np.argsort(target[eligible])[-band_peak_count:]])
            peaks=np.unique(np.r_[global_peaks,local]).astype(int)
        else:peaks=global_peaks
        if not len(peaks):peaks=np.array([int(target.argmax())])
        log=np.log(np.maximum(target,1e-15))
        left=log[np.maximum(peaks-1,0)];right=log[np.minimum(peaks+1,len(log)-1)]
        curvature=left-2*log[peaks]+right
        shift=np.divide(.5*(left-right),curvature,out=np.zeros(len(peaks)),where=abs(curvature)>1e-12)
        frequency=hz[useful][peaks]+np.clip(shift,-.5,.5)*hz[1]
        proposed=np.rint(CLOCK/(16*np.r_[frequency,frequency/3,frequency/5])).astype(int)
        proposed=np.unique(np.r_[proposed-1,proposed,proposed+1,preceding])
        proposed=proposed[(proposed>=periods[0])&(proposed<=periods[-1])]
        indices=proposed-periods[0]
        candidates=[];columns=[]
        for shape in allowed:
            candidates.extend((int(period),shape,0) for period in proposed)
            columns.extend(basis[shape,indices])
        shared=16
        # Shared noise is eligible only for a broadband source field. Estimate
        # colour from its median floor, rather than fitting random FFT peaks.
        if flatness[tick]>.12:
            floor=np.minimum(target,float(np.percentile(target,65)))
            scores=noise@floor/np.maximum(np.linalg.norm(noise,axis=1),1e-12)
            shared=int(scores.argmax()+1)
            candidates.append((4095,0,1));columns.append(noise[shared-1])
            for shape in allowed:
                candidates.extend((int(period),shape,2) for period in proposed)
                columns.extend(.5*basis[shape,indices]+np.sqrt(.25+VARIANCE[shape])*noise[shared-1])
        candidates=np.array(candidates,int);columns=np.asarray(columns,float)
        weighted=columns*weights[tick]
        power=np.sum(weighted*columns,axis=1)
        remaining=target.astype(float).copy();chosen=[];coeff=[]
        excluded=np.zeros(len(columns),bool)
        for _ in range(6):
            correlation=weighted@remaining
            benefit=np.maximum(correlation,0)**2/np.maximum(power,1e-20)
            # Slight hysteresis rewards a held nearby period/shape.
            held=np.any((abs(np.log2(candidates[:,0,None]/preceding))<.02)&
                (candidates[:,1,None]==preceding_shape),axis=1)
            benefit*=1+.012*held;benefit[excluded]=-1
            best=int(benefit.argmax())
            if benefit[best]<=max(float(np.sum(weights[tick]*target**2))*.002,1e-16):break
            gain=max(0,float(correlation[best]/max(power[best],1e-20)))
            chosen.append(best);coeff.append(gain);remaining=np.maximum(remaining-gain*columns[best],0)
            if candidates[best,2]==1:excluded|=candidates[:,2]!=0
            else:
                close=abs(np.log2(candidates[:,0]/candidates[best,0]))<.025
                excluded|=close&(candidates[:,2]!=1)
                if candidates[best,2]==2:excluded|=candidates[:,2]!=0
        if chosen:
            b=columns[chosen];gram=(b*weights[tick])@b.T;correlation=(b*weights[tick])@target
            coeff=np.array(coeff)
            for _ in range(12):
                for j in range(len(chosen)):
                    coeff[j]=max(0,(correlation[j]-gram[j]@coeff+gram[j,j]*coeff[j])/max(gram[j,j],1e-20))
            selected=candidates[chosen]
            variance=np.where(selected[:,2]==1,.25,VARIANCE[selected[:,1]])
            variance=np.where(selected[:,2]==2,.0625+.5*variance,variance)
            prediction=np.sqrt(np.sum(coeff**2*variance))
            coeff*=np.clip(rms[tick]/max(prediction,1e-12),.1,10)
            padded=np.tile([4095,0,0],(6,1));padded[:len(selected)]=selected
            levels=np.zeros(6);levels[:len(coeff)]=coeff
            distance=abs(np.log2(preceding[:,None]/padded[None,:,0]))+.12*(preceding_shape[:,None]!=padded[None,:,1])
            distance[:,levels==0]=0
            costs=distance[np.arange(6)[None,:],ORDERS].sum(axis=1)
            order=ORDERS[int(costs.argmin())]
            p[tick],s[tick],modes[tick]=padded[order].T
            amplitude[tick]=levels[order];preceding=p[tick].copy();preceding_shape=s[tick].copy()
        else:p[tick]=preceding
        npd[tick]=shared
    positive=amplitude[amplitude>0]
    voice_gain=max(float(np.percentile(positive,99.5))*1.1,1e-5) if len(positive) else 1.
    volume=abs(amplitude[:,:,None]/voice_gain-LEVELS).argmin(axis=2).astype(np.uint8)
    volume[amplitude==0]=0
    return dict(periods=p,shapes=s,modes=modes,volumes=volume,noise_periods=npd),voice_gain


@lru_cache(maxsize=1)
def noise_cycle():
    bits=np.empty(131071,np.uint8);state=1
    for i in range(len(bits)):
        bits[i]=state&1;state=(state>>1)|(((state^(state>>3))&1)<<16)
    if state!=1:raise AssertionError('noise polynomial did not complete its period')
    return bits


def waveform(shape,phase):
    if shape==0:return (phase<.5).astype(float)
    if shape==1:return 1-abs(2*phase-1)
    if shape==2:return .5+.5*np.sin(2*np.pi*phase)
    raise ValueError('unknown waveform')


def validate(controls):
    count=len(controls['periods'])
    for name in ('periods','shapes','modes','volumes'):
        if controls[name].shape!=(count,6):raise ValueError('expected six controls per field')
    if controls['noise_periods'].shape!=(count,):raise ValueError('shared noise period missing')
    for name,lo,hi in (('periods',1,4095),('shapes',0,2),('modes',0,2),('volumes',0,15),('noise_periods',1,31)):
        if np.any(controls[name]<lo) or np.any(controls[name]>hi):raise ValueError('invalid '+name)
    return count


def synthesize_raw(controls,voice_gain=1.,oversample=OVERSAMPLE,*,transition_ms=0.,aligned_triangle=False,compensate_dc=False):
    """Run six phases with optional raised-cosine control transitions.

    Target periods, DAC codes and routes still arrive at 50 Hz. With a positive
    transition duration, a voice morphs from its previous level/shape/route to
    the current target using ONE continuously running oscillator phase. It
    never crossfades old/new frequencies or adds a second oscillator. Period
    changes take effect at the field boundary, without resetting the phase.
    This envelope is an explicit extension of the hypothetical hardware model;
    it is not a property of real AY fixed-volume registers.

    The aligned triangle starts at its midpoint rising, aligning its positive
    fundamental with square/sine. The legacy triangle starts at its trough,
    so switching shapes also changed the fundamental's phase by 90 degrees.
    Tone+noise multiplies the unipolar wave by the common noise bit. Noise-only
    holds the oscillator gate high, exactly the AY mixer interpretation.
    Optional DC compensation subtracts each target's known ensemble mean
    (.5 for a tone/noise, .25 for their product), with the same transition.
    It removes control-induced DC movement without filtering away low tones.
    This is an explicit balanced-output mixer extension of the hypothetical
    model, calculated from controls only; it is not source PCM correction.
    """
    if not isinstance(oversample,(int,np.integer)) or oversample<1:
        raise ValueError('oversample must be a positive integer')
    if not np.isfinite(transition_ms) or not 0<=transition_ms<=20:
        raise ValueError('transition duration must be within 0..20 ms')
    count=validate(controls);rate=OUTPUT_RATE*oversample;chunk=rate//50
    raw=np.empty(count*chunk);phase=np.zeros(6);nphase=0.;nindex=0
    time_axis=np.arange(chunk)/rate;bits=noise_cycle()
    blend=(.5-.5*np.cos(np.pi*np.minimum(time_axis/(transition_ms/1000),1))) if transition_ms else None
    def tone_for(shape,mode,positions,noise):
        if mode==1:tone=np.ones(chunk)
        elif shape==1 and aligned_triangle:tone=waveform(shape,(positions+.25)%1)
        else:tone=waveform(shape,positions)
        return tone*noise if mode else tone
    for tick in range(count):
        steps=CLOCK/(16*int(controls['noise_periods'][tick]))
        noise=bits[(nindex+np.floor(nphase+time_axis*steps).astype(int))%len(bits)]
        advance=nphase+chunk/rate*steps;nindex=(nindex+int(advance))%len(bits);nphase=advance%1
        mixed=np.zeros(chunk)
        for channel in range(6):
            frequency=CLOCK/(16*int(controls['periods'][tick,channel]))
            positions=(phase[channel]+frequency*time_axis)%1
            phase[channel]=(phase[channel]+chunk/rate*frequency)%1
            level=LEVELS[controls['volumes'][tick,channel]]*voice_gain
            old_level=LEVELS[controls['volumes'][tick-1,channel]]*voice_gain if tick else 0.
            if not level and (blend is None or not old_level):continue
            mode=int(controls['modes'][tick,channel])
            tone=tone_for(int(controls['shapes'][tick,channel]),mode,positions,noise)
            current=level*tone
            if compensate_dc:current-=level*(.25 if mode==2 else .5)
            if blend is None:mixed+=current
            else:
                old_mode=int(controls['modes'][tick-1,channel]) if tick else 0
                old=tone_for(int(controls['shapes'][tick-1,channel]),old_mode,positions,noise) if tick and old_level else 0.
                previous=old_level*old
                if compensate_dc:previous-=old_level*(.25 if old_mode==2 else .5)
                if compensate_dc:mixed+=(1-blend)*previous+blend*current
                else:mixed+=(1-blend)*old_level*old+blend*level*tone
        raw[tick*chunk:(tick+1)*chunk]=mixed
    return raw


def render(controls,voice_gain=1.,oversample=OVERSAMPLE,*,transition_ms=0.,output_bandwidth_hz=None,aligned_triangle=False,compensate_dc=False):
    """AC coupling and FIR, preserving the original render with default args.

    The old 19.845-kHz output passband exposed square-wave harmonics outside
    the fitter's 50..8000-Hz objective. A specified cutoff makes the audible
    output bandwidth explicit and consistent with the spectrum being fitted.
    """
    if output_bandwidth_hz is not None and (not np.isfinite(output_bandwidth_hz) or not 0<output_bandwidth_hz<OUTPUT_RATE/2):
        raise ValueError('output bandwidth must be within 0..22050 Hz')
    raw=synthesize_raw(controls,voice_gain,oversample,transition_ms=transition_ms,aligned_triangle=aligned_triangle,compensate_dc=compensate_dc)
    # An unipolar DAC needs AC coupling. Retain the AY renderer's 1024-output-
    # sample moving-mean horizon. FIR decimation prevents waveform aliasing.
    length=1024*oversample;cumulative=np.r_[0,np.cumsum(raw)]
    mean=(cumulative[1:]-cumulative[np.maximum(0,np.arange(len(raw))+1-length)])/length
    raw-=mean
    width=63*oversample;offset=np.arange(-width,width+1);cutoff=.45/oversample
    if output_bandwidth_hz is not None:cutoff=min(cutoff,output_bandwidth_hz/(OUTPUT_RATE*oversample))
    kernel=2*cutoff*np.sinc(2*cutoff*offset)*np.hanning(len(offset));kernel/=kernel.sum()
    return np.convolve(np.pad(raw,(width,width)),kernel,mode='valid')[::oversample]


def feedback(samples,controls,voice_gain,objective,*,allow_wave_proposals=True,render_options=None):
    render_options={} if render_options is None else render_options
    audio=render(controls,voice_gain,**render_options)
    calibration=min(float(np.sqrt(np.mean(samples**2)/max(np.mean(noise_colour.downsample(audio)**2),1e-20))),
        .95/max(float(abs(audio).max()),1e-12)) if np.any(samples) else 1.
    gain=voice_gain*calibration;audio*=calibration
    best=objective.measure(noise_colour.downsample(audio));baseline=best.copy();history=[]
    previous={k:v.copy() for k,v in controls.items()}
    ratio=np.clip(tick_rms(samples)/np.maximum(tick_rms(noise_colour.downsample(audio)),1e-12),.25,4)
    proposals=[]
    for strength in (.5,1.):
        candidate={k:v.copy() for k,v in previous.items()}
        target=LEVELS[candidate['volumes']]*ratio[:,None]**strength
        candidate['volumes']=abs(target[:,:,None]-LEVELS).argmin(axis=2).astype(np.uint8)
        candidate['volumes'][previous['volumes']==0]=0
        proposals.append((f'volume-{strength}',candidate))
    # Each periodic oscillator can be replaced by a pure sine in the proposal;
    # the complete spectrum decides whether removing its harmonics is useful.
    if allow_wave_proposals and np.any(previous['shapes']!=2):
        candidate={k:v.copy() for k,v in previous.items()};candidate['shapes'][:]=2
        proposals.append(('sine-only',candidate))
    for delta in (-1,1):
        candidate={k:v.copy() for k,v in previous.items()}
        candidate['noise_periods']=np.clip(candidate['noise_periods'].astype(int)+delta,1,31).astype(np.uint8)
        proposals.append((f'noise-{delta:+d}',candidate))
    for name,candidate in proposals:
        trial=render(candidate,gain,**render_options);metrics=objective.measure(noise_colour.downsample(trial));peak=float(abs(trial).max())
        accepted=peak<=.999 and metrics['objective_db']<best['objective_db']-1e-6
        history.append(dict(proposal=name,peak=peak,accepted=accepted,metrics=metrics))
        print(json.dumps(dict(stage='six_voice_feedback',proposal=name,accepted=accepted,objective_db=metrics['objective_db'])),flush=True)
        if accepted:controls=candidate;audio=trial;best=metrics
    return controls,audio,dict(baseline=baseline,final=best,voice_gain=gain,history=history,
        fixed_candidate_calibration=True,source_pcm_added_to_output=False,render_options=render_options)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference',type=Path,help='prepared mono 22050-Hz PCM16, e.g. previous original-preview.wav')
    parser.add_argument('--output',type=Path,required=True)
    comparison=parser.add_mutually_exclusive_group()
    comparison.add_argument('--ay-baseline',type=Path,help='previous AY PCM16 WAV for comparison')
    comparison.add_argument('--baseline',type=Path,help='previous model PCM16 WAV for comparison')
    parser.add_argument('--square-control',action='store_true',help='also fit six square-only voices as an ablation')
    parser.add_argument('--transition-ms',type=float,default=4.,help='hypothetical raised-cosine transition envelope, 0..20 ms (default: 4)')
    parser.add_argument('--output-bandwidth-hz',type=float,default=8000.,help='output FIR cutoff (default: 8000 Hz)')
    parser.add_argument('--analysis-window',type=int,default=512,choices=(512,1024,1536,2048),help='spectral fit window in samples (default: 512, 23.2 ms)')
    parser.add_argument('--spectral-weight-exponent',type=float,default=1.,help='source-only inverse-magnitude weighting, 0..2 (default: 1)')
    parser.add_argument('--band-peak-count',type=int,default=4,choices=range(9),help='extra peak proposals per frequency band (default: 4)')
    parser.add_argument('--no-dc-compensation',action='store_true',help='retain the unbalanced mixer for comparison')
    parser.add_argument('--legacy-render',action='store_true',help='original fitter, stepped levels, trough-start triangle and 19.845-kHz FIR')
    args=parser.parse_args();out=args.output
    if not args.legacy_render:
        if not np.isfinite(args.transition_ms) or not 0<=args.transition_ms<=20:
            parser.error('--transition-ms must be within 0..20')
        if not np.isfinite(args.output_bandwidth_hz) or not 0<args.output_bandwidth_hz<OUTPUT_RATE/2:
            parser.error('--output-bandwidth-hz must be within 0..22050')
        if not np.isfinite(args.spectral_weight_exponent) or not 0<=args.spectral_weight_exponent<=2:
            parser.error('--spectral-weight-exponent must be within 0..2')
    if out.exists() and any(out.iterdir()):raise ValueError('output must be new or empty')
    out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    fit_settings=dict(analysis_window=2048 if args.legacy_render else args.analysis_window,
        spectral_weight_exponent=0. if args.legacy_render else args.spectral_weight_exponent,
        band_peak_count=0 if args.legacy_render else args.band_peak_count,source_relative_weight_floor=.025)
    samples=read_reference(args.reference);templates=dictionary(fit_settings['analysis_window']);objective=Objective(samples)
    options={} if args.legacy_render else dict(transition_ms=args.transition_ms,output_bandwidth_hz=args.output_bandwidth_hz,
        aligned_triangle=True,compensate_dc=not args.no_dc_compensation)
    results={}
    variants=['selectable','square'] if args.square_control else ['selectable']
    for variant in variants:
        controls,gain=fit(samples,templates,square_only=variant=='square',
            spectral_weight_exponent=fit_settings['spectral_weight_exponent'],band_peak_count=fit_settings['band_peak_count'])
        controls,audio,info=feedback(samples,controls,gain,objective,allow_wave_proposals=variant=='selectable',render_options=options)
        name='six-voice-preview.wav' if variant=='selectable' else 'six-square-preview.wav'
        quality.write_wav(out/name,audio,OUTPUT_RATE)
        np.savez_compressed(out/f'{variant}-controls.npz',**controls)
        save(out/f'{variant}-feedback.json',info)
        active=controls['volumes']>0
        results[variant]=dict(wav=name,feedback=info,peak=float(abs(audio).max()),rms=float(np.sqrt(np.mean(audio**2))),
            clipping_samples=int(np.count_nonzero(abs(audio)>1)),shape_channel_fields={shape:int(((controls['shapes']==index)&active&(controls['modes']!=1)).sum()) for index,shape in enumerate(SHAPES)},
            noise_channel_fields=int((active&(controls['modes']==1)).sum()),mixed_channel_fields=int((active&(controls['modes']==2)).sum()),
            active_voice_fields=int(active.sum()))
    shutil.copyfile(args.reference,out/'reference.wav')
    baseline_path=args.baseline or args.ay_baseline
    if baseline_path:
        with wave.open(str(baseline_path),'rb') as stream:
            if stream.getframerate()!=OUTPUT_RATE or stream.getnchannels()!=1 or stream.getsampwidth()!=2:raise ValueError('invalid AY baseline WAV')
            pcm=np.frombuffer(stream.readframes(stream.getnframes()),'<i2').astype(float)/32768
        if len(pcm)!=len(samples)*2:raise ValueError('AY baseline duration differs')
        label='previous_model' if args.baseline else 'previous_AY'
        results[label]=dict(metrics=objective.measure(noise_colour.downsample(pcm)),wav=str(baseline_path),
            sha256=hashlib.sha256(baseline_path.read_bytes()).hexdigest())
    producers=(Path(__file__),Path(ay_fidelity.__file__),Path(music_profile.__file__),Path(noise_colour.__file__),
        Path(psychoacoustic.__file__),Path(quality.__file__),Path(__file__).with_name('simulation_refine.py'))
    save(out/'report.json',dict(complete=True,date='2026-10-13',hypothetical_hardware=True,voices=6,
        waveforms=SHAPES,clock_hz=CLOCK,period_range=[1,4095],fixed_volume_codes=16,update_hz=50,
        continuous_phase=True,shared_noise_generators=1,noise_lfsr_bits=17,hardware_envelope_used=False,
        no_volume_interpolation=args.legacy_render or args.transition_ms==0,render_options=options,
        fit_settings=fit_settings,
        transition_model='legacy steps' if args.legacy_render else 'raised-cosine level/shape/route morph on one phase per voice',
        oversample=OVERSAMPLE,output_rate_hz=OUTPUT_RATE,ticks=len(samples)//441,
        seconds=len(samples)/RATE,reference=str(args.reference.resolve()),reference_sha256=hashlib.sha256(args.reference.read_bytes()).hexdigest(),
        processed_pcm_sha256=hashlib.sha256(samples.astype('<f8').tobytes()).hexdigest(),results=results,
        producer_sources_sha256_lf={p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in producers},
        elapsed_seconds=time.perf_counter()-started,
        limitations='Hypothetical oscillator DAC, gating, transition-envelope and balanced-mixer model, not an actual AY or six-channel hardware proof. Targets are fixed 16-code levels; smooth transitions and optional control-only DC compensation explicitly extend the original model. Bounded magnitude proposals and full-render feedback; not a global optimum or listening grade.'))
    print(json.dumps(dict(complete=True,seconds=len(samples)/RATE,results={k:v.get('feedback',{}).get('final',v.get('metrics')) for k,v in results.items()})),flush=True)


if __name__=='__main__':main()
