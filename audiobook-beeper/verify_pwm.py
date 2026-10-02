"""Independent PWM widths, IMA states, native timing and full cold Fuse checks."""
import gzip,hashlib,json,re,subprocess
from array import array
from collections import Counter
from pathlib import Path

import numpy as np

from ima_codec import decode
from ima_player import CPU_CLOCK,ORIGIN
from verify_pdm import extract_player,save
from smoke_test_fuse import hidden_startupinfo


def reference(packed,meta):
    pcm,indices=decode(packed,meta['initial_predictor'],meta['initial_index'])
    widths=np.repeat(((pcm.astype(np.int32)+32768)>>12)*4+68,2)
    periods=np.full(len(widths),226,dtype=np.int64)
    end=0
    for i,section in enumerate(meta['sections']):
        end+=section['bytes']
        periods[4*end-3]+=121 if i==7 else 89
    holds=np.empty(2*len(widths),dtype=np.int64)
    holds[::2]=widths;holds[1::2]=periods-widths
    return pcm,indices,holds


def native_check(disk,meta,packed):
    from z80 import Z80Machine
    pcm,indices,holds=reference(packed,meta)
    expected=np.tile(holds,2);n=len(holds);budget=int(expected.sum()+1000000)
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    blob=extract_player(disk);reserve=meta['resident_reserve'];banks={};offset=0
    m.set_memory_block(ORIGIN,blob)
    for s in meta['sections']:
        bank=bytearray(b'\xa5'*16384)
        bank[s['address']-0xc000:]=packed[offset:offset+s['bytes']];offset+=s['bytes']
        if s['bank']==2:bank[:reserve]=blob[:reserve];m.set_memory_block(0x8000,bank)
        if s['bank']==5:bank[:6912]=blob[reserve:];m.set_memory_block(0x4000,bank)
        banks[s['bank']]=bank
    before=bytes(m.memory[0x4000:0xc000]);labels=meta['player_labels']
    predictors=[];states=[];pages=[];times=array('I');values=bytearray()
    sample_at={labels[h+'_second_rise']+2 for h in ('low','high')}
    def page(bank):m.set_memory_block(0xc000,banks[bank]);pages.append(bank)
    def output(port,value):
        if port==0x10fe:
            k=len(values)
            if value!=(16 if k%2==0 else 0):raise AssertionError(f'wrong PWM level {k}: {value}')
            if k%2==0 and m.a!=15-((int(pcm[(k//4)%len(pcm)])+32768)>>12):
                raise AssertionError(f'wrong width at edge {k}: {m.a}')
            times.append(budget-m.ticks_to_stop);values.append(value)
            if m.pc in sample_at:predictors.append(m.ix);states.append((m.alt_hl-meta['table_base'])//64)
            if len(values)==2*n+1:m.set_breakpoint(labels['high_first_rise']+2)
        elif port==0x7ffd:
            if not 16<=value<24:raise AssertionError('bad page value')
            page(value&7)
        else:raise AssertionError(f'unexpected port {port:04x}')
    page(0);m.set_output_callback(output);m.pc=labels['ready'];m.sp=0x6000;m.ticks_to_stop=budget
    while len(values)<2*n+1 or m.pc!=labels['high_first_rise']+2:
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError(f'incomplete native playback: {len(values)} edges')
    measured=np.diff(np.asarray(times,dtype=np.int64))
    wrong=np.flatnonzero(measured!=expected)
    if len(wrong):raise AssertionError(f'hold mismatch {wrong[:12]}: actual {measured[wrong[:12]]}, expected {expected[wrong[:12]]}')
    if predictors!=np.tile(np.roll(pcm.astype(np.int32)+32768,-1),2).tolist():raise AssertionError('predictor mismatch')
    if states!=np.tile(np.roll(indices,-1),2).tolist():raise AssertionError('state mismatch')
    if pages!=[s['bank'] for s in meta['sections']]*2+[0]:raise AssertionError('bank mismatch')
    after=bytearray(m.memory[0x4000:0xc000])
    for a in meta['mutable_addresses']:after[a-0x4000]=before[a-0x4000]
    if after!=before:raise AssertionError('unexpected memory write')
    return dict(complete=True,cycles=2,edges=len(values),exact_widths_and_periods=True,
                exact_predictors_and_indices=len(predictors),memory_guards_passed=True,
                cycle_tstates=int(holds.sum()),ordinary_sample_tstates=452,
                scope='Independent Z80 CPU; no ULA, TR-DOS or disk latency')


def fuse_check(fuse,out,meta,packed):
    pcm,indices,holds=reference(packed,meta);n=len(holds);labels=meta['player_labels']
    work=out/'verification-work';work.mkdir(exist_ok=True)
    lines=['base 10','set $r 0','set $edges 0','set $loading 0'];widths={};event_id=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal event_id
        event_id+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {event_id}',f'print {tag}'])
        lines.extend('print '+x for x in expressions);lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition:lines.append(f'condition {event_id} {condition}')
    event(labels['start'],101,[],['set $loading 1'])
    event(labels['ready'],100,[stamp,'z80:sp'],['set $r 1','set $loading 0'])
    event('write 24319',199,[stamp,'z80:sp'],condition='$loading==1 && z80:sp<24320',stop=True)
    # Break after each actual OUT. The independent native core checks ED71's
    # zero output; normal-speed Fuse sound capture checks the audible path.
    for half in ('high','low'):
        for stage in ('first','second'):
            base=half+'_'+stage
            event(labels[base+'_rise']+2,140,[stamp,'z80:a','z80:b'],['set $edges $edges+1'])
            event(labels[base+'_fall']+2,141,[stamp,'z80:a'],['set $edges $edges+1'])
        event(labels[half+'_second_rise']+2,120,['z80:ix'])
        event(labels[half+'_first_state'],121,['z80:hl'])
    for i in range(8):event(labels[f'page_{i}']+2,150,['z80:a','ula:mem7ffd','ula:mem1ffd'])
    event(labels['disk_call'],102,['$r'])
    event(labels['high_first_rise']+2,200,[stamp],condition=f'$edges=={2*n+1}',stop=True)
    script='\n'.join(lines);(work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
             '--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())]
    result=subprocess.run(command,cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=300)
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(result.stdout,mtime=0));(work/'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode!=77:raise AssertionError(f'Fuse incomplete: {result.returncode}: {result.stderr[-1000:]}')
    nums=iter(int(s.strip(),0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=array('I');q=[];predictors=[];states=[];pages=[];reads=[];ready=[];ends=[]
    for tag in nums:
        row=[next(nums) for _ in range(widths[tag])]
        if tag in (140,141):
            if (tag==140)!=(len(times)%2==0):raise AssertionError('wrong edge order')
            times.append(row[0])
            if tag==140:
                q.append(row[1])
                if row[2]!=16:raise AssertionError('wrong high value')
        elif tag==120:predictors.append(row[0])
        elif tag==121:states.append((row[0]-meta['table_base'])//64)
        elif tag==150:pages.append(row)
        elif tag==102:reads.append(row[0])
        elif tag==100:ready.append(row)
        elif tag==200:ends.append(row)
        elif tag==199:raise AssertionError('startup stack exceeded reservation')
    if len(ready)!=1 or len(ends)!=1 or ready[0][1]!=0x6000 or len(times)!=2*n+1:raise AssertionError('incomplete trace')
    expected_q=np.r_[np.tile(np.repeat(15-((pcm.astype(np.int32)+32768)>>12),2),2),15-((int(pcm[0])+32768)>>12)]
    if not np.array_equal(q,expected_q):raise AssertionError('Fuse width mismatch')
    if not np.array_equal(predictors,np.tile(np.roll(pcm.astype(np.int32)+32768,-1),2)):raise AssertionError('Fuse PCM16 mismatch')
    if not np.array_equal(states,np.tile(np.roll(indices,-1),2)):raise AssertionError('Fuse IMA index mismatch')
    wanted=[s['bank']|16 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    if len(pages)!=16 or any(a!=b or latch!=b for (a,latch,_),b in zip(pages,wanted)) or len({p[2] for p in pages})!=1:raise AssertionError('Fuse page mismatch')
    if len(reads)!=len(packed)//256 or any(reads):raise AssertionError('disk read mismatch')
    ts=np.asarray(times,dtype=np.int64);ts-=ts[0];actual=np.diff(ts)
    if np.any(actual<np.tile(holds,2)):raise AssertionError('negative ULA wait')
    (out/'output-times.u32.gz').write_bytes(gzip.compress(ts.astype('<u4').tobytes(),mtime=0))
    periods=np.diff(ts[::2]);samples=np.diff(ts[::4])
    return dict(complete=True,cold_boot=True,machine='128',cycles=2,edges=len(ts),
                exact_predictors_and_indices=len(predictors),exact_pwm_width_selectors=True,
                paging_latches_verified=True,startup_stack_guard_passed=True,
                startup_sector_reads=len(reads),runtime_disk_reads=0,
                cycle_durations_seconds=(np.diff(ts[::n])/CPU_CLOCK).tolist(),
                average_pcm_rate_hz=2*len(pcm)*CPU_CLOCK/int(ts[-1]),
                average_pwm_carrier_hz=4*len(pcm)*CPU_CLOCK/int(ts[-1]),
                period_histogram_tstates=dict(sorted(Counter(map(int,periods)).items())),
                sample_histogram_tstates=dict(sorted(Counter(map(int,samples)).items())),
                additional_ula_tstates=int(actual.sum()-2*holds.sum()),maximum_edge_hold_tstates=int(actual.max()),
                trd_sha256=hashlib.sha256((out/'audiobook-preview.trd').read_bytes()).hexdigest(),
                fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)
