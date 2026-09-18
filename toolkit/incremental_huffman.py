"""Emit a bounded, resumable nibble-table Huffman producer for the Z80.

13-byte state: source, input_left, output, remaining, node (words), byte,
phase (0 next input byte / 1 low nibble pending), status (0 quota, 1 need
input, 2 done). Caller may replace an exhausted input window and drain/
replace the output buffer between calls. All live registers are saved in
state; no private stack or long-lived alternate-register ownership.

Table format from benchmark_huffman_z80, 12288 bytes at C000 in bank 6.
Caller must page that bank. Quota bounds output; max_code_bits bounds the
fast path's input need. Output buffer must have at least quota bytes free.
Only validated complete code trees with nonzero symbols and minimum code
length four are supported. This module does not emit a release player.
"""
from build_zxv_trd import MiniAssembler


def build(quota=32, max_code_bits=14, origin=0x8000):
    if not 1 <= quota <= 64 or not 4 <= max_code_bits <= 24:
        raise ValueError('unsupported quota/code limit')
    required = (quota * max_code_bits + 7) // 8
    if required > 255:
        raise ValueError('fast input bound exceeds byte comparison')
    a = MiniAssembler(origin)
    listing = []

    def emit(name, code, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks))
        a.emit(*code)

    def absolute(name, op, target, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks))
        a.abs16(op, target)

    def relative(name, op, target, ticks):
        listing.append(dict(address=a.pc, instruction=name, tstates=ticks))
        a.rel8(op, target)

    a.label('run')
    absolute('LD IX,(source)', [0xdd, 0x2a], 'source', 20)
    absolute('LD A,(byte)', 0x3a, 'byte', 13)
    emit('LD C,A', [0x4f], 4)
    emit('LD B,quota', [0x06, quota], 7)
    emit('EXX', [0xd9], 4)
    absolute('LD HL,(output)', 0x2a, 'output', 16)
    absolute('LD BC,(remaining)', [0xed, 0x4b], 'remaining', 20)
    absolute('LD DE,(input_left)', [0xed, 0x5b], 'input_left', 20)
    emit('LD A,B', [0x78], 4)
    emit('OR C', [0xb1], 4)
    absolute('JP Z,empty', 0xca, 'empty', 10)
    emit('LD A,D', [0x7a], 4)
    emit('OR A', [0xb7], 4)
    absolute('JP NZ,fast_select', 0xc2, 'fast_select', 10)
    emit('LD A,E', [0x7b], 4)
    emit('CP input_bound', [0xfe, required], 7)
    absolute('JP NC,fast_select', 0xd2, 'fast_select', 10)
    for kind in ('checked', 'fast'):
        a.label(kind + '_select')
        emit('EXX', [0xd9], 4)
        absolute('LD HL,(node)', 0x2a, 'node', 16)
        absolute('LD A,(phase)', 0x3a, 'phase', 13)
        emit('OR A', [0xb7], 4)
        absolute('JP NZ,low', 0xc2, kind + '_low', 10)
        a.label(kind + '_byte')
        if kind == 'checked':
            emit('EXX', [0xd9], 4)
            emit('LD A,D', [0x7a], 4)
            emit('OR E', [0xb3], 4)
            emit('EXX', [0xd9], 4)
            absolute('JP Z,need_input', 0xca, 'need_input', 10)
            emit('EXX', [0xd9], 4)
            emit('DEC DE', [0x1b], 6)
            emit('EXX', [0xd9], 4)
        emit('LD C,(IX+0)', [0xdd, 0x4e, 0], 19)
        emit('INC IX', [0xdd, 0x23], 10)
        for phase in ('high', 'low'):
            a.label(kind + '_' + phase)
            emit('LD A,C', [0x79], 4)
            if phase == 'high':
                for _ in range(4):
                    emit('RRCA', [0x0f], 4)
            emit('AND 0Fh', [0xe6, 15], 7)
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
            relative('JR Z,no_output', 0x28, kind + '_' + phase + '_done', [7, 12])
            emit('EXX', [0xd9], 4)
            emit('LD (HL),A', [0x77], 7)
            emit('INC HL', [0x23], 6)
            emit('DEC BC', [0x0b], 6)
            emit('LD A,B', [0x78], 4)
            emit('OR C', [0xb1], 4)
            emit('EXX', [0xd9], 4)
            absolute('JP Z,done', 0xca, 'done', 10)
            relative('DJNZ,more_output', 0x10, kind + '_' + phase + '_done', [8, 13])
            emit('LD A,next_phase', [0x3e, int(phase == 'high')], 7)
            absolute('LD (phase),A', 0x32, 'phase', 13)
            emit('XOR A', [0xaf], 4)
            absolute('JP save', 0xc3, 'save', 10)
            a.label(kind + '_' + phase + '_done')
        absolute('JP next byte', 0xc3, kind + '_byte', 10)
    a.label('need_input')
    emit('XOR A', [0xaf], 4)
    absolute('LD (phase),A', 0x32, 'phase', 13)
    emit('INC A', [0x3c], 4)
    absolute('JP save', 0xc3, 'save', 10)
    a.label('empty')
    emit('EXX', [0xd9], 4)
    # The normal node load was skipped. Preserve a valid node on empty calls.
    absolute('LD HL,(node)', 0x2a, 'node', 16)
    a.label('done')
    emit('LD A,2', [0x3e, 2], 7)
    a.label('save')
    absolute('LD (status),A', 0x32, 'status', 13)
    absolute('LD (node),HL', 0x22, 'node', 16)
    emit('LD A,C', [0x79], 4)
    absolute('LD (byte),A', 0x32, 'byte', 13)
    emit('EXX', [0xd9], 4)
    absolute('LD (output),HL', 0x22, 'output', 16)
    absolute('LD (remaining),BC', [0xed, 0x43], 'remaining', 20)
    emit('EXX', [0xd9], 4)
    # Calculate remaining input once per call, not once per byte on the fast path.
    absolute('LD HL,(source)', 0x2a, 'source', 16)
    absolute('LD DE,(input_left)', [0xed, 0x5b], 'input_left', 20)
    emit('ADD HL,DE', [0x19], 11)
    absolute('LD (source),IX', [0xdd, 0x22], 'source', 20)
    absolute('LD DE,(source)', [0xed, 0x5b], 'source', 20)
    emit('OR A', [0xb7], 4)
    emit('SBC HL,DE', [0xed, 0x52], 15)
    absolute('LD (input_left),HL', 0x22, 'input_left', 16)
    emit('RET', [0xc9], 10)
    a.label('state')
    for name, value in [('source', 0x6000), ('input_left', 0), ('output', 0xa400),
                        ('remaining', 0), ('node', 0xc000)]:
        a.label(name); a.word(value)
    for name, value in [('byte', 0), ('phase', 0), ('status', 2)]:
        a.label(name); a.emit(value)
    a.label('state_end')
    return a.resolve(), a.labels, listing
