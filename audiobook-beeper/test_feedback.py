"""Table quantizer and assembled lookup/IMA arithmetic boundary coverage."""
import json,unittest
from pathlib import Path
from z80 import Z80Machine
from feedback_player import program,layout,feedback_table
from verify_feedback import step
from ima_codec import STEPS,transition,require_unclipped


class FeedbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.blob,cls.labels=program(layout(),Path(__file__).resolve().parents[1]/'.tmp/feedback-unit')

    def test_every_pcm_and_feedback_state(self):
        table=feedback_table();count=0
        for pcm in range(256):
            for state in range(64):
                word,nxt=step(pcm,state);offset=((pcm>>2)*64+state)*2
                self.assertEqual(table[offset:offset+2],bytes([word,nxt*2]))
                m=Z80Machine();m.set_memory_block(0x8000,self.blob)
                m.pc=self.labels['low_sample'];m.ix=pcm<<8;m.b=state*2;m.e=0x96;m.af=0xffff
                m.set_breakpoint(self.labels['high']);m.ticks_to_stop=500
                while m.pc!=self.labels['high']:
                    self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                self.assertEqual((m.c,m.b,m.e),(word,nxt*2,word));count+=1
        print(json.dumps(dict(native_table_cases=count)),flush=True)

    def test_guarded_ima_transitions_and_sample_timing(self):
        checked=0
        halves=[('low'+suffix,'high'+suffix,428) for suffix in ('','1','2','3')]
        halves += [('high','low1',436),('high1','low2',436),('high2','low3',436),('high3','low',446)]
        for half,finish,total in halves:
            for predictor in (-32768,-12000,0,12000,32767):
                for index,step_size in enumerate(STEPS):
                    for code in range(16):
                        delta=(step_size>>3)+(step_size if code&4 else 0)+(step_size>>1 if code&2 else 0)+(step_size>>2 if code&1 else 0)
                        if not -32768<=predictor+(-delta if code&8 else delta)<=32767:continue
                        m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(0x8000,self.blob)
                        m.pc=self.labels[half];m.iy=0xc040;m.ix=predictor+32768
                        m.alt_hl=0x8700+64*index;m.b=(checked%64)*2;m.e=0x96;m.af=0xffff
                        m.memory[0xc040]=code if half.startswith('low') else code<<4
                        before=bytes(m.memory);state=checked%64;values=[];times=[]
                        def output(port,value):
                            self.assertIn(port,(254,4350));values.append(value);times.append(1000-m.ticks_to_stop)
                        m.set_output_callback(output);m.set_breakpoint(self.labels[finish]);m.ticks_to_stop=1000
                        while m.pc!=self.labels[finish]:self.assertFalse(m.run()&m._TICKS_LIMIT_HIT)
                        wanted,idx=transition(predictor,index,code);word,nxt=step((wanted+32768)>>8,state)
                        self.assertEqual(m.ix,wanted+32768);self.assertEqual(m.alt_hl,0x8700+64*idx)
                        self.assertEqual((m.e,m.c,m.b),(word,word,nxt*2))
                        self.assertEqual(values,[16,0,0,16,0,16,16,0])
                        self.assertEqual([b-a for a,b in zip(times,times[1:])],[49,53,56,58,53,56,59])
                        self.assertEqual(1000-m.ticks_to_stop,total);self.assertEqual(bytes(m.memory),before)
                        checked+=1
        print(json.dumps(dict(native_safe_ima_cases=checked)),flush=True)

    def test_unsafe_ima_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'requires saturation'):require_unclipped(b'\x77',32760,0)
        with self.assertRaisesRegex(ValueError,'requires saturation'):require_unclipped(b'\xff',-32760,0)


if __name__=='__main__':unittest.main()
