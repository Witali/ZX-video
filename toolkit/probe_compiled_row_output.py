"""Bounded compiled-row output feasibility, before changing player transport.

Generate COPY / constant-pattern FILL runs on the PC, execute real Z80
instructions for every bitmap, and compress the proposed packet payloads.
Attributes/audio are preserved in the old packet; this prototype does not
integrate boot, IRQ, queues or command copying into the player.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import numpy as np
from benchmark_compact_screen import NativeCPU, STACK, STOP
from build_fap3_trd import sha
from build_five_level_test_trd import save
from build_zxv_trd import spectrum_bitmap_offset
from probe_adaptive_block_codecs import ExternalCodec
from row_dictionary_video import reference_tables
from frame_output_pipeline import display_screen
from inplace_slot_input_z80 import MAX_OUTPUT
from inplace_zx0 import layout
import lzsa2_stream

COMMANDS, COMPACT, TABLE = 0x6400, 0xa800, 0x9e00


def routines():
    code = bytearray(); labels = {}; listing = {}
    def emit(blob, ticks, name):
        at = 0x9000+len(code); code.extend(blob)
        listing[at] = dict(tstates=ticks, instruction=name)
    for kind in ('copy','pattern','solid'):
        for i in range(32):
            labels[kind,32-i] = 0x9000+len(code)
            if kind == 'copy':
                emit([0x4e],7,'LD C,(HL)'); emit([0x0a],7,'LD A,(BC)')
            emit([0x12],7,'LD (DE),A')
            if kind == 'copy': emit([0x05 if i&1 else 0x04],4,'DEC/INC B')
            emit([0x15 if i&1 else 0x14],4,'DEC/INC D')
            if kind == 'copy': emit([0x0a],7,'LD A,(BC)')
            elif kind == 'pattern': emit([0x78 if i&1 else 0x79],4,'LD A,B/C')
            emit([0x12],7,'LD (DE),A'); emit([0x1c],4,'INC E')
            if kind == 'copy': emit([0x2c],4,'INC L')
        emit([0xc9],10,'RET')
    return bytes(code),labels,listing


def select_row(current, changed, tables):
    """One DP policy: native T plus 81 T per command byte (60 decode + 21 copy).

    60 approximates the *baseline* decoder's cost per output byte. It is a
    ranking heuristic, never a substitute for the new native codec profile.
    """
    positions = np.flatnonzero(changed).tolist(); n = len(positions)
    best = [0]*(n+1); choices = [None]*n
    for i in range(n-1,-1,-1):
        x = positions[i]; options = []
        for j in range(i,n):
            end = positions[j]+1; length = end-x
            options.append((54+51*length+81*11+best[j+1],j+1,'copy',x,length))
            if all(v == current[x] for v in current[x:end]):
                equal = tables[int(current[x])] == tables[256+int(current[x])]
                kind,setup,per,raw = ('solid',44,22,8) if equal else ('pattern',51,26,10)
                options.append((setup+per*length+81*raw+best[j+1],j+1,kind,x,length))
        choice = min(options); best[i] = choice[0]; choices[i] = choice
    result = []; i = 0
    while i<n:
        _,following,kind,x,length = choices[i];result.append((kind,x,length));i=following
    return result


def compile_frame(current, previous, index, tables, labels):
    code = bytearray(); listing = {}; counts = Counter(); cycles = 10
    def emit(blob,ticks,name):
        at=COMMANDS+len(code);code.extend(blob);listing[at]=dict(tstates=ticks,instruction=name)
    def word(op,value,ticks,name):emit(bytes([op])+value.to_bytes(2,'little'),ticks,name)
    for y in range(12,84):
        row=current[y*32:(y+1)*32];old=previous[y*32:(y+1)*32]
        for kind,x,length in select_row(row,row!=old,tables):
            phase=length&1
            destination=(0xc000 if index%2==0 else 0x4000)+spectrum_bitmap_offset(x,y*2)+256*phase
            if kind=='copy':word(0x21,COMPACT+y*32+x,10,'LD HL,source')
            word(0x11,destination,10,'LD DE,target')
            if kind=='copy':
                emit([0x06,(TABLE>>8)+phase],7,'LD B,table page');cycles+=54+51*length
            else:
                top,bottom=tables[int(row[x])],tables[256+int(row[x])]
                if kind=='solid':emit([0x3e,top],7,'LD A,fill');cycles+=44+22*length
                else:
                    word(0x01,256*top+bottom,10,'LD BC,pattern')
                    emit([0x79 if phase else 0x78],4,'LD A,C/B');cycles+=51+26*length
            word(0xcd,labels[kind,length],17,'CALL row run')
            counts[kind+'_runs']+=1;counts[kind+'_symbols']+=length
    emit([0xc9],10,'RET commands')
    if len(code)>0x1260:raise ValueError('compiled commands exceed reusable packet workspace')
    return bytes(code),listing,cycles,dict(counts)


def verify_all(states,tables,book,stub,labels,stub_listing):
    c=NativeCPU(b'',b'');c.guarding=False;c.port_7ffd=0x17
    def install(at,blob):
        for i,v in enumerate(blob):c.write8(at+i,v)
    install(0x9000,stub);install(TABLE,tables)
    screens={5:bytes(6144),7:bytes(6144)};rows=[];programs=[];hist=Counter()
    with reference_tables(book):
        for index,current in enumerate(states):
            previous=states[index-2] if index>=2 else np.zeros(3840,dtype=np.uint8)
            code,listing,expected,counts=compile_frame(current,previous,index,tables,labels)
            install(COMPACT,current);install(COMMANDS,code)
            c.pc=COMMANDS;c.sp=STACK;c.push(STOP);start=c.tstates;steps=0
            instructions=stub_listing|listing
            while c.pc!=STOP:
                pc=c.pc;before=c.tstates;c.step();steps+=1
                ticks=c.tstates-before
                if ticks!=instructions[pc]['tstates']:raise AssertionError(('instruction timing',pc,ticks))
                hist[instructions[pc]['instruction']]+=ticks
                if steps>100000:raise AssertionError('compiled output does not return')
            actual=c.tstates-start
            if actual!=expected:raise AssertionError(('run formula',index,actual,expected))
            target=7 if index%2==0 else 5
            screens[target]=display_screen(current.tobytes(),black_borders=True)[:6144]
            if any(bytes(c.banks[b][:6144])!=data for b,data in screens.items()):raise AssertionError(('bitmap',index))
            for at,data in ((COMPACT,current.tobytes()),(COMMANDS,code),(TABLE,tables),(0x9000,stub)):
                if bytes(c.read8(at+i) for i in range(len(data)))!=data:raise AssertionError(('input changed',index,at))
            if c.sp!=STACK or c.port_7ffd!=0x17:raise AssertionError('stack/paging differs')
            rows.append(dict(frame=index,tstates=actual,command_bytes=len(code),**counts));programs.append(code)
    return rows,programs,dict(hist)


def rewrite(video,programs):
    at=0;result=bytearray();largest=0
    for code in programs:
        n=struct.unpack_from('<H',video,at)[0];body=bytearray(video[at+2:at+2+n])
        flags,masks,coded=struct.unpack_from('<BHH',body)
        if flags&128:raise ValueError('prototype expects fragment-only input')
        map_at=200+masks
        oldmap=bytes(body[map_at:map_at+80]);body[map_at:map_at+80]=len(code).to_bytes(2,'little')+bytes(78)
        body.extend(code);largest=max(largest,len(body));result+=len(body).to_bytes(2,'little')+body
        restored=body[:-len(code)];restored[map_at:map_at+80]=oldmap
        if restored!=video[at+2:at+2+n]:raise AssertionError('non-output packet fields changed')
        at+=2+n
    if at!=len(video):raise ValueError('packet count differs')
    return bytes(result),largest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('states','metadata','video','lzsa','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    with np.load(a.states,allow_pickle=False) as f:states=f['states']
    m=json.loads(a.metadata.read_bytes());tables=bytes.fromhex(m['row_dictionary']['tables_hex'])
    if sha(states.tobytes())!=m['states_sha256']:raise ValueError('state identity differs')
    stub,labels,listing=routines();rows,programs,hist=verify_all(states,tables,m['row_dictionary'],stub,labels,listing)
    video=a.video.read_bytes();candidate,max_packet=rewrite(video,programs)
    (a.output/'cache').mkdir(exist_ok=True)
    codec=ExternalCodec('lzsa2',a.lzsa.resolve(),a.lzsa.resolve(),'pinned local LZSA2')
    stream=bytearray();blocks=[]
    for lo in range(0,len(candidate),MAX_OUTPUT):
        raw=candidate[lo:lo+MAX_OUTPUT];payload=codec.encode_verified(raw,None,a.output/'cache')
        decoded,proof=lzsa2_stream.trace(payload,limit=len(raw))
        space=layout(len(payload),len(raw),proof['minimum_input_start'],len(stream))
        if decoded!=raw or not space['sector_aligned_fits']:raise ValueError('block/overlap failure')
        blocks.append(dict(decoded_bytes=len(raw),compressed_bytes=len(payload),inplace=space))
        stream+=struct.pack('<HH',len(raw),len(payload))+payload
    (a.output/'video.raw').write_bytes(candidate);(a.output/'video.stream').write_bytes(stream)
    save(a.output/'probe.json',dict(complete=True,release=False,scope=__doc__,baseline_commit='42bcc0f',
        states_sha256=sha(states.tobytes()),baseline_video_sha256=sha(video),raw_sha256=sha(candidate),stream_sha256=sha(stream),
        bitmap_cpu_tstates=sum(r['tstates'] for r in rows),command_bytes=sum(map(len,programs)),
        command_copy_ldir_tstates=sum(21*len(code)-5 for code in programs),
        video_bytes=len(stream),video_sectors=(len(stream)+255)//256,decoded_bytes=len(candidate),max_packet_bytes=max_packet,
        packet_workspace_fits=max_packet<4704,all_bitmaps_exact=True,native_instruction_timings_exact=True,
        attributes_and_reconstruction_packet_bytes_unchanged=True,actual_playback_measured=False,
        rows=rows,blocks=blocks,instruction_tstates=hist,stub_bytes=len(stub),stub_hex=stub.hex()))
    print(json.dumps(dict(bitmap_cpu_tstates=sum(r['tstates'] for r in rows),command_bytes=sum(map(len,programs)),
        video_bytes=len(stream),decoded_bytes=len(candidate),max_packet_bytes=max_packet)),flush=True)


if __name__=='__main__':main()
