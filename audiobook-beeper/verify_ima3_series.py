"""Execute complete chained disks; compare each live pulse to its qualified part.

Pulse logging packs the hold duration and bit into one integer, avoiding the
multi-gigabyte verbose trace a full five-part volume would otherwise need.
Disk swaps resume actual predecessor RAM with other banks poisoned; physical
drive state and the user's key press are not emulated by that snapshot test.
"""
from array import array
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

import numpy as np
from z80 import Z80Machine

from verify_direct import reference,intervals
from verify_pcm import save
from smoke_test_fuse import hidden_startupinfo
from probe_reconstruction_error import wav8,filtered
from build_pdm import reconstruct,write_wav
from assess_snr import ratio,FILTER


def native_part(disk,meta,packed):
    pcm,indices,levels,expected=reference(packed,cycles=1,model=meta['model'])
    wanted_count=(len(pcm)-3)*16+15
    m=Z80Machine();m.memory[:]=b'\xa5'*65536
    blob=disk[meta['player_sector']*256:meta['player_sector']*256+23296]
    m.set_memory_block(0x8000,blob[:16384])
    for label,address,count in [('lower_disk',0x4000,28),('upper_disk',0x6000,32)]:
        pos=meta['player_labels'][label];sector=(pos>>8)*16+(pos&15)
        m.set_memory_block(address,disk[sector*256:(sector+count)*256])
    banks={}
    for part in meta['sections']:
        data=bytearray(b'\xa5'*16384)
        data[part['address']-0xc000:]=disk[part['sector']*256:(part['sector']+part['sectors'])*256]
        if part['bank']==7:data[:6912]=blob[16384:]
        if part['bank']==2:m.set_memory_block(part['address']-0x4000,data[part['address']-0xc000:])
        banks[part['bank']]=data
    before=bytes(m.memory[0x4000:0xc000]);bits=bytearray();ticks=array('I');pages=[];checked=0
    budget=int(intervals(meta).sum())+1000000
    def page(bank):
        if pages:
            old=pages[-1];start=meta['resident_reserve'] if old==2 else 0
            assert bytes(m.memory[0xc000+start:])==bytes(banks[old][start:])
        if bank==2:banks[2][:]=m.memory[0x8000:0xc000]
        m.set_memory_block(0xc000,banks[bank]);pages.append(bank)
    def output(port,value):
        nonlocal checked
        if port==0x7ffd:page(value&7);return
        assert port&255==254 and value in (0,16) and not 0x4000<=port<0x8000
        sample,slot=divmod(len(bits),16)
        if slot==4:
            nxt=(sample+1)%len(pcm)
            assert m.ix==int(pcm[nxt])+32768 and m.alt_hl==meta['decoder_rows'][int(indices[nxt])]
            checked+=1
        bits.append(value>>4);ticks.append(budget-m.ticks_to_stop)
    page(0);m.set_output_callback(output);m.pc=meta['player_labels']['ready'];m.sp=0x6000;m.ticks_to_stop=budget
    stop=meta['player_labels']['chain_exit'];m.set_breakpoint(stop)
    while m.pc!=stop:
        if m.run()&m._TICKS_LIMIT_HIT:raise AssertionError('one-pass native timeout')
    assert len(bits)==wanted_count,(len(bits),wanted_count)
    assert np.array_equal(np.frombuffer(bits,'u1'),expected[:wanted_count])
    assert np.array_equal(np.diff(np.asarray(ticks,dtype=np.int64)),intervals(meta)[:wanted_count-1])
    assert pages==[p['bank'] for p in meta['sections']]
    after=bytearray(m.memory[0x4000:0xc000])
    for address in meta['mutable_addresses']:after[address-0x4000]=before[address-0x4000]
    assert after==before
    return dict(complete=True,bits_verified=len(bits),predictor_index_samples_verified=checked,
                every_bit_and_native_hold_exact=True,memory_guards_passed=True,bank_sequence=pages,
                ordinary_tstates=427.375,ordinary_delta_tstates=0,
                discarded_guard_pulses=33,final_guard_pulses_retained=15)


