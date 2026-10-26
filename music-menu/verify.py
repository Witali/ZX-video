"""Replay actual assembled Z80 code and cold boot full songs in Fuse."""
import argparse
from collections import Counter
import gzip
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time

from build import BANKS, FIELD_T, HERE, ROOT, SAMPLE_T, sha


def unpack(data):
    if len(data) % 16 or not data.endswith(bytes(16)):
        raise ValueError('Missing record-aligned EOF')
    result = []
    for at in range(0, len(data)-16, 16):
        count = int.from_bytes(data[at:at+2], 'little')
        if not count:
            raise ValueError('Early EOF')
        result.extend([data[at+2:at+16]]*count)
    return result


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
        elif port & 255 != 254:
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


def native_check(output, metadata):
    blob = (output/'assembly/player.bin').read_bytes()
    labels = metadata['player_labels']
    results = []
    for index, variant in enumerate(metadata['variants']):
        data = (output/f'{variant["song"]}-{variant["mode"]}.rows').read_bytes()
        frames = unpack(data)
        assert len(frames) == variant['ticks']
        machine = Machine(blob, labels)
        m = machine.cpu
        for part, offset in enumerate(range(0, len(data), 16384)):
            chunk = data[offset:offset+16384]
            machine.banks[BANKS[part]][:len(chunk)] = chunk
        m.set_memory_block(0xC000, machine.banks[0])
        machine.byte('mode', index % 2)
        machine.byte('current_bank', 16)
        machine.word('record_pointer', 0xC000)
        machine.word('remaining', 0)
        histogram = Counter()
        row_updates = 0
        left = 0
        record = 0
        for tick, want in enumerate(frames):
            m.hl = (tick*1777) & 65535
            phase = m.hl
            count = len(machine.writes)
            histogram[machine.run_to(labels['field_work'], [labels['pwm_sample'], labels['ay_wait']])] += 1
            assert m.hl == phase and m.sp == 0xBD00, ('phase/stack', index, tick)
            if left == 0:
                left = int.from_bytes(data[record:record+2], 'little')
                record += 16
                row_updates += 1
                assert machine.writes[count:] == list(enumerate(want[3:])), ('AY', index, tick)
            else:
                assert len(machine.writes) == count
            left -= 1
            assert bytes(m.memory[labels['pwm_step']+1:labels['pwm_step']+3]) == want[:2]
            assert m.memory[labels['pwm_page']+1] == want[2]
        machine.run_to(labels['field_work'], [labels['menu']])
        assert m.sp == 0xBD00
        machine.call('mute')
        assert machine.writes[-14:] == [(i, 0) for i in range(14)]
        assert row_updates == variant['records']
        assert machine.pages == list(BANKS[1:len(variant['sections'])])
        results.append(dict(song=variant['song'], mode=variant['mode'], complete=True,
            frames=len(frames), records=row_updates, register_writes=row_updates*11,
            ay_and_dds_exact=True, phase_and_stack_preserved=True, eof_mutes=True,
            banks=[0]+machine.pages, deterministic_field_tstates=dict(sorted(histogram.items()))))

    # Every duty value exercises both complementary NOP ladders on real code.
    pwm = []
    for duty in range(16):
        machine = Machine(blob, labels)
        m = machine.cpu
        m.memory[0xAB00] = duty
        machine.byte('frame_due', 0)
        pulses = []
        budget = 5000
        base_output = machine.output
        def output(port, value):
            if port & 255 == 254:
                pulses.append((budget-m.ticks_to_stop, value))
            else:
                base_output(port, value)
        m.set_output_callback(output)
        m.pc = labels['pwm_sample']
        m.hl = 0
        m.memory[labels['pwm_step']+1:labels['pwm_step']+3] = bytes(2)
        m.ticks_to_stop = budget
        m.run()
        rising = [t for t, v in pulses if v == 16]
        # The core clamps ticks_to_stop during its final in-flight instruction.
        # Discard that tail observation, not any complete pulse/period.
        widths = [pulses[i+1][0]-pulses[i][0] for i in range(0, len(pulses)-3, 2)]
        assert set(b-a for a,b in zip(rising, rising[1:])) == {SAMPLE_T}, (duty, rising)
        assert set(widths) == {25+4*duty}, (duty, widths)
        pwm.append(dict(duty=duty, period_tstates=SAMPLE_T, high_tstates=25+4*duty))
    machine = Machine(blob, labels)
    machine.cpu.af = 0x1234
    machine.cpu.alt_af = 0x5678
    irq_t = machine.call('irq')
    assert irq_t == 46 and machine.cpu.af == 0x1234 and machine.cpu.alt_af == 0x0178
    assert machine.cpu.memory[labels['frame_due']] == 1
    return dict(variants=results, pwm_duties=pwm, controls=control_check(blob, labels),
                irq_handler_tstates=irq_t, im2_hardware_entry_tstates=19,
                scope='Complete independent Z80 execution; explicit physical banks; CPU counts without ULA/ROM/disk.')


