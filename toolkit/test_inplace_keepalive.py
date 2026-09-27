"""Cycle counts, current-cylinder ownership and real IRQ stress for maintenance."""
import argparse
import json
from pathlib import Path
import unittest

import ay_interrupt
import playback_schedule
from benchmark_compact_screen import STACK, STOP
from benchmark_context_huffman import word
from build_fap3_trd import sha
from build_zxv_trd import MiniAssembler
from inplace_keepalive_player import CODE, build
from test_fap3_disk import install
from test_inplace_slot import block, fixture

ROOT = Path(__file__).parent
REGISTERS = ('a','b','c','d','e','h','l','ix','iy','z','carry','alt_a','alt_b','alt_c',
             'alt_d','alt_e','alt_h','alt_l','alt_z','alt_carry','port_7ffd')


def setup():
    h = fixture([block(800, literal=True), block(15872)])
    code, labels, rows = build(h.d, h.elapsed_fields, h.p['last_read_field'])
    install(h.cpu, CODE, code); h.instructions.update({r['address']:r for r in rows})
    base = type(h.cpu)
    class PoisonSeekCPU(base):
        def instruction(self):
            poison = self.pc==labels['keepalive_enter']
            ticks = super().instruction()
            if poison:
                for name in ('ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
                    setattr(self,name,0)
                self.alt_z=self.alt_carry=False
            return ticks
    h.cpu.__class__ = PoisonSeekCPU
    h.cpu.i = 0xbe; h.cpu.im = 2; h.cpu.iff1 = True; word(h.cpu,0xbdbe,0xbd80)
    return h, labels, rows, code


def run_case(*, cached=3, before=100, now=164, remaining=7, interrupt=None):
    h, labels, rows, code = setup(); c = h.cpu
    c.write8(h.d['cached_track'], cached)
    word(c,h.d['disk_position'],4*256+7)  # next track is deliberately different
    word(c,h.d['remaining'],remaining); word(c,h.p['last_read_field'],before); word(c,h.elapsed_fields,now)
    c.write8(0x5cfe,0x84)
    for i, name in enumerate(REGISTERS): setattr(c,name,0x35+i if name not in ('z','carry','alt_z','alt_carry','port_7ffd') else True if name!='port_7ffd' else 0x1f)
    saved = {n:getattr(c,n) for n in REGISTERS}
    protected = {b:bytes(c.banks[b]) for b in (0,1,3,4,6,7)}; screen = bytes(c.banks[5][:6912])
    ticks = h.call(labels['check'],interrupt)
    if ({n:getattr(c,n) for n in REGISTERS}!=saved or c.sp!=STACK
            or any(bytes(c.banks[b])!=v for b,v in protected.items()) or bytes(c.banks[5][:6912])!=screen
            or word(c,h.d['disk_position'])!=4*256+7 or word(c,h.d['remaining'])!=remaining
            or c.read8(h.d['cached_track'])!=cached or c.read8(0x5cfe)!=0x84 or c.reads
            or (c.im,c.i,word(c,0xbdbe),c.iff1)!=(2,0xbe,0xbd80,True)):
        raise AssertionError('maintenance changed caller, disk cursor, bank or IRQ contract')
    return dict(cached=cached,before=before,now=now,remaining=remaining,
        tstates=ticks,wrapper_delta_tstates=ticks+27,seek_calls=c.seek_calls,
        last_service=word(c,h.p['last_read_field']),preserves_state=True,
        instruction_histogram=[dict(address=pc,tstates=t,count=n,instruction=h.instructions[pc]['instruction'])
            for (pc,t),n in sorted(h.histogram.items())]), code, labels, rows


class KeepaliveTests(unittest.TestCase):
    def test_threshold_wrap_first_read_and_eof(self):
        for before,now,cached,remaining,due in (
                (100,163,3,7,False),(100,164,3,7,True),(65520,48,3,7,True),
                (100,356,3,7,True),(100,164,255,7,False),(100,164,254,7,False),
                (100,164,3,0,False)):
            row,*_ = run_case(before=before,now=now,cached=cached,remaining=remaining)
            self.assertEqual(row['seek_calls'],[(0x3e44,cached//2,0)] if due else [])
            self.assertEqual(row['last_service'],now if due else before)

    def test_every_current_track_without_changing_side_or_reading(self):
        for cached in range(160):
            row,*_ = run_case(cached=cached)
            self.assertEqual(row['seek_calls'],[(0x3e44,cached//2,0)])

    def test_real_ay_irq_at_each_maintenance_instruction(self):
        h, labels, _, _ = setup(); c = h.cpu
        a = MiniAssembler(0x9400); ay_interrupt.emit(a)
        playback_schedule.emit_clock(a,dos_irq=True,full_rom_clock=True,memory_clock=True,audio_irq=True)
        ay_interrupt.emit_variables(a); a.label('elapsed_fields'); a.word(0); a.label('fatal'); a.emit(0x76)
        install(c,0x9400,a.resolve()); c.pc,c.sp=a.labels['setup_clock'],STACK; c.push(STOP)
        while c.pc!=STOP:c.step()
        c.write8(a.labels['audio_enabled'],1); c.write8(h.d['cached_track'],159)
        word(c,h.elapsed_fields,100); word(c,h.p['last_read_field'],0)
        calls = 0
        def irq(cpu):
            nonlocal calls
            if not cpu.iff1:return 0
            word(cpu,a.labels['audio_remaining'],65535); index=cpu.read8(a.labels['audio_read_index'])
            at=ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(at,1);cpu.write8(at+1,8);cpu.write8(at+2,calls&15)
            cpu.write8(a.labels['audio_write_index'],(index+1)&31)
            saved={n:getattr(cpu,n) for n in REGISTERS}; pc,sp,start=cpu.pc,cpu.sp,cpu.tstates
            cpu.push(pc);cpu.pc=0xbdbd;cpu.iff1=False;cpu.tstates+=19
            while cpu.pc!=pc:
                self.assertNotEqual(cpu.pc,a.labels['fatal']);cpu.step()
            self.assertEqual(saved,{n:getattr(cpu,n) for n in REGISTERS});self.assertEqual(cpu.sp,sp)
            self.assertEqual(cpu.ay[8],calls&15);calls+=1
            return cpu.tstates-start
        h.call(labels['check'],irq)
        self.assertGreater(calls,60); self.assertEqual(c.seek_calls,[(0x3e44,79,0)])
        self.assertEqual(word(c,a.labels['audio_underruns']),0);self.assertEqual(c.reads,[])


def report(path):
    cases=[]
    for name,params in (
        ('recent',dict(now=163)),('due',{}),('wrapped',dict(before=65520,now=48)),
        ('long',dict(now=356)),('uninitialized',dict(cached=255)),
        ('invalidated',dict(cached=254)),('eof',dict(remaining=0))):
        row,code,labels,listing=run_case(**params);cases.append(dict(name=name,**row))
    data=dict(complete=True,release=False,scope=__doc__,cases=cases,
        implementation=dict(address=CODE,code_hex=code.hex(),labels=labels,listing=listing),
        preserves_both_register_sets=True,rom_mocked=True,
        note='Includes helper RET and shared adapter restoration; excludes caller CALL and ROM/IRQ/ULA. '
             'Wrapper delta adds 27 T. Repeated queue checks and real ROM latency need integrated measurement.',
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('test_inplace_keepalive.py','inplace_keepalive_player.py','inplace_slot_input_z80.py',
             'benchmark_inplace_slot.py','test_inplace_slot.py','fap3_disk_z80.py')})
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps([{k:r[k] for k in ('name','tstates','wrapper_delta_tstates')} for r in cases]),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--report',type=Path);args=p.parse_args()
    if args.report:report(args.report)
    else:unittest.main(argv=['test_inplace_keepalive'])
