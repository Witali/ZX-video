"""Joint colour/coverage search bounded by the monochrome source error.

Host prototype. Every logical 2x2 sample must preserve or improve averaged
RGB error and physical RGB error against a source sample held constant over
its 2x2 footprint. Rec.709 luma error is bounded per cell (default) or per
sample. These are model-specific guarantees, not perceptual percentages or
guarantees about unsampled source detail.
"""
import numpy as np

import five_level_dither as five
import monochrome_five_level as mono
from cell_palette_quality import ATTRS, PAIRS, PALETTES, averaged
from dither_phase import reversed_phase

LUMA = np.array([.2126,.7152,.0722])
COVERAGE = np.arange(5)/4
GRAIN = COVERAGE[None,:]*(1-COVERAGE[None,:])*np.mean((PAIRS[:,1]-PAIRS[:,0])**2,axis=1)[:,None]
PARAMETERS = dict(grain_weight=.03, previous_pair_score_allowance=4,
                  cell_luma_search_weight=2, rgb_guard=True, physical_rgb_guard=True)


def errors(image, state):
    actual = averaged(state)
    rgb = np.mean((actual-image.astype(float))**2,axis=2)
    luma = ((actual-image)@LUMA)**2
    attrs = np.frombuffer(bytes(state[3840:]),dtype=np.uint8)
    match = attrs[:,None]==ATTRS[None]
    if not np.all(match.any(axis=1)): raise ValueError('expected canonical non-FLASH attributes')
    indices = match.argmax(axis=1).reshape(24,32).repeat(4,0).repeat(4,1)
    levels = five.unpack_levels(bytes(state[:3840]))
    grain = GRAIN[indices,levels]
    return dict(rgb=rgb, luma=luma, physical_rgb=rgb+grain, grain=grain)


def encode(image, previous_attrs=None, *, luma_guard='cell'):
    mono.luma_numerator(image)  # Validate once before candidate arithmetic.
    if luma_guard not in ('sample','cell'): raise ValueError('unknown luma guard')
    weight = PARAMETERS['cell_luma_search_weight'] if luma_guard=='cell' else 0
    # Explicit monochrome fallback also covers a palette whose locally best
    # weighted choices do not satisfy the cell-wide luma bound.
    attrs_available = np.r_[ATTRS,np.uint8(71)]
    width = len(attrs_available)
    colours,inverse = np.unique(image.reshape(-1,3),axis=0,return_inverse=True)
    scores = np.empty((len(colours),width))
    choices = np.empty(scores.shape,dtype=np.uint8)
    selected_luma = np.empty(scores.shape)
    for lo in range(0,len(colours),512):
        source = colours[lo:lo+512].astype(float)
        y = source@LUMA
        numerator = colours[lo:lo+512].astype(np.uint32)@np.array([2126,7152,722],dtype=np.uint32)
        gray = ((8*numerator+2550000)//5100000).astype(float)*255/4
        mono_rgb = np.mean((source-gray[:,None])**2,axis=1)
        mono_luma = (y-gray)**2
        mono_grain = (gray/255)*(1-gray/255)*255**2
        distances = np.mean((source[:,None,None]-PALETTES[None])**2,axis=3)
        luma = (y[:,None,None]-PALETTES[None]@LUMA)**2
        valid = ((distances<=mono_rgb[:,None,None]+1e-7)
                 & (distances+GRAIN[None]<=(mono_rgb+mono_grain)[:,None,None]+1e-7))
        if luma_guard=='sample':valid &= luma<=mono_luma[:,None,None]+1e-7
        cost = np.where(valid, distances+weight*luma+PARAMETERS['grain_weight']*GRAIN[None],np.inf)
        selected = cost.argmin(axis=2)
        scores[lo:lo+len(source),:-1] = cost.min(axis=2)
        choices[lo:lo+len(source),:-1] = selected
        selected_luma[lo:lo+len(source),:-1] = np.take_along_axis(luma,selected[:,:,None],axis=2)[:,:,0]
        scores[lo:lo+len(source),-1] = mono_rgb+weight*mono_luma+PARAMETERS['grain_weight']*mono_grain
        choices[lo:lo+len(source),-1] = np.rint(gray*4/255).astype(np.uint8)
        selected_luma[lo:lo+len(source),-1] = mono_luma
    def cells(values):
        return values[inverse].reshape(24,4,32,4,width).transpose(0,2,1,3,4).reshape(768,16,width)
    totals = cells(scores).sum(axis=1)
    if luma_guard=='cell':
        light = cells(selected_luma).sum(axis=1)
        totals = np.where(light<=light[:,-1:]+1e-6,totals,np.inf)
    selected = totals.argmin(axis=1)
    assert np.all(np.isfinite(totals[np.arange(768),selected])), 'monochrome fallback must be feasible'
    if previous_attrs is not None:
        old = np.asarray(previous_attrs,dtype=np.uint8)
        if old.shape!=(768,) or np.any(old&128): raise ValueError('invalid previous attributes')
        swapped = (old&64)|((old&7)<<3)|((old>>3)&7)
        old = np.where(reversed_phase(old),swapped,old)
        match = old[:,None]==attrs_available[None]
        prior = match.argmax(axis=1)
        retain = match.any(axis=1)&(totals[np.arange(768),prior]<=totals.min(axis=1)+16*PARAMETERS['previous_pair_score_allowance'])
        selected = np.where(retain,prior,selected)
    levels = cells(choices)[np.arange(768),:,selected].reshape(24,32,4,4).transpose(0,2,1,3).reshape(96,128)
    levels[:12]=0;levels[84:]=0
    attrs=attrs_available[selected].copy();attrs[:96]=1;attrs[672:]=1
    state=five.pack_levels(levels)+attrs.tobytes()
    before,after=errors(image,mono.encode(image)),errors(image,state)
    for metric in ('rgb','physical_rgb'):
        assert np.all(after[metric][12:84]<=before[metric][12:84]+1e-7),metric
    if luma_guard=='sample':
        assert np.all(after['luma'][12:84]<=before['luma'][12:84]+1e-7)
    else:
        delta=(after['luma']-before['luma'])[12:84].reshape(18,4,32,4).sum(axis=(1,3))
        assert np.all(delta<=1e-6),'cell luma'
    return state
