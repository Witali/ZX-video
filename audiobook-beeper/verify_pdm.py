"""Independent all-bit Z80 checking and complete cold Fuse port-FE timing."""
from __future__ import annotations

import argparse
from array import array
from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time

import numpy as np
from pdm_player import ORIGIN, CPU_CLOCK, BANK_BYTES, BIT_TSTATES
from smoke_test_fuse import hidden_startupinfo


def save(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')


def extract_player(disk):
    for i in range(128):
        entry=disk[i*16:i*16+16]
        if entry[:8]==b'PLAYER  ':
            start=(entry[15]*16+entry[14])*256
            return disk[start:start+int.from_bytes(entry[11:13],'little')]
    raise ValueError('PLAYER.C missing')


def native_check(disk,metadata,packed):
    from z80 import Z80Machine
    m=Z80Machine(); m.memory[:]=b'\xa5'*65536
    code=extract_player(disk); m.set_memory_block(ORIGIN,code)
    labels=metadata['player_labels']; writes=bytearray(); stamps=array('I'); pages=[]
    budget=100_000_000
    def output(port,value):
        if port==0x7ffd:
            bank=value&7; pages.append(bank)
            i=next(i for i,s in enumerate(metadata['sections']) if s['bank']==bank)
            s=metadata['sections'][i]; chunk=packed[i*BANK_BYTES:i*BANK_BYTES+s['bytes']]
            m.set_memory_block(0xc000,b'\xa5'*(s['address']-0xc000)+chunk)
        elif port in (0xfe,0x10fe) and value in (0,16):
            writes.append(value>>4); stamps.append(budget-m.ticks_to_stop)
        else: raise AssertionError(f'unexpected playback port/value {port:04x}/{value}')
    m.set_output_callback(output)
    output(0x7ffd,0x10|metadata['sections'][0]['bank'])
    m.hl=metadata['sections'][0]['address']; m.d=packed[0]; m.bc=0x7ffd
    m.sp=0xb800; m.pc=labels['playback']; m.set_breakpoint(labels['finished']); m.ticks_to_stop=budget
    while m.pc!=labels['finished']:
        if m.run()&m._TICKS_LIMIT_HIT: raise AssertionError('native PDM did not finish')
    expected=np.unpackbits(np.frombuffer(packed,dtype=np.uint8))
    if len(writes)!=len(expected)+1 or not np.array_equal(np.frombuffer(writes[:-1],dtype=np.uint8),expected):
        raise AssertionError('native bitstream mismatch')
    intervals=np.diff(np.array(stamps,dtype=np.int64))
    if np.any(intervals!=BIT_TSTATES): raise AssertionError(f'nonuniform native intervals {Counter(intervals)}')
    if writes[-1] or m.sp!=0xb800 or bytes(m.memory[ORIGIN:ORIGIN+len(code)])!=code:
        raise AssertionError('EOF/stack/code guard failed')
    if pages!=[s['bank'] for s in metadata['sections']]: raise AssertionError('bank sequence differs')
    return dict(complete=True,bits=len(expected),every_bit_exact=True,final_hold_tstates=int(intervals[-1]),
        interval_tstates=BIT_TSTATES,interval_count=len(intervals),bank_sequence=pages,eof_mutes=True,
        stack_and_code_intact=True,scope='independent Z80 core; excludes ULA and disk')


def fuse_check(fuse,directory,metadata,packed):
    labels=metadata['player_labels']; work=directory/'verification-work'; work.mkdir(exist_ok=True)
    lines=['base 10','set $r 0']; widths={}; event_count=0
    stamp='spectrum:frames*70908+ula:tstates'
    def event(address,tag,expressions,after=(),stop=False):
        nonlocal event_count
        event_count+=1; widths[tag]=len(expressions)
        lines.extend([f'breakpoint {address}',f'commands {event_count}',f'print {tag}'])
        lines.extend(f'print {x}' for x in expressions); lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
    event(labels['ready'],100,[stamp],['set $r 1'])
    for name in metadata['output_labels']: event(labels[name]+2,140,[stamp,'z80:a'])
    for name,address in labels.items():
        if name.startswith('page_'): event(address+2,150,[stamp,'z80:'+metadata['paging_value_register']])
    event(labels['disk_call'],102,[stamp,'$r'])
    event(labels['finished'],200,[stamp,'z80:a'],stop=True)
    script='\n'.join(lines)
    (work/'fuse-debugger.txt').write_text(script,encoding='utf-8',newline='\n')
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
    if result.returncode!=77: raise AssertionError(f'Fuse failed to reach EOF: {result.returncode}')
    numbers=(int(s.strip(),0) for s in trace.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip()))
    stamps=array('I'); values=bytearray(); pages=[]; reads=[]; ready=[]; ends=[]
    for tag in numbers:
        row=[next(numbers) for _ in range(widths[tag])]
        if tag==140: stamps.append(row[0]); values.append(row[1])
        elif tag==100: ready.append(row)
        elif tag==200: ends.append(row)
        elif tag==150: pages.append(row)
        elif tag==102: reads.append(row)
    expected=np.unpackbits(np.frombuffer(packed,dtype=np.uint8))*16
    if len(ready)!=1 or len(ends)!=1 or len(values)!=len(expected): raise AssertionError('incomplete Fuse PDM')
    if not np.array_equal(np.frombuffer(values,dtype=np.uint8),expected): raise AssertionError('Fuse bitstream mismatch')
    if ends[0][1]!=0 or any(row[1] for row in reads): raise AssertionError('EOF mute or runtime disk access failed')
    if [row[1]&7 for row in pages]!=[s['bank'] for s in metadata['sections'][1:]]:
        raise AssertionError('Fuse bank changes differ')
    timeline=np.r_[np.array(stamps,dtype=np.int64),ends[0][0]]
    timeline-=timeline[0]
    intervals=np.diff(timeline)
    if np.any(intervals<BIT_TSTATES) or CPU_CLOCK/int(intervals.max())<40000:
        raise AssertionError(f'PDM cadence below 40 kHz: {Counter(intervals)}')
    (directory/'output-times.u32.gz').write_bytes(gzip.compress(timeline.astype('<u4').tobytes(),mtime=0))
    return dict(complete=True,cold_boot=True,bits=len(expected),every_bit_exact=True,eof_mutes=True,
        startup_sector_reads=len(reads),runtime_disk_reads=0,bank_sequence=[metadata['sections'][0]['bank']]+[r[1]&7 for r in pages],
        interval_histogram_tstates={str(k):v for k,v in sorted(Counter(map(int,intervals)).items())},
        minimum_instantaneous_bit_rate_hz=CPU_CLOCK/int(intervals.max()),
        maximum_instantaneous_bit_rate_hz=CPU_CLOCK/int(intervals.min()),
        average_bit_rate_hz=len(expected)*CPU_CLOCK/int(timeline[-1]),
        first_out_phase_tstates=int(stamps[0]%70908),duration_seconds=int(timeline[-1])/CPU_CLOCK,
        final_hold_tstates=int(intervals[-1]),trd_sha256=hashlib.sha256((directory/'audiobook-preview.trd').read_bytes()).hexdigest(),
        fuse_sha256=hashlib.sha256(fuse.read_bytes()).hexdigest(),physical_hardware_tested=False)


def verify(directory,fuse):
    meta=json.loads((directory/'player.json').read_bytes())
    packed=gzip.decompress((directory/'soundtrack.pdm.gz').read_bytes())
    if hashlib.sha256(packed).hexdigest()!=meta['packed_sha256']: raise AssertionError('PDM hash changed')
    native=native_check((directory/'audiobook-preview.trd').read_bytes(),meta,packed)
    print(json.dumps(dict(native=native)),flush=True)
    actual=fuse_check(fuse,directory,meta,packed)
    report=dict(complete=True,native=native,fuse=actual,verification_sources_sha256_lf={
        name:hashlib.sha256(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')).hexdigest()
        for name in ('verify_pdm.py','pdm_player.py')})
    save(directory/'verification.json',report)
    print(json.dumps(dict(fuse=actual)),flush=True)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',type=Path)
    p.add_argument('--fuse',type=Path,required=True); args=p.parse_args(); verify(args.directory,args.fuse)
