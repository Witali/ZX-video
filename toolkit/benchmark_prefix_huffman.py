"""Execute the eight-bit prefix decoder for FPD1 direct values on a Z80 model.

Host supplies (attribute flag, predicted byte) pairs and parses the container.
The wrapper writes final bitmap bytes, but attribute bytes still require XOR.
Input groups are contiguous, plus one explicit zero lookahead byte. This CPU
fixture occupies 4000..7FFF, NOT a release memory map. Motion/masks, ZX0,
refill/paging, attribute XOR, screen expansion, IRQ/ULA/TR-DOS/physical disk
and frame delivery are excluded. No integrated playback claim is made.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from benchmark_context_huffman import GuardCPU, INPUT, OUTPUT, STACK, STOP, word
from probe_context_masks import unpermute
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader, groups, EXPECTED_SHA
from probe_motion_metadata import restore
import probe_motion_alphabet as alphabet
import probe_motion_residual_order as ordering
import probe_fine_motion as motion
import prefix_huffman_z80 as machine

PAIRS = 0xa000


class Harness:
    def __init__(self, tables, mapping, *, single_byte=False,carry_huffman=False):
        self.tables, self.mapping = tables, mapping
        self.single_byte=single_byte
        self.carry_huffman=carry_huffman
        self.bit_base=0xf8 if carry_huffman else 0xf0
        self.code, self.labels, self.listing, self.layout = machine.build(tables, mapping,single_byte=single_byte,carry_huffman=carry_huffman)
        self.regions = self.layout['regions']
        self.cpu = GuardCPU(b'', b'')
        self.cpu.sp, self.cpu.port_7ffd = STACK, 0x16
        self.cpu.state = self.labels['state'], self.labels['end']
        for base, data in [(machine.CODE, self.code)]+self.regions:
            for i, value in enumerate(data):
                self.cpu.write8(base+i, value)
        self.timings = {r['address']: r['tstates'] for r in self.listing}
        self.histogram = Counter()

    def begin(self, encoded):
        if len(encoded)+1 > 16384:
            raise ValueError('group and lookahead exceed contiguous benchmark input')
        self.cpu.guarding = False
        for i, value in enumerate(encoded+b'\0'):
            self.cpu.write8(INPUT+i, value)
        self.cpu.input_end = INPUT+len(encoded)+1
        word(self.cpu, self.labels['source'], INPUT)
        self.cpu.write8(self.labels['bit_page'], self.bit_base)

    def position(self):
        page = self.cpu.read8(self.labels['bit_page'])
        if not self.bit_base <= page <= self.bit_base+7:
            raise AssertionError('invalid saved bit position')
        return 8*(word(self.cpu, self.labels['source'])-INPUT)+(page & 7)

    def formula(self, pairs, values, position):
        result, bits, short = 0, 0, 0
        for (attribute, prediction), value in zip(pairs, values):
            context = len(self.tables)-1 if attribute else self.mapping[prediction]
            length = self.tables[context][value]
            if not length:
                raise AssertionError('uncoded reference value')
            start, end = (position+bits) % 8, (position+bits+length) % 8
            if length <= 8:
                result += 168+5*int(start+length >= 8)-attribute
                if self.single_byte: result += -50 if start+length<=7 else 58
                if self.carry_huffman: result -= 8
                short += 1
            else:
                available = 8-start if start else 0
                refills = (max(0, length-8-available)+7)//8
                carry = (self.layout['symbols'][context] & 255)+self.layout['indices'][context][value] > 255
                result += 420+53*(length-9)+32*refills-int(carry)+70*int(start > 0)+5*int(end > 0)-attribute
                if self.single_byte: result += 47
                if self.carry_huffman: result += 8*int(start>0)
            bits += length
        return result, bits, short

    def run(self, pairs, expected, interrupt=None):
        if len(pairs) != len(expected) or len(pairs) > 32 or any(p[0] not in (0, 1) for p in pairs):
            raise ValueError('invalid bounded predictor pairs')
        cpu = self.cpu
        cpu.guarding = False
        for i, value in enumerate(b for pair in pairs for b in pair):
            cpu.write8(PAIRS+i, int(value))
        cpu.a, cpu.ix, cpu.z, cpu.carry = 0x96, 0x1122, True, False
        cpu.set_bc(0xa53c); cpu.set_de(0x18fa); cpu.set_hl(0x9271)
        cpu.alt_b, cpu.alt_c = 0, len(expected)
        cpu.alt_h, cpu.alt_l = PAIRS >> 8, PAIRS & 255
        cpu.alt_d, cpu.alt_e = OUTPUT >> 8, OUTPUT & 255
        cpu.pc, cpu.sp = self.labels['chunk'], STACK
        cpu.push(STOP)
        cpu.guarding = True
        before, steps, primitive, irq = cpu.tstates, 0, 0, 0
        position = self.position()
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            if pc == self.labels['invalid'] or steps > max(50, len(expected)*500):
                raise AssertionError('invalid code or non-returning decoder')
            cpu.step(); steps += 1
            elapsed, wanted = cpu.tstates-ticks, self.timings[pc]
            if elapsed not in (wanted if isinstance(wanted, list) else [wanted]):
                raise AssertionError(f'instruction timing {pc:04x}: {elapsed}, expected {wanted}')
            self.histogram[pc, elapsed] += 1
            if pc < self.labels['primitive_end']:
                primitive += elapsed
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        elapsed = cpu.tstates-before-irq
        result = bytes(cpu.read8(OUTPUT+i) for i in range(len(expected)))
        if result != expected or cpu.sp != STACK:
            raise AssertionError(('wrong value bytes or stack', result, expected))
        formula, bits, short = self.formula(pairs, expected, position)
        wrapper = 105+sum(112 if attr else 119 for attr, _ in pairs) if expected else 27
        if primitive != formula or elapsed != primitive+wrapper or self.position() != position+bits:
            raise AssertionError((primitive, formula, elapsed, wrapper, self.position(), position+bits))
        return dict(values=len(expected), bits=bits, short_values=short,
                    primitive_tstates=primitive, wrapper_tstates=wrapper, total_tstates=elapsed)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpd', type=Path, required=True)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw, data = args.raw.read_bytes(), args.fpd.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected full FPR1')
    header, parsed = groups(raw)
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected movie states')
    offsets = [struct.unpack_from('<bb', header, 35+2*i) for i in range(header[30])]
    symbols = np.frombuffer(header[4:20], dtype=np.uint8).reshape(4, 4)
    converted = alphabet.remap(states, residual, symbols)
    if b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, converted, 8, offsets, 8), 8) != raw:
        raise ValueError('motion cache differs from reference')
    order = ordering.field_order(8)
    prediction = (states ^ residual)[:, order]
    direct = states.copy(); direct[:, 3072:] = residual[:, 3072:]
    direct = direct[:, order]
    r = Reader(data)
    if r.take(4) != b'FPD1' or r.take(1) != b'\x02':
        raise ValueError('expected direct FPD1')
    count = r.take(1)[0]
    if r.take(r.u16()) != header:
        raise ValueError('FPD1 header mismatch')
    mapping, tables = r.take(256), [r.take(256) for _ in range(count)]
    h = Harness(tables, mapping)
    report = dict(scope=__doc__, baseline_commit='fbf351e', input_sha256=sha(data),
        fpr1_sha256=sha(raw), states_sha256=sha(states.tobytes()),
        code_bytes=len(h.code)-3, state_bytes=3, primitive_bytes=h.labels['primitive_end']-machine.CODE,
        code_hex=h.code.hex(), labels=h.labels, instruction_listing=h.listing,
        timing_source='https://zxe.io/depot/documents/technical/Zilog/Z80%20CPU%20User%20Manual%20rev11%20(2016-09)(Zilog)(%23UM008011-0816)(en)%5B!%5D.pdf',
        tables=[dict(base=base, bytes=len(blob), sha256=sha(blob)) for base, blob in h.regions],
        useful_root_tail_bytes=h.layout['body_bytes'],
        primitive_formula='short bitmap: 168+5*(r+L>=8); long bitmap: 420+53*(L-9)+32*refills-carry+70*(r>0)+5*(end>0); attribute subtracts 1. refills=ceil(max(0,L-8-(8-r if r else 0))/8)',
        wrapper_formula='105+119*bitmap_values+112*attribute_values per nonempty chunk; empty=27',
        player_changed=False, integrated_player_delta_tstates=0,
        full_frame_delivery_measured=False, complete=False, frames=[])
    quanta = Counter()
    start = total_bits = 0
    for index, (fixed, _) in enumerate(parsed):
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if n != int.from_bytes(fixed[:2], 'little') or restore(r.take(vl), n, 192, 2) != fixed[2:2+n*192]:
            raise ValueError('group/vector mismatch')
        masks = unpermute(restore(r.take(ml), n, 480, 4), n, 2)
        if masks != fixed[2+n*192:]:
            raise ValueError('mask mismatch')
        bits = int.from_bytes(r.take(4), 'little')
        h.begin(r.take((bits+7)//8))
        mask = np.unpackbits(np.frombuffer(masks, dtype=np.uint8)).reshape(n, 3840).astype(bool)
        checked_bits = 0
        for frame in range(n):
            predictors = prediction[start+frame, mask[frame]].tolist()
            attributes = (order[mask[frame]] >= 3072).astype(np.uint8).tolist()
            pairs = list(zip(attributes, predictors))
            values = direct[start+frame, mask[frame]].tobytes()
            totals = Counter()
            for offset in range(0, max(1, len(values)), 32):
                result = h.run(pairs[offset:offset+32], values[offset:offset+32])
                totals.update(result); totals['calls'] += 1
                quanta[result['total_tstates']] += 1
            checked_bits += totals['bits']
            report['frames'].append(dict(index=start+frame, **totals))
        if checked_bits != bits or h.position() != bits:
            raise AssertionError('group bit coverage mismatch')
        total_bits += bits; start += n
        if index % 25 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'prefix: verified group {index+1}/{len(parsed)}', flush=True)
    r.end()
    if start != 4971:
        raise AssertionError('incomplete movie')
    summary = dict(frames=start, groups=len(parsed), values=sum(row['values'] for row in report['frames']),
        short_values=sum(row['short_values'] for row in report['frames']),
        bits=total_bits, calls=sum(quanta.values()), max_quantum_tstates=max(quanta),
        total_table_bytes=sum(len(blob) for _, blob in h.regions))
    for field in ('primitive_tstates', 'wrapper_tstates', 'total_tstates'):
        values = np.array([row[field] for row in report['frames']])
        summary[field] = dict(total=int(values.sum()), mean=float(values.mean()), maximum=int(values.max()),
            worst_frame=int(values.argmax()), frames_over_nominal_425448=int(np.count_nonzero(values > 425448)))
    report['summary'] = summary
    report['instruction_histogram'] = [dict(address=pc, tstates=t, count=n) for (pc, t), n in sorted(h.histogram.items())]
    if sum(pc_t[1]*n for pc_t, n in h.histogram.items()) != summary['total_tstates']['total']:
        raise AssertionError('instruction histogram sum mismatch')
    report['quantum_histogram'] = dict(sorted(quanta.items()))
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
