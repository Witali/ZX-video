"""Source-independent five-level preparation and exact CB41 volume encoding.

All quantization happens on the host. The native ABI, 256-entry cell book,
fixed dither phase and two independently stored screen histories are unchanged.
"""
from collections import Counter
from pathlib import Path

import numpy as np

import build_long_video_trd as video
import five_level_dither as five
import hybrid_five_level as hybrid
from build_fap3_trd import sha
from probe_cell_codebook import changes, decode_check, encode
from probe_hybrid_five_level import error
from row_dictionary_video import encode_states


def prepare_frames(images, compact, directory):
    """Refine the generic converter's palette without changing its media fit.

    Keep palette history from the four-level conversion, exactly as in the
    verified movie preparation. Add the missing quarter shade only when it
    reduces RGB error; dithering is applied afterward at a fixed screen phase.
    """
    if len(images) != len(compact) or not len(images):
        raise ValueError('expected matching nonempty RGB and compact frames')
    path = Path(directory)/'five-states.npy'
    states = np.lib.format.open_memmap(path, mode='w+', dtype=np.uint8,
                                     shape=(len(images), five.STATE_BYTES))
    image = np.zeros((96, 128, 3), dtype=np.uint8)
    before, after = [], []
    for index, active in enumerate(images):
        image[12:84] = active
        original = compact[index].tobytes()
        refined = bytearray(hybrid.refine_compact(original, image))
        refined[3840:3936] = bytes([1])*96
        refined[4512:] = bytes([1])*96
        state = bytes(refined)
        old_error = error(hybrid.from_compact(original), image)
        new_error = error(hybrid.from_five(state, adaptive=False), image)
        if new_error > old_error+1e-9:
            raise AssertionError(('five-level refinement increased RGB error', index))
        states[index] = np.frombuffer(state, dtype=np.uint8)
        before.append(old_error)
        after.append(new_error)
        if index % 100 == 0:
            print(f'Five-level refinement: {index+1}/{len(images)}', flush=True)
    states.flush()
    return states, dict(metric='MSE of cell-averaged RGB over the active image',
        measured_against='scaled source before Spectrum palette quantization',
        mean_mse=float(np.mean(after)), maximum_mse=max(after), frame_mse=after,
        four_level_frame_mse=before, four_level_mean_mse=float(np.mean(before)),
        refinement_never_increased_rgb_error=True, brightness_levels=5,
        dither='fixed-phase 2x2 after brightness reconstruction',
        compression_additional_pixel_changes=False, perceptual_percent_claimed=False)


def row_sets(frames):
    """Validate native borders/attributes before planning any independent disk."""
    if frames.ndim != 2 or frames.shape[1] != five.STATE_BYTES or not len(frames):
        raise ValueError('expected nonempty N x 4608 five-level states')
    result = []
    for index, frame in enumerate(frames):
        words = five.unpack_words(frame[:3840].tobytes())
        if np.any(words[:12]) or np.any(words[84:]):
            raise ValueError(f'frame {index}: CB41 requires black top/bottom bands')
        attrs = frame[3840:]
        if np.any(attrs & 128) or np.any(attrs[:96] != 1) or np.any(attrs[672:] != 1):
            raise ValueError(f'frame {index}: CB41 requires FLASH=0 and border attribute 1')
        result.append(set(map(int, words.ravel())) | {0})
    return result


def row_partitions(sets, max_frames):
    """Maximal exact row-limited prefixes including both cold histories.

    This is only a RAM constraint. Compressed disk and AY capacity must be
    checked separately; the result makes no timing or minimum-disk claim.
    """
    if not sets or not 1 <= max_frames <= 10922:
        raise ValueError('expected frames and max_frames in 1..10922')
    parts, start = [], 0
    while start < len(sets):
        used = {0}.union(*sets[max(0, start-2):start])
        end = start
        while end < min(len(sets), start+max_frames):
            candidate = used | sets[end]
            if len(candidate) > 256:
                break
            used, end = candidate, end+1
        if end == start:
            raise ValueError(f'frame {start}: image and two cold histories need '
                             f'{len(used | sets[start])} rows; native maximum is 256. '
                             'No frames or brightness levels were discarded.')
        parts.append(dict(start=start, end=end, rows=len(used)))
        start = end
    return parts


def representation(frames, start, end):
    """Encode a selected volume with exact row and cell books, even if static."""
    if not 0 <= start < end <= len(frames) or end-start > 10922:
        raise ValueError('invalid CB41 volume extent or 16-bit AY tick count')
    first = max(0, start-2)
    local, rows = encode_states([frame.tobytes() for frame in frames[first:end]])
    changed = changes(local, start-first, end-start)
    counts = Counter(row['patterns'][i] for row in changed for i in row['changed'])
    book = sorted(counts, key=lambda key: (-counts[key], key))[:256]
    # The native loader always reads 2048 bytes. Short/static videos need
    # deterministic unused entries, not a different packet or decoder format.
    book += [bytes(4)]*(256-len(book))
    raw, table, details = encode(changed, book, rows['words'])
    initial, screens = decode_check(raw, local, start-first, end-start, rows['words'], rows)
    return dict(first=first, start=start, end=end, states=local, rows=rows,
        raw=raw, initial=initial, book=table, details=details, screen_sha256=screens,
        unique_changed_patterns=len(counts), full_host_screens_exact=True,
        raw_sha256=sha(raw))


def write_preview(images, states, quality, path):
    """Render the actual five-level reference, never the old compact preview."""
    from PIL import Image, ImageDraw
    indices = sorted({0, len(states)-1, *map(int, np.argsort(quality['frame_mse'])[-4:])})
    sheet = Image.new('RGB', (512, len(indices)*216), (24, 24, 24))
    labels = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        source = np.zeros((96, 128, 3), dtype=np.uint8)
        source[12:84] = images[index]
        sheet.paste(Image.fromarray(source).resize((256, 192), Image.Resampling.NEAREST),
                    (0, row*216+24))
        rendered = video.base.render_spectrum_screen(*five.expand(states[index].tobytes()))
        sheet.paste(Image.fromarray(rendered), (256, row*216+24))
        labels.text((4, row*216+4), f'Frame {index}: scaled source', fill='white')
        labels.text((260, row*216+4), 'Spectrum: five levels', fill='white')
    sheet.save(path)
    quality.update(preview_frames=indices, preview=Path(path).name)
