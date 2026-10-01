"""Two exact AYH1 segments in banks 4 and 6, sharing the existing AY FIFO/IRQ."""
import struct

import ay_huffman_stream as wire
from build_fap3_trd import sha
from build_zxv_trd import MiniAssembler
from pipelined_frame_z80 import helpers
import resident_audio_z80 as resident


def encode(records,initial,*,split=None):
    split=len(records)//2 if split is None else split
    if not 0<split<len(records)<=65535:raise ValueError('invalid resident audio segment boundary')
    previous=bytearray(initial)
    for record in records[:split]:
        for reg,value in zip(record[1::2],record[2::2]):previous[reg]=value
    first,_=wire.encode(records[:split],initial)
    second,_=wire.encode(records[split:],bytes(previous))
    result=b'AYB1'+struct.pack('<II',len(first),len(second))+first+second
    assert decode(result)==(initial,records)
    return result


def segments(data):
    if data[:4]!=b'AYB1' or len(data)<12:raise ValueError('expected AYB1')
    one,two=struct.unpack_from('<II',data,4)
    if not one or not two or len(data)!=12+one+two:raise ValueError('invalid AYB1 extents')
    return data[12:12+one],data[12+one:]


def decode(data):
    first,second=segments(data)
    initial,left=wire.decode(first);middle,right=wire.decode(second)
    expected=bytearray(initial)
    for record in left:
        for reg,value in zip(record[1::2],record[2::2]):expected[reg]=value
    if bytes(expected)!=middle:raise ValueError('audio segment initial state is discontinuous')
    if not left or not right or len(left)+len(right)>65535:raise ValueError('invalid audio segment tick counts')
    return initial,left+right


def build(data,audio,*,batch=31):
    _,records=decode(data)
    compiled=[]
    for bank,payload in zip((4,6),segments(data)):
        part=resident.build(payload,audio,batch=batch,total_ticks=len(records),preinitialized=True)
        part['bank']=bank;compiled.append(part)
    assert compiled[0]['labels']==compiled[1]['labels']
    return dict(compiled[0],ticks=len(records),wire='AYB1',segments=compiled,
        segment_ticks=[c['ticks'] for c in compiled],banks=[4,6],ayb1_sha256=sha(data),
        all_segment_bytes=sum(c['image_bytes'] for c in compiled),
        initial_delta_tstates=10,decoder_per_tick_delta_tstates=0)


def hooks(origin,compiled,*,page):
    """Fixed-RAM tails: init once; switch before a refill when bank 4 is empty."""
    a=MiniAssembler(origin);rows=[];e,n=helpers(a,rows,'banked_audio')
    target=compiled['labels']
    a.label('init')
    e('LD A,bank 4',[0x3e,0x14],7);n('LD (active_bank),A',0x32,'active_bank',13)
    n('JP resident init',0xc3,target['init'],10)
    a.label('fill')
    n('LD HL,(segment remaining)',0x2a,target['remaining'],16)
    e('LD A,H',[0x7c],4);e('OR L',[0xb5],4)
    n('JP NZ,produce',0xc2,'produce',10)
    n('LD A,(active_bank)',0x3a,'active_bank',13);e('CP bank 4',[0xfe,0x14],7)
    n('JP NZ,produce',0xc2,'produce',10)
    e('LD A,bank 6',[0x3e,0x16],7);n('LD (active_bank),A',0x32,'active_bank',13)
    n('CALL page bank 6',0xcd,page,17)
    a.label('produce');n('JP resident fill',0xc3,target['fill'],10)
    a.label('active_bank');a.emit(0x14);a.label('end')
    if not 0x4000<=origin<a.pc<=0xc000:raise ValueError('audio segment hooks require fixed RAM')
    return dict(origin=origin,code_hex=a.resolve().hex(),labels=dict(a.labels),listing=rows,
        code_bytes=a.pc-origin,state_bytes=1,normal_tstates=44,switch_tstates=203,eof_tstates=74,
        normal_bridge_delta_tstates=50,switch_bridge_delta_tstates=209,eof_bridge_delta_tstates=80,
        init_bridge_delta_tstates=30,
        scope='Switch includes one 92-T paging call; excludes IRQ restarts, contention and resident fill body')
