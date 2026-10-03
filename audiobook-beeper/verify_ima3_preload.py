"""Verify every loaded sector, expansion group and final resident IMA byte."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
from z80 import Z80Machine
from smoke_test_fuse import hidden_startupinfo
from verify_pcm import save


def native(path):
    meta = json.loads((path/'player.json').read_bytes()); info = meta['preload']; labels = info['labels']
    blob = (path/'assembly/ima3-preload.bin').read_bytes(); disk = (path/'audiobook-preview.trd').read_bytes()
    packed = gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
    m = Z80Machine(); m.memory[:] = b'\xa5'*65536; m.set_memory_block(0x8000, blob)
    banks = {i:bytearray(b'\xa5'*16384) for i in range(8)}; current = 0
    reads = []; load = []; unpack = []; groups = []; chunks = []; previous = None
    def page(bank):
        nonlocal current
        if current == 2:
            m.memory[0xB800:0xC000] = m.memory[0xF800:0x10000]
            banks[2][:] = m.memory[0x8000:0xC000]
        else: banks[current][:] = m.memory[0xC000:0x10000]
        current = bank
        if bank == 2: banks[2][:] = m.memory[0x8000:0xC000]
        m.set_memory_block(0xC000, banks[bank])
    def output(port, value):
        if port == 0x7FFD:
            assert 16 <= value <= 23; page(value & 7)
        else: assert port == 254 and value == 0
    watches = {labels[k]:k for k in ('group_loop', 'expand_end', 'block_expanded',
        'load_progress_event', 'unpack_progress_event', 'unpack_complete')}
    for address in (*watches, 0x3D13): m.set_breakpoint(address)
    budget = 20_000_000; m.ticks_to_stop = budget; m.pc = 0x8000; m.set_output_callback(output)
    while True:
        assert not m.run() & m._TICKS_LIMIT_HIT, ('timeout', hex(m.pc))
        if m.pc == 0x3D13:
            assert m.bc == 0x0105 and m.iy == 0x5C3A
            sector = m.d*16+m.e
            assert sector == info['source_sector']+len(reads)
            assert 0x6000 <= m.hl <= 0x7700
            m.set_memory_block(m.hl, disk[sector*256:(sector+1)*256]); reads.append(sector)
            m.pc = int.from_bytes(m.memory[m.sp:m.sp+2], 'little'); m.sp += 2
            m.bc = 0xFFFF; m.iy = 0  # ROM scratch registers must not carry state.
            continue
        name = watches.get(m.pc)
        if name == 'unpack_complete': break
        if name in ('group_loop', 'expand_end'):
            now = budget-m.ticks_to_stop
            if previous is not None: groups.append(now-previous)
            previous = now if name == 'group_loop' else None
        elif name == 'block_expanded':
            chunk = info['chunks'][len(chunks)]; end = chunk['output_end']; start = end-chunk['bytes']
            assert bytes(m.memory[chunk['address']:chunk['address']+chunk['bytes']]) == packed[start:end]
            chunks.append(end)
        elif name == 'load_progress_event':
            value = m.memory[labels['load_progress']]; load.append(value)
            assert bytes(m.memory[0x5940:0x5960]) == bytes([0x64])*value+bytes([0x49])*(32-value)
        elif name == 'unpack_progress_event':
            value = m.memory[labels['unpack_progress']]; unpack.append(value)
            assert bytes(m.memory[0x5A00:0x5A20]) == bytes([0x64])*value+bytes([0x49])*(32-value)
        if name: m.step_over_breakpoint()
    total = budget-m.ticks_to_stop; page(current)
    restored = b''.join(bytes(banks[s['bank']][s['address']-0xC000:]) for s in meta['sections'])
    assert restored == packed
    assert bytes(m.memory[0x8000:labels['disk_position']]) == blob[:labels['disk_position']-0x8000]
    assert bytes(m.memory[0x9000:0xAF00]) == blob[0x1000:]
    assert load == unpack == list(range(1,33))
    assert len(groups) == len(packed)//4 and set(groups) == {285}
    assert len(reads) == info['load_sectors'] and len(chunks) == len(info['chunks'])
    report = dict(complete=True, full_resident_ima_exact=True, ima_bytes_verified=len(restored),
        groups_verified=len(groups), group_tstates=285, core_tstates=sum(groups),
        native_preload_tstates=total, cpu_only_seconds=total/3546900, disk_sectors=len(reads),
        progress_load=load, progress_unpack=unpack, code_and_tables_unchanged=True,
        ima_sha256=hashlib.sha256(restored).hexdigest(),
        scope='Actual Z80 preload; ROM disk reads are copy stubs; no disk/ROM/ULA latency')
    save(path/'preload-native.json', report); print(json.dumps(report), flush=True)
    return report


def cold(path, fuse, raw128):
    """Full cold disk path, byte checks at every expanded block, real ROM timing."""
    meta = json.loads((path/'player.json').read_bytes()); info = meta['preload']; labels = info['labels']
    packed = gzip.decompress((path/'soundtrack.ima.gz').read_bytes())
    stamp = 'spectrum:frames*70908+ula:tstates'
    lines = ['base 10', 'set $stage 0', 'set $chunk 0']; widths = {}; eid = 0
    def event(where, tag, expressions, after=(), condition='', stop=False):
        nonlocal eid
        eid += 1; widths[tag] = len(expressions)
        lines.extend([f'breakpoint {where}', f'commands {eid}', f'print {tag}'])
        lines.extend('print '+e for e in expressions); lines.extend(after)
        lines.extend(['exit 77' if stop else 'continue', 'end'])
        if condition: lines.append(f'condition {eid} {condition}')
    event(labels['start'], 1, [stamp], condition='$stage==0')
    event(labels['disk_call'], 2, [stamp, 'z80:de', 'z80:hl', 'ula:mem7ffd'], condition='$stage==0')
    event(labels['disk_return'], 3, [stamp], condition='$stage==0')
    event(labels['block_loaded'], 4, [stamp], condition='$stage==0')
    event(labels['block_expanded'], 5, [stamp], ['set $chunk $chunk+1'], condition='$stage==0')
    event(labels['group_written'], 11, [f'[(z80:de-{j})&65535]' for j in (4,3,2,1)], condition='$stage==0')
    event(labels['load_progress_event'], 6, [f'[{labels["load_progress"]}]'], condition='$stage==0')
    event(labels['unpack_progress_event'], 7, [f'[{labels["unpack_progress"]}]'], condition='$stage==0')
    event(labels['handoff'], 8, [stamp], ['set $stage 1'], condition='$stage==0')
    event(0x8000, 9, [stamp], ['set $stage 2'], condition='$stage==1')
    event(meta['player_labels']['ready'], 10, [stamp], condition='$stage==2', stop=True)
    script = '\n'.join(lines); (path/'preload-debugger.txt').write_text(script, encoding='utf-8')
    result = subprocess.run([str(fuse.resolve()), '--no-sound', '--no-autosave-settings', '--no-confirm-actions',
        '--speed', '10000', '--machine', '128', '--beta128', '--debugger-command', script,
        str((path/'audiobook-preview.trd').resolve())], cwd=fuse.parent, capture_output=True,
        startupinfo=hidden_startupinfo(), timeout=180)
    (path/'preload-trace.txt.gz').write_bytes(gzip.compress(result.stdout, mtime=0))
    assert result.returncode == 77, (result.returncode, result.stderr[:2000])
    numbers = iter(int(s,0) for s in result.stdout.decode().splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)',s))
    events = {tag:[] for tag in widths}
    for tag in numbers: events[tag].append([next(numbers) for _ in range(widths[tag])])
    actual = bytes(value for group in events[11] for value in group)
    assert actual == packed, 'cold expanded bytes'
    offset = len(actual)
    assert [v[0] for v in events[6]] == [v[0] for v in events[7]] == list(range(1,33))
    assert len(events[2]) == len(events[3]) == info['load_sectors']
    assert len(events[4]) == len(events[5]) == len(info['chunks'])
    assert all(len(events[tag])==1 for tag in (1,8,9,10))
    assert [(r[1]>>8)*16+(r[1]&255) for r in events[2]] == list(range(info['source_sector'],info['source_sector']+info['load_sectors']))
    rom = sum(b[0]-a[0] for a,b in zip(events[2],events[3]))
    conversion = sum(b[0]-a[0] for a,b in zip(events[4],events[5]))
    total = events[10][0][0]-events[1][0][0]
    limit = json.loads(raw128.read_bytes())['maximum_decode_seconds']
    report = dict(complete=True, cold_boot=True, machine='128', every_expanded_byte_exact=True,
        bytes_verified=offset, compressed_sector_reads=len(events[2]), progress_load=list(range(1,33)),
        progress_unpack=list(range(1,33)), real_rom_read_tstates=rom, real_rom_read_seconds=rom/3546900,
        expansion_tstates=conversion, expansion_seconds=conversion/3546900,
        preloader_to_player_ready_seconds=total/3546900, maximum_decode_seconds=limit,
        decode_time_accepted=conversion/3546900<=limit,
        entire_preparation_within_decode_limit=total/3546900<=limit,
        scope='Cold Fuse; real disk/ROM, all expanded blocks, progress and handoff; BASIC boot precedes the measured interval',
        physical_hardware_tested=False)
    assert report['decode_time_accepted']
    save(path/'preload-fuse.json', report); print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('directory',type=Path)
    p.add_argument('--fuse',type=Path); p.add_argument('--raw128-report',type=Path)
    a=p.parse_args()
    if a.fuse: cold(a.directory.resolve(),a.fuse,a.raw128_report)
    else: native(a.directory.resolve())
