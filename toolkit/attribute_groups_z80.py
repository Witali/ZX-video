"""Derive n-2 native attribute updates from two existing n-1 mask lists.

No stream changes. Compact attributes remain exact. Two lists hold absolute
eight-attribute group indices (12..83), with count bytes. Count 72 is also
a full-copy marker with unused index bytes. Raw-attribute frames and the
first two frames use that marker. Otherwise the
metadata decoder's flags identify nonzero masks without scanning 72 bytes.
Constant border attributes and unchanged border masks after warmup are
required. Code and lists occupy previously unused fixed RAM below stack.
"""
from build_zxv_trd import MiniAssembler
from frame_metadata_z80 import FLAGS

LISTS=(0x9c20,0x9c80)
LIST_BYTES=73
CODE=0x9cd0
END_LIMIT=0x9d90


def build(raw_attribute_flag):
    a=MiniAssembler(CODE); listing=[]
    def emit(name,data,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='attribute_groups')); a.emit(*data)
    def addr(name,opcode,value,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='attribute_groups'))
        if isinstance(value,str): a.abs16(opcode,value)
        else: a.emit(opcode); a.word(value)
    def jump(name,opcode,target,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='attribute_groups')); a.rel8(opcode,target)
    a.label('prepare')
    addr('LD A,(next_list)',0x3a,'next_list',13); emit('XOR A0h',[0xee,0xa0],7)
    addr('LD (next_list),A',0x32,'next_list',13)
    emit('LD L,A',[0x6f],4); emit('LD H,9Ch',[0x26,0x9c],7)
    emit('LD E,A',[0x5f],4); emit('LD D,H',[0x54],4); emit('INC E',[0x1c],4); emit('PUSH HL',[0xe5],11)
    addr('LD A,(warmup)',0x3a,'warmup',13); emit('OR A',[0xb7],4)
    jump('JR Z,check_raw',0x28,'check_raw',[7,12])
    emit('DEC A',[0x3d],4); addr('LD (warmup),A',0x32,'warmup',13)
    jump('JR full',0x18,'full',12)
    a.label('check_raw'); addr('LD A,(raw_attributes)',0x3a,raw_attribute_flag,13); emit('OR A',[0xb7],4)
    jump('JR NZ,full',0x20,'full',[7,12])
    addr('LD HL,attribute flags',0x21,FLAGS+49,10)
    emit('LD B,10',[0x06,10],7); emit('LD C,8',[0x0e,8],7)
    a.label('block'); emit('LD A,(HL)',[0x7e],7); emit('INC HL',[0x23],6); emit('OR A',[0xb7],4)
    jump('JR Z,empty',0x28,'empty',[7,12])
    for _ in range(8):
        emit('ADD A,A',[0x87],4)
        tag='skip_'+str(_); jump('JR NC,'+tag,0x30,tag,[7,12])
        emit("EX AF,AF'",[0x08],4); emit('LD A,C',[0x79],4); emit('LD (DE),A',[0x12],7)
        emit('INC E',[0x1c],4); emit("EX AF,AF'",[0x08],4)
        a.label(tag); emit('INC C',[0x0c],4)
    jump('JR next',0x18,'next',12)
    a.label('empty'); emit('LD A,C',[0x79],4); emit('ADD A,8',[0xc6,8],7); emit('LD C,A',[0x4f],4)
    a.label('next'); jump('DJNZ block',0x10,'block',[8,13])
    jump('JR done',0x18,'done',12)
    # Count 72 is a full-copy marker. The renderer does not read its stale
    # index bytes, so no 72-byte list needs to be rebuilt on this path.
    a.label('full'); emit('POP HL',[0xe1],10); emit('LD (HL),72',[0x36,72],10); emit('RET',[0xc9],10)
    a.label('done'); emit('POP HL',[0xe1],10); emit('LD A,E',[0x7b],4); emit('SUB L',[0x95],4)
    emit('DEC A',[0x3d],4); emit('LD (HL),A',[0x77],7); emit('RET',[0xc9],10)
    a.label('state'); a.label('next_list'); a.emit(0x80); a.label('warmup'); a.emit(2); a.label('end')
    if a.pc>END_LIMIT: raise ValueError('attribute lists helper overlaps IRQ stack reserve')
    return a.resolve(),dict(a.labels),listing,[(base,bytes(LIST_BYTES)) for base in LISTS]


