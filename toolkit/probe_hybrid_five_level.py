"""Compare adaptive five-level cells on short, freshly quantized RGB windows.

Standalone cell-delta/ZX0 controls, not FAP3 or a whole-movie release. Source
windows use absolute source times; no credit edit is applied by this probe.
"""
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
import five_level_dither as five
import hybrid_five_level as hybrid


PALETTE = np.array([[video.base.zx_rgb((a >> 3) & 7, (a >> 6) & 1),
                     video.base.zx_rgb(a & 7, (a >> 6) & 1)] for a in range(128)], dtype=np.float64)


def error(frame, image):
    levels, attrs = hybrid.decode(frame)
    pairs = PALETTE[np.frombuffer(attrs, dtype=np.uint8)].reshape(24, 32, 2, 3).repeat(4, 0).repeat(4, 1)
    averaged = pairs[:, :, 0]+levels[:, :, None]/4*(pairs[:, :, 1]-pairs[:, :, 0])
    return float(np.mean((averaged[12:84]-image[12:84])**2))


def native(frame):
    levels, attrs = hybrid.decode(frame)
    return Image.fromarray(video.base.render_spectrum_screen(*five.expand(five.pack_levels(levels)+attrs)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'ffmpeg', 'zx0', 'cache', 'output', 'preview'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--starts', type=int, nargs='+', default=[629, 2857, 3855])
    p.add_argument('--window', type=int, default=32)
    p.add_argument('--zoom', type=float, default=1.25)
    p.add_argument('--palette-policy', choices=('retain', 'search'), default='retain')
    a = p.parse_args()
    if a.window < 1 or any(start < 1 for start in a.starts) or not 1 <= a.zoom <= 2:
        p.error('invalid source windows or zoom')
    with a.source.open('rb') as stream: source_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    cache = a.cache.resolve(); cache.mkdir(parents=True, exist_ok=True)
    zxcache = cache/sha(a.zx0.read_bytes()); zxcache.mkdir(exist_ok=True)
    windows, previews = [], []
    for start in a.starts:
        command = [str(a.ffmpeg.resolve()), '-v', 'error', '-nostdin', '-ss', str((start-1)*3/25),
                   '-i', str(a.source.resolve()), '-an', '-vf', 'fps=25/3,scale=256:144:flags=area',
                   '-pix_fmt', 'rgb24', '-frames:v', str(a.window+1), '-f', 'rawvideo', '-']
        key = sha((source_sha+json.dumps(command)).encode())
        rgbpath = cache/(key+'.rgb')
        if not rgbpath.exists():
            result = subprocess.run(command, check=True, capture_output=True)
            rgbpath.write_bytes(result.stdout)
        rgb = rgbpath.read_bytes()
        if len(rgb) != (a.window+1)*256*144*3: raise ValueError('source window has incomplete RGB frames')
        images = np.frombuffer(rgb, dtype=np.uint8).reshape(a.window+1, 144, 256, 3)
        previous, previous_four_attrs, previous_five_attrs = {}, None, None
        streams = {name:bytearray() for name in ('four', 'five', 'hybrid', 'canonical')}
        frames = []; best_preview = None
        for local, analysis in enumerate(images):
            image = video.apply_reframe(analysis, video.ReframeWindow(0.5, 0.5, a.zoom))
            compact, previous_four_attrs = video.encode_compact_frame(image, previous_four_attrs, 100000, 'ordered4')
            five_state = (hybrid.refine_compact(compact, image) if a.palette_policy == 'retain'
                          else five.encode_image(image, previous_five_attrs, 100000))
            previous_five_attrs = np.frombuffer(five_state[3840:], dtype=np.uint8).copy()
            variants = dict(four=hybrid.from_compact(compact),
                five=hybrid.from_five(five_state, adaptive=False),
                hybrid=hybrid.from_five(five_state, previous=previous.get('hybrid')),
                canonical=hybrid.from_five(five_state, previous=previous.get('canonical'), canonical_quartets=True))
            wanted_lv, wanted_at = hybrid.decode(variants['five'])
            for name in ('hybrid', 'canonical'):
                lv, at = hybrid.decode(variants[name])
                if not np.array_equal(lv, wanted_lv) or at != wanted_at:
                    raise AssertionError('adaptive five-level coverage or colours changed')
            if local:
                for name, current in variants.items():
                    packet = hybrid.encode_delta(previous[name], current, policy=name)
                    if hybrid.decode_delta(previous[name], packet, policy=name) != current:
                        raise AssertionError('cell-delta roundtrip differs')
                    streams[name] += struct.pack('<H', len(packet))+packet
                before, after = error(variants['four'], image), error(variants['five'], image)
                if a.palette_policy == 'retain' and after > before+1e-9:
                    raise AssertionError('retained-palette refinement increased error')
                active_modes = variants['hybrid'].modes[96:672]
                frames.append(dict(source_frame=start+local-1, four_mse=before, five_mse=after,
                                   escaped_cells=sum(active_modes), active_cells=576))
                benefit = before-after
                if best_preview is None or benefit > best_preview[0]:
                    best_preview = (benefit, start+local-1, image.copy(), variants['four'], variants['hybrid'])
            previous = variants
        sizes = {}
        for name, blob in streams.items():
            chunks = [bytes(blob[pos:pos+15872]) for pos in range(0, len(blob), 15872)]
            with ThreadPoolExecutor(max_workers=3) as pool:
                blocks = list(pool.map(lambda chunk: compress(chunk, a.zx0.resolve(), zxcache), chunks))
            sizes[name] = dict(raw_bytes=len(blob), zx0_bytes=sum(b['zx0_bytes']+4 for b in blocks),
                               raw_sha256=sha(blob), blocks=blocks)
        row = dict(start=start, end_exclusive=start+a.window, carried_seed_frame=start-1,
                   command=command, rgb_sha256=sha(rgb), compression=sizes, frames=frames,
                   mean_four_mse=float(np.mean([r['four_mse'] for r in frames])),
                   mean_five_mse=float(np.mean([r['five_mse'] for r in frames])),
                   worse_mse_frames=sum(r['five_mse'] > r['four_mse'] for r in frames),
                   escape_fraction=sum(r['escaped_cells'] for r in frames)/(len(frames)*576))
        windows.append(row); previews.append(best_preview)
        print(json.dumps({k:v for k,v in row.items() if k not in ('frames', 'compression', 'command')}), flush=True)
    sheet = Image.new('RGB', (1536, 420*len(previews)), (24, 24, 24)); draw = ImageDraw.Draw(sheet)
    for row, (_, index, image, old, new) in enumerate(previews):
        panels = (Image.fromarray(image).resize((256,192), Image.Resampling.NEAREST), native(old), native(new))
        for col, (label, panel) in enumerate(zip(('Scaled source', 'Four-code cells', 'Adaptive five-level cells'), panels)):
            sheet.paste(panel.resize((512,384), Image.Resampling.NEAREST), (512*col,420*row+28))
            draw.text((512*col+8,420*row+8), f'{index}: {label}', fill='white')
    a.preview.parent.mkdir(parents=True, exist_ok=True); sheet.save(a.preview)
    report = dict(scope=__doc__, complete=True, release=False, source_sha256=source_sha,
        ffmpeg_sha256=sha(a.ffmpeg.read_bytes()), zx0_sha256=sha(a.zx0.read_bytes()),
        frames=sum(len(w['frames']) for w in windows), rgb_preprocessing='256x144 area scale, fixed central zoom, 128x72 active area; no adaptive tone grouping or feedback budget',
        metric='mean squared sRGB error of each 2x2 average versus scaled source, active picture only',
        attribute_change_penalty=100000, flash_used=False, exact_hybrid_five_equivalence=True,
        palette_policy=a.palette_policy,
        previous_state_carried_within_windows=True, cold_window_seed_not_in_compressed_bytes=True,
        native_consumer_implemented=False, native_tstates_measured=False, disk_delivery_measured=False,
        compression_excludes='FAP3 motion, Huffman, fragments, AY, native n-2 masks, checkpoints, startup and disk padding',
        preview_frames=[v[1] for v in previews], preview_sha256=sha(a.preview.read_bytes()), windows=windows,
        source_sha256_lf={name:sha((Path(__file__).parent/name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('hybrid_five_level.py','probe_hybrid_five_level.py','test_hybrid_five_level.py','five_level_dither.py')})
    a.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('windows','source_sha256_lf')}))


if __name__ == '__main__': main()
