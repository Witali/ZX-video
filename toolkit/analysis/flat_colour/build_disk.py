"""Build the solid/neutral-contour source prefix with unchanged continuous AY.

Reuse the earlier byte-authenticated coarse RGB preparation, but regenerate
flat colours, native packets, disk allocation and full Fuse proofs. Neither
the audio optimizer nor native player instructions are changed.
"""
import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit/analysis/attribute_pattern'))
import rebuild


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--flat-cache', type=Path)
    parser.add_argument('--image-cache', type=Path)
    parser.add_argument('--image-policy', choices=('flat', 'lineart'), default='lineart')
    args, remaining = parser.parse_known_args()
    original_main = rebuild.build_prefix.converter.main
    def selected(arguments):
        arguments = list(arguments)
        arguments[arguments.index('--prefix')+1] = 'ZX-video-sea-foam-'+args.image_policy
        image_options = ['--colour-policy', args.image_policy]
        if args.image_policy == 'flat':image_options += ['--colour-contours']
        return original_main([*arguments, *image_options])
    rebuild.build_prefix.converter.main = selected
    if args.flat_cache and (args.image_cache or args.image_policy != 'flat'):
        raise ValueError('--flat-cache requires flat policy without --image-cache')
    cache = args.image_cache or args.flat_cache
    if cache:
        import numpy as np
        import flat_colour
        import lineart_colour
        module = flat_colour if args.image_policy == 'flat' else lineart_colour
        saved = json.loads((cache/'video-quality.json').read_bytes())
        comparison = saved['colour_comparison']
        assert comparison['parameters'] == module.PARAMETERS
        assert saved['colour_policy'] == args.image_policy
        assert comparison['dither'] == 'none' and comparison['contours']
        if args.image_policy == 'flat':assert comparison['vision'] == 'none'
        source = np.fromfile(cache/'work/frames.rgb', np.uint8).reshape(-1, 72, 128, 3)
        states = np.load(cache/'work/five-states.npy')
        assert states.shape == (len(source), 4608) and states.dtype == np.uint8
        assert len(saved['frame_mse']) == len(source)
        original_fit = module.encode
        cursor = 0
        def cached(image, previous=None, previous_image=None, **settings):
            nonlocal cursor
            index = cursor;cursor += 1
            if index >= len(source):return original_fit(image, previous, previous_image, **settings)
            assert settings == (dict(dither='none', contours=True, vision='none')
                if args.image_policy == 'flat' else {})
            assert np.array_equal(image[12:84], source[index])
            if index:
                assert previous == states[index-1].tobytes()
                assert np.array_equal(previous_image[12:84], source[index-1])
            return states[index].tobytes()
        module.encode = cached
    sys.argv = [sys.argv[0], *remaining]
    rebuild.main()


if __name__ == '__main__':main()
