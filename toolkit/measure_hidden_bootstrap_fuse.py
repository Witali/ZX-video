"""Check loading-screen attributes and actual TR-DOS paging in Fuse.

Stops at the playback driver. This is a complete startup check, not a full
movie run or timing qualification. No debugger memory writes are performed.
"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import time

from build_fap3_trd import sha
from smoke_test_fuse import hidden_startupinfo


def measure(fuse, image, metadata, output, timeout):
    if sha(image.read_bytes()) != metadata['trd_sha256']:
        raise ValueError('TRD metadata differs')
    nonce = secrets.randbits(30)
    labels = metadata['bootstrap_labels']
    lines = ['base 10', 'set $running 0']
    widths = {}
    stamp = 'spectrum:frames*70908+ula:tstates'

    def event(pc, tag, expressions, *, start=False, stop=False):
        index = len(widths)+1
        widths[tag] = len(expressions)
        lines.extend([f'breakpoint {pc}', f'commands {index}', f'print {tag}'])
        if start:
            lines.append('set $running 1')
        lines.extend('print '+expr for expr in expressions)
        lines.extend(['exit 77' if stop else 'continue', 'end',
                      f'condition {index} $running == {0 if start else 1}'])

    event(labels['bootstrap_entry'], 900, [stamp, str(nonce)], start=True)
    event(labels['staging_attributes_hidden'], 901,
          [stamp, 'ula:mem7ffd']+[f'[{0xd800+i}]' for i in range(768)])
    event(labels['boot_disk_call'], 902, [stamp, 'ula:mem7ffd', 'z80:hl'])
    event(labels['boot_disk_call']+3, 903, [stamp, 'ula:mem7ffd'])
    event(labels['restore_boot_display'], 904, [stamp, 'ula:mem7ffd'])
    event(metadata['player_labels']['start'], 905, [stamp, 'ula:mem7ffd'], stop=True)
    script = '\n'.join(lines)
    output.with_suffix('.debugger.txt').write_text(script, encoding='utf-8', newline='\n')
    command = [str(fuse.resolve()), '--no-sound', '--no-autosave-settings', '--no-confirm-actions',
        '--speed', '10000', '--machine', '128', '--beta128', '--debugger-command', script, str(image.resolve())]
    if len(subprocess.list2cmdline(command)) >= 32760:
        raise ValueError('debugger command exceeds Windows limit')
    epoch = time.time()
    completed = subprocess.run(command, cwd=fuse.parent, env=dict(os.environ, SDL_VIDEODRIVER='dummy'),
        capture_output=True, startupinfo=hidden_startupinfo(), timeout=timeout)
    trace = completed.stdout.decode(errors='replace')
    fallback = fuse.parent/'stdout.txt'
    if not re.search(r'^\s*\d+\s*$', trace, re.M) and fallback.exists() and fallback.stat().st_mtime >= epoch-2:
        trace = fallback.read_text(errors='replace')
    output.with_suffix('.trace.txt').write_text(trace, encoding='utf-8', newline='\n')
    output.with_suffix('.stderr.txt').write_bytes(completed.stderr)
    numbers = [int(s.strip(), 0) for s in trace.splitlines() if re.fullmatch(r'(?:-?\d+|0x[\da-fA-F]+)', s.strip())]
    events = []
    while numbers:
        tag = numbers.pop(0)
        if tag not in widths or len(numbers) < widths[tag]:
            raise ValueError('invalid startup trace')
        values, numbers = numbers[:widths[tag]], numbers[widths[tag]:]
        events.append(dict(tag=tag, values=values))
    if (completed.returncode != 77 or not events or events[0]['tag'] != 900
            or events[0]['values'][1] != nonce or events[-1]['tag'] != 905):
        raise ValueError('startup did not complete with this trace nonce')
    mask = [e for e in events if e['tag'] == 901]
    reads = [e['values'] for e in events if e['tag'] == 902]
    returns = [e['values'] for e in events if e['tag'] == 903]
    restores = [e for e in events if e['tag'] == 904]
    if len(mask) != 1 or any(mask[0]['values'][2:]) or mask[0]['values'][1] != 0x17:
        raise ValueError('all 768 shadow attributes must be black before selection')
    if len(restores) != 1 or len(reads) != len(returns) or len(reads) != sum(s['sectors'] for s in metadata['sections']):
        raise ValueError('startup read coverage differs')
    if any(not before[1] & 8 or before[1] != after[1] for before, after in zip(reads, returns)):
        raise ValueError('TR-DOS changed or exposed the loading display')
    if events[-1]['values'][1] != 0x17:
        raise ValueError('normal display was not restored before runtime')
    report = dict(complete=True, release=False, full_playback_verified=False, debugger_memory_writes=0,
        part=metadata['part'], trd_sha256=metadata['trd_sha256'], trace_nonce_exact=True,
        attributes_checked=768, attributes_all_black=True, reads_checked=len(reads),
        real_rom_preserves_display=True, normal_display_restored=True,
        bootstrap_elapsed_tstates=events[-1]['values'][0]-events[0]['values'][0],
        rom_sha256=sha((fuse.parent/'roms/trdos.rom').read_bytes()),
        source_sha256_lf=sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
        trace_sha256=sha(output.with_suffix('.trace.txt').read_bytes()),
        debugger_script_sha256=sha(output.with_suffix('.debugger.txt').read_bytes()), events=events)
    output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--timeout', type=float, default=60)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output directory must be new')
    args.output.mkdir(parents=True)
    for path in sorted(args.directory.glob('ZX-video-huffman-preview_part*.json')):
        metadata = json.loads(path.read_bytes())
        report = measure(args.fuse, path.with_suffix('.trd'), metadata,
            args.output/f'part{metadata["part"]:02}.json', args.timeout)
        print(json.dumps({k: v for k, v in report.items() if k != 'events'}), flush=True)


if __name__ == '__main__':
    main()
