"""Verify native back-screen output for every saved compact movie frame.

Executes real Z80 opcodes, including bank paging and native bitmap/attribute
writes. Inputs are already reconstructed compact states; this is not yet
the combined player. Host provides the same frame pointer and back-screen
choice a player would use. No disk, metadata, ZX0, IRQ or ULA cost is added.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import compact_screen_z80 as machine
from build_long_video_trd import expand_compact_screen
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU

STACK, STOP = 0x9df0, 0x9df0


class NativeCPU(CPU):
    guarding = False

    def instruction(self):
        # The shared model batches LDIR. Here each repetition is visible,
        # including IRQ boundaries, as specified by the Z80 manual.
        if self.read8(self.pc) == 0xed and self.read8(self.pc+1) == 0xb0:
            self.write8(self.de(), self.read8(self.hl()))
            self.set_hl(self.hl()+1); self.set_de(self.de()+1); self.set_bc(self.bc()-1)
            if self.bc():
                return 21
            self.pc = (self.pc+2) & 65535
            return 16
        return super().instruction()

    def write8(self, address, value):
        if self.guarding:
            screen = ((self.target_bank == 5 and 0x4000 <= address < 0x5b00)
                or (self.target_bank == 7 and self.port_7ffd & 7 == 7 and 0xc000 <= address < 0xdb00))
            if not (screen or self.state[0] <= address < self.state[1] or STACK-96 <= address < STACK):
                raise AssertionError(f'write outside back screen/state/stack: {address:04x}')
        super().write8(address, value)


class Harness:
    def __init__(self, *, first=0, rows=96, paired=True, unrolled_attrs=True):
        self.first, self.rows = first, rows
        self.options = dict(first=first, rows=rows, paired=paired, unrolled_attrs=unrolled_attrs)
        self.code, self.labels, self.listing, self.regions = machine.build(**self.options)
        self.cpu = NativeCPU(b'', b'')
        self.cpu.state = self.labels['state'], self.labels['end']
        for address, blob in [(machine.CODE, self.code)]+self.regions:
            for i, value in enumerate(blob):
                self.cpu.write8(address+i, value)
        self.instructions = {r['address']: r for r in self.listing}
        self.histogram = Counter()
        self.expected_screens = {5: bytes(6912), 7: bytes(6912)}
        self.pages = []

    def run(self, state, index, interrupt=None):
        if (len(state) != 3840 or any(state[:self.first*32])
                or any(state[(self.first+self.rows)*32:3072])):
            raise ValueError('state has nonzero bitmap outside configured rows')
        cpu = self.cpu
        cpu.guarding = False
        target = 7 if index % 2 == 0 else 5
        page = 0x16 if target == 7 else 0x1e
        cpu.port_7ffd, cpu.target_bank = page, target
        for i, value in enumerate(state):
            cpu.write8(machine.FRAME+i, value)
        cpu.write8(self.labels['saved_page'], page)
        for name in ('b', 'c', 'd', 'e', 'h', 'l', 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l'):
            setattr(cpu, name, 0x97)
        cpu.a, cpu.ix, cpu.z, cpu.carry = 0xc0 if target == 7 else 0x40, 0x1122, True, False
        cpu.pc, cpu.sp = self.labels['draw'], STACK
        cpu.push(STOP); cpu.guarding = True
        before, previous_page, irq, steps = cpu.tstates, page, 0, 0
        stages, pages = Counter(), []
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            row = self.instructions[pc]
            cpu.step(); steps += 1
            elapsed = cpu.tstates-ticks
            wanted = row['tstates']
            if elapsed not in (wanted if isinstance(wanted, list) else [wanted]):
                raise AssertionError(('instruction timing', row, elapsed))
            stages[row['stage']] += elapsed; self.histogram[pc, elapsed] += 1
            if cpu.port_7ffd != previous_page:
                pages.append(cpu.port_7ffd); previous_page = cpu.port_7ffd
            if steps > 100000:
                raise AssertionError('renderer did not return')
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        bitmap, attrs = expand_compact_screen(state)
        expected = bitmap+attrs
        self.expected_screens[target] = expected
        if any(bytes(cpu.banks[b][:6912]) != screen for b, screen in self.expected_screens.items()):
            raise AssertionError('native screen differs or visible screen changed')
        if (cpu.port_7ffd != page or cpu.sp != STACK or pages != [page | 1, page]
                or bytes(cpu.read8(machine.FRAME+i) for i in range(3840)) != state
                or sum(stages.values()) != cpu.tstates-before-irq
                or sum(stages.values()) != machine.expected_tstates(**self.options)):
            raise AssertionError(('paging/stack/source/timing differs', sum(stages.values()), machine.expected_tstates(**self.options)))
        return dict(index=index, target_bank=target, tstates=sum(stages.values()), stages=dict(stages),
                    output_sha256=sha(expected), page_writes=pages, irq_tstates=irq)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--cpu-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--first', type=int, help='default: first nonzero bitmap row of the whole movie')
    p.add_argument('--rows', type=int, help='default: cover through the last nonzero row')
    args = p.parse_args()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    reconstruction = json.loads(args.cpu_report.read_text(encoding='utf-8'))
    if (states.dtype != np.uint8 or states.shape != (4971, 3840) or not reconstruction['complete']
            or reconstruction['states_sha256'] != sha(states.tobytes())
            or len(reconstruction['frames']) != len(states)):
        raise ValueError('different/incomplete compact states')
    raster = states[:, :3072].reshape(-1, 96, 32)
    used = np.flatnonzero(raster.any(axis=(0, 2)))
    first = args.first if args.first is not None else int(used[0]) if len(used) else 0
    rows = args.rows if args.rows is not None else int(used[-1])+1-first if len(used) else 1
    if np.any(raster[:, :first]) or np.any(raster[:, first+rows:]):
        raise ValueError('configured rows omit nonzero movie pixels')
    h = Harness(first=first, rows=rows)
    old = Harness(first=first, rows=rows, paired=False, unrolled_attrs=False)
    # Baseline timing is data independent. Cover page boundaries and both
    # banks here, rather than repeating an identical count 4971 times.
    baseline = [old.run(states[i].tobytes(), i) for i in range(2)]
    report = dict(scope=__doc__, baseline_commit='d4f2b15', complete=False,
        states_sha256=sha(states.tobytes()), reconstruction_report_sha256=sha(args.cpu_report.read_bytes()),
        options=h.options, code_bytes=h.labels['state']-machine.CODE, state_bytes=3,
        nonzero_bytes_per_logical_row=np.count_nonzero(raster, axis=(0, 2)).tolist(),
        code_hex=h.code.hex(), labels=h.labels, instruction_listing=h.listing,
        tables=[dict(base=b, bytes=len(v), sha256=sha(v)) for b, v in h.regions],
        baseline_options=old.options, baseline_code_hex=old.code.hex(), baseline_labels=old.labels,
        baseline_instruction_listing=old.listing, baseline_frames=baseline,
        deterministic_tstates=machine.expected_tstates(**h.options),
        baseline_tstates=machine.expected_tstates(**old.options), frames=[],
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        full_frame_delivery_measured=False, player_changed=False, integrated_player_delta_tstates=0)
    for index, state in enumerate(states):
        measured = h.run(state.tobytes(), index)
        measured['reconstruction_and_output_tstates'] = reconstruction['frames'][index]['total_tstates']+measured['tstates']
        report['frames'].append(measured)
        if index % 250 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'Native Z80 output verified {index+1}/{len(states)}', flush=True)
    work = [f['reconstruction_and_output_tstates'] for f in report['frames']]
    report['instruction_histogram'] = [dict(address=a, tstates=t, count=n) for (a, t), n in sorted(h.histogram.items())]
    if sum(r['tstates']*r['count'] for r in report['instruction_histogram']) != len(states)*report['deterministic_tstates']:
        raise AssertionError('histogram differs')
    report['summary'] = dict(frames=len(states), output_tstates=len(states)*report['deterministic_tstates'],
        delta_output_tstates=len(states)*(report['deterministic_tstates']-report['baseline_tstates']),
        reconstruction_and_output_tstates=sum(work), max_reconstruction_and_output_tstates=max(work),
        worst_frame=work.index(max(work)), frames_over_nominal_425448=sum(t > 425448 for t in work),
        mean_reconstruction_and_output_tstates=sum(work)/len(work))
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
