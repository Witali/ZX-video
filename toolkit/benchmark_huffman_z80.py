"""Execute a nibble-transition Huffman decoder over all FPE1 value bytes.

The static four-bit transition automaton has three 4096-byte columns:
output (zero means none), next-state address low, next-state address high.
Codes must be complete, nonzero symbols, minimum length four. One nibble
can then emit at most one byte. Tables are prepared on the PC, not the Z80.

Bench map (NOT the release RAM map): code 8000, input 4000..7FFF, output
9000..BFFF, stack 8FF0, tables C000..EFFF in bank 6. Input is contiguous,
already ZX0-decoded. Includes source reads, output writes and RET. Excludes
CALL/caller register setup, table loading, frame masks/motion/reconstruction,
ZX0, paging, IRQ, ULA, ROM, disk and the complete playback scheduler.
"""
import argparse
from collections import deque
import json
from pathlib import Path
import struct

import numpy as np

from build_zxv_trd import MiniAssembler
from probe_lossless_layouts import sha
from probe_motion_entropy import Reader, codes_for, decode, groups, parse_header, EXPECTED_SHA
from validate_fast_sparse import CPU

FPE_SHA = 'fd5eac0ebe023e0ceda403492483f34b8e5b404609d2317bed79953a59d00437'
CODE, INPUT, OUTPUT, STACK, STOP, TABLE = 0x8000, 0x4000, 0x9000, 0x8ff0, 0x8f00, 0xc000


def transition_tables(lengths):
    if len(lengths) != 256 or lengths[0] or min(n for n in lengths if n) < 4:
        raise ValueError('requires nonzero symbols with codes at least four bits long')
    root = {}
    for symbol, (code, length) in enumerate(codes_for(255, lengths)):
        if not length:
            continue
        node = root
        for shift in range(length - 1, 0, -1):
            node = node.setdefault((code >> shift) & 1, {})
            if not isinstance(node, dict):
                raise ValueError('prefix collision')
        if code & 1 in node:
            raise ValueError('code collision')
        node[code & 1] = symbol
    queue = deque([root])
    states = []
    while queue:
        node = queue.popleft()
        if set(node) != {0, 1}:
            raise ValueError('incomplete code tree')
        states.append(node)
        queue.extend(child for child in node.values() if isinstance(child, dict))
    if len(states) > 256:
        raise ValueError('too many prefix states')
    indices = {id(node): index for index, node in enumerate(states)}
    tables = bytearray(12288)
    for state, node in enumerate(states):
        for nibble in range(16):
            current, emitted = node, 0
            for shift in range(3, -1, -1):
                current = current[(nibble >> shift) & 1]
                if isinstance(current, int):
                    if emitted:
                        raise AssertionError('more than one output per nibble')
                    emitted, current = current, root
            offset = state * 16 + nibble
            pointer = TABLE + indices[id(current)] * 16
            tables[offset] = emitted
            tables[4096 + offset] = pointer & 255
            tables[8192 + offset] = pointer >> 8
    return bytes(tables), len(states)


