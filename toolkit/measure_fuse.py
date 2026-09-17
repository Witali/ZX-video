"""Measure real Fuse 128K frame delivery and TR-DOS CALL duration separately."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from smoke_test_fuse import hidden_startupinfo
from validate_streaming_player import extract_file, parse_dir


def measure(fuse: Path, trd: Path, labels: dict, timeout: float, trdos_rom: Path | None = None) -> dict:
    image = trd.read_bytes()
    player = extract_file(image, next(e for e in parse_dir(image) if e[0] == 'PLAYER'))
    # Bracket ROM service: CALL 3D13h or direct-entry JP, through RAM return.
    call = labels.get('disk_full_call')
    if call is None: call = 0x6000 + player.index(b'\xcd\x13\x3d', labels['read_n']-0x6000)
    events = [(labels.get('bootstrap',labels['start']), 100), (labels['main_loop'], 101),
              (call, 102), (call+3, 103), (labels['finished'], 199)]
    events += [(labels[n], 198) for n in ('wait_packet_fill','stream_byte_fill','fatal') if n in labels]
    if 'audio_tick' in labels:
        events += [(labels['audio_write_loop'],140),(labels['audio_tick_done'],143),
                   (labels['audio_tick_empty'],198)]
    if 'frame_prepared' in labels: events.append((labels['frame_prepared'],107))
    if 'screen_flip_out' in labels: events.append((labels['screen_flip_out'],150))
    if 'elapsed_fields' in labels: events.append((labels['clock_check'],108))
    if 'fast_read_enter' in labels: events.append((labels['fast_read_enter'],109))
    if 'disk_finish' in labels and 'fast_disk_return' in labels:
        events.append((labels['fast_disk_return'],103))
    for entry,exit in (('seek_enter','seek_return'),('seek_side_enter','seek_side_return'),
                       ('keepalive_seek_enter','keepalive_seek_return')):
        if entry in labels:
            events.extend(((labels[entry],110),(labels[exit],103)))
    default_rom = fuse.parent/'roms/trdos.rom'
    if trdos_rom is None and default_rom.exists(): trdos_rom = default_rom
    rom_hash = hashlib.sha256(trdos_rom.read_bytes()).hexdigest() if trdos_rom else None
    if 'fast_read_enter' in labels and rom_hash != '91259fca6a8ded428cc24046f5b48b31d4043f2afbd9087d8946eaf4e10d71a5':
        raise ValueError('direct reader requires the tested TR-DOS 5.03 ROM; supply --trdos-rom')
    rom_args = ['--rom-beta128',str(trdos_rom.resolve())] if trdos_rom else []
    lines = ['base 10']
    for index, (address, event) in enumerate(events, 1):
        expression = (f'[{labels["elapsed_fields"]}] + 256 * [{labels["elapsed_fields"]+1}]' if event == 108 else
                      f'[{labels["field_counter"]}]' if event == 107 else 'spectrum:frames * 70908 + ula:tstates')
        lines += [f'breakpoint 0x{address:04x}', f'commands {index}',
                  f'print {event}', f'print {expression}']
        if event == 107:
            lines += ['print 117', 'print spectrum:frames * 70908 + ula:tstates']
        if event == 108:
            lines += ['print 130', f'print [{labels["ring_count"]}] + 256 * [{labels["ring_count"]+1}]',
                      'print 131', f'print [{labels["next_frame_field"]}] + 256 * [{labels["next_frame_field"]+1}]',
                      'print 132', 'print spectrum:frames * 70908 + ula:tstates']
        if event in (102,109):lines += ['print 120','print z80:hl']
        if event==198:lines += ['print 197','print z80:pc']
        if event==140:lines += ['print 141','print [z80:hl]','print 142','print [z80:hl + 1]']
        lines += [
                  ('exit 77' if event == 199 else 'exit 99' if event == 198 else 'continue'), 'end']
    env = dict(os.environ, SDL_VIDEODRIVER='dummy')
    completed = subprocess.run([str(fuse), '--no-sound', '--no-autosave-settings',
        '--no-confirm-actions', '--speed', '1000', '--machine', '128', '--beta128',
        '--debugger-command', '\n'.join(lines), *rom_args, str(trd)], cwd=fuse.parent,
        env=env, capture_output=True, startupinfo=hidden_startupinfo(), timeout=timeout)
    if completed.returncode != 77:
        trace=(fuse.parent/'stdout.txt').read_text(errors='replace')
        raise RuntimeError(f'Fuse exit {completed.returncode}; trace tail: {trace[-300:]}')
    output = completed.stdout.decode(errors='replace')
    pattern = r'(?:0x[0-9a-fA-F]+|-?\d+)'
    if not any(re.fullmatch(pattern, line.strip()) for line in output.splitlines()):
        output = (fuse.parent/'stdout.txt').read_text(errors='replace')
    numbers = [int(line.strip(), 0) for line in output.splitlines() if re.fullmatch(pattern, line.strip())]
    if len(numbers) % 2: raise ValueError(f'incomplete Fuse trace: {output[-300:]}')
    frames = []; reads = []; read_start = None; decode_fields=[]; player_start=None; clock_checks=[]
    read_kinds=[];read_frames=[];read_buffers=[]
    prepared_times=[];queue_checks=[];deadline_checks=[];clock_times=[]
    audio_writes=[];audio_ticks=[];screen_flips=[]
    for event, timestamp in zip(numbers[::2], numbers[1::2]):
        if event == 100: player_start=timestamp
        elif event == 101: frames.append(timestamp)
        elif event == 107: decode_fields.append(timestamp)
        elif event == 108: clock_checks.append(timestamp)
        elif event == 117: prepared_times.append(timestamp)
        elif event == 130: queue_checks.append(timestamp)
        elif event == 131: deadline_checks.append(timestamp)
        elif event == 132: clock_times.append(timestamp)
        elif event == 140: audio_writes.append(dict(tstate=timestamp+55))
        elif event == 141: audio_writes[-1]['register']=timestamp
        elif event == 142: audio_writes[-1]['value']=timestamp
        elif event == 143: audio_ticks.append(timestamp)
        elif event == 150: screen_flips.append(timestamp+12)  # OUT (C),A completion.
        elif event in (102,109,110):
            if read_start is not None: raise ValueError('unpaired ROM entry')
            read_start = timestamp
            read_kinds.append({102:'dispatcher',109:'direct',110:'seek'}[event])
            read_frames.append(len(frames)-1)
            read_buffers.append(None)
        elif event == 120:
            if read_start is None:raise ValueError('read buffer outside a ROM call')
            read_buffers[-1]=timestamp
        elif event == 103:
            if read_start is None: raise ValueError('unpaired ROM exit')
            reads.append(timestamp-read_start); read_start=None
    if len(frames) < 2 or not reads: raise ValueError(f'empty trace: {output[:300]}')
    if read_start is not None: raise ValueError('missing final ROM exit')
    if 'frame_prepared' in labels and len(decode_fields) != len(frames)-1:
        raise ValueError('incomplete CPU field trace')
    if len(prepared_times)!=len(decode_fields):raise ValueError('incomplete preparation timestamps')
    if 'screen_flip_out' in labels and len(screen_flips)!=len(frames)-1:
        raise ValueError('incomplete screen flip trace')
    if any(len(trace)!=len(clock_checks) for trace in (queue_checks,deadline_checks,clock_times)):
        raise ValueError('incomplete scheduler trace')
    intervals = [b-a for a,b in zip(frames,frames[1:])]
    return dict(machine='Fuse 1.9.0 Spectrum 128 + Beta128', clock_hz=3546900,
                trd_sha256=hashlib.sha256(image).hexdigest(),player_sha256=hashlib.sha256(player).hexdigest(),
                trdos_rom_sha256=rom_hash,
                player_startup_ms=(frames[0]-player_start)/3546.9 if player_start is not None else None,
                frames=len(frames), frame_interval_tstates=intervals,
                audio_ticks=audio_ticks,audio_writes=audio_writes,
                frame_interval_mean_ms=sum(intervals)/len(intervals)/3546.9,
                frame_interval_max_ms=max(intervals)/3546.9,
                measured_fps=3546900*len(intervals)/sum(intervals),
                decode_fields=decode_fields,
                clock_checks=clock_checks,
                frame_timestamps=frames,frame_prepared_timestamps=prepared_times,
                screen_flip_timestamps=screen_flips,
                queue_checks=queue_checks,deadline_checks=deadline_checks,clock_timestamps=clock_times,
                rom_call_kinds=read_kinds,rom_call_entry_frames=read_frames,rom_call_buffers=read_buffers,
                rom_call_tstates=reads, rom_call_mean_ms=sum(reads)/len(reads)/3546.9,
                rom_call_max_ms=max(reads)/3546.9,
                note='ROM service intervals include entry CALL/JP, interrupts inside the interval and emulator disk latency; not a physical-drive measurement.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('fuse',type=Path)
    parser.add_argument('build',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--timeout',type=float,default=60)
    parser.add_argument('--volumes',type=int,nargs='+',help='measure selected one-based volumes for experiments; omit for a release')
    parser.add_argument('--reuse-timing',type=Path,nargs='+',help='reuse completed traces only for byte-identical TRDs, PLAYER, ROM and Fuse executable')
    parser.add_argument('--trdos-rom',type=Path,help='default: roms/trdos.rom next to Fuse; direct reader verifies the ROM hash')
    args=parser.parse_args()
    meta=json.loads((args.build/'build_metadata.json').read_text())
    results=[]
    reusable={}
    rom=args.trdos_rom or args.fuse.parent/'roms/trdos.rom'
    rom_hash=hashlib.sha256(rom.read_bytes()).hexdigest() if rom.exists() else None
    player_hash=hashlib.sha256((args.build/'PLAYER.C.bin').read_bytes()).hexdigest()
    fuse_hash=hashlib.sha256(args.fuse.read_bytes()).hexdigest()
    for path in args.reuse_timing or []:
        for trace in json.loads(path.read_text()):
            if (trace.get('player_sha256')==player_hash and trace.get('trdos_rom_sha256')==rom_hash
                    and trace.get('fuse_sha256')==fuse_hash
                    and len(trace.get('screen_flip_timestamps',[]))==trace['frames']-1):
                reusable[trace['trd_sha256']]=trace
    volumes=meta['volumes']
    if args.volumes:
        if any(index<1 or index>len(volumes) for index in args.volumes):parser.error('volume outside build')
        volumes=[volumes[index-1] for index in args.volumes]
    for volume in volumes:
        path=(args.build/volume['trd_name']).resolve()
        result=reusable.get(hashlib.sha256(path.read_bytes()).hexdigest())
        if result is None:
            result=measure(args.fuse.resolve(),path,meta['player_labels'],args.timeout,args.trdos_rom)
            result['fuse_sha256']=fuse_hash
        assert result['frames']==volume['frames']
        results.append(result)
        args.output.with_suffix('.partial.json').write_text(json.dumps(results,indent=2))
        print(json.dumps({key:value for key,value in result.items() if not isinstance(value,list)}),flush=True)
    args.output.write_text(json.dumps(results,indent=2))


if __name__=='__main__': main()
