"""Execute the local-bank decoder and current banked decoder on actual TRD blocks.

Both use identical 256-output-byte requests and token-boundary suspension.
The local fixture starts with compressed bytes already in its slot: source
transport is separately bounded below by 32 T per compressed byte (two LDI
copies), excluding their loops, setup and paging. This is NOT an integrated
player benchmark. Disk/ROM/ULA, IRQ, packet reading and queue control are
excluded; no cadence, disk delivery or release claim is made.
"""
import argparse
import json
from pathlib import Path
import struct

import bank_local_zx0 as machine
from benchmark_banked_zx0 import Harness as BankedHarness, STACK, STOP
from benchmark_compact_screen import NativeCPU
from benchmark_context_huffman import word
from build_fap3_trd import sha
import disk_layout
from validate_fast_sparse import CPU
from zx0_codec import decompress


class GuardCPU(NativeCPU):
    def read8(self, address):
        if self.guarding and address >= 0xc000:
            if self.port_7ffd & 7 != self.slot:
                raise AssertionError('wrong slot paged')
            if address < machine.OUTPUT:
                if (self.input_reads >= len(self.payload)
                        or address != self.input_start + self.input_reads):
                    raise AssertionError('input cursor or bound differs')
                self.input_reads += 1
            elif address >= machine.OUTPUT + self.produced:
                raise AssertionError('read past produced history')
        return CPU.read8(self, address)

    def write8(self, address, value):
        if self.guarding:
            history = machine.OUTPUT <= address <= 0xffff and self.port_7ffd & 7 == self.slot
            if history:
                if address != machine.OUTPUT + self.produced or self.produced >= self.limit:
                    raise AssertionError('output cursor or block bound differs')
                self.produced += 1
            private = machine.STACK_BOTTOM <= address < machine.STACK_TOP
            if private: self.private_min = min(self.private_min, address)
            if not (history or private or STACK-96 <= address < STACK
                    or self.labels['state'] <= address < self.labels['end']
                    or address in self.patched):
                raise AssertionError(f'write outside decoder contract: {address:04x}')
        return CPU.write8(self, address, value)


class Harness:
    def __init__(self, *, dynamic_input=False):
        self.dynamic_input=dynamic_input
        self.code, self.labels = machine.build(dynamic_input=dynamic_input)
        cpu = self.cpu = GuardCPU(b'', b'')
        cpu.labels = self.labels
        cpu.patched = {self.labels[n] for n in ('slice_high_operand', 'slice_low_operand',
            'slice_equal_branch', 'match_high_operand', 'match_low_operand', 'match_equal_branch')}
        cpu.patched.update((self.labels['dzx0t_last_offset']+1, self.labels['dzx0t_last_offset']+2))
        for bank in cpu.banks: bank[:] = b'\xa5'*16384
        for i, value in enumerate(self.code): cpu.write8(machine.CODE+i, value)

    def begin(self, payload, expected, *, slot=1, screen_bit=0, stored=False,input_offset=0,preloaded=False):
        if not 1 <= len(payload) <= 8192 or not 1 <= len(expected) <= 8192:
            raise ValueError('block exceeds the half-bank slot')
        if not 0<=input_offset<=8192-len(payload) or input_offset and not self.dynamic_input:
            raise ValueError('invalid input offset')
        if slot not in ((0,1,3,4) if self.dynamic_input else machine.BANKS) or screen_bit not in (0, 8):
            raise ValueError('invalid slot or screen bit')
        cpu = self.cpu; cpu.guarding = False
        cpu.slot, cpu.payload, self.expected = slot, payload, expected
        cpu.input_start=machine.INPUT+input_offset
        if preloaded:
            if bytes(cpu.banks[slot][input_offset:input_offset+len(payload)])!=payload:
                raise AssertionError('preloaded compressed bytes differ')
        else:
            cpu.banks[slot][:] = b'\xa5'*input_offset+payload+b'\xa5'*(16384-input_offset-len(payload))
        cpu.port_7ffd = self.page = 0x10 | slot | screen_bit
        cpu.produced = cpu.input_reads = 0; cpu.limit = len(expected)
        cpu.private_min = machine.STACK_TOP
        self.first = True; self.last_target = self.total = 0; self.slices = []
        for n, value in dict(block_length=len(expected), block_end=(machine.OUTPUT+len(expected)) & 65535).items():
            word(cpu, self.labels[n], value)
        cpu.write8(self.labels['block_stored'], 128 if stored else 0)
        if self.dynamic_input:word(cpu,self.labels['input_pointer'],cpu.input_start)
        self.protected = {b: bytes(cpu.banks[b]) for b in range(8) if b not in (slot, 2, 5)}
        self.fixed = bytes(cpu.banks[5][:0x3800])

    def run(self, target, interrupt=None):
        if not self.last_target <= target <= len(self.expected) or target == 0:
            raise ValueError('targets must be positive and monotonic')
        cpu = self.cpu; cpu.guarding = False
        word(cpu, self.labels['slice_target'], (machine.OUTPUT+target) & 65535)
        cpu.pc = self.labels['begin' if self.first else 'slice_until']
        cpu.sp = STACK; cpu.push(STOP); cpu.guarding = True
        before, steps, irq = cpu.tstates, cpu.steps, 0
        while cpu.pc != STOP:
            if cpu.pc == self.labels['fatal'] or cpu.steps-steps > 2_000_000:
                raise AssertionError('decoder did not return')
            cpu.step()
            if interrupt and cpu.pc != STOP: irq += interrupt(cpu)
        cpu.guarding = False
        if (cpu.sp != STACK or cpu.port_7ffd != self.page
                or not target <= cpu.produced <= len(self.expected)
                or bytes(cpu.banks[cpu.slot][8192:8192+cpu.produced]) != self.expected[:cpu.produced]):
            raise AssertionError('output, stack or page differs')
        elapsed = cpu.tstates-before-irq
        self.total += elapsed; self.first = False; self.last_target = target
        self.slices.append(dict(target=target, produced=cpu.produced, tstates=elapsed, irq_tstates=irq))
        # The caller owns both register sets between resumptions.
        for name in ('a','b','c','d','e','h','l','alt_a','alt_b','alt_c','alt_d','alt_e','alt_h','alt_l'):
            setattr(cpu, name, 0x97)
        cpu.z = cpu.carry = cpu.alt_z = cpu.alt_carry = True
        return elapsed

    def finish(self):
        cpu = self.cpu
        if (cpu.produced != len(self.expected) or cpu.input_reads != len(cpu.payload)
                or bytes(cpu.banks[cpu.slot][cpu.input_start-machine.INPUT:cpu.input_start-machine.INPUT+len(cpu.payload)]) != cpu.payload
                or bytes(cpu.banks[5][:0x3800]) != self.fixed
                or any(bytes(cpu.banks[b]) != data for b, data in self.protected.items())):
            raise AssertionError('incomplete input or damaged protected RAM')
        return dict(tstates=self.total, slices=self.slices,
            max_slice_tstates=max(s['tstates'] for s in self.slices),
            private_stack_bytes=machine.STACK_TOP-cpu.private_min)


