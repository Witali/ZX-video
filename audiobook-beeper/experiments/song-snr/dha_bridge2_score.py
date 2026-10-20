"""Score a bridge2 codec trial only at its original physical8k samples.

Helper samples are charged as storage and then discarded by the decoder.
They never become a new reference, audio bandwidth, fitted clock or gain.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

from build_pdm import CPU_CLOCK, write_wav
from dha_host_score import direct_error
from ima_codec import decode
from study import filtered, metrics


HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trial', type=Path, default=HERE / 'evidence/dha-bridge2-pilot')
    parser.add_argument('--output', type=Path, default=HERE / 'evidence/dha-bridge2-quality-pilot')
    parser.add_argument('--scratch', type=Path, default=HERE.parents[3] / '.tmp/dha-bridge2-quality')
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    trial = json.loads((args.trial / 'report.json').read_bytes())
    count = trial['physical_samples']
    physical = np.fromfile(args.trial / 'source-physical-pcm16.bin', '<i2')
    decoded = np.fromfile(args.trial / 'decoded-physical-pcm16.bin', '<i2')
    coded = np.fromfile(args.trial / 'coded-targets-pcm16.bin', '<i2')
    coded_actual = np.fromfile(args.trial / 'decoded-coded-pcm16.bin', '<i2')
    assert len(physical) == len(decoded) == count and len(coded) == len(coded_actual) == 2*count
    np.testing.assert_array_equal(physical, coded[::2])
    np.testing.assert_array_equal(decoded, coded_actual[::2])
    source = (physical.astype('i4') // 256 + 128).astype('u1')
    np.testing.assert_array_equal(physical.astype('i4'), (source.astype('i4')-128)*256)
    packed = gzip.decompress((HERE / 'evidence/general/inputs/sea_foam.ima.gz').read_bytes())
    ima, _ = decode(packed)
    direct = np.fromfile(HERE / 'evidence/dha-host/sea_foam/decoded-pcm16.bin', '<i2')[:count]
    times = np.arange(count+1, dtype='f8') * (CPU_CLOCK/8000)
    wanted = filtered(source/256, times, args.ffmpeg, args.scratch)
    rows = []
    for name, values in (('IMA4', ima[:count]), ('DHA_direct', direct), ('DHA_bridge2', decoded)):
        actual = filtered((values.astype('f8')+32768)/65536, times, args.ffmpeg, args.scratch)
        row = dict(codec=name, samples=len(values), PCM16_sha256=sha(values.astype('<i2').tobytes()),
                   filtered=metrics(wanted, actual), unfiltered=direct_error(source, values))
        rows.append(row)
        write_wav(args.output / (name+'.wav'), actual*.5)
    report = dict(complete=True, measured_physical_samples=count, physical_rate_hz=8000,
                  measured_seconds=count/8000, full_song_samples=720384,
                  complete_song_measured=count == 720384,
                  original_physical_PCM16_sha256=sha(physical.tobytes()),
                  all_original_positions_exact_before_codec=True, even_decimation_exact_after_codec=True,
                  codec_file_bytes=trial['file_bytes'], coded_samples_charged=trial['coded_samples'],
                  all_helpers_and_headers_charged=True, rows=rows,
                  source_clock_gain_delay_or_bandwidth_fitted=False,
                  filter_intermediate_hz=768000, fixed_edges_seconds=.1,
                  scope='Original physical8k reference and ideal multilevel DAC only; partial pilot unless count equals720384. No PDM/player/timing or whole-song compression claim.',
                  release_accepted=False, producer_sha256=sha(Path(__file__).read_bytes()))
    (args.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    (args.output / 'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    artifacts = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                 for p in sorted(args.output.iterdir()) if p.is_file() and p.name != 'manifest.json'}
    (args.output / 'manifest.json').write_text(json.dumps(dict(artifact_files=artifacts), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(samples=count, seconds=count/8000,
                          ideal_filtered_SNR_dB={row['codec']: row['filtered']['snr_db'] for row in rows})))


if __name__ == '__main__':
    main()
