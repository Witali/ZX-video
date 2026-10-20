"""Compare DHA and frozen IMA on the identical uniform8k source clock.

Scores here use an ideal multilevel DAC. They do not include a one-bit output
adapter or claim a new ZX player. Neither codec receives a fitted level,
delay, clock, bandwidth or shortened source. PCM fallback is charged in full.
"""
import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import wave
import zlib

import numpy as np

from build_pdm import CPU_CLOCK, write_wav
from ima_codec import decode
from study import filtered, metrics


HERE = Path(__file__).resolve().parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pcm16(path):
    with wave.open(str(path), 'rb') as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, 2, 8000)
        return np.frombuffer(stream.readframes(stream.getnframes()), '<i2').copy()


def validate_container(path, source, decoded):
    data = path.read_bytes()
    assert data[:4] == b'DHAF' and struct.unpack_from('<HH', data, 4) == (1, 1572)
    assert zlib.crc32(data[:1568]) == struct.unpack_from('<I', data, 1568)[0]
    rate, channels, frame_size, samples = struct.unpack_from('<IHHQ', data, 8)
    assert (rate, channels, samples) == (8000, 1, len(source))
    position, index, sequence = 1572, 0, 0
    counts = [0, 0]
    sample_counts = [0, 0]
    payload_bits = [0, 0]
    while position < len(data):
        assert data[position:position+4] == b'DHF1'
        size, seq, count, channel, kind = struct.unpack_from('<IIHBB', data, position+4)
        bits = struct.unpack_from('<I', data, position+24)[0]
        assert seq == sequence and channel == 0 and kind in (0, 1)
        assert 0 < count <= frame_size and size >= 32 and position + size <= len(data)
        payload = data[position+32:position+size]
        assert zlib.crc32(data[position:position+28]+payload) == struct.unpack_from('<I', data, position+28)[0]
        if kind == 0:
            assert bits == count*16 and len(payload) == count*2
            expected = ((source[index:index+count].astype('i4')-128)*256).astype('<i2')
            assert payload == expected.tobytes()
            np.testing.assert_array_equal(decoded[index:index+count], expected)
        else:
            assert len(payload) == (bits+7)//8
        counts[kind] += 1
        sample_counts[kind] += count
        payload_bits[kind] += bits
        index += count
        position += size
        sequence += 1
    assert position == len(data) and index == len(source)
    return dict(file_bytes=len(data), model_sha256=sha(data[32:1056]), ans_sha256=sha(data[1056:1568]),
                frames=sum(counts), predictive_frames=counts[1], PCM16_fallback_frames=counts[0],
                predictive_samples=sample_counts[1], PCM16_fallback_samples=sample_counts[0],
                meaningful_payload_bits=sum(payload_bits),
                all_header_frame_CRCs_and_counts_exact=True, every_fallback_sample_matches_original=True)


def direct_error(source, actual):
    wanted = source.astype('f8')[800:-800]-128
    actual = actual.astype('f8')[800:-800]/256
    error = actual-wanted
    signal, noise = float(np.mean(wanted*wanted)), float(np.mean(error*error))
    return dict(snr_db=None if signal < 1e-24 else (None if noise == 0 else 10*math.log10(signal/noise)),
                bit_exact_after_edges=noise == 0, error_rms_PCM8_units=math.sqrt(noise),
                maximum_absolute_error_PCM8_units=float(np.max(np.abs(error))),
                scope='Original8kPCM, fixed100-ms edges, no fitted gain/delay/clock')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', default='sea_foam')
    parser.add_argument('--trial', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.scratch.mkdir(parents=True, exist_ok=True)
    inputs = HERE / 'evidence/general/inputs'
    source_path = inputs / (args.source+'.wav')
    with wave.open(str(source_path), 'rb') as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, 1, 8000)
        source = np.frombuffer(stream.readframes(stream.getnframes()), 'u1').copy()
    decoded_path = args.trial / 'decoded.wav'
    dha = pcm16(decoded_path)
    assert len(dha) == len(source)
    packed = gzip.decompress((inputs / (args.source+'.ima.gz')).read_bytes())
    ima, _ = decode(packed)
    assert len(ima) == len(source)
    container = validate_container(args.trial / 'audio.dhaf', source, dha)
    times = np.arange(len(source)+1, dtype='f8')*(CPU_CLOCK/8000)
    reference = filtered(source/256, times, args.ffmpeg, args.scratch)
    rows = []
    for name, values in (('IMA4', ima), ('DHA', dha)):
        actual = filtered((values.astype('f8')+32768)/65536, times, args.ffmpeg, args.scratch)
        row = dict(codec=name, samples=len(values), PCM16_sha256=sha(values.astype('<i2').tobytes()),
                   unfiltered=direct_error(source, values), filtered=metrics(reference, actual))
        rows.append(row)
        np.save(args.scratch / (args.source+'-'+name+'-ideal-actual.npy'), actual)
        write_wav(args.output / (name+'-ideal.wav'), actual*.5)
    report = dict(complete=True, source=args.source, source_samples=len(source), sample_rate=8000,
                  source_PCM8_sha256=sha(source.tobytes()), source_WAV_sha256=sha(source_path.read_bytes()),
                  DHA_WAV_sha256=sha(decoded_path.read_bytes()), DHA_file_sha256=sha((args.trial/'audio.dhaf').read_bytes()),
                  container=container, frozen_IMA4_bytes=len(packed), frozen_IMA4_sha256=sha(packed),
                  DHA_size_fraction_of_IMA4=container['file_bytes']/len(packed),
                  rows=rows, filter_intermediate_hz=768000, filter_output_hz=44100,
                  scope='Complete original uniform8k source, ideal multilevel DAC only; fixed100-ms edges and unchanged listening filter. No actual one-bit output or ZX timing/player claim.',
                  score_source_clock_fitted=False, gain_delay_or_bandwidth_fitted=False,
                  precision='DHA predictive mode returns PCM8 rounded into PCM16; fallback preserves originalPCM16',
                  training_overlap='Original DHA default model was fitted to a25kHz15s portion of this song; common-model trial must identify its separate training inputs.',
                  player_or_release_accepted=False, producer_sha256=sha(Path(__file__).read_bytes()))
    (args.output / 'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    (args.output / 'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    artifacts = {p.name: dict(bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                 for p in sorted(args.output.iterdir()) if p.is_file() and p.name != 'manifest.json'}
    (args.output / 'manifest.json').write_text(json.dumps(dict(artifact_files=artifacts), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(source=args.source, DHA_bytes=container['file_bytes'], IMA_bytes=len(packed),
                          fallback_frames=container['PCM16_fallback_frames'],
                          ideal_filtered_SNR_dB={row['codec']: row['filtered']['snr_db'] for row in rows})), flush=True)


if __name__ == '__main__':
    main()
