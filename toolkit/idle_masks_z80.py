"""Experimental FAP3 metadata decoder that leaves idle bitmap stripes untouched.

Bank 7 is mapped, HL points to sparse masks, and vector_pointer addresses a
word pointing at all 192 vectors. BFF1..BFFC records stripes in reverse order
(the reconstruction counter is 12..1). An idle stripe has 32 zero bitmap
masks AND 16 zero vectors; attribute masks are always expanded. No stream
bytes change. Idle=FFh and active=0 so reconstruction can AND the flag with
its nonzero stripe index, saving one byte/four T. The compiled mask generator
must have run before entry.
"""
from build_zxv_trd import MiniAssembler
import compiled_masks_z80 as compiled
from frame_metadata_z80 import FLAGS, MASKS

CODE, IDLE_BASE, VECTOR_POINTER = 0xe200, 0xbff0, 0xbffe


def build(*, vector_pointer=VECTOR_POINTER):
    _, shared, _, _ = compiled.build()
    a, rows = MiniAssembler(CODE), []

    def emit(name, data, ticks):
        rows.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='idle_metadata'))
        a.emit(*data)

    def ref(name, opcode, target, ticks):
        rows.append(dict(address=a.pc, instruction=name, tstates=ticks, stage='idle_metadata'))
        if isinstance(target, str): a.abs16(opcode, target)
        else: a.emit(opcode); a.word(target)

    def advance(register, amount, tag):
        low, store = (0x7d, 0x6f) if register == 'HL' else (0x7b, 0x5f)
        emit('LD A,low', [low], 4); emit('ADD A,amount', [0xc6, amount], 7)
        emit('LD low,A', [store], 4)
        rows.append(dict(address=a.pc, instruction='JR NC,'+tag, tstates=[7, 12], stage='idle_metadata'))
        a.rel8(0x30, tag); emit('INC high', [0x24 if register == 'HL' else 0x14], 4)
        a.label(tag)

    a.label('decode')
    emit('PUSH HL', [0xe5], 11); emit('POP IX', [0xdd, 0xe1], 14)
    ref('LD DE,8', 0x11, 8, 10); emit('ADD HL,DE', [0x19], 11)
    ref('LD DE,FLAGS', 0x11, FLAGS, 10); emit('LD B,8', [0x06, 8], 7)
    ref('CALL compiled groups', 0xcd, shared['groups'], 17)
    emit('LD IX,FLAGS', [0xdd, 0x21, FLAGS & 255, FLAGS >> 8], 14)
    ref('LD DE,MASKS', 0x11, MASKS, 10)
    emit('EXX', [0xd9], 4)
    ref('LD HL,(vector_pointer)', 0x2a, vector_pointer, 16)
    ref('LD DE,FLAGS', 0x11, FLAGS, 10)
    ref('LD BC,last idle flag', 0x01, IDLE_BASE+12, 10)
    a.label('stripe')
    emit('EX DE,HL', [0xeb], 4)
    for i in range(4):
        emit('LD A,(HL)' if i == 0 else 'OR (HL)', [0x7e if i == 0 else 0xb6], 7)
        emit('INC L' if i < 3 else 'INC HL', [0x2c if i < 3 else 0x23], 4 if i < 3 else 6)
    emit('EX DE,HL', [0xeb], 4)
    ref('JP NZ,active_advance', 0xc2, 'active_advance', 10)
    for i in range(16):
        emit('LD A,(HL)' if i == 0 else 'OR (HL)', [0x7e if i == 0 else 0xb6], 7)
        emit('INC HL', [0x23], 6)
    ref('JP NZ,active', 0xc2, 'active', 10)
    emit('LD A,FFh', [0x3e, 255], 7)
    emit('LD (BC),A', [0x02], 7); emit('DEC C', [0x0d], 4)
    emit('EXX', [0xd9], 4)
    advance('DE', 32, 'masks_advanced')
    for _ in range(4): emit('INC IX', [0xdd, 0x23], 10)
    ref('JP stripe_done', 0xc3, 'stripe_done', 10)
    a.label('active_advance'); advance('HL', 16, 'vectors_advanced')
    a.label('active')
    emit('XOR A', [0xaf], 4)
    emit('LD (BC),A', [0x02], 7); emit('DEC C', [0x0d], 4)
    emit('EXX', [0xd9], 4)
    emit('LD B,4', [0x06, 4], 7); ref('CALL compiled groups', 0xcd, shared['groups'], 17)
    a.label('stripe_done')
    emit('EXX', [0xd9], 4); emit('LD A,C', [0x79], 4)
    emit('CP idle base', [0xfe, IDLE_BASE & 255], 7)
    ref('JP NZ,stripe', 0xc2, 'stripe', 10)
    emit('EXX', [0xd9], 4)
    emit('LD B,12', [0x06, 12], 7); ref('CALL attribute groups', 0xcd, shared['groups'], 17)
    emit('RET', [0xc9], 10)
    a.label('end')
    if a.pc > compiled.CODE: raise ValueError('idle decoder overlaps shared compiled groups')
    return a.resolve(), a.labels, rows


def idle_stripes(vectors, bitmap):
    if len(vectors) != 192 or len(bitmap) != 384: raise ValueError('one frame required')
    return [not any(vectors[i*16:i*16+16]) and not any(bitmap[i*32:i*32+32]) for i in range(12)]


def expected_tstates(encoded, vectors, *, vector_address=0xa400):
    """Instruction-table sum, including entry/RET, no IRQ or bank switching."""
    from probe_motion_metadata import restore
    bitmap = restore(encoded, 1, 480, 4)[:384]
    upper, lower, pos = encoded[:8], [], 8
    for mask in upper:
        for bit in range(8):
            present = mask & (128 >> bit)
            lower.append(encoded[pos] if present else 0)
            pos += bool(present)
    # Setup through alternate BC, plus final EXX/LD B/CALL/helper RET/RET.
    total = 154 + 48 + sum(compiled.group_tstates(v) for v in upper)
    for i, idle in enumerate(idle_stripes(vectors, bitmap)):
        groups = lower[i*4:i*4+4]
        # Four flags: 64. A full vector scan: 208+JP 10.
        if idle:
            # Set flag/EXX 22; advance output 27 (26 on carry); IX 40;
            # JP done 10; EXX/LD A,C/CP/JP 25.
            total += 406 - int(((MASKS+i*32) & 255) >= 224)
        else:
            check = 64 + (27-int(((vector_address+i*16) & 255) >= 240) if any(groups) else 218)
            # Active flag/EXX/LD B/CALL/helper RET = 53; loop tail = 25.
            total += check + 78 + sum(compiled.group_tstates(v) for v in groups)
    return total + sum(compiled.group_tstates(v) for v in lower[48:60])
