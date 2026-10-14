"""CB48 mode-plane kernel; direct native8-row writes and immutable row pairs.

ABI matches CB47: HL=validated packet, A=40h/C0h back screen, bank7 mapped.
Return HL=packet end; clobber both AF/BC/DE/HL sets, preserve IX/IY/SP. IRQs
must preserve both register sets. AF' holds the remaining mode/attribute
bits only during a changed cell; alternate HL scans mode then attribute
planes and alternate C counts groups. No paging or interrupt masking.
"""
from build_zxv_trd import MiniAssembler
from cell_codebook_z80 import BOOK,ROWS,INLINE_CODE


def build(*,zero_runs=False,repeat_rows=False):
    a=MiniAssembler(INLINE_CODE);listing=[];stage='setup'
    def emit(name,blob,t):listing.append(dict(address=a.pc,instruction=name,tstates=t,stage=stage));a.emit(*blob)
    def ld(name,op,value,t):
        if isinstance(value,str):
            listing.append(dict(address=a.pc,instruction=name,tstates=t,stage=stage));a.abs16(op,value)
        else:emit(name,([op] if isinstance(op,int) else list(op))+[value&255,value>>8],t)
    def jr(op,target):
        listing.append(dict(address=a.pc,instruction='JR '+target,tstates=12 if op==0x18 else [7,12],stage=stage));a.rel8(op,target)
    def exaf():emit("EX AF,AF'",[8],4)
    def exx():emit('EXX',[0xd9],4)
    def row():
        emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);emit('LD (DE),A',[0x12],7)
    a.label('draw');ld('LD (screen_high),A',0x32,'screen_high',13);ld('LD (packet),HL',0x22,'packet',16)
    exx();ld('LD HL,(packet)',0x2a,'packet',16)
    if zero_runs:emit('INC HL',[0x23],6);emit('INC HL',[0x23],6)
    emit('LD C,144',[0x0e,144],7);exx()
    if zero_runs:
        emit('LD E,(HL)',[0x5e],7);emit('INC HL',[0x23],6);emit('LD D,0',[0x16,0],7)
        emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6)
        emit('ADD HL,DE',[0x19],11);emit('LD E,A',[0x5f],4);emit('ADD HL,DE',[0x19],11)
    else:ld('LD DE,data offset',0x11,216,10);emit('ADD HL,DE',[0x19],11)
    ld('LD A,(screen_high)',0x3a,'screen_high',13);emit('LD D,A',[0x57],4);emit('LD E,96',[0x1e,96],7)
    stage='mode_mask';a.label('group');exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);exx()
    emit('OR A',[0xb7],4);ld('JP Z,empty group',0xca,'empty',10)
    for cell in range(4):
        s=str(cell)
        stage='mode';emit('RRCA',[0x0f],4);ld('JP C,odd mode',0xda,'odd'+s,10)
        emit('RRCA',[0x0f],4);ld('JP NC,skip cell',0xd2,'skip'+s,10)
        stage='literal';exaf()
        for r in range(8):
            row()
            if r<7:emit('INC D',[0x14],4)
        ld('JP cell done',0xc3,'done'+s,10)
        stage='mode';a.label('odd'+s);emit('RRCA',[0x0f],4);ld('JP C,special mode',0xda,'special'+s,10)
        exaf();stage='dictionary';emit('LD C,(HL)',[0x4e],7);emit('INC HL',[0x23],6);emit('LD B,book page',[6,BOOK>>8],7)
        ld('JP copy cell',0xc3,'copy'+s,10)
        stage='special';a.label('special'+s);exaf();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6)
        emit('OR A',[0xb7],4)
        if repeat_rows:ld('JP M,repeated row bytes',0xfa,'repeat'+s,10)
        ld('JP Z,front copy',0xca,'front'+s,10)
        emit('CP 9',[0xfe,9],7);ld('JP NC,pair form',0xd2,'pair_form'+s,10)
        stage='single_row';emit('DEC A',[0x3d],4);emit('ADD A,D',[0x82],4);emit('LD D,A',[0x57],4);row()
        ld('JP cell done',0xc3,'done'+s,10)
        stage='special';a.label('pair_form'+s);emit('CP 10',[0xfe,10],7);ld('JP Z,dictionary pairs',0xca,'pairs'+s,10)
        # The validated two-row selector packs ordered row indices in its
        # low six bits. Keep the original cell-row high byte in B, avoiding
        # a conditional row scan or a mutable dictionary update.
        stage='two_rows';emit('LD B,D',[0x42],4);emit('LD C,A',[0x4f],4)
        for _ in range(3):emit('RRCA',[0x0f],4)
        emit('AND 7',[0xe6,7],7);emit('ADD A,D',[0x82],4);emit('LD D,A',[0x57],4);row()
        emit('LD A,C',[0x79],4);emit('AND 7',[0xe6,7],7);emit('ADD A,B',[0x80],4);emit('LD D,A',[0x57],4);row()
        ld('JP cell done',0xc3,'done'+s,10)
        stage='pairs';a.label('pairs'+s);emit('LD B,row page',[6,ROWS>>8],7)
        for r in range(4):
            emit('LD C,(HL)',[0x4e],7);emit('INC HL',[0x23],6)
            emit('LD A,(BC)',[0x0a],7);emit('LD (DE),A',[0x12],7);emit('INC B',[4],4);emit('INC D',[0x14],4)
            emit('LD A,(BC)',[0x0a],7);emit('LD (DE),A',[0x12],7);emit('DEC B',[5],4)
            if r<3:emit('INC D',[0x14],4)
        ld('JP cell done',0xc3,'done'+s,10)
        stage='front_source';a.label('front'+s);emit('LD B,D',[0x42],4);emit('LD C,E',[0x4b],4)
        emit('LD A,B',[0x78],4);emit('XOR 80h',[0xee,0x80],7);emit('LD B,A',[0x47],4)
        stage='cell_copy';a.label('copy'+s)
        for r in range(8):
            emit('LD A,(BC)',[0x0a],7);emit('LD (DE),A',[0x12],7)
            if r<7:emit('INC B',[4],4);emit('INC D',[0x14],4)
        stage='cell_return';a.label('done'+s);emit('LD A,D',[0x7a],4);emit('AND F8h',[0xe6,0xf8],7);emit('LD D,A',[0x57],4);exaf()
        stage='mode_mask';a.label('skip'+s);emit('INC E',[0x1c],4)
    a.label('advance');jr(0x20,'same_band');emit('LD A,D',[0x7a],4);emit('ADD A,8',[0xc6,8],7);emit('LD D,A',[0x57],4)
    a.label('same_band');exx();emit('DEC C',[0x0d],4);exx();ld('JP NZ,next group',0xc2,'group',10)
    stage='attribute_mask';a.label('attribute_start');ld('LD A,(screen_high)',0x3a,'screen_high',13);emit('ADD A,24',[0xc6,24],7);emit('LD D,A',[0x57],4);emit('LD E,96',[0x1e,96],7)
    exx();emit('LD C,72',[0x0e,72],7);exx()
    a.label('attributes');exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);exx();emit('OR A',[0xb7],4);ld('JP Z,empty attributes',0xca,'empty_attrs',10)
    for bit in range(8):
        emit('RRCA',[0x0f],4);jr(0x30,'attr_skip'+str(bit));exaf();row();exaf();a.label('attr_skip'+str(bit));emit('INC DE',[0x13],6)
    a.label('attr_advance');exx();emit('DEC C',[0x0d],4);exx();ld('JP NZ,next attrs',0xc2,'attributes',10);emit('RET',[0xc9],10)
    if zero_runs:
        # A zero marker skips several four-cell mode groups at once. The
        #16-bit byte displacement is4*run; every carry through E advances
        # D by8, retaining the Spectrum's physical bitmap page mapping.
        stage='mode_zero_run';a.label('empty');exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6)
        emit('LD B,A',[0x47],4);emit('LD A,C',[0x79],4);emit('SUB B',[0x90],4);emit('LD C,A',[0x4f],4);emit('LD A,B',[0x78],4);exx()
        emit('LD B,0',[6,0],7)
        for _ in range(2):emit('ADD A,A',[0x87],4);emit('RL B',[0xcb,0x10],8)
        emit('ADD A,E',[0x83],4);emit('LD E,A',[0x5f],4);jr(0x30,'no_byte_carry');emit('INC B',[4],4)
        a.label('no_byte_carry');emit('LD A,B',[0x78],4)
        for _ in range(3):emit('RLCA',[7],4)
        emit('ADD A,D',[0x82],4);emit('LD D,A',[0x57],4)
        exx();emit('LD A,C',[0x79],4);emit('OR A',[0xb7],4);exx();ld('JP NZ,next mode group',0xc2,'group',10)
        ld('JP attribute plane',0xc3,'attribute_start',10)
        stage='attribute_zero_run';a.label('empty_attrs');exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6)
        emit('LD B,A',[0x47],4);emit('LD A,C',[0x79],4);emit('SUB B',[0x90],4);emit('LD C,A',[0x4f],4);emit('LD A,B',[0x78],4);exx()
        emit('PUSH HL',[0xe5],11);emit('LD L,A',[0x6f],4);emit('LD H,0',[0x26,0],7)
        for _ in range(3):emit('ADD HL,HL',[0x29],11)
        emit('ADD HL,DE',[0x19],11);emit('EX DE,HL',[0xeb],4);emit('POP HL',[0xe1],10)
        exx();emit('LD A,C',[0x79],4);emit('OR A',[0xb7],4);exx();ld('JP NZ,next attributes',0xc2,'attributes',10);emit('RET',[0xc9],10)
    else:
        stage='mode_mask';a.label('empty');emit('LD A,E',[0x7b],4);emit('ADD A,4',[0xc6,4],7);emit('LD E,A',[0x5f],4);ld('JP advance',0xc3,'advance',10)
        stage='attribute_mask';a.label('empty_attrs');emit('LD A,E',[0x7b],4);emit('ADD A,8',[0xc6,8],7);emit('LD E,A',[0x5f],4);jr(0x30,'attrs_advanced');emit('INC D',[0x14],4)
        a.label('attrs_advanced');ld('JP attr advance',0xc3,'attr_advance',10)
    if repeat_rows:
        stage='repeat_call'
        for cell in range(4):
            a.label('repeat'+str(cell));ld('CALL repeated row writer',0xcd,'repeat_rows',17);ld('JP cell done',0xc3,'done'+str(cell),10)
    stage='book_load';a.label('load_book');emit('LD C,0',[0x0e,0],7);a.label('book_entry');emit('LD B,book page',[6,BOOK>>8],7)
    for r in range(8):
        emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);emit('LD (BC),A',[2],7)
        if r<7:emit('INC B',[4],4)
    emit('INC C',[0x0c],4);jr(0x20,'book_entry');emit('RET',[0xc9],10)
    a.label('state');a.label('packet');a.word(0);a.label('screen_high');a.emit(0);a.label('end')
    if a.pc>0x9400:raise ValueError('native-mode renderer exceeds9400h')
    main=a;extra=[]
    if repeat_rows:
        # The unused legacy-frame gapB200h..B700h follows the measured AY
        # forest ending atB1BCh. Share the writer across four mode positions.
        # B keeps the seven transition flags while A carries the current
        # actual bitmap byte. Alternate AF and the plane cursor stay intact.
        a=MiniAssembler(0xb200);stage='repeat_rows';a.label('repeat_rows')
        emit('LD B,A',[0x47],4);row()
        for r in range(1,8):
            emit('INC D',[0x14],4);emit('SRL B',[0xcb,0x38],8);jr(0x30,'reuse_row'+str(r))
            emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);a.label('reuse_row'+str(r));emit('LD (DE),A',[0x12],7)
        emit('RET',[0xc9],10);a.label('repeat_end')
        labels=main.labels|a.labels;extra=[(a.origin,a.resolve(labels))]
    else:labels=main.labels
    return [(main.origin,main.resolve(labels))]+extra,dict(labels),dict(native_bitmap=True,native_modeplane=True,dictionary=True,front_reuse=True,partial_rows=True,
        inline_cells=True,origin=main.origin,instruction_listing=listing,code_bytes=len(main.code)-3+sum(len(data) for _,data in extra),state_bytes=3,book_bytes=2048,row_table_bytes=512,popcount_bytes=0,
        timing_scope='Instruction table; complete CPU and real disk execution determine the total delta.',timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
