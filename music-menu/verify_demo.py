"""Verify the complete native demo playlist, pictures, controls and cold Fuse.

Functional CPU checks use explicit ROM/disk/IRQ stubs. The independent Fuse
qualification uses actual ROM, rotational disk latency, ULA interrupts and
port transactions, including during foreground ZX0 decoding and transitions.
"""
import argparse
from collections import Counter
import gzip
import json
import re
from pathlib import Path
import sys

from build import HERE, ROOT, FIELD_T, MUTE_WRITES, sha
from demo_assets import DISK_NAME, NAMES
from verify import Machine, decode_records
from verify import run_fuse
sys.path.insert(0,str(ROOT/'libraries/lzsa/src'))


def boot(machine, disk):
    m, labels = machine.cpu,machine.labels
    # BASIC's SCREEN$ step, before RANDOMIZE USR32768, is explicit in this
    # functional shim. Cold Fuse separately executes the actual BASIC loader.
    loading = (HERE/'artwork/city.scr').read_bytes()
    assert loading in disk
    m.set_memory_block(0x4000,loading)
    m.pc = labels['start']
    stops = (0x3D13,0x10,0x0DAF,0x1601,labels['ready'])
    for address in stops:
        m.set_breakpoint(address)
    reads = []
    while m.pc != labels['ready']:
        m.ticks_to_stop = 5000000
        flags = m.run()
        if m.pc==0x3D13:
            assert m.b==1 and m.c==5
            sector = (m.de>>8)*16+(m.de&255)
            m.set_memory_block(m.hl,disk[sector*256:(sector+1)*256])
            reads.append((machine.bank,sector,m.hl))
            m.pc = int.from_bytes(m.memory[m.sp:m.sp+2],'little')
            m.sp += 2
        elif m.pc in (0x10,0x0DAF,0x1601):
            machine.rom_stub(m.pc)
        elif flags&m._TICKS_LIMIT_HIT:
            raise AssertionError('Native startup stalled')
    for address in stops:
        m.clear_breakpoint(address)
    assert bytes(m.memory[0x4000:0x5B00])==loading,'Loading SCR must remain visible'
    assert m.memory[labels['menu_visible']]==0
    assert m.sp==0xBD00
    return reads


