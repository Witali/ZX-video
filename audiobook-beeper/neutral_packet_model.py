"""Opt-in source-independent stable packet for the centered neutral PCM bin.

The frozen word is selected over every16-bit pattern using only counted
Pentagon timing and the established analytic listening filter. No source
audio participates in selection. Archived tables remain untouched by default.
"""
import numpy as np


NEUTRAL_PACKET_WORD=0x56AD
NEUTRAL_PACKET_SUCCESSOR=16
ORDINARY_PENTAGON_HOLDS=(36,28,28,31,24,26,22,46,22,26,22,30,31,27,34,16)
PHYSICAL_CPU_HZ=3584000


def on_time_tstates(word):
    """Exact unscaled ordinary hold area; bit15 is the first emitted bit."""
    if type(word) is not int or not 0<=word<=65535:
        raise ValueError('Neutral packet word must be builtin uint16 integer')
    return sum(hold for shift,hold in zip(range(15,-1,-1),ORDINARY_PENTAGON_HOLDS)
               if word&(1<<shift))


def validate_neutral_packet(model):
    """Return (word,16) when explicitly enabled, otherwise None.

    Validate before table mutation or any output-directory creation. A lone
    flag fails rather than silently enabling a partial model. Numerical model
    guards restrict this experiment to its fixed centered integral catalogue.
    """
    if model is None or not any(key in model for key in ('neutral_packet_word','neutral_packet_successor')):
        return None
    if not all(key in model for key in ('neutral_packet_word','neutral_packet_successor')):
        raise ValueError('Neutral packet word and successor must both be explicit')
    word=model['neutral_packet_word'];successor=model['neutral_packet_successor']
    if type(word) is not int or not 0<=word<=65535:
        raise ValueError('Neutral packet word must be builtin uint16 integer')
    if type(successor) is not int or successor!=NEUTRAL_PACKET_SUCCESSOR:
        raise ValueError('Neutral packet successor must be builtin integer16')
    if model.get('family','integral')!='integral':
        raise ValueError('Neutral packet requires the integral PDM family')
    bins=model.get('pcm_bins',64)
    if type(bins) is not int or bins!=64:
        raise ValueError('Neutral packet requires64 PCM bins')
    if type(model.get('pcm_quantization_bias')) is not int or model['pcm_quantization_bias']!=512:
        raise ValueError('Neutral packet requires centered PCM bias512')
    for key,default,expected in (('pcm_origin',.5,0),('extent',1.,1),('beta',.5,.5)):
        value=model.get(key,default)
        if type(value) not in (int,float) or value!=expected:
            raise ValueError(f'Neutral packet requires {key}={expected}')
    try:holds=tuple(model.get('holds',()));clip=tuple(model.get('q_clip',(0,15)))
    except TypeError:raise ValueError('Neutral timing and state bounds must be sequences') from None
    if holds!=ORDINARY_PENTAGON_HOLDS:
        raise ValueError('Neutral packet requires the exact counted449-T Pentagon holds')
    if clip!=(0,15) or any(type(value) is not int for value in clip):
        raise ValueError('Neutral packet requires the standard integer q_clip0..15')
    if on_time_tstates(word) not in (224,225):
        raise ValueError('Neutral packet on-time must be224 or225 of449 T states')
    return word,successor


def apply_neutral_packet(words,nxt,model):
    """Copy and override only bin32 for all32 states; absent option is identity."""
    override=validate_neutral_packet(model)
    if override is None:return words,nxt
    words_array=np.asarray(words);next_array=np.asarray(nxt)
    if (words_array.shape!=(64,32) or next_array.shape!=(64,32) or
            not np.issubdtype(words_array.dtype,np.integer) or
            not np.issubdtype(next_array.dtype,np.integer) or
            np.any(words_array<0) or np.any(words_array>65535) or
            np.any(next_array<0) or np.any(next_array>31)):
        raise ValueError('Neutral override requires uint16 words and closed64-bin/32-state tables')
    copied_words=words_array.copy();copied_next=next_array.copy()
    copied_words[32,:]=override[0];copied_next[32,:]=override[1]
    return copied_words,copied_next


