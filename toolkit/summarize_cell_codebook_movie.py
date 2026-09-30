"""Archive verified full-movie preparation and one measured volume partition."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'measurements', 'verification', 'capacity', 'preview', 'evidence', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    prepared = json.loads(a.prepared.read_bytes())
    measured = json.loads(a.measurements.read_bytes())
    verified = json.loads(a.verification.read_bytes())
    capacity = json.loads(a.capacity.read_bytes())
    identity = sha(a.prepared.read_bytes())
    assert measured['preparation_sha256'] == verified['preparation_sha256'] == identity
    assert capacity['preparation_sha256'] == identity
    assert capacity['measurements_sha256'] == sha(a.measurements.read_bytes())
    assert measured['frames'] == verified['frames'] == prepared['frames']
    assert all(r['complete'] and not r['release'] for r in (prepared, measured, verified))
    assert sha(a.preview.read_bytes()) == verified['preview_sha256']
    for source in (prepared['contract']['source_sha256_lf'], measured['source_sha256_lf'], capacity['source_sha256_lf']):
        for name, value in source.items():
            assert sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n', b'\n')) == value, name
    assert sha(Path(__file__).with_name('verify_cell_codebook_movie.py').read_bytes().replace(b'\r\n', b'\n')) == verified['source_sha256_lf']
    a.evidence.mkdir(parents=True, exist_ok=True)
    archives = []
    def archive(name, path):
        data = path.read_bytes()
        coded = gzip.compress(data, mtime=0)
        (a.evidence/name).write_bytes(coded)
        archives.append(dict(file=name, raw_bytes=len(data), archive_bytes=len(coded),
                             raw_sha256=sha(data), archive_sha256=sha(coded)))
    for name, path in (('prepared.json.gz', a.prepared), ('measurements.json.gz', a.measurements),
                       ('verification.json.gz', a.verification),
                       ('capacity.json.gz', a.capacity),
                       ('five-states.npz.gz', a.measurements.parent/'five-states.npz'),
                       ('audio.bin.gz', a.measurements.parent/'audio.bin')):
        archive(name, path)
    for volume in measured['volumes']:
        number = volume['volume']
        folder = a.measurements.parent/f'volume-{number}'
        names = ['audio.ayh1']
        if volume['row_table_fits']:
            names += ['codebook.raw', 'codebook.stream', 'row-dictionary.json', 'initial-screens.bin']
        for name in names:
            archive(f'volume-{number}-{name}.gz', folder/name)
        archive(f'volume-{number}-metadata.json.gz', a.capacity.parent/f'volume-{number}'/'metadata.json')
    exclusions = ('blocks', 'screen_sha256', 'frames')
    volumes = [{k:v for k,v in row.items() if k not in exclusions} for row in measured['volumes']]
    result = dict(complete=True, release=False, goal_achieved=False, date='2026-09-30',
        baseline_commit='2a9fa05', scope=__doc__, frames=prepared['frames'],
        last_source_frame=prepared['last_source_frame'], joins=prepared['joins'],
        duration_seconds=prepared['frames']*3/25, frame_rate=[25,3], ay_rate_hz=50,
        ay_ticks=prepared['ay_ticks'], ay_sha256=prepared['ay_sha256'],
        ay_registers_sha256=prepared['ay_registers_sha256'],
        source_video_sha256=prepared['contract']['source_sha256'],
        source_frame_map_sha256=prepared['source_frame_map_sha256'],
        unique_rows=prepared['unique_rows'], all_five_levels_used=prepared['all_five_levels_used'],
        row_windows=prepared['windows'], minimum_row_only_partition=measured['minimum_row_only_partition'],
        volumes=volumes, partitions_evaluated=measured['partitions_evaluated'],
        boundary_selection=measured['boundary_selection'],
        all_row_tables_fit=measured['all_row_tables_fit'], all_audio_banks_fit=measured['all_audio_banks_fit'],
        exact_host_screen_bytes=verified['screen_bytes_checked'],
        host_screen_sequence_sha256=verified['screen_sequence_sha256'],
        quality=dict(four_mse_mean=verified['four_mse_mean'], five_mse_mean=verified['five_mse_mean'],
                     refinement_never_increased_rgb_error=verified['refinement_never_increased_rgb_error'],
                     source_rgb_fixture_samples_exact=verified['source_rgb_fixture_samples_exact']),
        eof=dict(source_duration_seconds=prepared['decoded_source']['source_duration_seconds'],
                 tail_hold_seconds=prepared['decoded_source']['tail_hold_seconds'],
                 same_prefix_before_final_hold=verified['same_prefix_before_final_hold']),
        preview_sha256=verified['preview_sha256'], preview_frames=verified['preview_frames'],
        artifacts=archives, player_changed=False, player_instruction_delta_tstates=0,
        capacity=capacity['volumes'], all_volumes_fit=capacity['all_volumes_fit'],
        trd_images_built=any(v['fits'] for v in capacity['volumes']), actual_playback_measured=False,
        independent_cold_boots_verified=capacity['independently_cold_checked'],
        three_disk_release_proven=False)
    if all('compressed_bytes' in row for row in volumes):
        result['video_bytes'] = sum(row['compressed_bytes'] for row in volumes)
        result['video_sectors'] = sum(row['video_sectors'] for row in volumes)
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps({k:result[k] for k in ('frames','unique_rows','all_row_tables_fit','all_audio_banks_fit')}))


if __name__ == '__main__':
    main()
