"""Build and cold/prime-check three resident-AY disks with 15.5-KiB in-place video slots.

Checks unchanged original video and AY payloads, every
ZX0 block, installed RAM and complete first native/second compact frames.
TR-DOS is mocked for these checks; full Fuse delivery remains a separate run.
"""
import argparse
import json
from pathlib import Path
import numpy as np

from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha, display_screen
from build_integrated_bootstrap import check_cold
from inplace_slot_player import Builder
from test_fap3_disk import DiskCPU, verify_swaps
from test_warm_continuation import player, until
import disk_progress_z80 as progress
import fap3_disk_z80 as disk

ROOT = Path(__file__).parent


def prime(image, m, states):
    c = DiskCPU(player(image), image)
    for bank in (0, 1, 2, 3, 4, 6, 7): c.banks[bank][:] = b'\xa7'*16384
    c.banks[5][:6912] = b'\xa7'*6912; c.banks[5][0x2400:] = b'\xa7'*(16384-0x2400)
    until(c, disk.DRIVER); before = c.tstates; until(c, m['clock_labels']['start'])
    start = m['frame_start']; audio = m['audio_labels']; q = m['queue_labels']
    expected = progress.reference_screen(display_screen(states[start].tobytes(), black_borders=True), 0, m['frames'])
    if bytes(c.banks[7][:6912]) != expected: raise AssertionError('first full native screen differs')
    if bytes(c.read8(0xa800+i) for i in range(3840)) != states[start+1].tobytes():
        raise AssertionError('second compact frame differs')
    occupancy = (c.read8(audio['audio_write_index'])-c.read8(audio['audio_read_index']))&31
    if occupancy != 31 or c.read8(audio['audio_enabled']) or c.read8(q['count'])>3:
        raise AssertionError('primed queues differ')
    compiled = m['resident_audio']['compiled']; labels = compiled['labels']
    for i, value in enumerate(bytes.fromhex(compiled['image_hex'])):
        if labels['state']-0xc000 <= i < labels['state_end']-0xc000: continue
        if c.banks[4][i] != value: raise AssertionError('resident audio bank overwritten')
    return dict(first_native_screen_exact=True, second_compact_frame_exact=True,
        audio_bank_immutable_exact=True, prepared_audio_records=occupancy,
        priming_cpu_tstates=c.tstates-before, mocked_boot_and_priming_sectors=c.dos_reads)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline-build', 'raw-directory', 'states', 'zx0', 'output', 'report'):
        p.add_argument('--'+key, type=Path, required=True)
    p.add_argument('--read-cache', type=Path, action='append', default=[])
    a = p.parse_args(); old = json.loads(a.baseline_build.read_bytes())
    if not old['complete'] or not old['contract']['options']['foreground_audio']:
        raise ValueError('complete foreground resident baseline required')
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    contract = dict(old['contract'], version='resident-inplace-slot-2')
    if sha(states.tobytes()) != contract['states_sha256']: raise ValueError('different source states')
    fingerprint = b'AYH1IPL1'+bytes.fromhex(sha(json.dumps(contract, sort_keys=True).encode()))[:6]
    a.output.mkdir(parents=True, exist_ok=True); a.report.parent.mkdir(parents=True, exist_ok=True)
    report = dict(complete=False, release=False, scope=__doc__, baseline_commit='da369e6',
        baseline_build_sha256=sha(a.baseline_build.read_bytes()), contract=contract,
        zx0_sha256=sha(a.zx0.read_bytes()), volumes=[])
    def save(): a.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    records = []; start = 0
    try:
        for part, end in enumerate(contract['ends'], 1):
            print(f'Building in-place volume {part}', flush=True)
            raw = (a.raw_directory/f'volume-{part}.raw').read_bytes()
            if sha(raw) != contract['raw_sha256'][part-1]: raise ValueError('raw input differs')
            b = Builder(raw, states, a.zx0.resolve(), a.output/'zx0',
                        series_fingerprint=fingerprint, **contract['options'])
            b.ends = contract['ends']; b.read_cache = a.read_cache
            image, m = b.volume(start, end, part)
            if image is None: raise ValueError(('disk capacity exceeded', part, m['used_sectors']))
            stem = f'ZX-video-huffman-preview_part{part:02}'
            (a.output/(stem+'.trd')).write_bytes(image)
            (a.output/(stem+'.json')).write_text(json.dumps(m, indent=2)+'\n', encoding='utf-8', newline='\n')
            _, stream, blocks = disk_blocks(a.output, part)
            video, sound = b.separated(start, end)
            if b''.join(chunk for _, chunk in blocks) != video: raise AssertionError('TRD video differs')
            row = dict(part=part, frames=end-start, used_sectors=m['used_sectors'], free_sectors=m['free_sectors'],
                video_bytes=m['video_bytes'], video_sectors=m['video_sectors'], video_start_sector=m['video_start_sector'],
                trd_sha256=sha(image), metadata_sha256=sha((a.output/(stem+'.json')).read_bytes()),
                stream_sha256=sha(stream), raw_video_sha256=sha(video), audio_sha256=sha(sound),
                inplace_video=m['inplace_video'], independently_bootable=m['independently_bootable'],
                exact_video_field_roundtrip=True)
            row.update(check_cold(image, m, b.expected_banks)); row.update(prime(image, m, states))
            report['volumes'].append(row); save()
            records.append(dict(part=part, file=stem+'.trd', metadata=stem+'.json', sha256=sha(image),
                                frame_start=start, frame_end_exclusive=end))
            print(json.dumps({k: v for k, v in row.items() if k not in ('inplace_video', 'cold_sections')}), flush=True)
            start = end
        (a.output/'volumes.json').write_text(json.dumps(records, indent=2)+'\n', encoding='utf-8', newline='\n')
        verify_swaps(a.output, a.output/'swaps.json')
        report.update(complete=True, mocked_rom_swaps=json.loads((a.output/'swaps.json').read_bytes()))
    except Exception as exc:
        report['failure'] = repr(exc); raise
    finally:
        names = ('build_inplace_slot_player.py', 'inplace_slot_player.py', 'inplace_slot_input_z80.py',
                 'inplace_zx0.py', 'benchmark_inplace_slot.py', 'test_inplace_slot.py',
                 *old['source_sha256_lf'].keys())
        report['source_sha256_lf'] = {n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in names}
        save()


if __name__ == '__main__': main()
