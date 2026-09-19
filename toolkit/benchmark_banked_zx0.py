"""Execute bounded banked ZX0 on every saved block in the proposed video RAM map.

Actual CPU copies compressed bytes from banks 0/1/3/4 through BC00 and writes
history in bank 7 E000..FFFF. Host supplies complete blocks to the ring and
requests output boundaries; disk acquisition, packet parsing/AY/drawing,
ULA and ROM are excluded. Includes internal pointer setup, calls, paging and
copies. Host descriptor writes, request setup and the outer CALL are excluded.
With --token-boundaries a request is a minimum; complete copies may produce
additional bytes within the same verified block.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import banked_zx0 as machine
from benchmark_compact_screen import NativeCPU
from benchmark_context_huffman import word
from probe_lossless_layouts import sha
from validate_fast_sparse import CPU

STACK, STOP = 0x9df0, 0x93f0


class GuardCPU(NativeCPU):
    def read8(self, address):
        if self.guarding:
            if machine.INPUT <= address < machine.INPUT+256:
                valid = word(self, self.labels['valid'])
                if address-machine.INPUT >= valid or self.input_reads >= len(self.payload):
                    raise AssertionError('compressed input overread')
                value = CPU.read8(self, address)
                if value != self.payload[self.input_reads]:
                    raise AssertionError('compressed input order differs')
                self.input_reads += 1
                return value
            if address >= 0xc000:
                bank = self.port_7ffd & 7
                if bank in machine.BANKS:
                    position = machine.BANKS.index(bank)*16384+address-0xc000
                    if (self.ring_reads >= len(self.payload)
                            or position != (self.ring_start+self.ring_reads) % 65536):
                        raise AssertionError('ring input overread/order differs')
                    self.ring_reads += 1
                elif bank == 7:
                    if not machine.OUTPUT <= address < machine.OUTPUT+self.produced:
                        raise AssertionError('ZX0 reads outside produced history')
                else:
                    raise AssertionError('unexpected bank read')
        return CPU.read8(self, address)

    def write8(self, address, value):
        if self.guarding:
            history = (self.port_7ffd & 7) == 7 and machine.OUTPUT <= address <= 0xffff
            if history:
                if address-machine.OUTPUT != self.produced or self.produced >= self.limit:
                    raise AssertionError('ZX0 exceeded requested output boundary')
                self.produced += 1
            private = machine.STACK_BOTTOM <= address < machine.STACK_TOP
            if private:
                self.private_min = min(self.private_min, address)
            if not (history or private or STACK-96 <= address < STACK
                    or machine.INPUT <= address < machine.INPUT+256
                    or self.labels['state'] <= address < self.labels['ring_banks']
                    or address in self.patched_addresses):
                raise AssertionError(f'ZX0 write outside contract: {address:04x}')
        return CPU.write8(self, address, value)


class Harness:
    def __init__(self, *, fast_literal=False, fast_refill=False, profile=False, token_boundaries=False):
        self.code, self.labels = machine.build(fast_literal=fast_literal, fast_refill=fast_refill,token_boundaries=token_boundaries)
        self.token_boundaries = token_boundaries
        self.profile, self.histogram = profile, Counter()
        cpu = self.cpu = GuardCPU(b'', b'')
        cpu.labels = self.labels
        cpu.patched_addresses = {self.labels['slice_high_operand'], self.labels['slice_low_operand'],
                                 self.labels['dzx0t_last_offset']+1, self.labels['dzx0t_last_offset']+2}
        if token_boundaries: cpu.patched_addresses.add(self.labels['slice_equal_branch'])
        for bank in cpu.banks:
            bank[:] = b'\xa5'*16384
        for i, value in enumerate(self.code):
            cpu.write8(machine.CODE+i, value)
        self.rows = []

    def begin(self, payload, expected, *, ring_start=0, page=0x17, stored=False):
        if not 1 <= len(payload) <= 16384 or not 1 <= len(expected) <= 8192 or page not in (0x17, 0x1f):
            raise ValueError('invalid block sizes/page')
        cpu = self.cpu; cpu.guarding = False
        cpu.payload, cpu.ring_start = payload, ring_start % 65536
        for i, value in enumerate(payload):
            region, offset = divmod((cpu.ring_start+i) % 65536, 16384)
            cpu.banks[machine.BANKS[region]][offset] = value
        cpu.banks[7][8192:] = b'\xa5'*8192
        cpu.port_7ffd = page
        cpu.input_reads = cpu.ring_reads = cpu.produced = cpu.limit = 0
        cpu.private_min = machine.STACK_TOP
        self.expected, self.first, self.total, self.slices, self.pages = expected, True, 0, [], []
        self.last_target = 0
        for name, value in dict(block_length=len(expected), block_end=(machine.OUTPUT+len(expected)) & 65535,
                                remaining=len(payload), valid=0,
                                ring_pointer=0xc000+cpu.ring_start % 16384).items():
            word(cpu, self.labels[name], value)
        for name, value in dict(block_stored=128 if stored else 0, ring_region=cpu.ring_start//16384, history_page=page).items():
            cpu.write8(self.labels[name], value)

    def run(self, count, interrupt=None, *, copy_trace=None):
        cpu = self.cpu
        if not (self.last_target if self.token_boundaries else cpu.produced) <= count <= len(self.expected) or count == 0:
            raise ValueError('output targets must be monotonic')
        cpu.guarding = False
        word(cpu, self.labels['slice_target'], (machine.OUTPUT+count) & 65535)
        cpu.limit = len(self.expected) if self.token_boundaries else count
        cpu.pc = self.labels['begin' if self.first else 'slice_until']
        cpu.sp = STACK; cpu.push(STOP)
        start, steps, irq = cpu.tstates, cpu.steps, 0
        cpu.guarding = True
        while cpu.pc != STOP:
            if cpu.pc == self.labels['fatal'] or cpu.steps-steps > 2000000:
                raise AssertionError('decoder failed to return')
            page, pc, ticks = cpu.port_7ffd, cpu.pc, cpu.tstates
            if copy_trace is not None and pc == self.labels['slice_copy']:
                copy_trace.append(dict(produced=cpu.produced,tstates=cpu.tstates-start))
            cpu.step()
            if self.profile:
                self.histogram[pc, cpu.tstates-ticks] += 1
            if cpu.port_7ffd != page:
                self.pages.append(cpu.port_7ffd)
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        elapsed = cpu.tstates-start-irq
        if copy_trace is not None:
            copy_trace.append(dict(produced=cpu.produced,tstates=cpu.tstates-start,returned=True))
        cpu.guarding = False
        valid_count = count <= cpu.produced <= len(self.expected) if self.token_boundaries else cpu.produced == count
        if (cpu.sp != STACK or not valid_count or cpu.port_7ffd not in (0x17, 0x1f)
                or bytes(cpu.banks[7][8192:8192+cpu.produced]) != self.expected[:cpu.produced]):
            raise AssertionError('bounded output, stack or paging differs')
        self.first = False; self.total += elapsed; self.last_target = count
        self.slices.append(dict(target=count, tstates=elapsed, irq_tstates=irq,
            **(dict(produced=cpu.produced,extra_decoded_bytes=cpu.produced-count) if self.token_boundaries else {})))
        # Every suspended invocation must survive arbitrary caller registers.
        cpu.set_hl(0x1357); cpu.set_de(0x2468); cpu.set_bc(0xabcd)
        cpu.a, cpu.z, cpu.carry = 0x93, True, True
        cpu.alt_a, cpu.alt_b, cpu.alt_c, cpu.alt_d, cpu.alt_e, cpu.alt_h, cpu.alt_l = 0x3f, 0x78, 0x21, 0xac, 0x16, 0x57, 0xbe
        cpu.alt_z, cpu.alt_carry = False, True
        return elapsed

    def finish(self):
        cpu = self.cpu
        region, offset = divmod((cpu.ring_start+len(cpu.payload)) % 65536, 16384)
        if (cpu.produced != len(self.expected) or cpu.input_reads != len(cpu.payload)
                or cpu.ring_reads != len(cpu.payload) or word(cpu, self.labels['remaining'])
                or cpu.read8(self.labels['ring_region']) != region
                or word(cpu, self.labels['ring_pointer']) != 0xc000+offset
                or bytes(cpu.banks[5][:0x3800]) != b'\xa5'*0x3800
                or bytes(cpu.banks[7][:6912]) != b'\xa5'*6912
                or bytes(cpu.banks[6]) != b'\xa5'*16384):
            raise AssertionError('final input count, ring pointer or protected RAM differs')
        return dict(tstates=self.total, slices=self.slices, max_slice_tstates=max(r['tstates'] for r in self.slices),
                    private_stack_bytes=machine.STACK_TOP-cpu.private_min, page_switches=len(self.pages))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--storage-report', type=Path, required=True)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--baseline-cpu', type=Path, required=True)
    p.add_argument('--baseline-commit', default='9e4c6c0')
    p.add_argument('--quota', type=int, default=256)
    p.add_argument('--fast-literal', action='store_true')
    p.add_argument('--fast-refill', action='store_true')
    p.add_argument('--profile', action='store_true')
    p.add_argument('--token-boundaries',action='store_true',help='Yield between copies; may decode past requested target')
    p.add_argument('--token-boundary-check',choices=('aligned','decrement'),default='aligned',help='Reproduce the first target-1 experiment with decrement')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    token_mode = 'decrement' if args.token_boundaries and args.token_boundary_check=='decrement' else args.token_boundaries
    raw = args.raw.read_bytes()
    storage, baseline = (json.loads(p.read_text(encoding='utf-8')) for p in (args.storage_report, args.baseline_cpu))
    if (not storage['complete'] or not baseline['complete'] or not 1 <= args.quota <= 8192
            or storage['input_sha256'] != sha(raw) or baseline['input_sha256'] != sha(raw)):
        raise ValueError('different/incomplete baseline or invalid quota')
    h = Harness(fast_literal=args.fast_literal, fast_refill=args.fast_refill, profile=args.profile,token_boundaries=token_mode)
    position, ring = 0, 0xfff0
    report = dict(scope=__doc__, complete=False, baseline_commit=args.baseline_commit, input_sha256=sha(raw),
        code_hex=h.code.hex(), labels=h.labels, output_quota=args.quota, blocks=[],
        fast_literal=args.fast_literal, fast_refill=args.fast_refill,token_boundaries=token_mode,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf', disk_delivery_verified=False)
    for index, block in enumerate(storage['blocks']):
        expected = raw[position:position+block['decoded_bytes']]; position += len(expected)
        payload = (args.cache/(block['sha256']+'.zx0')).read_bytes()
        if sha(expected) != block['sha256'] or len(payload) != block['zx0_bytes']:
            raise ValueError('block differs')
        h.begin(payload, expected, ring_start=ring, page=0x17+(index % 2)*8)
        for target in range(args.quota, len(expected), args.quota):
            h.run(target)
        h.run(len(expected))
        result = h.finish()
        result.update(index=index, compressed_bytes=len(payload), decoded_bytes=len(expected),
                      baseline_tstates=baseline['blocks'][index]['tstates'], ring_start=ring)
        result['delta_tstates'] = result['tstates']-result['baseline_tstates']
        report['blocks'].append(result)
        ring = (ring+len(payload)+4) % 65536
        if index % 25 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'Banked ZX0 verified {index+1}/{len(storage["blocks"])}', flush=True)
    if position != len(raw):
        raise AssertionError('incomplete stream coverage')
    report['complete'] = True
    report['summary'] = dict(blocks=len(report['blocks']), code_bytes=len(h.code),
        total_tstates=sum(r['tstates'] for r in report['blocks']),
        baseline_tstates=sum(r['baseline_tstates'] for r in report['blocks']),
        delta_tstates=sum(r['delta_tstates'] for r in report['blocks']),
        max_slice_tstates=max(r['max_slice_tstates'] for r in report['blocks']),
        max_private_stack_bytes=max(r['private_stack_bytes'] for r in report['blocks']),
        page_switches=sum(r['page_switches'] for r in report['blocks']))
    if args.profile:
        report['instruction_histogram'] = [dict(address=a, tstates=t, count=n) for (a,t),n in sorted(h.histogram.items())]
        if sum(r['tstates']*r['count'] for r in report['instruction_histogram']) != report['summary']['total_tstates']:
            raise AssertionError('instruction histogram differs')
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
