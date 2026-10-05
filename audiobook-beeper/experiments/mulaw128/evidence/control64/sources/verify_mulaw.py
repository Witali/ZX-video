"""Independent complete mu-law byte/level/bit/timing checks, including cold Fuse."""
import gzip
import hashlib
import re
import subprocess
from collections import Counter

import numpy as np
from g711_codec import decode
from mulaw_player import CPU, intervals
from verify_pdm import extract_player, save
from smoke_test_fuse import hidden_startupinfo


def reference(payload):
    levels = decode(payload, 'mulaw').astype(np.int64)+32768
    targets = np.r_[np.tile(np.repeat(levels, 8), 2), levels[0]]
    # Independent cumulative-area recurrence, not emulation of ADD/SBC.
    area = 32768+np.cumsum(targets)
    bits = np.diff(np.r_[0, area//65536]).astype('u1')
    return targets, bits, area & 65535


def native_check(disk, meta, payload):
    from z80 import Z80Machine
    m=Z80Machine(); m.memory[:]=bytes([0xa5])*65536
    code=extract_player(disk); m.set_memory_block(0x8000,code)
    banks={b:bytearray([0xa5])*16384 for b in range(8)}
    banks[2][:2048]=code[:2048]
    banks[7][:6912]=code[2048:]
    offset=0
    for s in meta['sections']:
        begin=s['address']-0xc000
        banks[s['bank']][begin:begin+s['bytes']]=payload[offset:offset+s['bytes']]
        offset+=s['bytes']
    m.set_memory_block(0x4000,banks[5]); m.set_memory_block(0x8000,banks[2])
    before=bytes(m.memory[0x4000:0xc000]); pages=[]; times=[]; bits=bytearray()
    targets, expected, residual=reference(payload)
    budget=meta['deterministic_cycle_tstates']*2+1000000
    current=None
    def page(bank):
        nonlocal current
        if current is not None:
            begin=2048 if current==2 else 0
            assert bytes(m.memory[0xc000+begin:])==bytes(banks[current][begin:]), 'paged RAM modified'
        if bank==2: banks[2][:2048]=m.memory[0x8000:0x8800]
        m.set_memory_block(0xc000,banks[bank]); pages.append(bank); current=bank
    def output(port, value):
        if port==0x10fe:
            i=len(bits)
            assert value in (0,16) and value//16==expected[i], ('bit', i, value)
            assert m.de==targets[i] and m.hl==residual[i], ('decoded level/state',i)
            bits.append(value//16); times.append(budget-m.ticks_to_stop)
            if len(bits)==len(expected): m.set_breakpoint(m.pc)
        elif port==0x7ffd:
            assert 24<=value<=31; page(value&7)
        else: raise AssertionError(('unexpected port',port,value))
    page(0); m.set_output_callback(output); m.pc=meta['player_labels']['ready']; m.ticks_to_stop=budget
    while len(bits)<len(expected):
        if m.run()&m._TICKS_LIMIT_HIT: raise AssertionError(('timeout',hex(m.pc),len(bits)))
    actual=np.diff(np.asarray(times,dtype=np.int64)); wanted=np.tile(intervals(meta),2)
    wrong=np.flatnonzero(actual!=wanted)
    assert not len(wrong), ('timing',wrong[:10],actual[wrong[:10]],wanted[wrong[:10]])
    assert pages==[s['bank'] for s in meta['sections']]*2+[0]
    after=bytearray(m.memory[0x4000:0xc000])
    for a in (meta['player_labels']['end_page_compare']+1,0x87fe,0x87ff): after[a-0x4000]=before[a-0x4000]
    assert after==before, 'fixed RAM modified outside two-byte staging area and terminal operand'
    assert m.sp==0x8800
    return dict(complete=True,cycles_verified=2,bits_verified=len(bits),every_pdm_bit_exact=True,
                every_decoded_level_and_error_exact=True,memory_guards_passed=True,
                cycle_tstates=int(wanted[:len(payload)*8].sum()),bank_sequence=pages,
                interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
                scope='Continuous native Z80; excludes ULA waits, TR-DOS and physical disk latency')


def fuse_check(fuse, out, meta, payload):
    work=out/'verification-work';work.mkdir(exist_ok=True)
    targets,expected,residual=reference(payload); labels=meta['player_labels']
    lines=['base 10','set $r 0','set $bits 0'];widths={}; eid=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal eid
        eid+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {eid}',f'print {tag}'])
        lines.extend('print '+s for s in expressions); lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition:lines.append(f'condition {eid} {condition}')
    event(labels['ready'],100,[stamp],['set $r 1'])
    event('port write 4350',140,[stamp,'z80:a','z80:de','z80:hl'],['set $bits $bits+1'],condition='$r==1')
    event(labels['out_0']+2,200,[stamp,'z80:sp'],condition=f'$bits>={len(expected)}',stop=True)
    for i in range(len(meta['sections'])):
        event(labels[f'page_{i}']+2,150,['z80:a','ula:mem7ffd','ula:mem1ffd'])
    event(labels['disk_call'],102,['$r',stamp,'z80:sp','ula:mem7ffd'])
    for name,tag in [('loading_visible',103),('loading_hidden',104)]:
        event(labels[name],tag,[stamp,'ula:mem7ffd']+[f'[{0xd800+i}]' for i in range(96)])
    event(labels['load_progress_event'],105,[stamp,'ula:mem7ffd',f'[{labels["load_progress"]}]']+[f'[{0xd8a0+i}]' for i in range(32)])
    script='\n'.join(lines);(work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    run=subprocess.run([str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())],
        cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=600)
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(run.stdout,compresslevel=1,mtime=0))
    (work/'fuse-stderr.txt').write_bytes(run.stderr)
    assert run.returncode==77, ('Fuse failed',run.returncode,run.stderr[:1000])
    numbers=iter(int(s.strip(),0) for s in run.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=[]; pages=[]; reads=[]; progress=[]; shown=[]; hidden=[]; ready=[]; ends=[]
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140:
            i=len(times);tick,a,de,hl=row
            assert a in (0,16) and a//16==expected[i] and de==targets[i] and hl==residual[i], ('Fuse data',i,row)
            times.append(tick)
        elif tag==150:pages.append(row)
        elif tag==102:reads.append(row)
        elif tag==103:shown.append(row)
        elif tag==104:hidden.append(row)
        elif tag==105:progress.append(row)
        elif tag==100:ready.append(row)
        elif tag==200:ends.append(row)
    assert len(times)==len(expected) and len(ready)==len(ends)==1 and ends[0][1]==0x8800
    wanted=[s['bank']+24 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    assert len(pages)==len(wanted) and all(row[0]==row[1]==b for row,b in zip(pages,wanted))
    assert len({row[2] for row in pages})==1
    assert len(reads)==meta['playback_preload_sector_reads']
    assert all(row[0]==0 and 0x5f00<=row[2]<0x6000 and row[3]&8 for row in reads)
    assert len(shown)==len(hidden)==1 and shown[0][1]==hidden[0][1]==31
    assert shown[0][2:]==[0x47]*96 and hidden[0][2:]==[0]*96
    assert all(shown[0][0]<row[1]<hidden[0][0]<ready[0][0] for row in reads)
    assert len(progress)==32
    for i,row in enumerate(progress,1):
        assert row[1:3]==[31,i] and row[3:]==[0x20]*i+[0x08]*(32-i)
        assert shown[0][0]<row[0]<hidden[0][0]
    assert reads[-1][1]<progress[-1][0]
    times=np.asarray(times,dtype=np.int64);times-=times[0]
    actual=np.diff(times);native=np.tile(intervals(meta),2)
    assert np.all(actual>=native)
    n=meta['outputs_per_cycle'];rate=2*len(payload)*CPU/times[-1]
    assert abs(rate/8000-1)<=.02, ('speed outside two percent',rate)
    (out/'output-times.u32.gz').write_bytes(gzip.compress(times.astype('<u4').tobytes(),mtime=0))
    return dict(complete=True,cold_boot=True,machine='Spectrum 128 + Beta 128',cycles_verified=2,
        every_pdm_bit_exact=True,every_decoded_level_and_error_exact=True,bits_verified=len(times),
        paging_latches_verified=True,loading_message_and_32_progress_steps_verified=True,
        startup_sector_reads=len(reads),runtime_disk_reads=0,
        loading_seconds=(hidden[0][0]-shown[0][0])/CPU,
        average_pcm_rate_hz=float(rate),average_pdm_rate_hz=float(rate*8),
        speed_error_percent=float((rate/8000-1)*100),
        cycle_durations_seconds=(np.diff(times[::n])/CPU).tolist(),
        additional_ula_tstates=int(actual.sum()-native.sum()),
        interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
        fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)