def disk_blocks(directory, part):
    stem = f'ZX-video-huffman-preview_part{part:02}'
    image = (directory/(stem+'.trd')).read_bytes()
    meta = json.loads((directory/(stem+'.json')).read_bytes())
    if sha(image) != meta['trd_sha256']: raise ValueError('TRD hash differs')
    positions = list(disk_layout.positions(meta['video_sectors']+1, meta['video_start_sector'] % 16))
    base = meta['video_start_sector']*256
    stream = b''.join(image[base+p*256:base+(p+1)*256] for p in positions[:meta['video_sectors']])[:meta['video_bytes']]
    at = 0; blocks = []
    for b in meta['blocks']:
        n, size = struct.unpack_from('<HH', stream, at); at += 4
        payload = stream[at:at+size]; at += size
        raw = decompress(payload, limit=n)
        if n != b['decoded_bytes'] or size != b['zx0_bytes'] or sha(raw) != b['sha256']:
            raise ValueError('TRD block differs')
        blocks.append((payload, raw))
    if at != len(stream): raise ValueError('unconsumed stream')
    return meta, stream, blocks


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    local = Harness()
    banked = BankedHarness(fast_literal=True, fast_refill=True, token_boundaries=True, inline_matches=True)
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='a562c4d',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        local_code_bytes=len(local.code), banked_code_bytes=len(banked.code),
        local_code_sha256=sha(local.code), banked_code_sha256=sha(banked.code),
        local_labels=local.labels, player_changed=False, integrated_player_delta_tstates=0,
        source_transport_lower_bound_tstates_per_byte=32,
        irq_safe_paging_included=False, volumes=[])
    def save(): args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for part in (1,2,3):
        meta, stream, blocks = disk_blocks(args.directory, part)
        volume = dict(part=part, trd_sha256=meta['trd_sha256'], raw_sha256=meta['raw_sha256'],
            states_sha256=meta['states_sha256'], frame_start=meta['frame_start'],
            frame_end_exclusive=meta['frame_end_exclusive'], stream_sha256=sha(stream),
            stream_bytes=len(stream), blocks=[])
        report['volumes'].append(volume); ring = 0
        for i, (payload, raw) in enumerate(blocks):
            ring = (ring+4) % 65536
            banked.begin(payload, raw, ring_start=ring, page=0x17+8*(i%2))
            local.begin(payload, raw, slot=machine.BANKS[i%3], screen_bit=8*(i%2))
            for target in list(range(256,len(raw),256))+[len(raw)]:
                banked.run(target); local.run(target)
            before, after = banked.finish(), local.finish()
            volume['blocks'].append(dict(index=i, raw_bytes=len(raw), compressed_bytes=len(payload),
                raw_sha256=sha(raw), compressed_sha256=sha(payload),
                baseline_tstates=before['tstates'], **after,
                baseline_page_switches=before['page_switches'],
                delta_tstates=after['tstates']-before['tstates'],
                delta_with_transport_lower_bound_tstates=after['tstates']+32*len(payload)-before['tstates']))
            ring = (ring+len(payload)) % 65536
            if i%25 == 0: save(); print(f'Paired exact ZX0: disk {part}, block {i+1}/{len(blocks)}', flush=True)
    rows = [b for v in report['volumes'] for b in v['blocks']]
    report.update(complete=True, summary={k:sum(b[k] for b in rows) for k in
        ('raw_bytes','compressed_bytes','baseline_tstates','tstates','delta_tstates','delta_with_transport_lower_bound_tstates')})
    report['summary'].update(blocks=len(rows), max_slice_tstates=max(b['max_slice_tstates'] for b in rows),
        max_private_stack_bytes=max(b['private_stack_bytes'] for b in rows),
        max_compressed_bytes=max(b['compressed_bytes'] for b in rows))
    save(); print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__': main()