def control_check(blob, labels):
    machine = Machine(blob, labels)
    m = machine.cpu
    keys = ((0xF7FE, 0xFE, 1), (0xF7FE, 0xFD, 2), (0x7FFE, 0xFB, 3),
            (0xEFFE, 0xF7, 4), (0xEFFE, 0xEF, 5), (0xBFFE, 0xFE, 6))
    for port, value, command in keys:
        machine.ports = {port: value}
        machine.call('keys')
        assert m.a == command
    machine.ports = {}
    machine.call('keys')
    assert m.a == 0
    for y, selected in ((75, 0), (108, 1)):
        machine.byte('mouse_raw_x', 250)
        machine.byte('mouse_raw_y', 2)
        machine.byte('mouse_x', 80)
        machine.byte('mouse_y', y-4)
        machine.byte('mouse_button', 2)
        machine.ports = {0xFBDF: 2, 0xFFDF: 254, 0xFADF: 253}
        machine.call('mouse')
        assert m.a == 1 and m.memory[labels['selected']] == selected
        assert m.memory[labels['mouse_x']] == 88 and m.memory[labels['mouse_y']] == y
        machine.call('mouse')
        assert m.a == 0, 'held button must not repeat'
    machine.ports = {}
    machine.byte('mouse_raw_x', 255)
    machine.byte('mouse_raw_y', 255)
    machine.call('mouse')
    assert m.a == 0
    before = bytes(m.memory[0x4000:0x5800])
    machine.call('cursor')
    assert bytes(m.memory[0x4000:0x5800]) != before
    machine.call('cursor')
    assert bytes(m.memory[0x4000:0x5800]) == before
    # Space runs the same stop path in both modes before any new AY row.
    for mode in (0, 1):
        machine.byte('mode', mode)
        machine.ports = {0x7FFE: 254}
        m.sp = 0xBD00
        machine.run_to(labels['field_work'], [labels['menu']])
        assert m.sp == 0xBD00
    # Drive the real menu loop as well as its individual input routines.
    live = Machine(blob, labels)
    live.run_to(labels['start'], [labels['menu_ready']], 500000)
    def menu_input(ports):
        live.ports = ports
        live.run_to(labels['menu_ready']+1, [labels['menu_ready'], labels['choose']], 50000)
    menu_input({0x7FFE: 0xFB})
    assert live.cpu.memory[labels['mode']] == 1
    menu_input({0x7FFE: 0xFB})
    assert live.cpu.memory[labels['mode']] == 1, 'held M repeated'
    menu_input({})
    menu_input({0xEFFE: 0xEF})
    assert live.cpu.memory[labels['selected']] == 1
    menu_input({})
    menu_input({0xBFFE: 0xFE})
    assert live.cpu.pc == labels['choose'] and live.cpu.memory[labels['selected']] == 1
    live = Machine(blob, labels)
    live.run_to(labels['start'], [labels['menu_ready']], 500000)
    menu_input({0xFBDF:255, 0xFFDF:223, 0xFADF:253})
    assert live.cpu.pc == labels['choose'] and live.cpu.memory[labels['selected']] == 1
    return dict(key_commands=6, no_key=True, kempston_wrap_and_both_clicks=True,
                held_click_debounced=True, absent_mouse=True, cursor_xor_restores=True,
                space_stop_both_modes=True, integrated_menu_mode_navigation_enter_click=True)


