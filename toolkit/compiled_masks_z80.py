"""Generate straight-line sparse mask expanders in unused bank-7 RAM.

The existing two-level mask stream is unchanged. Zero/full groups retain
the previous fast paths. A partial group selects a 19-byte routine: eight
LDI or zero-store pairs, followed by JP compiled_done. A=0 across LDI.
Bank 7 must stay mapped. Initialization is before playback; normal IRQs
may run. E400..F8FF is generated on the Spectrum, not stored on disk.
"""
from build_zxv_trd import MiniAssembler
from frame_metadata_z80 import MASKS,FLAGS

INIT,CODE,TABLE,BODIES,STRIDE=0xe180,0xe300,0xe400,0xe600,19
END=BODIES+256*STRIDE


def build(*,prefill_entry=None):
    rows=[];a=MiniAssembler(CODE)
    def emit(name,data,ticks):
        rows.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='compiled_metadata'));a.emit(*data)
    def ref(name,op,target,ticks):
        rows.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='compiled_metadata'))
        if isinstance(target,str):a.abs16(op,target)
        else:a.emit(op);a.word(target)
    a.label('decode');emit('PUSH HL',[0xe5],11);emit('POP IX',[0xdd,0xe1],14)
    ref('LD DE,8',0x11,8,10);emit('ADD HL,DE',[0x19],11)
    ref('LD DE,FLAGS',0x11,FLAGS,10);emit('LD B,8',[0x06,8],7);ref('CALL groups',0xcd,'groups',17)
    emit('LD IX,FLAGS',[0xdd,0x21,FLAGS&255,FLAGS>>8],14)
    ref('LD DE,MASKS',0x11,MASKS,10);emit('LD B,60',[0x06,60],7);ref('CALL groups',0xcd,'groups',17)
    emit('RET',[0xc9],10)
    a.label('groups');emit('LD A,(IX+0)',[0xdd,0x7e,0],19);emit('INC IX',[0xdd,0x23],10)
    emit('LD C,A',[0x4f],4);emit('OR A',[0xb7],4);ref('JP Z,zero',0xca,'zero',10)
    emit('CP FFh',[0xfe,255],7);ref('JP Z,full',0xca,'full',10)
    emit('PUSH BC',[0xc5],11);emit('PUSH HL',[0xe5],11)
    emit('LD H,table page',[0x26,TABLE>>8],7);emit('LD L,C',[0x69],4)
    emit('LD A,(HL)',[0x7e],7);emit('INC H',[0x24],4);emit('LD H,(HL)',[0x66],7);emit('LD L,A',[0x6f],4)
    emit('EX (SP),HL',[0xe3],19);emit('XOR A',[0xaf],4);emit('RET (dispatch)',[0xc9],10)
    a.label('zero')
    for i in range(8):
        emit('LD (DE),A',[0x12],7);emit('INC E' if i<7 else 'INC DE',[0x1c if i<7 else 0x13],4 if i<7 else 6)
    ref('JP next',0xc3,'next',10)
    a.label('full');emit('PUSH BC',[0xc5],11)
    for _ in range(8):emit('LDI',[0xed,0xa0],16)
    a.label('compiled_done');emit('POP BC',[0xc1],10)
    a.label('next');emit('DEC B',[0x05],4);ref('JP NZ,groups',0xc2,'groups',10);emit('RET',[0xc9],10)
    a.label('end');runtime=a.resolve();labels=dict(a.labels)
    if a.pc>TABLE:raise ValueError('runtime overlaps table')
    a=MiniAssembler(INIT);a.labels.update(labels)
    a.label('initialize');ref('LD HL,table',0x21,TABLE,10);ref('LD DE,bodies',0x11,BODIES,10)
    emit('LD C,0',[0x0e,0],7);a.label('pattern')
    emit('LD (HL),E',[0x73],7);emit('INC H',[0x24],4);emit('LD (HL),D',[0x72],7)
    emit('DEC H',[0x25],4);emit('INC L',[0x2c],4);emit('PUSH BC',[0xc5],11);emit('LD B,8',[0x06,8],7)
    a.label('bit');emit('SLA C',[0xcb,0x21],8);ref('JP NC,emit_zero',0xd2,'emit_zero',10)
    emit('LD A,ED',[0x3e,0xed],7);emit('LD (DE),A',[0x12],7);emit('INC DE',[0x13],6)
    emit('LD A,A0',[0x3e,0xa0],7);ref('JP second',0xc3,'second',10)
    a.label('emit_zero');emit('LD A,12',[0x3e,0x12],7);emit('LD (DE),A',[0x12],7);emit('INC DE',[0x13],6)
    emit('LD A,1C',[0x3e,0x1c],7)
    a.label('second');emit('LD (DE),A',[0x12],7);emit('INC DE',[0x13],6)
    emit('DEC B',[0x05],4);ref('JP NZ,bit',0xc2,'bit',10)
    # The last zero store must cross an output page, unlike inner fields.
    emit('DEC DE',[0x1b],6);emit('LD A,(DE)',[0x1a],7);emit('CP 1C',[0xfe,0x1c],7)
    ref('JP NZ,last_ready',0xc2,'last_ready',10)
    emit('LD A,13',[0x3e,0x13],7);emit('LD (DE),A',[0x12],7)
    a.label('last_ready');emit('INC DE',[0x13],6)
    for name,value in (('JP opcode',0xc3),('return low',labels['compiled_done']&255),('return high',labels['compiled_done']>>8)):
        emit('LD A,'+name,[0x3e,value],7);emit('LD (DE),A',[0x12],7);emit('INC DE',[0x13],6)
    emit('POP BC',[0xc1],10);emit('INC C',[0x0c],4);ref('JP NZ,pattern',0xc2,'pattern',10)
    if prefill_entry is None:emit('RET',[0xc9],10)
    else:ref('JP queue prefill',0xc3,prefill_entry,10)
    a.label('initialize_end')
    if a.pc>CODE:raise ValueError('generator overlaps runtime')
    labels.update(initialize=a.labels['initialize'],initialize_end=a.pc,table=TABLE,bodies=BODIES,generated_end=END)
    body_rows=[];bodies=bytearray()
    for mask in range(256):
        pc=BODIES+mask*STRIDE
        for i in range(8):
            if mask&(128>>i):
                bodies+=b'\xed\xa0';body_rows.append(dict(address=pc,instruction='LDI',tstates=16,stage='compiled_metadata'))
            else:
                bodies+=bytes([0x12,0x1c if i<7 else 0x13])
                body_rows.extend([dict(address=pc,instruction='LD (DE),A',tstates=7,stage='compiled_metadata'),
                    dict(address=pc+1,instruction='INC E' if i<7 else 'INC DE',tstates=4 if i<7 else 6,stage='compiled_metadata')])
            pc+=2
        bodies+=bytes([0xc3,labels['compiled_done']&255,labels['compiled_done']>>8])
        body_rows.append(dict(address=pc,instruction='JP compiled_done',tstates=10,stage='compiled_metadata'))
    table=bytes((BODIES+m*STRIDE)&255 for m in range(256))+bytes((BODIES+m*STRIDE)>>8 for m in range(256))
    return [(INIT,a.resolve()),(CODE,runtime)],labels,rows+body_rows,[(TABLE,table+bytes(bodies))]


def group_tstates(mask):
    # Whole loop iteration, helper RET excluded. Partial: prologue 64,
    # dispatch 88, body 90+5*popcount-2*LSB, JP 10, POP 10,
    # DEC/JP 14. Full/zero retain their old instruction sequences.
    return 161 if mask==0 else 227 if mask==255 else 276+5*mask.bit_count()-2*(mask&1)


def expected_tstates(encoded):
    upper=encoded[:8];pos=8;lower=[]
    if len(upper)!=8 or upper[-1]&15:raise ValueError('bad upper masks')
    for flags in upper:
        for i in range(8):
            if flags&(128>>i):lower.append(encoded[pos]);pos+=1
            else:lower.append(0)
    if pos+sum(v.bit_count() for v in lower[:60])!=len(encoded):raise ValueError('bad mask length')
    return 158+sum(group_tstates(v) for v in list(upper)+lower[:60])
