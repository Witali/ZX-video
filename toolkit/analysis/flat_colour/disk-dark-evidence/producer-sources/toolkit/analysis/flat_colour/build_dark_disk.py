"""Build the accuracy-guarded dark-fill prefix with unchanged native AY/player."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'toolkit/analysis/attribute_pattern'))
sys.path.insert(0, str(ROOT/'toolkit'))
import rebuild
import lineart_colour as line


def main():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument('--image-cache', type=Path, required=True)
    args, remaining = p.parse_known_args()
    saved = np.load(args.image_cache/'states.npz')
    source, states = saved['source'], saved['dark']
    proof = json.loads((args.image_cache/'images.json').read_bytes())
    digest = hashlib.sha256((ROOT/'toolkit/lineart_colour.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()
    assert proof['complete_image_contracts'] and proof['frames'] == len(source) == len(states)
    assert proof['producer_sha256'] == digest and states.shape == (len(source), 4608)
    cursor = 0
    def cached(image, previous=None, previous_image=None, *, dark_fills=False):
        nonlocal cursor
        index = cursor;cursor += 1
        assert dark_fills and index < len(source)
        np.testing.assert_array_equal(image[12:84], source[index])
        if index:
            assert previous == states[index-1].tobytes()
            np.testing.assert_array_equal(previous_image[12:84], source[index-1])
        return states[index].tobytes()
    line.encode = cached
    original_main = rebuild.build_prefix.converter.main
    def selected(arguments):
        arguments = list(arguments)
        arguments[arguments.index('--prefix')+1] = 'ZX-video-sea-foam-lineart-dark'
        return original_main([*arguments, '--colour-policy', 'lineart', '--lineart-dark-fills'])
    rebuild.build_prefix.converter.main = selected
    sys.argv = [sys.argv[0], *remaining]
    rebuild.main()
    assert cursor == len(source)


if __name__ == '__main__':main()
