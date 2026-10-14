"""Full cold-Fuse sector-cadence UI proof and exact source-clock comparison.

Default-script verification does not run Fuse. Complete execution must use a
finished UI disk; partial runs never qualify as whole-song evidence.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[5]
sys.path[:0] = [str(ROOT/'audiobook-beeper'), str(ROOT/'toolkit')]

import numpy as np
from verify_stream_trd import fuse_check, native_check


BEST_SHA = 'ccab87249b9ce148f3b84cc317d64078a05f51c1e7d5ca7aa9f14958e8fc9074'
BASELINE = ROOT/'audiobook-beeper/experiments/song-snr/evidence/clock-joint/sea_foam'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def teardown_mute(folder):
    """Read the final untagged OUT interval, excluding tagged UI fields.

    Derive record widths from the actual saved debugger script. Retain only
    the last512KiB of decompressed trace, then align at a complete event tag;
    this avoids retaining another full11.5-million-pulse parse in memory.
    """
    widths = {}
    lines = (folder/'debugger.txt').read_text().splitlines()
    block = []
    for line in lines:
        if line.startswith('com '):
            block = []
        elif line == 'end':
            printed = [item[3:] for item in block if item.startswith('pr ')]
            if printed and re.fullmatch(r'-\d+', printed[0]):
                tag, count = int(printed[0]), len(printed)-1
                if tag in widths:
                    assert widths[tag] == count
                widths[tag] = count
        else:
            block.append(line)
    tail = b''
    with gzip.open(folder/'trace.txt.gz', 'rb') as stream:
        while True:
            chunk = stream.read(4*1024*1024)
            if not chunk:
                break
            tail = (tail+chunk)[-512*1024:]
    numbers = [int(match.group(1), 0) for match in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$', tail)]
    def signed(value):
        return value-2**32 if value>=0xffff0000 else value
    start = next(i for i,value in enumerate(numbers) if signed(value) in widths)
    at, last_out, terminal = start, None, None
    while at < len(numbers):
        value = signed(numbers[at])
        if value < 0:
            count = widths[value]
            fields = numbers[at+1:at+1+count]
            assert len(fields) == count
            if value == -199:
                terminal = fields
            at += count+1
        else:
            last_out = value
            at += 1
    assert last_out is not None and terminal is not None
    assert last_out & 1 == 0 and terminal[1] == 11526112
    return dict(last_source_to_mute_tstates=last_out>>1, value=0,
                terminal_source_plus_mute_outputs=terminal[1],
                record_widths=widths, parsing_scope='Final untagged OUT before terminal event; tagged UI/status payloads excluded')


def prove_default_script(out, fuse, baseline):
    """Intercept launch; require the exact established non-UI debugger script."""
    meta = json.loads((baseline/'player.json').read_text())
    packed = gzip.decompress((baseline/'soundtrack.ima.gz').read_bytes())
    expected = (baseline/'verification/pentagon512/debugger.txt').read_text()
    assert meta['trd_sha256'] == BEST_SHA and sha((baseline/'audio.trd').read_bytes()) == BEST_SHA
    assert not meta.get('audio_progress_ui')
    class LaunchIntercepted(Exception):
        pass
    actual = {}
    def intercept(command, **kwargs):
        index = command.index('--debugger-command')
        script = command[index+1]
        assert script == expected, 'default debugger script changed'
        actual.update(script_sha256=sha(script.encode()), bytes=len(script.encode()),
                      windows_command_characters=len(subprocess.list2cmdline(command)))
        raise LaunchIntercepted
    folder = out/'default-script'
    with patch('subprocess.run', side_effect=intercept):
        try:
            fuse_check(baseline/'audio.trd', meta, packed, 'pentagon512', folder, fuse)
        except LaunchIntercepted:
            pass
        else:
            raise AssertionError('default script intercept did not run')
    report = dict(complete=True, exact_prior_script=True, actual_Fuse_executed=False,
                  baseline_trd_sha256=BEST_SHA, **actual)
    save(out/'default-script-proof.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--packed', type=Path)
    parser.add_argument('--baseline', type=Path, default=BASELINE)
    parser.add_argument('--fuse', type=Path, default=Path('C:/Program Files (x86)/Fuse/fuse.exe'))
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--profiles', nargs='+', choices=('pentagon512','pentagon1024'),
                        default=('pentagon512','pentagon1024'))
    parser.add_argument('--captured', action='store_true')
    parser.add_argument('--check-default-only', action='store_true')
    parser.add_argument('--native-profile', choices=('128','scorpion','pentagon512','pentagon1024'),
                        help='Run one complete native profile instead of launching Fuse')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    baseline = args.baseline.resolve()
    default = None if args.native_profile else prove_default_script(out, args.fuse, baseline)
    if args.check_default_only:
        print(json.dumps(default))
        return
    if not all((args.disk, args.metadata, args.packed)):
        parser.error('--disk, --metadata and --packed are required for complete execution')
    disk, metadata, packed_path = args.disk.resolve(), args.metadata.resolve(), args.packed.resolve()
    meta = json.loads(metadata.read_text())
    packed = gzip.decompress(packed_path.read_bytes()) if packed_path.suffix.lower()=='.gz' else packed_path.read_bytes()
    prior = json.loads((baseline/'player.json').read_text())
    prior_packed = gzip.decompress((baseline/'soundtrack.ima.gz').read_bytes())
    assert packed == prior_packed and sha(packed) == meta['packed_sha256']
    assert meta.get('audio_progress_ui') and meta['audio_progress_ui']['live_bank_delta_tstates']==0
    assert sha(disk.read_bytes()) == meta['trd_sha256']
    old_model, new_model = dict(prior['model']), dict(meta['model'])
    new_model.pop('audio_progress_ui', None)
    assert old_model == new_model, 'UI disk changes the audio model'
    producers = (
        'audiobook-beeper/verify_stream_trd.py', 'audiobook-beeper/build_stream_trd.py',
        'audiobook-beeper/stream-player.asm', 'audiobook-beeper/stream-worker.asm',
        'audiobook-beeper/stream-playback-progress.asm', 'audiobook-beeper/stream-audio-ui.asm',
        'audiobook-beeper/stream-audio-ui-helper.asm',
        'audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator-sectors/verify.py',
    )
    before = {name: sha((ROOT/name).read_bytes()) for name in producers}
    if args.native_profile:
        actual=native_check(disk.read_bytes(),meta,packed,args.native_profile,
                            out=out/('native-'+args.native_profile+'.json'))
        assert before == {name: sha((ROOT/name).read_bytes()) for name in producers}, 'producer changed during native run'
        save(out/('native-'+args.native_profile+'-provenance.json'),dict(
            complete=True,profile=args.native_profile,trd_sha256=meta['trd_sha256'],
            packed_sha256=sha(packed),current_producer_sha256=before,
            source_ima_and_model_match_best_disk=True,
            scope='Complete instruction-level native proof; actual ULA/ROM/floppy timing belongs to separate Fuse captures'))
        print(json.dumps(dict(profile=args.native_profile,complete=True,
            bits=actual['bits_verified'],reloads=actual['reloads'],maximum_hold_tstates=actual['maximum_native_hold_tstates'])),flush=True)
        return
    fuse_sha256 = sha(args.fuse.read_bytes())
    results = []
    for profile in args.profiles:
        folder = out/profile
        if not args.captured and (folder/'trace.txt.gz').exists():
            raise ValueError('Refusing to overwrite a prior full capture; use another output or --captured')
        actual = fuse_check(disk, meta, packed, profile, folder, args.fuse,
                            captured=args.captured, capture_ui=True)
        old_times = np.frombuffer(gzip.decompress((baseline/'verification'/profile/'times.u32.gz').read_bytes()), '<u4')
        new_times = np.frombuffer(gzip.decompress((folder/'times.u32.gz').read_bytes()), '<u4')
        assert len(old_times) == len(new_times) == 11526111
        assert np.array_equal(old_times,new_times), 'introduced source-pulse timing change'
        comparison = dict(complete=True,reference_trd_sha256=BEST_SHA,
            fuse_executable=str(args.fuse.resolve()),fuse_executable_sha256=fuse_sha256,
            reference_profile=profile,source_out_timestamps_compared=len(new_times),
            every_relative_source_out_timestamp_exact=True,maximum_introduced_timing_change_tstates=0,
            relative_timestamps_sha256=sha(new_times.tobytes()),
            packed_ima_bytes_exact=True,every_source_bit_exact=actual['every_source_bit_and_state_exact'],
            source_guard_samples_included=True,startup_and_post_mute_rendering_excluded=True,
            physical_hardware_tested=False)
        old_mute = teardown_mute(baseline/'verification'/profile)
        new_mute = teardown_mute(folder)
        delta = new_mute['last_source_to_mute_tstates']-old_mute['last_source_to_mute_tstates']
        comparison['teardown_mute'] = dict(
            previous=old_mute,current=new_mute,delta_tstates=delta,
            delta_microseconds=delta/3584000*1e6,
            previous_relative_timestamp_tstates=int(old_times[-1])+old_mute['last_source_to_mute_tstates'],
            current_relative_timestamp_tstates=int(new_times[-1])+new_mute['last_source_to_mute_tstates'],
            every_source_bearing_pulse_remains_exact=True,
            raw_waveform_through_terminal_mute_identical=delta==0,
            scope='Explicit post-source teardown interval, measured separately; the established last100-ms listening crop excludes it')
        save(folder/'clock-comparison.json', comparison)
        actual['before_after_ui_clock'] = comparison
        save(folder/'report.json',actual)
        results.append(actual)
        print(json.dumps(dict(profile=profile,complete=True,bits=actual['bits_verified'],
            maximum_introduced_timing_change_tstates=0,loading_phases=len(actual['audio_progress_ui']['loading_dot_phases']),
            live_progress_updates=len(actual['audio_progress_ui']['live_progress']))),flush=True)
    assert before == {name: sha((ROOT/name).read_bytes()) for name in producers}, 'producer changed during capture'
    report = dict(complete=True,profiles=list(args.profiles),default_script_proof=default,
        fuse_executable=str(args.fuse.resolve()),fuse_executable_sha256=fuse_sha256,
        ui_trd_sha256=meta['trd_sha256'],reference_trd_sha256=BEST_SHA,packed_sha256=sha(packed),
        source_samples=meta['pcm_samples'],original_audio_model_preserved=True,
        original_relative_source_clock_preserved=True,current_producer_sha256=before,
        independent_cold_Fuse_runs=results,physical_hardware_tested=False,
        quality_scope='Exact IMA/model and every actual source-bearing bit/time match the previously measured20.250315887-dB disk; no new filter fit or source encoding.',
        screen_scope='Control bytes observed in full actual Fuse execution; cover pixels outside UI from the exact COVER file. PNGs are not a full-screen debugger dump.',
        reproducer='python audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator-sectors/verify.py --disk UI_AUDIO.trd --metadata UI_PLAYER.json --packed soundtrack.ima.gz --output NEW_FOLDER')
    save(out/'report.json', report)


if __name__ == '__main__':
    main()
