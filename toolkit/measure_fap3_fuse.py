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
    args=p.parse_args(); m=json.loads(args.metadata.read_text()); lab=m['player_labels']
    if m.get('required_trdos_sha256') and hashlib.sha256((args.fuse.parent/'roms/trdos.rom').read_bytes()).hexdigest()!=m['required_trdos_sha256']:
        raise ValueError('fast reader requires its verified TR-DOS ROM')
    lines=['base 10','set $running 0']; widths={}; events=[]
    def event(pc,tag,expressions,stop=False):
        index=len(events)+1; events.append((pc,tag)); widths[tag]=len(expressions)
        lines.extend([f'breakpoint 0x{pc:04x}',f'commands {index}',f'print {tag}'])
        if tag==100: lines.append('set $running 1')
        lines.extend('print '+e for e in expressions)
        lines.extend(['exit 77' if stop else 'continue','end'])
        if tag!=100: lines.append(f'condition {index} $running == {0 if tag==90 else 1}')
    def mem(address): return f'[{address}]+256*[{address+1}]'
    stamp='spectrum:frames*70908+ula:tstates'
    event(0x6000,90,[stamp])
    event(lab['start'],100,[stamp])
    samples=sorted(set([i*97%6912 for i in range(56)]+[6144+i*31 for i in range(24)]))
    sample_expr=[]
    # Sample after drawing returns to the bank-7 clock; publication itself
    # is allowed to interrupt a disk read with another bank at C000.
    for address in (0x4000,0xc000): sample_expr += [f'[{address+i}]' for i in samples]
    # Stop after OUT has executed: includes real I/O contention, without
    # adding an assumed 12 T to the preceding instruction boundary.
    event(lab['publish_out']+2,150,[stamp,'z80:a',mem(lab['elapsed_fields']),mem(lab['late_fields'])])
    for index,pc in enumerate(m['native_ready_pcs']): event(pc,151+index,[stamp,'ula:mem7ffd']+sample_expr)
    event(lab['audio_write_loop'],140,[stamp,'[z80:hl]','[z80:hl+1]'])
    event(lab['audio_tick_done'],143,[stamp])
    event(lab['audio_tick_empty'],144,[stamp])
    event(lab['disk_full_call'],102,[stamp,'z80:hl',mem(m['disk_labels']['disk_position'])])
    # A whole consumed sector was replaced at saved write_high. Read its
    # exact bytes before the decoder resumes; compact four bytes per print.
    base=f'256*[{m["disk_labels"]["write_high"]}]'
    sector_expr=['+'.join(f'{256**k}*[{base}+{i+k}]' for k in range(4)) for i in range(0,256,4)]
    event(lab['disk_return'],103,[stamp]+sector_expr)
    if 'fast_read_enter' in lab:
        event(lab['fast_read_enter'],110,[stamp,'z80:hl',mem(m['disk_labels']['disk_position'])])
        event(lab['fast_disk_return'],111,[stamp]+sector_expr)
        event(lab['fast_read_retry'],112,[stamp])
    if 'seek_enter' in lab:
        event(lab['seek_side_enter'],120,[stamp])
        event(lab['seek_side_return'],121,[stamp])
        event(lab['seek_enter'],122,[stamp])
        event(lab['seek_return'],123,[stamp])
    if 'keepalive_enter' in m.get('deferred_labels',{}):
        event(m['deferred_labels']['keepalive_enter'],124,[stamp])
        event(m['deferred_labels']['keepalive_return'],125,[stamp])
    event(lab['finished'],199,[stamp,mem(lab['published']),mem(lab['audio_ticks_played']),mem(lab['audio_underruns'])]+
        [f'[{base+i}]' for base in (0x50e0,0x51e0,0xd0e0,0xd1e0) for i in range(32)],True)
    for name in ('fatal','zx0_fatal'): event(lab[name],198,[stamp,'z80:pc'],True)
    if len('\n'.join(lines))>29000: raise ValueError('Windows command line too long')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix('.debugger.txt').write_text('\n'.join(lines))
    env=dict(os.environ,SDL_VIDEODRIVER='dummy')
    command=[str(args.fuse.resolve()),'--no-sound','--no-autosave-settings','--no-confirm-actions',
        '--speed','10000','--machine','128','--beta128','--debugger-command','\n'.join(lines),str(args.trd.resolve())]
    started=time.monotonic()
    completed=subprocess.run(command,cwd=args.fuse.parent,env=env,capture_output=True,
        startupinfo=hidden_startupinfo(),timeout=args.timeout)
    output=completed.stdout.decode(errors='replace')
    if not re.search(r'^\s*\d+\s*$',output,re.M) and (args.fuse.parent/'stdout.txt').exists():
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
    image=args.trd.read_bytes(); pending=None; errors=[]; native_count=0; retries=0; read_kind=None
    boot_started=player_started=None
    seek_pending=None; seek_calls=[]
    with np.load(args.states,allow_pickle=False) as data: states=data['states']
    for tag,v in parsed:
        if tag==90:
            if boot_started is None: boot_started=v[0]
        elif tag==100: player_started=v[0]
        elif tag==150:
            pubs.append(dict(tstate=v[0],page=v[1],field=v[2],late_fields=v[3]))
        elif tag in (151,152):
            frame=m['frame_start']+native_count
            samples_at=v[2:2+len(samples)] if native_count%2 else v[2+len(samples):]
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
        elif tag in (102,110):
            if pending is not None: raise ValueError('overlapping ROM reads')
            pending=v; read_kind='trdos' if tag==102 else 'direct503'
        elif tag in (103,111):
            # Successful direct reads jump to the shared full-read epilogue.
            # Its second breakpoint is not another ROM return/read attempt.
            if tag==103 and pending is None and reads and reads[-1]['kind']=='direct503' and not reads[-1]['retried']:
                continue
            if pending is None: raise ValueError('return without ROM entry')
            linear=(pending[2]>>8)*16+(pending[2]&255)
            actual=b''.join((value&0xffffffff).to_bytes(4,'little') for value in v[1:])
            reads.append(dict(sector=linear,tstates=v[0]-pending[0],kind=read_kind,
                bytes_exact=actual==image[linear*256:(linear+1)*256],retried=False,
                start_tstate=pending[0],end_tstate=v[0],entry_tstates=17 if tag==103 else 10)); pending=None
        elif tag==112:
            if not reads or reads[-1]['kind']!='direct503': raise ValueError('retry without direct read')
            retries+=1; reads[-1]['retried']=True
        elif tag in (120,122,124):
            if seek_pending is not None: raise ValueError('overlapping seek calls')
            seek_pending=(tag,v[0])
        elif tag in (121,123,125):
            if seek_pending is None or seek_pending[0]!=tag-1: raise ValueError('unmatched seek return')
            seek_calls.append(dict(kind={121:'side',123:'seek',125:'keepalive'}[tag],tstates=v[0]-seek_pending[1]))
            seek_pending=None
        elif tag==199: final=v
        elif tag==198: failure=v
    for read in reads:
        if not read['retried'] and not read['bytes_exact']:
            errors.append(dict(sector=read['sector'],error='accepted disk bytes differ'))
    accepted=[q['sector'] for q in reads if not q['retried']]
    positions=list(disk_layout.positions(m['video_sectors'],m['video_start_sector']%16)) if m.get('interleaved') else list(range(m['video_sectors']))
    wanted_sectors=[m['video_start_sector']+p for p in positions[min(256,m['video_sectors']):]]
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
    complete=bool(final and final[1]==m['frames'] and final[2]==6*m['frames'] and len(pubs)==m['frames']
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
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('reads','publications','actual_phase_tstates','audio_underrun_tstates','audio_tick_tstates','seek_calls','pixel_sample_offsets','late_runs','errors')}),flush=True)
    if not complete: raise SystemExit(1)


if __name__=='__main__': main()
