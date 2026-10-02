"""Exercise the assembled instructions, including all IMA state transitions."""
import json
import unittest
from pathlib import Path
import numpy as np
from z80 import Z80Machine
from ima_codec import encode,decode,transition
from ima_player import program,layout,build_disk,ORIGIN
from verify_ima import native_check


class ImaTests(unittest.TestCase):
    def test_all_states_and_clipping(self):
        sections,_=layout(); blob,meta=program(sections); labels=meta['player_labels']
        count=0
        for predictor in (-32768,0,32767):
            for index in range(89):
                for code in range(16):
                    m=Z80Machine();m.set_memory_block(ORIGIN,blob)
                    # PDM BC/DE and input HL are main; table HL is alternate.
                    setup=bytes.fromhex('01 fe 10 16 80 1e 00 08 3e 80 08 d9 21')
                    setup+=(meta['table_base']+64*index).to_bytes(2,'little')+bytes.fromhex('d9 c3')
                    m.set_memory_block(0x7800,setup+labels['low'].to_bytes(2,'little'))
                    m.memory[0xc000]=code;m.hl=0xc000;m.ix=predictor+32768
                    m.pc=0x7800;m.sp=0x6000
                    m.set_breakpoint(labels['high']);m.ticks_to_stop=1000
                    pulses=[];m.set_output_callback(lambda port,value:pulses.append((port,value)))
                    while m.pc!=labels['high']:
                        if m.run()&m._TICKS_LIMIT_HIT: self.fail('decode exceeded budget')
                    wanted,state=transition(predictor,index,code)
                    self.assertEqual(m.ix,wanted+32768)
                    self.assertEqual(len(pulses),6)
                    self.assertTrue(all(port==0x10fe and not value&15 for port,value in pulses))
                    count+=1
        print(json.dumps(dict(exhaustive_native_transitions=count)),flush=True)

    def test_two_nonrepeating_full_loops(self):
        sections,_=layout();size=sum(s['bytes'] for s in sections)
        packed=np.random.default_rng(1977).integers(0,256,size,dtype=np.uint8).tobytes()
        disk,meta=build_disk(packed)
        print(json.dumps(native_check(disk,meta,packed)),flush=True)

    def test_format_and_capacity(self):
        source=np.array([0,128,255,128]*100,dtype=np.uint8)
        packed=encode(source);pcm,indices=decode(packed)
        self.assertEqual(len(packed)*2,len(source));self.assertEqual(len(pcm),len(source))
        self.assertTrue(np.all(indices<=88))
        with self.assertRaises(ValueError): encode(source[:-1])
        with self.assertRaises(ValueError): build_disk(b'\0'*16384)


if __name__=='__main__': unittest.main()