def fuse_check(fuse, output, metadata, index, *, pulse_fields=0):
    """Cold boot real TR-DOS, then use debugger selection at the menu boundary.

    Port input logic is checked by native controls. The only Fuse mutation is
    choosing song/mode and jumping to the normal choose entry, once after boot.
    No payload, loader or playback instructions are patched.
    """
    variant = metadata['variants'][index]
    labels = metadata['player_labels']
    work = output/'fuse'/f'{variant["song"]}-{variant["mode"]}'
    work.mkdir(parents=True, exist_ok=True)
    lines = ['base 10', 'set $started 0', 'set $ticks 0', 'set $live 0', 'set $done 0']
    widths = {}
    event_id = 0
    stamp = f'spectrum:frames*{FIELD_T}+ula:tstates'
    def event(where, tag=None, expressions=(), after=(), condition=None):
        nonlocal event_id
        event_id += 1
        lines.extend((f'br {where}', f'com {event_id}'))
        if tag is not None:
            widths[tag] = len(expressions)
            lines.append(f'pr {tag}')
            lines.extend('pr '+expr for expr in expressions)
        lines.extend(after)
        lines.extend(('co', 'end'))
        if condition:
            lines.append(f'cond {event_id} {condition}')
    event(labels['menu_ready'], 100, [stamp],
          [f'set {labels["selected"]} {index//2}', f'set {labels["mode"]} {index%2}',
           'set $started 1', f'set z80:pc {labels["choose"]}'], '$started==0')
    event(labels['disk_call'], 101, [stamp, 'z80:de', 'z80:hl', 'z80:b', '$live', 'ula:mem7ffd'])
    event(labels['ready'], 102, [stamp], ['set $live 1'])
    event(labels['tick_done'], 103, [stamp], ['set $ticks $ticks+1'])
    event(labels['record_event'], 104,
          [stamp, 'z80:hl', f'[{labels["remaining"]}]', f'[{labels["remaining"]+1}]',
           f'[{labels["pwm_step"]+1}]', f'[{labels["pwm_step"]+2}]', f'[{labels["pwm_page"]+1}]'])
    event(labels['ay_out']+2, 105, ['z80:d', 'z80:e'])
    event(labels['mute_out']+2, 108, ['z80:d', 'z80:e'], condition='$done==1')
    event(labels['irq'], 106, [stamp], condition='$live==1')
    if pulse_fields:
        event('port write 254', 107, [stamp, 'z80:a'],
              condition=f'$live==1 && $ticks>0 && $ticks<={pulse_fields}')
    event(labels['finished'], 199, [stamp, '$ticks'], ['set $live 0', 'set $done 1'])
    # Stop only after the normal menu path has muted both chips again.
    event(labels['menu_ready'], 200, [stamp], ['ex 77'], '$done==1')
    script = '\n'.join(lines)
    (work/'debugger.txt').write_text(script+'\n', encoding='ascii')
    command = [str(fuse.resolve()), '--no-sound', '--no-autosave-settings', '--no-confirm-actions',
        '--speed', '10000', '--machine', '128', '--beta128', '--debugger-command', script,
        str((output/'ZX-Music-Menu.trd').resolve())]
    startup = None
    if sys.platform == 'win32':
        startup = subprocess.STARTUPINFO()
        startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startup.wShowWindow = subprocess.SW_HIDE
    epoch = time.time()
    result = subprocess.run(command, cwd=fuse.parent, capture_output=True,
        env=dict(os.environ, SDL_VIDEODRIVER='dummy'), startupinfo=startup, timeout=240)
    trace = result.stdout
    if not trace:
        fallback = fuse.parent/'stdout.txt'
        if fallback.exists() and fallback.stat().st_mtime >= epoch-2:
            trace = fallback.read_bytes()
    (work/'trace.txt.gz').write_bytes(gzip.compress(trace, mtime=0))
    (work/'stderr.txt').write_bytes(result.stderr)
    assert result.returncode == 77, ('Fuse exit', result.returncode, result.stderr[:200])
    numbers = [int(x.group(1), 0) for x in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$', trace)]
    events = {tag: [] for tag in widths}
    pos = 0
    while pos < len(numbers):
        tag = numbers[pos]
        assert tag in widths, ('Unexpected trace tag', tag, pos)
        width = widths[tag]
        events[tag].append(numbers[pos+1:pos+1+width])
        pos += width+1
    data = (output/f'{variant["song"]}-{variant["mode"]}.rows').read_bytes()
    expected_ay, expected_dds, expected_ticks = [], [], []
    tick = 1
    for at in range(0, len(data)-16, 16):
        duration = int.from_bytes(data[at:at+2], 'little')
        expected_ay.extend([[reg, value] for reg, value in enumerate(data[at+5:at+16])])
        expected_dds.append(list(data[at+2:at+5]))
        expected_ticks.append(tick)
        tick += duration
    assert events[105] == expected_ay, ('Fuse AY mismatch', index, len(events[105]), len(expected_ay))
    assert [row[4:7] for row in events[104]] == expected_dds, ('Fuse DDS mismatch', index)
    assert len(events[103]) == variant['ticks']
    assert len(events[199]) == 1 and events[199][0][1] == variant['ticks']
    assert len(events[100]) == len(events[102]) == len(events[200]) == 1
    assert events[108] == [[i,0] for i in range(14)], 'EOF did not mute AY'
    assert all(row[4] == 0 for row in events[101]), 'Disk read during playback'
    reads = []
    for section in variant['sections']:
        for sector in range(section['sector'], section['sector']+section['sectors']):
            reads.append([(sector//16)*256+sector%16, 0xC000+(sector-section['sector'])*256, 1, 0, 16+section['bank']])
    assert [row[1:] for row in events[101]] == reads, ('Wrong disk extents', index)
    stamps = [row[0] for row in events[103]]
    irqs = [row[0] for row in events[106]]
    assert len(irqs) == variant['ticks']+1, ('Missed IRQ', index, len(irqs))
    assert all(b//FIELD_T == a//FIELD_T+1 for a,b in zip(irqs, irqs[1:])), 'Skipped ULA field'
    latency = [t-irq for t,irq in zip(stamps, irqs)]
    assert min(latency) >= 0 and max(latency) < FIELD_T
    event_fields = [(row[0]//FIELD_T)-(stamps[0]//FIELD_T)+1 for row in events[104]]
    assert event_fields == expected_ticks, 'RLE duration / absolute field drift'
    pulse_report = None
    if pulse_fields:
        pulses = events.get(107, [])
        # Some debugger versions report the same port observation twice.
        pulses = [r for i,r in enumerate(pulses) if not i or r != pulses[i-1]]
        rises = [t for t,value in pulses if value == 16]
        periods = Counter(b-a for a,b in zip(rises, rises[1:]))
        high = []
        for a,b in zip(pulses, pulses[1:]):
            if a[1] == 16 and b[1] == 0:
                high.append(b[0]-a[0])
        assert pulses and high and min(high) >= 25 and max(high) <= 180
        pulse_report = dict(fields=pulse_fields, pulses=len(rises), period_tstates=dict(sorted(periods.items())),
            high_min_tstates=min(high), high_max_tstates=max(high),
            max_rising_interval_tstates=max(periods), ordinary_cpu_tstates=SAMPLE_T,
            explanation='Includes real ULA I/O contention, IRQ low holds and RLE/AY field service.')
    return dict(song=variant['song'], mode=variant['mode'], complete=True, cold_boot=True,
        ticks=variant['ticks'], records=variant['records'], ay_and_dds_exact=True,
        menu_reached=True, menu_after_eof=True, eof_mutes_ay=True, disk_reads=len(reads), disk_reads_during_playback=0,
        irq_count=len(irqs), missed_ula_fields=0, accumulated_schedule_drift_fields=0,
        service_latency_min_tstates=min(latency), service_latency_max_tstates=max(latency),
        loading_tstates=events[102][0][0]-events[100][0][0],
        pwm=pulse_report, trace_sha256=sha(trace), wall_seconds=time.time()-epoch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'build/music-menu')
    parser.add_argument('--fuse', type=Path)
    parser.add_argument('--variant', type=int, choices=range(4))
    parser.add_argument('--pulse-fields', type=int, default=0)
    args = parser.parse_args()
    metadata = json.loads((args.output/'build.json').read_text())
    if args.fuse:
        result = fuse_check(args.fuse, args.output, metadata, args.variant or 0, pulse_fields=args.pulse_fields)
        path = args.output/f'fuse-{args.variant or 0}.json'
    else:
        result = native_check(args.output, metadata)
        path = args.output/'native.json'
    path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
