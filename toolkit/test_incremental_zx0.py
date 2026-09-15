"""Resume across literal/match/frame boundaries without changing decoded data."""
import unittest

import build_fast_sparse_trd as codec
import test_blocked_stream as reference
from validate_fast_sparse import CPU

EMPTY_COMPRESSED = reference.EMPTY_COMPRESSED
EMPTY_DECODED = reference.EMPTY_DECODED


class IncrementalDecoderTests(unittest.TestCase):
    def test_every_output_boundary_and_register_clobber_between_calls(self):
        player,labels=codec.build_player(0,0,blocked=True,incremental=True)
        for stored in (False,True):
            cpu=CPU(player,b'');cpu.sp=0xBFF0
            data=EMPTY_DECODED if stored else EMPTY_COMPRESSED
            for i,value in enumerate(data):cpu.write8(0xA000+i,value)
            def word(name,value):
                cpu.write8(labels[name],value);cpu.write8(labels[name]+1,value>>8)
            word('block_length',len(EMPTY_DECODED));word('block_end',0x8000+len(EMPTY_DECODED))
            cpu.write8(labels['block_stored'],128 if stored else 0)
            for size in range(1,len(EMPTY_DECODED)+1):
                word('slice_target',0x8000+size)
                cpu.pc=labels['slice_begin' if size==1 else 'slice_until'];cpu.push(0x5F00)
                before=cpu.steps
                while cpu.pc!=0x5F00:
                    self.assertLess(cpu.steps-before,500);cpu.step()
                self.assertEqual(cpu.sp,0xBFF0)
                self.assertEqual(bytes(cpu.banks[2][:size]),EMPTY_DECODED[:size])
                # Caller owns the primary registers; suspended decoder state
                # must not depend on their contents on the next invocation.
                cpu.set_bc(0x1234);cpu.set_de(0x5678);cpu.set_hl(0x9ABC)
                cpu.a=0x36;cpu.z=True;cpu.carry=True
            self.assertGreaterEqual(cpu.min_sp,0x7D80)

    def test_complete_player_two_blocks_and_irq(self):
        import blocked_stream
        block=blocked_stream.Block(EMPTY_COMPRESSED,EMPTY_DECODED,500,False,0)
        helper=reference.BlockedStreamTests()
        helper.run_player([bytes(3840)]*1000,[block,block],clocked=True,
                          deadline=True,fast_disk=True,irq_disk=True,interleaved=True,
                          fast_draw=True,incremental=True)


if __name__=='__main__':unittest.main()
