"""Experimental G.726-16 codec audition; no TRD or real-time player is built."""
import argparse
from pathlib import Path
import math
import subprocess
import time
import wave

import numpy as np
from g726.codec import Codec, build_host, ffmpeg_decode, ffmpeg_encode, pack, save, sha


def write_pcm(path, pcm):
    with wave.open(str(path), 'wb') as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(8000)
        stream.writeframes(np.asarray(pcm, dtype='<i2').tobytes())


def measure(pcm, decoded, ffmpeg):
    """Codec error only, with exactly matching 8-kHz boundaries and no fitting."""
    from convert_mulaw_audio import filter_signal, STABLE_FILTER
    from ima_player import CPU_CLOCK
    def ratio(reference, error):
        signal_power = float(np.mean(reference*reference))
        noise_power = float(np.mean(error*error))
        # Zero-energy signal or exact reconstruction has no finite dB ratio.
        return 10*math.log10(signal_power/noise_power) if signal_power and noise_power else None
    reference = pcm.astype(float) / 32768
    output = decoded.astype(float) / 32768
    raw = ratio(reference, output-reference)
    times = np.arange(len(pcm)+1, dtype=float) * (CPU_CLOCK/8000)
    ref = filter_signal((reference+1)/2, times, ffmpeg, 768000)
    out = filter_signal((output+1)/2, times, ffmpeg, 768000)
    cut = slice(4410, -4410) if len(ref)>8820 else slice(None)
    return dict(raw_pcm_snr_db=raw, filtered_codec_snr_db=ratio(ref[cut], out[cut]-ref[cut]),
                filter=STABLE_FILTER, integration_rate_hz=768000,
                excluded_edge_seconds=.1 if len(ref)>8820 else 0,
                delay_fit=False, gain_fit=False, pdm_included=False,
                scope='Codec-only PCM16; fixed 8000-Hz clock. Not end-to-end beeper SNR.')


def convert(source, out, ffmpeg, seconds=60, library=None):
    if not math.isfinite(seconds) or seconds<=0:
        raise ValueError('seconds must be finite and positive')
    source, out = Path(source).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    # FFmpeg inserts its band-limited resampler when the input rate differs.
    # No loudness normalization/fade: retain the waveform for a fair codec test.
    run = subprocess.run([str(ffmpeg), '-v', 'error', '-nostdin', '-i', str(source),
        '-map', '0:a:0', '-t', str(seconds), '-ac', '1', '-ar', '8000', '-f', 's16le', '-'],
        capture_output=True, check=True)
    pcm = np.frombuffer(run.stdout, '<i2').copy()
    if not len(pcm):
        raise ValueError('No decodable audio')
    original_count = len(pcm)
    padding = (-len(pcm)) % 4
    pcm = np.pad(pcm, (0, padding), mode='edge')
    library = Path(library) if library else build_host(out/'host', 3)
    codec = Codec(library)
    started = time.perf_counter()
    codes = codec.encode(pcm)
    payload = pack(codes)
    decoded, _ = codec.decode(codes)
    duration = time.perf_counter()-started
    assert payload == ffmpeg_encode(pcm, ffmpeg)
    np.testing.assert_array_equal(decoded, ffmpeg_decode(payload, ffmpeg))
    write_pcm(out/'source-preview.wav', pcm)
    write_pcm(out/'decoded-preview.wav', decoded)
    (out/'soundtrack.g726').write_bytes(payload)
    report = dict(codec='G.726-16 uniform PCM', input=str(source), input_sha256=sha(source),
        pcm_reference_bits=16, sample_rate_hz=8000, bitrate=16000,
        original_samples=original_count, padding_samples=padding, samples=len(pcm),
        duration_seconds=len(pcm)/8000, payload_bytes=len(payload),
        payload_compression_ratio=pcm.nbytes/len(payload), header_bytes=0,
        packing='Four 2-bit codes per byte, MSB first; headerless FFmpeg g726 format',
        source_wav_sha256=sha(out/'source-preview.wav'), payload_sha256=sha(out/'soundtrack.g726'),
        decoded_wav_sha256=sha(out/'decoded-preview.wav'), host_library_sha256=sha(library),
        core_source_sha256=sha(Path(__file__).parent/'g726/core.c'),
        ffmpeg_sha256=sha(ffmpeg), standard_encoder_matches_ffmpeg=True,
        every_decoded_sample_matches_ffmpeg=True, host_encode_and_decode_seconds=duration,
        quality=measure(pcm, decoded, ffmpeg), native_pdm_qualified=False,
        scope='PC codec audition. No TRD generated; Z80 timing is a separate measured gate.')
    save(out/'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--outdir', type=Path, required=True)
    parser.add_argument('--ffmpeg', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=60)
    parser.add_argument('--library', type=Path, help='Use an already compiled g726 host library')
    args = parser.parse_args()
    report = convert(args.input, args.outdir, args.ffmpeg, args.seconds, args.library)
    print(f"{report['duration_seconds']:.3f} s, {report['payload_bytes']} bytes, 8:1 payload compression")
    print(f"Codec SNR: {report['quality']['filtered_codec_snr_db']} dB; see {args.outdir/'report.json'}")
    print('Experimental codec audition only; no real-time G.726 TRD player.')


if __name__ == '__main__':
    main()
