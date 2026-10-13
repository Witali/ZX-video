"""Rebuild the exact prefix while reusing its unchanged coarse preparation.

Only the host five-level selector changes. Validate all decoded RGB bytes
against an already qualified build before reusing its compact reference;
native encoding and complete Fuse verification still run from scratch.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import numpy as np

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit/analysis/sea_foam'))
import build_prefix


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--compact-cache', type=Path, required=True)
    parser.add_argument('--colour-cache', type=Path)
    parser.add_argument('--one-disk', action='store_true')
    args, remaining = parser.parse_known_args()
    cache = args.compact_cache
    saved = json.loads((cache/'conversion.json').read_bytes())
    rgb = np.fromfile(cache/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
    assert saved['input']['encoded_frames'] == len(rgb)
    compact = np.load(cache/'work/states.npy')
    assert compact.shape == (len(rgb), 3840) and compact.dtype == np.uint8
    def reused(images, directory, *, monochrome=False):
        count = len(images)
        assert not monochrome and count <= len(rgb) and np.array_equal(images, rgb[:count])
        np.save(directory/'states.npy', compact[:count])
        (directory.parent/'compact-reuse.json').write_text(json.dumps(dict(
            complete=True, every_source_rgb_byte_exact=True, frames=count,
            cache=str(cache.resolve()), cache_fully_qualified=bool(saved.get('timing_verified')),
            states_sha256=hashlib.sha256((cache/'work/states.npy').read_bytes()).hexdigest()),
            indent=2)+'\n', encoding='utf-8')
        print(f'Reused exact coarse preparation: {count} source RGB frames checked', flush=True)
        return compact[:count], {}
    build_prefix.converter.convert_frames = reused
    if args.colour_cache:
        import texture_colour
        cache_quality = json.loads((args.colour_cache/'video-quality.json').read_bytes())
        assert cache_quality['colour_comparison']['parameters'] == texture_colour.PARAMETERS
        cache_rgb = np.fromfile(args.colour_cache/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
        cache_states = np.load(args.colour_cache/'work/five-states.npy')
        assert cache_states.shape == (len(cache_rgb), 4608)
        assert len(cache_quality['frame_mse']) == len(cache_rgb)
        original_fit = texture_colour.encode;cursor = 0
        def reused_colour(image, reference, previous=None, previous_image=None):
            nonlocal cursor
            index = cursor;cursor += 1
            if index >= len(cache_rgb):return original_fit(image, reference, previous, previous_image)
            assert np.array_equal(image[12:84], cache_rgb[index])
            if index:assert previous == cache_states[index-1].tobytes()
            return cache_states[index].tobytes()
        texture_colour.encode = reused_colour
    if args.one_disk:
        import inspect
        import convert_cb41
        original_plan = convert_cb41.plan_volumes
        def single(*values, **options):
            bound = inspect.signature(original_plan).bind(*values, **options)
            bound.arguments['volume_cuts'] = [len(bound.arguments['frames'])]
            bound.arguments['target_volumes'] = None
            return original_plan(*bound.args, **bound.kwargs)
        convert_cb41.plan_volumes = single
    sys.argv = [sys.argv[0], *remaining]
    build_prefix.main()


if __name__ == '__main__':main()
