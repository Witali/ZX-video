"""Remove invisible CB46 attribute writes without adding later writes.

Keep bitmap bits and the five-level dither phase exactly. For each physical
screen parity, retain an attribute through an entire constant-attribute run
only when its used INK/PAPER colours stay identical throughout that run.
This is an encoder transform; no new player instruction or wire mode.
"""
import struct

import numpy as np

from build_fap3_trd import sha
from build_zxv_trd import render_spectrum_screen
from dynamic_row_dictionary import patterns
from probe_cell_codebook import indices, mask
import five_level_dither as five


def colours(attribute):
    """Colour identities: BRIGHT affects every colour except black."""
    bright = (attribute >> 3) & 8
    ink, paper = attribute & 7, (attribute >> 3) & 7
    return (ink | bright if ink else 0), (paper | bright if paper else 0)


def retain_runs(attributes, has_ink, has_paper, initial, frozen=None):
    """One parity, T x cells arrays; preserve initial physical attributes."""
    result = attributes.copy()
    for cell in range(attributes.shape[1]):
        values = attributes[:, cell]
        starts = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1]
        ends = np.r_[starts[1:], len(values)]
        previous = int(initial[cell])
        for lo, hi in zip(starts, ends):
            target = int(values[lo])
            old_ink, old_paper = colours(previous)
            ink, paper = colours(target)
            valid = ((old_ink == ink or not has_ink[lo:hi, cell].any())
                     and (old_paper == paper or not has_paper[lo:hi, cell].any()))
            if not valid or (frozen is not None and frozen[lo]):
                previous = target
            result[lo:hi, cell] = previous
    old_changed = attributes != np.vstack((initial, attributes[:-1]))
    new_changed = result != np.vstack((initial, result[:-1]))
    assert not np.any(new_changed & ~old_changed), 'introduced an attribute write'
    return result


def transform_states(frames, start, end, frozen_frames=()):
    if not 0 <= start < end <= len(frames):
        raise ValueError('invalid frame extent')
    if frames.shape[1] != 4608 or np.any(frames[:, 3840:] & 128):
        raise ValueError('expected five-level states without FLASH')
    result = frames.copy()
    frozen = np.array([f in frozen_frames for f in range(start,end)])
    words = np.stack([patterns(f) for f in frames[start:end]])
    top = np.frombuffer(five.TOP, dtype=np.uint8)[words]
    bottom = np.frombuffer(five.BOTTOM, dtype=np.uint8)[words]
    has_ink = np.any((top | bottom) != 0, axis=2)
    has_paper = np.any((top & bottom) != 255, axis=2)
    for parity in range(min(2, end-start)):
        first = start+parity
        history = frames[max(0, first-2), 3936:4512]
        result[first:end:2, 3936:4512] = retain_runs(
            frames[first:end:2, 3936:4512], has_ink[parity::2],
            has_paper[parity::2], history, frozen[parity::2])
    return result


def verify_rgb(before, after, start, end):
    """Independent rendered-pixel proof, including borders and both BRIGHTs."""
    assert before.shape == after.shape
    assert np.array_equal(before[:, :3840], after[:, :3840])
    assert np.array_equal(before[:start], after[:start])
    assert np.array_equal(before[end:], after[end:])
    hashes = []
    changed = []
    for frame in range(start, end):
        old_bitmap, old_attr = five.expand(before[frame].tobytes())
        new_bitmap, new_attr = five.expand(after[frame].tobytes())
        assert old_bitmap == new_bitmap
        old = render_spectrum_screen(old_bitmap, old_attr)
        new = render_spectrum_screen(new_bitmap, new_attr)
        assert np.array_equal(old, new), ('RGB differs', frame)
        hashes.append(sha(new.tobytes()))
        changed.append(int(np.count_nonzero(before[frame, 3840:] != after[frame, 3840:])))
    return dict(complete=True,frames=end-start,rendered_rgb_bytes=(end-start)*192*256*3,
        rendered_rgb_sha256=hashes,bitmap_bytes_identical=True,
        physical_attribute_differences=changed,visible_pixel_changes=0)


def attribute_tstates(bits):
    """Exact fast-mask attribute stage, excluding common entry/return.

    Nonempty group: 21+14+8*22+22 =233 T, plus23 per written attribute.
    Empty group: 21+14+37+22 =94 T; E carry uses7+4 instead of12, saving1.
    Counts exclude paging, IRQ, ULA and physical disk service.
    """
    assert len(bits) == 72
    return sum(233 + 23 * value.bit_count() if value else
               94 - (((96+8*group) & 255) == 248)
               for group, value in enumerate(bits))


def transform_stream(raw, frames, transformed, start, end, frozen_frames=()):
    if raw[:4] != b'CB46':
        raise ValueError('expected CB46')
    data = bytearray(raw)
    keep = np.ones(len(data), dtype=bool)
    at = 2056
    details = []
    for frame in range(start, end):
        while True:
            header = at
            size = struct.unpack_from('<H', data, at)[0]
            at += 2
            if not size & 0x8000:
                break
            at += 3*(size & 0x7fff)
        stop = at+size
        old_mask = bytes(data[at+72:at+144])
        old_cells = indices(old_mask, 576)
        attr_at = stop-len(old_cells)
        target = transformed[frame, 3936:4512]
        previous = transformed[max(0, frame-2), 3936:4512]
        new_cells = old_cells if frame in frozen_frames else np.flatnonzero(target != previous).tolist()
        assert set(new_cells).issubset(old_cells)
        assert bytes(data[attr_at:stop]) == bytes(frames[frame, 3936:4512][old_cells])
        for i, cell in enumerate(old_cells):
            if cell not in new_cells:
                keep[attr_at+i] = False
            else:
                assert target[cell] == data[attr_at+i], 'retained writes keep original values'
        new_mask = mask(new_cells, 576)
        data[at+72:at+144] = new_mask
        removed = len(old_cells)-len(new_cells)
        struct.pack_into('<H', data, header, size-removed)
        old_t, new_t = attribute_tstates(old_mask), attribute_tstates(new_mask)
        assert new_t <= old_t
        details.append(dict(frame=frame,attribute_writes_before=len(old_cells),
            attribute_writes_after=len(new_cells),removed=removed,
            original_raw_start=header,original_raw_end=stop,
            attribute_stage_tstates_before=old_t,attribute_stage_tstates_after=new_t,
            attribute_stage_delta_tstates=new_t-old_t))
        at = stop
    assert at == len(data)
    mapping = np.r_[0, np.cumsum(keep)]
    return bytes(np.frombuffer(data, dtype=np.uint8)[keep]), mapping, details
