"""Capacity, cold paging and exact refill-state regressions for the song TRD."""
from pathlib import Path
import tempfile
import unittest

from build_stream_trd import build,sections
from ram_cache import PROFILES
from verify_stream_trd import cold_load,native_check


class StreamTrd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[1]/'.tmp';root.mkdir(exist_ok=True)
        cls.temporary=tempfile.TemporaryDirectory(dir=root,prefix='stream-tests-')
        cls.root=Path(cls.temporary.name)

    @classmethod
    def tearDownClass(cls):cls.temporary.cleanup()

    def control(self,size,name):
        # Zero IMA4 decodes to real silence from the required zero seed.
        # Every bank's bytes are still checked during coherent cold loading.
        packed=bytes(size)
        disk,meta=build(packed,self.root/name,bytes(6912))
        return packed,disk,meta

    def test_capacity_accounts_for_code_tables_and_shadow_screen(self):
        capacities={'128':91392,'scorpion':222464,'pentagon512':484608,'pentagon1024':1008896}
        for profile,capacity in capacities.items():
            with self.subTest(profile=profile):
                batch,left=sections(capacity+256,PROFILES[profile]['pages'])
                self.assertEqual(left,256)
                self.assertEqual(sum(s['bytes'] for s in batch),capacity)
                self.assertEqual([s['bank'] for s in batch[:6]],[0,4,6,1,3,7])
                self.assertNotIn(2,[s['bank'] for s in batch]);self.assertNotIn(5,[s['bank'] for s in batch])
                self.assertEqual(batch[5]['address'],0xdb00)

    def test_short_batch_completes_all_progress_cells(self):
        packed,disk,meta=self.control(4096,'short')
        for profile in PROFILES:
            with self.subTest(profile=profile):
                m,r=cold_load(disk,meta,profile)
                self.assertTrue(r['progress_complete']);self.assertEqual(r['remaining_sectors'],0)
                self.assertEqual(r['loaded_sections'],[dict(bank=0,address=0xf000,bytes=len(packed))])
                self.assertEqual(m.banks[7][0x1ac0:0x1ae0],bytes([0x24]*32))

    def test_exact_bank_holds_and_preserved_decoder_across_refill(self):
        packed,disk,meta=self.control(100352,'refill')
        for profile in PROFILES:
            with self.subTest(profile=profile):
                r=native_check(disk,meta,packed,profile)
                self.assertTrue(r['every_continuous_native_hold_exact'])
                self.assertTrue(r['every_bit_predictor_index_exact'])
                self.assertEqual(r['reloads'],int(profile=='128'))

    def test_high_bank_descriptor_uses_1024_bit_without_512_lock(self):
        packed,disk,meta=self.control(512000,'high-bank')
        for profile in ('pentagon512','pentagon1024'):
            with self.subTest(profile=profile):
                m,r=cold_load(disk,meta,profile)
                self.assertFalse(m.locked)
                if profile=='pentagon1024':
                    self.assertEqual(r['remaining_sectors'],0)
                    self.assertGreater(max(s['bank'] for s in r['loaded_sections']),31)
                else:
                    self.assertEqual(r['remaining_sectors'],107)
                    self.assertEqual(max(s['bank'] for s in r['loaded_sections']),31)


if __name__=='__main__':unittest.main()
