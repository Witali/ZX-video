"""Measure a complete experimental FAP3 disk with the real Fuse/TR-DOS.

Records actual publication OUTs, every AY register write/tick, all runtime
sector bytes and deterministic pixel samples per frame. Samples are not a
full image comparison. No synthetic disk producer or IRQ is used.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time

import numpy as np
import disk_layout
from bulk_frame_stream import read_packet
from frame_output_pipeline import display_screen
from probe_motion_entropy import Reader
from probe_spatial_contexts import read_header
from smoke_test_fuse import hidden_startupinfo

FIELD=70908


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('fuse','trd','metadata','raw','states','output'): p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--timeout',type=float,default=180)
    p.add_argument('--continuation-snapshot',type=Path,help='Resume the previous verified EOF at its disk prompt')
    p.add_argument('--export-warm-ram',type=Path,help='Dump actual banks 5/2/6 only after the complete disk finishes')
    p.add_argument('--trace-fields',action='store_true',help='Record IRQ entries and CPU state at field offsets 0/32; no player changes')
    p.add_argument('--trace-paging',action='store_true',help='Record IRQ entries and paging boundaries near the IRQ pulse; address breakpoints only')
    p.add_argument('--slot-queue',action='store_true',help='Install the experimental four-slot player after normal cold bootstrap')
    p.add_argument('--uncontended-frame',action='store_true',help='With --slot-queue, relocate compact frame/cache to bank 2')
    p.add_argument('--compiled-masks',action='store_true',help='With --slot-queue, generate sparse-mask routines in bank 7')
    p.add_argument('--idle-masks',action='store_true',help='With compiled masks, skip untouched bitmap stripes using RAM flags')
    p.add_argument('--trace-pipeline',action='store_true',help='With slot queue, record packet/prepare/draw entries and synchronous empty-queue waits')
    p.add_argument('--partial-slots',action='store_true',help='With slot queue, allow consumption of a produced prefix before block EOF')
    p.add_argument('--cached-huffman-byte',action='store_true',help='With slot queue, retain the current Huffman input byte in B')
    p.add_argument('--inline-literals',action='store_true',help='With slot queue, copy ZX0 literals without CALL/RET')
    p.add_argument('--demand-decode',action='store_true',help='With slot queue, decode the requested prefix before one contiguous copy')
    p.add_argument('--fixture-zx0',type=Path,help='ZX0 executable for compressing debugger-only startup patches')
    args=p.parse_args(); m=json.loads(args.metadata.read_text()); lab=m['player_labels']
    patches=[];nonce=secrets.randbits(30)
    if args.uncontended_frame and not args.slot_queue:raise ValueError('relocation requires --slot-queue')
    if args.compiled_masks and not args.slot_queue:raise ValueError('compiled masks require --slot-queue')
    if args.idle_masks and not args.compiled_masks:raise ValueError('idle masks require --compiled-masks')
    if args.trace_pipeline and not args.slot_queue:raise ValueError('pipeline tracing requires --slot-queue')
    if args.partial_slots and not args.slot_queue:raise ValueError('partial slots require --slot-queue')
    if args.cached_huffman_byte and not args.slot_queue:raise ValueError('cached byte requires --slot-queue')
    if args.inline_literals and not args.slot_queue:raise ValueError('inline literals require --slot-queue')
    if args.demand_decode and not args.slot_queue:raise ValueError('demand decoding requires --slot-queue')
    if args.slot_queue:
        if args.continuation_snapshot or args.export_warm_ram:raise ValueError('queue fixture requires an independent cold boot')
        from slot_queue_player import build
        patches,m=build(m,args.raw.read_bytes(),uncontended=args.uncontended_frame,
            compiled_masks=args.compiled_masks,idle_masks=args.idle_masks,
            partial_consumption=args.partial_slots,cached_huffman_byte=args.cached_huffman_byte,
            inline_literals=args.inline_literals,demand_decode=args.demand_decode);lab=m['player_labels']
    if not m.get('independently_bootable',True) and not args.continuation_snapshot:
        raise ValueError('continuation disk requires RAM exported from its predecessor')
    if m.get('required_trdos_sha256') and hashlib.sha256((args.fuse.parent/'roms/trdos.rom').read_bytes()).hexdigest()!=m['required_trdos_sha256']:
        raise ValueError('fast reader requires its verified TR-DOS ROM')
    lines=['base 10','set $running 0','set $dump 65537']; widths={}; events=[]
    target_samples=args.idle_masks or args.trace_pipeline
    if target_samples: lines.append('set $n 0')
    if args.trace_pipeline:lines.append('set $qwait 0')
    def event(pc,tag,expressions,stop=False,after=(),breakpoint=None,before=()):
        index=len(events)+1; events.append((pc,tag)); widths[tag]=len(expressions)
        lines.extend([breakpoint or f'breakpoint {pc}',f'commands {index}',f'print {tag}'])
        if tag==100: lines.append('set $running 1')
        lines.extend(before)
        lines.extend('print '+e for e in expressions)
        lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if tag!=100: lines.append(f'condition {index} $running == {0 if tag==90 else 1}')
    def mem(address): return f'[{address}]+256*[{address+1}]'
    stamp='spectrum:frames*70908+ula:tstates'
    event(m['bootstrap_labels'].get('bootstrap_entry',0x6000),90,[stamp])
    if args.continuation_snapshot:
        event(m['bootstrap_labels']['next_disk_accepted'],88,[stamp])
        lines[-1]=f'condition {len(events)} $running == 0'
    if args.slot_queue:
        if not args.fixture_zx0:raise ValueError('--slot-queue requires --fixture-zx0')
        from fuse_patch_loader import build as build_installer
        patches,install_entry,install_report=build_installer(patches,lab['start'],args.fixture_zx0,args.output.parent/'install',
            copies=m.get('fixture_checkpoint_copies',()))
        # Installation is logged separately; entering the actual driver is
        # the start of measured playback, after the temporary loader returns.
        event(lab['start'],89,[stamp],after=[f'se {a} {v}' for a,v in patches]+['set $running 2',f'set z80:pc {install_entry}'])
        lines[-1]=f'condition {len(events)} $running == 0'
    event(lab['start'],100,[stamp,str(nonce)])
    lines.append(f'condition {len(events)} $running == {2 if args.slot_queue else 0}')
    samples=sorted(set([i*97%6912 for i in range(56)]+[6144+i*31 for i in range(24)]))
    sample_expr=[]
    # Sample after drawing returns to the bank-7 clock; publication itself
    # is allowed to interrupt a disk read with another bank at C000.
    for address in (0x4000,0xc000): sample_expr += [f'[{address+i}]' for i in samples]
    if target_samples:
        # Old traces exported both screens then discarded the non-target 80
        # samples. Export the same target addresses directly to leave room for
        # the larger installer in Windows' 32767-character command line.
        sample_expr=[f'[$s+{i}]' for i in samples]
    # Stop after OUT has executed: includes real I/O contention, without
    # adding an assumed 12 T to the preceding instruction boundary.
    event(lab['publish_out']+2,150,[stamp,'z80:a',mem(lab['elapsed_fields']),mem(lab['late_fields'])])
    for index,pc in enumerate(m['native_ready_pcs']):
        event(pc,151+index,[stamp,'ula:mem7ffd']+sample_expr,
            before=['set $s 49152-32768*($n&1)'] if target_samples else (),
            after=['set $n $n+1'] if target_samples else ())
    if args.trace_pipeline:
        q,z,packet=m['queue_labels'],m['decoder_labels'],m['packet_labels']
        queue_state=[stamp,'ula:mem7ffd',f'[{q["count"]}]',f'[{q["phase"]}]',
            mem(q['blocks_left']),mem(q['position']),mem(z['slice_output'])]
        for label,tag in (('read_packet',160),('packet_ready',161),('prepare_bridge',162),('draw_bridge',163)):
            event(packet[label],tag,queue_state)
        event(q['take_next'],165,queue_state,after=['set $qwait 1'])
        lines[-1]=f'condition {len(events)} $running == 1 && [{q["count"]}]==0 && $qwait==0'
        event(q['take_available'],166,queue_state,after=['set $qwait 0'])
        lines[-1]=f'condition {len(events)} $running == 1 && $qwait==1'
    event(lab['audio_write_loop'],140,[stamp,'[z80:hl]','[z80:hl+1]'])
    event(lab['audio_tick_done'],143,[stamp])
    event(lab['audio_tick_empty'],144,[stamp])
    if args.trace_fields or args.trace_paging:
        event(0xbdbd,130,[stamp,'[z80:sp]+256*[z80:sp+1]','z80:im','ula:mem7ffd'])
    if args.trace_fields:
        for offset,tag in ((0,131),(32,132)):
            event(0,tag,[stamp,'z80:pc','z80:iff1','z80:iff2','z80:im','ula:mem7ffd',mem(lab['elapsed_fields'])],
                breakpoint=f'breakpoint time {offset}')
    if args.trace_paging:
        if m.get('irq_safe_paging'): raise ValueError('DI window tracing requires the old paging helper')
        for pc,tag in ((0x9781,133),(0x9793,134)):
            event(pc,tag,[stamp,'z80:iff1','z80:iff2','z80:sp','[z80:sp]+256*[z80:sp+1]'])
            lines[-1]=f'condition {len(events)} $running == 1 && (ula:tstates >= 70800 || ula:tstates < 108)'
    event(lab['disk_full_call'],102,[stamp,'z80:hl',mem(m['disk_labels']['disk_position'])],
        after=[f'set $b 256*[{m["disk_labels"]["write_high"]}]'])
    # A whole consumed sector was replaced at saved write_high. Read its
    # exact bytes before the decoder resumes; compact four bytes per print.
    base='$b'
    sector_expr=['+'.join((f'{256**k}*' if k else '')+f'[{base}+{i+k}]' for k in range(4)) for i in range(0,256,4)]
    event(lab['disk_return'],103,[stamp]+sector_expr)
    if 'fast_read_enter' in lab:
        event(lab['fast_read_enter'],110,[stamp,'z80:hl',mem(m['disk_labels']['disk_position'])],
            after=[f'set $b 256*[{m["disk_labels"]["write_high"]}]'])
        event(lab['fast_disk_return'],111,[stamp]+([] if args.slot_queue else sector_expr))
        event(lab['fast_read_retry'],112,[stamp])
    if 'seek_enter' in lab:
        event(lab['seek_side_enter'],120,[stamp])
        event(lab['seek_side_return'],121,[stamp])
        event(lab['seek_enter'],122,[stamp])
        event(lab['seek_return'],123,[stamp])
    if 'keepalive_enter' in m.get('deferred_labels',{}):
        event(m['deferred_labels']['keepalive_enter'],124,[stamp])
        event(m['deferred_labels']['keepalive_return'],125,[stamp])
    export=['set $running 0','set $dump 16384','out 32765 22','set z80:pc 39520'] if args.export_warm_ram else []
    event(lab['finished'],199,[stamp,mem(lab['published']),mem(lab['audio_ticks_played']),mem(lab['audio_underruns'])]+
        [f'[{base+i}]' for base in (0x50e0,0x51e0,0xd0e0,0xd1e0) for i in range(32)],not bool(export),after=export)
    for name in ('fatal','zx0_fatal'): event(lab[name],198,[stamp,'z80:pc'],True)
    if args.slot_queue:
        for labels in (m['queue_labels'],m['producer_labels']):event(labels['fatal'],198,[stamp,'z80:pc'],True)
    if export:
        # After EOF only: repeat the existing DI at 9A60; debugger redirects
        # PC before its following instruction. RAM is neither patched nor
        # synthesized. Three actual banks are exported at one dword per hit.
        event(0x9a61,300,['[$dump]+256*[$dump+1]+65536*[$dump+2]+16777216*[$dump+3]'],
            after=['set $dump $dump+4','set z80:pc 39520'])
        lines[-1]=f'condition {len(events)} $dump < 65536'
        event(0x9a61,301,[],True)
        lines[-1]=f'condition {len(events)} $running == 0 && $dump == 65536'
    # Documented debugger abbreviations keep the patch fixture below Windows' limit.
    lines=[s.replace('print ','pr ',1) if s.startswith('print ') else s for s in lines]
    abbreviations={'set ':'se ','breakpoint ':'br ','condition ':'cond ','commands ':'com ','exit ':'ex ','continue':'co'}
    for i,line in enumerate(lines):
        for long,short in abbreviations.items():
            if line.startswith(long):line=short+line[len(long):];break
        # '[' delimits a memory expression without whitespace; verified with
        # Fuse 1.9.0. Keep every pixel/sector expression and breakpoint intact.
        if line.startswith('pr ['): line='pr['+line[4:]
        lines[i]=line.replace('$running','$r').replace(' == ','==')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix('.debugger.txt').write_text('\n'.join(lines))
    env=dict(os.environ,SDL_VIDEODRIVER='dummy')
    media=['--betadisk',str(args.trd.resolve()),'--snapshot',str(args.continuation_snapshot.resolve())] if args.continuation_snapshot else [str(args.trd.resolve())]
    command=[str(args.fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command','\n'.join(lines)]+media
    if len(subprocess.list2cmdline(command))>=32760:
        raise ValueError(f'Windows command line too long: {len(subprocess.list2cmdline(command))}')
    started=time.monotonic();epoch=time.time()
    completed=subprocess.run(command,cwd=args.fuse.parent,env=env,capture_output=True,
        startupinfo=hidden_startupinfo(),timeout=args.timeout)
    output=completed.stdout.decode(errors='replace')
    if (not re.search(r'^\s*\d+\s*$',output,re.M) and (args.fuse.parent/'stdout.txt').exists()
            and (args.fuse.parent/'stdout.txt').stat().st_mtime>=epoch-2):
        output=(args.fuse.parent/'stdout.txt').read_text(errors='replace')
    args.output.with_suffix('.stderr.txt').write_text(completed.stderr.decode(errors='replace'))
    args.output.with_suffix('.trace.txt').write_text(output)
    nums=[int(s.strip(),0) for s in output.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s.strip())]
    parsed=[]; pos=0
    while pos<len(nums):
        tag=nums[pos]; pos+=1
        if tag not in widths or pos+widths[tag]>len(nums): raise ValueError(f'bad trace at {pos}: {nums[pos-1:pos+3]} / {output[-300:]}')
        parsed.append((tag,nums[pos:pos+widths[tag]])); pos+=widths[tag]
    pubs=[]; writes=[]; ticks=[]; underruns=[]; reads=[]; final=None; failure=None
    irq_entries=[];field_samples=[];paging_samples=[];pipeline_events=[]
    image=args.trd.read_bytes(); pending=None; errors=[]; native_count=0; retries=0; read_kind=None
    boot_started=player_started=None;nonces=[]
    warm_ram=bytearray(); warm_dump_complete=False; continuation_accepted=[]
    seek_pending=None; seek_calls=[]
    with np.load(args.states,allow_pickle=False) as data: states=data['states']
    for tag,v in parsed:
        if tag==90:
            if boot_started is None: boot_started=v[0]
        elif tag==88: continuation_accepted.append(v[0])
        elif tag==300: warm_ram+=(v[0]&0xffffffff).to_bytes(4,'little')
        elif tag==301: warm_dump_complete=True
        elif tag==100: player_started=v[0];nonces.append(v[1])
        elif tag==150:
            pubs.append(dict(tstate=v[0],page=v[1],field=v[2],late_fields=v[3]))
        elif tag in (151,152):
            frame=m['frame_start']+native_count
            samples_at=v[2:] if target_samples else (v[2:2+len(samples)] if native_count%2 else v[2+len(samples):])
            wanted=display_screen(states[frame].tobytes(),black_borders=True)
            bad=[i for i,x in zip(samples,samples_at) if x!=wanted[i]]
            # Bar occupies bitmap offsets 10e0/11e0 and attribute 1ae0.
            bad=[i for i in bad if not (0x10e0<=i<0x1100 or 0x11e0<=i<0x1200 or 0x1ae0<=i<0x1b00)]
            if bad: errors.append(dict(frame=frame,page=v[1],pixels=bad,
                values=[dict(offset=i,actual=x,expected=wanted[i]) for i,x in zip(samples,samples_at) if i in bad]))
            native_count+=1
        elif tag==140: writes.append(v)
        elif tag==143: ticks.append(v[0])
        elif tag==144: underruns.append(v[0])
        elif tag in (160,161,162,163,165,166):
            pipeline_events.append(dict(kind={160:'packet_start',161:'packet_ready',162:'prepare_start',
                163:'draw_start',165:'empty_wait_start',166:'empty_wait_end'}[tag],
                **dict(zip(('tstate','page','count','phase','blocks_left','position','slice_output'),v))))
        elif tag==130: irq_entries.append(dict(tstate=v[0],interrupted_pc=v[1],im=v[2],page=v[3]))
        elif tag in (131,132):
            field_samples.append(dict(offset=0 if tag==131 else 32,tstate=v[0],pc=v[1],iff1=v[2],iff2=v[3],
                im=v[4],page=v[5],elapsed_fields=v[6]))
        elif tag in (133,134):
            paging_samples.append(dict(kind='after_di' if tag==133 else 'before_ret',tstate=v[0],
                iff1=v[1],iff2=v[2],sp=v[3],caller=v[4]))
        elif tag in (102,110):
            if pending is not None: raise ValueError('overlapping ROM reads')
            pending=v; read_kind='trdos' if tag==102 else 'direct503'
        elif tag in (103,111):
            if args.slot_queue and tag==111:
                # The shared disk_finish breakpoint exports accepted bytes
                # for either entry path; avoid duplicating 64 expressions.
                continue
            # Successful direct reads jump to the shared full-read epilogue.
            # Its second breakpoint is not another ROM return/read attempt.
            if tag==103 and pending is None and reads and reads[-1]['kind']=='direct503' and not reads[-1]['retried']:
                continue
            if pending is None: raise ValueError('return without ROM entry')
            linear=(pending[2]>>8)*16+(pending[2]&255)
            actual=b''.join((value&0xffffffff).to_bytes(4,'little') for value in v[1:])
            reads.append(dict(sector=linear,tstates=v[0]-pending[0],kind=read_kind,
                bytes_exact=actual==image[linear*256:(linear+1)*256],retried=False,
                start_tstate=pending[0],end_tstate=v[0],entry_tstates=17 if read_kind=='trdos' else 10)); pending=None
        elif tag==112:
            if args.slot_queue:
                if pending is None or read_kind!='direct503':raise ValueError('retry without direct read')
                linear=(pending[2]>>8)*16+(pending[2]&255)
                reads.append(dict(sector=linear,tstates=v[0]-pending[0],kind=read_kind,
                    bytes_exact=False,retried=True,start_tstate=pending[0],end_tstate=v[0],entry_tstates=10))
                retries+=1;pending=None
                continue
            if not reads or reads[-1]['kind']!='direct503': raise ValueError('retry without direct read')
            retries+=1; reads[-1]['retried']=True
        elif tag in (120,122,124):
            if seek_pending is not None: raise ValueError('overlapping seek calls')
            seek_pending=(tag,v[0])
        elif tag in (121,123,125):
            if seek_pending is None or seek_pending[0]!=tag-1: raise ValueError('unmatched seek return')
            seek_calls.append(dict(kind={121:'side',123:'seek',125:'keepalive'}[tag],tstates=v[0]-seek_pending[1],
                start_tstate=seek_pending[1],end_tstate=v[0]))
            seek_pending=None
        elif tag==199: final=v
        elif tag==198: failure=v
    for read in reads:
        if not read['retried'] and not read['bytes_exact']:
            errors.append(dict(sector=read['sector'],error='accepted disk bytes differ'))
    accepted=[q['sector'] for q in reads if not q['retried']]
    positions=list(disk_layout.positions(m['video_sectors'],m['video_start_sector']%16)) if m.get('interleaved') else list(range(m['video_sectors']))
    wanted_sectors=[m['video_start_sector']+p for p in positions[min(m.get('runtime_video_preload_sectors',256),m['video_sectors']):]]
    if pending is not None or seek_pending is not None or accepted!=wanted_sectors:
        errors.append(dict(error='runtime sector sequence incomplete or duplicated'))
    raw=args.raw.read_bytes(); r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3')
    expected=[]
    for i in range(count):
        _,detail=read_packet(r,stored_guards=False)
        if m['frame_start']<=i<m['frame_end_exclusive']: expected+=detail['ticks']
    actual=[]; cursor=0
    for timestamp in ticks:
        changed=[]
        while cursor<len(writes) and writes[cursor][0]<timestamp:
            changed+=writes[cursor][1:]; cursor+=1
        actual.append(bytes([len(changed)//2]+changed))
    ay_exact=actual==expected
    offsets=[q['tstate']-pubs[0]['tstate']-6*i*FIELD for i,q in enumerate(pubs)]
    intervals=[b['tstate']-a['tstate'] for a,b in zip(pubs,pubs[1:])]
    runs=[]; first=None
    for i,q in enumerate(pubs):
        if q['late_fields'] and first is None: first=i
        if not q['late_fields'] and first is not None:
            runs.append(dict(start=first,end=i-1,recovered_at=i)); first=None
    if first is not None: runs.append(dict(start=first,end=len(pubs)-1,recovered_at=None))
    progress_complete=bool(final and final[4:]==[255]*128)
    if args.continuation_snapshot and len(continuation_accepted)!=1:
        errors.append(dict(error='continuation ID was not accepted exactly once'))
    if args.export_warm_ram and (not warm_dump_complete or len(warm_ram)!=49152):
        errors.append(dict(error='warm RAM export incomplete',bytes=len(warm_ram)))
    complete=bool(nonces==[nonce] and final and final[1]==m['frames'] and final[2]==6*m['frames'] and len(pubs)==m['frames']
        and native_count==m['frames'] and ay_exact and not errors and progress_complete)
    report=dict(scope=__doc__,part=m['part'],complete=complete,release=False,exit_code=completed.returncode,
        runtime_seconds=time.monotonic()-started,trd_sha256=hashlib.sha256(image).hexdigest(),
        final=final[:4] if final else None,failure=failure,frames=len(pubs),native_frames_sampled=native_count,
        progress_100_percent=progress_complete,ay_ticks=len(ticks),ay_records_exact=ay_exact,
        audio_underruns=len(underruns),runtime_sectors_checked=len(accepted),read_attempts=len(reads),errors=errors[:100],
        fast_read_retries=retries,fast_disk=m.get('fast_disk',False),
        cached_seek=m.get('cached_seek',False),seek_calls=seek_calls,
        interleaved=m.get('interleaved',False),
        audio_tick_tstates=ticks,
        elapsed_timing=dict(bootstrap_tstates=player_started-boot_started if player_started is not None and boot_started is not None else None,
            playback_tstates=final[0]-player_started if final and player_started is not None else None,
            bootstrap_and_playback_tstates=final[0]-boot_started if final and boot_started is not None else None,
            includes='all elapsed CPU/ROM/disk/IRQ/ULA time from PLAYER entry to finished; excludes BASIC loading PLAYER and human disk changes'),
        ay_record_field_gaps=sum(max(0,b//FIELD-a//FIELD-1) for a,b in zip(ticks,ticks[1:])),
        ay_record_field_duplicates=sum(b//FIELD==a//FIELD for a,b in zip(ticks,ticks[1:])),
        pixel_sample_offsets=samples,pixel_samples_per_frame=len(samples),full_pixel_comparison=False,
        nominal_late_frames=sum(q['late_fields']>0 for q in pubs),max_late_fields=max((q['late_fields'] for q in pubs),default=0),
        actual_out_over_one_field=sum(x>FIELD for x in offsets),max_actual_deviation_tstates=max(offsets,default=0),
        bad_actual_intervals=sum(x<5*FIELD-64 or x>7*FIELD+64 for x in intervals),
        late_runs=runs,publications=pubs,actual_phase_tstates=offsets,reads=reads,
        audio_underrun_tstates=underruns,
        rom_sha256=hashlib.sha256((args.fuse.parent/'roms/trdos.rom').read_bytes()).hexdigest())
    report.update(trace_nonce=nonce,trace_nonce_exact=nonces==[nonce],
        debugger_script_sha256=hashlib.sha256(args.output.with_suffix('.debugger.txt').read_bytes()).hexdigest(),
        trace_sha256=hashlib.sha256(args.output.with_suffix('.trace.txt').read_bytes()).hexdigest())
    if args.slot_queue:
        report['fixture_installer']=install_report
        report['partial_slot_consumption']=m['partial_slot_consumption']
        if args.uncontended_frame:report['uncontended_frame']=m['uncontended_frame']
        if args.compiled_masks:report['compiled_masks']=m['compiled_masks']
        if m.get('cached_huffman_byte'):report['cached_huffman_byte']=m['cached_huffman_byte']
        if args.inline_literals:report['inline_literals']=m['inline_literals']
        if args.demand_decode:report['demand_decode']=m['demand_decode']
        if args.idle_masks:
            report['idle_masks']=m['idle_masks']
        if target_samples:
            report['native_sample_trace']='target-only; same 80 offsets and per-disk parity as the two-screen trace'
        report['slot_queue_fixture']={k:v for k,v in m.items() if k.startswith('slot_queue_') or k in
            ('queue_labels','producer_labels','decoder_labels','clock_labels','packet_labels','native_ready_pcs')}
    if args.continuation_snapshot:
        report.update(continuation_snapshot_sha256=hashlib.sha256(args.continuation_snapshot.read_bytes()).hexdigest(),
            continuation_disk_accepted_tstates=continuation_accepted)
    if args.trace_fields or args.trace_paging: report['irq_entries']=irq_entries
    if args.trace_fields: report['field_samples']=field_samples
    if args.trace_pipeline:report['pipeline_events']=pipeline_events
    if args.trace_paging: report['paging_samples']=paging_samples
    if args.export_warm_ram:
        report.update(warm_ram_bytes=len(warm_ram),warm_ram_sha256=hashlib.sha256(warm_ram).hexdigest(),
            warm_ram_export_complete=warm_dump_complete and len(warm_ram)==49152)
        if complete:
            args.export_warm_ram.parent.mkdir(parents=True,exist_ok=True)
            args.export_warm_ram.write_bytes(warm_ram)
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('reads','publications','actual_phase_tstates','audio_underrun_tstates','audio_tick_tstates','seek_calls','pixel_sample_offsets','late_runs','errors','irq_entries','field_samples','paging_samples','pipeline_events','slot_queue_fixture','uncontended_frame')}),flush=True)
    if not complete: raise SystemExit(1)


if __name__=='__main__': main()
