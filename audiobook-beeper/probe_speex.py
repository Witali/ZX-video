"""Full-excerpt Speex audition; host measurements are not a Z80 decoder proof.

The reference keeps its original clock, gain and all samples. Codec latency
is disclosed as a constant integer offset, never a time stretch. The extra
silent frame flushes the codec so alignment cannot discard the source tail.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import wave

import numpy as np

from assess_snr import FILTER, ratio
from probe_dense_codecs import filtered
from lpc_preload import encode_ima
from ima_codec import decode, require_unclipped
from verify_pcm import save


def wav16(path, samples):
    with wave.open(str(path), 'wb') as w:
        w.setparams((1, 2, 8000, 0, 'NONE', 'not compressed'))
        w.writeframes(np.asarray(samples, dtype='<i2').tobytes())


def ogg_packets(blob):
    """Read laced packets, including packets continued across Ogg pages."""
    offset = 0
    partial = bytearray()
    packets = []
    while offset < len(blob):
        assert blob[offset:offset+5] == b'OggS\0'
        count = blob[offset+26]
        lacing = blob[offset+27:offset+27+count]
        position = offset+27+count
        for size in lacing:
            partial.extend(blob[position:position+size])
            position += size
            if size < 255:
                packets.append(bytes(partial))
                partial.clear()
        assert position <= len(blob)
        offset = position
    assert not partial
    assert packets[0].startswith(b'Speex   ')
    return packets


def aligned(source, decoded):
    """A reported constant codec delay only; no gain or sample-rate fitting."""
    n = len(source)
    delays = range(0, min(320, len(decoded)-n)+1)
    edge = 800
    target = source[edge:-edge].astype(float)
    scores = [(float(np.mean((decoded[d+edge:d+n-edge]-target)**2)), d)
              for d in delays]
    _, delay = min(scores)
    return decoded[delay:delay+n].copy(), delay


def quality(reference, actual, ffmpeg):
    ref = filtered(reference.astype(float)/32768, ffmpeg)
    signal = filtered(actual.astype(float)/32768, ffmpeg)
    assert len(ref) == len(signal)
    edge = 4410
    ref, signal = ref[edge:-edge], signal[edge:-edge]
    error = signal-ref
    windows = []
    for start in range(0, len(ref)-44100+1, 44100):
        x, e = ref[start:start+44100], error[start:start+44100]
        windows.append(dict(start_seconds=.1+start/44100,
                            reference_rms=float(np.sqrt(np.mean(x*x))),
                            snr_db=ratio(x, e)))
    return dict(filtered_snr_db=ratio(ref, error),
                raw_pcm16_snr_db=ratio(reference.astype(float), actual.astype(float)-reference),
                peak_abs_pcm16_error=int(np.max(abs(actual.astype(np.int32)-reference))),
                windows=windows)


def run(source_path, out, ffmpeg):
    out.mkdir(parents=True, exist_ok=False)
    with wave.open(str(source_path), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 1, 8000)
        raw = w.readframes(w.getnframes())
    source = (np.frombuffer(raw, 'u1').astype(np.int32)-128)*256
    assert len(source) % 160 == 0 and np.all(source[-128:] == 0)
    wav16(out/'original-preview.wav', source)
    encoder_input = np.r_[source, np.zeros(160, dtype=np.int32)].astype('<i2').tobytes()
    base = [ffmpeg, '-v', 'error', '-nostdin']
    rows = []
    for bitrate in (8000, 11000, 15000, 18200, 24600):
        name = f'speex-{bitrate}'
        command = base + ['-f', 's16le', '-ar', '8000', '-ac', '1', '-i', '-',
                          '-c:a', 'libspeex', '-b:a', str(bitrate), '-compression_level', '10',
                          '-frames_per_packet', '1', '-vad', '0', '-dtx', '0', '-f', 'ogg', '-']
        encoded = subprocess.run(command, input=encoder_input, capture_output=True, check=True).stdout
        (out/(name+'.spx.gz')).write_bytes(gzip.compress(encoded, mtime=0))
        packets = ogg_packets(encoded)
        header, payload = packets[0], packets[2:]
        assert struct.unpack_from('<i', header, 36)[0] == 8000
        assert struct.unpack_from('<i', header, 40)[0] == 0  # narrowband
        assert struct.unpack_from('<i', header, 52)[0] == bitrate
        assert struct.unpack_from('<i', header, 64)[0] == 1
        mode = payload[0][0] >> 3
        frame_bits = {3:160, 4:220, 5:300, 6:364, 7:492}[mode]
        assert all(p[0] >> 3 == mode and len(p) == (frame_bits+7)//8 for p in payload)
        # A proposed byte-aligned stream needs no per-frame lengths in CBR.
        # Count a fixed 32-byte header, plus EVERY frame including the flush.
        packed = b''.join(payload)
        (out/(name+'.frames.gz')).write_bytes(gzip.compress(packed, mtime=0))
        for decoder in ('libspeex', 'speex'):
            restored = subprocess.run(base + ['-c:a', decoder, '-i', '-', '-f', 's16le', '-'],
                                      input=encoded, capture_output=True, check=True).stdout
            decoded = np.frombuffer(restored, '<i2').astype(np.int32)
            pcm, delay = aligned(source, decoded)
            trial = name+'-'+decoder
            wav16(out/(trial+'-preview.wav'), pcm)
            row = dict(name=trial, bitrate_bps=bitrate, decoder=decoder, mode=mode,
                       samples=len(source), decoded_samples_before_alignment=len(decoded),
                       constant_latency_removed_samples=delay, latency_seconds=delay/8000,
                       encoder_complexity=10, vbr=False, vad=False, dtx=False,
                       frame_bits=frame_bits, frames=len(payload), flush_input_samples=160,
                       ogg_bytes=len(encoded), payload_bytes=len(packed), framing_allowance_bytes=32,
                       proposed_storage_bytes=len(packed)+32,
                       pcm16_to_codec_ratio=2*len(source)/(len(packed)+32),
                       pcm16_to_ogg_ratio=2*len(source)/len(encoded),
                       compressed_sha256=hashlib.sha256(encoded).hexdigest(),
                       native_z80_tested=False, integrated_pdm_tested=False,
                       codec=quality(source, pcm, ffmpeg))
            # Reproduce the existing startup IMA encoder. No expensive PC beam
            # search is substituted for work that would have to run on the Z80.
            target = np.clip((pcm+32768)>>8, 0, 255).astype('u1')
            target[-128:] = 128
            try:
                ima = encode_ima(target)
                row['ima_saturation_guard'] = require_unclipped(ima)
                restored_ima, indices = decode(ima)
                assert (int(restored_ima[-1]), int(indices[-1])) == (0, 0)
                row['after_ima'] = quality(source, restored_ima, ffmpeg)
                (out/(trial+'.ima.gz')).write_bytes(gzip.compress(ima, mtime=0))
                wav16(out/(trial+'-ima-preview.wav'), restored_ima)
            except (ValueError, AssertionError) as error:
                row['ima_guard_rejected'] = str(error)
            rows.append(row)
            print(json.dumps({k: row[k] for k in ('name', 'constant_latency_removed_samples',
                  'pcm16_to_codec_ratio')} | {'codec_snr_db':row['codec']['filtered_snr_db'],
                  'after_ima_snr_db':row.get('after_ima', {}).get('filtered_snr_db'),
                  'ima_guard_rejected':row.get('ima_guard_rejected')}), flush=True)
    save(out/'report.json', dict(scope=__doc__, date='2026-10-03', complete=True,
         source_pcm8_sha256=hashlib.sha256(raw).hexdigest(), samples=len(source),
         seconds=len(source)/8000, pcm16_denominator_bytes=2*len(source), filter=FILTER,
         end_to_end_pdm_20db_gate_verified=False, rows=rows,
         ffmpeg_version=subprocess.run([ffmpeg, '-version'], capture_output=True,
                                       check=True, text=True).stdout.splitlines()[0]))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--ffmpeg', required=True)
    args = p.parse_args()
    run(args.source, args.output, args.ffmpeg)
