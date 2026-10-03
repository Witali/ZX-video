"""Separate cold TR-DOS reading from actual contended LPC conversion time."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from smoke_test_fuse import hidden_startupinfo
from verify_pcm import save


def measure(path, fuse, raw128_report=None):
    meta = json.loads((path / 'player.json').read_bytes())
    labels = meta['lpc_preload']['labels']
    stamp = 'spectrum:frames*70908+ula:tstates'
    script = ['base 10', 'set $started 0']
    for i, name in enumerate(('start', 'disk_call', 'load_complete', 'unpack_complete'), 1):
        script += [f'breakpoint {labels[name]}']
        if name == 'disk_call':
            script += [f'condition {i} $started==0']
        script += [f'commands {i}', 'print ' + stamp]
        if name == 'disk_call':
            script += ['set $started 1']
        script += ['exit 77' if name == 'unpack_complete' else 'continue', 'end']
    script = '\n'.join(script)
    (path / 'startup-debugger.txt').write_text(script, encoding='utf-8')
    result = subprocess.run([str(fuse.resolve()), '--no-sound', '--no-autosave-settings',
        '--no-confirm-actions', '--speed', '10000', '--machine', '128', '--beta128',
        '--debugger-command', script, str((path / 'audiobook-preview.trd').resolve())],
        cwd=fuse.parent, capture_output=True, startupinfo=hidden_startupinfo(), timeout=180)
    (path / 'startup-trace.txt').write_bytes(result.stdout)
    (path / 'startup-stderr.txt').write_bytes(result.stderr)
    assert result.returncode == 77, (result.returncode, result.stderr[:1000])
    times = [int(s, 0) for s in result.stdout.decode().splitlines()
             if re.fullmatch(r'(?:\d+|0x[\da-fA-F]+)', s)]
    assert len(times) == 4, times
    read = times[2] - times[1]
    conversion = times[3] - times[2]
    raw = json.loads(raw128_report.read_bytes()) if raw128_report else None
    report = dict(complete=True, absolute_tstates=times,
        lpc_sectors=meta['lpc_preload']['load_sectors'], lpc_read_tstates=read,
        conversion_tstates=conversion, lpc_read_seconds=read/3546900,
        conversion_seconds=conversion/3546900, conversion_to_lpc_read_ratio=conversion/read,
        raw128_seconds=raw['seconds'] if raw else None,
        maximum_decode_seconds=raw['maximum_decode_seconds'] if raw else None,
        startup_time_accepted=conversion/3546900 <= raw['maximum_decode_seconds'] if raw else None,
        scope='Cold Fuse Spectrum 128; real TR-DOS ROM, disk service and ULA contention',
        physical_hardware_tested=False)
    save(path / 'startup-timing.json', report)
    print(json.dumps(report), flush=True)
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('directory', type=Path)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--raw128-report', type=Path)
    args = p.parse_args()
    measure(args.directory, args.fuse, args.raw128_report)
