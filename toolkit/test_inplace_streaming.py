"""Real sector production, in-place overlap, input waits and AY IRQ safety."""
import struct
import unittest
from unittest.mock import patch

from benchmark_inplace_streaming import Harness
from test_inplace_slot import block
import test_inplace_slot as complete


def fixture(blocks, first=53):
    stream=b''.join(struct.pack('<HH',len(raw),len(payload))+payload for payload,raw in blocks)
    return Harness(stream,first)


class StreamingInplaceTests(unittest.TestCase):
    def test_header_crossings_and_rotating_banks(self):
        with patch.object(complete,'fixture',fixture):
            complete.InplaceSlotTests().test_header_crossings_first_track_and_full_size_bank_rotation()

    def test_shared_carry_and_short_read_retry(self):
        with patch.object(complete,'fixture',fixture):
            complete.InplaceSlotTests().test_shared_sector_and_short_read_retry()

    def test_irq_after_every_instruction_preserves_both_register_sets(self):
        with patch.object(complete,'fixture',fixture):
            complete.InplaceSlotTests().test_real_ay_irq_after_each_producer_and_decoder_instruction()

    def test_partial_literals_and_matches_before_complete_acquisition(self):
        blocks=[block(n,literal=True) for n in (255,256,257,511,800,4096,7900)]
        blocks += [block(15872)]*3
        h=fixture(blocks)
        for i,(payload,raw) in enumerate(blocks): h.block(payload,raw,i)
        h.finish()
        for row in h.results[:7]:
            if row['payload_bytes']>512:
                self.assertGreater(len(row['input_waits']),0)
                self.assertLess(row['first_output_loaded_bytes'],row['payload_bytes'])
        self.assertTrue(all(r['exact'] for r in h.results))

    def test_full_output_still_waits_for_end_marker(self):
        # Slide the same long match across every possible sector alignment.
        # At least one alignment leaves the EOF marker on an unloaded page
        # after the match has already produced the entire decoded block.
        candidates={}
        for n in range(1,520):
            value=block(n,literal=True)
            candidates.setdefault((len(value[0])+4)%256,value)
        pending=0
        for offset in range(256):
            blocks=[candidates[offset],block(15872)]
            h=fixture(blocks)
            for i,(payload,raw) in enumerate(blocks): h.block(payload,raw,i)
            pending+=sum(w['produced']==15872 for w in h.results[-1]['input_waits'])
            h.finish()
        self.assertGreater(pending,0)


if __name__=='__main__':unittest.main()
