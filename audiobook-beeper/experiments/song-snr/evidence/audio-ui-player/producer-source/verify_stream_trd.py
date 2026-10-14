"""Verify complete continuous bank playback and explicit insufficient-RAM refills."""
from array import array
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
from z80 import Z80Machine

from ram_cache import PROFILES
from ram_machine import MemoryMachine
from verify_direct import reference
from verify_pcm import save


def fuse_check(disk_path,meta,packed,profile,out,fuse,*,captured=False,capture_ui=False):
    """Cold-boot the actual TRD; check every source-bearing pulse and state.

    Native holds are separately exact. These timestamps include actual ULA,
    TR-DOS ROM and emulated floppy latency; reload gaps are never silently
    included in a continuous sample-rate estimate or dropped from the trace.
    """
    import os
    import re
    import subprocess
    from smoke_test_fuse import hidden_startupinfo
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    labels=meta['player_labels'];cpu=PROFILES[profile]['cpu'];field=PROFILES[profile]['field']
    ui_enabled=bool(meta.get('audio_progress_ui'))
    if capture_ui and (not ui_enabled or profile not in ('pentagon512','pentagon1024')):
        raise ValueError('Full live UI capture requires an enabled Pentagon UI disk')
    # Observe the rendered control bytes while physical bank7 is mapped.
    # Other cover pixels are kept from the exact independently loaded TRD;
    # PNG provenance explicitly distinguishes this from a full-screen dump.
    ui_addresses=([0xD08B+row*256+column for row in range(8) for column in range(10)]+
                  list(range(0xDA8B,0xDA95))+list(range(0xDAC0,0xDAE0)))
    final_ui_addresses=([0xD080+row*256+column for row in range(8) for column in range(32)]+
                        list(range(0xDA80,0xDAA0))+list(range(0xDAC0,0xDAE0)))
    stamp=f'spectrum:frames*{field}+ula:tstates'
    lines=['base 10','set $active 0','set $last 0','set $pulse 0','set $batch 0']
    widths={};eid=0
    def event(where,tag,expressions,after=(),condition='',stop=False):
        nonlocal eid
        eid+=1;widths[tag]=len(expressions)
        lines.extend([f'br {where}',f'com {eid}'])
        if tag is not None:lines.append(f'pr {tag}')
        lines.extend('pr '+x for x in expressions);lines.extend(after)
        lines.extend(['ex 77' if stop else 'co','end'])
        if condition:lines.append(f'cond {eid} {condition}')
    event(labels['ready'],-100,[stamp,'ula:mem7ffd'],['se $active 1','se $last '+stamp],condition='$active==0')
    event(labels['stream_reload_begin'],-101,[stamp,'$pulse'],['se $active 0','se $batch $batch+1'],condition='$active==1')
    event(labels['stream_reload_end'],-103,[stamp,'$pulse'],['se $active 1'],condition='$active==0')
    event(labels['cover_visible'],-104,[stamp,'ula:mem7ffd','[49152]','[55199]'])
    event(labels['cache_progress_event'],-105,['$batch','[23416]'],condition='$active==0')
    event(0x3d13,-106,['$active',stamp,'z80:hl','z80:de','z80:b'])
    # Fuse reports these OUTs after updating PC. Other loading/beeper OUTs
    # are excluded by explicit player entry/refill events, not pulse values.
    bit='([z80:pc-1]==81 || ([z80:pc-1]==65 && z80:b==16) || ([z80:pc-1]==254 && z80:a==16))'
    event('port write 254',None,[f'({stamp}-$last)*2+{bit}'],['se $last '+stamp,'se $pulse $pulse+1'],condition='$active==1')
    for address in meta['first_addresses']:
        event(address+16,-121,['$pulse','z80:hl'],condition='$active==1')
        event(address+23,-120,['$pulse','z80:ix'],condition='$active==1')
    page_expressions=['$pulse',stamp,'z80:a']
    if capture_ui:page_expressions+=['ula:mem7ffd']+[f'[{address}]' for address in ui_addresses]
    event(labels['stream_page_event'],-107,page_expressions)
    if ui_enabled:
        # Each optional literal tail restores the next audio page here. The
        # old event remains necessary for the unchanged128/Scorpion path.
        for bit in (0,1):
            event(labels[f'stream_play_page_event_{bit}'],-107,page_expressions)
    if capture_ui:
        controls=[stamp,'ula:mem7ffd','$pulse','([23672]+[23673]*256)',
                  f"[{labels['audio_ui_loading']}]",f"[{labels['audio_ui_dots']}]",'[23416]']
        controls += [f'[{address}]' for address in ui_addresses]
        event(labels['audio_ui_leave_enabled'],-108,controls)
        event(labels['audio_ui_bar_complete'],-108,controls)
    terminal_expressions=[stamp,'$pulse','ula:mem7ffd']
    if capture_ui:terminal_expressions += [f'[{address}]' for address in final_ui_addresses]
    event(labels['stream_finished'],-199,terminal_expressions,stop=True)
    script='\n'.join(lines)
    command=[str(Path(fuse).resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
             '--speed','10000','--machine',profile,'--beta128','--debugger-command',script,str(Path(disk_path).resolve())]
    assert len(subprocess.list2cmdline(command))<32760
    if captured:
        assert (out/'debugger.txt').read_text()==script
        trace=gzip.decompress((out/'trace.txt.gz').read_bytes())
    else:
        (out/'debugger.txt').write_text(script,encoding='utf-8',newline='\n')
        result=subprocess.run(command,cwd=Path(fuse).parent,env=dict(os.environ,SDL_VIDEODRIVER='dummy'),
                              capture_output=True,startupinfo=hidden_startupinfo(),timeout=1200)
        trace=result.stdout
        (out/'trace.txt.gz').write_bytes(gzip.compress(trace,compresslevel=1,mtime=0))
        (out/'stderr.txt').write_bytes(result.stderr)
        assert result.returncode==77,('Fuse exit',profile,result.returncode,result.stderr[:1000])
    values=(int(x.group(1),0) for x in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace))
    pulses=array('I');preds=[];rows=[];ready=[];begins=[];ends=[];reads=[];covers=[];progress=[];pages=[];terminal=[];ui=[]
    targets={-100:ready,-101:begins,-103:ends,-104:covers,-105:progress,-106:reads,-107:pages,-108:ui,-120:preds,-121:rows,-199:terminal}
    for tag in values:
        if tag>=0xffff0000:tag-=2**32
        if tag>=0:pulses.append(tag)
        else:targets[tag].append([next(values) for _ in range(widths[tag])])
    pcm,indices,_,expected=reference(packed,cycles=1,model=meta['model'])
    count=(len(pcm)-3)*16+15
    recorded=np.asarray(pulses,dtype=np.int64)
    # The terminal breakpoint follows stream_finish's explicit beeper mute.
    # Check that extra teardown OUT too; it is not a compressed-source pulse.
    assert len(recorded)==count+1 and recorded[-1]&1==0,('Fuse output count',profile,len(recorded),count+1)
    pulse=recorded[:-1];bits=(pulse&1).astype('u1')
    assert np.array_equal(bits,expected[:count]),('Fuse source pulses',profile,np.flatnonzero(bits!=expected[:count])[:8])
    # At rare debugger/field boundaries Fuse observes one address twice.
    # Collapse only identical (pulse number,state) observations; preserve and
    # check every distinct source state and its exact source position.
    def state_check(observed,wanted,kind,slot):
        distinct=[r for i,r in enumerate(observed) if i==0 or r!=observed[i-1]]
        assert len(distinct)==len(pcm)-2,(kind,profile,len(distinct),len(pcm)-2)
        state=np.asarray([r[1] for r in distinct])
        assert np.array_equal(state,wanted[1:-1]),(kind,profile,np.flatnonzero(state!=wanted[1:-1])[:8])
        assert [r[0] for r in distinct]==list(range(slot,count,16)),('state source position',kind,profile,distinct[:3])
        return len(distinct)
    checked=state_check(preds,pcm.astype(np.int32)+32768,'predictor',4)
    state_check(rows,np.asarray(meta['decoder_rows'])[indices],'index',3)
    assert len(ready)==1 and len(terminal)==1 and terminal[0][1]==count+1
    assert len(covers)==1 and covers[0][0]<ready[0][0] and covers[0][1]&8
    assert all(r[0]==0 for r in reads),'ROM read during live audio'
    assert len(begins)==len(ends)
    for batch in range(len(begins)+1):
        observed=[r[1] for r in progress if r[0]==batch]
        published=[v for i,v in enumerate(observed) if i==0 or v!=observed[i-1]]
        assert published==list(range(1,33)),('progress',profile,batch,published)
    times=np.cumsum(pulse>>1);times-=times[0];holds=np.diff(times)
    refill_indices=[r[1]-1 for r in begins]
    assert [r[1] for r in begins]==[r[1] for r in ends]
    keep=np.ones(len(holds),dtype=bool)
    for k in refill_indices:keep[k]=False
    continuous=holds[keep];rate=(len(continuous)/16)*cpu/int(continuous.sum())
    assert abs(100*(rate/8000-1))<=2,('Fuse continuous speed',profile,rate)
    assert int(continuous.max())<1000,('unexpected continuous gap',profile,int(continuous.max()))
    from build_stream_trd import sections
    batches=[];remaining=len(packed)
    while remaining:
        batch,remaining=sections(remaining,PROFILES[profile]['pages']);batches.append(batch)
    assert len(begins)==len(batches)-1
    # Cold loading selects bank0 before entry. On refill, the saved live tail
    # resumes through the first new descriptor too; check that handoff as well.
    handoffs=[s for i,batch in enumerate(batches) for s in (batch[1:] if i==0 else batch)]
    expected_pages=[24|(s['bank']&7)|((s['bank']&0x18)<<3)|(s['bank']&32) for s in handoffs]
    if profile=='scorpion':expected_pages=[24|(s['bank']&7) for s in handoffs]
    assert [r[2] for r in pages]==expected_pages,('Fuse paging',profile,pages[:5],expected_pages[:5])
    audio_start=meta['audio_sector'];actual_audio=[(r[3]>>8)*16+(r[3]&15) for r in reads if r[2]==labels['stream_bounce']]
    assert actual_audio==list(range(audio_start,audio_start+meta['audio_sectors']))
    if len(batches)==1:assert not begins and all(r[1]<ready[0][0] for r in reads)
    (out/'times.u32.gz').write_bytes(gzip.compress(times.astype('<u4').tobytes(),mtime=0))
    report=dict(complete=True,profile=profile,independently_cold_booted=True,bits_verified=count,
                predictor_index_samples_verified=checked,every_source_bit_and_state_exact=True,teardown_silencing_outputs_verified=1,
                cover_before_audio=True,progress_per_batch_verified=True,end_of_audio_reached=True,
                initial_ready_seconds=ready[0][0]/cpu,reloads=len(begins),sector_reads=len(reads),
                reload_pause_seconds=[int(holds[k])/cpu for k in refill_indices],
                runtime_disk_reads_during_live_audio=0,continuous_sample_rate_hz=rate,
                continuous_speed_error_percent=100*(rate/8000-1),maximum_continuous_hold_tstates=int(continuous.max()),
                maximum_continuous_hold_microseconds=int(continuous.max())/cpu*1e6,
                bank_transition_pulses=[r[0] for r in pages],paging_values=[r[2] for r in pages],
                complete_playback_seconds=int(times[-1])/cpu,
                physical_hardware_tested=False,captured_complete_trace_rechecked=captured,
                trd_sha256=hashlib.sha256(Path(disk_path).read_bytes()).hexdigest())
    if meta['model'].get('pcm_quantization_bias'):
        report.update(pcm_quantization_bias=512,lookup_native_tstate_delta=0,
                      ula_timing_claim='Actual timing belongs to this complete source/profile; no source-independent128/Scorpion contention claim')
    if capture_ui:
        # Check exact gray/green cells, actual dot progression, and every live
        # prefix. This uses observed bytes rather than inferring the UI from
        # source position. Only control bytes have debugger capture coverage.
        assert ui and pages and terminal, 'missing actual UI observations'
        assert all(item[1]==31 for item in ui), 'loading UI not mapped to physical bank7'
        loading=[item for item in ui if item[4]]
        phase=[]
        for item in loading:
            assert item[5] in (1,2,3) and 0<=item[6]<=32
            if not phase or phase[-1]!=item[5]:phase.append(item[5])
            assert item[7+90:]==[0x3F]*item[6]+[7]*(32-item[6]), 'actual gray loading bar'
        assert len(phase)>=3 and phase[:3]==[1,2,3]
        assert all(value==1+i%3 for i,value in enumerate(phase)), 'actual LOADING dot order'
        playback=[]
        for item in pages:
            assert item[3]==31, 'live attributes not on physical bank7'
            attributes=item[4+90:]
            filled=sum(value==0x24 for value in attributes)
            assert attributes==[0x24]*filled+[4]*(32-filled), 'actual green playback prefix'
            playback.append(dict(pulse=item[0],timestamp_tstates=item[1],filled_columns=filled,
                                 glyph_bytes=item[4:4+80],label_attributes=item[4+80:4+90],
                                 bar_attributes=attributes))
        assert all(a['filled_columns']<=b['filled_columns'] for a,b in zip(playback,playback[1:]))
        assert terminal[0][3+288:]==[0x24]*32, 'actual final full-green bar'
        entry=next(item for item in meta['directory'] if item['name']=='COVER')
        start=(entry['track']*16+entry['sector'])*256
        cover=Path(disk_path).read_bytes()[start:start+6912]
        from audio_cover import render
        def snapshot(name,addresses,values):
            screen=bytearray(cover)
            for address,value in zip(addresses,values):screen[address-0xC000]=value
            raw=out/(name+'.scr');raw.write_bytes(screen)
            png=out/(name+'.png');render(bytes(screen)).resize((768,576),resample=0).save(png)
            return dict(screen=raw.name,png=png.name,screen_sha256=hashlib.sha256(screen).hexdigest(),
                        png_sha256=hashlib.sha256(png.read_bytes()).hexdigest())
        pictures=[]
        for dots in (1,2,3):
            item=next(row for row in loading if row[5]==dots)
            pictures.append(snapshot('loading-'+str(dots),ui_addresses,item[7:]))
        empty=next(row for row in ui if not row[4] and row[6]==0)
        pictures.append(snapshot('playing-start',ui_addresses,empty[7:]))
        middle=min(pages,key=lambda row:abs(sum(value==0x24 for value in row[4+90:])-16))
        pictures.append(snapshot('playing-middle',ui_addresses,middle[4:]))
        pictures.append(snapshot('playing-end',final_ui_addresses,terminal[0][3:]))
        ui_report=dict(complete=True,loading_observations=len(loading),loading_dot_phases=phase,
                       loading_gray_attributes_exact=True,live_green_prefixes_exact=True,
                       live_progress=playback,final_full_green=True,pictures=pictures,
                       observed_controls=dict(loading_and_playback_glyph_bytes=80,label_attributes=10,bar_attributes=32,
                                              final_glyph_bytes=256,final_label_attributes=32),
                       cover_sha256=hashlib.sha256(cover).hexdigest(),
                       screen_scope='Actual cold-Fuse status bitmap/attributes and bar attributes; other untouched cover pixels from the exact TRD. This is not a full6912-byte debugger dump.',
                       physical_hardware_tested=False)
        save(out/'ui.json',ui_report);report['audio_progress_ui']=ui_report
    save(out/'report.json',report)
    return report


