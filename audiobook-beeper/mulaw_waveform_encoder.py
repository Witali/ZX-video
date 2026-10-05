"""Offline G.711 search against the existing eight-pulse PDM player.

The stream remains standard one-byte mu-law. Only the PC searches: the Z80
still inverse-compands each byte and runs its unchanged exact accumulator.
The saved clock is a proposal, never a substitute for executing the result.
"""
import gzip
import time
from pathlib import Path

import numpy as np
from g711_codec import decode_table
from ima_waveform_encoder import WaveformModel, _best_unique
from waveform_kernel import workspace


def prepare(pcm, timeline):
    count = len(pcm) - 128
    holds = np.diff(timeline[:count * 8 + 1]).reshape(count, 8)
    unique, ids = np.unique(holds, axis=0, return_inverse=True)
    model = WaveformModel()
    # Split each physical hold into two equal integration intervals. This
    # reuses the tested 16-term kernel without inventing extra output edges.
    patterns = (((np.arange(256)[:, None] >> np.arange(8)) & 1) * 2 - 1)
    signed = np.repeat(patterns, 2, axis=1)
    features = []
    for row in unique:
        halves = np.repeat(row / 2, 2)
        a, b, l, r = model.packet(halves)
        features.append((a, l, signed @ r.T, signed @ b.T, halves / (3546900 / 8000)))
    starts = timeline[:count * 8].reshape(count, 8)
    queries = np.stack((starts + holds / 4, starts + holds * .75), axis=-1).reshape(count, 16)
    desired = model.reference(pcm.astype(float) / 256 + 128, queries)
    return desired, features, ids


