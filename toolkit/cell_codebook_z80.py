"""Experimental CB41 cell renderer: exact masks, planar book and row fallback.

Component ABI: HL=validated frame payload (no length word), A=40h/C0h for
an already mapped back screen. Return HL=end of consumed payload. Clobbers
AF/BC/DE/HL and their alternatives; preserves IX/IY/SP and performs no paging,
publication or interrupt masking. Caller must preserve both register sets
in its IRQ path. Dictionary presence is fixed when assembling the volume.

Layout is provisional: book/popcount replace part of the obsolete compact
frame, not additional claimed free RAM in the existing production player.
"""
from build_zxv_trd import MiniAssembler

CODE, ROWS, BOOK, POPCOUNT = 0x9000,0x9e00,0xa800,0xb000


def build(*,dictionary=True,front_reuse=False):
    if front_reuse and not dictionary:raise ValueError('front reuse requires the cell book')
    a=MiniAssembler(CODE);listing=[];stage='setup'
    def emit(name,blob,t):listing.append(dict(address=a.pc,instruction=name,tstates=t,stage=stage));a.emit(*blob)
    def fixed(name,op,value,t):
        if isinstance(op,int):op=[op]
        emit(name,[*op,value&255,value>>8],t)
    def labelop(name,op,label,t):
        listing.append(dict(address=a.pc,instruction=name,tstates=t,stage=stage));a.abs16(op,label)
    def jr(op,label):
        listing.append(dict(address=a.pc,instruction='JR '+label,tstates=12 if op==0x18 else [7,12],stage=stage));a.rel8(op,label)
    def exx():emit('EXX',[0xd9],4)
    def exaf():emit("EX AF,AF'",[8],4)
    a.label('draw');labelop('LD (screen_high),A',0x32,'screen_high',13)
    labelop('LD (packet),HL',0x22,'packet',16)
    if dictionary:
        # Alternate HL scans the bitmap mask while primary HL indexes popcounts.
        exx();fixed('LD HL,popcounts',0x21,POPCOUNT,10)
        fixed('LD DE,0',0x11,0,10);emit('LD B,72',[6,72],7)
        a.label('count');exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);exx()
        emit('LD L,A',[0x6f],4);emit('LD A,(HL)',[0x7e],7);emit('ADD A,E',[0x83],4);emit('LD E,A',[0x5f],4)
        jr(0x30,'count_no_carry');emit('INC D',[0x14],4);a.label('count_no_carry')
        listing.append(dict(address=a.pc,instruction='DJNZ count',tstates=[8,13],stage=stage));a.rel8(0x10,'count')
        rounding=3 if front_reuse else 7
        fixed(f'LD HL,{rounding}',0x21,rounding,10);emit('ADD HL,DE',[0x19],11)
        for _ in range(2 if front_reuse else 3):emit('SRL H',[0xcb,0x3c],8);emit('RR L',[0xcb,0x1d],8)
        labelop('LD BC,(packet)',[0xed,0x4b],'packet',20);emit('ADD HL,BC',[9],11)
        fixed('LD BC,144',1,144,10);emit('ADD HL,BC',[9],11)
    else:
        fixed('LD DE,144',0x11,144,10);emit('ADD HL,DE',[0x19],11)
    # Primary HL=data; alternate HL=bitmap mask, DE=mode mask, B=sentinel.
    exx();labelop('LD HL,(packet)',0x2a,'packet',16);emit('PUSH HL',[0xe5],11)
    fixed('LD DE,144',0x11,144,10);emit('ADD HL,DE',[0x19],11);emit('EX DE,HL',[0xeb],4)
    emit('POP HL',[0xe1],10);emit('LD B,1',[6,1],7);emit('LD C,72',[0x0e,72],7);exx()
    labelop('LD A,(screen_high)',0x3a,'screen_high',13);emit('LD D,A',[0x57],4);emit('LD E,96',[0x1e,96],7)
    stage='bitmap_mask';a.label('bitmap_group')
    exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);exx()
    for _ in range(8):
        emit('RRCA',[0x0f],4);labelop('CALL C,cell',0xdc,'cell', [10,17]);emit('INC E',[0x1c],4)
    jr(0x20,'same_band');emit('LD A,D',[0x7a],4);emit('ADD A,8',[0xc6,8],7);emit('LD D,A',[0x57],4)
    a.label('same_band');exx();emit('DEC C',[0x0d],4);exx();labelop('JP NZ,bitmap_group',0xc2,'bitmap_group',10)
    stage='attribute_mask'
    labelop('LD A,(screen_high)',0x3a,'screen_high',13);emit('ADD A,24',[0xc6,24],7)
    emit('LD D,A',[0x57],4);emit('LD E,96',[0x1e,96],7)
    exx();emit('LD C,72',[0x0e,72],7);exx()
    a.label('attribute_group');exx();emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);exx()
    for _ in range(8):
        emit('RRCA',[0x0f],4);labelop('CALL C,attribute',0xdc,'attribute',[10,17]);emit('INC DE',[0x13],6)
    exx();emit('DEC C',[0x0d],4);exx();labelop('JP NZ,attribute_group',0xc2,'attribute_group',10)
    emit('RET',[0xc9],10)
    stage='mode';a.label('cell');exaf()
    if dictionary:
        exx();emit('SRL B',[0xcb,0x38],8);jr(0x20,'mode_ready')
        # A drained sentinel is exactly B=1, so SRL already sets carry.
        # LD/INC DE preserve it; RRA inserts the next sentinel without SCF.
        emit('LD A,(DE)',[0x1a],7);emit('INC DE',[0x13],6)
        emit('RRA',[0x1f],4);emit('LD B,A',[0x47],4)
        a.label('mode_ready')
        if front_reuse:
            # Two bits always consume the sentinel in pairs. Modes are
            # 00 literal, 01 book, 10 same-position front; 11 is rejected
            # by the builder, as spatial copying is not a native feature.
            jr(0x38,'book_mode');emit('SRL B',[0xcb,0x38],8);exx()
            labelop('JP NC,literal',0xd2,'literal',10)
            stage='front_source'
            emit('LD B,D',[0x42],4);emit('LD C,E',[0x4b],4)
            emit('LD A,B',[0x78],4);emit('XOR 80h',[0xee,0x80],7);emit('LD B,A',[0x47],4)
            labelop('JP copy cell',0xc3,'copy_cell',10)
            stage='mode';a.label('book_mode');emit('SRL B',[0xcb,0x38],8);exx()
        else:exx();jr(0x30,'literal')
        stage='dictionary'
        emit('LD C,(HL)',[0x4e],7);emit('INC HL',[0x23],6);emit('LD B,book page',[6,BOOK>>8],7)
        a.label('copy_cell')
        if front_reuse:stage='cell_copy'
        for i in range(8):
            emit('LD A,(BC)',[0x0a],7);emit('LD (DE),A',[0x12],7)
            if i<7:emit('INC B',[4],4);emit('INC D',[0x14],4)
        jr(0x18,'cell_done')
    stage='literal';a.label('literal');emit('LD B,row page',[6,ROWS>>8],7)
    for i in range(4):
        emit('LD C,(HL)',[0x4e],7);emit('INC HL',[0x23],6)
        emit('LD A,(BC)',[0x0a],7);emit('LD (DE),A',[0x12],7)
        emit('INC B',[4],4);emit('INC D',[0x14],4)
        emit('LD A,(BC)',[0x0a],7);emit('LD (DE),A',[0x12],7);emit('DEC B',[5],4)
        if i<3:emit('INC D',[0x14],4)
    stage='cell_return';a.label('cell_done')
    emit('LD A,D',[0x7a],4);emit('AND F8h',[0xe6,0xf8],7);emit('LD D,A',[0x57],4);exaf();emit('RET',[0xc9],10)
    stage='attributes';a.label('attribute');exaf();emit('LD A,(HL)',[0x7e],7)
    emit('LD (DE),A',[0x12],7);emit('INC HL',[0x23],6);exaf();emit('RET',[0xc9],10)
    stage='book_load';a.label('load_book');emit('LD C,0',[0x0e,0],7)
    a.label('book_entry');emit('LD B,book page',[6,BOOK>>8],7)
    for i in range(8):
        emit('LD A,(HL)',[0x7e],7);emit('INC HL',[0x23],6);emit('LD (BC),A',[2],7)
        if i<7:emit('INC B',[4],4)
    emit('INC C',[0x0c],4);jr(0x20,'book_entry');emit('RET',[0xc9],10)
    a.label('state');a.label('packet');a.word(0);a.label('screen_high');a.emit(0);a.label('end')
    if a.pc>0x9d00:raise ValueError('renderer exceeds provisional code allocation')
    regions=[(CODE,a.resolve()),(POPCOUNT,bytes(i.bit_count() for i in range(256)))]
    return regions,a.labels,dict(dictionary=dictionary,front_reuse=front_reuse,instruction_listing=listing,code_bytes=len(regions[0][1])-3,
        state_bytes=3,book_bytes=2048,popcount_bytes=256,row_table_bytes=512,
        layout_scope='Component-only: reuses obsolete compact-frame range A800..B0FF; integration must remove old frame consumers.',
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
