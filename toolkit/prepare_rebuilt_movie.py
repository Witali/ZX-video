"""Assemble hashed inputs for packaging a rebuilt player and verified disks.

Reuse the exact source video and AY stages; keep their original hashes.
The final package tool independently checks the new disks, CPU/Fuse traces,
audio comparison and strict six-field cadence before publishing anything.
"""
import argparse
import copy
import json
from pathlib import Path
import shutil

from build_full_movie import digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source_build', type=Path)
    p.add_argument('--disks', type=Path, required=True)
    p.add_argument('--comparison', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    manifest = json.loads((args.source_build / 'manifest.json').read_text())
    result = copy.deepcopy(manifest)
    result['stages'] = {}
    args.output.mkdir(parents=True, exist_ok=True)
    for stage in ('audio', 'video'):
        for name, expected in manifest['stages'][stage].items():
            src = args.source_build / name
            if digest(src) != expected:
                raise ValueError(f'changed source artifact: {name}')
            dst = args.output / name; dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
        result['stages'][stage] = manifest['stages'][stage]
    preview = 'source/preview.mp4'
    shutil.copyfile(args.source_build / preview, args.output / preview)
    meta = json.loads((args.disks / 'build_metadata.json').read_text())
    names = ['build_metadata.json', 'PLAYER.C.bin', *(v['trd_name'] for v in meta['volumes'])]
    (args.output / 'disks').mkdir(exist_ok=True)
    for name in [*names, 'fuse_timing.json', 'cpu_validation.json']:
        shutil.copyfile(args.disks / name, args.output / 'disks' / name)
    result['stages']['disks'] = {f'disks/{name}': digest(args.output / 'disks' / name) for name in names}
    result['disk_settings'] = {key: meta['block_codec'][key] for key in
        ('max_volume_frames', 'minimum_planned_queue', 'separate_stored')}
    result['disk_settings']['store_over_bytes'] = meta['block_codec']['store_over_frame_bytes']
    for key in ('minimum_match', 'speed_over_frame_bytes', 'volume_end_frames', 'stored_frames'):
        result['disk_settings'][key] = meta['block_codec'].get(key, [] if key in ('volume_end_frames', 'stored_frames') else 0)
    if 'player_rebuild' in meta:
        result['disk_settings']['player_rebuild'] = meta['player_rebuild']
    shutil.copytree(args.comparison, args.output / 'comparison', dirs_exist_ok=True)
    (args.output / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(args.output.resolve())


if __name__ == '__main__':
    main()
