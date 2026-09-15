"""Presentation deadlines may defer reads, but not the minimum input reserve."""
import unittest

import build_fast_sparse_trd as codec
from test_packet_lookahead import OPTIONS,word
from test_uncontended_player import relocate
from validate_fast_sparse import CPU


def fixture(*, reserve=64, keepalive=0):
    player,labels=codec.build_player(3,2,**OPTIONS,full_rom_clock=True,cached_seek=True,
                                    uncontended=True,read_reserve=reserve,keepalive_fields=keepalive)
    cpu=CPU(player,bytes(2560*256));relocate(cpu,labels);cpu.sp=0xBFF0;cpu.port_7ffd=0x17
    for name,value in dict(disk_track=3,disk_sector=2,fast_disk_track=3,
                           ring_write_region=1,ring_write_high=0xC0).items():cpu.write8(labels[name],value)
    cpu.write8(0x5CF5,3)
    return cpu,labels


def run_late(cpu,labels,*,elapsed=13,deadline=6):
    word(cpu,labels,'elapsed_fields',elapsed);word(cpu,labels,'next_frame_field',deadline)
    cpu.alt_h=elapsed>>8;cpu.alt_l=elapsed&255
    cpu.pc=labels['prefetch_loop'];start=cpu.tstates;steps=cpu.steps
    while cpu.pc!=labels['flip_screen']:
        assert cpu.steps-steps<5000
        cpu.step()
    return cpu.tstates-start


class ReadDebtTests(unittest.TestCase):
    def test_late_frame_defers_reads_and_retains_debt(self):
        for elapsed,deadline in ((13,6),(2,65534)):
            cpu,labels=fixture()
            word(cpu,labels,'ring_count',200);word(cpu,labels,'disk_sectors_remaining',300)
            for expected in (3,6,9):
                run_late(cpu,labels,elapsed=elapsed,deadline=deadline)
                self.assertEqual(cpu.dos_reads,0)
                self.assertEqual(cpu.read8(labels['read_debt']),expected)
                self.assertEqual(cpu.read8(labels['next_frame_field'])|cpu.read8(labels['next_frame_field']+1)<<8,(deadline+6)&65535)

    def test_reserve_and_eof_override_debt(self):
        for reserve in (64,96,256):
            for count,left,expected in ((reserve-5,20,5),(reserve-5,2,2),(reserve,20,0),(1,0,0)):
                cpu,labels=fixture(reserve=reserve)
                word(cpu,labels,'ring_count',count);word(cpu,labels,'disk_sectors_remaining',left)
                run_late(cpu,labels)
                self.assertEqual(cpu.dos_reads,expected)
                self.assertEqual(cpu.read8(labels['ring_count'])|cpu.read8(labels['ring_count']+1)<<8,count+expected)
                self.assertEqual(cpu.read8(labels['read_debt']),max(0,3-expected))

    def test_debt_saturates_without_wrapping(self):
        for debt,expected in ((317,320),(318,320),(320,320)):
            cpu,labels=fixture();word(cpu,labels,'read_debt',debt)
            word(cpu,labels,'ring_count',200);word(cpu,labels,'disk_sectors_remaining',300)
            run_late(cpu,labels)
            self.assertEqual(cpu.read8(labels['read_debt'])|cpu.read8(labels['read_debt']+1)<<8,expected)

    def test_keepalive_when_a_late_frame_defers_all_reads(self):
        cpu,labels=fixture(keepalive=64)
        word(cpu,labels,'ring_count',200);word(cpu,labels,'disk_sectors_remaining',300)
        run_late(cpu,labels,elapsed=64,deadline=60)
        self.assertEqual(cpu.dos_reads,0)
        self.assertEqual(len(cpu.seek_calls),1)
        self.assertEqual(cpu.read8(labels['last_disk_fields']),64)

    def test_same_track_and_track_change_read_windows(self):
        for same in (False,True):
            for fields_left in (1,2,3,4):
                cpu,labels=fixture()
                word(cpu,labels,'ring_count',100);word(cpu,labels,'disk_sectors_remaining',300)
                word(cpu,labels,'next_frame_field',10);word(cpu,labels,'read_debt',3)
                cpu.write8(labels['fast_disk_track'],3 if same else 2)
                cpu.alt_l=10-fields_left;cpu.pc=labels['prefetch_check']
                stops={labels[n]:n for n in ('debt_read','debt_decode','debt_wait')}
                while cpu.pc not in stops:
                    self.assertLess(cpu.steps,100);cpu.step()
                expected='debt_wait' if fields_left==1 else 'debt_read' if (same or fields_left>=4) else 'debt_decode'
                self.assertEqual(stops[cpu.pc],expected)


if __name__=='__main__':unittest.main()
