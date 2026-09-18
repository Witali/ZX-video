"""Execute context Huffman on real Z80 instructions for all FPC2 corrections.

Both the primitive and a bounded wrapper are measured. The wrapper reads
precomputed (attribute flag, predicted byte) pairs and writes corrections.
Host supplies those pairs, parses masks/headers and feeds contiguous groups.
Motion prediction/reconstruction, ZX0, window refill/paging, disk/ROM/ULA,
IRQ and the actual video/AY schedule are excluded. This is NOT a release map:
the contiguous input at 4000..7FFF overwrites the display/history area.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import context_huffman_z80 as machine
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader, groups, EXPECTED_SHA
from probe_motion_metadata import restore
import probe_motion_alphabet as alphabet
import probe_motion_residual_order as ordering
import probe_fine_motion as motion
from validate_fast_sparse import CPU

INPUT, PAIRS, OUTPUT, STACK, STOP = 0x4000, 0xa000, 0xa400, 0x9ff0, 0x8f00


def word(cpu, address, value=None):
    if value is None:
        return cpu.read8(address) | cpu.read8(address+1) << 8
    cpu.write8(address, value & 255); cpu.write8(address+1, value >> 8)


class GuardCPU(CPU):
    guarding = False
    state = (0, 0)
    input_end = INPUT

    def read8(self, address):
        if self.guarding and INPUT <= address < INPUT+16384 and address >= self.input_end:
            raise AssertionError(f'read past coded input: {address:04x}')
        return super().read8(address)

    def write8(self, address, value):
        if self.guarding and not (STACK-96 <= address < STACK or OUTPUT <= address < OUTPUT+32
                                  or self.state[0] <= address < self.state[1]):
            raise AssertionError(f'unexpected write {address:04x}')
        super().write8(address, value)


class Harness:
    def __init__(self, tables, mapping, variant):
        self.tables, self.mapping, self.variant = tables, mapping, variant
        self.code, self.labels, self.listing, self.regions = machine.build(tables, mapping, variant)
        self.cpu = GuardCPU(b'', b'')
        self.cpu.sp, self.cpu.port_7ffd = STACK, 0x16
        self.cpu.state = self.labels['state'], self.labels['end']
        for base, data in [(machine.CODE, self.code)]+self.regions:
            for i, value in enumerate(data):
                self.cpu.write8(base+i, value)
        self.timings = {r['address']: r['tstates'] for r in self.listing}
        self.histogram = Counter()
        _, _, self.symbols, _ = machine.prepare(tables, mapping, variant)
        self.indices = []
        for table in tables:
            symbols = [v for _, v in sorted((n, v) for v, n in enumerate(table) if n)]
            self.indices.append({v: i for i, v in enumerate(symbols)})

    def begin(self, encoded):
        if len(encoded) > 16384:
            raise ValueError('group exceeds contiguous benchmark input')
        self.cpu.guarding = False
        for i, value in enumerate(encoded):
            self.cpu.write8(INPUT+i, value)
        self.cpu.input_end = INPUT+len(encoded)
        word(self.cpu, self.labels['source'], INPUT)
        self.cpu.write8(self.labels['reservoir'], 0x80)

    def formula(self, pairs, values, refills):
        result, bits = 32*refills, 0
        for (attribute, prediction), value in zip(pairs, values):
            context = len(self.tables)-1 if attribute else self.mapping[prediction]
            length = self.tables[context][value]
            if not length:
                raise AssertionError('uncoded reference value')
            crossing = (self.symbols[context] & 255)+self.indices[context][value] > 255
            if self.variant == 'unrolled':
                result += (72 if attribute else 101)+53*length-int(crossing)
            else:
                result += (65 if attribute else 117 if self.variant == 'compact' else 94)+62*length-int(crossing)
            bits += length
        return result, bits

    def run(self, pairs, expected, interrupt=None):
        if len(pairs) != len(expected) or len(pairs) > 32 or any(p[0] not in (0, 1) for p in pairs):
            raise ValueError('invalid bounded predictor pairs')
        cpu = self.cpu
        cpu.guarding = False
        for i, value in enumerate(b for pair in pairs for b in pair):
            cpu.write8(PAIRS+i, int(value))
        # The only persistent input state is in RAM, not these registers.
        cpu.a, cpu.ix, cpu.z, cpu.carry = 0x96, 0x1122, True, False
        cpu.set_bc(0xa53c); cpu.set_de(0x18fa); cpu.set_hl(0x9271)
        cpu.alt_b, cpu.alt_c = 0, len(expected)
        cpu.alt_h, cpu.alt_l = PAIRS >> 8, PAIRS & 255
        cpu.alt_d, cpu.alt_e = OUTPUT >> 8, OUTPUT & 255
        cpu.pc, cpu.sp = self.labels['chunk'], STACK
        cpu.push(STOP)
        cpu.guarding = True
        before, steps, primitive, irq = cpu.tstates, 0, 0, 0
        source_before = word(cpu, self.labels['source'])
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            if pc == self.labels.get('invalid') or steps > max(50, len(expected)*500):
                raise AssertionError('invalid code or non-returning decoder')
            cpu.step()
            steps += 1
            elapsed = cpu.tstates-ticks
            wanted = self.timings[pc]
            if elapsed not in (wanted if isinstance(wanted, list) else [wanted]):
                raise AssertionError(f'instruction timing {pc:04x}: {elapsed}, expected {wanted}')
            self.histogram[pc, elapsed] += 1
            if pc < self.labels['primitive_end']:
                primitive += elapsed
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        elapsed = cpu.tstates-before-irq
        result = bytes(cpu.read8(OUTPUT+i) for i in range(len(expected)))
        consumed = word(cpu, self.labels['source'])-source_before
        if result != expected or cpu.sp != STACK:
            raise AssertionError('wrong correction bytes or stack')
        formula, bits = self.formula(pairs, expected, consumed)
        wrapper = 105+sum(112 if attribute else 119 for attribute, _ in pairs) if expected else 27
        if primitive != formula or elapsed != primitive+wrapper:
            raise AssertionError((primitive, formula, elapsed, wrapper))
        return dict(values=len(expected), bits=bits, input_bytes=consumed,
                    primitive_tstates=primitive, wrapper_tstates=wrapper, total_tstates=elapsed)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpc', type=Path, required=True)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--variant', choices=['compact', 'direct', 'unrolled'], default='unrolled')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    raw, data = args.raw.read_bytes(), args.fpc.read_bytes()
    if sha(raw) != EXPECTED_SHA:
        raise ValueError('unexpected full FPR1')
    header, parsed = groups(raw)
    with np.load(args.motion_cache) as saved:
        states, vectors, residual = (saved[k] for k in ('states', 'vectors', 'residual'))
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected movie states')
    import struct
    offsets = [struct.unpack_from('<bb', header, 35+2*i) for i in range(header[30])]
    symbols = np.frombuffer(header[4:20], dtype=np.uint8).reshape(4, 4)
    converted = alphabet.remap(states, residual, symbols)
    if b'FPR1'+symbols.tobytes()+ordering.encode(motion.encode(vectors, converted, 8, offsets, 8), 8) != raw:
        raise ValueError('motion cache differs from reference')
    order = ordering.field_order(8)
    prediction = (states ^ residual)[:, order]
    r = Reader(data)
    if r.take(4) != b'FPC2':
        raise ValueError('expected FPC2')
    count = r.take(1)[0]
    if r.take(r.u16()) != header:
        raise ValueError('FPC2 header differs from reference')
    mapping = r.take(256)
    tables = [r.take(256) for _ in range(count)]
    h = Harness(tables, mapping, args.variant)
    report = dict(scope=__doc__, baseline_commit='8e0812b', variant=args.variant,
        input_sha256=sha(data), fpr1_sha256=sha(raw), states_sha256=sha(states.tobytes()),
        code_bytes=len(h.code)-3, state_bytes=3, primitive_bytes=h.labels['primitive_end']-machine.CODE,
        code_hex=h.code.hex(), labels=h.labels, instruction_listing=h.listing,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        tables=[dict(base=base, bytes=len(blob), sha256=sha(blob)) for base, blob in h.regions],
        primitive_formula='loop: bitmap 117/94+62*L; attribute 65+62*L; unrolled: bitmap 101+53*L; attribute 72+53*L; plus 32 per input byte and minus 1 per symbol-address carry',
        wrapper_formula='105+119*bitmap_values+112*attribute_values per nonempty chunk; empty=27',
        player_changed=False, integrated_player_delta_tstates=0,
        full_frame_delivery_measured=False, complete=False, frames=[])
    quanta = Counter()
    groups_bits = []
    start = 0
    for index, (fixed, expected) in enumerate(parsed):
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if n != int.from_bytes(fixed[:2], 'little'):
            raise AssertionError('wrong frame count')
        if restore(r.take(vl), n, 192, 2) != fixed[2:2+n*192]:
            raise AssertionError('wrong vectors')
        masks = restore(r.take(ml), n, 480, 4)
        if masks != fixed[2+n*192:]:
            raise AssertionError('wrong masks')
        bits = int.from_bytes(r.take(4), 'little')
        encoded = r.take((bits+7)//8)
        h.begin(encoded)
        mask = np.unpackbits(np.frombuffer(masks, dtype=np.uint8)).reshape(n, 3840).astype(bool)
        cursor, checked_bits = 0, 0
        for frame in range(n):
            predictors = prediction[start+frame, mask[frame]].tolist()
            attributes = (order[mask[frame]] >= 3072).astype(np.uint8).tolist()
            pairs = list(zip(attributes, predictors))
            values = expected[cursor:cursor+len(pairs)]
            cursor += len(pairs)
            totals = Counter()
            for offset in range(0, max(1, len(values)), 32):
                result = h.run(pairs[offset:offset+32], values[offset:offset+32])
                totals.update(result)
                quanta[result['total_tstates']] += 1
                totals['calls'] += 1
            checked_bits += totals['bits']
            report['frames'].append(dict(index=start+frame, **totals))
        if cursor != len(expected) or checked_bits != bits or word(h.cpu, h.labels['source']) != INPUT+len(encoded):
            raise AssertionError('wrong group input/output coverage')
        reservoir = 0x80 if not bits % 8 else ((encoded[-1] << (bits % 8)) & 255) | (1 << (bits % 8-1))
        if h.cpu.read8(h.labels['reservoir']) != reservoir:
            raise AssertionError('wrong retained padding bits')
        groups_bits.append(bits)
        start += n
        if index % 25 == 0:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'{args.variant}: verified group {index+1}/{len(parsed)}', flush=True)
    r.end()
    if start != 4971:
        raise AssertionError('incomplete movie')
    summary = dict(frames=start, groups=len(parsed), values=sum(row['values'] for row in report['frames']),
        bits=sum(groups_bits), calls=sum(quanta.values()), max_quantum_tstates=max(quanta),
        total_table_bytes=sum(len(blob) for _, blob in h.regions))
    for field in ('primitive_tstates', 'wrapper_tstates', 'total_tstates'):
        values = np.array([row[field] for row in report['frames']])
        summary[field] = dict(total=int(values.sum()), mean=float(values.mean()),
            maximum=int(values.max()), worst_frame=int(values.argmax()),
            frames_over_nominal_425448=int(np.count_nonzero(values > 425448)))
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