def native(output):
    meta = json.loads((output/'build.json').read_text())
    labels = meta['player_labels']
    disk = (output/DISK_NAME).read_bytes()
    blob = (output/'assembly/player.bin').read_bytes()
    assert sha(disk)==meta['trd_sha256'] and sha(blob)==meta['player_sha256']
    # The real ROM font is optional in the shim; Fuse authenticates stock text.
    machine = Machine(blob,labels)
    reads = boot(machine,disk)
    expected_reads = [(s['bank'],sector,0xC000+(sector-s['sector'])*256)
        for s in meta['cache_sections'] for sector in range(s['sector'],s['sector']+s['sectors'])]
    assert reads==expected_reads
    rows = [decode_records((output/f'{s["song"]}.rows').read_bytes())[0] for s in meta['songs']]
    schedule = [{r['tick']:r['writes'] for r in rs} for rs in rows]
    starts = [0,meta['songs'][0]['ticks']+meta['songs'][0]['additional_pause_fields']]
    starts.append(starts[1]+meta['songs'][1]['ticks']+meta['songs'][1]['additional_pause_fields'])
    irq_times,foreground = Counter(),Counter()
    pictures,decode_times = [],[]
    for field in range(starts[2]+101):
        expected = []
        for which,start in enumerate(starts):
            index = which%2
            local = field-start
            if local==0:
                expected.extend(MUTE_WRITES)
            expected.extend(schedule[index].get(local,[]))
            if local==meta['songs'][index]['ticks']:
                expected.extend(MUTE_WRITES)
        before = len(machine.writes)
        irq_times[machine.call('irq')] += 1
        assert machine.writes[before:]==expected,('AY mismatch',field,machine.writes[before:],expected)
        before_picture = machine.cpu.memory[labels['current_picture']]
        cost = machine.run_to(labels['field_start'],[labels['menu_frame_done']],3000000)
        foreground[cost] += 1
        current = machine.cpu.memory[labels['current_picture']]
        if current != before_picture:
            name = NAMES[current]
            path = HERE/'artwork'/f'{name}.scr'
            if not path.exists():
                path = HERE/'artwork/proposals'/f'{name}.scr'
            assert bytes(machine.cpu.memory[0x4000:0x5B00])==path.read_bytes(),('SCR mismatch',field,name)
            pictures.append(dict(field=field,name=name,sha256=sha(path.read_bytes())))
        assert machine.cpu.memory[labels['menu_visible']]==0
        assert machine.cpu.sp==0xBD00
    assert set(p['name'] for p in pictures)==set(NAMES)
    assert all(not (value&24) for value in machine.beeper)
    # Every decoder profile is timed on actual complete art, including entry
    # setup and exact EOF. Both tiny ZX0 variants are compared on identical input.
    from zx0.small import build as small
    from zx0.block import build as block
    from lzsa.compact import build as compact
    profiles = [('zx0-smc',small('smc',core=0x8D00,core_limit=0x9000)),
                ('zx0-gamma-jp',small('gamma-jp',core=0x8D00,core_limit=0x9000)),
                ('zx0-standard',block('standard',core=0x8D00,core_limit=0x9000)),
                ('lzsa-compact-eof',compact(core=0x8D00,core_limit=0x9000,compact_eof=True))]
    codec_results = []
    for profile,(regions,ls,inventory) in profiles:
        times=[]
        for picture in meta['pictures']:
            test = Machine(blob,labels)
            for address,data in regions:
                test.cpu.set_memory_block(address,data)
            extension = 'lzsa' if profile.startswith('lzsa') else 'zx0'
            path = HERE/'artwork/packed'/f'{picture["name"]}.{extension}'
            if not path.exists():
                # LZSA is a comparison fixture generated by measure_packing.py.
                path = output.parent/'packing'/path.name
            data=path.read_bytes()
            test.cpu.set_memory_block(0xC000,data)
            test.cpu.hl,test.cpu.de = 0xC000,0xA000
            test.cpu.sp = 0xBCFE
            test.cpu.memory[0xBCFE:0xBD00]=b'\xff\x7f'
            entry = ls.get('dzx0_standard',ls.get('start'))
            t = test.run_to(entry,[0x7FFF],3000000)
            from slides import picture_columns
            screen_path=HERE/'artwork'/f'{picture["name"]}.scr'
            if not screen_path.exists():
                screen_path=HERE/'artwork/proposals'/screen_path.name
            assert bytes(test.cpu.memory[0xA000:0xB680])==b''.join(picture_columns(screen_path.read_bytes()))
            times.append(dict(name=picture['name'],tstates=t,compressed_bytes=len(data)))
        stack=6 if profile=='zx0-standard' else inventory['caller_stack_bytes']
        codec_results.append(dict(profile=profile,code_bytes=sum(len(b) for _,b in regions),
            caller_stack_bytes=stack,service_bytes=sum(len(b) for _,b in regions)+stack,images=times))
    controls = check_controls(machine)
    report = dict(trd_sha256=meta['trd_sha256'],complete_playlist=True,fields=starts[2]+101,
        track_starts=starts,full_durations_and_registers_exact=True,pictures_completed=pictures,
        no_disk_reads_after_ready=True,no_beeper_audio=True,menu_hidden_without_input=True,
        irq_body_tstates=dict(sorted(irq_times.items())),foreground_tstates=dict(sorted(foreground.items())),
        decoder_comparison=codec_results,controls=controls,
        scope='Functional native Z80 with ROM/disk/IRQ stubs; physical timing is qualified separately in Fuse.')
    (output/'native-demo.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(native_complete=True,fields=report['fields'],pictures=len(pictures),max_irq=max(irq_times),max_foreground=max(foreground))))
    return report


def check_controls(machine):
    labels,m = machine.labels,machine.cpu
    # call() has a small legacy default; use an explicit budget for screen copies.
    def call(name):
        m.sp=0xBCFE
        m.memory[0xBCFE:0xBD00]=b'\xff\x7f'
        return machine.run_to(labels[name],[0x7FFF],3000000)
    machine.ports={0x00FE:30,0x7FFE:30}
    call('ui_tick')
    assert m.memory[labels['menu_visible']]==1
    assert m.memory[labels['queued_command']]==0,'Space revealing menu must not stop'
    call('ui_tick')
    assert m.memory[labels['queued_command']]==0
    machine.ports={}
    call('ui_tick')
    machine.ports={0x00FE:27,0xDFFE:27}
    call('ui_tick')
    assert m.memory[labels['pictures_enabled']]==0
    machine.ports={}
    call('ui_tick')
    machine.ports={0x00FE:30,0x7FFE:30}
    call('ui_tick')
    assert m.memory[labels['queued_command']]==3
    machine.call('irq')
    assert m.memory[labels['playing']]==255 and m.memory[labels['pause_remaining']]==0
    machine.ports={}
    call('ui_tick')
    machine.ports={0x00FE:29,0xF7FE:29}
    call('ui_tick')
    assert m.memory[labels['queued_command']]==2
    machine.call('irq')
    assert m.memory[labels['playing']]==1
    return dict(any_key_opens_menu=True,held_space_swallowed=True,checkbox_toggles=True,
                menu_space_stops=True,manual_song_switch=True)


def fuse_check(fuse,output,*,captured=False):
    meta=json.loads((output/'build.json').read_text())
    labels=meta['player_labels']
    folder=output/'fuse-demo'
    folder.mkdir(exist_ok=True)
    stamp=f'spectrum:frames*{FIELD_T}+ula:tstates'
    lines=['base 10','set $live 0','set $segment 0','set $ticks 0']
    widths={}
    event_id=0
    def event(where,tag,expressions=(),after=(),condition=None):
        nonlocal event_id
        event_id+=1
        lines.extend((f'br {where}',f'com {event_id}',f'pr {tag}'))
        widths[tag]=len(expressions)
        lines.extend('pr '+e for e in expressions)
        lines.extend(after)
        lines.extend(('co','end'))
        if condition:
            lines.append(f'cond {event_id} {condition}')
    # Fixed evenly distributed samples cover bitmap and attribute memory;
    # native replay checks every byte of every completed picture independently.
    samples=list(range(0,6912,13))
    screen_expressions=[f'[{0x4000+i}]' for i in samples]
    event(labels['ready'],100,[stamp,'ula:mem7ffd',f'[{labels["menu_visible"]}]',*screen_expressions],['set $live 1'])
    event(labels['menu_snapshot_done'],102,[stamp,'ula:mem7ffd'])
    event(labels['disk_call'],101,[stamp,'z80:de','z80:hl','z80:b','$live','ula:mem7ffd'])
    event(labels['song_started'],111,[stamp,f'[{labels["playing"]}]'],['set $segment $segment+1','set $ticks 0'])
    event(labels['music_tick'],103,[stamp,'$segment','$ticks+1'],['set $ticks $ticks+1'])
    event(labels['record_event'],104,[stamp,'$segment','$ticks',f'[{labels["raw_position"]}]',f'[{labels["raw_position"]+1}]'])
    event('port write 49149',105,[stamp,'$segment','$ticks','z80:a','z80:h'],condition=f'z80:pc=={labels["ay_out"]+2}')
    event(labels['irq'],106,[stamp],condition='$live==1')
    event(labels['audio_done'],108,[stamp],condition='$live==1')
    event('port write 254',107,['z80:a'],condition='$live==1')
    event(labels['picture_complete'],112,[stamp,f'[{labels["current_picture"]}]',*screen_expressions])
    event(labels['show_menu'],113,[stamp])
    event(labels['menu_frame_done'],200,[stamp],['ex 77'],condition='$segment==3 && $ticks>=100')
    script='\n'.join(lines)
    assert len(script)<30000,'Windows command-line budget'
    if captured:
        saved=json.loads((output/'fuse-demo.json').read_text())
        assert saved['trd_sha256']==meta['trd_sha256']
        assert (folder/'debugger.txt').read_text()==script+'\n'
        trace=gzip.decompress((folder/'trace.txt.gz').read_bytes())
        assert sha(trace)==saved['trace_sha256']
    else:
        (folder/'debugger.txt').write_text(script+'\n',encoding='ascii')
        result,trace=run_fuse(fuse,output,script,timeout=240)
        assert result.returncode==77,('Fuse failed',result.returncode,result.stderr[:200])
    # Retain only the numeric debugger events consumed by the verifier. Fuse
    # banners and unrelated console messages can contain local metadata; they
    # are not needed for the proof and are excluded from retained evidence.
    trace=b'\n'.join(m.group(1) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace))+b'\n'
    (folder/'trace.txt.gz').write_bytes(gzip.compress(trace,mtime=0))
    numbers=[int(m.group(1),0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace)]
    events={tag:[] for tag in widths}
    pos=0
    while pos<len(numbers):
        tag=numbers[pos]
        assert tag in widths,('Unexpected trace tag',tag)
        width=widths[tag]
        events[tag].append(numbers[pos+1:pos+1+width])
        pos+=width+1
    assert len(events[100])==len(events[102])==len(events[200])==1
    assert events[102][0][1]==31,'Menu must be prepared behind shadow splash'
    assert events[100][0][1]&8==0 and events[100][0][2]==0
    city=(HERE/'artwork/city.scr').read_bytes()
    assert events[100][0][3:]==[city[i] for i in samples]
    assert events[113]==[],'Menu must never appear during unattended startup/playback'
    expected_reads=[[sector//16*256+sector%16,0xC000+(sector-s['sector'])*256,1,0,16+s['bank']]
        for s in meta['cache_sections'] for sector in range(s['sector'],s['sector']+s['sectors'])]
    assert [row[1:] for row in events[101]]==expected_reads
    assert [r[1] for r in events[111]]==[0,1,0]
    first_frame=events[111][0][0]//FIELD_T
    expected_starts=[0,meta['songs'][0]['ticks']+meta['songs'][0]['additional_pause_fields']]
    expected_starts.append(expected_starts[1]+meta['songs'][1]['ticks']+meta['songs'][1]['additional_pause_fields'])
    assert [r[0]//FIELD_T-first_frame for r in events[111]]==expected_starts
    segments=[]
    for segment,index in ((1,0),(2,1),(3,0)):
        song=meta['songs'][index]
        records,_=decode_records((output/f'{song["song"]}.rows').read_bytes())
        ticks=[row for row in events[103] if row[1]==segment]
        count=song['ticks'] if segment<3 else len(ticks)
        assert len(ticks)==count+(segment<3)
        assert [r[2] for r in ticks]==list(range(1,len(ticks)+1))
        assert all(b[0]//FIELD_T==a[0]//FIELD_T+1 for a,b in zip(ticks,ticks[1:])),('Skipped AY field',segment)
        actual=[r[2:] for r in events[105] if r[1]==segment]
        want=[[record['tick']+1,reg,value] for record in records if record['tick']<count for reg,value in record['writes']]
        assert actual==want,('Fuse AY mismatch',segment,len(actual),len(want))
        observed=[r for r in events[104] if r[1]==segment]
        expected=[r for r in records if r['tick']<count]
        assert len(observed)==len(expected)
        for a,e in zip(observed,expected):
            assert a[2]==e['tick']+1 and a[3]+256*a[4]==e['end']
        segments.append(dict(song=song['song'],fields=count,complete=segment<3,
                             register_writes=len(actual),registers_exact=True))
    irqs=[r[0] for r in events[106]]
    assert all(b//FIELD_T==a//FIELD_T+1 for a,b in zip(irqs,irqs[1:])), 'Skipped real ULA IRQ'
    assert len(events[108])==len(irqs)
    audio=[end[0]-start for start,end in zip(irqs,events[108])]
    assert max(audio)<FIELD_T
    for row in events[112]:
        name=NAMES[row[1]]
        path=HERE/'artwork'/f'{name}.scr'
        if not path.exists():
            path=HERE/'artwork/proposals'/path.name
        screen=path.read_bytes()
        assert row[2:]==[screen[i] for i in samples],('Fuse image samples',name)
    assert set(r[1] for r in events[112])==set(range(len(NAMES)))
    assert events[107] and all(not(r[0]&24) for r in events[107])
    report=dict(trd_sha256=meta['trd_sha256'],cold_boot=True,complete_playlist=True,
        segments=segments,track_start_fields=expected_starts,no_ula_irq_skipped=True,
        irq_count=len(irqs),max_irq_to_audio_complete_tstates=max(audio),
        loading_screen_samples=len(samples),menu_prepared_behind_shadow_screen=True,
        menu_hidden_without_input=True,picture_completions=len(events[112]),
        picture_samples_checked=len(events[112])*len(samples),all_pictures_completed=True,
        startup_sector_reads=len(expected_reads),disk_reads_after_ready=0,no_beeper_audio=True,
        trace_sha256=sha(trace),script_sha256=sha(script.encode()),
        trace_format='Numeric debugger events only; non-event console banners excluded.',
        scope='Complete cold real128 Fuse ROM/Beta Disk/ULA run: both full tracks, pauses, return to Lumiere; actual AY ports and sampled completed screens.')
    (output/'fuse-demo.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/expedition-33-demo')
    parser.add_argument('--fuse',type=Path)
    parser.add_argument('--captured',action='store_true',help='Authenticate and recheck existing complete matching Fuse evidence')
    args=parser.parse_args()
    sys.path.insert(0,str(ROOT/'libraries/lzsa/src'))
    if args.fuse:
        fuse_check(args.fuse,args.output.resolve(),captured=args.captured)
    else:
        native(args.output.resolve())
