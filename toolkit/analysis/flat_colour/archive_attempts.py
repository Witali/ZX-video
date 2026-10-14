"""Preserve measured size failures and the user-interrupted flat preparation."""
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def seal(directory):
    files = {path.relative_to(directory).as_posix():dict(bytes=path.stat().st_size, sha256=sha(path))
        for path in directory.rglob('*') if path.is_file() and path.name != 'manifest.json'}
    (directory/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8', newline='\n')
    return len(files)


def main():
    destination = HERE/'disk-attempts'
    if destination.exists():raise ValueError('attempt archive exists')
    for count in (1005, 980):
        source = ROOT/f'.tmp/lineart-disk-{count}'
        target = destination/f'capacity-{count}';target.mkdir(parents=True)
        for name in ('conversion.json', 'video-quality.json', 'audio-quality.json',
            'partition.json', 'timing.json', 'codec.json', 'compact-reuse.json', 'ZX-video-sea-foam-lineart_part01.json'):
            shutil.copyfile(source/name, target/name)
        shutil.copyfile(source.with_suffix('.log'), target/'conversion.log')
        meta = json.loads((target/'ZX-video-sea-foam-lineart_part01.json').read_bytes())
        (target/'attempt.json').write_text(json.dumps(dict(date='2026-10-14', frames=count,
            used_sectors=meta['used_sectors'], maximum_sectors=2544, trd_created=False,
            complete_host_preparation=True, complete_disk_playback=False,
            decision='Oversize actual disk assembly; preserve source/settings and shorten only the end.',
            input_cache='capacity-1005/cache-inputs.npz',
            image_parameters=json.loads((target/'video-quality.json').read_bytes())['colour_comparison']['parameters']),
            indent=2)+'\n', encoding='utf-8', newline='\n')
    source = ROOT/'.tmp/lineart-disk-1005/work'
    np.savez_compressed(destination/'capacity-1005/cache-inputs.npz',
        source=np.fromfile(source/'frames.rgb', np.uint8).reshape(-1, 72, 128, 3),
        compact=np.load(source/'states.npy'), states=np.load(source/'five-states.npy'))
    flat = ROOT/'.tmp/flat-disk-1005';target = destination/'interrupted-flat';target.mkdir()
    for name in ('conversion.json', 'compact-reuse.json'):
        shutil.copyfile(flat/name, target/name)
    shutil.copyfile(flat.with_suffix('.log'), target/'conversion.log')
    states = np.load(flat/'work/five-states.npy')
    ready = np.all(states[:, 3840:3936] == 1, axis=1) & np.all(states[:, 4512:] == 1, axis=1)
    count = int(ready.sum());assert ready[:count].all() and not ready[count:].any()
    np.savez_compressed(target/'partial-five-states.npz', states=states[:count])
    (target/'attempt.json').write_text(json.dumps(dict(date='2026-10-14', requested_frames=1005,
        complete_prepared_host_rows=count, stopped_by_user_steering=True, trd_created=False,
        complete_disk_playback=False, decision='User rejected flat fills and requested comprehensive source-line drawing.',
        encoder_commit='96fcec79', original_uncommitted_build_wrapper_not_snapshotted=True,
        equivalent_reproducer='build_disk.py --image-policy flat with the original recorded arguments',
        source_rgb_sha256=sha(flat/'work/frames.rgb'), source_input_cache='../capacity-1005/cache-inputs.npz'),
        indent=2)+'\n', encoding='utf-8', newline='\n')
    # Exact six-frame source/model snapshots for both visual review thresholds.
    for name in ('lineart-review', 'lineart-review-strict'):
        review = HERE/name
        if not (review/'producer-sources').exists():
            (review/'producer-sources').mkdir()
            for filename, path in (('lineart_colour.py', ROOT/'toolkit/lineart_colour.py'), ('lineart_probe.py', HERE/'lineart_probe.py')):
                shutil.copyfile(path, review/'producer-sources'/filename)
        seal(review)
    for directory in destination.iterdir():
        print(directory.name, seal(directory))


if __name__ == '__main__':main()
