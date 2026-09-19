"""FAP2/FAP3 Z80 parser: read a whole packet, consume values in place."""
from build_zxv_trd import MiniAssembler
from frame_output_pipeline import INPUT,INPUT_END,VECTORS,MAP
from frame_stream_z80 import CODE,BRIDGE,HEADER
from causal_tile_z80 import CACHE_MAP
import frame_stream_z80

LENGTH = 0xba58


def build(zx0,reader,wrapper,draw,metadata,audio, *, stored_guards=True):
    _, bridge, oldlabels, oldlisting = frame_stream_z80.build(zx0,reader,wrapper,draw,metadata,audio)
    listing = [row for row in oldlisting if BRIDGE <= row['address'] < oldlabels['bridge_end']]
    a = MiniAssembler(CODE)
    def emit(name,data,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='packet')); a.emit(*data)
    def addr(name,opcode,value,ticks):
        listing.append(dict(address=a.pc,instruction=name,tstates=ticks,stage='packet'))
        if isinstance(value,str): a.abs16(opcode,value)
        else:
            a.emit(*(opcode if isinstance(opcode,tuple) else (opcode,))); a.word(value)
    def copy(count,destination):
        addr('LD DE,copy destination',0x11,destination,10)
        addr('LD BC,copy size',0x01,count,10)
        if count == 192:
            emit('LD A,12',[0x3e,12],7); a.label('copy_vectors')
            for _ in range(16): emit('LDI',[0xed,0xa0],16)
            emit('DEC A',[0x3d],4); addr('JP NZ,copy_vectors',0xc2,'copy_vectors',10)
        else:
            for _ in range(count): emit('LDI',[0xed,0xa0],16)
    def point(count,name):
        addr('LD ('+name+'),HL',0x22,wrapper[name],16)
        addr('LD DE,field length',0x11,count,10); emit('ADD HL,DE',[0x19],11)
    a.label('next_frame')
    minimum = 294+2*stored_guards
    maximum = INPUT_END-INPUT-int(not stored_guards)
    addr('LD DE,length',0x11,LENGTH,10); addr('LD BC,2',0x01,2,10)
    addr('CALL take length',0xcd,reader['take'],17)
    addr('LD HL,(length)',0x2a,LENGTH,16); addr('LD DE,minimum length',0x11,minimum,10)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15); addr('JP C,fatal',0xda,zx0['fatal'],10)
    addr('LD DE,valid length range',0x11,maximum-minimum+1,10)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15); addr('JP NC,fatal',0xd2,zx0['fatal'],10)
    addr('LD DE,packet',0x11,INPUT,10); addr('LD BC,(length)',(0xed,0x4b),LENGTH,20)
    addr('CALL take packet',0xcd,reader['take'],17)
    addr('LD (payload_end),DE',(0xed,0x53),'payload_end',20)
    addr('LD HL,AY records',0x21,INPUT,10); addr('CALL enqueue_six',0xcd,audio['audio_enqueue_six'],17)
    copy(5,HEADER)
    emit('PUSH HL',[0xe5],11)
    addr('LD A,(flags)',0x3a,HEADER,13); emit('AND 38h',[0xe6,0x38],7)
    addr('JP NZ,fatal',0xc2,zx0['fatal'],10)
    addr('LD A,(flags)',0x3a,HEADER,13); emit('AND 80h',[0xe6,128],7)
    addr('LD (cache_flag),A',0x32,wrapper['cache_flag'],13)
    addr('LD A,(flags)',0x3a,HEADER,13); emit('AND 40h',[0xe6,64],7)
    addr('LD (raw_attribute_flag),A',0x32,wrapper['raw_attribute_flag'],13)
    addr('LD HL,(mask_length)',0x2a,HEADER+1,16); addr('LD DE,8',0x11,8,10)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15); addr('JP C,fatal',0xda,zx0['fatal'],10)
    addr('LD DE,541',0x11,541,10)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15); addr('JP NC,fatal',0xd2,zx0['fatal'],10)
    emit('POP HL',[0xe1],10); emit('PUSH HL',[0xe5],11)
    addr('LD DE,cache+vectors+map+guards',0x11,275+2*stored_guards,10); emit('ADD HL,DE',[0x19],11)
    addr('LD DE,(mask_length)',(0xed,0x5b),HEADER+1,20); emit('ADD HL,DE',[0x19],11)
    addr('LD DE,(coded_length)',(0xed,0x5b),HEADER+3,20); emit('ADD HL,DE',[0x19],11)
    addr('JP C,fatal',0xda,zx0['fatal'],10)
    addr('LD DE,(payload_end)',(0xed,0x5b),'payload_end',20)
    emit('OR A',[0xb7],4); emit('SBC HL,DE',[0xed,0x52],15)
    addr('JP Z,length_valid',0xca,'length_valid',10); addr('JP NC,fatal',0xd2,zx0['fatal'],10)
    a.label('length_valid'); emit('POP HL',[0xe1],10)
    copy(3,CACHE_MAP)
    if 'vector_pointer' in wrapper: point(192,'vector_pointer')
    else: copy(192,VECTORS)
    addr('CALL expand_masks',0xcd,metadata['decode'],17)
    if 'native_pointer' in wrapper: point(80,'native_pointer')
    else: copy(80,MAP)
    addr('LD (coded_pointer),HL',0x22,wrapper['coded_pointer'],16)
    addr('LD DE,(coded_length)',(0xed,0x5b),HEADER+3,20); emit('ADD HL,DE',[0x19],11)
    if stored_guards:
        emit('LD A,(HL)',[0x7e],7); emit('OR A',[0xb7],4); addr('JP NZ,fatal',0xc2,zx0['fatal'],10)
        emit('INC HL',[0x23],6)
    addr('LD (literal_pointer),HL',0x22,wrapper['literal_pointer'],16)
    emit('EX DE,HL',[0xeb],4); addr('LD HL,(payload_end)',0x2a,'payload_end',16)
    if stored_guards:
        emit('DEC HL',[0x2b],6); emit('LD A,(HL)',[0x7e],7); emit('OR A',[0xb7],4)
        addr('JP NZ,fatal',0xc2,zx0['fatal'],10)
    else:
        emit('LD (HL),0',[0x36,0],10); emit('OR A',[0xb7],4)
    emit('SBC HL,DE',[0xed,0x52],15)
    addr('LD (literal_length),HL',0x22,HEADER+5,16)
    addr('CALL prepare_bridge',0xcd,oldlabels['prepare_bridge'],17); emit('RET',[0xc9],10)
    a.label('state'); a.label('payload_end'); a.word(0); a.label('end')
    if a.pc > 0xde00: raise ValueError('bulk parser overlaps frame clock')
    labels = dict(a.labels,prepare_bridge=oldlabels['prepare_bridge'],publish_bridge=oldlabels['publish_bridge'],
        bridge_end=oldlabels['bridge_end'])
    return a.resolve(),bridge,labels,listing
