import unittest

import cell_audio_stream
from frame_output_pipeline import Harness, frames, serialized_masks
from frame_metadata_z80 import expected_tstates
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from probe_lossless_layouts import sha
from raw_attribute_stream import pack, decode
from test_frame_output_pipeline import fixture


class RawAttributeTests(unittest.TestCase):
    def test_default_renderer_keeps_previous_machine_code(self):
        # Golden generated from git show 11dc864:toolkit/causal_tile_z80.py,
        # with two uniform 8-bit Huffman tables and the same enabled options.
        h = Harness([bytes([8]*256)]*2, bytes(256))
        self.assertEqual(sha(h.recon_code), 'febe72283aad3b1fdb71defee755a2b9ac79ed8f3df8352e475ea53b0adce29c')

    def test_exact_mixed_frames_and_cpu_delta(self):
        states, original, _ = fixture()
        selected = [False, True, False, True, True]
        data, rows = pack(original, states, selected)
        self.assertEqual(decode(data), states.tobytes())
        tables, mapping, before = frames(original)
        _, _, after = frames(data)
        baseline = Harness(tables, mapping)
        candidate = Harness(tables, mapping, raw_attributes=True, decode_metadata=True)
        encoded_masks = serialized_masks(data)
        returns = [row['address']+3 for row in baseline.instructions.values()
                   if row['instruction'] == 'CALL attribute_pass']
        self.assertEqual(len(returns), 1)
        for index, state in enumerate(states):
            clocks = []

            def record(cpu):
                if cpu.pc in (baseline.recon['attribute_pass'], returns[0]):
                    clocks.append(cpu.tstates)
                return 0

            old = baseline.run(*before[index], state.tobytes(), index, record)
            new = candidate.run(*after[index], state.tobytes(), index, encoded_metadata=encoded_masks[index])
            self.assertEqual(len(clocks), 2)
            expected_delta = 16209-(clocks[1]-clocks[0])+26 if selected[index] else 55
            expected_delta += expected_tstates(encoded_masks[index])
            self.assertEqual(new['total_tstates']-old['total_tstates'], expected_delta)
        for bad in (data[:-1], data+b'!', b'FSC1'+data[4:]):
            with self.assertRaises(ValueError):
                decode(bad)
        self.assertLessEqual(max(r['coded_bytes'] for r in rows), 4704)

    def test_audio_roundtrip_and_unused_flag_rejected(self):
        states, original, _ = fixture(2)
        data, _ = pack(original, states, [True, False])
        audio = b'\0'*12
        combined = cell_audio_stream.pack(data, audio)
        self.assertEqual(combined[:4], b'FSA2')
        self.assertEqual(cell_audio_stream.unpack(combined), (data, audio, [6, 6]))
        r = Reader(data); read_header(r, magic=b'FSC2')
        bad = bytearray(data); bad[r.pos+6] |= 32
        with self.assertRaisesRegex(ValueError, 'cache flags'):
            decode(bytes(bad))


if __name__ == '__main__':
    unittest.main()
