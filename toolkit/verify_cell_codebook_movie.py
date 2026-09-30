"""Verify full preparation coverage, independent fixed dither and EOF handling.

Check every host screen, all retained AY states, the edit join and selected
RGB alignment against the old fixture. Produce a small source/reference
contact sheet; native playback remains a separate release requirement.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import ay_interrupt
import build_long_video_trd as video
import five_level_dither as five
from build_five_level_test_trd import save
from prepare_cell_codebook_movie import file_sha, sha, FRAME_BYTES
from prepare_edited_movie import frame_map


def independent_screen(frame):
    levels = five.unpack_levels(frame[:3840])
    # Explicit screen-phase cells; independent of TOP/BOTTOM lookup pages.
    tiles = np.array([[[0,0],[0,0]], [[1,0],[0,0]], [[1,0],[0,1]],
                      [[1,1],[0,1]], [[1,1],[1,1]]], dtype=np.uint8)
    pixels = tiles[levels].transpose(0,2,1,3).reshape(192,256)
    rows = np.packbits(pixels, axis=1)
    bitmap = bytearray(6144)
    for y, row in enumerate(rows):
        at = ((y & 7)<<8) | ((y & 56)<<2) | ((y & 192)<<5)
        bitmap[at:at+32] = row.tobytes()
    assert not np.any(pixels[:24]) and not np.any(pixels[168:])
    return bytes(bitmap)+frame[3840:]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'old-fixture', 'unextended-rgb', 'output', 'preview'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    report = json.loads(a.prepared.read_bytes())
    work = a.prepared.parent
    timeline = report['contract']['timeline']
    mapping = frame_map(timeline['source_frames'], timeline['remove_frames'])
    assert sha(mapping.astype('<i8').tobytes()) == report['source_frame_map_sha256']
    assert len(mapping) == report['frames'] and mapping[-1] == timeline['source_frames']-1
    raw = work/'analysis.rgb'
    assert file_sha(raw) == report['decoded_source']['sha256']
    old_hash, prefix_hash = hashlib.sha256(), hashlib.sha256()
    with a.unextended_rgb.open('rb') as original, raw.open('rb') as extended:
        while data := original.read(1024*1024):
            old_hash.update(data)
            prefix_hash.update(extended.read(len(data)))
        tail = extended.read()
    assert old_hash.digest() == prefix_hash.digest()
    assert len(tail) == FRAME_BYTES
    assert 0 <= report['decoded_source']['tail_hold_seconds'] < .12
    rgb = np.memmap(raw, dtype=np.uint8, mode='r', shape=(timeline['source_frames'],144,256,3))
    with np.load(a.old_fixture, allow_pickle=False) as old:
        samples = []
        for local, source in ((0,629),(63,692),(64,2857),(127,2920),(128,3855),(191,3918)):
            image = video.apply_reframe(rgb[source], video.ReframeWindow(.5,.5,1.25))
            assert np.array_equal(image, old['images'][local]), ('fixture RGB alignment', source)
            samples.append(source)
    requested = [629,2857,3855,4085,4086,4150,len(mapping)-1]
    worst = max(range(len(mapping)), key=lambda i: report['quality'][i]['five_mse'])
    if worst not in requested:
        requested.append(worst)
    pictures, exact, quality = {}, 0, report['quality']
    screens_hash = hashlib.sha256()
    for chunk in report['chunks']:
        path = work/chunk['file']
        assert file_sha(path) == chunk['sha256']
        with np.load(path, allow_pickle=False) as data:
            assert np.array_equal(data['source_frames'], mapping[chunk['start']:chunk['end']])
            for i, row in enumerate(data['five_states']):
                index = chunk['start']+i
                frame = row.tobytes()
                screen = independent_screen(frame)
                assert sha(screen) == quality[index]['screen_sha256'], ('independent dither', index)
                assert quality[index]['source_frame'] == mapping[index]
                assert quality[index]['five_mse'] <= quality[index]['four_mse']+1e-9
                assert not np.any(row[3840:] & 128)
                assert np.all(row[3840:3936] == 1) and np.all(row[4512:] == 1)
                screens_hash.update(screen)
                exact += 1
                if index in requested:
                    pictures[index] = data['images'][i].copy(), screen
    assert exact == len(mapping)
    sound = (work/'audio.bin').read_bytes()
    assert len(sound) == len(mapping)*54 and sha(sound) == report['ay_sha256']
    registers = b''.join(ay_interrupt.registers(video.AyFrame.deserialize(sound[i:i+9]))
                         for i in range(0,len(sound),9))
    assert sha(registers) == report['ay_registers_sha256']
    canvas = Image.new('RGB', (528, len(requested)*218), '#202020')
    draw = ImageDraw.Draw(canvas)
    for r, index in enumerate(requested):
        source, screen = pictures[index]
        draw.text((8,r*218+3), f'Frame {index}, source {mapping[index]}: RGB / five-level reference', fill='white')
        canvas.paste(Image.fromarray(source).resize((256,192),Image.Resampling.NEAREST),(4,r*218+22))
        rendered = video.base.render_spectrum_screen(screen[:6144],screen[6144:])
        canvas.paste(Image.fromarray(rendered),(268,r*218+22))
    a.preview.parent.mkdir(parents=True,exist_ok=True)
    canvas.save(a.preview)
    result = dict(complete=True, release=False, scope=__doc__, preparation_sha256=file_sha(a.prepared),
                  frames=exact, full_host_screens_exact=True, screen_bytes_checked=exact*6912,
                  screen_sequence_sha256=screens_hash.hexdigest(),
                  source_rgb_fixture_samples_exact=samples, same_prefix_before_final_hold=True,
                  unextended_frames=a.unextended_rgb.stat().st_size//FRAME_BYTES,
                  unextended_sha256=old_hash.hexdigest(), final_held_frame_bytes=len(tail),
                  all_retained_audio_ticks=len(sound)//9, ay_sha256=sha(sound),
                  source_frame_map_sha256=report['source_frame_map_sha256'],
                  four_mse_mean=float(np.mean([q['four_mse'] for q in quality])),
                  five_mse_mean=float(np.mean([q['five_mse'] for q in quality])),
                  refinement_never_increased_rgb_error=True, preview_frames=requested,
                  preview_sha256=file_sha(a.preview), actual_playback_measured=False,
                  source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n')))
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('frames','screen_bytes_checked','four_mse_mean','five_mse_mean')}))


if __name__ == '__main__':
    main()
