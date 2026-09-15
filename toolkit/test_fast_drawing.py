"""Compare all native row addresses and exact T-states of bitmap commands."""
import random
import unittest

import build_fast_sparse_trd as codec
from validate_fast_sparse import CPU


def execute(player,labels,command,payload,base=0x40,start=0x8000):
    cpu=CPU(player,b'')
    cpu.pc=labels[command];cpu.ix=start;cpu.port_7ffd=0x17
    cpu.alt_h=0x12;cpu.alt_l=0x34
    for bank in (5,7):cpu.banks[bank][:6912]=bytes([0xA5])*6912
    cpu.write8(labels['update_base'],base)
    for i,value in enumerate(payload):cpu.write8(start+i,value)
    while cpu.pc!=labels['command_loop']:
        if cpu.steps>10000:raise AssertionError('command did not terminate')
        cpu.step()
    assert cpu.ix==start+len(payload),'packet pointer'
    assert (cpu.alt_h,cpu.alt_l)==(0x12,0x34),'clock register'
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
                            old,old_t=execute(*legacy,command,payload,base,start=0x80FD)
                            new,new_t=execute(*fast,command,payload,base,start=0x80FD)
                            self.assertEqual(new,old)
                            self.assertLess(new_t,old_t)
                            self.assertEqual((old_t,new_t),
                                (2067+64*count,984+60*count) if command=='command_row'
                                else (260+265*count,207+114*count if count else 217))

    def test_spans_gaps_lengths_and_page_crossings(self):
        legacy=codec.build_player(0,0,blocked=True,clocked=True)
        fast=codec.build_player(0,0,blocked=True,clocked=True,fast_draw=True)
        rng=random.Random(733)
        for row in range(96):
            cases=[[],[(0,16),(0,16)],[(15,1),(15,1)],[(0,1)]*15]
            for _ in range(8):
                spans=[];column=0
                for _ in range(6):
                    if column==32:break
                    gap=rng.randrange(min(15,31-column)+1)
                    length=rng.randrange(1,min(16,32-column-gap)+1)
                    spans.append((gap,length));column+=gap+length
                cases.append(spans)
            for spans in cases:
                payload=bytes([row,len(spans)])+b''.join(
                    bytes([gap*16+length-1])+rng.randbytes(length) for gap,length in spans)
                count=sum(n for _,n in spans)
                for base in (0x40,0xC0):
                    old,old_t=execute(*legacy,'command_spans',payload,base,start=0x80FD)
                    new,new_t=execute(*fast,'command_spans',payload,base,start=0x80FD)
                    self.assertEqual(new,old)
                    self.assertEqual((old_t,new_t),(220+178*len(spans)+126*count,
                                                 243+122*len(spans)+90*count))
                    if spans:self.assertLess(new_t,old_t)

    def test_rle_literals_repeats_and_all_dither_values(self):
        legacy=codec.build_player(0,0,blocked=True,clocked=True)
        fast=codec.build_player(0,0,blocked=True,clocked=True,fast_draw=True)
        rng=random.Random(712)
        cases=[]
        for row in range(96):
            for data in (rng.randbytes(32),bytes([row])*32,bytes([7])*3+bytes(range(29)),
                         bytes([0])*16+bytes([255])*16,bytes([31])*31+bytes([30])):
                cases.append((row,codec.encode_byte_rle(data)))
        cases.extend((47,codec.encode_byte_rle(bytes([v])*32)) for v in range(256))
        cases.append((95,bytes([0x80,7,0x80+28,9])))  # Legal length-2 repeat.
        for row,packed in cases:
            pos=0;literal_tokens=repeat_tokens=literal_bytes=repeat_bytes=0
            while pos<len(packed):
                token=packed[pos];pos+=1
                if token&128:
                    repeat_tokens+=1;repeat_bytes+=(token&127)+2;pos+=1
                else:
                    literal_tokens+=1;literal_bytes+=token+1;pos+=token+1
            self.assertEqual(literal_bytes+repeat_bytes,32)
            payload=bytes([row,len(packed)])+packed
            for base in (0x40,0xC0):
                old,old_t=execute(*legacy,'command_row_rle',payload,base,start=0x80FD)
                new,new_t=execute(*fast,'command_row_rle',payload,base,start=0x80FD)
                self.assertEqual(new,old)
                self.assertEqual(old_t,208+95*literal_tokens+152*repeat_tokens+183*literal_bytes+167*repeat_bytes)
                self.assertEqual(new_t,189+50*literal_tokens+147*repeat_tokens+90*literal_bytes+47*repeat_bytes)
                self.assertLess(new_t,old_t)


if __name__=='__main__':unittest.main()