def select_neutral_packet():
    """Enumerate all words before inspecting sources; return report and arrays.

    Solve the periodic filter state exactly in the analytic6-state model.
    Score each balanced word at the16 pulse midpoints, with physical duration
    weighting. Complementary signed waveforms have identical variance by
    linearity; evaluate their shared canonical representative and assign that
    exact score to both, so floating roundoff cannot break a mathematical tie.
    """
    from build_pdm import CPU_CLOCK
    from ima_waveform_encoder import WaveformModel
    holds=np.asarray(ORDINARY_PENTAGON_HOLDS,dtype=np.int64)
    physical_holds=holds*CPU_CLOCK/PHYSICAL_CPU_HZ
    analog=WaveformModel();a,b,l,r=analog.packet(physical_holds)
    fixed=np.linalg.solve(np.eye(6)-a,b)
    response=l@fixed+r
    words=np.arange(65536,dtype=np.int64)
    bits=((words[:,None]>>np.arange(15,-1,-1))&1).astype(np.int64)
    on=bits@holds;allowed=(on==224)|(on==225)
    canonical=np.minimum(words,65535-words)
    lower=np.arange(32768,dtype=np.int64)
    output=(bits[lower].astype(float)*2-1)@response.T
    mean=(output*holds).sum(axis=1)/449
    variance=(((output-mean[:,None])**2)*holds).sum(axis=1)/449
    second_moment=((output*output)*holds).sum(axis=1)/449
    variance=variance[canonical];second_moment=second_moment[canonical]
    signed_mean=mean[canonical]*np.where(words==canonical,1.,-1.)
    candidates=words[allowed]
    ranking=candidates[np.lexsort((candidates,variance[candidates]))]
    chosen=int(ranking[0])
    if chosen!=NEUTRAL_PACKET_WORD:
        raise RuntimeError('Analytic selector no longer reproduces the frozen neutral word')
    top=[]
    for word in ranking[:20]:
        top.append(dict(word=int(word),hex=f'0x{int(word):04X}',on_tstates=int(on[word]),
                        variance=float(variance[word]),rms=float(np.sqrt(variance[word])),
                        midpoint_weighted_mean=float(signed_mean[word]),
                        second_moment=float(second_moment[word])))
    next_pair=next(int(word) for word in ranking if int(canonical[word])!=int(canonical[chosen]))
    report=dict(date='2026-10-14',source_audio_opened=False,all_words_enumerated=65536,
                balanced_candidates=len(candidates),complement_pairs=len(candidates)//2,
                selected_word=chosen,selected_hex=f'0x{chosen:04X}',successor=NEUTRAL_PACKET_SUCCESSOR,
                selected_on_tstates=int(on[chosen]),period_tstates=449,
                physical_cpu_hz=PHYSICAL_CPU_HZ,reference_cpu_hz=CPU_CLOCK,
                physical_period_seconds=449/PHYSICAL_CPU_HZ,
                integer_holds=holds.tolist(),reference_holds=physical_holds.tolist(),
                constraints=dict(on_tstates=[224,225],maximum_half_duty_area_error_tstates=.5,
                                 all_zero_and_all_one_words_rejected=True,neutral_pcm_bin=32,
                                 all_feedback_states=32,successor=16),
                objective='Duration-weighted variance of the steady-state bipolar filtered waveform at each pulse midpoint',
                formula='steady=(I-A)^-1 Bword; output=Lsteady+Rword; variance=sum(hold*(output-weightedmean)^2)/449',
                filter='Existing6-state analytic70-Hz high-pass and two4500-Hz Butterworth low-pass pairs; no altered bandwidth',
                tie_rule='Exact complement symmetry followed by ascending unsigned word ID; no source-specific tie choice',
                selected_estimated_variance=float(variance[chosen]),
                selected_estimated_rms=float(np.sqrt(variance[chosen])),
                selected_signed_dc_duty=float((2*on[chosen]-449)/449),
                next_distinct_pair_word=next_pair,
                next_distinct_variance_ratio=float(variance[next_pair]/variance[chosen]),
                solve_condition=float(np.linalg.cond(np.eye(6)-a)),
                solve_residual_max=float(np.max(abs((np.eye(6)-a)@fixed-b))),
                spectral_radius=float(max(abs(np.linalg.eigvals(a)))),top_candidates=top,
                scope='Numerical analytic ordinary-packet selection only. Page/bank excursions, complete sources, actual FFmpeg/noise metrics and native/Fuse playback remain separate validation; no release or universal quality claim.')
    arrays=dict(words=words,on_tstates=on,allowed=allowed,variance=variance,
                second_moment=second_moment,midpoint_weighted_mean=signed_mean,
                ranking=ranking,a=a,b=b,l=l,r=r,steady_basis=fixed)
    return report,arrays
