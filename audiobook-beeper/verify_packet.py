"""Continuous native and cold Spectrum 128 verification of packet playback."""
import argparse
from array import array
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess

import numpy as np

from ima_codec import decode, decoder_table
from packet_player import HOLDS, layout
from pdm_player import CPU_CLOCK
from smoke_test_fuse import hidden_startupinfo
from verify_pcm import extract_player, save


def rational_tables(holds=HOLDS,expected_tables=None,beta=.5,extent=1.):
    words=np.empty((64,32),dtype='<u2');successors=np.empty((64,32),dtype='u1')
    for value in range(64):
        for state in range(32):
            x=Fraction(2*value+1,128);q=Fraction(state//2-8,8)
            recent=Fraction(2*(state%2)-1,2)*Fraction(extent);word=0
            for hold in holds:
                weight=Fraction(hold*16,sum(holds))
                u=x+q/weight+recent*Fraction(beta);bit=int(u>=Fraction(1,2))
                recent=u-bit;q+=weight*(x-bit);word=word*2+bit
            code=max(0,min(15,(q*8+Fraction(17,2)).__floor__()))
            words[value,state]=word;successors[value,state]=code*2+int(recent>=0)
    a,b,*_=(layout() if expected_tables is None else expected_tables)
    assert np.array_equal(words,a) and np.array_equal(successors,b), 'table differs from rational recurrence'
    return words,successors


def reference(packed,cycles=2):
    pcm,index=decode(packed)
    assert (pcm[-1],index[-1])==(0,0)
    levels=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    words,successors=rational_tables();state=16;output=np.empty(len(pcm)*cycles+1,dtype='>u2')
    for i in range(len(output)):
        value=int(levels[i%len(pcm)])//4
        output[i]=words[value,state];state=int(successors[value,state])
    return pcm,index,levels,np.unpackbits(output.view('u1'))[:len(pcm)*cycles*16+1]


def intervals(meta):
    holds=np.tile(HOLDS,meta['pcm_samples']).astype(np.int64)
    end=0
    for s in meta['sections']:
        for byte in range(256,s['bytes']+1,256):
            sample=2*(end+byte)-3
            holds[sample*16+15]+=meta['bank_extra_tstates'] if byte==s['bytes'] else 18
        end+=s['bytes']
    return holds


def native_check(disk,meta,packed,reference_fn=reference,intervals_fn=intervals):
    from z80 import Z80Machine
    pcm,indices,levels,expected=reference_fn(packed)
    timing=intervals_fn(meta);budget=int(timing.sum()*2+1000000)
    labels=meta['player_labels'];blob=extract_player(disk)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    m.set_memory_block(0x8000,blob[:16384])
    if meta.get('direct'):
        for key,address,count in [('lower_disk',0x4000,28),('upper_disk',0x6000,32)]:
            location=labels[key];sector=(location>>8)*16+(location&255)
            m.set_memory_block(address,disk[sector*256:(sector+count)*256])
    else:
        m.set_memory_block(0x4000,decoder_table(0x4000,False))
        words,successors,first,second,ids,_,_,_=layout()
        import struct
        table=b''.join(struct.pack('<HBB',first[int(words[v,s])>>8],int(successors[v,s])*4,ids[int(words[v,s])&255])
                       for v in range(64) for s in range(32))
        m.set_memory_block(0x6000,table)
    decoder_rows=meta.get('decoder_rows',[0x4000+i*64 for i in range(89)])
    banks={};offset=0
    for s in meta['sections']:
        data=bytearray(b'\xa5'*16384);data[s['address']-0xc000:]=packed[offset:offset+s['bytes']]
        if s['bank']==7:data[:6912]=blob[16384:]
        if s['bank']==2:m.set_memory_block(s['address']-0x4000,data[s['address']-0xc000:])
        banks[s['bank']]=data;offset+=s['bytes']
    before=bytes(m.memory[0x4000:0xc000]);bits=bytearray();times=array('I');pages=[];checked=0
    def page(bank):
        if pages:
            previous=pages[-1];begin=meta['resident_reserve'] if previous==2 else 0
            assert bytes(m.memory[0xc000+begin:])==bytes(banks[previous][begin:]), 'paged payload/screen changed'
        if bank==2:banks[2][:]=m.memory[0x8000:0xc000]
        m.set_memory_block(0xc000,banks[bank]);pages.append(bank)
    def output(port,value):
        nonlocal checked
        if port&255==254:
            i=len(bits);sample=i//16;slot=i%16
            pairs=meta.get('loop_idle_pairs',0)
            if pairs:
                cycle,local=divmod(i,meta['outputs_per_cycle']);at=(meta['pcm_samples']-3)*16+15
                if at<=local<at+pairs*2:slot=-1
                else:
                    if local>=at:local-=pairs*2
                    sample=cycle*meta['pcm_samples']+local//16;slot=local%16
            assert value in (0,16), (i,port,value)
            assert not 0x4000<=port<0x8000, ('contended output port',hex(port))
            if slot==4:
                nxt=(sample+1)%len(pcm)
                assert m.ix==int(pcm[nxt])+32768, (sample,'predictor',m.ix,int(pcm[nxt])+32768)
                assert m.alt_hl==decoder_rows[int(indices[nxt])],(sample,'index')
                checked+=1
            bits.append(value>>4);times.append(budget-m.ticks_to_stop)
            if len(bits)==len(expected):m.set_breakpoint(m.pc)
        elif port==0x7ffd:
            assert 24<=value<=31
            page(value&7)
        else:raise AssertionError(('unexpected port',port,value))
    page(0);m.set_output_callback(output);m.pc=labels['ready'];m.sp=0x6000;m.ticks_to_stop=budget
    while len(bits)<len(expected):
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError(('timeout',hex(m.pc),len(bits)))
    wrong=np.flatnonzero(np.frombuffer(bits,'u1')!=expected)
    assert not len(wrong), ('bits',wrong[:10])
    actual=np.diff(np.asarray(times,dtype=np.int64));wanted=np.tile(timing,2)
    wrong=np.flatnonzero(actual!=wanted)
    assert not len(wrong),('timing',wrong[:10],actual[wrong[:10]],wanted[wrong[:10]])
    assert pages==[s['bank'] for s in meta['sections']]*2+[0]
    after=bytearray(m.memory[0x4000:0xc000])
    for a in meta['mutable_addresses']:after[a-0x4000]=before[a-0x4000]
    assert bytes(after)==before,'fixed RAM changed'
    return dict(complete=True,cycles_verified=2,bits_verified=len(bits),pcm16_samples_verified=checked,
                every_pdm_bit_exact=True,every_predictor_and_index_exact=True,memory_guards_passed=True,
                every_output_port_uncontended=True,bank_sequence=pages,cycle_tstates=int(timing.sum()),
                maximum_hold_tstates=int(actual.max()),rational_table_cases=2048,
                interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
                scope='Continuous Z80 execution; excludes ULA contention, disk and ROM')


def fuse_check(fuse,out,meta,packed,probe=False,reference_fn=reference,intervals_fn=intervals):
    pcm,indices,levels,expected=reference_fn(packed)
    labels=meta['player_labels'];blob=extract_player((out/'audiobook-preview.trd').read_bytes())
    count=33 if probe else len(expected)
    work=out/('fuse-probe' if probe else 'verification-work');work.mkdir(exist_ok=True)
    lines=['base 10','set $r 0','set $bits 0'];widths={};eid=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal eid
        eid+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {eid}',f'print {tag}'])
        lines.extend('print '+s for s in expressions);lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition:lines.append(f'condition {eid} {condition}')
    event(labels['ready'],100,[stamp,'z80:sp'],['set $r 1'])
    attrs=[f'[{0xd800+i}]' for i in range(96)]
    event(labels['loading_visible'],103,[stamp,'ula:mem7ffd',*attrs])
    event(labels['loading_hidden'],104,[stamp,'ula:mem7ffd',*attrs])
    event('port write 254',140,[stamp,'z80:pc','z80:a','z80:d']+(['z80:b'] if meta.get('direct') else []),['set $bits $bits+1'],condition='$r==1')
    event('port write 254',200,[stamp],condition=f'$bits>={count}',stop=True)
    for address in meta['first_addresses']:
        if not probe:
            event(address+23,120,['z80:ix'])
            event(address+20,121,['z80:hl'])
    for i in range(7):event(labels[f'page_{i}']+2,150,['z80:a','ula:mem7ffd','ula:mem1ffd'])
    event(labels['disk_call'],102,['$r',stamp,'ula:mem7ffd','z80:sp'])
    script='\n'.join(lines);(work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
             '--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())]
    try:
        result=subprocess.run(command,cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=600)
    except subprocess.TimeoutExpired as e:
        (work/'timeout-trace.txt.gz').write_bytes(gzip.compress(e.stdout or b'',mtime=0));raise
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(result.stdout,mtime=0))
    (work/'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode!=77:raise AssertionError(('Fuse failed',result.returncode,result.stderr[:1000]))
    numbers=iter(int(s.strip(),0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=array('I');bits=bytearray();samples=[];states=[];pages=[];reads=[];ready=[];ends=[];shown=[];hidden=[]
    port_rows=[]
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140:
            tick,pc,a,d=row[:4]
            op=blob[pc-2-0x8000:pc-0x8000]
            if op==b'\xed\x51':value=d
            elif op==b'\xed\x41' and meta.get('direct'):value=row[4]
            elif op==b'\xed\x71':value=0
            elif op==b'\xd3\xfe':value=a
            else:raise AssertionError(('unknown output instruction',row,op.hex()))
            assert value in (0,16)
            bits.append(value>>4);times.append(tick)
            if probe:port_rows.append(row+[value])
        elif tag==120:samples.append(row[0])
        elif tag==121:states.append(row[0])
        elif tag==150:pages.append(row)
        elif tag==102:reads.append(row)
        elif tag==103:shown.append(row)
        elif tag==104:hidden.append(row)
        elif tag==100:ready.append(row)
        elif tag==200:ends.append(row)
    if probe:return dict(port_rows=port_rows,ready=ready,reads=len(reads),shown=shown,hidden=hidden)
    assert len(ready)==len(ends)==1 and ready[0][1]==0x6000
    assert count<=len(bits)<=count+1
    bits=bits[:count];times=times[:count]
    assert np.array_equal(np.frombuffer(bits,'u1'),expected),'Fuse PDM mismatch'
    expected_pcm=np.tile(np.r_[pcm[1:],pcm[:1]].astype(np.int32)+32768,2)
    row_addresses=np.array(meta.get('decoder_rows',[0x4000+i*64 for i in range(89)]))
    expected_index=np.tile(row_addresses[np.r_[indices[1:],indices[:1]]],2)
    assert np.array_equal(samples,expected_pcm),'Fuse predictor mismatch'
    assert np.array_equal(states,expected_index),'Fuse index mismatch'
    wanted=[s['bank']+24 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    assert len(pages)==len(wanted) and all(r[0]==r[1]==b for r,b in zip(pages,wanted))
    assert len({r[2] for r in pages})==1
    assert len(reads)==meta.get('preload_table_sectors',55)+len(packed)//256 and all(r[0]==0 and r[2]&8 and 0x5f00<=r[3]<0x6000 for r in reads)
    assert len(shown)==len(hidden)==1 and shown[0][1]==hidden[0][1]==31
    assert shown[0][2:]==[0x47]*96 and hidden[0][2:]==[0]*96
    assert all(shown[0][0]<=r[1]<hidden[0][0]<ready[0][0] for r in reads)
    timeline=np.asarray(times,dtype=np.int64);timeline-=timeline[0]
    actual=np.diff(timeline);native=np.tile(intervals_fn(meta),2)
    assert np.all(actual>=native)
    (out/'output-times.u32.gz').write_bytes(gzip.compress(timeline.astype('<u4').tobytes(),mtime=0))
    n=meta.get('outputs_per_cycle',meta['pcm_samples']*16)
    return dict(complete=True,cold_boot=True,machine='128',cycles_verified=2,bits_verified=len(bits),
                pcm16_samples_verified=len(samples),every_pdm_bit_exact=True,every_predictor_and_index_exact=True,
                paging_latches_verified=True,startup_sector_reads=len(reads),runtime_disk_reads=0,
                cycle_durations_seconds=(np.diff(timeline[::n])/CPU_CLOCK).tolist(),
                average_pdm_rate_hz=2*n*CPU_CLOCK/int(timeline[-1]),
                average_pcm_rate_hz=2*len(pcm)*CPU_CLOCK/int(timeline[-1]),
                maximum_hold_tstates=int(actual.max()),minimum_instantaneous_pdm_rate_hz=CPU_CLOCK/int(actual.max()),
                additional_ula_tstates=int(actual.sum()-native.sum()),native_tstates_per_cycle=int(native[:n].sum()),
                interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
                loading_message=dict(shown_before_reads=True,hidden_before_playback=True,shadow_screen_selected_during_all_reads=True),
                trd_sha256=hashlib.sha256((out/'audiobook-preview.trd').read_bytes()).hexdigest(),
                fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path)
    p.add_argument('--fuse',type=Path);p.add_argument('--probe',action='store_true')
    args=p.parse_args();out=args.directory.resolve()
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    if args.fuse:
        report=fuse_check(args.fuse,out,meta,packed,args.probe)
        save(out/('probe.json' if args.probe else 'fuse.json'),report)
    else:
        report=native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed)
        save(out/'native.json',report)
    print(json.dumps(report),flush=True)
