"""Exact ZX0-v2 boundary, overlap, bank and real interrupt tests."""
import hashlib
import struct
import unittest
from unittest.mock import patch

from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from benchmark_faster_zx0 import fixture
from inplace_zx0 import trace
from test_inplace_slot import block
import test_inplace_slot as old_tests
from zx0_speed import Token, encode

VARIANTS=('turbo_tuned','fast')


def make_fixture(blocks,first=53,variant='fast'):
    stream=b''.join(struct.pack('<HH',len(raw),len(payload))+payload for payload,raw in blocks)
    return fixture(stream,first,variant)[0]


def requested_decode(payload,raw,variant,targets):
    """Run arbitrary demand requests, including no-op repeated targets."""
    h=make_fixture([(payload,raw)],variant=variant);c=h.cpu
    c.a=0;h.call(h.p['begin'])
    while True:
        h.call(h.p['step'])
        if c.a==1:break
    c.slot,c.payload,c.expected,c.output_base=0,payload,raw,0xc000
    c.input_start=word(c,h.z['input_pointer']);c.produced=c.input_reads=0;c.digest=hashlib.sha256()
    outputs=[]
    for index,target in enumerate(targets):
        c.decoding=False;word(c,h.z['slice_target'],0xc000+target)
        c.pc=h.z['begin' if index==0 else 'slice_until'];c.sp=STACK;c.push(STOP);c.decoding=True
        before=c.steps
        while c.pc!=STOP:
            if c.steps-before>2000000:raise AssertionError('decoder stalled')
            c.step()
        c.decoding=False
        if c.sp!=STACK or c.produced<target or c.port_7ffd&7!=0:raise AssertionError('bad continuation')
        outputs.append((c.produced,c.input_reads))
        for name in ('a','b','c','d','e','h','l','ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
            setattr(c,name,0x97)
        c.z=c.carry=c.alt_z=c.alt_carry=True
    if c.produced!=len(raw) or c.input_reads!=len(payload):raise AssertionError('missing EOF')
    _,proof=trace(payload,limit=len(raw))
    if c.digest.hexdigest()!=proof['write_input_cursors_sha256']:raise AssertionError('overlap cursor changed')
    return outputs


class FasterZX0Tests(unittest.TestCase):
    def test_sector_crossings_bank_rotation_and_shared_carry(self):
        for variant in VARIANTS:
            def supplied(blocks,first=53):return make_fixture(blocks,first,variant)
            with self.subTest(variant=variant),patch.object(old_tests,'fixture',supplied):
                old_tests.InplaceSlotTests().test_header_crossings_first_track_and_full_size_bank_rotation()
                old_tests.InplaceSlotTests().test_shared_sector_and_short_read_retry()

    def test_real_irq_after_every_instruction_preserves_state(self):
        for variant in VARIANTS:
            def supplied(blocks,first=53):return make_fixture(blocks,first,variant)
            with self.subTest(variant=variant),patch.object(old_tests,'fixture',supplied):
                old_tests.InplaceSlotTests().test_real_ay_irq_after_each_producer_and_decoder_instruction()

    def test_gamma_lengths_offset_classes_and_repeated_offsets(self):
        cases=[]
        for offset in (1,2,127,128,129,255,256,257,1024,8193):
            for n in (2,3,7,127,128,255,256,257,1025):
                prefix=bytes((i*47+i//251)&255 for i in range(offset))
                raw=prefix+bytes(prefix[i%offset] for i in range(n))
                # A one-byte literal separates a repeated-offset match;
                # a one-byte repeated match is legal even though a new one is not.
                raw+=b'\x95';raw+=raw[-offset:-offset+1] if offset>1 else b'\x95'
                tokens=[Token(0,offset),Token(offset,n,offset),Token(offset+n,1),Token(offset+n+1,1,offset)]
                cases.append((encode(raw,tokens),raw))
        for variant in VARIANTS:
            h=make_fixture(cases,variant=variant)
            for index,(payload,raw) in enumerate(cases):h.block(payload,raw,index)
            self.assertTrue(h.finish()['sectors_exact_once'])

    def test_unaligned_one_byte_demands_overshoot_repeated_target_and_eof(self):
        for payload,raw in (block(15872),block(2100,literal=True)):
            targets=sorted(set([1,2,3,127,128,255,256,257,511,512,513,len(raw)-1,len(raw)]))
            targets=[n for n in targets for _ in range(2)]
            baseline=requested_decode(payload,raw,'baseline',targets)
            for variant in VARIANTS:
                self.assertEqual(requested_decode(payload,raw,variant,targets),baseline)


if __name__=='__main__':unittest.main()
