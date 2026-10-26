"""Verify complete AY-only playback, live input, cached switching and chip I/O."""
import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from types import SimpleNamespace

from build import BANKS, FIELD_T, ROOT, REGISTER_ORDER, MUTE_WRITES, sha


def decode_records(data):
    records = []
    position = 0
    tick = 0
    while True:
        if position>=len(data):
            raise ValueError('Missing EOF')
        duration = data[position]
        position += 1
        if not duration:
            if position!=len(data):
                raise ValueError('Trailing bytes after EOF')
            return records,tick
        if position+2>len(data):
            raise ValueError('Truncated register mask')
        mask = int.from_bytes(data[position:position+2],'little')
        position += 2
        if mask&0xC000:
            raise ValueError('Invalid register mask')
        writes = []
        for slot,reg in enumerate(REGISTER_ORDER):
            if mask&(1<<slot):
                if position>=len(data):
                    raise ValueError('Truncated register value')
                value = data[position]
                position += 1
                if (reg in (1,3,5) and value>15 or reg==6 and value>31
                    or reg==7 and value>63 or reg in (8,9,10) and value>31
                    or reg==13 and value>15):
                    raise ValueError('Invalid AY register value')
                writes.append((reg,value))
        records.append(dict(tick=tick,duration=duration,writes=writes,end=position))
        tick += duration


def unpack(data):
    records,ticks = decode_records(data)
    frames = []
    state = bytearray(14)
    state[13] = 255
    for record in records:
        state[13] = 255
        for register,value in record['writes']:
            state[register] = value
        frames.append(bytes(state))
        for _ in range(record['duration']-1):
            state[13] = 255
            frames.append(bytes(state))
    assert len(frames)==ticks
    return frames


class Machine:
    """Independent CPU with physical bank swaps and explicit input ports."""
    def __init__(self, blob, labels):
        from z80 import Z80Machine
        self.cpu = Z80Machine()
        self.cpu.memory[:] = bytes([0xA5])*65536
        self.cpu.set_memory_block(0x8000, blob)
        self.labels = labels
        self.banks = {b: bytearray([0xA5])*16384 for b in BANKS}
        self.bank = 0
        self.ports = {}
        self.writes = []
        self.pages = []
        self.beeper = []
        self.ay_register = 0
        self.cpu.set_output_callback(self.output)
        self.cpu.set_input_callback(lambda port: self.ports.get(port, 255))
        self.cpu.sp = 0xBD00

    def output(self, port, value):
        if port == 0x7FFD:
            self.banks[self.bank][:] = self.cpu.memory[0xC000:]
            self.bank = value & 7
            self.cpu.set_memory_block(0xC000, self.banks[self.bank])
            self.pages.append(self.bank)
        elif port == 0xFFFD:
            self.ay_register = value
        elif port == 0xBFFD:
            self.writes.append((self.ay_register, value))
        elif port & 255 == 254:
            self.beeper.append(value)
        else:
            raise AssertionError(f'Unknown output port {port:04X}')

    def byte(self, name, value):
        self.cpu.memory[self.labels[name]] = value

    def word(self, name, value):
        self.cpu.memory[self.labels[name]:self.labels[name]+2] = value.to_bytes(2, 'little')

    def run_to(self, start, ends, limit=20000):
        m = self.cpu
        for address in ends:
            m.set_breakpoint(address)
        m.pc = start
        m.ticks_to_stop = limit
        while m.pc not in ends:
            flags = m.run()
            if flags & m._TICKS_LIMIT_HIT:
                raise AssertionError(f'CPU timeout at {m.pc:04X}')
        for address in ends:
            m.clear_breakpoint(address)
        return limit-m.ticks_to_stop

    def call(self, name):
        self.cpu.sp = 0xBCFE
        self.cpu.memory[0xBCFE:0xBD00] = b'\xFF\x7F'
        return self.run_to(self.labels[name], [0x7FFF])


