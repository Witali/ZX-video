"""Cached logical tracks, side mapping, step rates and cold-read fallback."""
import unittest

import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU


OPTIONS=dict(blocked=True,clocked=True,deadline=True,fast_disk=True,irq_disk=True,
             interleaved=True,full_rom_clock=True,cached_seek=True)


class CachedSeekTests(unittest.TestCase):
    def test_all_tracks_and_drive_step_rates_preserve_sector_and_destination(self):
        player,labels=codec.build_player(0,0,**OPTIONS)
        trd=b''.join(bytes([i%251])*256 for i in range(2560))
        for track in range(160):
            for drive in range(4):
                cpu=CPU(player,trd);cpu.port_7ffd=0x17;cpu.sp=0xBFF0
                for name,value in dict(disk_track=track,disk_sector=3,fast_disk_track=track^1,
                                       disk_interleaved=1).items():cpu.write8(labels[name],value)
                cpu.write8(0x5CF6,drive);cpu.write8(0x5CFA+drive,0x80|drive)
                cpu.set_hl(0xC000);cpu.b=1;cpu.pc=labels['read_n'];cpu.push(0x5F00)
                while cpu.pc!=0x5F00:
                    self.assertLess(cpu.steps,400);cpu.step()
                self.assertEqual(cpu.dos_reads,1)
                self.assertEqual([c[0] for c in cpu.seek_calls],
                                 [0x1FF6 if track&1 else 0x1FEB,0x3E44])
                self.assertEqual(cpu.seek_calls[-1][1:],(track//2,drive))
                self.assertEqual(bytes(cpu.banks[7][:256]),trd[(track*16+3)*256:(track*16+4)*256])
                self.assertEqual(cpu.read8(labels['disk_sector']),11)
                self.assertEqual(cpu.read8(labels['fast_disk_track']),track)
                self.assertEqual(cpu.read8(0x5CF5),track)
                self.assertEqual(cpu.read8(0x5CFE),0x84)
                self.assertEqual(cpu.sp,0xBFF0)
                self.assertEqual(bytes(cpu.read8(0xBDBD+i) for i in range(3)),bytes.fromhex('d923d9'))

    def test_first_and_same_track_reads_do_not_seek(self):
        player,labels=codec.build_player(3,2,**OPTIONS)
        for cached in (255,3):
            cpu=CPU(player,bytes(2560*256));cpu.port_7ffd=0x17
            for name,value in dict(disk_track=3,disk_sector=2,fast_disk_track=cached).items():
                cpu.write8(labels[name],value)
            cpu.write8(0x5CF5,3);cpu.set_hl(0xC000);cpu.b=1
            cpu.pc=labels['read_n'];cpu.push(0x5F00)
            while cpu.pc!=0x5F00:
                self.assertLess(cpu.steps,400);cpu.step()
            self.assertEqual(cpu.dos_reads,1);self.assertEqual(cpu.seek_calls,[])
            self.assertEqual(cpu.read8(0x5CFE),0x80)

    def test_requires_irq_and_full_clock(self):
        with self.assertRaises(ValueError):codec.build_player(0,0,cached_seek=True)
        with self.assertRaises(ValueError):codec.build_player(0,0,**{**OPTIONS,'full_rom_clock':False})

    def test_keepalive_seeks_current_cylinder_without_reading_or_moving_cursor(self):
        player,labels=codec.build_player(0,0,**OPTIONS,keepalive_fields=64)
        for track in range(160):
            for elapsed,last,remaining,due in ((63,0,5,False),(64,0,5,True),
                                              (28,65500,5,True),(100,0,0,False)):
                cpu=CPU(player,bytes(2560*256));cpu.port_7ffd=0x17;cpu.sp=0xBFF0
                cpu.alt_l=elapsed&255;cpu.alt_h=elapsed>>8
                for name,value in dict(elapsed_fields=elapsed,last_disk_fields=last,
                                       ring_count=320,disk_sectors_remaining=remaining).items():
                    cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)
                for name,value in dict(disk_track=(track+1)%160,disk_sector=0,
                                       fast_disk_track=track,ring_write_region=1,ring_write_high=0xC0).items():
                    cpu.write8(labels[name],value)
                cpu.write8(0x5CFE,0x84)
                before=[bytes(cpu.banks[i]) for i in (0,1,3,4,6,7)]
                cpu.pc=labels['producer_one'];cpu.push(0x5F00)
                while cpu.pc!=0x5F00:
                    self.assertLess(cpu.steps,300);cpu.step()
                self.assertEqual(cpu.dos_reads,0)
                self.assertEqual(cpu.seek_calls,[(0x3E44,track//2,0)] if due else [])
                self.assertEqual([bytes(cpu.banks[i]) for i in (0,1,3,4,6,7)],before)
                for name,value in dict(disk_track=(track+1)%160,disk_sector=0,fast_disk_track=track,
                                       ring_write_region=1,ring_write_high=0xC0).items():
                    self.assertEqual(cpu.read8(labels[name]),value)
                for name,value in dict(ring_count=320,disk_sectors_remaining=remaining,
                                       last_disk_fields=elapsed if due else last).items():
                    self.assertEqual(cpu.read8(labels[name])|cpu.read8(labels[name]+1)<<8,value)
                self.assertEqual(cpu.read8(0x5CFE),0x84)
                self.assertEqual((cpu.sp,cpu.a,cpu.alt_h*256+cpu.alt_l),(0xBFF0,0,elapsed))
                if due:
                    self.assertEqual(bytes(cpu.read8(0xBDBD+i) for i in range(3)),bytes.fromhex('d923d9'))


if __name__=='__main__':unittest.main()
