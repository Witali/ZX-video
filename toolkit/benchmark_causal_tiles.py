"""Execute causal compact-frame reconstruction from FPD1 on actual Z80 opcodes.

Host only expands vector/mask metadata and loads contiguous group bitstreams.
It does NOT compute predictors or initialize the decoded frame between calls.
Includes frame traversal, original-row caching, motion/zero prediction, masks,
Huffman, bitmap writes and attribute XOR. Excludes metadata/ZX0 decoding,
stream-window refill/paging, native screen expansion, IRQ/ULA/ROM/disk.
Input 4000..63FF overwrites the screen/TR-DOS area: CPU fixture, not release.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct

import numpy as np

from benchmark_context_huffman import word
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader
from probe_motion_metadata import restore
import probe_motion_alphabet as alphabet
import causal_tile_z80 as machine
from validate_fast_sparse import CPU

INPUT, VECTORS, BITMAP_MASKS, ATTRIBUTE_MASKS = 0x4000, 0xa400, 0xaa00, 0xb600
STACK, STOP = 0x9df0, 0x9e00


class GuardCPU(CPU):
    guarding = False

    def read8(self, address):
        if self.guarding and INPUT <= address < machine.FRAME and address >= self.input_end:
            raise AssertionError(f'coded input overread: {address:04x}')
        return super().read8(address)

    def write8(self, address, value):
        if self.guarding:
            allowed = (machine.FRAME <= address < machine.FRAME+3840
                or machine.CACHE <= address < machine.CACHE+1024 and 1 <= (address & 63) <= 32
                or self.state[0] <= address < self.state[1] or STACK-96 <= address < STACK)
            if not allowed:
                raise AssertionError(f'write outside frame/cache/state/stack: {address:04x}')
        super().write8(address, value)


class Harness:
    def __init__(self, tables, mapping, offsets, *, skip_empty=False, hybrid=False, raw_kind=None, intra_above=False, intra_extended=False, fast_fragments=False, unrolled_motion=False, raw_intra=False, split_literals=False, sparse_patches=False):
        self.hybrid = hybrid
        self.raw_kind = raw_kind
        self.fast_fragments = fast_fragments
        self.unrolled_motion, self.offsets = unrolled_motion, offsets
        self.raw_intra = raw_intra
        self.split_literals = split_literals
        self.code, self.labels, self.listing, self.regions = machine.build(tables, mapping, offsets, skip_empty=skip_empty, hybrid=hybrid, raw_kind=raw_kind, intra_above=intra_above, intra_extended=intra_extended, fast_fragments=fast_fragments, unrolled_motion=unrolled_motion, raw_intra=raw_intra, split_literals=split_literals, sparse_patches=sparse_patches)
        self.raw_value_entries = {self.labels[f'raw_value_{i}'] for i in range(16)} if raw_kind is not None else set()
        self.cpu = GuardCPU(b'', b'')
        self.cpu.port_7ffd, self.cpu.sp = 0x16, STACK
        self.cpu.state = self.labels['state'], self.labels['end']
        for base, blob in [(machine.CODE, self.code)]+self.regions:
            for i, value in enumerate(blob):
                self.cpu.write8(base+i, value)
        self.instructions = {r['address']: r for r in self.listing}
        self.histogram = Counter()

    def begin(self, encoded, vectors, bitmap_masks, attribute_masks, *, literals=None):
        if not 1 <= len(vectors)//192 <= 8 or len(vectors) % 192:
            raise ValueError('invalid group vectors')
        frames = len(vectors)//192
        if len(bitmap_masks) != frames*384 or len(attribute_masks) != frames*96:
            raise ValueError('invalid group masks')
        if (literals is not None) != self.split_literals:
            raise ValueError('literal channel configuration differs')
        input_data = encoded+b'\0'+literals if self.split_literals else encoded
        if len(input_data)+1 > machine.FRAME-INPUT:
            raise ValueError('input exceeds contiguous CPU fixture')
        self.cpu.guarding = False
        for base, blob in ((INPUT, input_data+b'\0'), (VECTORS, vectors),
                           (BITMAP_MASKS, bitmap_masks), (ATTRIBUTE_MASKS, attribute_masks)):
            for i, value in enumerate(blob):
                self.cpu.write8(base+i, value)
        self.cpu.input_end = INPUT+len(input_data)+1
        if self.split_literals:
            self.literal_start = INPUT+len(encoded)+1
            word(self.cpu, self.labels['literal_source'], self.literal_start)
        word(self.cpu, self.labels['source'], INPUT)
        self.cpu.write8(self.labels['bit_page'], 0xf0)
        self.group_frames = frames
        self.cache_frames = [any(0 < (v & (127 if self.raw_kind is not None else 255)) < 81 for v in vectors[i*192:(i+1)*192]) for i in range(frames)]

    def position(self):
        page = self.cpu.read8(self.labels['bit_page'])
        if not 0xf0 <= page <= 0xf7:
            raise AssertionError('invalid retained bit position')
        return (word(self.cpu, self.labels['source'])-INPUT)*8+(page & 7)

    def literal_position(self):
        return word(self.cpu, self.labels['literal_source'])-self.literal_start

    def run(self, frame, expected, interrupt=None):
        if not 0 <= frame < self.group_frames or len(expected) != 3840:
            raise ValueError('invalid frame')
        cpu = self.cpu
        cpu.guarding = False
        if self.hybrid:
            cpu.write8(self.labels['cache_enabled'], int(self.cache_frames[frame]))
        for name, value in (('vectors', VECTORS+192*frame), ('bitmap_masks', BITMAP_MASKS+384*frame),
                             ('attribute_masks', ATTRIBUTE_MASKS+96*frame)):
            word(cpu, self.labels[name], value)
        # Only RAM state survives across calls. No host-prepared predictor.
        for name in ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l'):
            setattr(cpu, name, 0x97)
        cpu.ix, cpu.z, cpu.carry = 0x1122, True, False
        cpu.pc, cpu.sp = self.labels['frame'], STACK
        cpu.push(STOP); cpu.guarding = True
        before, position, steps, irq = cpu.tstates, self.position(), 0, 0
        stages, values, literals, raw_values, raw_tiles, unaligned = Counter(), 0, 0, 0, 0, 0
        fast_kinds, fast_formula, fast_unaligned = Counter(), 0, 0
        motion_formula, motion_vectors = 0, Counter()
        raw_intra_formula, raw_intra_tiles, raw_intra_values, raw_intra_unaligned = 0, 0, 0, 0
        while cpu.pc != STOP:
            pc, ticks = cpu.pc, cpu.tstates
            if pc == self.labels['invalid'] or steps > 2_000_000:
                raise AssertionError('decoder did not finish frame')
            row = self.instructions[pc]
            if self.raw_intra and pc == self.labels['raw_intra']:
                target = word(cpu, self.labels['target'])-machine.FRAME
                tile = (target//256)*16+(target % 32)//2
                masks = word(cpu, self.labels['bitmap_masks'])
                mask = cpu.read8(masks)*256+cpu.read8(masks+1)
                is_unaligned = bool(cpu.alt_c & 7)
                raw_intra_formula += machine.raw_intra_tstates(cpu.a & 127, tile, mask, unaligned=is_unaligned)
                raw_intra_tiles += 1; raw_intra_values += mask.bit_count(); raw_intra_unaligned += is_unaligned
            if self.unrolled_motion and pc == self.labels['motion']:
                motion_formula += machine.motion_tstates(cpu.a, self.offsets, unrolled=True)
                motion_vectors[cpu.a] += 1
            if pc in (self.labels['bitmap'], self.labels['attribute']):
                values += 1
            if self.hybrid and pc == self.labels.get('literal'):
                literals += 1
            if pc in self.raw_value_entries:
                raw_values += 1
            if self.raw_kind is not None and pc == self.labels['raw_patches']:
                raw_tiles += 1; unaligned += int(cpu.alt_c & 7 != 0)
            if self.fast_fragments and pc == self.labels['fast_fragment']:
                is_unaligned = False if self.split_literals else bool(cpu.alt_c & 7)
                source = word(cpu, self.labels['literal_source']) if self.split_literals else cpu.ix+is_unaligned
                selector = cpu.read8(source+4) if cpu.a == 87 else 0
                fast_formula += machine.fast_tstates(cpu.a, unaligned=is_unaligned, selector=selector, split_literals=self.split_literals)
                fast_unaligned += is_unaligned; fast_kinds[cpu.a] += 1
            cpu.step(); steps += 1
            elapsed, wanted = cpu.tstates-ticks, row['tstates']
            if elapsed not in (wanted if isinstance(wanted, list) else [wanted]):
                raise AssertionError((row, elapsed))
            stages[row['stage']] += elapsed
            self.histogram[pc, elapsed] += 1
            if interrupt and cpu.pc != STOP:
                irq += interrupt(cpu)
        actual = bytes(cpu.read8(machine.FRAME+i) for i in range(3840))
        if actual != expected:
            mismatch = next(i for i, (x, y) in enumerate(zip(actual, expected)) if x != y)
            raise AssertionError(f'frame differs at compact offset {mismatch}: {actual[mismatch]} != {expected[mismatch]}')
        if cpu.sp != STACK or sum(stages.values()) != cpu.tstates-before-irq:
            raise AssertionError('stack/timing differs')
        for name, wanted in (('vectors', VECTORS+192*(frame+1)), ('bitmap_masks', BITMAP_MASKS+384*(frame+1)),
                             ('attribute_masks', ATTRIBUTE_MASKS+96*(frame+1))):
            if word(cpu, self.labels[name]) != wanted:
                raise AssertionError(f'incomplete metadata traversal: {name}')
        result = dict(values=values, bits=self.position()-position, total_tstates=sum(stages.values()), stages=dict(stages))
        if self.hybrid:
            result.update(literals=literals, cache=self.cache_frames[frame])
        if self.raw_kind is not None:
            result.update(raw_values=raw_values, raw_tiles=raw_tiles, unaligned_raw_tiles=unaligned)
        if self.fast_fragments:
            if fast_formula != stages['fast_fragment']:
                raise AssertionError(('fast-fragment timing formula', fast_formula, stages['fast_fragment']))
            result.update(fast_kinds=dict(fast_kinds), fast_tiles=sum(fast_kinds.values()),
                fast_unaligned=fast_unaligned, fast_formula_tstates=fast_formula)
        if self.unrolled_motion:
            if motion_formula != stages['motion']:
                raise AssertionError(('unrolled motion timing formula', motion_formula, stages['motion']))
            result.update(motion_vectors=dict(motion_vectors), motion_formula_tstates=motion_formula)
        if self.raw_intra:
            if raw_intra_formula != stages['raw_intra']:
                raise AssertionError(('raw intra timing formula', raw_intra_formula, stages['raw_intra']))
            result.update(raw_intra_tiles=raw_intra_tiles, raw_intra_values=raw_intra_values,
                raw_intra_unaligned=raw_intra_unaligned, raw_intra_formula_tstates=raw_intra_formula)
        return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fpd', type=Path, required=True)
    p.add_argument('--motion-cache', type=Path, required=True)
    p.add_argument('--prefix-report', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--skip-empty', action='store_true', help='skip empty bitmap halves and attribute nibbles')
    args = p.parse_args()
    data = args.fpd.read_bytes()
    old = json.loads(args.prefix_report.read_text(encoding='utf-8'))
    if not old['complete'] or old['input_sha256'] != sha(data):
        raise ValueError('incomplete/mismatched previous CPU run')
    with np.load(args.motion_cache) as saved:
        states, reference_vectors = saved['states'], saved['vectors']
    if states.shape != (4971, 3840) or sha(states.tobytes()) != alphabet.INPUT_STATES_SHA:
        raise ValueError('unexpected full movie')
    r = Reader(data)
    if r.take(5) != b'FPD1\x02':
        raise ValueError('expected direct FPD1')
    count, header = r.take(1)[0], r.take(r.u16())
    offsets = [struct.unpack_from('<bb', header, 35+2*i) for i in range(header[30])]
    mapping, tables = r.take(256), [r.take(256) for _ in range(count)]
    h = Harness(tables, mapping, offsets, skip_empty=args.skip_empty)
    report = dict(scope=__doc__, baseline_commit='2f3ce3f', input_sha256=sha(data),
        states_sha256=sha(states.tobytes()), frames_expected=4971, complete=False,
        variant='skip_empty' if args.skip_empty else 'baseline',
        code_bytes=h.labels['state']-machine.CODE, state_bytes=h.labels['end']-h.labels['state'],
        compact_frame_bytes=3840, motion_cache_bytes=1024, code_hex=h.code.hex(), labels=h.labels,
        instruction_listing=h.listing, timing_source='Zilog UM008011-0816',
        tables=[dict(base=base, bytes=len(blob), sha256=sha(blob)) for base, blob in h.regions],
        player_changed=False, integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        groups=[], frames=[])
    start = 0
    while start < len(states):
        n, vl, ml = r.u16(), r.u16(), r.u16()
        if not 1 <= n <= min(8, len(states)-start):
            raise ValueError('invalid group count')
        vectors = restore(r.take(vl), n, 192, 2)
        if vectors != reference_vectors[start:start+n].tobytes():
            raise ValueError('vector mismatch')
        masks = restore(r.take(ml), n, 480, 4)
        bits = int.from_bytes(r.take(4), 'little')
        encoded = r.take((bits+7)//8)
        h.begin(encoded, vectors, masks[:n*384], masks[n*384:])
        for frame in range(n):
            result = h.run(frame, states[start+frame].tobytes())
            prior = old['frames'][start+frame]
            if (result['values'] != prior['values'] or result['bits'] != prior['bits']
                    or result['stages'].get('huffman', 0) != prior['primitive_tstates']):
                raise AssertionError('Huffman differs from prior full run')
            report['frames'].append(dict(index=start+frame, **result))
        if h.position() != bits:
            raise AssertionError('group bit coverage differs')
        report['groups'].append(dict(start=start, frames=n, encoded_bytes=len(encoded), bits=bits))
        start += n
        if len(report['groups']) % 25 == 1:
            args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
            print(f'causal Z80: verified {start}/4971 frames', flush=True)
    r.end()
    stages = Counter()
    for row in report['frames']:
        stages.update(row['stages'])
    totals = [row['total_tstates'] for row in report['frames']]
    report['summary'] = dict(frames=start, groups=len(report['groups']), total_tstates=sum(totals),
        mean_frame_tstates=sum(totals)/start, max_frame_tstates=max(totals), worst_frame=totals.index(max(totals)),
        frames_over_nominal_425448=sum(t > 425448 for t in totals), stages=dict(stages),
        values=sum(row['values'] for row in report['frames']), bits=sum(row['bits'] for row in report['frames']),
        previous_huffman_and_wrapper_tstates=old['summary']['total_tstates']['total'],
        incomparable_scope_delta_tstates=sum(totals)-old['summary']['total_tstates']['total'],
        max_contiguous_input_bytes=max(row['encoded_bytes'] for row in report['groups']),
        vector_histogram=np.bincount(reference_vectors.ravel(), minlength=len(offsets)+1).tolist())
    report['instruction_histogram'] = [dict(address=pc, tstates=t, count=n) for (pc, t), n in sorted(h.histogram.items())]
    if sum(t*n for (_, t), n in h.histogram.items()) != sum(totals):
        raise AssertionError('histogram timing sum differs')
    report['complete'] = True
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
