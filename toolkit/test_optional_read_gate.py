"""Exhaustive small admission state grid and independent Z80 instruction costs."""
import itertools
import unittest
from z80 import Z80Machine
from optional_read_gate import build
from pipelined_frame_z80 import DEADLINE,READY


class GateTests(unittest.TestCase):
    def test_admission_and_instruction_costs(self):
        metadata=dict(queue_labels=dict(step=0x7000,count=0x6000,phase=0x6001),
            disk_labels=dict(cached_track=0x6002,disk_position=0x6003),
            player_labels=dict(elapsed_fields=0x6005),
            compressed_sector_cache=dict(labels=dict(count=0x6007)))
        code,labels,_=build(metadata);costs=set();cases=0
        for count,phase,cache,same,ready,delta,elapsed in itertools.product(
                range(5),range(3),(0,1),(False,True),(0,1),(-1,0,1,2,3,4,5),(100,65534)):
            m=Z80Machine();m.set_memory_block(labels['step'],code)
            m.set_memory_block(0x7000,b'\x3e\x01\xc9') # unchanged queue step stub: 17 T
            for at,value in ((0x6000,count),(0x6001,phase),(0x6002,10),
                             (0x6004,10 if same else 11),(0x6007,cache),(READY,ready)):
                m.memory[at]=value
            m.set_memory_block(0x6005,elapsed.to_bytes(2,'little'))
            m.set_memory_block(DEADLINE,((elapsed+delta)&65535).to_bytes(2,'little'))
            m.set_memory_block(0x7fee,b'\x00\x01');m.sp=0x7fee;m.pc=labels['step']
            m.set_breakpoint(0x100);m.ticks_to_stop=10000
            while m.pc!=0x100:
                self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
            eligible=count>=2 and (count==4 or (phase!=2 and cache==0)) and not same
            defer=eligible and (not ready or delta<2)
            self.assertEqual(m.a,0 if defer else 1)
            self.assertEqual(m.sp,0x7ff0)
            # Zilog instruction table, excluding the unchanged stub and caller CALL.
            ticks=10000-m.ticks_to_stop-(0 if defer else 17)
            expected=30
            if count>=2:
                expected+=17
                if count!=4:
                    expected+=30
                    if phase!=2:expected+=27
                if count==4 or (phase!=2 and cache==0):
                    expected+=44
                    if not same:
                        expected+=63
                        if ready:
                            expected+=37
                            if delta>=0:expected+=18+21
                        if defer:expected+=14
            self.assertEqual(ticks,expected,(count,phase,cache,same,ready,delta))
            costs.add(ticks);cases+=1
        print(dict(cases=cases,gate_tstates=sorted(costs)),flush=True)

    def test_publication_at_each_gate_instruction_boundary(self):
        metadata=dict(queue_labels=dict(step=0x7000,count=0x6000,phase=0x6001),
            disk_labels=dict(cached_track=0x6002,disk_position=0x6003),
            player_labels=dict(elapsed_fields=0x6005),
            compressed_sector_cache=dict(labels=dict(count=0x6007)))
        code,labels,rows=build(metadata)
        for row in rows:
            m=Z80Machine();m.set_memory_block(labels['step'],code)
            m.set_memory_block(0x7000,b'\x3e\x01\xc9')
            for at,value in ((0x6000,4),(0x6002,10),(0x6004,11),(READY,1)):
                m.memory[at]=value
            m.set_memory_block(0x6005,(99).to_bytes(2,'little'))
            m.set_memory_block(DEADLINE,(100).to_bytes(2,'little'))
            m.set_memory_block(0x7fee,b'\x00\x01');m.sp=0x7fee;m.pc=labels['step']
            target=row['address'];m.set_breakpoint(target);m.set_breakpoint(0x100)
            m.ticks_to_stop=10000
            while m.pc!=0x100:
                if m.pc==target:
                    # Register-preserving publication updates, applied at an
                    # instruction boundary. This tests the race, not AY IRQ cost.
                    m.memory[READY]=0
                    m.set_memory_block(0x6005,(100).to_bytes(2,'little'))
                    m.set_memory_block(DEADLINE,(105).to_bytes(2,'little'))
                    m.clear_breakpoint(target)
                self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
            self.assertEqual(m.a,0,row)


if __name__=='__main__':unittest.main()
