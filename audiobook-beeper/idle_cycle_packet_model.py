"""Opt-in word-only replacement in the actual centered idle feedback cycle.

The prior source-independent selection froze 0x56AD. This mechanism replaces
only the emitted words for bin 32/state 16 and bin 32/state 17. It preserves the
entire successor graph, every other word and all existing default tables.
"""
import numpy as np
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS,on_time_tstates


IDLE_CYCLE_WORD=0x56AD
IDLE_CYCLE_STATES=(16,17)


def validate_idle_cycle_packet(model):
    """Return the frozen word for an enabled model, otherwise None.

    Array/cycle validation follows separately in apply_idle_cycle_packet;
    these model guards run before builders create any output directories.
    """
    if model is None or 'idle_cycle_word' not in model:return None
    if any(key in model for key in ('neutral_packet_word','neutral_packet_successor')):
        raise ValueError('Idle cycle cannot mix prior all-state neutral packet flags')
    word=model['idle_cycle_word']
    if type(word) is not int or not 0<=word<=65535:
        raise ValueError('Idle cycle word must be builtin uint16 integer')
    if word!=IDLE_CYCLE_WORD:
        raise ValueError('Idle cycle requires the previously frozen word 0x56AD')
    if on_time_tstates(word) not in (224,225):
        raise ValueError('Idle cycle word must have 224 or 225 on-T of 449')
    if model.get('family','integral')!='integral':
        raise ValueError('Idle cycle requires the integral PDM family')
    if type(model.get('pcm_bins',64)) is not int or model.get('pcm_bins',64)!=64:
        raise ValueError('Idle cycle requires 64 PCM bins')
    if type(model.get('pcm_quantization_bias')) is not int or model['pcm_quantization_bias']!=512:
        raise ValueError('Idle cycle requires centered PCM bias 512')
    for key,default,expected in (('pcm_origin',.5,0),('extent',1.,1),('beta',.5,.5)):
        value=model.get(key,default)
        if type(value) not in (int,float) or value!=expected:
            raise ValueError(f'Idle cycle requires {key}={expected}')
    try:holds=tuple(model.get('holds',()));clip=tuple(model.get('q_clip',(0,15)))
    except TypeError:raise ValueError('Idle timing and state bounds must be sequences') from None
    if holds!=ORDINARY_PENTAGON_HOLDS:
        raise ValueError('Idle cycle requires the exact counted 449-T Pentagon holds')
    if clip!=(0,15) or any(type(value) is not int for value in clip):
        raise ValueError('Idle cycle requires the standard integer q_clip 0..15')
    return word


def apply_idle_cycle_packet(words,nxt,model):
    """Copy exactly two words; keep every successor and the other 2046 words.

    Require the actual unmodified 16→17→16 neutral cycle. In particular this
    refuses an all-state successor reset even if its flags were stripped.
    Absent option is an identity operation with no extra table validation.
    """
    word=validate_idle_cycle_packet(model)
    if word is None:return words,nxt
    current=np.asarray(words);successors=np.asarray(nxt)
    if (current.shape!=(64,32) or successors.shape!=(64,32) or
            not np.issubdtype(current.dtype,np.integer) or
            not np.issubdtype(successors.dtype,np.integer) or
            np.any(current<0) or np.any(current>65535) or
            np.any(successors<0) or np.any(successors>31)):
        raise ValueError('Idle cycle requires uint16 words and closed 64-bin/32-state tables')
    if int(successors[32,16])!=17 or int(successors[32,17])!=16:
        raise ValueError('Idle cycle requires the original bin 32 successor cycle 16→17→16')
    copied=current.copy()
    copied[32,16]=word;copied[32,17]=word
    return copied,nxt
