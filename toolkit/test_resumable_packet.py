"""Actual cold-loaded parser/queue: forced yields, exact packets and IRQ stress.

ROM is mocked and video publication is injected at queue boundaries. This
is a state/cycle test, not an emulated disk-latency or frame-cadence proof.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

from benchmark_bank_local_zx0 import disk_blocks
from benchmark_context_huffman import word
from build_fap3_trd import sha
from test_fap3_disk import DiskCPU
from test_warm_continuation import player, until
from test_inplace_keepalive import REGISTERS
import pipelined_frame_z80 as video
import ay_interrupt

ROOT = Path(__file__).parent
STACK, STOP = 0x9df0, 0x5f00


class CheckedCPU(DiskCPU):
    recording = False
    def instruction(self):
        if self.read8(self.pc) == 0x37:  # SCF: preserve Z, set carry; 4 T.
            self.pc += 1; self.carry = True; return 4
        return super().instruction()

    def write8(self, at, value):
        if self.recording and self.input_start <= at < self.input_end:
            self.writes[at-self.input_start] += 1
        return super().write8(at, value)


def fixture(directory, part):
    stem = f'ZX-video-huffman-preview_part{part:02}'
    image = (directory/(stem+'.trd')).read_bytes(); m = json.loads((directory/(stem+'.json')).read_bytes())
    c = CheckedCPU(player(image), image)
    # Stop after real initialization and mask generation, before any prefill.
    until(c, m['queue_labels']['prefill'])
    c.write8(video.ENABLED, 0)
    _, _, blocks = disk_blocks(directory, part); raw = b''.join(b for _, b in blocks)
    packets = []; pos = 0
    while pos < len(raw):
        size = struct.unpack_from('<H', raw, pos)[0]; pos += 2
        packets.append(raw[pos:pos+size]); pos += size
    if pos != len(raw) or len(packets) != m['frames']: raise ValueError('invalid stored video')
    return c, m, packets, sha(image)


def irq(c, m, serial):
    if not c.iff1: return 0
    a = m['audio_labels']; c.write8(a['audio_enabled'], 1); word(c, a['audio_remaining'], 65535)
    index = c.read8(a['audio_read_index']); at = ay_interrupt.QUEUE_BASE+index*32
    c.write8(at, 1); c.write8(at+1, 8); c.write8(at+2, serial & 15)
    c.write8(a['audio_write_index'], (index+1)&31)
    saved = {n:getattr(c,n) for n in REGISTERS}; pc, sp, before = c.pc, c.sp, c.tstates
    c.push(pc); c.pc = 0xbdbd; c.iff1 = False; c.tstates += 19
    while c.pc != pc: c.step()
    if saved != {n:getattr(c,n) for n in REGISTERS} or c.sp != sp or c.ay[8] != (serial&15):
        raise AssertionError('real IRQ corrupts suspended reader state')
    c.write8(a['audio_enabled'], 0)
    return c.tstates-before


def run(directory, part, *, count, forced, stress, split_length=False):
    c, m, packets, digest = fixture(directory, part)
    candidate = m.get('resumable_packet'); q = m['queue_labels']; gate = candidate['labels']['gate'] if candidate else -1
    if split_length:
        if not candidate or not forced: raise ValueError('split-length case requires the optional reader')
        data = struct.pack('<H',len(packets[0]))+packets[0]
        c.banks[0][0] = data[0]; c.banks[1][:len(data)-1] = data[1:]
        c.write8(q['count'],2); c.write8(q['read_slot'],0); c.write8(q['write_slot'],2)
        c.write8(q['phase'],0); word(c,q['blocks_left'],0); word(c,q['position'],0)
        word(c,q['lengths'],1); word(c,q['lengths']+2,len(data)-1)
        packets = packets[:1]
    rows = {r['address']:r for r in m['slot_queue_instruction_listing']}
    touched = set(); hist = Counter(); results = []; irq_calls = 0
    def call(entry, pause_at=None):
        nonlocal irq_calls
        c.pc = entry; c.sp = STACK; c.push(STOP); before = c.tstates; steps = c.steps; gates = 0; irq_ticks = 0
        while c.pc != STOP:
            if c.pc in (q['fatal'], m['producer_labels']['fatal'], m['decoder_labels']['fatal']):
                raise AssertionError(('reader reached fatal', hex(c.pc)))
            if c.steps-steps > 4000000: raise AssertionError(('reader stalled', hex(c.pc)))
            if c.pc == gate:
                if gates == pause_at: c.write8(video.READY, 0)
                gates += 1
            pc = c.pc; started = c.tstates; c.step(); ticks = c.tstates-started
            # Historical listings retain earlier relocated frame addresses;
            # they must not be mistaken for the overlaid bank-2 ZX0 code.
            # Check all new helper/patch timings; CPU execution still counts
            # every original instruction, including decoder/queue/ROM hooks.
            if pc in rows and rows[pc].get('phase') == 'resumable_packet':
                expected = rows[pc]['tstates']
                if ticks not in (expected if isinstance(expected,list) else [expected]):
                    raise AssertionError(('instruction timing differs',hex(pc),ticks,rows[pc]))
            hist[pc,ticks] += 1
            if candidate and candidate['labels']['required'] <= pc < candidate['labels']['stage']:
                touched.add(pc)
                if stress:
                    irq_ticks += irq(c,m,irq_calls); irq_calls += 1
        if c.sp != STACK or c.port_7ffd&7 != 7: raise AssertionError('caller stack or page differs')
        return c.tstates-before-irq_ticks

    for index, data in enumerate(packets[:count]):
        c.input_start = candidate['sites']['input'] if candidate else 0x6400
        c.input_end = c.input_start+len(data); c.writes = Counter(); c.recording = True
        c.write8(video.READY, 1); before_reads = c.dos_reads; start = c.tstates
        if candidate:
            entry = candidate['labels']['optional'] if forced else candidate['labels']['required']
        else: entry = m['packet_labels']['read_packet']
        ticks = call(entry, 1 if split_length else (0,1,2,20)[index%4] if forced else None)
        paused = bool(candidate and c.a == 0)
        stage = c.read8(candidate['labels']['stage']) if candidate else 0
        if paused:
            if stage not in (1,2): raise AssertionError('invalid suspended parser stage')
            if split_length and (stage != 1 or word(c,q['pending']) != 1 or word(c,q['destination']) != 0xba59):
                raise AssertionError('length was not suspended between its two bytes')
            # Native output/foreground work may reuse all CPU registers.
            # Only the queue/parser RAM continuation may survive this gap.
            for i,n in enumerate(('a','b','c','d','e','h','l','ix','iy','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l')):
                setattr(c,n,0x71+i)
            c.z = c.carry = c.alt_z = c.alt_carry = True
            ticks += call(candidate['labels']['required'])
        c.recording = False
        if bytes(c.read8(c.input_start+i) for i in range(len(data))) != data:
            raise AssertionError(('packet differs',part,index))
        if c.writes != Counter({i:1 for i in range(len(data))}):
            raise AssertionError(('packet lost or copied twice',part,index))
        if candidate and (c.a != 1 or c.read8(candidate['labels']['stage']) or c.read8(candidate['labels']['optional_mode'])):
            raise AssertionError('completed parser did not reset')
        results.append(dict(frame=m['frame_start']+index,bytes=len(data),tstates=ticks,
                            paused=paused,paused_stage=stage,rom_reads=c.dos_reads-before_reads))
    if split_length and (c.read8(q['count']) or word(c,q['pending']) or c.read8(q['read_slot']) != 2):
        raise AssertionError('final split slot was not released exactly at EOF')
    return dict(part=part,frames=results,trd_sha256=digest,forced=forced,irq_stress=stress,split_length=split_length,
        irq_calls=irq_calls,paused=sum(r['paused'] for r in results),
        helper_instruction_addresses=sorted(touched),tstates=sum(r['tstates'] for r in results),
        instruction_histogram=[dict(address=pc,tstates=t,count=n,instruction=rows.get(pc,{}).get('instruction')
                                   if rows.get(pc,{}).get('phase') == 'resumable_packet' else None)
                               for (pc,t),n in sorted(hist.items())],
        every_packet_exact=True,every_packet_byte_written_once=True,stack_and_bank_restored=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory',type=Path,required=True); p.add_argument('--baseline',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True); p.add_argument('--frames',type=int,default=80)
    p.add_argument('--parts',type=int,nargs='+',default=[1,2,3],choices=(1,2,3))
    a = p.parse_args(); report = dict(complete=False,release=False,scope=__doc__,parts=a.parts,volumes=[])
    def save(): a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    save()
    try:
        for part in a.parts:
            row = dict(part=part); report['volumes'].append(row)
            for name,directory,forced,stress,count in (
                    ('baseline',a.baseline,False,False,a.frames),
                    ('required',a.directory,False,False,a.frames),
                    ('resumed',a.directory,True,False,a.frames),
                    ('irq',a.directory,True,True,8)):
                row[name] = run(directory,part,count=count,forced=forced,stress=stress); save()
                print(json.dumps(dict(part=part,case=name,frames=len(row[name]['frames']),
                    paused=row[name]['paused'],tstates=row[name]['tstates'],irq_calls=row[name]['irq_calls'])),flush=True)
            if not row['resumed']['paused'] or not row['irq']['irq_calls']:
                raise AssertionError('suspension/IRQ case was not exercised')
            row['required_delta_tstates'] = row['required']['tstates']-row['baseline']['tstates']
            row['resumed_delta_tstates'] = row['resumed']['tstates']-row['baseline']['tstates']
            row['split_length'] = run(a.directory,part,count=1,forced=True,stress=True,split_length=True)
            save()
        report.update(complete=True,source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('test_resumable_packet.py','resumable_packet_player.py')})
    except Exception as exc: report['failure'] = repr(exc); raise
    finally: save()


if __name__ == '__main__': main()
