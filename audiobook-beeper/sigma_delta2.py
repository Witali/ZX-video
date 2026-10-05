"""Exact second-order error-feedback packets for the existing 16-pulse player.

Only the input is quantized. Both error coordinates survive packet boundaries
exactly; there is no state clipping, damping, or independent history rounding.
The closure certificate covers arbitrary sequences of the admitted input levels.
"""
from collections import deque
from fractions import Fraction
from functools import lru_cache
import json

import numpy as np


def model(scale=64, gain=(3, 8)):
    return dict(family='sigma_delta2', dac_scale=scale, gain_numerator=gain[0],
                gain_denominator=gain[1], output_gain=gain[0]/gain[1],
                pcm_bins=128, level_bounds=[4,123], slots=16,
                state_quantization=False, state_clipping=False,
                clock_scope='exact recurrence in decision index; physical OUT holds remain nonuniform')


def step(x, q, recent, scale, slots=16):
    """q=e[n-1]-e[n-2]; u=x+q+e[n-1]; e[n]=u-scale*bit."""
    word=peak=0
    for _ in range(slots):
        value=x+q+recent
        bit=int(2*value>=scale)
        recent=value-scale*bit
        q+=x-scale*bit
        word=word*2+bit
        peak=max(peak,abs(q),abs(recent))
    return word,(q,recent),peak


@lru_cache(maxsize=16)
def _build(encoded_model):
    spec=json.loads(encoded_model);scale=spec['dac_scale'];bins=spec['pcm_bins']
    gain=Fraction(spec['gain_numerator'],spec['gain_denominator'])
    if scale not in (32,64,128,256) or bins!=128 or spec['slots']!=16 or not 0<gain<=Fraction(1,2):
        raise ValueError('unsupported exact second-order packet parameters')
    if spec.get('output_gain')!=float(gain):
        raise ValueError('declared measurement gain differs from the modulator gain')
    levels=[round(Fraction(scale,2)+scale*gain*(Fraction(2*v+1,2*bins)-Fraction(1,2)))
            for v in range(bins)]
    reached={(0,0)};todo=deque(reached);peak=0
    while todo:
        q,r=todo.popleft()
        for x in sorted(set(levels)):
            _,state,p=step(x,q,r,scale);peak=max(peak,p)
            if p>8*scale or len(reached)>4096:
                raise ValueError('no bounded finite-state certificate within the declared limits')
            if state not in reached:reached.add(state);todo.append(state)
    # Keep the existing seed ID 16 and 32-column host-search representation.
    # The Spectrum stores only reachable states in six-byte packet entries.
    if len(reached)>32:
        raise ValueError(f'{len(reached)} exact states exceed the 32-column interface')
    ids=[i for i in range(32) if i!=16]
    states={16:(0,0)}
    states.update(zip(ids,sorted(reached-{(0,0)})))
    reverse={s:i for i,s in states.items()}
    words=np.empty((bins,32),dtype='<u2');nxt=np.empty((bins,32),dtype='u1')
    for v,x in enumerate(levels):
        for sid in range(32):
            word,state,_=step(x,*states.get(sid,(0,0)),scale)
            words[v,sid]=word;nxt[v,sid]=reverse[state]
    report=dict(order=2,ntf='(1-z^-1)^2 in decision index',
                exact_state_count=len(reached), input_levels=sorted(set(levels)),
                states={str(i):list(s) for i,s in states.items()},
                all_input_sequences_closed=True, state_rounding=False, state_clipping=False,
                maximum_internal_absolute_state=peak, dac_scale=scale,
                input_gain=float(gain), table_cases=bins*32,
                note='Input-level quantization and physical nonuniform timing are separate error sources.')
    words.flags.writeable=False;nxt.flags.writeable=False
    return words,nxt,report


def tables(spec):
    return _build(json.dumps(spec,sort_keys=True))


def independent_tables(spec):
    """Check every entry with separate two-history error-feedback equations."""
    words,nxt,report=tables(spec);scale=spec['dac_scale']
    states={int(i):tuple(s) for i,s in report['states'].items()}
    gain=Fraction(spec['gain_numerator'],spec['gain_denominator'])
    for v in range(128):
        x=round(Fraction(scale,2)+scale*gain*(Fraction(2*v+1,256)-Fraction(1,2)))
        for sid in range(32):
            q,recent=states.get(sid,(0,0));older=recent-q;word=0
            for _ in range(16):
                value=x+2*recent-older;bit=int(value>=Fraction(scale,2))
                older,recent=recent,value-bit*scale;word=(word<<1)|bit
            assert word==int(words[v,sid])
            assert (recent-older,recent)==states[int(nxt[v,sid])]
    return words,nxt