def close_guard(chosen, error, levels):
    """Return the accumulator to its seed using only the silent guard.

    All mu-law levels are multiples of four. Eight pulses per sample make
    the residual a multiple of32; correcting the signed decoded sum modulo
    8192 therefore closes the exact16-bit state. Small +/-132,120,8 levels
    suffice in fewer than40 samples, below0.41% of DAC full-scale.
    """
    needed = ((32768-error)//8 + 4096) % 8192 - 4096
    lookup = {int(value)-32768:code for code,value in enumerate(levels)}
    values=[]
    if needed % 8:
        value = 132 if needed > 0 else -132
        values.append(value); needed-=value
    while needed:
        value = min(120,abs(needed)) * (1 if needed > 0 else -1)
        values.append(value);needed-=value
    assert len(values) <= 64
    for offset,value in enumerate(values):chosen[len(chosen)-64+offset]=lookup[value]
    assert (32768+8*sum(int(levels[code]) for code in chosen)) & 65535 == 32768


def pulse_tables(levels):
    """PC-only transitions for all2048 reachable residues and256 bytes."""
    residue=np.arange(0,65536,32)[:,None]+np.zeros((1,256),dtype=np.int64)
    words=np.zeros(residue.shape,dtype='u1')
    for bit in range(8):
        residue+=levels[None,:]
        words|=((residue>>16)<<bit).astype('u1')
        residue&=65535
    return words,residue.astype(np.uint16)


def encode(pcm, timeline, width=8, horizon=16, commit=8, regularization=.03,
           backend='auto', statistics=None):
    if not 1 <= commit <= horizon or width < 1 or regularization < 0:
        raise ValueError('invalid bounded mu-law search')
    n=len(pcm)*8
    clocks=[timeline[:n+1]-timeline[0]]
    if len(timeline)>=2*n+1:clocks.append(timeline[n:2*n+1]-timeline[n])
    models=[prepare(pcm,clock) for clock in clocks]
    prior=np.mean([timed_pcm(pcm,clock) for clock in clocks],axis=0)
    count=len(pcm)-128
    levels = decode_table('mulaw').astype(np.int64) + 32768
    pulse_words,pulse_successors=pulse_tables(levels)
    kernel = workspace(width, 256, backend)
    chosen = np.full(len(pcm), 255, dtype='u1')
    error = 32768
    state = [np.zeros(6) for _ in models]
    started = time.perf_counter()
    for start in range(0, count, commit):
        stop = min(start + horizon, count)
        errors = np.array([error]); states = [s[None].copy() for s in state]; costs = np.zeros(1)
        parents = np.empty((stop-start, width), dtype=np.intp)
        codes = np.empty((stop-start, width), dtype='u1')
        for sample in range(start, stop):
            word=pulse_words[errors>>5].ravel().astype(np.int64)
            next_error=pulse_successors[errors>>5].ravel().astype(np.int64)
            parent = np.repeat(np.arange(len(errors)), 256)
            score=costs[parent].copy()
            for s,(desired,features,ids) in zip(states,models):
                a,l,response,endpoint,weights=features[ids[sample]]
                base=s@l.T
                if kernel is None:
                    terms=(base[parent]+response[word]-desired[sample])**2*weights
                else:terms=kernel.errors(base,response,word,desired[sample],weights)
                score+=np.sum(terms,axis=1)/len(models)
            score += regularization * np.tile(((levels-32768-prior[sample]) / 32768) ** 2, len(errors))
            candidates = np.arange(len(score))
            best = (_best_unique(candidates, score, next_error, width) if kernel is None else
                    kernel.select(candidates, score, next_error))
            for cycle,(_,features,ids) in enumerate(models):
                a,_,_,endpoint,_=features[ids[sample]]
                states[cycle]=(states[cycle]@a.T)[parent[best]]+endpoint[word[best]]
            errors = next_error[best]; costs = score[best]
            parents[sample-start, :len(best)] = parent[best]
            codes[sample-start, :len(best)] = best % 256
        path = np.empty(stop-start, dtype='u1'); winner = 0
        for j in range(stop-start-1, -1, -1):
            path[j] = codes[j, winner]; winner = parents[j, winner]
        # Carry only the committed prefix. Speculative filter/accumulator
        # states beyond it must not leak into the next overlapping window.
        for sample, code in zip(range(start, min(start+commit, stop)), path):
            word=int(pulse_words[error>>5,code])
            error=int(pulse_successors[error>>5,code])
            for cycle,(_,features,ids) in enumerate(models):
                a,_,_,endpoint,_=features[ids[sample]]
                state[cycle]=a@state[cycle]+endpoint[word]
            chosen[sample] = code
        if start and start%16384==0:
            print({'mulaw_encoded_samples':start,'total_samples':count},flush=True)
    close_guard(chosen,error,levels)
    if statistics is not None:
        statistics.update(width=width, horizon=horizon, commit=commit,
            regularization=regularization, seconds=time.perf_counter()-started,
            backend='native' if kernel else 'numpy', clock_patterns=[len(m[1]) for m in models],
            reference_clocks=len(models),control_prior='mean timed PCM16, Lanczos16',
            z80_tstate_delta=0, spectrum_expanded_audio_bytes=0)
    return chosen.tobytes()


def saved_timeline(folder):
    return np.frombuffer(gzip.decompress((Path(folder)/'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)


def timed_pcm(pcm, timeline):
    """Float64 Lanczos prior at real hold centers; no PCM8 intermediate."""
    times=timeline[:len(pcm)*8+1:8]
    positions=(times[:-1]+times[1:])/(2*(3546900/8000))-.5
    centers=np.floor(positions).astype(np.int64);offsets=np.arange(-15,17)
    result=np.empty(len(pcm))
    for start in range(0,len(pcm),8192):
        stop=min(start+8192,len(pcm));index=centers[start:stop,None]+offsets
        distance=positions[start:stop,None]-index
        weights=np.sinc(distance)*np.sinc(distance/16)
        values=np.where((index>=0)&(index<len(pcm)),pcm[np.clip(index,0,len(pcm)-1)],0.)
        result[start:stop]=(values*weights).sum(axis=1)/weights.sum(axis=1)
    return np.clip(result,-32768,32767)
