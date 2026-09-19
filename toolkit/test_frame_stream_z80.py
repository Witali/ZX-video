import struct
import unittest

from cell_audio_stream import pack as audio
from frame_packet_stream import pack
from frame_output_pipeline import frames, Harness as FrameHarness, wrapper
from frame_stream_harness import Harness
from probe_sparse_motion_cache import pack as cache
from raw_attribute_stream import pack as attributes
from test_frame_output_pipeline import fixture
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from build_long_video_trd import expand_compact_screen
from benchmark_context_huffman import word
from zx0_speed import Token, encode


def source(count=4, *, constant_attribute_borders=False):
    states, cells, _ = fixture(count,constant_attribute_borders=constant_attribute_borders)
    cells, _ = attributes(cells, states, [i % 2 == 0 for i in range(count)])
    ticks = [bytes([1, (i % 11), (i*3) & 15]) if i % 3 else b'\0' for i in range(count*6)]
    sc, _ = cache(audio(cells, b''.join(ticks)), states, 32, 4)
    raw, _ = pack(sc)
    return states, cells, raw, ticks


def ring(raw, size=8192, compressed=False):
    result = bytearray()
    for start in range(0, len(raw), size):
        part = raw[start:start+size]
        payload = encode(part, [Token(0,len(part))]) if compressed else part
        result += struct.pack('<HH', len(part), len(payload) | (0 if compressed else 0x8000))+payload
    return bytes(result)


class FrameStreamTests(unittest.TestCase):
    def test_combined_stored_and_compressed_every_frame(self):
        states, cells, raw, ticks = source()
        tables, mapping, packets = frames(cells)
        r = Reader(raw); read_header(r, magic=b'FAP1')
        for compressed in (False, True):
            h = Harness(ring(raw, 509, compressed), tables, mapping, len(states), ring_start=0xffff)
            h.consume_header(raw[:r.pos])
            for i, state in enumerate(states):
                result = h.prepare()
                self.assertGreater(result['stages']['packet'], 0)
                self.assertEqual(bytes(h.cpu.read8(0x6400+j) for j in range(3840)), state.tobytes())
                bank = 7 if i % 2 == 0 else 5
                h.expected_screens[bank] = b''.join(expand_compact_screen(state.tobytes()))
                for b, expected in h.expected_screens.items(): self.assertEqual(bytes(h.cpu.banks[b][:6912]), expected)
                h.publish(); h.drain_six(ticks[i*6:i*6+6])
                self.assertEqual(bytes(h.cpu.banks[5][0x1b00:0x2400]), b'\xa5'*0x900)
                for base, blob in h.frame.protected_regions:
                    old = h.cpu.port_7ffd; h.cpu.port_7ffd = (old & ~7) | 6
                    self.assertEqual(bytes(h.cpu.read8(base+j) for j in range(len(blob))), blob)
                    h.cpu.port_7ffd = old
            self.assertEqual(h.cpu.consumed, len(h.cpu.ring_data))
            self.assertEqual(word(h.cpu, h.audio['audio_ticks_played']), len(states)*6)
            self.assertEqual(h.cpu.read8(h.audio['audio_enabled']), 0)

    def test_deferred_wrapper_keeps_existing_default(self):
        _, cells, _, _ = source(1)
        tables, mapping, _ = frames(cells)
        h = FrameHarness(tables, mapping, raw_attributes=True, selective_cache=True)
        before, old, oldrows = wrapper(h.recon, h.draw, origin=0x7900)
        after, new, newrows = wrapper(h.recon, h.draw, origin=0x7900, deferred_publish=True)
        cut = old['publish']-old['run']
        self.assertEqual(before, h.wrapper_code)
        relocated = bytearray(before)
        for row in oldrows:
            if row['instruction'] in ('LD HL,(literal_pointer)', 'LD A,(cache_flag)', 'LD A,(raw_attribute_flag)'):
                pos = row['address']-old['run']+1
                struct.pack_into('<H', relocated, pos, struct.unpack_from('<H', relocated,pos)[0]+1)
        relocated[cut:cut] = b'\xc9'
        self.assertEqual(relocated, after)
        self.assertEqual(new['publish']-old['publish'], 1)
        self.assertEqual(sum(r['tstates'] for r in newrows)-sum(r['tstates'] for r in oldrows), 10)

    def test_invalid_fap_headers_rejected_before_video_writes(self):
        states, cells, raw, _ = source(1)
        tables, mapping, _ = frames(cells)
        r = Reader(raw); read_header(r, magic=b'FAP1')
        start = r.pos
        for _ in range(6): count = r.take(1)[0]; r.take(count*2)
        for offset, bad in ((0,b'\x08'), (1,b'\x07\0'), (1,b'\x25\x02'),
                            (3,b'\xff\xff'), (5,b'\xff\xff')):
            data = bytearray(raw); data[r.pos+offset:r.pos+offset+len(bad)] = bad
            h = Harness(ring(data), tables, mapping, 1)
            h.consume_header(data[:start])
            with self.assertRaises(AssertionError): h.prepare()
            self.assertFalse(any(h.cpu.banks[5][:6912])); self.assertFalse(any(h.cpu.banks[7][:6912]))


if __name__ == '__main__': unittest.main()
