"""Record one unmodified demo playlist with Fuse's synchronized FMF recorder."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'music-menu'))
from verify import run_fuse


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(fuse, build, output, *, preview_fields=None):
    output.mkdir(parents=True, exist_ok=True)
    metadata = json.loads((build / 'build.json').read_text())
    disk = build / metadata['disk_name']
    assert digest(disk) == metadata['trd_sha256']
    labels = metadata['player_labels']
    lines = ['base 10', 'set $segment 0', 'set $ticks 0']
    event = 0

    def breakpoint(where, tag, expressions=(), commands=(), condition=None):
        nonlocal event
        event += 1
        lines.extend([f'br {where}', f'com {event}', f'pr {tag}'])
        lines.extend('pr ' + expression for expression in expressions)
        lines.extend(commands)
        lines.extend(['co', 'end'])
        if condition:
            lines.append(f'cond {event} {condition}')

    stamp = ['spectrum:frames', 'ula:tstates']
    breakpoint(labels['ready'], 100, stamp)
    breakpoint(labels['song_started'], 111, [*stamp, f'[{labels["playing"]}]'],
               ['set $segment $segment+1', 'set $ticks 0'])
    breakpoint(labels['picture_complete'], 112,
               [*stamp, f'[{labels["current_picture"]}]'])
    breakpoint(labels['show_menu'], 113, stamp)
    breakpoint(labels['music_tick'], 114, commands=['set $ticks $ticks+1'])
    # Stop before a third track writes any AY data. No keys or target memory
    # changes are injected: normal cold disk boot and native autoplay only.
    stop = ('$segment==1 && $ticks>=' + str(preview_fields)
            if preview_fields else '$segment==3')
    breakpoint(labels['menu_frame_done'], 200, stamp, ['ex 77'], stop)
    script = '\n'.join(lines) + '\n'
    (output / 'debugger.txt').write_text(script, encoding='ascii')
    movie = output / 'capture.fmf'
    print('Starting real-time Fuse stereo FMF capture.', flush=True)
    result, trace = run_fuse(fuse, build, script.rstrip('\n'), sound=True, timeout=720,
        extra=['--sound-freq', '44100', '--separation', 'ACB',
               '--movie-start', str(movie.resolve()), '--movie-compr', 'None'])
    assert result.returncode == 77, ('Fuse failed', result.returncode)
    # Keep numeric proof only; unrelated host banners and paths stay local.
    numbers = [int(m.group(1), 0) for m in
               re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$', trace)]
    widths = {100: 2, 111: 3, 112: 3, 113: 2, 114: 0, 200: 2}
    events = {tag: [] for tag in widths}
    position = 0
    while position < len(numbers):
        tag = numbers[position]
        width = widths[tag]
        events[tag].append(numbers[position + 1:position + 1 + width])
        position += width + 1
    assert len(events[100]) == len(events[200]) == 1
    assert not events[113], 'Menu must remain hidden without input'
    assert [row[2] for row in events[111]] == ([0] if preview_fields else [0, 1, 0])
    report = dict(trd_sha256=digest(disk), fuse_sha256=digest(fuse),
        movie_sha256=digest(movie), movie_bytes=movie.stat().st_size,
        script_sha256=hashlib.sha256(script.encode()).hexdigest(),
        source='Actual Fuse 1.9.0 Spectrum 128 + Beta Disk capture; cold boot, no injected input.',
        sound='44100 Hz PCM16 stereo, ACB AY separation',
        frame_tstates=metadata['frame_tstates'], cpu_hz=3546900,
        ready=events[100][0], track_starts=events[111],
        picture_completions=events[112], stop=events[200][0],
        music_ticks=len(events[114]), menu_shown=False,
        preview_only=bool(preview_fields))
    (output / 'capture.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in
        ('movie_bytes', 'ready', 'track_starts', 'stop', 'music_ticks')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fuse', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--preview-fields', type=int)
    args = parser.parse_args()
    capture(args.fuse, args.build, args.output, preview_fields=args.preview_fields)
