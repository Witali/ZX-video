"""Measure one adaptive 4x4 candidate on three short original-RGB windows."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
from PIL import Image, ImageDraw

from audit_dither_phase import compress, sha
import build_long_video_trd as video
import spatial_dither as spatial


def mse(a, b):
    return float(np.mean((a.astype(np.float64)-b)**2))


def metrics(rendered, source, previous=None):
    source = source.astype(np.float64)
    native, wanted = rendered[24:168], source[12:84].repeat(2, 0).repeat(2, 1)
    average = spatial.pool(native, 2)
    residual = average-source[12:84]
    # Sliding 4x4 averages include all sixteen phase offsets, not only the
    # tiles used by the candidate's selection rule.
    sliding = [mse(spatial.pool(native[y:y+140, x:x+252], 4),
                   spatial.pool(wanted[y:y+140, x:x+252], 4)) for y in range(4) for x in range(4)]
    result = dict(native_mse=mse(native, wanted), logical_2x2_mse=mse(average, source[12:84]),
                  aligned_4x4_mse=mse(spatial.pool(native, 4), spatial.pool(wanted, 4)),
                  sliding_4x4_mse=float(np.mean(sliding)),
                  logical_grain=float(np.mean((average-spatial.pool(average, 2).repeat(2, 0).repeat(2, 1))**2)),
                  gradient_error=float(np.mean([mse(np.diff(average, axis=axis), np.diff(source[12:84], axis=axis)) for axis in (0, 1)])))
    result['temporal_residual_mse'] = None if previous is None else mse(residual, previous)
    return result, residual


def panels(image, old, new):
    source = image.repeat(2, 0).repeat(2, 1).astype(np.uint8)
    changed = np.any(old != new, axis=2)
    diff = (source.astype(np.float64)*0.25).astype(np.uint8)
    diff[changed] = (255, 64, 128)
    return [source, old.astype(np.uint8), new.astype(np.uint8), diff]


def sheet(rows, path):
    canvas = Image.new('RGB', (2048, 418*len(rows)), (24, 24, 24)); draw = ImageDraw.Draw(canvas)
    for row, (label, images) in enumerate(rows):
        for col, (title, array) in enumerate(zip(('Scaled source', 'Five levels', 'Adaptive 4x4', 'Changed native pixels'), images)):
            canvas.paste(Image.fromarray(array).resize((512, 384), Image.Resampling.NEAREST), (512*col, row*418+28))
            draw.text((512*col+6, row*418+8), label+' / '+title, fill='white')
    path.parent.mkdir(parents=True, exist_ok=True); canvas.save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'ffmpeg', 'zx0', 'cache', 'output', 'preview', 'synthetic-preview'):
        p.add_argument('--'+name, required=True, type=Path)
    p.add_argument('--starts', nargs='+', type=int, default=[629, 2857, 3855])
    p.add_argument('--window', type=int, default=32)
    a = p.parse_args()
    if a.window < 1 or any(start < 1 for start in a.starts): p.error('invalid window')
    with a.source.open('rb') as f: source_sha = hashlib.file_digest(f, 'sha256').hexdigest()
    cache = a.cache.resolve(); cache.mkdir(parents=True, exist_ok=True)
    zxcache = cache/sha(a.zx0.read_bytes()); zxcache.mkdir(exist_ok=True)
    windows, previews = [], []
    for start in a.starts:
        command = [str(a.ffmpeg.resolve()), '-v', 'error', '-nostdin', '-ss', str((start-1)*3/25),
                   '-i', str(a.source.resolve()), '-an', '-vf', 'fps=25/3,scale=256:144:flags=area',
                   '-pix_fmt', 'rgb24', '-frames:v', str(a.window+1), '-f', 'rawvideo', '-']
        path = cache/(sha((source_sha+json.dumps(command)).encode())+'.rgb')
        if not path.exists(): path.write_bytes(subprocess.run(command, check=True, capture_output=True).stdout)
        data = path.read_bytes()
        if len(data) != (a.window+1)*256*144*3: raise ValueError('incomplete RGB window')
        images = np.frombuffer(data, dtype=np.uint8).reshape(a.window+1, 144, 256, 3)
        previous_attrs, previous, residuals = None, {}, {}
        streams = {name:bytearray() for name in ('five', 'spatial')}
        # Equal native-byte XOR controls isolate the pattern from escape overhead.
        native_streams = {name:bytearray() for name in streams}; previous_native = {}
        rows, best = [], None
        for local, analysis in enumerate(images):
            image = video.apply_reframe(analysis, video.ReframeWindow(0.5, 0.5, 1.25))
            compact, previous_attrs = video.encode_compact_frame(image, previous_attrs, 100000, 'ordered4')
            old, new, selected = spatial.quantize(image, compact)
            current, rendered, measured = dict(five=old, spatial=new), {}, {}
            for name, frame in current.items():
                bits = spatial.decode(frame)
                rendered[name] = spatial.rgb(bits, frame.attrs)
                measured[name], residuals[name] = metrics(rendered[name], image, residuals.get(name))
                native = np.concatenate((np.packbits(bits).reshape(-1), np.frombuffer(frame.attrs, dtype=np.uint8)))
                if local:
                    packet = spatial.encode_delta(previous[name], frame, escapes=name == 'spatial')
                    if spatial.decode_delta(previous[name], packet, escapes=name == 'spatial') != frame:
                        raise AssertionError('cell delta roundtrip differs')
                    streams[name] += struct.pack('<H', len(packet))+packet
                    native_streams[name] += (native ^ previous_native[name]).tobytes()
                previous_native[name] = native
            if (old.attrs != new.attrs or np.any(rendered['spatial'][:24])
                    or np.any(rendered['spatial'][168:])):
                raise AssertionError('attributes or black borders changed')
            if measured['spatial']['aligned_4x4_mse'] > measured['five']['aligned_4x4_mse']+1e-8:
                raise AssertionError('selection increased aligned mean error')
            if local:
                changed = np.any(rendered['five'][24:168] != rendered['spatial'][24:168], axis=2)
                row = dict(source_frame=start+local-1, metrics=measured, selected_tiles=int(selected[6:42].sum()),
                           native_escape_cells=sum(new.modes[96:672]), changed_native_fraction=float(changed.mean()))
                rows.append(row)
                gain = measured['five']['aligned_4x4_mse']-measured['spatial']['aligned_4x4_mse']
                if best is None or gain > best[0]: best = (gain, row['source_frame'], panels(image, rendered['five'], rendered['spatial']))
            previous = current
        sizes = {}
        for name, blob in list(streams.items())+[(name+'_native_xor', blob) for name, blob in native_streams.items()]:
            chunks = [bytes(blob[i:i+15872]) for i in range(0, len(blob), 15872)]
            with ThreadPoolExecutor(max_workers=3) as pool:
                blocks = list(pool.map(lambda b: compress(b, a.zx0.resolve(), zxcache), chunks))
            sizes[name] = dict(raw_bytes=len(blob), zx0_bytes=sum(b['zx0_bytes']+4 for b in blocks), raw_sha256=sha(blob), blocks=blocks)
        summary = {name:{key:float(np.mean([r['metrics'][name][key] for r in rows])) for key in rows[0]['metrics'][name]} for name in streams}
        window = dict(start=start, carried_seed_frame=start-1, rgb_sha256=sha(data), command=command,
                      means=summary, compression=sizes, frames=rows,
                      mean_escape_fraction=sum(r['native_escape_cells'] for r in rows)/(len(rows)*576),
                      mean_changed_native_fraction=float(np.mean([r['changed_native_fraction'] for r in rows])))
        windows.append(window); previews.append((str(best[1]), best[2]))
        print(json.dumps(dict(start=start, means=summary, zx0={name:size['zx0_bytes'] for name, size in sizes.items()}, escape_fraction=window['mean_escape_fraction'])), flush=True)
    sheet(previews, a.preview)
    # A stationary grey ramp, eight uniform bars and fine contour fixtures.
    synthetic = np.zeros((96, 128, 3), dtype=np.uint8)
    synthetic[12:36] = np.arange(128)[None, :, None]*2
    synthetic[36:60] = np.repeat(np.round(spatial.DOT_COUNTS/16*255).astype(np.uint8), 16)[None, :, None]
    yy, xx = np.indices((24, 128))
    synthetic[60:84] = np.where((xx > yy*3)[..., None], 255, 0)
    attrs = np.zeros(768, dtype=np.uint8); attrs[96:672] = 71
    old, new, selected = spatial.quantize(synthetic, bytes(3072)+attrs.tobytes())
    sr = {name:spatial.rgb(spatial.decode(frame), frame.attrs) for name, frame in [('five', old), ('spatial', new)]}
    sheet([('Ramp / eight bars / diagonal edge', panels(synthetic, sr['five'], sr['spatial']))], a.synthetic_preview)
    report = dict(complete=True, release=False, baseline_commit='a3b4e4e', source_sha256=source_sha,
                  ffmpeg_sha256=sha(a.ffmpeg.read_bytes()), zx0_sha256=sha(a.zx0.read_bytes()), frames=len(rows)*len(windows),
                  logical_grid=[128,96], active_grid=[128,72], native_grid=[256,192], fps='25/3', ay='unchanged; not in this host probe',
                  algorithm=dict(bayer=spatial.BAYER.tolist(), dot_counts=spatial.DOT_COUNTS.tolist(), smooth_rgb_range=32,
                                 selection='strictly lower aligned 4x4 mean RGB error; fixed screen phase',
                                 baseline='nearest of all five coverages, same canonical endpoints and BRIGHT',
                                 preprocessing='256x144 area scale, fixed central zoom 1.25, no adaptive tone grouping or budget feedback'),
                  packet='96-byte attribute mask, 96-byte cell mask, nonzero attribute XORs, candidate-only mode bits for changed cells, 5-byte radix-5 or 8-byte native cells; u16 length',
                  compression='ZX0 blocks <=15872 decoded bytes plus 4-byte headers; windows carry seed but exclude its startup bytes',
                  excludes='FAP3 motion/Huffman/fragments, AY, n-2 masks, checkpoints, startup, disk padding and latency',
                  native_consumer_implemented=False, native_tstates_measured=False, full_playback_verified=False,
                  synthetic_metrics={name:metrics(rendered, synthetic)[0] for name, rendered in sr.items()},
                  preview_frames=[int(row[0]) for row in previews], preview_sha256=sha(a.preview.read_bytes()),
                  synthetic_preview_sha256=sha(a.synthetic_preview.read_bytes()), windows=windows,
                  source_sha256_lf={name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n', b'\n')) for name in
                                   ('spatial_dither.py','probe_spatial_dither.py','test_spatial_dither.py','five_level_dither.py','build_long_video_trd.py','audit_dither_phase.py','dither_phase.py')})
    a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(report=str(a.output), frames=report['frames'], preview_frames=report['preview_frames'])))


if __name__ == '__main__': main()
