"""Independent PCM/PDM recurrence, instruction timing and cold-Fuse checks."""
from __future__ import annotations
import argparse,gzip,hashlib,json,os,re,subprocess,time
from array import array
from collections import Counter,deque
from pathlib import Path
import numpy as np
from pcm_player import ORIGIN,CPU_CLOCK,BANK_BYTES,OVERSAMPLE
from verify_pdm import save,extract_player
from smoke_test_fuse import hidden_startupinfo


def reference(pcm,cycles=2,oversample=OVERSAMPLE):
    """Integer integrator and a separate FIFO, independent of RR/RES opcodes."""
    count=len(pcm)*oversample*cycles+1
    bits=np.empty(count,dtype=np.uint8); error=128; pending=deque([0,0,0])
    for i in range(count):
        error+=pcm[(i//oversample)%len(pcm)]
        pulse=int(error>=256)
        if pulse: error-=256
        bits[i]=pending.popleft(); pending.append(pulse)
    return bits,error


def native_intervals(meta):
    oversample=meta['oversample']; steady=meta.get('steady',False)
    n=meta['pcm_samples']; out=np.full(n*oversample,44 if steady else 32,dtype=np.int64)
    for sample in range(n):
        if sample%4==0: out[sample*oversample+1]+=4*meta['quarter_nops']
        if sample%4<3: out[(sample+1)*oversample-1]=43
        else:
            out[sample*oversample]=46
            out[(sample+1)*oversample-1]=49
        if sample%256==255: out[sample*oversample+1]=46
    total=0
    for section in meta['sections']:
        total+=section['bytes']; sample=total-1
        out[sample*oversample+2]=58
        out[sample*oversample+3]=42
    assert int(out.sum())==meta['deterministic_cycle_tstates']
    return out


def native_check(disk,meta,pcm):
    from z80 import Z80Machine
    oversample=meta['oversample']
    expected,error=reference(pcm,oversample=oversample); budget=100_000_000
    machine=Z80Machine(); machine.memory[:]=b'\xa5'*65536
    code=extract_player(disk); machine.set_memory_block(ORIGIN,code)
    labels=meta['player_labels']; endpoint=labels['out_0_0_0']+2
    bits=bytearray(); times=array('I'); pages=[]
    def load_bank(bank):
        index=next(i for i,s in enumerate(meta['sections']) if s['bank']==bank)
        s=meta['sections'][index]; part=pcm[index*BANK_BYTES:index*BANK_BYTES+s['bytes']]
        machine.set_memory_block(0xc000,b'\xa5'*(s['address']-0xc000)+part); pages.append(bank)
    def output(port,value):
        if port==0x10fe:
            index=len(bits)
            if value&15: raise AssertionError('MIC/border bits changed')
            if machine.d!=pcm[(index//oversample)%len(pcm)]: raise AssertionError('wrong PCM sample/order')
            bits.append((value>>4)&1); times.append(budget-machine.ticks_to_stop)
            if len(bits)==len(expected): machine.set_breakpoint(endpoint)
        elif port&255==253 and port>>8==value and 0x10<=value<=0x17:
            load_bank(value&7)
        else: raise AssertionError(f'unexpected port/value {port:04x}/{value}')
    load_bank(meta['sections'][0]['bank'])
    machine.set_output_callback(output)
    machine.pc=labels['playback']; machine.sp=0xb800
    machine.hl=meta['sections'][0]['address']; machine.bc=0x10fe; machine.a=128; machine.e=0
    machine.ticks_to_stop=budget
    while machine.pc!=endpoint or len(bits)!=len(expected):
        if machine.run()&machine._TICKS_LIMIT_HIT: raise AssertionError('PCM player did not complete two loops')
    if not np.array_equal(np.frombuffer(bits,dtype=np.uint8),expected): raise AssertionError('native PDM mismatch')
    intervals=np.diff(np.asarray(times,dtype=np.int64))
    if not np.array_equal(intervals,np.tile(native_intervals(meta),2)): raise AssertionError(f'native timing mismatch {Counter(intervals)}')
    expected_pages=[s['bank'] for s in meta['sections']]*2+[meta['sections'][0]['bank']]
    if pages!=expected_pages or machine.sp!=0xb800 or machine.a!=error:
        raise AssertionError('paging/stack/accumulator mismatch')
    if bytes(machine.memory[ORIGIN:ORIGIN+len(code)])!=code: raise AssertionError('code/screen changed')
    return dict(complete=True,cycles_verified=2,bits_verified=len(bits),all_pcm_values_exact=True,
        every_pdm_bit_exact=True,accumulator_exact=True,stack_and_code_intact=True,bank_sequence=pages,
        interval_histogram_tstates=dict(sorted(Counter(map(int,intervals)).items())),
        cycle_tstates=int(intervals[:meta['bits_per_cycle']].sum()),pdm_buffer_bytes=0,
        scope='independent Z80; integer/FIFO reference; no ULA or ROM/disk latency')


def fuse_check(fuse,directory,meta,pcm):
    work=directory/'verification-work'; work.mkdir(exist_ok=True)
    oversample=meta['oversample']
    labels=meta['player_labels']; expected,_=reference(pcm,oversample=oversample)
    lines=['base 10','set $r 0','set $bits 0']; widths={}; event_count=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(breakpoint,tag,expressions,after=(),condition='',stop=False):
        nonlocal event_count
        event_count+=1; widths[tag]=len(expressions)
        lines.extend([f'breakpoint {breakpoint}',f'commands {event_count}',f'print {tag}'])
        lines.extend(f'print {x}' for x in expressions); lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition: lines.append(f'condition {event_count} {condition}')
    event(labels['ready'],100,[stamp],['set $r 1'])
    # One port breakpoint covers hundreds of unrolled output instructions.
    event('port write 4350',140,[stamp,'z80:e','z80:d'],['set $bits $bits+1'],condition='$r==1')
    for name,address in labels.items():
        if re.fullmatch(r'page_\d+',name): event(address+2,150,[stamp,'z80:a'])
    event(labels['disk_call'],102,[stamp,'$r'])
    # Fuse completes the instruction at an exit breakpoint. Stop on ADD/RR,
    # not OUT, or its port callback would append an unwanted extra pulse.
    stop_offset=4 if meta.get('steady',False) else 3
    event(labels['out_0_0_0']+stop_offset,200,[stamp],condition=f'$bits=={len(expected)}',stop=True)
    script='\n'.join(lines); (work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
        '--machine','128','--beta128','--debugger-command',script,str((directory/'audiobook-preview.trd').resolve())]
    epoch=time.time()
    result=subprocess.run(command,cwd=fuse.parent,capture_output=True,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
        startupinfo=hidden_startupinfo(),timeout=300)
    trace=result.stdout.decode(errors='replace'); fallback=fuse.parent/'stdout.txt'
    if not re.search(r'^\s*\d+\s*$',trace,re.M) and fallback.exists() and fallback.stat().st_mtime>=epoch-2:
        trace=fallback.read_text(errors='replace')
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(trace.encode(),mtime=0))
    (work/'fuse-stderr.txt').write_bytes(result.stderr)
    if result.returncode!=77: raise AssertionError(f'Fuse did not complete loops: {result.returncode}')
    numbers=(int(s.strip(),0) for s in trace.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=array('I'); values=bytearray(); inputs=bytearray(); pages=[]; reads=[]; ready=[]; ends=[]
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140: times.append(row[0]); values.append(row[1]); inputs.append(row[2])
        elif tag==100: ready.append(row)
        elif tag==200: ends.append(row)
        elif tag==150: pages.append(row)
        elif tag==102: reads.append(row)
    actual=np.frombuffer(values,dtype=np.uint8)
    if len(ready)!=1 or len(ends)!=1 or len(actual)!=len(expected): raise AssertionError('incomplete Fuse PCM')
    if np.any(actual&15) or not np.array_equal((actual>>4)&1,expected): raise AssertionError('Fuse PDM mismatch')
    wanted_pcm=np.r_[np.tile(np.repeat(np.frombuffer(pcm,dtype=np.uint8),oversample),2),pcm[0]]
    if not np.array_equal(np.frombuffer(inputs,dtype=np.uint8),wanted_pcm): raise AssertionError('Fuse PCM read order mismatch')
    expected_pages=[s['bank'] for s in meta['sections']]*2+[meta['sections'][0]['bank']]
    if [meta['sections'][0]['bank']]+[r[1]&7 for r in pages]!=expected_pages: raise AssertionError('wrong Fuse banks')
    if len(reads)!=len(pcm)//256 or any(r[1] for r in reads): raise AssertionError('runtime or missing disk reads')
    timeline=np.asarray(times,dtype=np.int64); timeline-=timeline[0]
    intervals=np.diff(timeline); deterministic=np.tile(native_intervals(meta),2)
    if np.any(intervals<deterministic) or CPU_CLOCK/int(intervals.max())<40000:
        raise AssertionError(f'bad real cadence {Counter(intervals)}')
    (directory/'output-times.u32.gz').write_bytes(gzip.compress(timeline.astype('<u4').tobytes(),mtime=0))
    n=meta['bits_per_cycle']; durations=np.diff(timeline[::n])/CPU_CLOCK
    sample_intervals=np.diff(timeline[::oversample]); rate=2*len(pcm)*CPU_CLOCK/int(timeline[-1])
    return dict(complete=True,cold_boot=True,cycles_verified=2,bits_verified=len(expected),every_pdm_bit_exact=True,
        all_pcm_values_exact=True,bank_sequence=expected_pages,startup_sector_reads=len(reads),runtime_disk_reads=0,
        average_pdm_rate_hz=rate*oversample,average_pcm_rate_hz=rate,pcm_clock_error_percent=(rate/8000-1)*100,
        minimum_instantaneous_pdm_rate_hz=CPU_CLOCK/int(intervals.max()),
        maximum_instantaneous_pdm_rate_hz=CPU_CLOCK/int(intervals.min()),
        interval_histogram_tstates=dict(sorted(Counter(map(int,intervals)).items())),
        pcm_interval_min_tstates=int(sample_intervals.min()),pcm_interval_max_tstates=int(sample_intervals.max()),
        loop_hold_tstates=list(map(int,intervals[n-1::n])),cycle_durations_seconds=durations.tolist(),
        first_out_phase_tstates=int(times[0]%70908),native_tstates_per_cycle=int(deterministic[:n].sum()),
        additional_ula_tstates=int(timeline[-1]-deterministic.sum()),
        trd_sha256=hashlib.sha256((directory/'audiobook-preview.trd').read_bytes()).hexdigest(),
        fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)


def verify(directory,fuse):
    meta=json.loads((directory/'player.json').read_bytes())
    pcm=gzip.decompress((directory/'soundtrack.pcm.gz').read_bytes())
    assert hashlib.sha256(pcm).hexdigest()==meta['pcm_sha256']
    native=native_check((directory/'audiobook-preview.trd').read_bytes(),meta,pcm)
    print(json.dumps(dict(native=native)),flush=True)
    actual=fuse_check(fuse,directory,meta,pcm)
    report=dict(complete=True,native=native,fuse=actual,verification_sources_sha256_lf={
        name:hashlib.sha256(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        for name in ('verify_pcm.py','pcm_player.py')})
    save(directory/'verification.json',report); print(json.dumps(dict(fuse=actual)),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',type=Path); p.add_argument('--fuse',type=Path,required=True)
    args=p.parse_args(); verify(args.directory,args.fuse)
