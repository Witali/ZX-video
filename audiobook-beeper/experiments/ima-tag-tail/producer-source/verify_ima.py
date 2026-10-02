"""Independent IMA recurrence, complete Z80 execution and cold-Fuse gates."""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,re,subprocess,time
from array import array
from collections import Counter,deque
from pathlib import Path
import numpy as np
from ima_codec import decode
from ima_player import CPU_CLOCK,ORIGIN
from verify_pdm import extract_player,save
from smoke_test_fuse import hidden_startupinfo


def reference(packed,meta):
    pcm,indices=decode(packed,meta['initial_predictor'],meta['initial_index'])
    pcm8=((pcm.astype(np.int32)+32768)>>8).astype(np.uint8)
    weights=np.full(len(pcm),6,dtype=np.int32); offset=0
    for s in meta['sections']:
        offset+=s['bytes']; weights[2*offset-2]=10
    sample_per_slot=np.repeat(pcm8,weights)
    levels=np.r_[sample_per_slot,sample_per_slot,pcm8[0]]
    bits=np.empty(len(levels),dtype=np.uint8); error=128; pending=deque([0,0,0])
    for i,value in enumerate(levels):
        error+=int(value); bit=int(error>=256); error&=255
        bits[i]=pending.popleft(); pending.append(bit)
    return pcm,indices,levels,bits,len(sample_per_slot)


