"""Boundary and clobbered-register tests for batched disk reads."""
import unittest

import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU


class BatchedProducerTests(unittest.TestCase):
    def test_deadline_wrap_and_late_frame_keeps_input_available(self):
        for elapsed,deadline in ((65535,65534),(2,65534),(13,6)):
            for count in (63,64):
                player,labels=codec.build_player(0,0,blocked=True,clocked=True,deadline=True)
                cpu=CPU(player,bytes(2560*256));cpu.port_7ffd=0x17
                for name,value in dict(elapsed_fields=elapsed,next_frame_field=deadline,
                                       ring_count=count,disk_sectors_remaining=1).items():
                    cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)
                cpu.write8(labels['ring_write_region'],1);cpu.write8(labels['ring_write_high'],0xC0)
                cpu.pc=labels['prefetch_loop']
                while cpu.pc!=labels['flip_screen']:
                    self.assertLess(cpu.steps,1000);cpu.step()
                next_field=cpu.read8(labels['next_frame_field']) | cpu.read8(labels['next_frame_field']+1)<<8
                self.assertEqual(next_field,(deadline+6)&65535)
                self.assertEqual(cpu.read8(labels['ring_count']),64)
                self.assertEqual(cpu.bytes_read,(64-count)*256)

    def test_irq_input_limit_protects_clock_and_stack(self):
        player,labels=codec.build_player(0,0,blocked=True,clocked=True,deadline=True,
                                        fast_disk=True,irq_disk=True)
        for size,valid in ((1,True),(7424,True),(7425,False),(8192,False),(0,False)):
            cpu=CPU(player,b'');cpu.pc=labels['load_block_header'];cpu.push(0x5F00)
            cpu.write8(labels['ring_count'],64)
            header=iter(size.to_bytes(2,'little')+bytes((0,32)))
            while cpu.pc not in (0x5F00,labels['fatal']):
                self.assertLess(cpu.steps,100)
                if cpu.pc==labels['stream_byte']:
                    cpu.a=next(header);cpu.pc=cpu.pop()
                else:cpu.step()
            self.assertEqual(cpu.pc==0x5F00,valid)

    def test_uncontended_clock_vector_and_register_preservation(self):
        player,labels=codec.build_player(0,0,blocked=True,clocked=True,deadline=True,
                                        fast_disk=True,irq_disk=True,interleaved=True)
        cpu=CPU(player,b'');cpu.sp=0xBFF0;cpu.pc=labels['setup_clock'];cpu.push(0x6001)
        while cpu.pc!=0x6001:cpu.step()
        vector=cpu.read8((cpu.i<<8)|255) | cpu.read8((cpu.i<<8)+256)<<8
        self.assertEqual(vector,0xBDBD)
        self.assertEqual(bytes(cpu.read8(vector+i) for i in range(7)),bytes.fromhex('d923d9fbc32f3d'))
        cpu.set_bc(0x1234);cpu.set_de(0x5678);cpu.set_hl(0x9ABC)
        cpu.a=77;cpu.z=True;cpu.carry=True;cpu.alt_a=54
        start=cpu.tstates;cpu.pc=vector;cpu.push(0x6001)
        while cpu.pc!=0x6001:cpu.step()
        self.assertEqual(cpu.tstates-start,42)
        self.assertEqual((cpu.bc(),cpu.de(),cpu.hl(),cpu.a,cpu.z,cpu.carry,cpu.alt_a),
                         (0x1234,0x5678,0x9ABC,77,True,True,54))
        self.assertEqual(cpu.alt_h*256+cpu.alt_l,1)

    def test_bank_track_capacity_and_end_limits(self):
        trd = b''.join(bytes([sector % 251])*256 for sector in range(2560))
        for batch in (1,2,4,8,16):
            player, labels = codec.build_player(0,0,blocked=True,clocked=True,
                                                read_batch=batch,deadline=True)
            for count,remaining,high,sector,region in (
                (0,500,0xC0,0,1), (319,500,0xC0,0,1),
                (318,500,0xC0,0,1), (0,1,0xC0,0,1),
                (0,500,0xFF,0,1), (0,500,0xFE,0,5),
                (0,500,0xFF,15,5), (0,500,0xC0,13,1),
                (320,500,0xC0,0,1), (0,0,0xC0,0,1),
            ):
                with self.subTest(batch=batch,count=count,remaining=remaining,
                                  high=high,sector=sector,region=region):
                    cpu=CPU(player,trd);cpu.port_7ffd=0x17
                    def word(name,value):
                        cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)
                    def readword(name):
                        return cpu.read8(labels[name]) | cpu.read8(labels[name]+1)<<8
                    word('ring_count',count);word('disk_sectors_remaining',remaining)
                    for name,value in dict(ring_write_high=high,ring_write_region=region,
                                           disk_track=3,disk_sector=sector).items():
                        cpu.write8(labels[name],value)
                    cpu.pc=labels['producer_one'];cpu.push(0x5F00)
                    while cpu.pc != 0x5F00:
                        self.assertLess(cpu.steps,1000);cpu.step()
                    expected=min(batch,320-count,remaining,256-high,16-sector)
                    self.assertEqual(cpu.a,expected)
                    self.assertEqual(cpu.bytes_read,expected*256)
                    self.assertEqual(readword('ring_count'),count+expected)
                    self.assertEqual(readword('disk_sectors_remaining'),remaining-expected)
                    self.assertEqual(cpu.read8(labels['disk_track'])*16+cpu.read8(labels['disk_sector']),
                                     3*16+sector+expected)
                    bank=(0,1,3,4,6)[region-1]
                    offset=(high-0xC0)*256
                    self.assertEqual(bytes(cpu.banks[bank][offset:offset+expected*256]),
                                     trd[(48+sector)*256:(48+sector+expected)*256])
                    wrapped=high+expected==256
                    self.assertEqual(cpu.read8(labels['ring_write_high']),0xC0 if wrapped else high+expected)
                    self.assertEqual(cpu.read8(labels['ring_write_region']),region%5+1 if wrapped else region)


if __name__=='__main__': unittest.main()