def cold_load(disk,meta,profile):
    labels=meta['player_labels'];m=MemoryMachine(profile,b'',labels)
    player=next(x for x in meta['directory'] if x['name']=='PLAYER')
    sector=player['track']*16+player['sector']
    m.banks[2][:]=disk[sector*256:(sector+64)*256]
    m.m.pc=labels['start'];m.m.set_breakpoint(labels['stream_loaded'])
    m.m.clear_breakpoint(0x40)
    reads=[];cover=False;ui_enabled=bool(meta.get('audio_progress_ui'));ui_loading_complete=False
    m.m.set_breakpoint(labels['cover_visible'])
    if ui_enabled:m.m.set_breakpoint(labels['audio_ui_begin_playback'])
    while m.m.pc!=labels['stream_loaded']:
        m.m.ticks_to_stop=100_000_000;event=m.m.run()
        if m.m.pc==0x3d13:
            assert m.selected<8,'extended mapping during ROM'
            sector=(m.m.de>>8)*16+(m.m.de&255);reads.append(sector)
            for i,v in enumerate(disk[sector*256:(sector+1)*256]):m.write(m.m.hl+i,v)
            m.m.clear_breakpoint(0x3d13);m.m.ticks_to_stop=4;m.m.run();m.m.set_breakpoint(0x3d13)
        elif m.m.pc==labels['cover_visible']:
            entry=next(x for x in meta['directory'] if x['name']=='COVER')
            at=entry['track']*16+entry['sector'];assert m.banks[7][:6912]==disk[at*256:(at+27)*256]
            cover=True;m.m.clear_breakpoint(labels['cover_visible'])
        elif ui_enabled and m.m.pc==labels['audio_ui_begin_playback']:
            # Gray loading is complete before the separate green playback
            # initialization resets CACHE_BAR to this batch's source origin.
            assert m.read(0x5b78)==32 and m.word(0x5b7a)==0,'UI loader completion'
            ui_loading_complete=True;m.m.clear_breakpoint(labels['audio_ui_begin_playback'])
        elif event&m.m._TICKS_LIMIT_HIT:raise AssertionError(('cold timeout',hex(m.m.pc)))
    assert cover and not m.locked
    if ui_enabled:assert ui_loading_complete and m.read(0x5b78)==0,'initial UI playback origin'
    else:assert m.read(0x5b78)==32
    pointer=labels['stream_records'];sections=[];offset=meta['audio_sector']*256
    while m.read(pointer):
        paging=m.read(pointer);high=m.read(pointer+1);scorp=m.read(pointer+2)
        page=(paging&7)|((scorp&16)>>1 if profile=='scorpion' else (paging&0xc0)>>3|(paging&32) if profile=='pentagon1024' else (paging&0xc0)>>3 if profile=='pentagon512' else 0)
        size=(256-high)*256
        assert m.banks[page][high*256-0xc000:]==disk[offset:offset+size],('loaded bytes',profile,page)
        sections.append(dict(bank=page,address=high*256,bytes=size));offset+=size;pointer+=3
    # Independently inspect all256 hardware selector bytes after cold loading.
    # This covers every signed PCM16 value, even when a short source does not
    # visit all64 bins. No selector arithmetic executes on the Z80 hot path.
    bias=meta['model'].get('pcm_quantization_bias',0)
    if type(bias) is not int or bias not in (0,512):
        raise ValueError('invalid PCM quantization bias in player metadata')
    if bias and (meta['model'].get('pcm_bins',64)!=64 or meta['model'].get('family') not in (None,'integral')):
        raise ValueError('PCM quantization bias requires the64-bin integral PDM model')
    lookup=labels['pcm_high']
    expected=bytes(meta['packet_pages'][min(63,(high*256+bias)//1024)]>>8 for high in range(256))
    assert bytes(m.read(lookup+high) for high in range(256))==expected,'hardware PCM quantizer lookup'
    report=dict(complete=True,profile=profile,cover_before_audio=True,progress_complete=True,
                loaded_sections=sections,disk_calls=len(reads),remaining_sectors=m.word(labels['stream_remaining']))
    if ui_enabled:report['audio_progress_ui']=dict(gray_loading_complete_before_green=True,initial_playback_column=0)
    return m,report


def native_check(disk,meta,packed,profile,*,out=None):
    cold,loading=cold_load(disk,meta,profile)
    banks=[bytearray(x) for x in cold.banks];m=Z80Machine()
    m.memory[:16384]=cold.rom;m.memory[0x4000:0x8000]=banks[5];m.memory[0x8000:0xc000]=banks[2]
    low,high,eff=24,0,0;selected=0
    m.memory[0xc000:]=banks[0]
    pcm,indices,_,bits=reference(packed,cycles=1,model=meta['model'])
    count=(len(pcm)-3)*16+15;expected=bits[:count]
    got=bytearray();times=array('I');pages=[];extra=[];reads=0;reloads=0;active=True;checked=0
    before_hot=bytes(m.memory[min(meta['first_addresses']):meta['player_labels']['resident_end']])
    before_tables=bytes(m.memory[0x4000:0x8000]);disk_reads=[]
    budget=1_500_000_000;labels=meta['player_labels']
    def page():
        nonlocal selected
        nxt=low&7
        if profile=='scorpion':nxt|=(high&16)>>1
        elif profile=='pentagon512':nxt|=(low&0xc0)>>3
        elif profile=='pentagon1024' and not eff&4:nxt|=(low&0xc0)>>3|low&32
        assert nxt<len(banks)
        banks[selected][:]=m.memory[0xc000:];selected=nxt;m.memory[0xc000:]=banks[nxt]
        if active:pages.append(dict(pulse=len(got),bank=nxt))
    def output(port,value):
        nonlocal low,high,eff,checked
        if port==0xeff7:eff=value;return
        if port==0x1ffd:
            if profile=='scorpion':high=value;page()
            return
        if port&0x8002==0:low=value;page();return
        if port&255==254 and active:
            sample,slot=divmod(len(got),16)
            if slot==4:
                assert m.ix==int(pcm[sample+1])+32768,(profile,sample,'predictor')
                assert m.alt_hl==meta['decoder_rows'][int(indices[sample+1])],(profile,sample,'index')
                checked+=1
            assert value in (0,16) and not 0x4000<=port<0x8000
            got.append(value>>4);times.append(budget-m.ticks_to_stop)
    m.set_output_callback(output);m.pc=labels['ready'];m.sp=0x6000;m.ticks_to_stop=budget
    for label in ('stream_reload_begin','stream_reload_end','stream_finish'):m.set_breakpoint(labels[label])
    m.set_breakpoint(0x3d13)
    def step_breakpoint(at):
        m.clear_breakpoint(at)
        left=m.ticks_to_stop;m.ticks_to_stop=1;m.run();spent=1-m.ticks_to_stop
        m.ticks_to_stop=left-spent;m.set_breakpoint(at)
    while m.pc!=labels['stream_finish']:
        event=m.run()
        if m.pc==labels['stream_reload_begin']:
            assert active;active=False;reloads+=1;extra.append(len(got));step_breakpoint(m.pc)
        elif m.pc==labels['stream_reload_end']:
            assert not active;active=True;step_breakpoint(m.pc)
        elif m.pc==0x3d13:
            assert not active and selected<8
            sector=(m.de>>8)*16+(m.de&255);reads+=1;disk_reads.append(sector)
            m.memory[m.hl:m.hl+256]=disk[sector*256:(sector+1)*256];step_breakpoint(m.pc)
        elif event&m._TICKS_LIMIT_HIT:raise AssertionError(('native timeout',profile,hex(m.pc),len(got)))
    assert len(got)==count,(profile,len(got),count)
    assert np.array_equal(np.frombuffer(got,'u1'),expected),('native pulse values',profile,np.flatnonzero(np.frombuffer(got,'u1')!=expected)[:8])
    periods=np.diff(np.asarray(times,dtype=np.int64))
    baseline=np.tile(meta['ordinary_holds_tstates'],len(pcm))[:len(periods)].astype(np.int64)
    baseline[7::16]+=PROFILES[profile]['ima4_extra']
    delta=periods-baseline
    # From the instruction table: old ordinary-bank handoff extra140 T;
    # new fixed descriptor path extra243 T (delta+103). Scorpion replaces
    # JP10 by3 NOPs12 +LD BC10 +OUT12: another24 T,extra267,delta+127.
    from build_stream_trd import sections
    remaining=len(packed);offset=0;wanted=baseline.copy();reload_positions=[]
    bank_extra=267 if profile=='scorpion' else 243
    while remaining:
        batch,left=sections(remaining,PROFILES[profile]['pages'])
        for j,s in enumerate(batch):
            for byte in range(256,s['bytes']+1,256):
                k=(2*(offset+byte)-3)*16+14
                if k>=len(wanted):continue # final excluded silent guard only
                if byte<s['bytes']:wanted[k]+=14
                elif j+1<len(batch):wanted[k]+=bank_extra
                else:reload_positions.append(k)
            offset+=s['bytes']
        remaining=left
    mask=np.ones(len(periods),dtype=bool)
    for k in reload_positions:mask[k]=False
    assert np.array_equal(periods[mask],wanted[mask]),('native holds',profile,np.flatnonzero((periods!=wanted)&mask)[:8])
    assert len(reload_positions)==reloads
    assert bytes(m.memory[min(meta['first_addresses']):labels['resident_end']])==before_hot
    assert bytes(m.memory[0x4000:0x5b70])==before_tables[:0x1b70]
    assert bytes(m.memory[0x5b80:0x5c00])==before_tables[0x1b80:0x1c00]
    assert bytes(m.memory[0x6000:0x8000])==before_tables[0x2000:]
    assert disk_reads==list(range(meta['audio_sector']+sum(s['bytes'] for s in loading['loaded_sections'])//256,meta['audio_sector']+meta['audio_sectors']))
    # Record every unusual interval. Only explicit insufficient-RAM reloads
    # may be long; full-RAM playback excludes no source-bearing interval.
    events=[(int(k),int(delta[k])) for k in np.flatnonzero(delta)]
    if profile in ('pentagon512','pentagon1024') and not loading['remaining_sectors']:
        assert reloads==reads==0
        assert int(periods.max())<1000,'unexpected bank gap'
    report=dict(complete=True,profile=profile,bits_verified=count,predictor_index_samples=checked,reloads=reloads,
                rom_calls_during_refills=reads,maximum_native_hold_tstates=int(periods.max()),loading=loading,
                every_bit_predictor_index_exact=True,every_continuous_native_hold_exact=True,memory_guards_passed=True,
                explicit_reload_intervals=reload_positions,bank_extra_tstates=bank_extra,bank_delta_tstates=bank_extra-140,
                ordinary_tstates=423+PROFILES[profile]['ima4_extra'],pages=pages,interval_extras=events)
    if meta['model'].get('pcm_quantization_bias'):
        report.update(pcm_quantization_bias=512,all256_hardware_lookup_entries_verified=True,
                      lookup_native_tstate_delta=0,
                      ula_timing_claim='Native CPU proof excludes data-dependent128/Scorpion ULA waits')
    if out is not None:save(out,report)
    return report


def main():
    import argparse
    from concurrent.futures import ThreadPoolExecutor
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory',type=Path)
    p.add_argument('--fuse',type=Path)
    p.add_argument('--profile',choices=tuple(PROFILES),action='append')
    p.add_argument('--jobs',type=int,default=1)
    p.add_argument('--captured',action='store_true',help='Recheck authenticated complete Fuse traces without launching Fuse')
    a=p.parse_args();root=a.directory.resolve();out=root/'verification';out.mkdir(exist_ok=True)
    meta=json.loads((root/'player.json').read_bytes());packed=gzip.decompress((root/'soundtrack.ima.gz').read_bytes())
    disk=root/'audio.trd';assert hashlib.sha256(disk.read_bytes()).hexdigest()==meta['trd_sha256']
    assert hashlib.sha256(packed).hexdigest()==meta['packed_sha256']
    def run(profile):
        native=native_check(disk.read_bytes(),meta,packed,profile,out=out/f'native-{profile}.json')
        print('Native complete: '+profile,flush=True)
        actual=fuse_check(disk,meta,packed,profile,out/profile,a.fuse,captured=a.captured) if a.fuse else None
        print('Complete: '+profile,flush=True)
        return dict(profile=profile,native=native,fuse=actual)
    with ThreadPoolExecutor(max_workers=a.jobs) as pool:results=list(pool.map(run,a.profile or tuple(PROFILES)))
    save(out/'report.json',dict(complete=True,profiles=results,trd_sha256=meta['trd_sha256']))


if __name__=='__main__':main()
