"""Validate generic CB41 evidence and archive reproducible small media cases."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from five_level_dither import unpack_levels
import resumable_lzsa2

from convert_video import write_json


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work', 'checks', 'evidence', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--failed-run', type=Path, help='Retain the first one-frame host-guard failure')
    a = p.parse_args()
    root = Path(__file__).resolve().parent
    checks = json.loads(a.checks.read_bytes())
    assert checks['complete'] and checks['actual_fuse_requested']
    assert {c['name'] for c in checks['cases']} == {'single', 'portrait', 'colour', 'anamorphic', 'audio-tail'}
    for name, expected in checks['source_sha256_lf'].items():
        assert sha((root/name).read_bytes().replace(b'\r\n', b'\n')) == expected, ('source changed', name)
    baseline_path = root/'cell_codebook_balanced_profile.json'
    baseline = json.loads(baseline_path.read_bytes())
    assert baseline['complete'] and baseline['movie_playback_verified']
    assert baseline['frames'] == 4221 and baseline['full_screens_exact'] and baseline['ay_records_exact']
    assert baseline['nominal_late_frames'] == 0 and len(baseline['volumes']) == 3
    for artifact in baseline['artifacts']:
        packed = (root/'cell_codebook_balanced_evidence'/artifact['file']).read_bytes()
        assert sha(packed) == artifact['archive_sha256']
        restored = gzip.decompress(packed)
        assert sha(restored) == artifact['raw_sha256'] and len(restored) == artifact['raw_bytes']
    assert all(c['complete'] and c['nominal_late_frames'] == c['audio_underruns'] == 0
        and c['ay_records_exact'] and c['ay_gaps'] == c['ay_duplicates'] == 0 for c in baseline['continuation'])
    assert all(v['all_six_field_intervals'] and v['sector_bytes_exact'] and v['free_sectors'] >= 0
        and v['full_screen_bytes_compared'] == v['frames']*6912 for v in baseline['volumes'])
    old_meta = json.loads(gzip.decompress((root/'cell_codebook_balanced_evidence/volume-1-metadata.json.gz').read_bytes()))
    def decoder_identity(metadata):
        place = metadata['pre_fast_bank2_zx0']
        regions, _, layout = resumable_lzsa2.build(core=place['new_origin'], core_limit=place['new_end'])
        expected = [dict(address=at, code_hex=data.hex(), sha256=sha(data)) for at, data in regions]
        assert metadata['lzsa2']['regions'] == expected
        assert metadata['lzsa2']['layout'] == layout
        return [{k:v for k,v in row.items() if k != 'address'} for row in layout['instruction_listing']]
    old_decoder = decoder_identity(old_meta)
    for v in baseline['volumes']:
        assert sha((root.parent/v['root_file']).read_bytes()) == v['trd_sha256']
    movie = checks['movie']
    assert movie['frames'] == 4221 and all(v['full_host_screens_exact'] for v in movie['volumes'])
    assert sum(v['end']-v['start'] for v in movie['volumes']) == 4221
    disks, archives = [], []
    a.evidence.mkdir(parents=True, exist_ok=True)

    def archive(path, key):
        raw = path.read_bytes()
        if path.suffix.lower() == '.trd':
            destination = a.evidence/(key+'.trd')
            shutil.copyfile(path, destination)  # tracked using the existing *.trd LFS rule
        else:
            destination = a.evidence/(key+'.gz')
            destination.write_bytes(gzip.compress(raw, compresslevel=9, mtime=0))
        archives.append(dict(file=destination.name, bytes=len(raw), sha256=sha(raw),
            stored_bytes=destination.stat().st_size, stored_sha256=sha(destination.read_bytes())))

    for case in checks['cases']:
        name = case['name']
        folder = a.work/(name+'-out')
        assert sha((a.work/(name+'.mkv')).read_bytes()) == case['source_sha256']
        assert sha((folder/'conversion.json').read_bytes()) == case['conversion_sha256']
        manifest = json.loads((folder/'conversion.json').read_bytes())
        five = np.load(folder/'work/five-states.npy', allow_pickle=False)
        levels = sorted(set(int(v) for frame in five for v in np.unique(unpack_levels(frame[:3840].tobytes()))))
        if name == 'colour':
            assert levels == list(range(5)), 'moving colour fixture must exercise all five shades'
        case['brightness_levels_used'] = levels
        timing = json.loads((folder/'timing.json').read_bytes())
        assert manifest['complete'] and manifest['timing_verified']
        assert timing['complete'] and timing['all_nominal_deadlines_met']
        for record, timed in zip(manifest['volumes'], timing['disks'], strict=True):
            metadata = json.loads((folder/record['metadata']).read_bytes())
            image = folder/record['file']
            assert sha(image.read_bytes()) == record['sha256'] == metadata['trd_sha256']
            work = folder/Path(record['states']).parent
            actual = json.loads((work/'timing.json').read_bytes())
            screens = json.loads((work/'screens.json').read_bytes())
            assert actual['complete'] and actual['frames'] == record['frames']
            assert screens['complete'] and screens['frames'] == record['frames']
            assert screens['trd_sha256'] == actual['trd_sha256'] == record['sha256']
            assert screens['compared_bytes'] == record['frames']*6912 and screens['full_screens_exact']
            assert actual['nominal_late_frames'] == actual['audio_underruns'] == 0
            assert actual['ay_records_exact'] and actual['ay_ticks'] == record['frames']*6
            assert actual['ay_record_field_gaps'] == actual['ay_record_field_duplicates'] == 0
            assert actual['runtime_sectors_checked'] == metadata['video_sectors']
            assert actual['fast_read_retries'] == 0 and metadata['independently_bootable']
            for key in ('native', 'packet_listing'):
                assert metadata['cell_codebook'][key] == old_meta['cell_codebook'][key], key
            # Legacy scaffold tables can move the uncontended core. Reassemble
            # at each recorded address, then compare instruction identities and
            # absolute T-state tables; relocated operands are not opcode changes.
            assert decoder_identity(metadata) == old_decoder
            assert timed['cold']['dirty_ram_boot_exact'] and timed['cpu_all_native_screens_exact']
            disks.append(dict(case=name, part=metadata['part'], frames=record['frames'],
                trd_sha256=record['sha256'], used_sectors=metadata['used_sectors'],
                ay_ticks=actual['ay_ticks'], nominal_late_frames=actual['nominal_late_frames'],
                actual_phase_tstates=actual['actual_phase_tstates'], full_screen_bytes=screens['compared_bytes'],
                video_sectors=metadata['video_sectors'], native_and_packet_identical=True,
                lzsa2_same_instructions_and_tstates=True,
                lzsa2_core=metadata['pre_fast_bank2_zx0']['new_origin'],
                previous_lzsa2_core=old_meta['pre_fast_bank2_zx0']['new_origin']))
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(part in ('zx0', 'lzsa') for part in path.relative_to(folder).parts):
                continue
            # Keep small source/reference/output and raw verification evidence;
            # audio preview is reproducible from the saved AY and source file.
            if path.suffix == '.wav':
                continue
            key = name+'-'+str(path.relative_to(folder)).replace('\\', '-').replace('/', '-')
            archive(path, key[:-4] if path.suffix.lower()=='.trd' else key)
        archive(a.work/(name+'.mkv'), name+'-source.mkv')
        archive(a.work/(name+'.log'), name+'-run.log')
    swaps = json.loads((a.work/'colour-out/disk-swaps.json').read_bytes())
    assert len(swaps) == 2 and all(s['prompt_exact'] and s['wrong_disk_rejected']
        and s['wrong_series_rejected'] and s['correct_disk_accepted'] and s['bootstrap_ram_exact'] for s in swaps)
    archive(a.checks, 'checks.json')
    if a.failed_run:
        failure = a.failed_run/'single-out/conversion.json'
        failed = json.loads(failure.read_bytes())
        assert not failed['complete'] and 'frame service hook layout differs' in failed['failure']
        assert not list((a.failed_run/'single-out').glob('*.trd'))
        archive(failure, 'initial-single-failure.json')
        archive(a.failed_run/'single.log', 'initial-single-failure.log')
    result = dict(complete=True, release=False, date='2026-10-01', baseline_commit='9885483',
        scope='Generic opt-in CB41 conversion and exact reuse of the unchanged full-movie representation',
        generic_converter_integrated=True, cases=checks['cases'], disks=disks,
        frames=sum(d['frames'] for d in disks), ay_ticks=sum(d['ay_ticks'] for d in disks),
        compared_full_fuse_bytes=sum(d['full_screen_bytes'] for d in disks),
        nominal_late_frames=sum(d['nominal_late_frames'] for d in disks),
        native_instruction_delta_tstates=0, disk_swaps=swaps, movie=movie,
        movie_playback_evidence_sha256=sha(baseline_path.read_bytes()), root_movie_images_unchanged=True,
        movie_archive_hashes_verified=len(baseline['artifacts']),
        limits=['No universal cadence or three-disk guarantee for arbitrary input.',
                'Row/AY/native capacity failures are explicit and preserve quality.',
                '32-frame size estimates can require a smaller max-frames-per-disk on retry.',
                'Short synthetic cases do not prove sustained disk delivery; full movie evidence does.',
                'Physical disk swaps were not measured.'],
        source_sha256_lf={name:sha((root/name).read_bytes().replace(b'\r\n', b'\n'))
            for name in (*checks['source_sha256_lf'], 'resident_audio_player.py',
                         'resumable_lzsa2.py', 'test_generic_cell_codebook.py', 'summarize_generic_cb41.py')}, artifacts=archives)
    write_json(a.output, result)
    print(json.dumps({key:result[key] for key in ('frames', 'ay_ticks', 'compared_full_fuse_bytes',
                                                 'nominal_late_frames', 'native_instruction_delta_tstates')}))


if __name__ == '__main__':
    main()