def boot(machine, disk):
    """Use a documented ROM-read stub for native UI tests; Fuse uses real ROM."""
    m = machine.cpu
    labels = machine.labels
    m.pc = labels['start']
    m.set_breakpoint(0x3D13)
    m.set_breakpoint(labels['menu_ready'])
    reads = []
    while m.pc!=labels['menu_ready']:
        m.ticks_to_stop = 1000000
        flags = m.run()
        if m.pc==0x3D13:
            assert m.b==1 and m.c==5
            sector = (m.de>>8)*16+(m.de&255)
            m.set_memory_block(m.hl,disk[sector*256:(sector+1)*256])
            reads.append((machine.bank,sector,m.hl))
            m.pc = int.from_bytes(m.memory[m.sp:m.sp+2],'little')
            m.sp += 2
        elif flags&m._TICKS_LIMIT_HIT:
            raise AssertionError('Native startup stalled')
    m.clear_breakpoint(0x3D13)
    m.clear_breakpoint(labels['menu_ready'])
    assert m.sp==0xBD00
    return reads


def native_check(output, metadata):
    labels = metadata['player_labels']
    blob = (output/'assembly/player.bin').read_bytes()
    disk = (output/'ZX-Music-Menu.trd').read_bytes()
    results = []
    for index,song in enumerate(metadata['songs']):
        data = (output/f'{song["song"]}.rows').read_bytes()
        records,ticks = decode_records(data)
        scheduled = {r['tick']:r for r in records}
        machine = Machine(blob,labels)
        reads = boot(machine,disk)
        machine.byte('selected',index)
        start = len(machine.writes)
        machine.call('choose')
        assert machine.writes[start:start+14]==list(MUTE_WRITES)
        assert machine.writes[start+14:]==records[0]['writes']
        audio_hist,ui_hist,total_hist = Counter(),Counter(),Counter()
        for tick in range(1,ticks):
            start = len(machine.writes)
            audio = machine.run_to(labels['field_start'],[labels['audio_done']])
            ui = machine.run_to(labels['audio_done'],[labels['menu_frame_done']],30000)
            want = scheduled.get(tick,{}).get('writes',[])
            assert machine.writes[start:]==want,('native AY mismatch',index,tick)
            assert machine.cpu.sp==0xBD00
            audio_hist[audio] += 1
            ui_hist[ui] += 1
            total_hist[audio+ui] += 1
        start = len(machine.writes)
        machine.run_to(labels['field_start'],[labels['menu_frame_done']],30000)
        assert machine.writes[start:]==list(MUTE_WRITES)
        assert machine.cpu.memory[labels['playing']]==255
        assert machine.beeper and set(machine.beeper)=={0},'ULA audio output is forbidden'
        assert max(total_hist)<FIELD_T
        results.append(dict(song=song['song'],complete=True,ticks=ticks,records=len(records),
            register_writes=sum(len(r['writes']) for r in records),registers_exact=True,
            no_beeper_audio=True,full_foreground_menu_replayed=True,stack_balanced=True,
            eof_mutes=True,startup_reads=len(reads),
            audio_service_with_caller_tstates=dict(sorted(audio_hist.items())),
            ui_tstates=dict(sorted(ui_hist.items())),total_foreground_tstates=dict(sorted(total_hist.items()))))
    machine = Machine(blob,labels)
    assert machine.call('irq')==18
    mute_tstates = machine.call('mute')
    assert mute_tstates==1164
    # Authenticate every write-count formula using the real decoder, including
    # a byte crossing between values in the middle of a register-mask record.
    timings = {}
    for count in (0,1,3,13,14):
        fixture = bytes([1])+((1<<count)-1).to_bytes(2,'little')+bytes(count)+b'\0'
        probe = Machine(blob,labels)
        probe.cpu.set_memory_block(0xC000,fixture)
        probe.word('record_pointer',0xC000)
        probe.byte('remaining',0)
        probe.byte('current_bank_index',0)
        elapsed = probe.call('music_tick')
        assert elapsed==1452+164*count,(count,elapsed)
        timings[count] = elapsed
    crossing = Machine(blob,labels)
    crossing.cpu.set_memory_block(0xFFFD,b'\x01\x01\x00')
    crossing.banks[4][0:2] = b'\x09\x00'
    crossing.word('record_pointer',0xFFFD)
    crossing.byte('remaining',0)
    crossing.byte('current_bank_index',0)
    crossing_t = crossing.call('music_tick')
    assert crossing_t==1452+164+185 and crossing.writes==[(0,9)],crossing_t
    return dict(player_sha256=sha(blob),songs=results,irq_handler_tstates=18,
        im2_hardware_entry_tstates=19,mute_tstates=mute_tstates,
        read_byte_ordinary_tstates=75,read_byte_boundary_extra_tstates=185,
        delta_record_tstates=timings,controls=control_check(blob,labels,disk),
        scope='Complete independent Z80 foreground/menu replay; explicit bank swaps and ROM-read stub; Fuse separately cold boots real ROM/floppy.')


