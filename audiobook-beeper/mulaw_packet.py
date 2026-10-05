"""Compact G.711 bytes -> sixteen-pulse table packets, assembled separately."""
import ast
from functools import lru_cache
import hashlib
import struct
import subprocess
import sys
from pathlib import Path
import numpy as np
from g711_codec import decode_table
from mulaw_player import screen
from pcm_player import TrdFile,basic_line,calculate_file_start,place_files

HERE=Path(__file__).resolve().parent
CPU=3546900
HOLDS=[41,23,23,23,22,26,26,30,26,26,27,27,24,26,27,26]
MODEL=dict(family='mulaw_packet',holds=HOLDS,beta=.5,extent=.5,q_clip=[4,11])


def tables(model=MODEL):
    # Full G.711 decoded levels enter the weighted recurrence. There is no
    # linear PCM7/PCM8 intermediate. Only packet feedback is quantized.
    levels=decode_table('mulaw').astype(np.int64)+32768
    x=levels[:,None]/65536
    q=np.broadcast_to((np.arange(32)//2-8)/8,(256,32)).copy()
    recent=np.broadcast_to((np.arange(32)%2-.5)*model['extent'],(256,32)).copy()
    words=np.zeros((256,32),dtype=np.uint16)
    for weight in np.asarray(model['holds'])/np.mean(model['holds']):
        u=x+q/weight+model['beta']*recent
        bit=u>=.5-1e-12
        recent=u-bit;q+=weight*(x-bit);words=(words<<1)|bit
    qcode=np.clip(np.floor(q*8+8.5+1e-12),*model['q_clip'])
    r=np.clip(np.floor(recent/model['extent']+1+1e-12),0,1)
    return words,(qcode*2+r).astype('u1')


def layout(model=MODEL):
    words,nxt=tables(model)
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    states=sorted(reachable)
    assert len(states)<=16,'four-byte records must fit one64-byte row'
    unique,ids=np.unique(np.c_[words[:,states],nxt[:,states]],axis=0,return_inverse=True)
    assert len(unique)<=240,'packet rows exceed fixed bank5 excluding TR-DOS'
    first={p:0x8400+i*64 for i,p in enumerate(sorted(set(map(int,(words[:,states]>>8).ravel()))))}
    end=0x8400+len(first)*64
    second={p:end+i*44 for i,p in enumerate(sorted(set(map(int,(words[:,states]&255).ravel()))))}
    pointers=(end+len(second)*44+255)&~255
    reserve=pointers+512-0x8000
    assert reserve<=16384,'packet code exceeds fixed bank2'
    pages=[0x4000+i*256 for i in range(64) if not 28<=i<32]
    row_addresses=[pages[i//4]+(i%4)*64 for i in range(len(unique))]
    used_pages=(len(unique)+3)//4
    reset=next(s for s in states if int(nxt[255,s])==16)
    regions=[(b,0xc000,16384) for b in (0,4,6,1,3)]+[(7,0xdb00,9472)]
    if reserve<16384:regions.append((2,0xc000+reserve,16384-reserve))
    # Reclaim whole unused table pages at the top of bank5 for audio.
    if used_pages<60:
        start=pages[used_pages];assert start>=0x6000
        regions.append((5,start+0x8000,0x8000-start))
    return words,nxt,states,first,second,pointers,reserve,ids,row_addresses,reset,regions


def intervals(meta):
    result=np.tile(HOLDS,meta['pcm_samples']).astype(np.int64)
    end=0
    for section in meta['sections']:
        for n in range(256,section['bytes']+1,256):
            result[(end+n-2)*16]+=112 if n==section['bytes'] else 41
        end+=section['bytes']
    k=(meta['pcm_samples']-2)*16
    result[k]+=7 # Reset only the last silent packet's input feedback.
    pairs=meta['loop_idle_pairs']
    if pairs:
        idle=[]
        for j in range(pairs):idle.extend([26,33 if (j+1)%255==0 and j+1<pairs else 26])
        idle[-1]=66+meta['loop_idle_pad_tstates']
        result=np.r_[result[:k],127,idle,result[k+1:]]
    return result


def reference(payload,model=MODEL,cycles=2,idle_pairs=0):
    words,nxt,states,_,_,_,_,_,_,reset,_=layout(model)
    q=16;output=[];after=[]
    for cycle in range(cycles):
        for i,code in enumerate(payload):
            if i==len(payload)-1:q=reset
            word=int(words[code,q]);q=int(nxt[code,q]);after.append(q)
            bits=[(word>>shift)&1 for shift in range(15,-1,-1)]
            if i==len(payload)-2 and idle_pairs:bits[1:1]=[1,0]*idle_pairs
            output.extend(bits)
    output.append(int(words[payload[0],q])>>15)
    after.append(int(nxt[payload[0],q]))
    return np.asarray(output,dtype='u1'),np.asarray(after,dtype='u1')


def build_disk(payload,work,model=MODEL,idle_pairs=0,idle_pad=0):
    work=Path(work).resolve();work.mkdir(parents=True,exist_ok=True)
    words,nxt,states,first,second,pointers,reserve,ids,rows,reset,regions=layout(model)
    capacity=sum(s for _,_,s in regions)
    if not 8192<=len(payload)<=capacity or len(payload)%256 or payload[-1]!=255:
        raise ValueError('packet mu-law requires aligned8192..capacity bytes and a final zero code255')
    assert 0<=idle_pairs<=1530 and (idle_pairs or idle_pad==0)
    memory=bytearray(65536)
    for code in range(256):
        row=rows[int(ids[code])]
        memory[pointers+code]=row&255;memory[pointers+256+code]=row>>8
        for sid,state in enumerate(states):
            word=int(words[code,state]);first_pointer=first[word>>8]|(states.index(int(nxt[code,state]))*4)
            memory[row+sid*4:row+sid*4+4]=struct.pack('<HH',second[word&255],first_pointer)
    sections=[];left=len(payload)
    for bank,address,size in regions:
        count=min(left,size)
        if count:sections.append(dict(bank=bank,address=0x10000-count,bytes=count,sectors=count//256))
        left-=count
    assert left==0
    basic=b''.join([basic_line(10,b'\xfd \xb0 "32767"'),
        basic_line(20,b'\xf9 \xc0 \xb0 "15619":\xea:\xef "PLAYER" \xaf'),
        basic_line(30,b'\xf9 \xc0 \xb0 "32768"')])
    boot=TrdFile('boot','B',basic,autostart_line=10)
    track,sector=calculate_file_start([boot,TrdFile('PLAYER','C',bytes(23296),start=0x8000)])
    lower=track*16+sector;upper=lower+28;pos=upper+32
    for s in sections:s['sector']=pos;pos+=s['sectors']
    reads=60+sum(s['sectors'] for s in sections)
    steps=np.diff(np.r_[0,(np.arange(1,33)*reads+31)//32])
    constants=dict(first_address=sections[0]['address'],progress_first=int(steps[0]),
        packet_map=pointers,initial_feedback_offset=states.index(16)*4,
        guard_feedback_offset=states.index(reset)*4,first_resume_offset=9,
        loop_idle_pairs=idle_pairs,resident_reserve=reserve)
    loads=next((b for b in range(4) if idle_pad>=7*b and (idle_pad-7*b)%4==0),None)
    assert loads is not None
    constants.update(idle_pad_loads=loads,idle_pad_nops=(idle_pad-7*loads)//4)
    for i in range(6):constants[f'idle_count_{i}']=min(255,max(0,idle_pairs-255*i))
    for i in range(256):constants.update({f'first_address_{i}':first.get(i,-1),f'second_address_{i}':second.get(i,-1)})
    (work/'config.inc').write_text(''.join(f'{k}: EQU {v}\n' for k,v in constants.items()))
    table_loads=''
    for sector,address,count in ((lower,0x4000,28),(upper,0x6000,32)):
        table_loads+=f'        LD DE,{sector//16*256+sector%16}\n        LD HL,{address}\n        LD B,{count}\n        CALL read_n\n'
    (work/'loads.inc').write_text(table_loads+''.join(f'        LOAD_AUDIO {s["bank"]},{s["sector"]//16*256+s["sector"]%16},{s["address"]},{s["sectors"]}\n' for s in sections))
    tails=[]
    for i in range(len(sections)):
        j=(i+1)%len(sections);s=sections[j]
        tails.append(f'        BANK_TAIL {i},{s["bank"]},{s["address"]},{j},{int(i==len(sections)-1)}\n')
    (work/'tails.inc').write_text(''.join(tails))
    for name,data in [('map',memory[pointers:pointers+512]),('bank5-lower',memory[0x4000:0x5c00]),
        ('bank5-upper',memory[0x6000:0x8000]),('progress-steps',bytes(steps[1:].astype('u1'))+b'\xff'),
        ('screen',screen(len(payload)))]:
        (work/(name+'.bin')).write_bytes(data)
    # Reuse the established commented loader verbatim as assembler includes.
    # No instructions are emitted as Python byte constants.
    template=(HERE/'mulaw-player.asm').read_text()
    startup=template[template.index('LOAD_AUDIO: MACRO'):template.index('ready:')]
    loader=template[template.index('read_n:'):template.index('        ASSERT $ <= 0x8500')]
    (work/'startup.inc').write_text(startup)
    (work/'loader.inc').write_text(loader)
    (work/'first.inc').write_text(''.join(f'        FIRST {p}\n' for p in first))
    (work/'second.inc').write_text(''.join(f'        SECOND {p}\n' for p in second))
    (work/'player.asm').write_bytes((HERE/'mulaw-packet-player.asm').read_bytes())
    run=subprocess.run([sys.executable,'-m','pyz80.pyz80','--obj=player.bin','--lstfile=player.lst','-s','.*','player.asm'],
        cwd=work,capture_output=True,text=True)
    (work/'assembler.log').write_text(run.stdout+run.stderr)
    if run.returncode:raise RuntimeError(run.stdout+run.stderr)
    labels=next(ast.literal_eval(s) for s in run.stdout.splitlines() if s.startswith('{'))
    blob=(work/'player.bin').read_bytes();assert len(blob)==23296
    files=[boot,TrdFile('PLAYER','C',blob,start=0x8000),
        TrdFile('LOWER','C',bytes(memory[0x4000:0x5c00]),start=0x4000),
        TrdFile('UPPER','C',bytes(memory[0x6000:0x8000]),start=0x6000)]
    offset=0
    for i,s in enumerate(sections):
        files.append(TrdFile(f'ULAW{i}','C',payload[offset:offset+s['bytes']],start=s['address']));offset+=s['bytes']
    disk,directory,free=place_files(files,'ULAW128')
    meta=dict(codec='mulaw-packet',model=model,pcm_samples=len(payload),oversample=16,
        source_sample_rate_hz=8000,cpu_clock_hz=CPU,sections=sections,player_labels=labels,
        first_addresses=list(first.values()),second_addresses=list(second.values()),feedback_states=states,
        packet_rows=rows,code_rows=ids.tolist(),initial_feedback=16,guard_feedback=reset,
        loop_idle_pairs=idle_pairs,loop_idle_pad_tstates=idle_pad,
        outputs_per_cycle=len(payload)*16+idle_pairs*2,record_stop_addresses=[a+2 for a in first.values()],
        paging_base=24,repeat=True,ordinary_tstates=sum(HOLDS),ordinary_delta_vs_64khz=-9,
        page_extra_tstates=41,bank_extra_tstates=112,guard_reset_extra_tstates=7,
        table_regions=[dict(sector=lower,address=0x4000,sectors=28),dict(sector=upper,address=0x6000,sectors=32)],
        playback_preload_sector_reads=reads,loading_progress_steps=32,
        resident_reserve=reserve,unique_packet_rows=len(rows),directory=directory,capacity=free,
        memory=dict(total_ram_bytes=131072,audio_bytes=len(payload),maximum_audio_bytes=capacity,
            unused_audio_bytes=capacity-len(payload),bank2_resident_bytes=reserve,shadow_screen_bytes=6912,
            table_and_trdos_bytes=131072-capacity-reserve-6912,pcm_audio_buffer_bytes=0,pdm_audio_buffer_bytes=0),
        payload_sha256=hashlib.sha256(payload).hexdigest(),binary_sha256=hashlib.sha256(blob).hexdigest())
    meta['deterministic_cycle_tstates']=int(intervals(meta).sum())
    return disk,meta
