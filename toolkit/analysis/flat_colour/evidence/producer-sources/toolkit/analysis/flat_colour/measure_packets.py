"""Exact host screen roundtrips and compressed size; no native timing claim."""
import argparse
import json
from pathlib import Path
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'toolkit'))
from generic_cell_codebook import representation, row_sets
from convert_cb41 import pack_blocks
from probe_adaptive_block_codecs import ExternalCodec
from probe import WINDOWS, COUNT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--lzsa', type=Path, required=True)
    args = parser.parse_args()
    saved = np.load(args.evidence/'states.npz')
    baseline = np.load(args.baseline/'work/five-states.npy')
    codec = ExternalCodec('lzsa2', args.lzsa, args.lzsa, 'existing project encoder')
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for lo in WINDOWS:
            positions = np.flatnonzero((saved['indices'] >= lo) & (saved['indices'] < lo+COUNT))
            for name in (key for key in saved.files if key not in ('indices', 'source')):
                frames = np.concatenate([baseline[lo-2:lo], saved[name][positions]])
                try:
                    row_sets(frames)
                    result = representation(frames, 2, len(frames))
                    packed, blocks = pack_blocks(result['raw'], codec, Path(tmp))
                    rows.append(dict(window_start=lo, variant=name, complete=True,
                        frames=COUNT, rows=result['rows']['entries'],
                        raw_bytes=len(result['raw']), packed_bytes=len(packed),
                        full_host_screens_exact=result['full_host_screens_exact'],
                        raw_sha256=result['raw_sha256'], screen_sha256=result['screen_sha256'], blocks=blocks))
                except ValueError as error:
                    rows.append(dict(window_start=lo, variant=name, complete=False, error=str(error)))
                print(f'{lo} {name}: '+str(rows[-1].get('packed_bytes', rows[-1].get('error'))), flush=True)
    report = dict(scope='Six 16-frame windows, each with the same two previous qualified baseline screens. Actual LZSA2 exact decode and host CB41 screen roundtrip; not full-volume capacity or Z80/Fuse delivery timing.',
        player_instructions_changed=False, instruction_delta_tstates=0, windows=rows,
        totals={name:dict(complete=all(row['complete'] for row in rows if row['variant'] == name),
            packed_bytes=sum(row.get('packed_bytes', 0) for row in rows if row['variant'] == name),
            maximum_rows=max(row.get('rows', 0) for row in rows if row['variant'] == name))
            for name in (key for key in saved.files if key not in ('indices', 'source'))})
    (args.evidence/'packets.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['totals'], indent=2))


if __name__ == '__main__':main()
