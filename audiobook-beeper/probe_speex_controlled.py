"""Compare stock Speex API options and integer decoding on the full source.

No library algorithms are patched. Disabling the optional highpass and
perceptual enhancement is a supported API configuration, not a new codec.
The known 40+40 sample codec latency is removed; no fitted gain or timing.
"""
import argparse
import ctypes as c
import gzip
import hashlib
import json
from pathlib import Path
import struct
import wave

import numpy as np

from assess_snr import FILTER
from probe_speex import quality, wav16
from lpc_preload import encode_ima
from ima_codec import decode, require_unclipped
from verify_pcm import save


class Bits(c.Structure):
    _fields_ = [('chars', c.c_void_p)] + [(n, c.c_int) for n in
        ('nbBits', 'charPtr', 'bitPtr', 'owner', 'overflow', 'buf_size', 'reserved1')] + [('reserved2', c.c_void_p)]


class Speex:
    def __init__(self, path):
        self.lib = lib = c.CDLL(str(path.resolve()))
        ptr = c.c_void_p
        bp = c.POINTER(Bits)
        signatures = {
            'speex_lib_get_mode': (ptr, [c.c_int]),
            'speex_encoder_init': (ptr, [ptr]), 'speex_decoder_init': (ptr, [ptr]),
            'speex_encoder_ctl': (c.c_int, [ptr, c.c_int, ptr]),
            'speex_decoder_ctl': (c.c_int, [ptr, c.c_int, ptr]),
            'speex_encoder_destroy': (None, [ptr]), 'speex_decoder_destroy': (None, [ptr]),
            'speex_bits_init': (None, [bp]), 'speex_bits_destroy': (None, [bp]),
            'speex_bits_reset': (None, [bp]),
            'speex_bits_write': (c.c_int, [bp, ptr, c.c_int]),
            'speex_bits_read_from': (None, [bp, ptr, c.c_int]),
            'speex_encode_int': (c.c_int, [ptr, ptr, bp]),
            'speex_decode_int': (c.c_int, [ptr, bp, ptr]),
        }
        for name, (result, args) in signatures.items():
            fn = getattr(lib, name)
            fn.restype, fn.argtypes = result, args
        self.mode = lib.speex_lib_get_mode(0)
        assert self.mode

    def ctl(self, state, request, value=0, encoder=False):
        result = c.c_int(value)
        fn = self.lib.speex_encoder_ctl if encoder else self.lib.speex_decoder_ctl
        assert fn(state, request, c.byref(result)) == 0, request
        return result.value

    def encode(self, source, bitrate, highpass):
        lib = self.lib
        state = lib.speex_encoder_init(self.mode)
        assert state
        bits = Bits()
        lib.speex_bits_init(c.byref(bits))
        try:
            for request, value in ((18, bitrate), (16, 10), (44, highpass), (12, 0), (30, 0), (34, 0)):
                self.ctl(state, request, value, True)
            assert self.ctl(state, 19, encoder=True) == bitrate
            size = self.ctl(state, 3, encoder=True)
            latency = self.ctl(state, 39, encoder=True)
            assert (size, latency) == (160, 40)
            data = np.r_[source, np.zeros(size, dtype=np.int16)].astype('<i2')
            packets = []
            buffer = c.create_string_buffer(200)
            counts = []
            for offset in range(0, len(data), size):
                lib.speex_bits_reset(c.byref(bits))
                frame = data[offset:offset+size].copy()
                assert len(frame) == size
                assert lib.speex_encode_int(state, frame.ctypes.data, c.byref(bits)) == 1
                counts.append(bits.nbBits)
                length = lib.speex_bits_write(c.byref(bits), buffer, len(buffer))
                packets.append(buffer.raw[:length])
            assert len(set(counts)) == 1
            return packets, counts[0], latency
        finally:
            lib.speex_bits_destroy(c.byref(bits))
            lib.speex_encoder_destroy(state)

    def decode(self, packets, highpass, enhance):
        lib = self.lib
        state = lib.speex_decoder_init(self.mode)
        assert state
        bits = Bits()
        lib.speex_bits_init(c.byref(bits))
        try:
            self.ctl(state, 44, highpass)
            self.ctl(state, 0, enhance)
            size, latency = self.ctl(state, 3), self.ctl(state, 39)
            assert (size, latency) == (160, 40)
            frames = []
            for packet in packets:
                lib.speex_bits_read_from(c.byref(bits), c.c_char_p(packet), len(packet))
                frame = np.empty(size, dtype='<i2')
                assert lib.speex_decode_int(state, c.byref(bits), frame.ctypes.data) == 0
                assert not bits.overflow
                frames.append(frame)
            return np.concatenate(frames), latency
        finally:
            lib.speex_bits_destroy(c.byref(bits))
            lib.speex_decoder_destroy(state)


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    with wave.open(str(args.source), 'rb') as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 1, 8000)
        raw = w.readframes(w.getnframes())
    source = (np.frombuffer(raw, 'u1').astype(np.int32)-128)*256
    assert len(source) % 160 == 0 and np.all(source[-128:] == 0)
    wav16(out/'original-preview.wav', source)
    enc = Speex(args.host/'float/speex.dll')
    decoders = {v:Speex(args.host/v/'speex.dll') for v in ('float', 'fixed')}
    rows = []
    for bitrate in (8000, 11000, 15000, 18200, 24600):
        for highpass in (1, 0):
            packets, frame_bits, encode_latency = enc.encode(source, bitrate, highpass)
            payload = b''.join(packets)
            name = f'speex-{bitrate}-hp{highpass}'
            (out/(name+'.frames.gz')).write_bytes(gzip.compress(payload, mtime=0))
            for enhance in ((1,) if highpass else (1, 0)):
                for arithmetic, dec in decoders.items():
                    decoded, decode_latency = dec.decode(packets, highpass, enhance)
                    latency = encode_latency+decode_latency
                    pcm = decoded[latency:latency+len(source)]
                    assert len(pcm) == len(source)
                    trial = name+f'-enh{enhance}-{arithmetic}'
                    wav16(out/(trial+'-preview.wav'), pcm)
                    row = dict(name=trial, bitrate_bps=bitrate, highpass=highpass,
                               enhancement=enhance, arithmetic=arithmetic, frame_bits=frame_bits,
                               encoder_complexity=10, encode_latency_samples=encode_latency,
                               decode_latency_samples=decode_latency,
                               declared_latency_removed_samples=latency,
                               frames=len(packets), frame_bytes=len(packets[0]),
                               payload_bytes=len(payload), framing_allowance_bytes=32,
                               proposed_storage_bytes=len(payload)+32,
                               pcm16_to_codec_ratio=2*len(source)/(len(payload)+32),
                               payload_sha256=hashlib.sha256(payload).hexdigest(),
                               codec=quality(source, pcm, args.ffmpeg))
                    target = np.clip((pcm.astype(np.int32)+32768)>>8, 0, 255).astype('u1')
                    target[-128:] = 128
                    try:
                        ima = encode_ima(target)
                        row['ima_saturation_guard'] = require_unclipped(ima)
                        restored, indices = decode(ima)
                        assert (int(restored[-1]), int(indices[-1])) == (0, 0)
                        row['after_ima'] = quality(source, restored, args.ffmpeg)
                        (out/(trial+'.ima.gz')).write_bytes(gzip.compress(ima, mtime=0))
                        wav16(out/(trial+'-ima-preview.wav'), restored)
                    except (ValueError, AssertionError) as error:
                        row['ima_guard_rejected'] = str(error)
                    rows.append(row)
                    print(json.dumps(dict(name=trial, ratio=row['pcm16_to_codec_ratio'],
                          codec_snr_db=row['codec']['filtered_snr_db'],
                          after_ima_snr_db=row.get('after_ima', {}).get('filtered_snr_db'),
                          rejected=row.get('ima_guard_rejected'))), flush=True)
                    save(out/'report.json', dict(scope=__doc__, complete=False, rows=rows))
    save(out/'report.json', dict(scope=__doc__, date='2026-10-03', complete=True,
         source_pcm8_sha256=hashlib.sha256(raw).hexdigest(), samples=len(source),
         seconds=len(source)/8000, pcm16_denominator_bytes=2*len(source), filter=FILTER,
         source_release='Speex 1.2.1', encoder_arithmetic='floating point, highest complexity 10',
         native_z80_tested=False, integrated_pdm_tested=False, end_to_end_20db_verified=False,
         rows=rows, libraries={v:hashlib.sha256((args.host/v/'speex.dll').read_bytes()).hexdigest()
                              for v in ('float', 'fixed')}))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--host', required=True, type=Path)
    p.add_argument('--ffmpeg', required=True)
    run(p.parse_args())
