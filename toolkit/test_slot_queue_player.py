"""Envelope checkpoint replay and instruction-counted bootstrap restoration."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import slot_queue_player as slot
import fap3_disk_z80 as disk
from test_fap3_disk import DiskCPU,install


class CheckpointTests(unittest.TestCase):
    def test_fourteen_registers_at_zero_and_after_held_and_restarted_envelopes(self):
        self.assertEqual(slot.checkpoint(object(),0,14),bytes(14))
        records=[(None,dict(ticks=[bytes([4,8,16,11,123,12,2,13,14])])),
                 (None,dict(ticks=[bytes([0]),bytes([1,11,124]),bytes([1,13,14])]))]
        with patch('slot_queue_player.read_packet',side_effect=records):
            result=slot.checkpoint(object(),2,14)
        self.assertEqual(result[8],16);self.assertEqual(result[11:],bytes([124,2,14]))
        with patch('slot_queue_player.read_packet',side_effect=records):
            with self.assertRaises(ValueError):slot.checkpoint(object(),1,11)
        self.assertEqual(slot.checkpoint(object(),0,11),bytes(11))

    def test_native_restore_loop_and_exact_255_t_startup_difference(self):
        totals=[]
        h=SimpleNamespace(frames=1,audio=dict(audio_init=0x9000,setup_clock=0x9000,audio_drain=0x9000))
        clock=dict(prime=0x9000,start=0x9000,remaining=0x9000,play_one=0x9000)
        for count in (11,14):
            values=bytes(range(count));code,labels=disk.build_driver(h,clock,values)
            cpu=DiskCPU(b'',b'');install(cpu,disk.DRIVER,code)
            cpu.pc=labels['ay_restore'];cpu.set_hl(labels['ay_state']);cpu.d=0
            writes=[]
            while cpu.pc!=labels['ay_restore']+18:
                if cpu.pc==labels['ay_restore']+10:writes.append((cpu.d,cpu.a))
                cpu.step()
            self.assertEqual(writes,list(enumerate(values)))
            self.assertEqual(cpu.tstates,85*count-5);totals.append(cpu.tstates)
        self.assertEqual(totals,[930,1185]);self.assertEqual(totals[1]-totals[0],255)


if __name__=='__main__':unittest.main()
