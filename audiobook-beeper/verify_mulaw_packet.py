"""Independent packet-table arithmetic and full native/cold-Fuse execution."""
from fractions import Fraction
import gzip
import hashlib
import re
import subprocess
from collections import Counter
import numpy as np
from g711_codec import decode_table
from mulaw_packet import CPU,tables,reference,intervals
from verify_pdm import extract_player,save
from smoke_test_fuse import hidden_startupinfo


def rational_check(model):
    words,nxt=tables(model)
    for code,value in enumerate(decode_table('mulaw')):
        x=Fraction(int(value)+32768,65536)
        for state in range(32):
            q=Fraction(state//2-8,8);recent=Fraction(2*(state%2)-1,2)*Fraction(model['extent']);word=0
            for hold in model['holds']:
                weight=Fraction(hold*16,sum(model['holds']))
                u=x+q/weight+Fraction(model['beta'])*recent;bit=int(u>=Fraction(1,2))
                recent=u-bit;q+=weight*(x-bit);word=word*2+bit
            qcode=max(model['q_clip'][0],min(model['q_clip'][1],(q*8+Fraction(17,2)).__floor__()))
            assert word==words[code,state] and qcode*2+int(recent>=0)==nxt[code,state],(code,state)
    return dict(complete=True,g711_codes=256,feedback_states=32,exact_fraction_transitions=8192)


def sample_at(i,meta):
    cycle,local=divmod(i,meta['outputs_per_cycle'])
    at=(meta['pcm_samples']-2)*16+1;pairs=meta['loop_idle_pairs']
    if at<=local<at+pairs*2:return None
    if local>=at:local-=pairs*2
    return cycle*meta['pcm_samples']+local//16,local%16


def native_check(disk,meta,payload):
    from z80 import Z80Machine
    expected,after=reference(payload,meta['model'],idle_pairs=meta['loop_idle_pairs'])
    timing=intervals(meta);budget=int(timing.sum()*2+1000000)
    blob=extract_player(disk);banks={b:bytearray([0xa5])*16384 for b in range(8)}
    banks[2][:]=blob[:16384];banks[7][:6912]=blob[16384:]
    for region in meta['table_regions']:
        begin=region['address']-0x4000
        banks[5][begin:begin+region['sectors']*256]=disk[region['sector']*256:(region['sector']+region['sectors'])*256]
    offset=0
    for s in meta['sections']:
        data=disk[s['sector']*256:(s['sector']+s['sectors'])*256]
        assert data==payload[offset:offset+s['bytes']]
        begin=s['address']-0xc000;banks[s['bank']][begin:begin+s['bytes']]=data;offset+=s['bytes']
    m=Z80Machine();m.memory[:]=bytes([0xa5])*65536
    m.set_memory_block(0x4000,banks[5]);m.set_memory_block(0x8000,banks[2])
    before=bytes(m.memory[0x4000:0xc000]);pages=[];times=[];bits=bytearray();checks=0
    first={a+2 for a in meta['first_addresses']}
    def page(bank):
        if pages:assert bytes(m.memory[0xc000:])==bytes(banks[pages[-1]]),'paged RAM changed'
        m.set_memory_block(0xc000,banks[bank]);pages.append(bank)
    def output(port,value):
        nonlocal checks
        if port==0xfe:
            i=len(bits);assert value in (0,16) and value//16==expected[i],('bit',i,value,expected[i])
            if m.pc in first:
                sample,slot=sample_at(i,meta);assert slot==0
                assert m.d==16 and m.e%4==0 and meta['feedback_states'][m.e//4]==after[sample],('feedback',i,m.e,after[sample])
                checks+=1
            bits.append(value//16);times.append(budget-m.ticks_to_stop)
            if len(bits)==len(expected):m.set_breakpoint(m.pc)
        elif port==0x7ffd:
            assert 24<=value<=31;page(value&7)
        else:raise AssertionError(('unexpected port',hex(port),value,hex(m.pc)))
    page(meta['sections'][0]['bank']);m.set_output_callback(output);m.pc=meta['player_labels']['ready'];m.sp=0x6000;m.ticks_to_stop=budget
    while len(bits)<len(expected):
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError(('timeout',hex(m.pc),len(bits)))
    assert checks==meta['pcm_samples']*2+1,('feedback check count',checks)
    actual=np.diff(np.asarray(times));wanted=np.tile(timing,2);wrong=np.flatnonzero(actual!=wanted)
    assert not len(wrong),('timing',wrong[:20],actual[wrong[:20]],wanted[wrong[:20]])
    assert bytes(m.memory[0x4000:0xc000])==before,'fixed RAM changed during playback'
    assert bytes(m.memory[0xc000:])==bytes(banks[pages[-1]])
    assert pages==[s['bank'] for s in meta['sections']]*2+[meta['sections'][0]['bank']]
    return dict(complete=True,cycles_verified=2,bits_verified=len(bits),every_pdm_bit_exact=True,
        every_packet_feedback_exact=True,packet_feedback_checks=checks,memory_guards_passed=True,
        every_output_port_uncontended=True,cycle_tstates=int(timing.sum()),bank_sequence=pages,
        interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
        scope='Native instruction-table T-states, excluding ULA waits, ROM and disk latency')


def fuse_check(fuse,out,meta,payload):
    expected,after=reference(payload,meta['model'],idle_pairs=meta['loop_idle_pairs'])
    labels=meta['player_labels'];work=out/'verification-work';work.mkdir(exist_ok=True)
    lines=['base 10','set $r 0','set $bits 0'];widths={};eid=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal eid
        eid+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {eid}',f'print {tag}'])
        lines.extend('print '+s for s in expressions);lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition:lines.append(f'condition {eid} {condition}')
    event(labels['ready'],100,[stamp],['set $r 1'])
    event('port write 254',140,[stamp,'z80:pc','z80:d','z80:e'],['set $bits $bits+1'],condition='$r==1')
    # The port callback reports PC after the instruction; distinguish ED51
    # from ED71 directly and read the D/E state without fitting a bitstream.
    event('port write 254',200,[stamp],condition=f'$bits>={len(expected)}',stop=True)
    for i in range(len(meta['sections'])):event(labels[f'page_{i}']+2,150,['z80:a','ula:mem7ffd','ula:mem1ffd'])
    event(labels['disk_call'],102,['$r',stamp,'z80:sp','ula:mem7ffd'])
    for name,tag in [('loading_visible',103),('loading_hidden',104)]:
        event(labels[name],tag,[stamp,'ula:mem7ffd']+[f'[{0xd800+i}]' for i in range(96)])
    event(labels['load_progress_event'],105,[stamp,'ula:mem7ffd',f'[{labels["load_progress"]}]']+[f'[{0xd8a0+i}]' for i in range(32)])
    script='\n'.join(lines);(work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    run=subprocess.run([str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
        '--machine','128','--beta128','--debugger-command',script,str((out/'audiobook-preview.trd').resolve())],
        cwd=fuse.parent,capture_output=True,startupinfo=hidden_startupinfo(),timeout=600)
    (work/'fuse-trace.txt.gz').write_bytes(gzip.compress(run.stdout,compresslevel=1,mtime=0));(work/'fuse-stderr.txt').write_bytes(run.stderr)
    assert run.returncode==77,('Fuse failed',run.returncode,run.stderr[:1000])
    numbers=iter(int(s.strip(),0) for s in run.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    times=[];pages=[];reads=[];progress=[];shown=[];hidden=[];ready=[];ends=[];checks=0
    blob=extract_player((out/'audiobook-preview.trd').read_bytes())
    first=set(meta['first_addresses'])
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140:
            tick,pc,d,e=row;i=len(times);pc-=2
            assert blob[pc-0x8000]==0xed and blob[pc-0x8000+1] in (0x51,0x71),(i,hex(pc))
            bit=d//16 if blob[pc-0x8000+1]==0x51 else 0
            assert bit==expected[i] and d==16,('Fuse bit',i,row)
            if pc in first:
                sample,slot=sample_at(i,meta);assert slot==0
                assert e%4==0 and meta['feedback_states'][e//4]==after[sample],('Fuse feedback',i,row)
                checks+=1
            times.append(tick)
        elif tag==150:pages.append(row)
        elif tag==102:reads.append(row)
        elif tag==103:shown.append(row)
        elif tag==104:hidden.append(row)
        elif tag==105:progress.append(row)
        elif tag==100:ready.append(row)
        elif tag==200:ends.append(row)
    assert len(times)==len(expected) and checks==len(payload)*2+1 and len(ready)==len(ends)==1
    wanted=[s['bank']+24 for s in meta['sections'][1:]+meta['sections'][:1]]*2
    assert len(pages)==len(wanted) and all(row[0]==row[1]==b for row,b in zip(pages,wanted))
    assert len({row[2] for row in pages})==1 and len(reads)==meta['playback_preload_sector_reads']
    assert all(row[0]==0 and 0x5f00<=row[2]<0x6000 and row[3]&8 for row in reads)
    assert len(shown)==len(hidden)==1 and shown[0][1]==hidden[0][1]==31
    assert shown[0][2:]==[0x47]*96 and hidden[0][2:]==[0]*96
    assert all(shown[0][0]<row[1]<hidden[0][0]<ready[0][0] for row in reads)
    assert len(progress)==32
    for i,row in enumerate(progress,1):
        assert row[1:3]==[31,i] and row[3:]==[0x20]*i+[0x08]*(32-i)
        assert shown[0][0]<row[0]<hidden[0][0]
    times=np.asarray(times,dtype=np.int64);times-=times[0]
    actual=np.diff(times);native=np.tile(intervals(meta),2);assert np.all(actual>=native)
    n=meta['outputs_per_cycle'];periods=np.diff(times[::n]);rate=2*len(payload)*CPU/times[-1]
    assert abs(rate/8000-1)<=.02,('speed outside two percent',rate)
    (out/'output-times.u32.gz').write_bytes(gzip.compress(times.astype('<u4').tobytes(),mtime=0))
    return dict(complete=True,cold_boot=True,machine='Spectrum128 +Beta128',cycles_verified=2,
        every_pdm_bit_exact=True,every_packet_feedback_exact=True,packet_feedback_checks=checks,bits_verified=len(times),
        paging_latches_verified=True,loading_message_and_32_progress_steps_verified=True,
        startup_sector_reads=len(reads),runtime_disk_reads=0,loading_seconds=(hidden[0][0]-shown[0][0])/CPU,
        average_pcm_rate_hz=float(rate),signal_pdm_rate_hz=float(rate*16),
        average_output_rate_including_guard_hz=float(2*n*CPU/times[-1]),speed_error_percent=float((rate/8000-1)*100),
        cycle_durations_seconds=(periods/CPU).tolist(),cycle_phase_deltas_tstates=(periods%70908).tolist(),
        additional_ula_tstates=int(actual.sum()-native.sum()),
        interval_histogram_tstates=dict(sorted(Counter(map(int,actual)).items())),
        trd_sha256=hashlib.sha256((out/'audiobook-preview.trd').read_bytes()).hexdigest(),
        fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)
