"""Guarded IMA and complementary PWM ramp checks using independent Z80 execution."""
import json
import unittest
from z80 import Z80Machine
from ima_codec import STEPS,transition
from ima_player import program,layout,build_disk,ORIGIN


class PwmTests(unittest.TestCase):
    def test_both_nibbles_safe_transitions_and_all_widths(self):
        sections,_=layout();blob,meta=program(sections,pwm=True)
        labels=meta['player_labels'];checked=0;width_counts=[0]*16
        for half,finish in (('low','high'),('high','low')):
            for predictor in (-32768,-12000,0,12000,32767):
                for index,step in enumerate(STEPS):
                    for code in range(16):
                        diff=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
                        raw=predictor+(-diff if code&8 else diff)
                        if not -32768<=raw<=32767:continue
                        q=checked%16;width_counts[q]+=1
                        m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(ORIGIN,blob)
                        m.pc=labels[half+'_first'];m.bc=0x10fe;m.de=0xc040;m.hl=0xffff
                        m.af=q*256+255;m.alt_af=0xffff;m.ix=predictor+32768;m.sp=0x6000
                        m.alt_hl=meta['table_base']+64*index;m.memory[0xc040]=code if half=='low' else code<<4
                        before=bytes(m.memory);times=[];values=[]
                        m.set_breakpoint(labels[finish+'_first']);m.ticks_to_stop=1000
                        def output(port,value):
                            self.assertEqual(port,0x10fe);times.append(1000-m.ticks_to_stop);values.append(value)
                        m.set_output_callback(output)
                        while m.pc!=labels[finish+'_first']:
                            if m.run()&m._TICKS_LIMIT_HIT:self.fail('decode or ramp escaped')
                        wanted,state=transition(predictor,index,code)
                        self.assertEqual(m.ix,wanted+32768)
                        self.assertEqual(m.a,15-((wanted+32768)>>12))
                        self.assertEqual(m.alt_hl,meta['table_base']+64*state)
                        self.assertEqual(values,[16,0,16,0])
                        high=128-4*q
                        self.assertEqual([b-a for a,b in zip(times,times[1:])],[high,226-high,high])
                        self.assertEqual(1000-m.ticks_to_stop,452)
                        self.assertEqual(bytes(m.memory),before);checked+=1
        print(json.dumps(dict(safe_transitions=checked,width_cases=width_counts)),flush=True)

    def test_guard_and_variant_selection(self):
        sections,_=layout();packed=b'\x77'*sum(s['bytes'] for s in sections)
        with self.assertRaisesRegex(ValueError,'requires saturation'):build_disk(packed,pwm=True)
        with self.assertRaisesRegex(ValueError,'one modulation'):build_disk(packed,pwm=True,uniform=True)


if __name__=='__main__':unittest.main()
