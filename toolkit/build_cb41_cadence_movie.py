"""Build a prepared movie (or one bounded window) at its recorded cadence.

The FAP3 scaffold contains black placeholders and build-only AY envelopes.
Every runtime picture comes from the exact prepared five-level CB41 states;
every runtime AY tick comes from the independently hashed resident stream.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from build_long_video_trd import AyFrame
from convert_video import executable, write_json
from convert_cb41 import build
from encode_fap3 import encode
from prepare_cell_codebook_movie import file_sha, sha
from video_cadence import scaffold_audio
from verify_cell_codebook_movie import independent_screen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'output', 'trdos-rom'):
        p.add_argument('--'+name, type=Path, required=True)
    for name in ('zx0', 'lzsa'):
        p.add_argument('--'+name)
    p.add_argument('--fuse', type=Path)
    p.add_argument('--start', type=int, default=0)
    p.add_argument('--count', type=int)
    p.add_argument('--max-frames-per-disk', type=int, default=4096)
    p.add_argument('--target-volumes', type=int, choices=(3,), help='balance three volumes with local window costs')
    p.add_argument('--volume-cuts', type=lambda s:list(map(int,s.split(','))),
        help='explicit exclusive frame ends, including EOF, for measured timing repairs')
    p.add_argument('--only-volume', type=int, help='build/verify one selected volume with the final series identity')
    p.add_argument('--dynamic-rows',action='store_true',help='CB42 lossless row replacement during playback')
    p.add_argument('--verify', choices=('cpu','fuse','none'), default='fuse')
    p.add_argument('--verification-timeout', type=float, default=1800)
    p.add_argument('--prefix', default='ZX-video-10fps')
    p.add_argument('--monochrome', action='store_true',
        help='quantize cached source RGB to five fixed black/BRIGHT-white coverages')
    a = p.parse_args()
    meta = json.loads(a.prepared.read_bytes())
    a.frame_fields = meta['contract']['frame_fields']
    stop = a.start+a.count if a.count is not None else meta['frames']
    if not 0 <= a.start < stop <= meta['frames']:
        p.error('invalid prepared frame window')
    if a.output.exists() and any(a.output.iterdir()):
        p.error('output must be new or empty')
    from fap3_disk_z80 import TRDOS_503_SHA256
    assert file_sha(a.trdos_rom) == TRDOS_503_SHA256
    tools = {n:executable(getattr(a,n),n) for n in ('zx0','lzsa')}
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=True)
    work = a.output/'work'; work.mkdir()
    frames, images, quality = [], [], []
    for chunk in meta['chunks']:
        if chunk['end'] <= a.start or chunk['start'] >= stop:
            continue
        path = a.prepared.parent/chunk['file']
        assert file_sha(path) == chunk['sha256']
        with np.load(path, allow_pickle=False) as saved:
            lo,hi = max(a.start,chunk['start']),min(stop,chunk['end'])
            for index in range(lo,hi):
                frame = saved['five_states'][index-chunk['start']].copy()
                assert sha(independent_screen(frame.tobytes())) == meta['quality'][index]['screen_sha256']
                if a.monochrome:
                    import monochrome_five_level as mono
                    import five_level_dither as five
                    image = saved['images'][index-chunk['start']].copy()
                    frame = np.frombuffer(mono.encode(image), dtype=np.uint8).copy()
                    screen = independent_screen(frame.tobytes())
                    assert screen == b''.join(five.expand(frame.tobytes()))
                    images.append(image)
                    quality.append(dict(frame=index, source_frame=int(saved['source_frames'][index-chunk['start']]),
                                        screen_sha256=sha(screen), **mono.quality(image,frame)))
                frames.append(frame)
    frames = np.stack(frames)
    np.savez_compressed(work/'five-states.npz',five_states=frames)
    data = (a.prepared.parent/'audio.bin').read_bytes()
    assert sha(data) == meta['ay_sha256'] and len(data) == meta['frames']*a.frame_fields*9
    data = data[a.start*a.frame_fields*9:stop*a.frame_fields*9]
    audio = [AyFrame.deserialize(data[i:i+9]) for i in range(0,len(data),9)]
    (work/'ay.bin').write_bytes(data)
    compact = np.zeros((len(frames),3840),dtype=np.uint8)
    compact[:,3072:] = 1
    raw,scaffold = encode(compact,scaffold_audio(audio,a.frame_fields))
    (work/'stream.raw').write_bytes(raw)
    write_json(work/'scaffold.json', dict(scaffold, build_only=True, runtime_video='CB41',
        frame_fields=a.frame_fields, actual_ay_ticks=len(audio), ay_sha256=sha(data)))
    manifest = dict(complete=False,release=False,preparation_sha256=file_sha(a.prepared),
        video_fps=meta['contract']['fps'],frame_fields=a.frame_fields,ay_hz=50,
        prepared_range=[a.start,stop],whole_movie=a.start==0 and stop==meta['frames'],
        independent_host_screens_exact=True,scaffold_is_runtime_video=False)
    if a.monochrome:
        images = np.stack(images)
        np.savez_compressed(work/'monochrome-inputs.npz',images=images)
        samples = mono.preview(images,frames,a.start,a.output/'monochrome-preview.png')
        write_json(a.output/'monochrome-quality.json',dict(frames=quality,
            preview_frames=samples, input_rgb_sha256=sha(images.tobytes()),
            method='encoded Rec.709 Y = (2126 R + 7152 G + 722 B)/10000; nearest of five fixed coverages',
            active_attribute=71, flash=False, contrast_stretch=False,
            mean_luma_mse=float(np.mean([q['luma_mse'] for q in quality])),
            metric_limits='luma error after intentionally discarding colour; no colour-fidelity or perceptual percentage claim'))
        manifest.update(monochrome=True, palette='black and BRIGHT white; five fixed-phase 2x2 coverages',
            source_rgb_unchanged=True, colour_removed_by_user_request=True,
            quality_report='monochrome-quality.json', preview='monochrome-preview.png')
    write_json(a.output/'conversion.json',manifest)
    try:
        build(frames,audio,raw,compact,a,tools,a.output,manifest)
        manifest['complete'] = True
    except Exception as error:
        manifest['failure'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        write_json(a.output/'conversion.json',manifest)
    print(json.dumps({k:manifest[k] for k in ('frames','ay_ticks','timing_verified','duration_seconds')}),flush=True)


if __name__ == '__main__':
    main()
