"""Raw LZ4 Z80 decoder, with the existing bank-local coroutine ABI.

Original project implementation of the public LZ4 block specification.
Reuse the project's AF/AF'-preserving wrapper from resumable_lzsa2; keep
that module and its upstream license notice. No LZSA decoding code executes.
Long literal/match copies poll the output quota every 256 bytes. Small runs
poll at sequence boundaries. Only host-validated <=15872-byte blocks enter.
"""
from build_zxv_trd import MiniAssembler
import resumable_lzsa2 as wrapper

PREFIX,PREFIX_LIMIT,STACK=wrapper.PREFIX,wrapper.PREFIX_LIMIT,wrapper.STACK


def build(*,core=0x8de0,core_limit=0x8ef7,fast_short=True):
    old_regions,old,old_report=wrapper.build(core=core,core_limit=core_limit)
    a=MiniAssembler(core);rows=[]
    def emit(name,code,t):rows.append(dict(address=a.pc,instruction=name,tstates=t));a.emit(*code)
    def address(name,op,label,t):
        rows.append(dict(address=a.pc,instruction=name,tstates=t))
        if isinstance(label,int):
            a.emit(*([op] if isinstance(op,int) else op));a.word(label)
        else:a.abs16(op,label)
    def jp(op,label):address('JP '+label,op,label,10)
    def jr(op,label):
        rows.append(dict(address=a.pc,instruction='JR '+label,tstates=12 if op==0x18 else [7,12]));a.rel8(op,label)
    def call(label):address('CALL '+label,0xcd,label,17)
    def inc():emit('INC HL',[0x23],6)
    def ldir():emit('LDIR',[0xed,0xb0],[16,21])
    a.label('start')
    for suffix in ('high','low'):
        address('LD A,(block end)',0x3a,old['block_end']+(suffix=='high'),13)
        address('LD (end operand),A',0x32,'end_'+suffix,13)
    a.label('Token')
    emit('LD A,(HL)',[0x7e],7);inc();emit('LD B,A',[0x47],4)
    emit('AND 15',[0xe6,15],7);emit("EX AF,AF'",[8],4)
    emit('LD A,B',[0x78],4);emit('AND F0h',[0xe6,0xf0],7);jr(0x28,'AfterLiterals')
    for _ in range(4):emit('RRCA',[0x0f],4)
    emit('LD C,A',[0x4f],4);emit('LD B,0',[6,0],7);emit('CP 15',[0xfe,15],7)
    if fast_short:
        jr(0x20,'ShortLiterals');call('Length');call('CopyRun');jr(0x18,'AfterLiterals')
        a.label('ShortLiterals');ldir()
    else:
        address('CALL Z,Length',0xcc,'Length',[10,17]);call('CopyRun')
    a.label('AfterLiterals')
    emit('LD A,D',[0x7a],4);a.labels['end_high']=a.pc+1;emit('CP end high',[0xfe,0],7);jr(0x20,'Match')
    emit('LD A,E',[0x7b],4);a.labels['end_low']=a.pc+1;emit('CP end low',[0xfe,0],7);emit('RET Z',[0xc8],[5,11])
    a.label('Match')
    emit('LD C,(HL)',[0x4e],7);inc();emit('LD B,(HL)',[0x46],7);inc()
    emit('PUSH HL',[0xe5],11);emit('LD H,D',[0x62],4);emit('LD L,E',[0x6b],4)
    emit('OR A',[0xb7],4);emit('SBC HL,BC',[0xed,0x42],15)
    if not fast_short:emit('EX (SP),HL',[0xe3],19)
    emit("EX AF,AF'",[8],4);emit('ADD A,4',[0xc6,4],7);emit('LD C,A',[0x4f],4);emit('LD B,0',[6,0],7)
    emit('CP 19',[0xfe,19],7)
    if fast_short:
        jr(0x28,'LongMatch');ldir()
    else:
        address('CALL Z,Length',0xcc,'Length',[10,17])
        emit('EX (SP),HL',[0xe3],19);call('CopyRun')
    a.label('AfterMatch');emit('POP HL',[0xe1],10)
    call('Quota');jp(0xc3,'Token')
    if fast_short:
        a.label('LongMatch');emit('EX (SP),HL',[0xe3],19);call('Length')
        emit('EX (SP),HL',[0xe3],19);call('CopyRun');jp(0xc3,'AfterMatch')
    a.label('Length')
    emit('LD A,(HL)',[0x7e],7);inc();emit('PUSH AF',[0xf5],11)
    emit('ADD A,C',[0x81],4);emit('LD C,A',[0x4f],4);jr(0x30,'NoCarry')
    emit('INC B',[4],4);jp(0xca,'fatal')
    a.label('NoCarry');emit('POP AF',[0xf1],10);emit('CP 255',[0xfe,255],7);jr(0x28,'Length');emit('RET',[0xc9],10)
    a.label('CopyRun')
    emit('LD A,B',[0x78],4);emit('OR A',[0xb7],4);jr(0x28,'SmallCopy')
    emit('PUSH BC',[0xc5],11);emit('LD BC,256',[1,0,1],10);ldir();emit('POP BC',[0xc1],10)
    emit('DEC B',[5],4);call('Quota');jr(0x18,'CopyRun')
    a.label('SmallCopy')
    emit('LD A,C',[0x79],4);emit('OR A',[0xb7],4);emit('RET Z',[0xc8],[5,11]);ldir();emit('RET',[0xc9],10)
    a.label('Quota')
    emit('LD A,D',[0x7a],4);a.labels['high_operand']=a.pc+1;emit('CP target high',[0xfe,0],7)
    emit('RET C',[0xd8],[5,11]);jr(0x20,'Suspend')
    emit('LD A,E',[0x7b],4);a.labels['low_operand']=a.pc+1;emit('CP target low',[0xfe,0],7);emit('RET C',[0xd8],[5,11])
    a.label('Suspend');jp(0xc3,'slice_yield')
    labels={k:v for k,v in old.items() if PREFIX<=v<=old_report['prefix_end']}|a.labels
    if a.pc>core_limit:raise ValueError(('LZ4 core exceeds allocation',hex(a.pc),hex(core_limit)))
    # Patch only the wrapper's address operands that refer into the core.
    prefix=bytearray(old_regions[0][1]);remap={old[k]:labels[k] for k in ('start','high_operand','low_operand')}
    for row in old_report['instruction_listing']:
        pc=row['address']
        if not PREFIX<=pc<labels['state']:continue
        op=prefix[pc-PREFIX]
        if op in (0xc3,0x32):
            at=pc-PREFIX+1;value=int.from_bytes(prefix[at:at+2],'little')
            if value in remap:prefix[at:at+2]=remap[value].to_bytes(2,'little')
        rows.append(row)
    regions=[(PREFIX,bytes(prefix)),(core,a.resolve(labels))]
    return regions,labels,dict(prefix_end=old_report['prefix_end'],core_end=a.pc,
        code_bytes=sum(len(blob) for _,blob in regions),
        patched_addresses=[labels[k] for k in ('end_high','end_low','high_operand','low_operand')],
        instruction_listing=rows,copy_quantum_bytes=256,fast_short=fast_short,
        trusted_input='host validates lengths, offsets, exact EOF and bank overlap before creating a player stream',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
        format_source='https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md')
