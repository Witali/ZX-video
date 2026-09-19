"""Fixed six-IRQ frame deadlines for the FAP1 reader. No disk producer yet."""
from build_zxv_trd import MiniAssembler

CODE = 0xde00


def build(packet, audio, *, zx0=None, lookahead=False):
    if lookahead and zx0 is None: raise ValueError('lookahead requires ZX0 labels')
    a, listing = MiniAssembler(CODE), []
    def emit(name, data, ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,phase='schedule'))
        a.emit(*data)
    def addr(name, opcode, value, ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,phase='schedule'))
        if isinstance(value,str): a.abs16(opcode,value)
        else:
            a.emit(*(opcode if isinstance(opcode,tuple) else (opcode,))); a.word(value)
    a.label('start')
    addr('CALL audio_start',0xcd,audio['audio_start'],17)
    addr('LD HL,(elapsed_fields)',0x2a,audio['elapsed_fields'],16)
    addr('LD (deadline),HL',0x22,'deadline',16)
    addr('JP wait_publish',0xc3,'wait_publish',10)
    a.label('play_one')
    addr('CALL next_frame',0xcd,packet['next_frame'],17)
    addr('CALL wait_publish',0xcd,'wait_publish',17)
    emit('RET',[0xc9],10)
    a.label('wait_publish')
    addr('LD HL,(elapsed_fields)',0x2a,audio['elapsed_fields'],16)
    addr('LD DE,(deadline)',(0xed,0x5b),'deadline',20)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
    addr('JP NC,due',0xd2,'due',10)
    if lookahead:
        # Keep a complete field for IRQ and the bounded decode quantum.
        emit('INC HL',[0x23],6); emit('LD A,H',[0x7c],4); emit('OR L',[0xb5],4)
        addr('JP Z,wait_field',0xca,'wait_field',10)
        addr('CALL ahead',0xcd,'ahead',17)
        emit('OR A',[0xb7],4); addr('JP NZ,wait_publish',0xc2,'wait_publish',10)
    a.label('wait_field')
    emit('EI',[0xfb],4); emit('HALT',[0x76],4)
    addr('JP wait_publish',0xc3,'wait_publish',10)
    a.label('due')
    addr('LD (late_fields),HL',0x22,'late_fields',16)
    addr('CALL publish_bridge',0xcd,packet['publish_bridge'],17)
    addr('LD HL,(deadline)',0x2a,'deadline',16)
    addr('LD DE,6',0x11,6,10); emit('ADD HL,DE',[0x19],11)
    addr('LD (deadline),HL',0x22,'deadline',16)
    emit('RET',[0xc9],10)
    if lookahead:
        a.label('ahead')
        addr('LD HL,(slice_output)',0x2a,zx0['slice_output'],16)
        addr('LD DE,2000',0x11,8192,10); emit('ADD HL,DE',[0x19],11)
        addr('LD DE,(block_length)',(0xed,0x5b),zx0['block_length'],20)
        emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
        addr('JP Z,ahead_done',0xca,'ahead_done',10)
        emit('ADD HL,DE',[0x19],11)
        addr('LD DE,256',0x11,256,10); emit('ADD HL,DE',[0x19],11)
        addr('LD DE,(block_length)',(0xed,0x5b),zx0['block_length'],20)
        emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
        addr('JP C,ahead_fits',0xda,'ahead_fits',10)
        emit('EX DE,HL',[0xeb],4); addr('JP ahead_target',0xc3,'ahead_target',10)
        a.label('ahead_fits'); emit('ADD HL,DE',[0x19],11)
        a.label('ahead_target')
        addr('LD DE,E000',0x11,0xe000,10); emit('ADD HL,DE',[0x19],11)
        addr('LD (slice_target),HL',0x22,zx0['slice_target'],16)
        addr('CALL slice_until',0xcd,zx0['slice_until'],17)
        emit('LD A,1',[0x3e,1],7); emit('RET',[0xc9],10)
        a.label('ahead_done'); emit('XOR A',[0xaf],4); emit('RET',[0xc9],10)
    a.label('state')
    a.label('deadline'); a.word(0)
    a.label('late_fields'); a.word(0)
    a.label('end')
    if a.pc > 0xe000: raise ValueError('frame clock overlaps ZX0 history')
    return a.resolve(), dict(a.labels), listing