def intervals(meta):
    parts=[]; offset=0
    for s in meta['sections']:
        for byte in range(s['bytes']):
            # First input sample is primed; while holding it, decode the high nibble.
            if byte==s['bytes']-1: high=[74,78,81,76,80,79,77,80,72,77]
            elif byte%256==255: high=[74,78,81,76,80,78]
            else: high=[74,78,81,76,66,78]
            parts.extend(high); parts.extend([74,78,81,72,56,78])
        offset+=s['bytes']
    result=np.array(parts,dtype=np.int64)
    assert result.sum()==446*(2*offset)+14*(offset//256)+307*len(meta['sections'])
    return result


def native_check(disk,meta,packed):
    from z80 import Z80Machine
    pcm,indices,levels,expected,n=reference(packed,meta)
    timing=intervals(meta); budget=int(2*timing.sum()+1000000)
    machine=Z80Machine(); machine.memory[:]=b'\xa5'*65536
    blob=extract_player(disk); machine.set_memory_block(ORIGIN,blob)
    reserve=meta['resident_reserve']; banks={}; offset=0
    for s in meta['sections']:
        bank=bytearray(b'\xa5'*16384); part=packed[offset:offset+s['bytes']]; offset+=s['bytes']
        bank[s['address']-0xc000:]=part
        if s['bank']==2:
            bank[:reserve]=blob[:reserve]; machine.set_memory_block(0x8000,bank)
        if s['bank']==5:
            bank[:6912]=blob[reserve:reserve+6912]; machine.set_memory_block(0x4000,bank)
        banks[s['bank']]=bank
    before=bytes(machine.memory[0x4000:0xc000]); labels=meta['player_labels']
    samples_at={labels[name.replace('_clipped','_out4')]+2 for name in meta['sample_labels']}
    times=array('I'); bits=bytearray(); pages=[]; predictors=[]
    def page(bank): machine.set_memory_block(0xc000,banks[bank]); pages.append(bank)
    def output(port,value):
        if port==0x10fe:
            i=len(bits)
            if machine.d!=int(levels[i]) or value&15: raise AssertionError(f'PCM/border mismatch at {i}: {machine.d}/{levels[i]}')
            times.append(budget-machine.ticks_to_stop); bits.append((value>>4)&1)
            if machine.pc in samples_at: predictors.append(machine.ix)
            if len(bits)==len(expected): machine.set_breakpoint(labels['high_out0']+2)
        elif port==0x7ffd:
            if value not in range(16,24): raise AssertionError('invalid paging value')
            page(value&7)
        else: raise AssertionError(f'unexpected port {port:04x}')
    page(meta['sections'][0]['bank']); machine.set_output_callback(output)
    machine.pc=labels['ready']; machine.sp=0x6000; machine.ticks_to_stop=budget
    while len(bits)<len(expected) or machine.pc!=labels['high_out0']+2:
        if machine.run()&machine._TICKS_LIMIT_HIT: raise AssertionError('incomplete native IMA playback')
    if not np.array_equal(np.frombuffer(bits,'u1'),expected): raise AssertionError('native PDM mismatch')
    measured=np.diff(np.asarray(times,dtype=np.int64))
    if not np.array_equal(measured,np.tile(timing,2)):
        wrong=np.flatnonzero(measured!=np.tile(timing,2)); raise AssertionError(f'native intervals differ at {wrong[:10]}: {measured[wrong[:10]]}')
    wanted=np.tile(np.r_[pcm[1:],pcm[:1]].astype(np.int32)+32768,2)
    if predictors!=wanted.tolist(): raise AssertionError(f'16-bit predictor mismatch/count: {len(predictors)} expected {len(wanted)}')
    wanted_pages=[s['bank'] for s in meta['sections']]*2+[meta['sections'][0]['bank']]
    if pages!=wanted_pages: raise AssertionError('bank sequence changed')
    after=bytearray(machine.memory[0x4000:0xc000])
    for address in meta['mutable_addresses']: after[address-0x4000]=before[address-0x4000]
    if after!=before: raise AssertionError('code/table/PCM/screen memory changed')
    return dict(complete=True,cycles_verified=2,bits_verified=len(bits),pcm16_samples_verified=len(predictors),
        all_predictors_exact=True,all_pcm8_values_exact=True,every_pdm_bit_exact=True,memory_guards_passed=True,
        cycle_tstates=int(timing.sum()),maximum_hold_tstates=int(measured.max()),bank_sequence=pages,
        scope='Z80 CPU execution; no ULA or ROM/disk latency')


def fuse_check(fuse,out,meta,packed):
    pcm,indices,levels,expected,n=reference(packed,meta); labels=meta['player_labels']
    work=out/'verification-work';work.mkdir(exist_ok=True)
    lines=['base 10','set $r 0','set $bits 0','set $loading 0']; widths={}; event_id=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal event_id
        event_id+=1; widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {event_id}',f'print {tag}'])
        lines.extend('print '+x for x in expressions); lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition: lines.append(f'condition {event_id} {condition}')
    event(labels['start'],101,[],['set $loading 1'])
    event(labels['ready'],100,[stamp,'z80:sp'],['set $r 1','set $loading 0'])
    event('write 24319',199,[stamp,'z80:sp'],condition='$loading==1 && z80:sp<24320',stop=True)
    event('port write 4350',140,[stamp,'z80:e','z80:d'],['set $bits $bits+1'],condition='$r==1')
    for name in meta['sample_labels']: event(labels[name],120,['z80:ix','z80:hl'])
    for i in range(len(meta['sections'])):
        event(labels[f'page_{i}']+2,150,['z80:a','ula:mem7ffd','ula:mem1ffd'])
    event(labels['disk_call'],102,['$r'])
    event(labels['high_out0']+4,200,[stamp],condition=f'$bits=={len(expected)}',stop=True)
    script='\n'.join(lines); (work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
             '--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())]
    result=subprocess.run(command,cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=300)
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(result.stdout,mtime=0))
    (work/'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode!=77: raise AssertionError(f'Fuse incomplete: {result.returncode}')
    numbers=iter(int(s.strip(),0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=array('I'); values=bytearray(); inputs=bytearray(); predictors=[]; states=[]; pages=[]; reads=[]; ready=[]; ends=[]
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140: times.append(row[0]);values.append(row[1]);inputs.append(row[2])
        elif tag==120: predictors.append(row[0]);states.append((row[1]-meta['table_base'])//64)
        elif tag==150: pages.append(row)
        elif tag==102: reads.append(row[0])
        elif tag==100: ready.append(row)
        elif tag==200: ends.append(row)
        elif tag==199: raise AssertionError('startup stack exceeded reservation')
    values=np.frombuffer(values,'u1')
    if len(ready)!=1 or len(ends)!=1 or ready[0][1]!=0x6000 or len(values)!=len(expected): raise AssertionError('incomplete Fuse trace')
    if not np.array_equal(np.frombuffer(inputs,'u1'),levels) or np.any(values&15): raise AssertionError('Fuse PCM8/border mismatch')
    if not np.array_equal((values>>4)&1,expected): raise AssertionError('Fuse PDM mismatch')
    if not np.array_equal(predictors,np.tile(np.r_[pcm[1:],pcm[:1]].astype(np.int32)+32768,2)): raise AssertionError('Fuse PCM16 predictor mismatch')
    if not np.array_equal(states,np.tile(np.r_[indices[1:],indices[:1]],2)): raise AssertionError('Fuse IMA index mismatch')
    banks=[s['bank']|16 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    if len(pages)!=len(banks) or any(p[0]!=b or p[1]!=b for p,b in zip(pages,banks)) or len({p[2] for p in pages})!=1:
        raise AssertionError('Fuse paging latch mismatch')
    if len(reads)!=len(packed)//256 or any(reads): raise AssertionError('unexpected disk reads')
    timeline=np.asarray(times,dtype=np.int64);timeline-=timeline[0]
    actual=np.diff(timeline);native=np.tile(intervals(meta),2)
    if np.any(actual<native) or CPU_CLOCK/actual.max()<40000: raise AssertionError(f'output deadline missed: {actual.max()} T')
    (out/'output-times.u32.gz').write_bytes(gzip.compress(timeline.astype('<u4').tobytes(),mtime=0))
    return dict(complete=True,cold_boot=True,machine='128',cycles_verified=2,bits_verified=len(expected),
        pcm16_samples_verified=len(predictors),every_predictor_and_index_exact=True,every_pdm_bit_exact=True,
        every_pcm8_value_exact=True,paging_latches_verified=True,startup_stack_guard_passed=True,
        startup_sector_reads=len(reads),runtime_disk_reads=0,cycle_durations_seconds=(np.diff(timeline[::n])/CPU_CLOCK).tolist(),
        average_pcm_rate_hz=2*len(pcm)*CPU_CLOCK/int(timeline[-1]),average_pdm_rate_hz=2*n*CPU_CLOCK/int(timeline[-1]),
        minimum_instantaneous_pdm_rate_hz=CPU_CLOCK/int(actual.max()),maximum_hold_tstates=int(actual.max()),
        interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
        additional_ula_tstates=int(actual.sum()-native.sum()),native_tstates_per_cycle=int(native[:n].sum()),
        trd_sha256=hashlib.sha256((out/'audiobook-preview.trd').read_bytes()).hexdigest(),
        fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)


def verify(out,fuse):
    meta=json.loads((out/'player.json').read_bytes());packed=gzip.decompress((out/'soundtrack.ima.gz').read_bytes())
    native=native_check((out/'audiobook-preview.trd').read_bytes(),meta,packed)
    print(json.dumps({'native':native}),flush=True)
    actual=fuse_check(fuse,out,meta,packed)
    report=dict(complete=True,native=native,fuse=actual)
    save(out/'verification.json',report);print(json.dumps({'fuse':actual}),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--fuse',required=True,type=Path)
    args=p.parse_args();verify(args.directory,args.fuse)
