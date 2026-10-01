"""Measure CB41 output work on the saved palette/contrast windows.

Component timings only: excludes LZSA2, packet copies, paging, IRQ/ULA,
TR-DOS and drive latency. This does not verify a playback deadline.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from generic_cell_codebook import representation
from prepare_cell_codebook_movie import file_sha, sha
from verify_cell_codebook_z80 import Harness, independent, packets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True)
    parser.add_argument('--variants', nargs='+', default=['baseline', 'endpoints'])
    args = parser.parse_args()
    report_path = args.work/'report.json'
    quality = json.loads(report_path.read_bytes())
    files = {row['file']: row['sha256'] for row in quality['artifacts']}
    results = []
    for window in quality['windows']:
        folder = args.work/f"window-{window['start']}"
        input_path = folder/'input.npz'
        assert file_sha(input_path) == files[input_path.relative_to(args.work).as_posix()]
        with np.load(input_path, allow_pickle=False) as data:
            for name in args.variants:
                frames = data[name]
                start = len(window['seed_frames'])
                rep = representation(frames, start, len(frames))
                assert rep['raw_sha256'] == window['compression'][name]['raw_sha256']
                payloads, book, dictionary = packets(rep['raw'])
                harness = Harness(book, bytes.fromhex(rep['rows']['tables_hex']), rep['initial'], dictionary)
                expected = {7: rep['initial'][:6912], 5: rep['initial'][6912:]}
                samples = []
                for i, payload in enumerate(payloads):
                    bank = 7 if i % 2 == 0 else 5
                    target = 0xc0 if bank == 7 else 0x40
                    before = expected.copy()
                    row = harness.run('draw', payload, 0x6400, target)
                    expected[bank] = bytes(harness.c.banks[bank][:6912])
                    assert sha(expected[bank]) == rep['screen_sha256'][i]
                    assert bytes(harness.c.banks[12-bank][:6912]) == before[12-bank]
                    if i in (0, len(payloads)-1):
                        row['independent'] = independent(harness, payload, 0x6400, target, before, expected, row['tstates'])
                    samples.append(dict(frame=window['start']+i, **row))
                result = dict(start=window['start'], variant=name, frames=samples,
                    all_screens_exact=True, all_instruction_timings_exact=True,
                    mean_tstates=float(np.mean([r['tstates'] for r in samples])),
                    maximum_tstates=max(r['tstates'] for r in samples),
                    loader_tstates=harness.loader['tstates'],
                    code_sha256=sha(b''.join(b for _, b in harness.regions)))
                results.append(result)
                print(json.dumps({k:v for k,v in result.items() if k != 'frames'}), flush=True)
    output = dict(complete=True, release=False, scope=__doc__,
        quality_report_sha256=file_sha(report_path), results=results,
        source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')))
    (args.work/'native.json').write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')


if __name__ == '__main__':
    main()