def continuation_snapshot(ram,pc):
    assert len(ram)==49152
    def block(name,data):return name+struct.pack('<I',len(data))+data
    regs=bytearray(37);struct.pack_into('<HHH',regs,18,0x5c3a,0x6000,pc)
    regs[26:29]=bytes([1,1,1]);regs[33]=48
    data=b'ZXST'+bytes([1,5,2,0])+block(b'Z80R',regs)
    data+=block(b'SPCR',struct.pack('<BBBBI',0,31,0,0,0))
    data+=block(b'B128',struct.pack('<IBBBBBB',1,4,0x1c,0,1,0,0))
    banks={5:ram[:16384],2:ram[16384:32768],7:ram[32768:]}
    for bank in range(8):data+=block(b'RAMP',struct.pack('<HB',0,bank)+banks.get(bank,b'\xa5'*16384))
    return data


def fuse_volume(disk_path,volume,out,fuse,*,ffmpeg,snapshot=None,expect_wrong=False):
    out.mkdir(parents=True,exist_ok=True)
    metas=[json.loads(Path(p['metadata']).read_bytes()) for p in volume['parts']]
    labels=volume['controller_labels'];stamp='spectrum:frames*70908+ula:tstates'
    lines=['base 10','set $active 0','set $part 0','set $dump 0','set $last 0']
    widths={};eid=0
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal eid
        eid+=1;widths[tag]=len(expressions)
        lines.extend([f'breakpoint {where}',f'commands {eid}'])
        if tag is not None:lines.append(f'print {tag}')
        lines.extend('print '+expr for expr in expressions);lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if condition:lines.append(f'condition {eid} {condition}')
    for i,meta in enumerate(metas):
        lab=meta['player_labels']
        event(lab['ready'],-100,['$part',stamp,'ula:mem7ffd'],['set $active 1','set $last '+stamp],condition=f'$part=={i} && $active==0')
        event(lab['loading_visible'],-103,['$part',stamp,'[55296]','[55391]'],condition=f'$part=={i} && $active==0')
        event(lab['loading_hidden'],-104,['$part',stamp,'[55296]','[55391]'],condition=f'$part=={i} && $active==0')
        event(lab['load_progress_event'],-105,['$part',f'[{lab["load_progress"]}]'],condition=f'$part=={i} && $active==0')
    for address in sorted({m['player_labels']['chain_exit'] for m in metas}):
        event(address,-110,['$part',stamp],['set $active 0','set $part $part+1'],condition='$active==1')
    # The native verifier checks the exact output opcodes and source values.
    bit='([z80:pc-1]==81 || ([z80:pc-1]==65 && z80:b==16) || ([z80:pc-1]==254 && z80:a==16))'
    event('port write 254',None,[f'({stamp}-$last)*2+{bit}'],['set $last '+stamp],condition='$active==1')
    for address in metas[0]['first_addresses']:
        event(address+20,-121,['z80:hl'],condition='$active==1')
        event(address+23,-120,['z80:ix'],condition='$active==1')
    event(0x3d13,-102,['$active',stamp,'z80:hl','z80:de','z80:b'])
    event(labels['header_accepted'],-130,[stamp,f'[{labels["expected_volume"]}]',f'[{labels["expected_volume"]+1}]'])
    terminal=labels['swap_prompt'] if volume['volume']<volume['total_volumes'] else labels['finished']
    event(labels['wrong_disk_prompt'],-198,[stamp],stop=True)
    event(terminal,-199,['$part',stamp,'ula:mem7ffd'],
          ['set $dump 16384','set z80:pc 16395'])
    event(0x400c,-300,['[$dump]+256*[$dump+1]+65536*[$dump+2]+16777216*[$dump+3]'],
          ['set $dump $dump+4','set z80:pc 16395'],condition='$dump>=16384 && $dump<65536')
    event(0x400c,-301,[],condition='$dump==65536',stop=True)
    # Keep the command below Windows' 32767-character limit.
    abbreviations={'breakpoint ':'br ','commands ':'com ','condition ':'cond ','print ':'pr ','set ':'se ','continue':'co','exit ':'ex '}
    for i,line in enumerate(lines):
        for long,short in abbreviations.items():
            if line.startswith(long):lines[i]=short+line[len(long):];break
    script='\n'.join(lines);(out/'debugger.txt').write_text(script,encoding='utf-8',newline='\n')
    media=['--betadisk',str(disk_path.resolve()),'--snapshot',str(snapshot.resolve())] if snapshot else [str(disk_path.resolve())]
    command=[str(fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions','--speed','10000',
             '--machine','128','--beta128','--debugger-command',script]+media
    assert len(subprocess.list2cmdline(command))<32760
    result=subprocess.run(command,cwd=fuse.parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                          capture_output=True,startupinfo=hidden_startupinfo(),timeout=1200)
    (out/'trace.txt.gz').write_bytes(gzip.compress(result.stdout,compresslevel=1,mtime=0))
    (out/'stderr.txt').write_bytes(result.stderr)
    if result.returncode!=77:raise AssertionError(('Fuse failed',result.returncode,result.stderr[:1000]))
    values=(int(m.group(1),0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',result.stdout))
    pulses=[array('I') for _ in metas];preds=[array('H') for _ in metas];indices=[array('H') for _ in metas]
    ready=[];ends=[];reads=[];shown=[];hidden=[];progress=[];accepted=[];terminal_row=None;ram=bytearray();wrong=False;part=None
    for tag in values:
        # Fuse prints negative event markers as unsigned 32-bit hexadecimal.
        # Payload words remain unsigned (including the captured RAM words).
        if tag>=0xffff0000:tag-=2**32
        if tag>=0:
            assert part is not None;pulses[part].append(tag);continue
        row=[next(values) for _ in range(widths[tag])]
        if tag==-100:part=row[0];ready.append(row)
        elif tag==-110:ends.append(row);part=None
        elif tag==-120:preds[part].append(row[0])
        elif tag==-121:indices[part].append(row[0])
        elif tag==-102:reads.append(row)
        elif tag==-103:shown.append(row)
        elif tag==-104:hidden.append(row)
        elif tag==-105:progress.append(row)
        elif tag==-130:accepted.append(row)
        elif tag==-198:wrong=True
        elif tag==-199:terminal_row=row
        elif tag==-300:ram+=(row[0]&0xffffffff).to_bytes(4,'little')
    if expect_wrong:
        assert wrong and not ready,'wrong disk reached audio'
        report=dict(complete=True,wrong_disk_rejected_before_playback=True)
        save(out/'report.json',report);return report,None
    assert not wrong and terminal_row is not None and terminal_row[0]==len(metas)
    assert len(ready)==len(ends)==len(metas) and len(ram)==49152
    assert all(r[0]==0 for r in reads),'disk call during audio'
    reports=[]
    for i,meta in enumerate(metas):
        selected=Path(meta['selected_source']);packed=gzip.decompress((selected/'soundtrack.ima.gz').read_bytes())
        pcm,idx,_,wanted=reference(packed,cycles=1,model=meta['model'])
        pulse=np.asarray(pulses[i],dtype=np.int64);bits=(pulse&1).astype('u1')
        count=(len(pcm)-3)*16+15
        assert len(bits)==count and np.array_equal(bits,wanted[:count]),('pulse mismatch',i,len(bits),count)
        times=np.cumsum(pulse>>1);times-=times[0]
        # Preserve actual disk timing for reproducible boundary-noise analysis.
        (out/f'part-{i+1:02d}-times.u32.gz').write_bytes(gzip.compress(times.astype('<u4').tobytes(),mtime=0))
        old_times=np.frombuffer(gzip.decompress((selected/'output-times.u32.gz').read_bytes()),'<u4').astype(np.int64)[:count]
        delta=times-(old_times-old_times[0])
        # HALT can enter the ROM IRQ at one of four T-state offsets. Cold
        # loading and an automatic transition need not select the same one.
        # Verify the bounded phase difference AND measure this actual waveform.
        assert np.max(np.abs(delta))<=8,('output clock changed',i,
            int(np.flatnonzero(delta)[0]),delta[:32].tolist(),int(delta.min()),int(delta.max()))
        assert np.array_equal(np.asarray(preds[i]),pcm[1:1+len(preds[i])].astype(np.int32)+32768)
        assert np.array_equal(np.asarray(indices[i]),np.asarray(meta['decoder_rows'])[idx[1:1+len(indices[i])]])
        assert [r[1] for r in progress if r[0]==i]==list(range(1,33))
        assert [r[2:] for r in shown if r[0]==i]==[[71,71]]
        assert [r[2:] for r in hidden if r[0]==i]==[[0,0]]
        source=wav8(selected/'source-preview.wav');assert np.all(source[-128:]==128)
        # Exclude the final guard pulse's interval and retain all
        # source-bearing intervals in the same listening-filter measurement.
        edges=times;output=filtered(reconstruct(bits[:-1],edges),ffmpeg)
        period=3546900/8000;segments=int(np.ceil(edges[-1]/period))
        fixed_edges=np.r_[np.arange(segments)*period,edges[-1]]
        values=np.pad(source/256,(0,max(0,segments-len(source))),constant_values=.5)[:segments]
        fixed=filtered(reconstruct(values,fixed_edges),ffmpeg)
        edge=min(4410,len(output)//10);window=slice(edge,-edge if edge else None)
        score=ratio(fixed[window],output[window]-fixed[window]) if np.any(source!=128) else None
        rate=((count-1)/16)*3546900/edges[-1];speed=100*(rate/8000-1)
        assert abs(speed)<=2,('playback speed',speed)
        write_wav(out/f'part-{i+1:02d}-output.wav',output)
        reports.append(dict(part=i+1,bits_verified=count,predictor_index_samples_verified=len(preds[i]),
                            every_live_bit_identical=True,
                            timing_delta_from_qualified_part_tstates=[int(delta.min()),int(delta.max())],
                            fixed_clock_snr_db=score,source_silent=not np.any(source!=128),
                            filter=FILTER,speed_error_percent=speed,
                            start_tstates=ready[i][1],stop_tstates=ends[i][1]))
    assert [r[1]+256*r[2] for r in accepted]==[volume['volume']]*(len(metas)+1)
    (out/'terminal.ram.gz').write_bytes(gzip.compress(ram,mtime=0))
    gaps=[(ready[i+1][1]-ends[i][1])/3546900 for i in range(len(metas)-1)]
    assert ready[0][1]/3546900<=60 and all(g<=60 for g in gaps),'preparation exceeds 60 seconds'
    report=dict(complete=True,volume=volume['volume'],from_actual_predecessor_ram=snapshot is not None,
                parts=reports,automatic_part_transitions=max(0,len(metas)-1),between_part_pause_seconds=gaps,
                runtime_disk_reads_during_audio=0,total_sector_calls=len(reads),loading_ui_checked=True,
                first_ready_seconds=ready[0][1]/3546900,
                ended_at='swap_prompt' if volume['volume']<volume['total_volumes'] else 'end_of_audio',
                terminal_ram_sha256=hashlib.sha256(ram).hexdigest(),trd_sha256=hashlib.sha256(disk_path.read_bytes()).hexdigest(),
                physical_hardware_tested=False)
    save(out/'report.json',report);return report,bytes(ram)


def verify_series(out,fuse,ffmpeg):
    volumes=json.loads((out/'volumes.json').read_bytes());report=dict(complete=False,volumes=[],continuations=[])
    verification=out/'verification';verification.mkdir(exist_ok=True);previous=None
    for volume in volumes:
        disk=(out/volume['file']).read_bytes()
        assert hashlib.sha256(disk).hexdigest()==volume['trd_sha256']
        for i,record in enumerate(volume['parts'],1):
            meta=json.loads(Path(record['metadata']).read_bytes())
            packed=gzip.decompress((Path(record['selected'])/'soundtrack.ima.gz').read_bytes())
            result=native_part(disk,meta,packed);save(verification/f'native-{volume["volume"]:04d}-{i:02d}.json',result)
        cold,ram=fuse_volume(out/volume['file'],volume,verification/f'cold-{volume["volume"]:04d}',fuse,ffmpeg=ffmpeg)
        report['volumes'].append(cold)
        if previous is not None:
            snap=verification/f'resume-{volume["volume"]:04d}.szx'
            snap.write_bytes(continuation_snapshot(previous,previous_labels['key_accepted']))
            wrong,_=fuse_volume(out/previous_volume['file'],volume,verification/f'wrong-{volume["volume"]:04d}',fuse,
                                ffmpeg=ffmpeg,snapshot=snap,expect_wrong=True)
            resumed,ram=fuse_volume(out/volume['file'],volume,verification/f'resumed-{volume["volume"]:04d}',fuse,
                                   ffmpeg=ffmpeg,snapshot=snap)
            resumed['wrong_disk_check']=wrong
            report['continuations'].append(resumed)
        previous=ram;previous_labels=volume['controller_labels'];previous_volume=volume
        save(verification/'report.json',report)
    report['complete']=True;save(verification/'report.json',report)
    return report


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path)
    parser.add_argument('--fuse',type=Path,required=True)
    parser.add_argument('--ffmpeg',required=True)
    args=parser.parse_args()
    print(json.dumps(verify_series(args.directory.resolve(),args.fuse,args.ffmpeg)))
