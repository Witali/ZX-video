"""Physical allocation, final-track holes, and the player's sector cursor."""
import unittest

import build_fast_sparse_trd as codec
import disk_layout
from validate_fast_sparse import CPU


class DiskLayoutTests(unittest.TestCase):
    def test_round_trip_and_all_partial_tracks(self):
        order = [0,8,1,9,2,10,3,11,4,12,5,13,6,14,7,15]
        self.assertEqual([disk_layout.physical_sector(i) for i in range(16)], order)
        for first in range(16):
            for count in range(65):
                stream = b''.join(bytes([i])*256 for i in range(count))
                arranged = disk_layout.arrange(stream, first)
                expected = list(range(16-first))
                for track in range(1,6):
                    expected += [track*16+sector-first for sector in order]
                used = expected[:count]
                self.assertEqual(len(arranged)//256, max(used,default=-1)+1)
                self.assertEqual(b''.join(arranged[p*256:(p+1)*256] for p in used), stream)
                self.assertEqual(len(arranged)//256, disk_layout.required_sectors(count,first))

    def test_disk_budget_includes_final_holes(self):
        # Two sectors on the next track occupy physical IDs 1 and 9.
        self.assertEqual(disk_layout.required_sectors(18,0),25)
        self.assertGreater(disk_layout.required_sectors(2530,0),2530)

    def test_player_sector_order_and_track_wrap(self):
        trd=b''.join(i.to_bytes(2,'little')*128 for i in range(2560))
        for first in (0,1,8,15):
            player,labels=codec.build_player(3,first,blocked=True,clocked=True,interleaved=True)
            cpu=CPU(player,trd);cpu.port_7ffd=0x17
            cpu.write8(labels['disk_track'],3);cpu.write8(labels['disk_sector'],first)
            for position in disk_layout.positions(50,first):
                cpu.set_hl(0xC000);cpu.b=1;cpu.pc=labels['read_n'];cpu.push(0x5F00)
                while cpu.pc!=0x5F00:cpu.step()
                actual=cpu.read8(0xC000) | cpu.read8(0xC001)<<8
                self.assertEqual(actual,3*16+first+position)


if __name__=='__main__': unittest.main()
