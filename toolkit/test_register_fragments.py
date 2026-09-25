"""Paired fragment opcodes, complete mixed frames, and instruction-boundary AY."""
import unittest
from benchmark_causal_tiles import Harness,INPUT,BITMAP_MASKS,STACK,STOP
from benchmark_context_huffman import word
import causal_tile_z80 as machine
import probe_fast_fragments as fast
import probe_fragment_channels as channels
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header,read_group,OFFSETS
from test_hybrid_tiles import header
import test_fast_fragments as fixtures
import test_causal_tiles as irq_tests

DELTAS={85:0,86:-68,87:-109,88:-36}


def primitive_cases():
    rows=[]
    for split in (False,True):
        hs=[Harness([bytes([8]*256)]*2,bytes(256),OFFSETS,hybrid=True,skip_empty=True,
            intra_above=True,intra_extended=True,fast_fragments=True,split_literals=split,
            register_fragments=enabled) for enabled in (False,True)]
        for mode in DELTAS:
            for selector in (range(256) if mode==87 else (0,)):
                payload={85:bytes(range(16)),86:b'\x12\xab',87:bytes([0x15,0x51,0x6c,0xc6,selector]),88:b'\x39'}[mode]
                bitmap={85:payload,86:payload*8,87:b''.join(payload[2:4] if selector&(128>>r) else payload[:2] for r in range(8)),88:payload*16}[mode]
                for offset in ((0,) if split else (0,3,7)):
                    for target in (machine.FRAME,machine.FRAME+5*256+14,machine.FRAME+11*256+30):
                        times=[]
                        for enabled,h in enumerate(hs):
                            prefix=b'\xa0' if offset else b''
                            h.begin(prefix+payload if not split else b'',bytes(192),bytes(384),bytes(96),literals=payload if split else None)
                            c=h.cpu;c.guarding=False
                            for i in range(3840):c.write8(machine.FRAME+i,0xa5)
                            expected=bytearray(b'\xa5'*3840)
                            for r in range(8):expected[target-machine.FRAME+32*r:target-machine.FRAME+32*r+2]=bitmap[2*r:2*r+2]
                            word(c,h.labels['target'],target);word(c,h.labels['bitmap_masks'],BITMAP_MASKS)
                            c.a=mode;c.alt_c=0xf0+offset;c.ix=INPUT
                            c.pc=h.labels['fast_fragment'];c.sp=STACK;c.push(STOP);c.guarding=True
                            start=c.tstates
                            while c.pc!=STOP:
                                pc=c.pc;t=c.tstates;c.step();wanted=h.instructions[pc]['tstates']
                                assert c.tstates-t in (wanted if isinstance(wanted,list) else [wanted])
                            elapsed=c.tstates-start
                            assert elapsed==machine.fast_tstates(mode,unaligned=bool(offset),selector=selector,
                                split_literals=split,register_fragments=bool(enabled)),(mode,split,offset,elapsed)
                            assert bytes(c.read8(machine.FRAME+i) for i in range(3840))==expected
                            assert word(c,h.labels['bitmap_masks'])==BITMAP_MASKS+2 and c.sp==STACK
                            assert (h.literal_position()==len(payload)) if split else (c.ix==INPUT+len(prefix)+len(payload))
                            times.append(elapsed)
                        assert times[1]-times[0]==DELTAS[mode]
                        rows.append(dict(mode=mode,split_literals=split,offset=offset,selector=selector,
                            target=target,baseline_tstates=times[0],tstates=times[1],delta_tstates=times[1]-times[0]))
    return rows


class RegisterFragmentTests(unittest.TestCase):
    def test_all_selectors_cursors_targets_and_cycles(self):
        self.assertEqual(len(primitive_cases()),3108)

    def test_mixed_causal_frames_and_both_channels(self):
        states,vectors,residual,selected=fixtures.FastFragmentTests().fixture(3)
        source,_=fast.encode(header(3),states,vectors,residual,bytes(256),[bytes([8]*256)]*2,selected,cap=4500)
        for split,data in ((False,source),(True,channels.split(source,states,vectors,residual)[0])):
            r=Reader(data);_,_,remaining,mapping,tables=read_header(r,magic=b'FSF1' if split else b'FHF1')
            hs=[Harness(tables,mapping,OFFSETS,hybrid=True,skip_empty=True,intra_above=True,intra_extended=True,
                fast_fragments=True,unrolled_motion=True,split_literals=split,register_fragments=v) for v in (False,True)]
            index=0
            while remaining:
                n,_,bits,v,bm,at,encoded=read_group(r,remaining,fast_fragments=True)
                literal=r.take(sum(fast.SIZES.get(x,0) for x in v)) if split else None
                for h in hs:h.begin(encoded,v,bm,at,literals=literal)
                for frame in range(n):
                    old,new=[h.run(frame,states[index+frame].tobytes()) for h in hs]
                    change=sum(DELTAS.get(x,0) for x in v[192*frame:192*(frame+1)])
                    self.assertEqual(new['total_tstates']-old['total_tstates'],change)
                for h in hs:
                    self.assertEqual(h.position(),bits)
                    if split:self.assertEqual(h.literal_position(),len(literal))
                index+=n;remaining-=n
            r.end()

    def test_ay_after_each_instruction(self):
        states,vectors,residual,selected=fixtures.FastFragmentTests().fixture(1)
        source,_=fast.encode(header(1),states,vectors,residual,bytes(256),[bytes([8]*256)]*2,selected)
        for split,data in ((False,source),(True,channels.split(source,states,vectors,residual)[0])):
            irq_tests.CausalTileTests().exercise_irq(True,spatial_data=data,spatial_extended=True,
                fast_fragments=True,unrolled_motion=True,split_literals=split,register_fragments=True)

    def test_requires_fragment_format(self):
        with self.assertRaisesRegex(ValueError,'require fast fragments'):
            machine.build([bytes([8]*256)]*2,bytes(256),OFFSETS,register_fragments=True)


if __name__=='__main__':unittest.main()
