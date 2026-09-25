"""Experimental one-sector-at-a-time input producer for local-bank ZX0.

Reads the existing interleaved stream without padding or repeated sectors.
Only the last shared sector is copied through BC00 between input slots.
Caller passes an empty slot's region (0..3 -> banks 0/1/3/4) to begin, then
calls step until A=1. A=0 means pending; each step reads at most one sector.
The current decoder must have finished before starting another block.
This module does not implement queue ownership, frame output or pacing.
"""
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers,PAGE

CODE,END_LIMIT,CARRY=0x7d50,0x8000,0xbc00


def build(z, disk):
    if z['end']>CODE:raise ValueError('local decoder overlaps input producer')
    a=MiniAssembler(CODE);rows=[];e,n=helpers(a,rows,'direct_slot_input')
    def branch(op,target):n('JP '+str(target),op,target,10)
    def call(target):n('CALL '+str(target),0xcd,target,17)
    def load(name):n('LD A,('+name+')',0x3a,name,13)
    def store(name):n('LD ('+name+'),A',0x32,name,13)
    def wordload(name):n('LD HL,('+str(name)+')',0x2a,name,16)
    def wordstore(name):n('LD ('+str(name)+'),HL',0x22,name,16)
    def ret():e('RET',[0xc9],10)
    a.label('begin')
    e('CP 4',[0xfe,4],7);branch(0xd2,'fatal')
    n('LD (write_region),A',0x32,disk['write_region'],13)
    e('XOR A',[0xaf],4);store('phase')
    e('LD A,C0h',[0x3e,0xc0],7);n('LD (write_high),A',0x32,disk['write_high'],13)
    call('page_slot');load('has_carry');e('OR A',[0xb7],4);branch(0xca,'begin_done')
    n('LD HL,carry',0x21,CARRY,10);n('LD DE,input',0x11,0xc000,10);call('copy_sector')
    e('LD A,C1h',[0x3e,0xc1],7);n('LD (write_high),A',0x32,disk['write_high'],13)
    a.label('begin_done');e('XOR A',[0xaf],4);ret()

    a.label('step');call('page_slot');load('phase');e('OR A',[0xb7],4);branch(0xc2,'body')
    n('LD A,(write_high)',0x3a,disk['write_high'],13);e('CP C0h',[0xfe,0xc0],7);branch(0xca,'read_pending')
    e('CP C1h',[0xfe,0xc1],7);branch(0xc2,'header')
    load('offset');e('CP 253',[0xfe,253],7);branch(0xd2,'read_pending')
    a.label('header');load('offset');e('LD L,A',[0x6f],4);e('LD H,C0h',[0x26,0xc0],7)
    # DE=decoded length, BC=compressed length, HL=start of compressed bytes.
    for text,op,t in (('LD E,(HL)',0x5e,7),('INC HL',0x23,6),('LD D,(HL)',0x56,7),('INC HL',0x23,6),
                      ('LD C,(HL)',0x4e,7),('INC HL',0x23,6),('LD B,(HL)',0x46,7),('INC HL',0x23,6)):
        e(text,[op],t)
    wordstore(z['input_pointer']);n('LD (compressed_length),BC',(0xed,0x43),'compressed_length',20)
    n('LD (decoded_length),DE',(0xed,0x53),z['block_length'],20)
    e('PUSH HL',[0xe5],11);e('PUSH BC',[0xc5],11);e('EX DE,HL',[0xeb],4);call('validate_length')
    n('LD DE,output',0x11,0xe000,10);e('ADD HL,DE',[0x19],11);wordstore(z['block_end'])
    e('POP HL',[0xe1],10);call('validate_length');e('POP DE',[0xd1],10);e('ADD HL,DE',[0x19],11)
    wordstore('compressed_end');e('LD A,H',[0x7c],4);e('CP E0h',[0xfe,0xe0],7)
    branch(0xda,'end_fits');branch(0xc2,'fatal');e('LD A,L',[0x7d],4);e('OR A',[0xb7],4);branch(0xc2,'fatal')
    a.label('end_fits');e('LD A,L',[0x7d],4);store('offset');e('OR A',[0xb7],4)
    e('LD A,H',[0x7c],4);branch(0xca,'aligned_end');e('INC A',[0x3c],4)
    a.label('aligned_end');store('target_high')
    e('XOR A',[0xaf],4);n('LD (stored),A',0x32,z['block_stored'],13)
    e('LD A,1',[0x3e,1],7);store('phase')
    a.label('body');load('phase');e('CP 2',[0xfe,2],7);branch(0xca,'ready_return')
    load('target_high');e('LD B,A',[0x47],4);n('LD A,(write_high)',0x3a,disk['write_high'],13)
    e('CP B',[0xb8],4);branch(0xda,'read_pending')
    load('offset');e('OR A',[0xb7],4);store('has_carry');branch(0xca,'ready')
    wordload('compressed_end');e('LD L,0',[0x2e,0],7);n('LD DE,carry',0x11,CARRY,10);call('copy_sector')
    a.label('ready');e('LD A,2',[0x3e,2],7);store('phase')
    a.label('ready_return');e('LD A,1',[0x3e,1],7);ret()
    a.label('read_pending');call('read_sector');e('XOR A',[0xaf],4);ret()

    a.label('validate_length')
    e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);branch(0xca,'fatal')
    e('PUSH HL',[0xe5],11);n('LD BC,8193',0x01,8193,10);e('OR A',[0xb7],4)
    e('SBC HL,BC',[0xed,0x42],15);e('POP HL',[0xe1],10);branch(0xd2,'fatal');ret()
    a.label('page_slot');n('LD A,(write_region)',0x3a,disk['write_region'],13)
    e('CP 2',[0xfe,2],7);branch(0xda,'page_value');e('INC A',[0x3c],4)
    a.label('page_value');e('OR 10h',[0xf6,0x10],7);branch(0xc3,PAGE)

    a.label('copy_sector');n('LD BC,256',0x01,256,10);e('LD A,8',[0x3e,8],7)
    a.label('copy_chunk')
    for _ in range(32):e('LDI',[0xed,0xa0],16)
    e('DEC A',[0x3d],4);branch(0xc2,'copy_chunk');ret()

    a.label('read_sector');wordload(disk['remaining']);e('LD A,H',[0x7c],4);e('OR L',[0xb5],4);branch(0xca,'fatal')
    # The existing layout leaves its first partial track linear. Subsequent
    # tracks use the current adapter's 0,8,1,9,... cursor. Repair only that
    # initial cursor after a read; no sector is read twice or reordered.
    load('linear');e('OR A',[0xb7],4);branch(0xca,'read_interleaved')
    wordload(disk['disk_position']);e('INC L',[0x2c],4);e('BIT 4,L',[0xcb,0x65],8);branch(0xca,'linear_next')
    e('LD L,0',[0x2e,0],7);e('INC H',[0x24],4)
    e('XOR A',[0xaf],4);store('linear')
    a.label('linear_next');e('PUSH HL',[0xe5],11);call(disk['read_one']);e('POP HL',[0xe1],10)
    wordstore(disk['disk_position']);ret()
    a.label('read_interleaved');branch(0xc3,disk['read_one'])
    a.label('fatal');e('HALT',[0x76],4)
    a.label('state')
    for name,value in (('phase',0),('has_carry',0),('offset',0),('target_high',0),('linear',1)):
        a.label(name);a.emit(value)
    for name in ('compressed_length','compressed_end'):a.label(name);a.word(0)
    a.label('end')
    if a.pc>END_LIMIT:raise ValueError(f'direct producer overlaps reconstruction: {a.pc:04x}')
    return a.resolve(),dict(a.labels),rows
