"""Bounded host-only palette repair for fixed-phase five-level pictures.

Evaluate all legal canonical colour pairs, including normal white. Retain a
previous pair only within a small per-cell RGB error budget, and never above
the supplied baseline's error. Pixel/attribute formats and native code stay
unchanged. This experimental selector is not the converter default.
"""
import numpy as np
import build_long_video_trd as video
import five_level_dither as five
from dither_phase import reversed_phase

ATTRS = np.array([(bright<<6)|(paper<<3)|ink for bright in range(2)
                 for paper in range(8) for ink in range(paper+1,8)],dtype=np.uint8)
PAIRS = np.array([[video.base.zx_rgb((int(a)>>3)&7,int(a)>>6),
                   video.base.zx_rgb(int(a)&7,int(a)>>6)] for a in ATTRS],dtype=np.float64)
PALETTES = PAIRS[:,0,None]+np.arange(5)[None,:,None]/4*(PAIRS[:,1]-PAIRS[:,0])[:,None]


def averaged(state):
    levels = five.unpack_levels(bytes(state[:3840]))
    attrs = np.frombuffer(bytes(state[3840:]),dtype=np.uint8)
    pairs = np.array([[video.base.zx_rgb((int(a)>>3)&7,(int(a)>>6)&1),
                       video.base.zx_rgb(int(a)&7,(int(a)>>6)&1)] for a in attrs],dtype=np.float64)
    pairs = pairs.reshape(24,32,2,3).repeat(4,0).repeat(4,1)
    return pairs[:,:,0]+levels[:,:,None]/4*(pairs[:,:,1]-pairs[:,:,0])


def restore_endpoints(image, state, *, margin=12):
    """Experimental near-endpoint bias, preserving colours and all five codes.

    A fixed 12..243 contrast stretch proposes endpoint decisions only. Keep
    every other pixel unchanged; allow quarter-to-black or three-quarter-to-
    bright-white moves, never coloured endpoint snapping. This intentionally
    trades some RGB accuracy for larger solid black/white areas. It is not a
    lossless transform or the converter default.
    """
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 RGB 128x96')
    if not 0 <= margin < 128:
        raise ValueError('invalid contrast margin')
    levels = five.unpack_levels(bytes(state[:3840]))
    attrs = np.frombuffer(bytes(state[3840:]), dtype=np.uint8)
    if attrs.shape != (768,) or np.any(attrs & 128):
        raise ValueError('expected a non-FLASH five-level state')
    pairs = np.array([[video.base.zx_rgb((int(a)>>3)&7, (int(a)>>6)&1),
                       video.base.zx_rgb(int(a)&7, (int(a)>>6)&1)]
                      for a in attrs], dtype=float)
    pairs = pairs.reshape(24, 32, 2, 3).repeat(4, 0).repeat(4, 1)
    shades = pairs[:, :, :1] + np.arange(5)[None, None, :, None]/4 * (
        pairs[:, :, 1:] - pairs[:, :, :1])
    target = np.clip((image.astype(float)-margin)*255/(255-2*margin), 0, 255)
    nearest = ((shades-target[:, :, None])**2).sum(axis=3).argmin(axis=2)
    for endpoint, adjacent in ((0, 1), (4, 3)):
        colour = shades[:, :, endpoint]
        neutral_extreme = np.all(colour == 0, axis=2) | np.all(colour == 255, axis=2)
        move = (levels == adjacent) & (nearest == endpoint) & neutral_extreme
        levels[move] = endpoint
    levels[:12] = 0
    levels[84:] = 0
    return five.pack_levels(levels) + bytes(state[3840:])


def encode(image, reference, previous_attrs=None, *, keep_mse=64):
    image = np.asarray(image)
    if image.shape!=(96,128,3) or image.dtype!=np.uint8 or keep_mse<0:
        raise ValueError('expected uint8 RGB 128x96 and nonnegative keep budget')
    if len(reference)!=4608 or np.any(np.frombuffer(bytes(reference[3840:]),dtype=np.uint8)&128):
        raise ValueError('expected a non-FLASH five-level reference')
    colours,inverse = np.unique(image.reshape(-1,3),axis=0,return_inverse=True)
    errors = np.empty((len(colours),len(ATTRS)))
    choices = np.empty(errors.shape,dtype=np.uint8)
    for lo in range(0,len(colours),512):
        distances = ((colours[lo:lo+512,None,None].astype(float)-PALETTES[None])**2).sum(axis=3)
        errors[lo:lo+512] = distances.min(axis=2)
        choices[lo:lo+512] = distances.argmin(axis=2)
    def cells(values):
        return values[inverse].reshape(24,4,32,4,len(ATTRS)).transpose(0,2,1,3,4).reshape(768,16,len(ATTRS))
    scores = cells(errors).sum(axis=1)
    selected = scores.argmin(axis=1)
    reference_error = ((averaged(reference)-image)**2).reshape(24,4,32,4,3).transpose(0,2,1,3,4).sum(axis=(2,3,4)).reshape(768)
    allowed = np.minimum(scores.min(axis=1)+keep_mse*48,reference_error)
    if previous_attrs is not None:
        old = np.asarray(previous_attrs,dtype=np.uint8)
        if old.shape!=(768,) or np.any(old&128): raise ValueError('invalid previous attributes')
        swapped = (old&64)|((old&7)<<3)|((old>>3)&7)
        old = np.where(reversed_phase(old),swapped,old)
        match = ATTRS[None]==old[:,None]
        index = match.argmax(axis=1)
        retain = match.any(axis=1)&(scores[np.arange(768),index]<=allowed+1e-8)
        selected = np.where(retain,index,selected)
    levels = cells(choices)[np.arange(768),:,selected].reshape(24,32,4,4).transpose(0,2,1,3).reshape(96,128)
    levels[:12]=0;levels[84:]=0
    attrs=ATTRS[selected].copy();attrs[:96]=1;attrs[672:]=1
    state=five.pack_levels(levels)+attrs.tobytes()
    after=((averaged(state)-image)**2).reshape(24,4,32,4,3).transpose(0,2,1,3,4).sum(axis=(2,3,4)).reshape(768)
    if np.any(after[96:672]>reference_error[96:672]+1e-8):
        raise AssertionError('palette repair increased active-cell RGB error')
    return state