def draw_tstates(counts):
    if len(counts)!=2 or any(not 0<=n<=72 for n in counts): raise ValueError('two list counts required')
    # Selection costs 51 T; >=34 groups uses the original 9778-T full copy.
    # Two LD HL/CALL pairs and JP to attribute_end = 64 T in sparse mode.
    # Empty list 32; nonempty list 31 + 285*n including RET.
    return 51+min(9778,64+sum(32 if not n else 31+285*n for n in counts))


def prepare_tstates(flags,*,raw=False,warmup=False):
    if len(flags)!=10: raise ValueError('ten metadata flag bytes required')
    if warmup: return 150
    if raw: return 155
    return 760+152*sum(bool(v) for v in flags)+18*sum(v.bit_count() for v in flags)


def emit_draw(a,emit,ref,imm):
    stage='attributes'
    imm('LD A,(first group count)',0x3a,LISTS[0],13,stage); emit('LD B,A',[0x47],4,stage)
    imm('LD A,(second group count)',0x3a,LISTS[1],13,stage); emit('ADD A,B',[0x80],4,stage)
    emit('CP 34',[0xfe,34],7,stage); ref('JP NC,attribute_full',0xd2,'attribute_full',10,stage)
    for base in LISTS:
        imm('LD HL,attribute list',0x21,base,10,stage)
        ref('CALL draw attribute list',0xcd,'attribute_list',17,stage)
    ref('JP attribute_end',0xc3,'attribute_end',10,stage)
    a.label('attribute_list')
    emit('LD B,(HL)',[0x46],7,stage); emit('INC HL',[0x23],6,stage)
    emit('LD A,B',[0x78],4,stage); emit('OR A',[0xb7],4,stage); emit('RET Z',[0xc8],[5,11],stage)
    a.label('attribute_group')
    emit('LD A,(HL)',[0x7e],7,stage); emit('INC HL',[0x23],6,stage)
    emit('PUSH HL',[0xe5],11,stage); emit('PUSH BC',[0xc5],11,stage)
    for _ in range(3): emit('RLCA',[0x07],4,stage)
    emit('LD C,A',[0x4f],4,stage); emit('AND F8h',[0xe6,0xf8],7,stage)
    emit('LD E,A',[0x5f],4,stage); emit('LD L,A',[0x6f],4,stage)
    emit('LD A,C',[0x79],4,stage); emit('AND 3',[0xe6,3],7,stage); emit('LD H,A',[0x67],4,stage)
    ref('LD A,(screen_base)',0x3a,'screen_base',13,stage)
    emit('OR 18h',[0xf6,0x18],7,stage); emit('OR H',[0xb4],4,stage); emit('LD D,A',[0x57],4,stage)
    emit('LD A,H',[0x7c],4,stage); emit('OR 70h',[0xf6,0x70],7,stage); emit('LD H,A',[0x67],4,stage)
    for _ in range(8): emit('LDI',[0xed,0xa0],16,stage)
    emit('POP BC',[0xc1],10,stage); emit('POP HL',[0xe1],10,stage)
    # ref emits absolute jumps; this short loop is explicitly relative.
    displacement=a.labels['attribute_group']-a.pc-2
    if not -128<=displacement<=127: raise ValueError('attribute loop exceeds relative branch range')
    emit('DJNZ attribute_group',[0x10,displacement&255],[8,13],stage)
    emit('RET',[0xc9],10,stage)
    a.label('attribute_full')
    imm('LD HL,compact attributes',0x21,0x7060,10,stage)
    ref('LD A,(screen_base)',0x3a,'screen_base',13,stage)
    emit('OR 18h',[0xf6,0x18],7,stage); emit('LD D,A',[0x57],4,stage); emit('LD E,96',[0x1e,96],7,stage)
    imm('LD BC,576',0x01,576,10,stage); emit('LD A,36',[0x3e,36],7,stage)
    a.label('attribute_full_chunk')
    for _ in range(16): emit('LDI',[0xed,0xa0],16,stage)
    emit('DEC A',[0x3d],4,stage); ref('JP NZ,attribute_full_chunk',0xc2,'attribute_full_chunk',10,stage)
