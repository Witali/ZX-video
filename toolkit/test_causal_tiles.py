import unittest

import numpy as np

import ay_interrupt
import playback_schedule
from build_zxv_trd import MiniAssembler
from benchmark_causal_tiles import Harness, STOP, word
from probe_context_values import pack
from probe_motion_entropy import codes_for
from validate_fast_sparse import CPU
import causal_tile_z80 as machine

OFFSETS = [(0, 0)]+[(x, y) for y in range(-4, 5) for x in range(-4, 5) if x or y]


def predict(previous, vectors):
    result = bytearray(previous)
    for tile, vector in enumerate(vectors):
        ty, tx = divmod(tile, 16)
        dx, dy = OFFSETS[vector] if vector < 81 else (0, 0)
        for row in range(8):
            y, sy = ty*8+row, ty*8+row-dy
            for byte in range(2):
                x = tx*8+byte*4
                value = 0
                if vector < 81 and 0 <= sy < 96:
                    for p in range(4):
                        sx = x+p-dx
                        if 0 <= sx < 128:
                            value |= ((previous[sy*32+sx//4] >> (6-2*(sx % 4))) & 3) << (6-2*p)
                result[y*32+tx*2+byte] = value
    return bytes(result)


def tile_order():
    return [address for ty in range(12) for tx in range(16) for address in (
        [((ty*8+y)*32+tx*2+x) for y in range(8) for x in range(2)]+
        [3072+(ty*2+y)*32+tx*2+x for y in range(2) for x in range(2)])]


def group(previous, vectors, targets, tables, mapping):
    values, contexts, bm, attrs = bytearray(), [], bytearray(), bytearray()
    for v, current in zip(vectors, targets):
        predicted = predict(previous, v)
        bflags, aflags = [], []
        for address in tile_order():
            attr = address >= 3072
            changed = current[address] != predicted[address]
            (aflags if attr else bflags).append(changed)
            if changed:
                values.append((current[address] ^ predicted[address]) if attr else current[address])
                contexts.append(len(tables)-1 if attr else mapping[predicted[address]])
        bm += np.packbits(bflags).tobytes(); attrs += np.packbits(aflags).tobytes()
        previous = current
    bits, encoded = pack(values, contexts, [codes_for(255, table) for table in tables])
    return bits, encoded, b''.join(vectors), bytes(bm), bytes(attrs)


class CausalTileTests(unittest.TestCase):
    def test_causal_motion_masks_borders_and_group_retention(self):
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        h = Harness(tables, mapping, OFFSETS)
        previous = bytes(3840)
        rng = np.random.default_rng(12896)
        edge = [tile for tile in range(192) if tile//16 in (0, 11) or tile % 16 in (0, 15)]
        seen = set()
        for index in range(6):
            vectors = bytearray((tile+index*19) % 82 for tile in range(192))
            for j, tile in enumerate(edge):
                vectors[tile] = (index*len(edge)+j) % 82
                seen.add(vectors[tile])
            predicted = predict(previous, vectors)
            target = bytearray(predicted)
            for address in range(3840):
                if index == 0 or (address+index) % 5 == 0:
                    target[address] ^= int(rng.integers(1, 256))
            current = bytes(target)
            bits, encoded, v, bm, at = group(previous, [bytes(vectors)], [current], tables, mapping)
            h.begin(encoded, v, bm, at)
            h.run(0, current)
            self.assertEqual(h.position(), bits)
            previous = current
        self.assertEqual(seen, set(range(82)))
        # All unchanged, no Huffman bytes. Values already in the in-place
        # history must survive when a new group resets the input state.
        h.begin(b'', bytes(192), bytes(384), bytes(96))
        result = h.run(0, previous)
        self.assertEqual((result['values'], result['bits']), (0, 0))

    def test_last_short_group_nonbyte_aligned_context_stream(self):
        # Every bitmap byte is 0 or FF. One-bit codes carry across frames.
        table = bytes([1]+[0]*254+[1])
        h = Harness([table]*2, bytes(256), OFFSETS)
        targets, current = [], bytearray(3840)
        for index in range(3):
            for address in (index, 3072+index):
                current[address] ^= 255
            targets.append(bytes(current))
        bits, encoded, v, bm, at = group(bytes(3840), [bytes(192)]*3, targets, [table]*2, bytes(256))
        self.assertEqual(bits, 6)
        h.begin(encoded, v, bm, at)
        for frame, target in enumerate(targets):
            h.run(frame, target)
        self.assertEqual(h.position(), bits)

    def test_skip_empty_halves_and_attribute_nibbles(self):
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        variants = [Harness(tables, mapping, OFFSETS, skip_empty=option) for option in (False, True)]
        previous = bytes(3840)
        vectors = [bytes(192)]*3
        targets, target = [], bytearray(previous)
        # Exercise both empty halves, either half alone, both nonempty and
        # both positions within each shared attribute-mask byte.
        for frame in range(3):
            for tile in range(192):
                fields = [n for n in range(20) if (tile+frame) % 5 == n//4]
                for field in fields:
                    address = tile_order()[tile*20+field]
                    target[address] ^= 255
            targets.append(bytes(target))
        bits, encoded, v, bm, at = group(previous, vectors, targets, tables, mapping)
        totals = []
        for h in variants:
            h.begin(encoded, v, bm, at)
            totals.append(sum(h.run(i, current)['total_tstates'] for i, current in enumerate(targets)))
            self.assertEqual(h.position(), bits)
        self.assertLess(totals[1], totals[0])

    def test_ldi_memory_wrap_flags_and_timing(self):
        cpu = CPU(b'', b'')
        cpu.write8(0x8000, 0xed); cpu.write8(0x8001, 0xa0)
        for source, destination in ((0x6500, 0x7501), (0xffff, 0x7520), (0x65ff, 0xffff)):
            for count in (0, 1, 256, 65535):
                for z in (False, True):
                    for carry in (False, True):
                        cpu.write8(source, 0xa7)
                        cpu.set_hl(source); cpu.set_de(destination); cpu.set_bc(count)
                        cpu.z, cpu.carry, cpu.pc = z, carry, 0x8000
                        before = cpu.tstates; cpu.step()
                        self.assertEqual((cpu.hl(), cpu.de(), cpu.bc()), ((source+1) & 65535, (destination+1) & 65535, (count-1) & 65535))
                        self.assertEqual((cpu.read8(destination), cpu.z, cpu.carry, cpu.tstates-before), (0xa7, z, carry, 16))

    def test_ay_irq_after_every_frame_instruction(self):
        for skip_empty in (False, True):
            with self.subTest(skip_empty=skip_empty):
                self.exercise_irq(skip_empty)

    def exercise_irq(self, skip_empty, *, hybrid_data=None, raw_data=None, spatial_data=None, spatial_extended=False, fast_fragments=False, unrolled_motion=False, raw_intra=False, split_literals=False,register_fragments=False):
        tables, mapping = [bytes([8]*256)]*2, bytes(256)
        # Several moving boundary tiles, attributes and untouched regions.
        v = bytearray(192)
        for tile, vector in ((0, 1), (15, 9), (176, 73), (191, 81)):
            v[tile] = vector
        current = bytes(255 if i % 401 == 0 else 0 for i in range(3840))
        _, encoded, vectors, bm, at = group(bytes(3840), [bytes(v)], [current], tables, mapping)
        targets = [current]
        literals = None
        raw_kind = None
        if hybrid_data is not None:
            from probe_hybrid_tiles import read_header, read_group, decode
            from probe_motion_entropy import Reader
            r = Reader(hybrid_data)
            _, n, _, mapping, tables = read_header(r)
            count, _, _, vectors, bm, at, encoded = read_group(r, n)
            self.assertEqual(count, n); r.end()
            restored, _ = decode(hybrid_data)
            targets = [restored[i*3840:(i+1)*3840] for i in range(n)]
        if raw_data is not None:
            from probe_raw_patches import read_header, read_group, decode
            from probe_motion_entropy import Reader
            self.assertIsNone(hybrid_data)
            r = Reader(raw_data)
            raw_kind, _, n, mapping, tables, _ = read_header(r)
            count, _, _, vectors, bm, at, encoded = read_group(r, n)
            self.assertEqual(count, n); r.end()
            restored, _ = decode(raw_data)
            targets = [restored[i*3840:(i+1)*3840] for i in range(n)]
        if spatial_data is not None:
            from probe_spatial_contexts import read_header, read_group, decode
            from probe_motion_entropy import Reader
            self.assertIsNone(hybrid_data); self.assertIsNone(raw_data)
            r = Reader(spatial_data)
            model, _, n, mapping, tables = read_header(r, magic=b'FSF1' if split_literals else b'FHC1' if raw_intra else b'FHF1' if fast_fragments else b'FHS1')
            self.assertEqual(model, 0)
            count, _, _, vectors, bm, at, encoded = read_group(r, n, fast_fragments=fast_fragments, raw_intra=raw_intra)
            if split_literals:
                from probe_fast_fragments import SIZES
                from probe_fragment_channels import restore
                literals = r.take(sum(SIZES.get(v, 0) for v in vectors))
            self.assertEqual(count, n); r.end()
            if split_literals:
                _, restored = restore(spatial_data)
            else:
                restored, _ = decode(spatial_data, fast_fragments=fast_fragments, raw_intra=raw_intra)
            targets = [restored[i*3840:(i+1)*3840] for i in range(n)]
        h = Harness(tables, mapping, OFFSETS, skip_empty=skip_empty,
            hybrid=hybrid_data is not None or raw_data is not None or spatial_data is not None,
            raw_kind=raw_kind, intra_above=spatial_data is not None, intra_extended=spatial_extended, fast_fragments=fast_fragments, unrolled_motion=unrolled_motion, raw_intra=raw_intra, split_literals=split_literals,register_fragments=register_fragments)
        h.begin(encoded, vectors, bm, at, literals=literals)
        irq_base = 0x9400 if unrolled_motion else 0x9200 if spatial_extended else 0x8800
        a = MiniAssembler(irq_base)
        ay_interrupt.emit(a)
        playback_schedule.emit_clock(a, dos_irq=True, full_rom_clock=True, memory_clock=True, audio_irq=True)
        ay_interrupt.emit_variables(a)
        a.label('elapsed_fields'); a.word(0)
        a.label('fatal'); a.emit(0x76)
        self.assertLess(h.labels['end'], irq_base)
        self.assertLess(a.pc, machine.VECTOR_X)
        cpu = h.cpu
        for i, value in enumerate(a.resolve()):
            cpu.write8(irq_base+i, value)
        cpu.pc = a.labels['setup_clock']; cpu.push(STOP)
        while cpu.pc != STOP:
            cpu.step()
        cpu.write8(a.labels['audio_enabled'], 1)
        word(cpu, a.labels['audio_remaining'], 65535)
        names = ('a', 'b', 'c', 'd', 'e', 'h', 'l', 'ix', 'z', 'carry',
                 'alt_a', 'alt_b', 'alt_c', 'alt_d', 'alt_e', 'alt_h', 'alt_l',
                 'alt_z', 'alt_carry', 'port_7ffd', 'sp')
        calls = 0

        def interrupt(cpu):
            nonlocal calls
            cpu.guarding = False
            # Exhaustive instruction-boundary injection may exceed 65535
            # ticks. Keep this synthetic stream active; its final-tick path
            # has separate AY tests. The real clock still wraps at 16 bits.
            word(cpu, a.labels['audio_remaining'], 65535)
            index = cpu.read8(a.labels['audio_read_index'])
            slot = ay_interrupt.QUEUE_BASE+index*ay_interrupt.SLOT_BYTES
            cpu.write8(slot, 1); cpu.write8(slot+1, 8); cpu.write8(slot+2, calls & 15)
            cpu.write8(a.labels['audio_write_index'], (index+1) & 31)
            before = {name: getattr(cpu, name) for name in names}
            start, pc = cpu.tstates, cpu.pc
            cpu.push(pc); cpu.pc = 0xbdbd; cpu.iff1 = False; cpu.tstates += 19
            while cpu.pc != pc:
                self.assertNotEqual(cpu.pc, a.labels['fatal']); cpu.step()
            self.assertEqual(before, {name: getattr(cpu, name) for name in names})
            self.assertEqual(cpu.ay[8], calls & 15)
            self.assertEqual(cpu.tstates-start, 116+17+367+83)
            calls += 1
            self.assertEqual(word(cpu, a.labels['elapsed_fields']), calls & 65535)
            self.assertEqual(word(cpu, a.labels['audio_underruns']), 0)
            cpu.guarding = True
            return cpu.tstates-start

        for i, target in enumerate(targets):
            h.run(i, target, interrupt)
        self.assertGreater(calls, 10000)


if __name__ == '__main__':
    unittest.main()
