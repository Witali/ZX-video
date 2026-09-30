"""Build one measured CB41 volume set and report exact cold-boot disk capacity.

Reuse measured streams without another compression sweep. The retained FAP3
input supplies AY and legacy bootstrap scaffolding only; CB41 supplies every
runtime image packet and both stored screen histories. No cadence claim.
"""
import argparse
import json
from pathlib import Path

import numpy as np

from build_five_level_test_trd import save
from build_integrated_bootstrap import check_cold
from cell_codebook_player import Builder
from prepare_cell_codebook_movie import file_sha, sha
from row_dictionary_video import reference_tables


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'measurements', 'source-fap3', 'options', 'zx0', 'lzsa', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    prepared = json.loads(a.prepared.read_bytes())
    measured = json.loads(a.measurements.read_bytes())
    assert measured['preparation_sha256'] == file_sha(a.prepared)
    assert measured['all_row_tables_fit'] and measured['all_audio_banks_fit']
    raw = a.source_fap3.read_bytes()
    assert sha(raw) == prepared['input_audio_fap3_sha256']
    options = json.loads(a.options.read_bytes())['contract']['options']
    options['startup_delta'] = False
    ends = [v['end'] for v in measured['volumes']]
    fingerprint = b'CB41FULL'+bytes.fromhex(sha(b''.join(bytes.fromhex(v['stream_sha256']) for v in measured['volumes'])))[:6]
    results = []
    for volume in measured['volumes']:
        part, start, end = volume['volume'], volume['start'], volume['end']
        folder = a.measurements.parent/f'volume-{part}'
        target = a.output/f'volume-{part}'
        target.mkdir(exist_ok=True)
        rows = json.loads((folder/'row-dictionary.json').read_bytes())
        with np.load(folder/'states.npz', allow_pickle=False) as cache:
            local = cache['states']
        first = max(0, start-2)
        assert len(local) == end-first
        # Only this volume's two histories and display range use this table.
        states = np.zeros((prepared['frames'],3840), dtype=np.uint8)
        states[first:end] = local
        cell = (folder/'codebook.raw').read_bytes()
        stream = (folder/'codebook.stream').read_bytes()
        assert sha(cell) == volume['raw_sha256'] and sha(stream) == volume['stream_sha256']
        blocks = [dict(raw_start=b['raw_start'], raw_end=b['raw_end'], decoded_bytes=b['decoded_bytes'],
                       compressed_bytes=b['compressed_bytes'], codec='lzsa2',
                       sha256=sha(cell[b['raw_start']:b['raw_end']]),
                       inplace_proof=b['proof'], inplace_layout=b['layout']) for b in volume['blocks']]
        with reference_tables(rows):
            builder = Builder(raw, states, a.zx0.resolve(), a.output/'zx0', row_dictionary=rows,
                lzsa=a.lzsa.resolve(), series_fingerprint=fingerprint, cell_raw=cell, cell_start=start, **options)
            builder.ends = ends
            builder.inplace_streams[start,end] = stream, blocks
            builder.resident_streams[start,end] = b'', (folder/'audio.ayh1').read_bytes()
            image, metadata = builder.volume(start, end, part)
            save(target/'metadata.json', metadata)
            result = dict(volume=part, start=start, end=end, frames=end-start,
                indexed_state_scope=[first,end], used_sectors=metadata['used_sectors'],
                free_sectors=metadata['free_sectors'], video_sectors=metadata['video_sectors'],
                overhead_sectors=metadata['used_sectors']-metadata['video_sectors'], fits=image is not None,
                stream_reused_byte_exact=True, actual_playback_measured=False)
            if image is not None:
                (target/'candidate.trd').write_bytes(image)
                result.update(trd_sha256=sha(image), dirty_cold=check_cold(image,metadata,builder.expected_banks))
            results.append(result)
            print(json.dumps({k:v for k,v in result.items() if k!='dirty_cold'}), flush=True)
    report = dict(complete=True, release=False, goal_achieved=False, scope=__doc__,
        preparation_sha256=file_sha(a.prepared), measurements_sha256=file_sha(a.measurements),
        all_volumes_fit=all(v['fits'] for v in results), volumes=results,
        independently_cold_checked=[v['volume'] for v in results if v['fits']],
        actual_playback_measured=False, source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
            for name in ('build_cell_codebook_movie.py','cell_codebook_player.py')})
    save(a.output/'capacity.json',report)


if __name__ == '__main__':
    main()
