"""Resident-AY builder subclass with lossless six-byte motion-cache maps."""
import struct

from build_fap3_trd import sha, padded, sectors
from probe_motion_entropy import Reader
from resident_audio_player import Builder as PreviousBuilder
import half_row_cache as half


class Builder(PreviousBuilder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.half_streams = {}

    def separated(self, start, end):
        key = start, end
        if key not in self.half_streams:
            old, sound = super().separated(start, end)
            reader = Reader(old); video = bytearray()
            for _ in range(end-start):
                body = reader.take(reader.u16()); wide = half.widen(body)
                if half.narrow(wide) != body: raise AssertionError('cache-map roundtrip differs')
                if len(wide)>4702: raise ValueError('half-row packet exceeds guarded input window')
                video += struct.pack('<H', len(wide))+wide
            reader.end(); self.half_streams[key] = bytes(video), sound
        return self.half_streams[key]

    def ram(self, start, end, next_sector, remaining):
        sections, metadata = super().ram(start, end, next_sector, remaining)
        banks = self.expected_banks
        def bank_at(at): return 5 if at<0x8000 else 2 if at<0xc000 else 7
        def read8(at): return banks[bank_at(at)][at&16383]
        def put(at, code):
            if (at&16383)+len(code)>16384: raise ValueError('cross-bank patch')
            banks[bank_at(at)][at&16383:(at&16383)+len(code)] = code
        half.install(read8, put, metadata)
        result = []
        for section in sections:
            at = section['address']&16383
            raw = bytes(banks[section['bank']][at:at+section['decoded_bytes']])
            if sha(raw) == section['sha256']:
                result.append(section); continue
            if section.get('startup_delta'): raise ValueError('unexpected table modification')
            coded = self.compress(raw)
            result.append(dict(section, data=padded(coded), compressed_bytes=len(coded),
                               sectors=sectors(coded), sha256=sha(raw)))
        return result, metadata
