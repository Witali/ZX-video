"""Measure lossless control storage; this is not a native AY/player format."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zlib

import numpy as np

HERE = Path(__file__).resolve().parent
CORE = HERE.parents[1]
sys.path.insert(0, str(CORE))
sys.path.insert(0, str(CORE.parent / 'toolkit'))
import experimental_six_voice as synth
import quality
from support import hidden_startupinfo
from zx0_codec import decompress as unzx0

HEADER = struct.Struct('<4sBBHIIIdfHBB')  # 36 bytes, including renderer settings.
LAYOUTS = ('packed_rows', 'columnar', 'columnar_delta')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def pack(c, layout):
    """Keep muted-voice periods and noise clocks too: they affect later phase."""
    if layout == 'packed_rows':
        rows = []
        for t in range(len(c['periods'])):
            value = int(c['noise_periods'][t]) << 120
            for ch in range(6):
                word = (int(c['periods'][t, ch]) | int(c['volumes'][t, ch]) << 12
                        | int(c['shapes'][t, ch]) << 16 | int(c['modes'][t, ch]) << 18)
                value |= word << (20 * ch)
            rows.append(value.to_bytes(16, 'little'))
        return b''.join(rows)
    p = c['periods'].astype(np.int64)
    command = c['volumes'] | c['shapes'] << 4 | c['modes'] << 6
    noise = c['noise_periods']
    if layout == 'columnar_delta':
        p = (p - np.vstack((np.zeros((1, 6), dtype=int), p[:-1]))) & 4095
        command = np.bitwise_xor(command, np.vstack((np.zeros((1, 6), dtype=np.uint8), command[:-1])))
        noise = np.bitwise_xor(noise, np.r_[np.uint8(0), noise[:-1]])
    return np.column_stack((p & 255, p >> 8, command, noise)).astype(np.uint8).T.copy().tobytes()


def unpack(data, ticks, layout):
    if layout == 'packed_rows':
        p = np.zeros((ticks, 6), dtype=np.uint16)
        command = np.zeros((ticks, 6), dtype=np.uint8)
        noise = np.zeros(ticks, dtype=np.uint8)
        if len(data) != ticks * 16:
            raise ValueError('wrong packed length')
        for t in range(ticks):
            value = int.from_bytes(data[t * 16:(t + 1) * 16], 'little')
            if value >> 125:
                raise ValueError('nonzero padding')
            noise[t] = value >> 120
            for ch in range(6):
                word = (value >> (20 * ch)) & 0xfffff
                p[t, ch] = word & 4095
                command[t, ch] = word >> 12
    else:
        rows = np.frombuffer(data, dtype=np.uint8).reshape(19, ticks).T
        p = rows[:, :6].astype(np.uint16) | rows[:, 6:12].astype(np.uint16) << 8
        command, noise = rows[:, 12:18].copy(), rows[:, 18].copy()
        if layout == 'columnar_delta':
            p = (np.cumsum(p, axis=0, dtype=np.uint32) & 4095).astype(np.uint16)
            command = np.bitwise_xor.accumulate(command, axis=0)
            noise = np.bitwise_xor.accumulate(noise)
    c = dict(periods=p, volumes=command & 15, shapes=(command >> 4) & 3,
             modes=command >> 6, noise_periods=noise)
    if synth.validate(c) != ticks:
        raise ValueError('wrong decoded tick count')
    return c


def read_stream(stream):
    """Decode the actual saved bytes and model metadata independently."""
    magic, layout_id, flags, hz, ticks, clock, rate, gain, morph, bandwidth, oversample, version = HEADER.unpack_from(stream)
    assert magic == b'S6P1' and version == 1 and hz == 50
    assert clock == synth.CLOCK and rate == synth.OUTPUT_RATE and flags & 3 == 3
    layout = LAYOUTS[layout_id]
    codec = flags >> 2
    position = HEADER.size
    chunks = {k: [] for k in ('periods', 'volumes', 'shapes', 'modes', 'noise_periods')}
    while position < len(stream):
        size, length = struct.unpack_from('<HH', stream, position)
        position += 4
        coded = stream[position:position + length]
        assert len(coded) == length
        position += length
        decoded = (zlib.decompress(coded) if codec == 1 else
                   lzma.decompress(coded) if codec == 2 else unzx0(coded, limit=size))
        assert len(decoded) == size
        row_size = 16 if layout == 'packed_rows' else 19
        assert size % row_size == 0
        controls = unpack(decoded, size // row_size, layout)
        for k in chunks:
            chunks[k].append(controls[k])
    assert position == len(stream)
    controls = {k: np.concatenate(v) for k, v in chunks.items()}
    assert synth.validate(controls) == ticks
    return controls, gain, dict(transition_ms=morph, output_bandwidth_hz=bandwidth,
                               aligned_triangle=bool(flags & 1), compensate_dc=bool(flags & 2),
                               oversample=oversample)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--zx0', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('use a new output directory')
    source = CORE / 'analysis/six_voice_spectral/evidence'
    previous = json.loads((source / 'report.json').read_bytes())
    with np.load(source / 'selectable-controls.npz') as saved:
        controls = {k: saved[k] for k in saved.files}
    ticks = synth.validate(controls)
    assert previous['complete'] and ticks == 1500 and previous['update_hz'] == 50
    feedback = previous['results']['selectable']['feedback']
    options = feedback['render_options']
    assert options == previous['render_options'] and previous['output_rate_hz'] == 44100
    for name, digest in previous['producer_sources_sha256_lf'].items():
        assert sha((CORE / name).read_bytes().replace(b'\r\n', b'\n')) == digest, name
    args.output.mkdir(parents=True)

    def header(layout, codec):
        flags = int(options['aligned_triangle']) | int(options['compensate_dc']) << 1 | codec << 2
        return HEADER.pack(b'S6P1', LAYOUTS.index(layout), flags, 50, ticks, previous['clock_hz'],
                           previous['output_rate_hz'], feedback['voice_gain'], options['transition_ms'],
                           int(options['output_bandwidth_hz']), previous['oversample'], 1)

    def compressed(data, codec, temporary):
        if codec == 'deflate':
            coded = zlib.compress(data, 9)
            decoded = zlib.decompress(coded)
        elif codec == 'xz':
            coded = lzma.compress(data, preset=6)
            decoded = lzma.decompress(coded)
        else:
            src, dst = temporary / 'input.raw', temporary / 'output.zx0'
            src.write_bytes(data)
            subprocess.run([str(args.zx0.resolve()), '-f', str(src), str(dst)],
                           check=True, capture_output=True, startupinfo=hidden_startupinfo())
            coded = dst.read_bytes()
            decoded = unzx0(coded, limit=len(data))
        assert decoded == data, codec
        return coded, decoded

    results = []
    raw_results = []
    with tempfile.TemporaryDirectory(dir=args.output) as folder:
        temporary = Path(folder).resolve()
        for layout in LAYOUTS:
            raw = pack(controls, layout)
            back = unpack(raw, ticks, layout)
            assert all(np.array_equal(back[k], controls[k]) for k in controls)
            raw_results.append(dict(layout=layout, payload_bytes=len(raw), file_bytes=HEADER.size + len(raw)))
            for block_ticks in (1500, 50):
                for codec_id, codec in enumerate(('deflate', 'xz', 'zx0'), start=1):
                    stream = bytearray(header(layout, codec_id))
                    recovered = {k: [] for k in controls}
                    blocks = []
                    for start in range(0, ticks, block_ticks):
                        chunk = {k: v[start:start + block_ticks] for k, v in controls.items()}
                        data = pack(chunk, layout)
                        coded, decoded = compressed(data, codec, temporary)
                        stream += struct.pack('<HH', len(data), len(coded)) + coded
                        restored = unpack(decoded, len(chunk['periods']), layout)
                        for k in controls:
                            recovered[k].append(restored[k])
                        blocks.append(dict(raw_bytes=len(data), compressed_bytes=len(coded)))
                    recovered = {k: np.concatenate(v) for k, v in recovered.items()}
                    assert all(np.array_equal(recovered[k], controls[k]) for k in controls)
                    filename = f'{layout}-{block_ticks}.{codec}'
                    (args.output / filename).write_bytes(stream)
                    recovered, replay_gain, replay_options = read_stream((args.output / filename).read_bytes())
                    assert all(np.array_equal(recovered[k], controls[k]) for k in controls)
                    assert replay_gain == feedback['voice_gain']
                    assert replay_options == dict(options, oversample=previous['oversample'])
                    row = dict(layout=layout, codec=codec, block_ticks=block_ticks, blocks=blocks,
                               file=filename, file_bytes=len(stream), header_bytes=HEADER.size + 4 * len(blocks),
                               sha256=sha(stream), all_1500_controls_exact=True,
                               bytes_per_second=len(stream) / 30,
                               minute_bytes_linear_estimate=len(stream) * 2,
                               hour_bytes_linear_estimate=len(stream) * 120)
                    results.append(row)
                    print(json.dumps({k: row[k] for k in ('layout', 'codec', 'block_ticks', 'file_bytes')}), flush=True)
        # One full waveform replay suffices after every representation recovers
        # every control exactly. Use the stored gain/settings, never source PCM.
        replay = temporary / 'replay.wav'
        quality.write_wav(replay, synth.render(recovered, replay_gain, **replay_options), 44100)
        assert replay.read_bytes() == (source / 'six-voice-preview.wav').read_bytes()
    report = dict(complete=True, date='2026-10-13', seconds=30, ticks=ticks, update_hz=50,
                  hypothetical_model=True, native_ay_format=False, native_player_implemented=False,
                  native_decode_timing_verified=False, no_source_pcm_in_stream=True,
                  all_controls_exact=True, full_1323000_sample_wav_replay_exact=True,
                  source_controls_sha256=sha((source / 'selectable-controls.npz').read_bytes()),
                  source_wav_sha256=sha((source / 'six-voice-preview.wav').read_bytes()),
                  npz_file_bytes=(source / 'selectable-controls.npz').stat().st_size,
                  wav_file_bytes=(source / 'six-voice-preview.wav').stat().st_size,
                  tight_bitstream_payload_lower_size=(ticks * 125 + 7) // 8,
                  raw=raw_results, compressed=results,
                  encoder_sha256=sha(args.zx0.read_bytes()), encoder_mode='optimal ZX0 v2',
                  python_version=sys.version, numpy_version=np.__version__,
                  producer_sources_sha256_lf={name: sha(path.read_bytes().replace(b'\r\n', b'\n')) for name, path in
                      [('measure.py', Path(__file__)), ('zx0_codec.py', CORE.parent / 'toolkit/zx0_codec.py')]},
                  model_producer_sources_sha256_lf=previous['producer_sources_sha256_lf'],
                  extrapolation='Linear scaling of this 30-second excerpt including repeated headers; other audio was not measured.',
                  excluded='Synthesizer/player code, disk directory/sector padding, and physical-chip implementation.')
    (args.output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
