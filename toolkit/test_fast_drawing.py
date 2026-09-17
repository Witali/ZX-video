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


def execute_packet(player,labels,packet,base=0x40,start=0x90FD):
    cpu=CPU(player,b'')
    cpu.pc=labels['command_loop'];cpu.ix=start;cpu.port_7ffd=0x17
    cpu.sp=0xBFF0;cpu.push(0x5F00)
    cpu.alt_h=0x12;cpu.alt_l=0x34
    for bank in (5,7):cpu.banks[bank][:6912]=bytes([0xA5])*6912
    cpu.write8(labels['update_base'],base)
    for i,value in enumerate(packet):cpu.write8(start+i,value)
    while cpu.pc!=0x5F00:
        if cpu.steps>200000:raise AssertionError('packet did not terminate')
        cpu.step()
    assert cpu.ix==start+len(packet),'packet pointer'
    assert cpu.sp==0xBFF0,'stack balance'
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
        for length in range(2,33):
            tail=bytes([31-length])+bytes(range(32-length)) if length<32 else b''
            cases.append((95,bytes([0x80+length-2,197])+tail))
        for length in range(1,33):
            tail=bytes([0x80+30-length,97]) if length<31 else bytes([0,97]) if length==31 else b''
            cases.append((95,bytes([length-1])+rng.randbytes(length)+tail))
        for row,packed in cases:
            pos=0;literal_tokens=repeat_tokens=literal_bytes=repeat_bytes=0
            literal_delta=repeat_delta=0
            while pos<len(packed):
                token=packed[pos];pos+=1
                if token&128:
                    repeat_tokens+=1;repeat_bytes+=(token&127)+2;pos+=1
                    n=(token&127)+2
                    repeat_delta+=(-2 if n%2 else 16)-21*(n//2)
                else:
                    literal_tokens+=1;literal_bytes+=token+1;pos+=token+1
                    n=token+1
                    literal_delta+=-2 if n==1 else (4 if n%2 else 22)-45*(n//2)
            self.assertEqual(literal_bytes+repeat_bytes,32)
            payload=bytes([row,len(packed)])+packed
            for base in (0x40,0xC0):
                old,old_t=execute(*legacy,'command_row_rle',payload,base,start=0x80FD)
                new,new_t=execute(*fast,'command_row_rle',payload,base,start=0x80FD)
                self.assertEqual(new,old)
                self.assertEqual(old_t,208+95*literal_tokens+152*repeat_tokens+183*literal_bytes+167*repeat_bytes)
                self.assertEqual(new_t,215+50*literal_tokens+155*repeat_tokens+90*literal_bytes+39*repeat_bytes+literal_delta+repeat_delta)
                self.assertLess(new_t,old_t)

    def test_rle_chains_preserve_stream_and_exit_to_other_commands(self):
        legacy=codec.build_player(0,0,blocked=True,clocked=True)
        fast=codec.build_player(0,0,blocked=True,clocked=True,fast_draw=True)
        for count in (1,2,4,96):
            rows=b''.join(bytes([codec.CMD_BITMAP_ROW_RLE,row,2,158,row*37%256])
                          for row in range(count))
            for base in (0x40,0xC0):
                old,old_t=execute_packet(*legacy,rows+b'\0',base)
                new,new_t=execute_packet(*fast,rows+b'\0',base)
                self.assertEqual(new,old)
                # Each standalone row costs 1298 T, dispatch costs 123 T,
                # each successful chain removes 172 T, and END costs 44 T.
                self.assertEqual(new_t,count*(1298+123)-172*(count-1)+44)
                self.assertLess(new_t,old_t)
                # A points command breaks the chain, followed by another RLE.
                separator=bytes([codec.CMD_BITMAP_POINTS,95,1,31,129])
                packet=rows+separator+rows+b'\0'
                self.assertEqual(execute_packet(*fast,packet,base)[0],
                                 execute_packet(*legacy,packet,base)[0])

    def test_rra_model_preserves_zero_and_rotates_through_carry(self):
        cpu=CPU(bytes([0x1F]),b'')
        for value in range(256):
            for carry in (False,True):
                for zero in (False,True):
                    cpu.pc=0x6000;cpu.a=value;cpu.carry=carry;cpu.z=zero
                    start=cpu.tstates;cpu.step()
                    self.assertEqual((cpu.a,cpu.carry,cpu.z,cpu.tstates-start),
                                     ((value>>1)|(int(carry)<<7),bool(value&1),zero,4))

    def test_rle_pairs_and_chains_survive_irq_in_both_screen_banks(self):
        from test_memory_clock import fixture
        rows=[]
        for n in range(1,33):
            tail=bytes([0x80+30-n,97]) if n<31 else bytes([0,97]) if n==31 else b''
            packed=bytes([n-1])+bytes((x*37+n)%256 for x in range(n))+tail
            rows.append(bytes([codec.CMD_BITMAP_ROW_RLE,len(rows),len(packed)])+packed)
        for n in range(2,33):
            tail=bytes([31-n])+bytes(range(32-n)) if n<32 else b''
            packed=bytes([0x80+n-2,n*37%256])+tail
            rows.append(bytes([codec.CMD_BITMAP_ROW_RLE,len(rows),len(packed)])+packed)
        packet=b''.join(rows)+b'\0'
        legacy=codec.build_player(0,0,blocked=True,clocked=True)
        for base in (0x40,0xC0):
            expected,_=execute_packet(*legacy,packet,base)
            cpu,labels=fixture(direct_input=True,wrapped_input=True)
            for bank in (5,7):cpu.banks[bank][:6912]=bytes([0xA5])*6912
            cpu.write8(labels['update_base'],base)
            for i,value in enumerate(packet):cpu.write8(0x60FD+i,value)
            cpu.pc=labels['command_loop'];cpu.ix=0x60FD;cpu.push(0x5F00);cpu.iff1=True
            next_irq=cpu.tstates+233;interrupts=0
            while cpu.pc!=0x5F00:
                self.assertLess(cpu.steps,100000)
                cpu.step()
                if cpu.iff1 and cpu.tstates>=next_irq and cpu.pc!=0x5F00:
                    cpu.push(cpu.pc);cpu.pc=0xBDBD;cpu.iff1=False;cpu.tstates+=19
                    next_irq=cpu.tstates+233;interrupts+=1
            self.assertGreater(interrupts,100)
            self.assertEqual(cpu.sp,0xBFF0)
            self.assertEqual(cpu.ix,0x60FD+len(packet))
            self.assertEqual(bytes(cpu.banks[5 if base==0x40 else 7][:6912]),expected)


if __name__=='__main__':unittest.main()
