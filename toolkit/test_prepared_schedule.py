import unittest
from probe_prepared_schedule import simulate,PERIOD


class PreparedScheduleTests(unittest.TestCase):
    def test_free_producer_and_budget_do_not_add_delay(self):
        r=simulate([0]*100,[10000]*100,[1000]*100,3000)
        self.assertEqual(r['late_frames'],0)
        self.assertEqual(r['maximum_queue_bytes'],3000)
        self.assertTrue(r['eof_accounting_verified'])

    def test_sustained_overload_is_late_and_not_recovered(self):
        r=simulate([2*PERIOD]*100,[1000]*100,[1000]*100,3000)
        self.assertGreater(r['late_frames'],80)
        self.assertIsNone(r['late_runs'][-1]['recovered_at_frame'])
        self.assertGreater(r['frames_outside_20ms'],0)

    def test_burst_recovers_to_original_grid(self):
        work=[0]*100; work[20:30]=[2*PERIOD]*10
        r=simulate(work,[10000]*100,[1000]*100,3000)
        self.assertGreater(r['late_frames'],0)
        self.assertIsNotNone(r['late_runs'][-1]['recovered_at_frame'])
        self.assertLess(r['late_runs'][-1]['recovered_at_frame'],99)


if __name__=='__main__': unittest.main()
