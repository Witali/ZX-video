"""Final-input guard bypass shared by raw-v2 streaming applications."""


def emit_guard_update(a, z, *, emit=None, operand=None, label_prefix=''):
    """Emit the existing Z80 guard patcher, with all_loaded (0/1) in A.

    Call only while the decoder is suspended. First publish input_high and
    both frontier operands, then set all_loaded, and only mark complete after
    the last input and shared-sector tail are saved. Clobbers AF and HL;
    BC/DE/AF' stay intact. Falls through (append RET in a standalone helper).
    Restores guarded jumps on a new partial block and bypasses guards after
    final input, with zero additional per-token instructions. Optional emit/
    operand callbacks have the MiniAssembler tracing convention and preserve
    application timing listings. Default callbacks return an instruction list.
    """
    rows = []
    if emit is None:
        def emit(name, data, ticks):
            rows.append(dict(address=a.pc, instruction=name, tstates=ticks))
            a.emit(*data)
    if operand is None:
        def operand(name, opcode, value, ticks):
            rows.append(dict(address=a.pc, instruction=name, tstates=ticks))
            if isinstance(value, str):
                a.abs16(opcode, value)
            else:
                a.emit(opcode)
                a.word(value)
    def store(label):
        operand('LD ('+str(label)+'),A', 0x32, label, 13)
    def jump(op, label):
        operand('JP '+label, op, label, 10)
    name = label_prefix + 'set_guards'
    emit('OR A',[0xb7],4)
    emit('LD A,PUSH AF',[0x3e,0xf5],7)
    jump(0xca,name)
    emit('LD A,RET',[0x3e,0xc9],7)
    a.label(name)
    if 'header_patch' in z:
        store(z['header_patch'])
    store(z['guard_literals'])
    # OR's zero flag remains live across LD. Repoint the original branches
    # instead of adding a per-token test after the complete block is retained.
    for key, active, complete, operands in (
            ('token',z['token_guard'],z['token_body'],('token_high_target','token_low_target','token_end_target')),
            ('long8',z['guard_long8'],z['CopyMoreLiterals'],('long8_target',)),
            ('long16',z['guard_long16'],z['NextUseBC'],('long16_target',))):
        operand('LD HL,guarded '+key,0x21,active,10)
        jump(0xca,label_prefix+'set_'+key)
        operand('LD HL,complete '+key,0x21,complete,10)
        a.label(label_prefix+'set_'+key)
        for target in operands:
            operand('LD ('+target+'),HL',0x22,z[target],16)
    return rows
