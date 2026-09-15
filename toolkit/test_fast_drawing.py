"""Compare all native row addresses and exact T-states of bitmap commands."""
import random
import unittest

import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU


def execute(player,labels,command,payload,base=0x40):
    cpu=CPU(player,b'')
    cpu.pc=labels[command];cpu.ix=0x8000;cpu.port_7ffd=0x17
    cpu.write8(labels['update_base'],base)
    for i,value in enumerate(payload):cpu.write8(0x8000+i,value)
    while cpu.pc!=labels['command_loop']:
        if cpu.steps>10000:raise AssertionError('command did not terminate')
        cpu.step()
    return bytes(cpu.banks[5 if base==0x40 else 7][:6912]),cpu.tstates


class FastDrawingTests(unittest.TestCase):
    def test_every_row_and_sparse_dense_masks(self):
        legacy=codec.build_player(0,0,blocked=True,clocked=True)
        fast=codec.build_player(0,0,blocked=True,clocked=True,fast_draw=True)
        rng=random.Random(83)
        for row in range(96):
            for count in (0,1,2,8,16,32):
                columns=sorted(rng.sample(range(32),count));values=rng.randbytes(count)
                mask=sum(1<<(31-column) for column in columns)
                commands=(('command_row',bytes([row])+mask.to_bytes(4,'big')+values),
                    ('command_points',bytes([row,count])+b''.join(bytes([x,v]) for x,v in zip(columns,values))))
                for command,payload in commands:
                    for base in (0x40,0xC0):
                        with self.subTest(row=row,count=count,command=command,base=base):
                            old,old_t=execute(*legacy,command,payload,base)
                            new,new_t=execute(*fast,command,payload,base)
                            self.assertEqual(new,old)
                            self.assertLess(new_t,old_t)
                            self.assertEqual((old_t,new_t),
                                (2067+64*count,1287+68*count) if command=='command_row'
                                else (260+265*count,220+189*count))


if __name__=='__main__':unittest.main()
