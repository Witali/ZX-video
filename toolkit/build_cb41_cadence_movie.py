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
    p.add_argument('--verify', choices=('cpu','fuse','none'), default='fuse')
    p.add_argument('--verification-timeout', type=float, default=1800)
    p.add_argument('--prefix', default='ZX-video-10fps')
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
    frames = []
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
