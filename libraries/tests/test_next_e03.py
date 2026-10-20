"""Private E03 construction, dataflow and native byte/flag qualification."""
from pathlib import Path
import sys
import unittest

LIBRARIES = Path(__file__).resolve().parents[1]
for path in (LIBRARIES/'lzsa/src',LIBRARIES/'zx0/src',LIBRARIES/'tests',LIBRARIES.parent):
    sys.path.insert(0,str(path))

from emulator.cpu import load_library
import next_e03_profiles as profiles
from next_e03_measure import bind, micro_screen, replay, resident_reset_screen, hot_family_screen


class E03Tests(unittest.TestCase):
    def test_inventory_lower_bounds(self):
        rows = [profiles.inventory(name) for name in ('fast','balanced','compact')]
        self.assertEqual([row['count'] for row in rows],[123,75,48])
        self.assertEqual([row['optimistic_zero_extra_dispatch_service_delta'] for row in rows],[264,360,414])
        self.assertEqual([row['specified_service_lower_bound_delta'] for row in rows],[275,371,425])

    def test_actual_service_and_mutable_inventory(self):
        for design,size,patches,stack in [('hot_pair',9515,2,6),('shared_smc',8056,3,8)]:
            regions,labels,metadata = profiles.build(design)
            self.assertEqual(sum(len(blob) for _,blob in regions)+stack,size)
            self.assertEqual(metadata['total_storage_bytes'],size)
            self.assertEqual(len(metadata['patched_addresses']),patches)
            self.assertEqual(metadata['variant'],'next-e03-'+design)
            self.assertTrue(metadata['test_only'])
            self.assertFalse(metadata['irq_qualified'])
            self.assertFalse(metadata['inplace_qualified'])

    def test_native_byte_flags_and_phase(self):
        library=load_library();bind(library)
        report = micro_screen(library,values=(0,1,15,16,127,128,254,255))
        self.assertTrue(report['complete'])
        self.assertEqual(report['kernels']['shared_smc']['executions'],8*2*64*2)

    def test_dirty_state_reset_and_odd_eof(self):
        library=load_library();bind(library)
        for design in ('hot_pair','shared_smc'):
            profile=profiles.build(design)
            for payload,raw in [(bytes.fromhex('e7 f0 e8'),b''),(bytes.fromhex('ef 41 f0 e8'),b'A')]:
                result=replay(profile,payload,raw,library=library)
                self.assertTrue(result['exact'])
                self.assertLessEqual(result['stack_bytes'],profile[2]['caller_stack_bytes'])

    def test_resident_odd_even_phase_reset(self):
        report=resident_reset_screen(load_library())
        self.assertTrue(report['complete'])
        self.assertEqual([row['final_phase'] for row in report['blocks']],
            ['full','empty','full','empty','full','empty','empty','full'])

    def test_hot_family_all_match_extension_exits(self):
        library=load_library();bind(library)
        report=hot_family_screen(library,profiles.baseline(),
            {name:profiles.build(name) for name in ('hot_pair','shared_smc')})
        self.assertTrue(report['complete'])
        self.assertEqual(report['cases'],56)


if __name__=='__main__':
    unittest.main()