def build_decoder():
    asm = MiniAssembler(CODE)
    listing = []
    returns = set()

    def emit(name, code, ticks):
        listing.append(dict(address=asm.pc, instruction=name, tstates=ticks))
        asm.emit(*code)

    def branch(name, opcode, target, ticks, relative=False):
        listing.append(dict(address=asm.pc, instruction=name, tstates=ticks))
        (asm.rel8 if relative else asm.abs16)(opcode, target)

    emit('EXX', [0xd9], 4)
    emit('LD A,B', [0x78], 4)
    emit('OR C', [0xb1], 4)
    emit('EXX', [0xd9], 4)
    emit('RET Z', [0xc8], [5, 11])
    emit('LD HL,C000h', [0x21, 0, 0xc0], 10)
    asm.label('byte')
    emit('LD C,(IX+0)', [0xdd, 0x4e, 0], 19)
    emit('INC IX', [0xdd, 0x23], 10)
    for phase in ('high', 'low'):
        emit('LD A,C', [0x79], 4)
        if phase == 'high':
            for _ in range(4):
                emit('RRCA', [0x0f], 4)
        emit('AND 0Fh', [0xe6, 0x0f], 7)
        emit('OR L', [0xb5], 4)
        emit('LD L,A', [0x6f], 4)
        emit('LD A,(HL)', [0x7e], 7)
        emit('LD D,A', [0x57], 4)
        emit('SET 4,H', [0xcb, 0xe4], 8)
        emit('LD E,(HL)', [0x5e], 7)
        emit('LD A,H', [0x7c], 4)
        emit('XOR 30h', [0xee, 0x30], 7)
        emit('LD H,A', [0x67], 4)
        emit('LD H,(HL)', [0x66], 7)
        emit('LD L,E', [0x6b], 4)
        emit('LD A,D', [0x7a], 4)
        emit('OR A', [0xb7], 4)
        branch('JR Z,no_output', 0x28, phase + '_done', [7, 12], True)
        emit('EXX', [0xd9], 4)
        emit('LD (HL),A', [0x77], 7)
        emit('INC HL', [0x23], 6)
        emit('DEC BC', [0x0b], 6)
        emit('LD A,B', [0x78], 4)
        emit('OR C', [0xb1], 4)
        emit('EXX', [0xd9], 4)
        returns.add(asm.pc)
        emit('RET Z', [0xc8], [5, 11])
        asm.label(phase + '_done')
    branch('JP byte', 0xc3, 'byte', 10)
    return asm.resolve(), listing, returns


def expected_cycles(bits, values):
    if not values:
        return 27
    nibbles = (bits + 3) // 4
    high, low = (nibbles + 1) // 2, nibbles // 2
    return 37 + 136 * high + 101 * low + 35 * values - (10 if nibbles % 2 == 0 else 0)


class CheckedCPU(CPU):
    guarding = False

    def write8(self, address, value):
        if self.guarding and not (OUTPUT <= address < self.output_end or STACK - 2 <= address < STACK):
            raise AssertionError(f'unexpected Z80 write {address:04x}')
        super().write8(address, value)


