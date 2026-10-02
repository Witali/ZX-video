"""Fast PWM: exact carry choices, timing and guarded IMA transitions."""
import json
import unittest
from z80 import Z80Machine
from ima_codec import STEPS,transition
from ima_player import program,layout,build_disk,ORIGIN


class FastPwmTests(unittest.TestCase):
    def test_safe_transitions_and_width_feedback(self):
        sections,_=layout();blob,meta=program(sections,pwm='fast')
        labels=meta['player_labels'];checked=0;phases=set();levels=set();choices=[0,0]
        for half,finish in (('low','high'),('high','low')):
            for predictor in (-32768,-12000,0,12000,32767):
                for index,step in enumerate(STEPS):
                    for code in range(16):
                        diff=(step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
                        raw=predictor+(-diff if code&8 else diff)
                        if not -32768<=raw<=32767:continue
                        old=checked%256;error=(checked*37+128)%256;levels.add(old);phases.add(error)
                        m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(ORIGIN,blob)
                        m.pc=labels[half];m.bc=0x10fe;m.de=old*256;m.hl=0xc040
                        m.af=0xffff;m.alt_af=error*256+255;m.ix=predictor+32768;m.sp=0x6000
                        m.alt_hl=meta['table_base']+64*index;m.memory[0xc040]=code if half=='low' else code<<4
                        before=bytes(m.memory);times=[];values=[]
                        m.set_breakpoint(labels[finish]);m.ticks_to_stop=1000
                        def output(port,value):
                            self.assertEqual(port,0x10fe);times.append(1000-m.ticks_to_stop);values.append(value)
                        m.set_output_callback(output)
                        while m.pc!=labels[finish]:
                            if m.run()&m._TICKS_LIMIT_HIT:self.fail('decode or PWM escaped')
                        wanted,state=transition(predictor,index,code)
                        self.assertEqual(m.ix,wanted+32768);self.assertEqual(m.d,(wanted+32768)>>8)
                        self.assertEqual(m.alt_hl,meta['table_base']+64*state)
                        self.assertEqual(values,[16,0]*5)
                        intervals=[]
                        for duration in (84,84,84,87,84):
                            error+=old;wide=error>>8;error&=255;choices[wide]+=1
                            high=30+10*wide;intervals.extend((high,duration-high))
                        self.assertEqual([b-a for a,b in zip(times,times[1:])],intervals[:-1])
                        self.assertEqual(m.alt_af>>8,error)
                        self.assertEqual(1000-m.ticks_to_stop,423);self.assertEqual(bytes(m.memory),before)
                        checked+=1
        print(json.dumps(dict(safe_transitions=checked,pcm8_levels=len(levels),initial_error_phases=len(phases),
                              narrow_and_wide_pulses=choices)),flush=True)

    def test_fast_guard(self):
        sections,_=layout();packed=b'\x77'*sum(s['bytes'] for s in sections)
        with self.assertRaisesRegex(ValueError,'requires saturation'):build_disk(packed,pwm='fast')


if __name__=='__main__':unittest.main()