def control_check(blob, labels, disk):
    machine = Machine(blob,labels)
    boot(machine,disk)
    def frame(ports):
        machine.ports = ports
        machine.run_to(labels['field_start'],[labels['menu_frame_done']],50000)
        assert machine.cpu.sp==0xBD00
    # Select a song, advance while the live cursor/navigation runs, switch
    # without stopping, verify the other tick-zero writes and no reload.
    frame({0xF7FE:254})
    assert machine.cpu.memory[labels['playing']]==0
    frame({})
    frame({0xEFFE:239})
    assert machine.cpu.memory[labels['selected']]==1 and machine.cpu.memory[labels['playing']]==0
    frame({})
    frame({0xBFFE:254})
    assert machine.cpu.memory[labels['playing']]==1
    mute_count = len(machine.beeper)
    frame({0xBFFE:254})
    assert len(machine.beeper)==mute_count,'Held Enter restarted'
    frame({})
    # Mouse counters wrap, and clicking the first card switches during Alicia.
    machine.byte('mouse_x',80)
    machine.byte('mouse_y',71)
    machine.byte('mouse_raw_x',250)
    machine.byte('mouse_raw_y',2)
    machine.byte('mouse_button',2)
    frame({0xFBDF:2,0xFFDF:254,0xFADF:253})
    assert machine.cpu.memory[labels['playing']]==0
    assert machine.cpu.memory[labels['mouse_x']]==88 and machine.cpu.memory[labels['mouse_y']]==75
    frame({})
    frame({0x7FFE:254})
    assert machine.cpu.memory[labels['playing']]==255
    frame({})
    assert set(machine.beeper)=={0}
    return dict(keyboard_switch_during_playback=True,navigation_preserves_playback=True,
        enter_switches_without_stop=True,held_enter_debounced=True,mouse_switch_during_playback=True,
        mouse_counter_wrap=True,space_stop=True,no_beeper_audio=True)


