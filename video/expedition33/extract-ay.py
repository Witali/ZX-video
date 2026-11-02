"""Extract authenticated port transactions from the retained native Fuse proof."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def extract(path, output):
    data = gzip.decompress(path.read_bytes())
    expected = '948a142c4709c65a92f672eb8a6f7d10d42be6d08c237bc33558e4caa9dd4476'
    digest = hashlib.sha256(data).hexdigest()
    assert digest == expected, 'Use the full qualification trace of the published disk'
    numbers = [int(line, 0) for line in data.splitlines()]
    samples = len(range(0, 6912, 13))
    widths = {100: 3 + samples, 102: 2, 101: 6, 111: 2, 103: 3, 104: 5,
              105: 5, 106: 1, 108: 1, 107: 1, 112: 2 + samples, 113: 1, 200: 1}
    events = {tag: [] for tag in widths}
    position = 0
    while position < len(numbers):
        tag = numbers[position]
        size = widths[tag]
        events[tag].append(numbers[position + 1:position + 1 + size])
        position += size + 1
    origin = events[111][0][0] // 70908 * 70908
    assert [r[0] // 70908 - origin // 70908 for r in events[111]] == [0, 11254, 19140]
    result = dict(trace_sha256=digest, starts=[r[0] - origin for r in events[111]],
        writes=[[r[0] - origin, r[3], r[4]] for r in events[105]],
        end_tstates=19140 * 70908)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result) + '\n')
    print('Authenticated full native AY trace:', len(result['writes']), 'writes including loop sample.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    extract(args.trace, args.output)
