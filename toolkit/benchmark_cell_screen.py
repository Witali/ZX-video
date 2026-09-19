"""Execute actual marked-cell/dense-band output for the whole edited movie.

Host supplies verified n-2 masks and already reconstructed compact frames.
The 80-byte map copy, pixel/attribute writes and page switching run on Z80.
Metadata/ZX0, IRQ/ULA, ROM/disk and combined memory placement are separate.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import cell_screen_z80 as machine
from benchmark_compact_screen import NativeCPU, STACK, STOP
from build_long_video_trd import expand_compact_screen
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU

INPUT = 0xa400


class CellCPU(NativeCPU):
    def write8(self, address, value):
        if self.guarding and machine.MASK <= address < machine.MASK+80:
            return CPU.write8(self, address, value)
        return super().write8(address, value)


class Harness:
    def __init__(self):
        self.code, self.labels, self.listing, self.regions = machine.build()
        self.cpu = CellCPU(b'', b'')
        self.cpu.state = self.labels['state'], self.labels['end']
        for address, blob in [(machine.CODE, self.code)]+self.regions:
            for i, value in enumerate(blob):
                self.cpu.write8(address+i, value)
        self.instructions = {r['address']: r for r in self.listing}
        self.histogram = Counter()
        self.expected_screens = {5: bytes(6912), 7: bytes(6912)}

    def run(self, state, mask, index, interrupt=None):
        if len(state) != 3840 or len(mask) != 80 or any(state[:256]) or any(state[2816:3072]):
            raise ValueError('invalid frame/map or nonzero omitted rows')
        cpu = self.cpu
        cpu.guarding = False
        target = 7 if index % 2 == 0 else 5
        page = 0x16 if target == 7 else 0x1e
        cpu.port_7ffd, cpu.target_bank = page, target
        for base, blob in ((machine.FRAME, state), (INPUT, mask)):
            for i, value in enumerate(blob):
                cpu.write8(base+i, value)
        cpu.write8(self.labels['saved_page'], page)
        for name in ('b', 'c', 'd', 'e', 'h', 'l', 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l'):
            setattr(cpu, name, 0x97)
        cpu.a, cpu.ix, cpu.z, cpu.carry = 0xc0 if target == 7 else 0x40, 0x1122, True, False
        cpu.set_hl(INPUT)
        cpu.pc, cpu.sp = self.labels['draw'], STACK
        cpu.push(STOP); cpu.guarding = True
        before, previous_page, irq, steps = cpu.tstates, page, 0, 0
        stages, pages = Counter(), []
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            row = self.instructions[pc]
            cpu.step(); steps += 1
            elapsed = cpu.tstates-ticks
            if elapsed != row['tstates']:
                raise AssertionError(('instruction timing', row, elapsed))
            stages[row['stage']] += elapsed; self.histogram[pc, elapsed] += 1
            if cpu.port_7ffd != previous_page:
                pages.append(cpu.port_7ffd); previous_page = cpu.port_7ffd
            if steps > 100000:
                raise AssertionError('renderer did not return')
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        expected = b''.join(expand_compact_screen(state))
        self.expected_screens[target] = expected
        if any(bytes(cpu.banks[b][:6912]) != screen for b, screen in self.expected_screens.items()):
            raise AssertionError('native screen differs or visible screen changed')
        if (cpu.port_7ffd != page or cpu.sp != STACK or pages != [page | 1, page]
                or bytes(cpu.read8(machine.FRAME+i) for i in range(3840)) != state
                or bytes(cpu.read8(INPUT+i) for i in range(80)) != mask
                or sum(stages.values()) != cpu.tstates-before-irq
                or sum(stages.values()) != machine.expected_tstates(mask)):
            raise AssertionError(('paging/stack/source/timing differs', sum(stages.values()), machine.expected_tstates(mask)))
        return dict(index=index, target_bank=target, tstates=sum(stages.values()), stages=dict(stages),
                    output_sha256=sha(expected), page_writes=pages, irq_tstates=irq)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--masks', type=Path, required=True)
    p.add_argument('--mask-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    with np.load(args.states, allow_pickle=False) as saved:
        states = saved['states']
    masks = args.masks.read_bytes()
    old = json.loads(args.mask_report.read_text(encoding='utf-8'))
    if (not old['complete'] or states.shape != (old['frames'], 3840)
            or sha(states.tobytes()) != old['states_sha256'] or sha(masks) != old['stream_sha256']
            or len(masks) != len(states)*80):
        raise ValueError('different/incomplete masks or screens')
    h = Harness()
    report = dict(scope=__doc__, complete=False, baseline_commit='4f92850',
        states_sha256=sha(states.tobytes()), masks_sha256=sha(masks), frames_expected=len(states),
        baseline_tstates=154089, code_bytes=h.labels['state']-machine.CODE,
        state_bytes=h.labels['end']-h.labels['state'], code_hex=h.code.hex(), labels=h.labels,
        instruction_listing=h.listing, tables=[dict(base=b, bytes=len(v), sha256=sha(v)) for b, v in h.regions],
        formula='58784 + 4793*dense_bands + 4*odd_dense_bands + 277*partial_cells',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', frames=[],
        full_frame_delivery_measured=False, player_changed=False, integrated_player_delta_tstates=0)
    for index, state in enumerate(states):
        report['frames'].append(h.run(state.tobytes(), masks[index*80:index*80+80], index))
        if index % 250 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'Cell output Z80 verified {index+1}/{len(states)}', flush=True)
    total = sum(f['tstates'] for f in report['frames'])
    report['instruction_histogram'] = [dict(address=a, tstates=t, count=n) for (a, t), n in sorted(h.histogram.items())]
    if sum(r['tstates']*r['count'] for r in report['instruction_histogram']) != total:
        raise AssertionError('histogram differs')
    report['summary'] = dict(total_tstates=total, mean_frame_tstates=total/len(states),
        maximum_frame_tstates=max(f['tstates'] for f in report['frames']),
        baseline_total_tstates=154089*len(states), delta_tstates=total-154089*len(states))
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
