"""Skip eight empty reconstruction masks using existing metadata flags.

The controller occupies the unused tail below AY, not another RAM bank.
HL traverses A640..A69F, DE traverses 7000..72FF, B indexes the twelve
flag bytes at BFB0..BFBB, C shifts a flag. The shared group routine may
clobber BC but preserves HL and advances DE by eight. No stream changes.
"""
from build_zxv_trd import MiniAssembler
from frame_metadata_z80 import FLAGS

CODE, END_LIMIT = 0x9360, 0x9400


def build(labels):
    a=MiniAssembler(CODE); a.labels.update(labels); rows=[]
    def emit(name,data,ticks):
        rows.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='attribute_pass'))
        a.emit(*data)
    def addr(name,op,target,ticks):
        rows.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='attribute_pass'))
        if isinstance(target,str): a.abs16(op,target)
        else: a.emit(op); a.word(target)
    def jr(name,op,target,ticks):
        rows.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='attribute_pass'))
        a.rel8(op,target)
    def advance(amount,tag):
        emit('LD A,E',[0x7b],4); emit('ADD A,'+str(amount),[0xc6,amount],7)
        emit('LD E,A',[0x5f],4); jr('JR NC,'+tag,0x30,tag,[7,12])
        emit('INC D',[0x14],4); a.label(tag)
    a.label('attribute_flag_scan')
    addr('LD HL,(attribute_masks)',0x2a,'attribute_masks',16)
    addr('LD DE,compact attributes',0x11,0x7000,10)
    emit('LD B,attribute flag low',[0x06,(FLAGS+48)&255],7)
    a.label('attribute_flag_block')
    emit('PUSH HL',[0xe5],11); emit('LD H,flag page',[0x26,FLAGS>>8],7)
    emit('LD L,B',[0x68],4); emit('LD C,(HL)',[0x4e],7); emit('POP HL',[0xe1],10)
    emit('INC B',[0x04],4); emit('LD A,C',[0x79],4); emit('OR A',[0xb7],4)
    jr('JR Z,attribute_empty_block',0x28,'attribute_empty_block',[7,12])
    a.label('attribute_flag_group')
    emit('SLA C',[0xcb,0x21],8)
    jr('JR NC,attribute_skip_group',0x30,'attribute_skip_group',[7,12])
    emit('LD A,(HL)',[0x7e],7); emit('INC L',[0x2c],4)
    emit('PUSH BC',[0xc5],11); emit('LD B,A',[0x47],4)
    addr('CALL attribute_group_apply',0xcd,'attribute_group_apply',17)
    emit('POP BC',[0xc1],10); addr('JP attribute_group_done',0xc3,'attribute_group_done',10)
    a.label('attribute_skip_group'); emit('INC L',[0x2c],4)
    advance(8,'attribute_skip_page')
    a.label('attribute_group_done')
    emit('LD A,L',[0x7d],4); emit('AND 7',[0xe6,7],7)
    jr('JR NZ,attribute_flag_group',0x20,'attribute_flag_group',[7,12])
    a.label('attribute_block_done')
    emit('LD A,B',[0x78],4); emit('CP attribute flag end',[0xfe,(FLAGS+60)&255],7)
    addr('JP NZ,attribute_flag_block',0xc2,'attribute_flag_block',10)
    addr('LD (attribute_masks),HL',0x22,'attribute_masks',16); emit('RET',[0xc9],10)
    a.label('attribute_empty_block')
    emit('LD A,L',[0x7d],4); emit('ADD A,8',[0xc6,8],7); emit('LD L,A',[0x6f],4)
    advance(64,'attribute_empty_page')
    addr('JP attribute_block_done',0xc3,'attribute_block_done',10)
    a.label('attribute_flag_end')
    if a.pc>END_LIMIT: raise ValueError('attribute controller overlaps AY')
    return a.resolve(),dict(a.labels),rows


def delta_tstates(masks,raw=False):
    """Exact new-minus-old attribute pass, excluding unchanged Huffman.

Old zero masks: 75 T (74 at a page end); nonzero: 240 + 47*bits +
Huffman. Old setup/exit 81. New empty flag block: 136 (135 at a
page end); nonempty: 666+215*groups+47*bits+Huffman, minus one when
its last group is empty at a page end. New setup/exit 98. Thus all
page-crossing and correction costs cancel in the difference below.
"""
    if len(masks)!=96: raise ValueError('96 attribute masks required')
    flags=sum(any(masks[i:i+8]) for i in range(0,96,8))
    groups=sum(bool(x) for x in masks)
    return 0 if raw else -5551+530*flags+50*groups