def fuse_check(fuse, output, metadata, index, *, captured=False):
    """Cold boot, switch twice through live menu dispatch, finish a whole song.

    At key_changed the debugger supplies a command instead of a hardware key.
    Native tests separately exercise actual input ports. Player/cache/ROM and
    audio instructions are never patched. Both preliminary segments last100
    ticks; the final segment starts from tick zero and reaches real EOF.
    """
    song = metadata['songs'][index]
    labels = metadata['player_labels']
    folder = output/'fuse'/song['song']
    folder.mkdir(parents=True,exist_ok=True)
    lines = ['base 10','set $live 0','set $segment 0','set $ticks 0']
    widths = {}
    event_id = 0
    stamp = f'spectrum:frames*{FIELD_T}+ula:tstates'
    def event(where,tag=None,expressions=(),after=(),condition=None):
        nonlocal event_id
        event_id += 1
        lines.extend((f'br {where}',f'com {event_id}'))
        if tag is not None:
            widths[tag] = len(expressions)
            lines.append(f'pr {tag}')
            lines.extend('pr '+e for e in expressions)
        lines.extend(after)
        lines.extend(('co','end'))
        if condition:
            lines.append(f'cond {event_id} {condition}')
    event(labels['ready'],100,[stamp],['set $live 1'])
    event(labels['disk_call'],101,[stamp,'z80:de','z80:hl','z80:b','$live','ula:mem7ffd'])
    event(labels['key_changed'],110,[stamp,'$segment'],
        [f'set z80:a {index+1}+($segment==1)*{1 if index==0 else -1}'],
        '$segment==0 || ($segment<3 && $ticks>=100)')
    event(labels['song_started'],111,[stamp,f'[{labels["playing"]}]'],
        ['set $segment $segment+1','set $ticks 0'])
    event(labels['music_tick'],103,[stamp,'$segment','$ticks+1'],['set $ticks $ticks+1'])
    event(labels['record_event'],104,[stamp,'$segment','$ticks',
        f'[{labels["record_pointer"]}]',f'[{labels["record_pointer"]+1}]',
        f'[{labels["current_bank_index"]}]'])
    # no_write is the instruction immediately after OUT, and skipped mask bits
    # jump there too. Observe actual port transactions, not that shared join.
    event('port write 49149',105,[stamp,'$segment','$ticks','z80:a','z80:h'],
        condition=f'z80:pc=={labels["ay_out"]+2}')
    event(labels['mute_out']+2,108,['z80:a','z80:e'],condition='$live==1')
    event(labels['irq'],106,[stamp],condition='$live==1')
    event('port write 254',107,['z80:a'],condition='$live==1')
    event(labels['field_start'],120,[stamp],condition='$live==1')
    event(labels['menu_frame_done'],121,[stamp],condition='$live==1')
    event(labels['menu_frame_done'],200,[stamp,f'[{labels["playing"]}]'],['ex 77'],
        f'$segment==3 && $ticks=={song["ticks"]+1}')
    script = '\n'.join(lines)
    if captured:
        saved = json.loads((output/f'fuse-{song["song"]}.json').read_text())
        assert saved['trd_sha256']==metadata['trd_sha256']
        assert (folder/'debugger.txt').read_text()==script+'\n'
        trace = gzip.decompress((folder/'trace.txt.gz').read_bytes())
        assert sha(trace)==saved['trace_sha256']
        result = SimpleNamespace(returncode=77,stderr=(folder/'stderr.txt').read_bytes())
    else:
        (folder/'debugger.txt').write_text(script+'\n',encoding='ascii')
        result,trace = run_fuse(fuse,output,script)
        (folder/'trace.txt.gz').write_bytes(gzip.compress(trace,mtime=0))
        (folder/'stderr.txt').write_bytes(result.stderr)
    assert result.returncode==77,('Fuse failed',result.returncode,result.stderr[:300])
    numbers = [int(m.group(1),0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace)]
    events = {tag:[] for tag in widths}
    position = 0
    while position<len(numbers):
        tag = numbers[position]
        assert tag in widths,('Trace tag',tag)
        width = widths[tag]
        events[tag].append(numbers[position+1:position+1+width])
        position += width+1
    assert len(events[100])==len(events[200])==1 and events[200][0][1]==255
    assert [r[1] for r in events[111]]==[index,1-index,index]
    expected_reads = []
    for section in metadata['cache_sections']:
        for sector in range(section['sector'],section['sector']+section['sectors']):
            expected_reads.append([(sector//16)*256+sector%16,0xC000+(sector-section['sector'])*256,
                                   1,0,16+section['bank']])
    assert [r[1:] for r in events[101]]==expected_reads
    assert events[107] and all(r==[0] for r in events[107]),'Beeper output detected'
    assert events[108]==[list(pair) for pair in MUTE_WRITES]*4
    segment_reports = []
    for segment,which in enumerate((index,1-index,index),1):
        item = metadata['songs'][which]
        records,total_ticks = decode_records((output/f'{item["song"]}.rows').read_bytes())
        count = total_ticks if segment==3 else 100
        expected_ay = [[record['tick']+1,reg,value] for record in records if record['tick']<count
                       for reg,value in record['writes']]
        actual_ay = [r[2:] for r in events[105] if r[1]==segment]
        assert actual_ay==expected_ay,('Fuse AY mismatch',segment,len(actual_ay),len(expected_ay))
        ticks = [r[0] for r in events[103] if r[1]==segment]
        assert len(ticks)==count+(segment==3)
        assert all(b//FIELD_T==a//FIELD_T+1 for a,b in zip(ticks,ticks[1:])),('Missed music field',segment)
        observed = [r for r in events[104] if r[1]==segment]
        expected_records = [r for r in records if r['tick']<count]
        assert len(observed)==len(expected_records)
        for actual,expected in zip(observed,expected_records):
            assert actual[2]==expected['tick']+1
            ptr = actual[3]+actual[4]*256
            absolute = ((actual[5]+1)*16384 if ptr==0 else actual[5]*16384+ptr-0xC000)
            assert absolute==item['offset']+expected['end'],'Bank/cursor mismatch'
        segment_reports.append(dict(song=item['song'],ticks=count,complete=segment==3,
            register_writes=len(actual_ay),records=len(observed),registers_exact=True))
    irqs = [r[0] for r in events[106]]
    assert all(b//FIELD_T==a//FIELD_T+1 for a,b in zip(irqs,irqs[1:])), 'Skipped ULA IRQ'
    assert len(events[120])==len(events[121])
    foreground = [end[0]-start[0] for start,end in zip(events[120],events[121])]
    assert foreground and min(foreground)>0 and max(foreground)<FIELD_T
    switch_latencies = [start[0]-request[0] for start,request in zip(events[111],events[110])]
    assert all(0<=value<FIELD_T for value in switch_latencies)
    first_write,complete_state = [],[]
    for segment,request in enumerate(events[110],1):
        writes = [r[0] for r in events[105] if r[1]==segment and r[2]==1]
        first_write.append(writes[0]-request[0])
        complete_state.append(writes[-1]-request[0])
    assert all(0<value<FIELD_T for value in first_write+complete_state)
    return dict(song=song['song'],trd_sha256=metadata['trd_sha256'],complete=True,cold_boot=True,
        full_song_ticks=song['ticks'],live_menu_switches=2,segments=segment_reports,
        startup_reads=len(expected_reads),disk_reads_after_ready=0,no_beeper_audio=True,
        no_ula_fields_skipped=True,accumulated_song_drift_fields=0,eof_mutes_and_menu_remains_active=True,
        irq_count=len(irqs),foreground_min_tstates=min(foreground),foreground_max_tstates=max(foreground),
        max_command_to_song_start_tstates=max(switch_latencies),
        max_command_to_first_ay_write_tstates=max(first_write),
        max_command_to_complete_initial_state_tstates=max(complete_state),
        cache_loading_tstates=events[100][0][0]-events[101][0][0],trace_sha256=sha(trace),
        scope='Complete real128 Fuse playback with ULA/TR-DOS and live command dispatch; native tests cover hardware input decoding.')


def run_fuse(fuse, output, script, *, extra=(), sound=False, timeout=240):
    command = [str(fuse.resolve()),'--sound' if sound else '--no-sound','--no-autosave-settings',
        '--no-confirm-actions','--speed','100' if sound else '10000','--machine','128','--beta128',
        *extra,'--debugger-command',script,str((output/'ZX-Music-Menu.trd').resolve())]
    startup = None
    if sys.platform=='win32':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    epoch = time.time()
    result = subprocess.run(command,cwd=fuse.parent,capture_output=True,startupinfo=startup,
        env=dict(os.environ,SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy'),timeout=timeout)
    trace = result.stdout
    fallback = fuse.parent/'stdout.txt'
    if not trace and fallback.exists() and fallback.stat().st_mtime>=epoch-2:
        trace = fallback.read_bytes()
    return result,trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-click-fix')
    parser.add_argument('--fuse',type=Path)
    parser.add_argument('--song',choices=('lumiere','alicia'),default='lumiere')
    parser.add_argument('--captured',action='store_true',help='Recheck matching saved full traces without rerunning Fuse')
    args = parser.parse_args()
    meta = json.loads((args.output/'build.json').read_text())
    if args.fuse:
        result = fuse_check(args.fuse,args.output,meta,int(args.song=='alicia'),captured=args.captured)
        path = args.output/f'fuse-{args.song}.json'
    else:
        result = native_check(args.output,meta)
        path = args.output/'native.json'
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
