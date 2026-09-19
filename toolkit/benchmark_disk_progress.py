"""Execute per-disk progress through EOF/reset, checking every instruction.

Synthetic disk lengths exercise the display counter; no movie partition,
disk delivery, ULA contention or video cadence is claimed by this report.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import disk_progress_z80 as progress
from benchmark_compact_screen import NativeCPU
from validate_fast_sparse import CPU

STACK,STOP = 0x9df0,0x93f0


class ProgressCPU(NativeCPU):
    def write8(self,address,value):
        if self.guarding:
            allowed = (self.labels['state'] <= address < self.labels['state_end']
                or STACK-96 <= address < STACK
                or any(base <= address < base+32 for base in self.bar_ranges))
            if not allowed or self.port_7ffd & 7 != 7:
                raise AssertionError(f'progress write outside contract {address:04x}')
        return CPU.write8(self,address,value)


class Harness:
    def __init__(self):
        self.cpu = ProgressCPU(b'',b'')
        for bank in self.cpu.banks: bank[:] = b'\xa5'*16384
        self.cpu.port_7ffd = 0x17
        rows = progress.PIXEL_ROWS+(progress.ATTRIBUTE_ROW,)
        self.cpu.bar_ranges = rows+tuple(n+0x8000 for n in rows)

    def load_disk(self,count):
        self.code,self.labels,self.listing,self.deadlines = progress.build(count)
        self.instructions = {r['address']:r for r in self.listing}
        self.cpu.labels = self.labels
        self.cpu.guarding = False
        for i,value in enumerate(self.code): self.cpu.write8(progress.CODE+i,value)
        self.histogram = Counter()
        return self.run('reset')

    def run(self,entry):
        cpu = self.cpu; cpu.guarding = False
        cpu.pc,cpu.sp = self.labels[entry],STACK; cpu.push(STOP)
        start = cpu.tstates; cpu.guarding = True
        while cpu.pc != STOP:
            row = self.instructions[cpu.pc]
            before,pc = cpu.tstates,cpu.pc
            cpu.step(); ticks = cpu.tstates-before
            wanted = row['tstates']
            if ticks not in (wanted if isinstance(wanted,list) else [wanted]):
                raise AssertionError(('instruction timing',row,ticks))
            self.histogram[pc,ticks] += 1
        if cpu.sp != STACK or cpu.port_7ffd != 0x17: raise AssertionError('stack/paging differs')
        cpu.guarding = False
        return cpu.tstates-start


def measure_disk(h,count):
    # A new volume reuses the screens containing the preceding volume's bar.
    previous = {bank:bytes(h.cpu.banks[bank][:6912]) for bank in (5,7)}
    reset = h.load_disk(count)
    if reset != 4298: raise AssertionError(('reset timing',reset))
    for bank in (5,7):
        if bytes(h.cpu.banks[bank][:6912]) != progress.reference_screen(previous[bank],0,count):
            raise AssertionError('reset changed picture or left previous volume progress')
    histogram,events,steps = Counter(),[],0
    for frame in range(1,count+1):
        new_steps = frame*64//count
        ticks = h.run('tick'); histogram[ticks] += 1
        if ticks != progress.expected_tick_tstates(steps,new_steps): raise AssertionError('tick timing differs')
        if h.cpu.read8(h.labels['remaining']) != 64-new_steps: raise AssertionError('wrong progress counter')
        if new_steps != steps: events.append(dict(frame=frame,steps=new_steps,tstates=ticks))
        for bank in (5,7):
            if bytes(h.cpu.banks[bank][:6912]) != progress.reference_screen(previous[bank],frame,count):
                raise AssertionError(('progress screen differs',frame,bank))
        steps = new_steps
    finished = h.run('tick')
    if finished != 28: raise AssertionError('finished countdown did not stop')
    for bank in (5,7):
        if bytes(h.cpu.banks[bank][:6912]) != progress.reference_screen(previous[bank],count,count):
            raise AssertionError('extra publication wrapped progress')
    total = sum(t*n for t,n in histogram.items())
    instruction_total = sum(t*n for (_,t),n in h.histogram.items())
    if instruction_total != reset+total+finished: raise AssertionError('instruction histogram total differs')
    return dict(frames_on_disk=count,steps=64,reset_tstates=reset,code_bytes=len(h.code),
        state_bytes=h.labels['state_end']-h.labels['state'],end=h.labels['end'],events=events,
        tick_histogram=[dict(tstates=t,frames=n) for t,n in sorted(histogram.items())],
        foreground_ticks=total,bridge_extra_tstates=27*count,total_extra_tstates=total+27*count,
        mean_extra_tstates=(total+27*count)/count,finished_tick_tstates=finished)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    h = Harness()
    lengths = (1,2,63,64,65,128,1000,4221,16320,999)
    rows = [measure_disk(h,count) for count in lengths]
    result = dict(scope=__doc__,complete=True,baseline_commit='7608922',release=False,
        disk_delivery_verified=False,cadence_verified=False,synthetic_disk_lengths=list(lengths),
        both_screens_checked_every_frame=True,reset_between_disks=True,
        outside_bar_writes_rejected=True,disks=rows,instruction_listing=h.listing,
        code_hex=h.code.hex(),timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
    args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps([{k:v for k,v in r.items() if k not in ('events','tick_histogram')} for r in rows]))


if __name__ == '__main__': main()
