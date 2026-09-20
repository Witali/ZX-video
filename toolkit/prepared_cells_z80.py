"""Experimental B2 prepared-cell consumer. Real Z80, no producer/scheduler yet.

Queue body: 72 MSB-first mask bytes, 18 byte lengths, 576 attributes,
then per-band pixels. Dense bands are row-major, sparse bands cell-major.
Both queue banks reserve FC00..FFFF; window reads cross 3/4 and wrap.
Bank 5 reads in place when contiguous; bank 7 uses a 128-byte staging area.
No full screen copy. Entry A=40/C0; exit pages bank 6, preserving front bit.
"""
from build_zxv_trd import MiniAssembler
from build_long_video_trd import build_player_dither_tables

CODE, STAGE, MASK, LENGTHS, TABLE, PAGE = 0x9000,0x7300,0xbf20,0xbf68,0x9e00,0x9780
RING_BEGIN,RING_END,RING_BANK_BYTES=0xc000,0xfc00,15360


def build(*,unrolled_staging=False):
    a=MiniAssembler(CODE); listing=[]
    def emit(name,data,t,stage='control'):
        listing.append(dict(address=a.pc,instruction=name,tstates=t,stage=stage)); a.emit(*data)
    def ref(name,opcode,value,t,stage='control'):
        listing.append(dict(address=a.pc,instruction=name,tstates=t,stage=stage))
        if isinstance(value,str): a.abs16(opcode,value)
        else: a.emit(*(opcode if isinstance(opcode,tuple) else (opcode,))); a.word(value)
    def adjust(reg,n,stage='address'):
        emit('LD A,'+reg,[{'D':0x7a,'E':0x7b}[reg]],4,stage)
        emit('ADD/SUB immediate',[0xc6 if n>=0 else 0xd6,abs(n)],7,stage)
        emit('LD '+reg+',A',[{'D':0x57,'E':0x5f}[reg]],4,stage)
    def pixel(reverse=False,advance=False,stage='pixels'):
        emit('LD C,(HL)',[0x4e],7,stage); emit('INC HL',[0x23],6,stage)
        emit('LD A,(BC)',[0x0a],7,stage); emit('LD (DE),A',[0x12],7,stage)
        emit('DEC/INC B',[0x05 if reverse else 0x04],4,stage)
        emit('DEC/INC D',[0x15 if reverse else 0x14],4,stage)
        emit('LD A,(BC)',[0x0a],7,stage); emit('LD (DE),A',[0x12],7,stage)
        if advance: emit('INC E',[0x1c],4,stage)
    def copy_chunks():
        # Positive multiple of 16 only. LDI leaves A unchanged.
        a.label('copy_chunks')
        for _ in range(16): emit('LDI',[0xed,0xa0],16,'attribute_copy')
        emit('LD A,B',[0x78],4,'attribute_copy'); emit('OR C',[0xb1],4,'attribute_copy')
        ref('JP NZ,copy_chunks',0xc2,'copy_chunks',10,'attribute_copy')
        emit('RET',[0xc9],10,'attribute_copy')
    def stage_copy():
        if unrolled_staging: ref('CALL copy_window',0xcd,'copy_window',17,'staging')
        else: emit('LDIR',[0xed,0xb0],[16,21],'staging')

    a.label('draw'); ref('LD (screen_base),A',0x32,'screen_base',13)
    emit('LD C,90',[0x0e,90],7); ref('CALL window',0xcd,'window',17)
    ref('LD DE,mask',0x11,MASK,10); ref('LD BC,90',0x01,90,10)
    emit('LDIR',[0xed,0xb0],[16,21],'mask_copy')
    ref('LD A,(screen_base)',0x3a,'screen_base',13)
    emit('OR 18h',[0xf6,0x18],7); emit('LD D,A',[0x57],4); emit('LD E,96',[0x1e,96],7)
    emit('LD A,6',[0x3e,6],7); ref('LD (chunks_left),A',0x32,'chunks_left',13)
    a.label('attributes')
    emit('PUSH DE',[0xd5],11); emit('LD C,96',[0x0e,96],7)
    ref('CALL window',0xcd,'window',17); emit('POP DE',[0xd1],10)
    ref('LD BC,96',0x01,96,10); ref('CALL copy_chunks',0xcd,'copy_chunks',17)
    ref('LD A,(chunks_left)',0x3a,'chunks_left',13); emit('DEC A',[0x3d],4)
    ref('LD (chunks_left),A',0x32,'chunks_left',13); ref('JP NZ,attributes',0xc2,'attributes',10)
    emit('EXX',[0xd9],4); ref('LD HL,mask',0x21,MASK,10); emit('EXX',[0xd9],4)
    ref('LD HL,lengths',0x21,LENGTHS,10); ref('LD (length_pointer),HL',0x22,'length_pointer',16)
    ref('LD A,(screen_base)',0x3a,'screen_base',13); emit('LD D,A',[0x57],4)
    emit('LD E,96',[0x1e,96],7); emit('LD A,18',[0x3e,18],7)
    ref('LD (bands_left),A',0x32,'bands_left',13)
    a.label('band')
    ref('LD HL,(length_pointer)',0x2a,'length_pointer',16)
    emit('LD C,(HL)',[0x4e],7); emit('INC HL',[0x23],6)
    ref('LD (length_pointer),HL',0x22,'length_pointer',16)
    emit('LD A,C',[0x79],4); emit('OR A',[0xb7],4)
    ref('JP Z,empty_band',0xca,'empty_band',10)
    emit('PUSH DE',[0xd5],11); ref('CALL window',0xcd,'window',17); emit('POP DE',[0xd1],10)
    emit('LD B,table',[0x06,TABLE>>8],7)
    emit('EXX',[0xd9],4)
    for i in range(4):
        emit('LD A,(HL)' if not i else 'AND (HL)',[0x7e if not i else 0xa6],7)
        emit('INC HL',[0x23],6)
    emit('CP 255',[0xfe,255],7); emit('EXX',[0xd9],4)
    ref('JP Z,dense',0xca,'dense',10)
    emit('EXX',[0xd9],4)
    for _ in range(4): emit('DEC HL',[0x2b],6)
    emit('LD C,4',[0x0e,4],7); emit('EXX',[0xd9],4)
    a.label('mask_byte')
    emit('EXX',[0xd9],4); emit('LD A,(HL)',[0x7e],7); emit('INC HL',[0x23],6); emit('EXX',[0xd9],4)
    emit('OR A',[0xb7],4); ref('JP Z,empty_mask',0xca,'empty_mask',10)
    for _ in range(8):
        emit('ADD A,A',[0x87],4); ref('CALL C,cell',0xdc,'cell',[10,17]); emit('INC E',[0x1c],4)
    a.label('mask_done')
    emit('EXX',[0xd9],4); emit('DEC C',[0x0d],4); emit('EXX',[0xd9],4)
    ref('JP NZ,mask_byte',0xc2,'mask_byte',10); ref('JP band_done',0xc3,'band_done',10)
    a.label('dense')
    emit('LD A,4',[0x3e,4],7); ref('LD (dense_rows),A',0x32,'dense_rows',13)
    a.label('dense_row')
    for col in range(32): pixel(bool(col&1),True,'dense_pixels')
    ref('LD A,(dense_rows)',0x3a,'dense_rows',13); emit('DEC A',[0x3d],4)
    ref('LD (dense_rows),A',0x32,'dense_rows',13); ref('JP Z,dense_done',0xca,'dense_done',10)
    adjust('E',-32); emit('INC D',[0x14],4); emit('INC D',[0x14],4)
    ref('JP dense_row',0xc3,'dense_row',10)
    a.label('dense_done'); adjust('D',-6)
    a.label('band_done')
    emit('LD A,E',[0x7b],4); emit('OR A',[0xb7],4)
    ref('JP NZ,band_page_ready',0xc2,'band_page_ready',10); adjust('D',8)
    a.label('band_page_ready')
    ref('LD A,(bands_left)',0x3a,'bands_left',13); emit('DEC A',[0x3d],4)
    ref('LD (bands_left),A',0x32,'bands_left',13); ref('JP NZ,band',0xc2,'band',10)
    emit('LD A,16h',[0x3e,0x16],7); ref('CALL atomic_page',0xcd,PAGE,17,'paging')
    emit('RET',[0xc9],10)
    a.label('empty_band')
    emit('EXX',[0xd9],4)
    for _ in range(4): emit('INC HL',[0x23],6)
    emit('EXX',[0xd9],4); adjust('E',32); ref('JP band_done',0xc3,'band_done',10)
    a.label('empty_mask'); adjust('E',8); ref('JP mask_done',0xc3,'mask_done',10)
    a.label('cell')
    emit("EX AF,AF'",[0x08],4)
    for row in range(4):
        pixel(bool(row&1))
        if row!=3: emit('INC D',[0x14],4); emit('INC D',[0x14],4)
    adjust('D',-6); emit("EX AF,AF'",[0x08],4); emit('RET',[0xc9],10)
    copy_chunks()
    a.label('draw_end')

    # A direct bank-5 window avoids staging. Splits and bank 7 use STAGE.
    # Request C=1..128, alternate register set untouched. Cursor is advanced
    # before use; a future producer must retain the whole record until draw ends.
    a.label('window')
    emit('LD A,C',[0x79],4,'window'); ref('LD (request),A',0x32,'request',13,'window')
    ref('CALL normalize',0xcd,'normalize',17,'window')
    ref('CALL source_page',0xcd,'source_page',17,'window')
    ref('LD HL,(read_pointer)',0x2a,'read_pointer',16,'window')
    emit('PUSH HL',[0xe5],11,'window')
    ref('LD A,(request)',0x3a,'request',13,'window'); emit('LD C,A',[0x4f],4,'window'); emit('LD B,0',[0x06,0],7,'window')
    emit('ADD HL,BC',[0x09],11,'window'); emit('LD A,H',[0x7c],4,'window'); emit('CP FCh',[0xfe,0xfc],7,'window')
    ref('JP C,contiguous',0xda,'contiguous',10,'window')
    emit('LD A,L',[0x7d],4,'window'); emit('OR A',[0xb7],4,'window')
    ref('JP NZ,split',0xc2,'split',10,'window')
    a.label('contiguous')
    ref('LD (read_pointer),HL',0x22,'read_pointer',16,'window'); emit('POP HL',[0xe1],10,'window')
    ref('LD A,(screen_base)',0x3a,'screen_base',13,'window'); emit('CP 40h',[0xfe,0x40],7,'window')
    emit('RET Z',[0xc8],[5,11],'window')
    ref('LD DE,stage',0x11,STAGE,10,'window'); stage_copy()
    ref('JP staged',0xc3,'staged',10,'window')
    a.label('split')
    # First length = 256 - old low byte, less than the requested <=128.
    emit('POP HL',[0xe1],10,'window'); emit('XOR A',[0xaf],4,'window'); emit('SUB L',[0x95],4,'window')
    emit('LD C,A',[0x4f],4,'window'); ref('LD (first_length),A',0x32,'first_length',13,'window')
    ref('LD DE,stage',0x11,STAGE,10,'window'); stage_copy()
    ref('LD (read_pointer),HL',0x22,'read_pointer',16,'window'); emit('PUSH DE',[0xd5],11,'window')
    ref('CALL normalize',0xcd,'normalize',17,'window'); ref('CALL source_page',0xcd,'source_page',17,'window')
    emit('POP DE',[0xd1],10,'window'); ref('LD HL,(read_pointer)',0x2a,'read_pointer',16,'window')
    ref('LD A,(first_length)',0x3a,'first_length',13,'window'); emit('LD C,A',[0x4f],4,'window')
    ref('LD A,(request)',0x3a,'request',13,'window'); emit('SUB C',[0x91],4,'window')
    emit('LD C,A',[0x4f],4,'window'); emit('LD B,0',[0x06,0],7,'window')
    stage_copy(); ref('LD (read_pointer),HL',0x22,'read_pointer',16,'window')
    a.label('staged')
    ref('LD A,(screen_base)',0x3a,'screen_base',13,'window'); emit('CP C0h',[0xfe,0xc0],7,'window')
    ref('JP NZ,window_ready',0xc2,'window_ready',10,'window')
    emit('LD A,17h',[0x3e,0x17],7,'window'); ref('CALL atomic_page',0xcd,PAGE,17,'paging')
    a.label('window_ready'); ref('LD HL,stage',0x21,STAGE,10,'window'); emit('RET',[0xc9],10,'window')
    a.label('source_page')
    ref('LD A,(read_bank)',0x3a,'read_bank',13,'window'); emit('OR 10h',[0xf6,0x10],7,'window')
    ref('JP atomic_page',0xc3,PAGE,10,'paging')
    a.label('normalize')
    ref('LD HL,(read_pointer)',0x2a,'read_pointer',16,'window'); emit('LD A,H',[0x7c],4,'window')
    emit('CP FCh',[0xfe,0xfc],7,'window'); emit('RET NZ',[0xc0],[5,11],'window')
    ref('LD HL,C000',0x21,RING_BEGIN,10,'window'); ref('LD (read_pointer),HL',0x22,'read_pointer',16,'window')
    ref('LD A,(read_bank)',0x3a,'read_bank',13,'window'); emit('XOR 7',[0xee,7],7,'window')
    ref('LD (read_bank),A',0x32,'read_bank',13,'window'); emit('RET',[0xc9],10,'window')
    if unrolled_staging:
        a.label('copy_window')
        emit('LD A,C',[0x79],4,'staging'); emit('NEG',[0xed,0x44],8,'staging')
        emit('AND 31',[0xe6,31],7,'staging'); emit('ADD A,A',[0x87],4,'staging')
        ref('LD (copy_operand),A',0x32,'copy_operand',13,'staging')
        a.label('copy_jump'); emit('JR copy tail',[0x18,0],12,'staging')
        a.labels['copy_operand']=a.labels['copy_jump']+1
        a.label('copy_32')
        for _ in range(32): emit('LDI',[0xed,0xa0],16,'staging')
        emit('LD A,B',[0x78],4,'staging'); emit('OR C',[0xb1],4,'staging')
        ref('JP NZ,copy_32',0xc2,'copy_32',10,'staging'); emit('RET',[0xc9],10,'staging')
    a.label('state')
    for name in ('screen_base','chunks_left','bands_left','dense_rows','request','first_length','read_bank'):
        a.label(name); a.emit(0)
    for name in ('length_pointer','read_pointer'): a.label(name); a.word(0)
    a.label('end')
    if a.pc>0x9400: raise ValueError(f'prepared consumer overlaps AY: {a.pc:04x}')
    top,bottom=build_player_dither_tables()
    return a.resolve(),a.labels,listing,[(TABLE,top+bottom)]


def body(state,mask):
    """PC fixture only: a real RAM producer is still required."""
    if len(state)!=3840 or len(mask)!=80:
        raise ValueError('B2 requires a compact state and an 80-byte source map')
    # Existing FAP3 can mark the outer bands. Both the current cropped output
    # and B2 deliberately omit them; write guards verify the black borders.
    mask=mask[4:76]; lengths=[]; data=bytearray()
    for band in range(18):
        flags=mask[band*4:band*4+4]; lengths.append(4*sum(v.bit_count() for v in flags))
        first=(12+band*4)*32
        if flags==b'\xff'*4:
            data+=state[first:first+128]
        else:
            for col in range(32):
                if flags[col//8] & (128>>(col%8)):
                    for row in range(4): data.append(state[first+row*32+col])
    return mask+bytes(lengths)+state[3168:3744]+data
