"""Independent integer reference, full native execution and cold Fuse checks."""
import argparse,gzip,hashlib,json,re,subprocess
from array import array
from collections import Counter
from pathlib import Path
import numpy as np
from ima_codec import decode
from pdm_player import ORIGIN,CPU_CLOCK
from verify_pcm import extract_player,save
from smoke_test_fuse import hidden_startupinfo


def step(pcm8,state):
    # Exact Q16 recurrence, independent of the floating-point table builder.
    recent=((state>>2)*2-15)*2048;older=((state&3)*2-3)*8192
    x=((int(pcm8)>>2)*4+2)*256;word=0
    for _ in range(8):
        u=x+(3*recent-older)//2
        bit=int(u>=32768);older,recent=recent,u-bit*65536
        word=word*2+bit
    r=max(0,min(15,(recent*16+8*65536)//65536))
    o=max(0,min(3,(older*4+2*65536)//65536))
    return word,r*4+o


def reference(packed,meta,cycles=2):
    pcm,indices=decode(packed,meta['initial_predictor'],meta['initial_index'])
    levels=((pcm.astype(np.int32)+32768)>>8).astype('u1')
    weights=np.ones(len(pcm),dtype=np.int32)
    end=0
    for s in meta['sections']:end+=s['bytes']*2;weights[end-1]=2
    words=[];state=meta['initial_feedback']
    for _ in range(cycles):
        for value,count in zip(levels,weights):
            word,state=step(value,state);words.extend([word]*int(count))
    final,_=step(levels[0],state)
    bits=np.r_[np.unpackbits(np.array(words,dtype='u1')),final>>7].astype('u1')
    return pcm,indices,levels,weights,bits


def intervals(meta):
    result=[]
    for s in meta['sections']:
        for byte in range(s['bytes']):
            high=[49,53,56,58,53,56,59,62 if byte%4==3 else 52]
            if byte%256==255:high[-1]+=18
            result.extend(high)
            if byte==s['bytes']-1:result.extend([65,54,44,56,48,44,51,54])
            result.extend([49,53,56,58,53,56,59,44])
    result=np.array(result,dtype=np.int64)
    assert result.sum()==433.25*meta['pcm_samples']+18*(meta['packed_bytes']//256-len(meta['sections']))+434*len(meta['sections'])
    return result


def native_check(disk,meta,packed):
    from z80 import Z80Machine
    pcm,indices,levels,weights,expected=reference(packed,meta)
    timing=intervals(meta);budget=int(2*timing.sum()+1000000)
    labels=meta['player_labels'];blob=extract_player(disk)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536;m.set_memory_block(ORIGIN,blob[:16384])
    m.set_memory_block(0x4000,blob[16384:16384+6912]);banks={};offset=0
    for s in meta['sections']:
        data=bytearray(b'\xa5'*16384)
        data[s['address']-0xc000:]=packed[offset:offset+s['bytes']];offset+=s['bytes']
        if s['bank']==5:
            data[:6912]=blob[16384:16384+6912];m.set_memory_block(0x4000,data)
        banks[s['bank']]=data
    before=bytes(m.memory[0x4000:0xc000]);times=array('I');bits=bytearray();pages=[];predictors=[];states=[]
    at={labels[k.replace('_sample','_out5')]+2 for k in labels if k.endswith('_sample')}
    def page(bank):
        if pages:assert bytes(m.memory[0xc000:])==bytes(banks[pages[-1]]),'paged audio RAM changed'
        m.set_memory_block(0xc000,banks[bank]);pages.append(bank)
    def output(port,value):
        if port&255==254:
            if value not in (0,16):raise AssertionError('MIC/border changed')
            times.append(budget-m.ticks_to_stop);bits.append(value>>4)
            if m.pc in at:
                predictors.append(m.ix);states.append((m.alt_hl-meta['table_base'])//64)
            if len(bits)==len(expected):m.set_breakpoint(labels['high_out0']+2)
        elif port==0x7ffd:
            if value not in range(16,24):raise AssertionError('bad paging value')
            page(value&7)
        else:raise AssertionError(f'unexpected port {port:04x}')
    page(0);m.set_output_callback(output);m.pc=labels['ready'];m.sp=0x6000;m.ticks_to_stop=budget
    while len(bits)<len(expected) or m.pc!=labels['high_out0']+2:
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError('incomplete native playback')
    actual=np.frombuffer(bits,'u1');wrong=np.flatnonzero(actual!=expected)
    if len(wrong):raise AssertionError(f'PDM bits differ at {wrong[:10]}')
    measured=np.diff(np.asarray(times,dtype=np.int64));wanted=np.tile(timing,2)
    wrong=np.flatnonzero(measured!=wanted)
    if len(wrong):raise AssertionError(f'timing at {wrong[:8]}: {measured[wrong[:8]]} vs {wanted[wrong[:8]]}')
    assert predictors==np.tile(np.r_[pcm[1:],pcm[:1]].astype(np.int32)+32768,2).tolist()
    assert states==np.tile(np.r_[indices[1:],indices[:1]],2).tolist()
    assert pages==[s['bank'] for s in meta['sections']]*2+[0]
    after=bytearray(m.memory[0x4000:0xc000])
    for address in meta['mutable_addresses']:after[address-0x4000]=before[address-0x4000]
    assert bytes(after)==before,'native fixed RAM changed'
    assert bytes(m.memory[0xc000:])==bytes(banks[0])
    return dict(complete=True,cycles_verified=2,bits_verified=len(bits),pcm16_samples_verified=len(predictors),
                every_pdm_bit_exact=True,every_predictor_and_index_exact=True,memory_guards_passed=True,
                bank_sequence=pages,cycle_tstates=int(timing.sum()),maximum_hold_tstates=int(measured.max()),
                interval_histogram_tstates=dict(sorted(Counter(map(int,measured)).items())),
                scope='Z80 CPU; excludes ULA, ROM and disk latency')


def fuse_check(fuse,out,meta,packed):
    pcm,indices,levels,weights,expected=reference(packed,meta);n=(len(expected)-1)//2
    labels=meta['player_labels'];work=out/'verification-work';work.mkdir(exist_ok=True)
    lines=['base 10','set $r 0','set $bits 0','set $loading 0'];widths={};eid=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal eid
        eid+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {eid}',f'print {tag}'])
        lines.extend('print '+s for s in expressions);lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition:lines.append(f'condition {eid} {condition}')
    event(labels['start'],101,[],['set $loading 1'])
    event(labels['ready'],100,[stamp,'z80:sp'],['set $r 1','set $loading 0'])
    event('write 24319',199,[stamp,'z80:sp'],condition='$loading==1 && z80:sp<24320',stop=True)
    # Fuse treats the 8-bit port 254 as a low-byte match, covering both
    # 00FE and 10FE. Adding a second 10FE breakpoint double-counts ones.
    event('port write 254',140,[stamp,'z80:a'],['set $bits $bits+1'],condition='$r==1')
    for label in labels:
        if label.endswith('_sample'):event(labels[label],120,['z80:ix'])
        if label.endswith('_state'):event(labels[label],121,['z80:hl'])
    for i in range(len(meta['sections'])):event(labels[f'page_{i}']+2,150,['z80:a','ula:mem7ffd','ula:mem1ffd'])
    event(labels['disk_call'],102,['$r'])
    event(labels['high_out0']+2,200,[stamp],condition=f'$bits=={len(expected)}',stop=True)
    script='\n'.join(lines);(work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
             '--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())]
    try:
        result=subprocess.run(command,cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=300)
    except subprocess.TimeoutExpired as failure:
        (work/'timeout-trace.txt.gz').write_bytes(gzip.compress(failure.stdout or b'',mtime=0))
        save(work/'timeout.json',dict(timeout_seconds=300,complete=False))
        raise
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(result.stdout,mtime=0));(work/'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode!=77:raise AssertionError(f'Fuse did not finish: {result.returncode}')
    numbers=iter(int(s.strip(),0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=array('I');values=bytearray();predictors=[];states=[];pages=[];reads=[];ready=[];ends=[]
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140:times.append(row[0]);values.append(row[1])
        elif tag==120:predictors.append(row[0])
        elif tag==121:states.append((row[0]-meta['table_base'])//64)
        elif tag==150:pages.append(row)
        elif tag==102:reads.append(row[0])
        elif tag==100:ready.append(row)
        elif tag==200:ends.append(row)
        elif tag==199:raise AssertionError('startup stack overflow')
    assert len(ready)==len(ends)==1 and ready[0][1]==0x6000
    values=np.frombuffer(values,'u1');assert np.all((values==0)|(values==16))
    assert np.array_equal(values>>4,expected),'Fuse bit mismatch'
    assert predictors==np.tile(np.r_[pcm[1:],pcm[:1]].astype(np.int32)+32768,2).tolist()
    assert states==np.tile(np.r_[indices[1:],indices[:1]],2).tolist()
    wanted_pages=[s['bank']|16 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    assert len(pages)==len(wanted_pages) and all(p[0]==p[1]==b for p,b in zip(pages,wanted_pages))
    assert len({p[2] for p in pages})==1
    assert len(reads)==len(packed)//256 and not any(reads)
    timeline=np.asarray(times,dtype=np.int64);timeline-=timeline[0]
    actual=np.diff(timeline);native=np.tile(intervals(meta),2);assert np.all(actual>=native)
    (out/'output-times.u32.gz').write_bytes(gzip.compress(timeline.astype('<u4').tobytes(),mtime=0))
    return dict(complete=True,cold_boot=True,machine='128',cycles_verified=2,bits_verified=len(expected),
                pcm16_samples_verified=len(predictors),every_pdm_bit_exact=True,every_predictor_and_index_exact=True,
                paging_latches_verified=True,startup_stack_guard_passed=True,startup_sector_reads=len(reads),runtime_disk_reads=0,
                cycle_durations_seconds=(np.diff(timeline[::n])/CPU_CLOCK).tolist(),
                average_pdm_rate_hz=2*n*CPU_CLOCK/int(timeline[-1]),
                average_pcm_rate_hz=2*len(pcm)*CPU_CLOCK/int(timeline[-1]),
                maximum_hold_tstates=int(actual.max()),minimum_instantaneous_pdm_rate_hz=CPU_CLOCK/int(actual.max()),
                interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
                additional_ula_tstates=int(actual.sum()-native.sum()),native_tstates_per_cycle=int(native[:n].sum()),
                trd_sha256=hashlib.sha256((out/'audiobook-preview.trd').read_bytes()).hexdigest(),
                fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--fuse',type=Path)
    args=p.parse_args();out=args.directory.resolve()
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    native=native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed);print(json.dumps(native),flush=True)
    actual=fuse_check(args.fuse,out,meta,packed) if args.fuse else None
    save(out/'verification.json',dict(complete=bool(actual),native=native,fuse=actual));print(json.dumps(actual),flush=True)
