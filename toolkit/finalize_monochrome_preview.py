"""Authenticate and publish one fully verified monochrome preview TRD."""
import argparse
import gzip
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

from prepare_cell_codebook_movie import file_sha, sha


def read(path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == '.gz' else data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('build', 'prepared', 'colour-baseline', 'tests', 'evidence', 'output', 'image'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--allow-fallback', action='store_true',
        help='retain a preview meeting the user-authorized one-field recovery allowance')
    args = parser.parse_args()
    conversion = read(args.build/'conversion.json')
    assert conversion['complete'] and conversion['monochrome']
    timing = read(args.build/'timing.json')
    assert timing['complete']
    fallback_met = all(d['disk_timing']['fallback_one_field_met'] for d in timing['disks'])
    assert conversion['timing_verified'] or (args.allow_fallback and fallback_met)
    assert len(conversion['volumes']) == 1
    preparation = read(args.prepared)
    assert file_sha(args.prepared) == conversion['preparation_sha256']
    start, end = conversion['prepared_range']
    source_audio = (args.prepared.parent/'audio.bin').read_bytes()
    assert sha(source_audio) == preparation['ay_sha256']
    audio = (args.build/'work/ay.bin').read_bytes()
    assert audio == source_audio[start*conversion['frame_fields']*9:end*conversion['frame_fields']*9]
    assert args.tests.read_text().strip().endswith('OK')
    with np.load(args.build/'work/five-states.npz', allow_pickle=False) as data:
        states = data['five_states']
        assert sha(states.tobytes()) == conversion['five_states_sha256']
        assert np.all(states[:,3936:4512] == 71)
        assert np.all(states[:,3840:3936] == 1) and np.all(states[:,4512:] == 1)
    record = conversion['volumes'][0]
    metadata = read(args.build/record['metadata'])
    old = read(args.colour_baseline)
    assert metadata['cell_codebook']['native'] == old['cell_codebook']['native']
    assert metadata['cell_codebook']['packet_listing'] == old['cell_codebook']['packet_listing']
    assert metadata['video_cadence'] == old['video_cadence']
    assert metadata['used_sectors'] <= 2544
    # Reuse the existing whole-clip timing, screen-trace and cold-boot archive gate.
    subprocess.run([sys.executable, str(Path(__file__).with_name('summarize_cb41_cadence.py')),
                    '--run', str(args.build), '--evidence', str(args.evidence),
                    '--output', str(args.output)], check=True)
    result = read(args.output)
    assert len(result['runs']) == 1
    assert result['all_nominal_deadlines_met'] or (args.allow_fallback and fallback_met)
    image = (args.build/record['file']).read_bytes()
    assert sha(image) == record['sha256']
    if args.image.exists() and args.image.read_bytes() != image:
        raise ValueError('refusing to replace a different existing root image')
    args.image.write_bytes(image)
    extra = [(args.build/'monochrome-preview.png', 'monochrome-preview.png'),
             (args.build/'work/ay.bin', 'original-ay.bin'), (args.tests, 'tests.txt')]
    sources = ('monochrome_five_level.py', 'test_monochrome_five_level.py',
               'build_cb41_cadence_movie.py', 'finalize_monochrome_preview.py')
    extra += [(Path(__file__).with_name(name), 'source-'+name) for name in sources]
    for path, name in extra:
        raw = path.read_bytes()
        if path.suffix == '.py': raw = raw.replace(b'\r\n', b'\n')
        packed = raw if path.suffix == '.png' else gzip.compress(raw, mtime=0)
        target = args.evidence/(name if path.suffix == '.png' else name+'.gz')
        target.write_bytes(packed)
        result['artifacts'].append(dict(file=target.name, raw_bytes=len(raw), raw_sha256=sha(raw),
            archive_bytes=len(packed), archive_sha256=sha(packed)))
    quality = read(args.build/'monochrome-quality.json')
    result.update(date='2026-10-01', root_image=args.image.name, root_image_sha256=sha(image),
        whole_movie=False, preview_only=True, prepared_range=[start,end],
        duration_seconds=conversion['duration_seconds'], original_ay_slice_exact=True,
        monochrome=True, active_attribute=71, physical_pixel_values=[0,255], brightness_levels=5,
        contrast_stretch=False, colour_discarded_by_user_request=True,
        mean_luma_mse=quality['mean_luma_mse'], preview_frames=quality['preview_frames'],
        colour_baseline=dict(metadata_sha256=file_sha(args.colour_baseline),
            video_bytes=old['video_bytes'], used_sectors=old['used_sectors']),
        monochrome_volume=dict(video_bytes=metadata['video_bytes'], used_sectors=metadata['used_sectors']),
        hot_path='Identical to the 10-fps colour window: native renderer, packet adapter and cadence; 0 T instruction delta.',
        fallback_one_field_met=fallback_met,
        exact_nominal_target_met=result['all_nominal_deadlines_met'],
        full_movie_capacity_or_timing_claimed=False)
    for artifact in result['artifacts']:
        assert file_sha(args.evidence/artifact['file']) == artifact['archive_sha256']
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('root_image','frames','ay_ticks','all_nominal_deadlines_met','monochrome_volume')}))


if __name__ == '__main__':
    main()