def run_group(cpu, encoded, bits, expected, frame_counts, code, return_checks, raw=False):
    if len(encoded) > 16384 or len(expected) > 12288:
        raise ValueError('group exceeds benchmark buffers')
    cpu.guarding = False
    for address, blob in ((CODE, code), (INPUT, encoded)):
        for offset, value in enumerate(blob):
            cpu.write8(address + offset, value)
    for i in range(len(expected)):
        cpu.write8(OUTPUT + i, 0)
    cpu.pc, cpu.sp, cpu.ix = CODE, STACK, INPUT
    cpu.push(STOP)
    cpu.output_end = OUTPUT + len(expected)
    cpu.guarding = True
    cpu.alt_h, cpu.alt_l = OUTPUT >> 8, OUTPUT & 255
    cpu.alt_b, cpu.alt_c = len(expected) >> 8, len(expected) & 255
    if raw:
        cpu.set_hl(INPUT); cpu.set_de(OUTPUT); cpu.set_bc(len(expected))
    boundaries = set(np.cumsum(frame_counts).tolist()) - {0}
    timestamps = {}
    before, steps = cpu.tstates, cpu.steps
    while cpu.pc != STOP:
        pc = cpu.pc
        cpu.step()
        if cpu.steps - steps > max(100, len(expected) * 250):
            raise AssertionError('decoder did not return')
        if not raw and cpu.ix > INPUT + len(encoded):
            raise AssertionError('read past coded data')
        if pc in return_checks:
            count = len(expected) - (cpu.alt_b * 256 + cpu.alt_c)
            if count in boundaries:
                timestamps[count] = cpu.tstates - before
    elapsed = cpu.tstates - before
    predicted = (21 * len(expected) + 18 if expected else 19) if raw else expected_cycles(bits, len(expected))
    if elapsed != predicted or cpu.sp != STACK:
        raise AssertionError((elapsed, predicted, cpu.sp))
    if bytes(cpu.read8(OUTPUT + i) for i in range(len(expected))) != expected:
        raise AssertionError('decoded bytes changed')
    if not raw and cpu.ix - INPUT != len(encoded):
        raise AssertionError('unexpected coded byte consumption')
    frame_ticks = []
    previous, count = 0, 0
    for size in frame_counts:
        count += size
        current = timestamps.get(count, previous)
        frame_ticks.append(current - previous)
        previous = current
    if raw:
        frame_ticks = [21 * n for n in frame_counts]
        frame_ticks[next((i for i, n in enumerate(frame_counts) if n), 0)] += 18 if expected else 19
    elif not expected:
        frame_ticks[0] = elapsed
    if sum(frame_ticks) != elapsed:
        raise AssertionError('frame timing partition differs from group')
    return elapsed, frame_ticks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fpe', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    data = args.fpe.read_bytes()
    if sha(data) != FPE_SHA:
        raise ValueError('unexpected measured FPE1 stream')
    original = decode(data)
    if sha(original) != EXPECTED_SHA:
        raise AssertionError('unexpected restored FPR1')
    header, parsed = groups(original)
    reader = Reader(data)
    if reader.take(5) != b'FPE1\xff':
        raise ValueError('expected Huffman mode')
    lengths = reader.take(reader.u16())
    if reader.take(reader.u16()) != header:
        raise AssertionError('header mismatch')
    tables, state_count = transition_tables(lengths)
    code, listing, checks = build_decoder()
    raw_code = bytes([0x78, 0xb1, 0xc8, 0xed, 0xb0, 0xc9])
    cpu = CheckedCPU(b'', b'')
    cpu.port_7ffd = 0x16
    for offset, value in enumerate(tables):
        cpu.write8(TABLE + offset, value)
    report = dict(scope=__doc__, baseline_commit='f3f5390', input_sha256=sha(data),
        restored_sha256=sha(original), timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        code_hex=code.hex(), code_bytes=len(code), instruction_listing=listing,
        raw_code_hex=raw_code.hex(), raw_formula='21*N+18 if N>0 else 19',
        huffman_formula='37+136*ceil(nibbles/2)+101*floor(nibbles/2)+35*N-10*(nibbles even); empty=27',
        prefix_states=state_count, table_bytes=len(tables), tables_sha256=sha(tables),
        player_changed=False, integrated_player_delta_tstates=0,
        full_frame_delivery_measured=False, complete=False, groups=[], frames=[])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    for index, (fixed, expected) in enumerate(parsed):
        if reader.take(len(fixed)) != fixed:
            raise AssertionError('group fixed fields changed')
        frame_count = int.from_bytes(fixed[:2], 'little')
        masks = fixed[2 + 192 * frame_count:]
        counts = [sum(x.bit_count() for x in masks[i*480:(i+1)*480]) for i in range(frame_count)]
        bits = int.from_bytes(reader.take(4), 'little')
        encoded = reader.take((bits+7)//8)
        baseline, raw_frames = run_group(cpu, expected, len(expected)*8, expected, counts, raw_code, set(), raw=True)
        elapsed, huff_frames = run_group(cpu, encoded, bits, expected, counts, code, checks)
        report['groups'].append(dict(index=index, frames=frame_count, values=len(expected), bits=bits,
            input_bytes=len(encoded), raw_tstates=baseline, huffman_tstates=elapsed, delta_tstates=elapsed-baseline))
        for n, raw_t, huff_t in zip(counts, raw_frames, huff_frames):
            report['frames'].append(dict(index=len(report['frames']), values=n,
                raw_tstates=raw_t, huffman_tstates=huff_t, delta_tstates=huff_t-raw_t))
        if index % 25 == 0:
            args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
            print(f'Z80 verified group {index+1}/{len(parsed)}', flush=True)
    reader.end()
    report['complete'] = True
    report['summary'] = dict(frames=len(report['frames']), groups=len(parsed),
        values=sum(row['values'] for row in report['groups']),
        max_group_input_bytes=max(row['input_bytes'] for row in report['groups']),
        max_group_output_bytes=max(row['values'] for row in report['groups']))
    for field in ('raw_tstates', 'huffman_tstates', 'delta_tstates'):
        values = np.array([row[field] for row in report['frames']])
        report['summary'][field] = dict(total=int(values.sum()), mean=float(values.mean()),
            maximum=int(values.max()), worst_frame=int(values.argmax()))
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report['summary']), flush=True)


if __name__ == '__main__':
    main()
