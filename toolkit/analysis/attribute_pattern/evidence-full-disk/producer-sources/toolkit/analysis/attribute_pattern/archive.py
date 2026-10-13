"""Preserve only a completely qualified local-seam excerpt as release evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=HERE/'evidence')
    args = parser.parse_args();build = args.build
    conversion = json.loads((build/'conversion.json').read_bytes())
    timing = json.loads((build/'timing.json').read_bytes())
    comparison = json.loads((build/'pattern-comparison.json').read_bytes())
    assert conversion['complete'] and conversion['timing_verified']
    count = conversion['frames']
    assert conversion['ay_ticks'] == count*5
    audio_quality = json.loads((build/'audio-quality.json').read_bytes())
    assert audio_quality['reuse']['rgb_prefix_exact']
    assert audio_quality['reuse']['exported_ticks'] == count*5
    assert timing['complete'] and timing['all_nominal_deadlines_met']
    assert comparison['complete'] and comparison['full_native_qualified'] and comparison['exact_source_and_ay_unchanged']
    records = []
    for volume, proof in zip(conversion['volumes'], timing['disks'], strict=True):
        assert proof['full_fuse_screens_exact'] and proof['cold']['dirty_ram_boot_exact']
        measured = proof['disk_timing']
        assert measured['complete'] and measured['actual_ay_50hz']
        assert measured['missed_nominal_frames'] == measured['ay_missing_fields'] == 0
        real = json.loads((build/'work'/Path(volume['file']).stem/'timing.json').read_bytes())
        assert real['complete'] and real['ay_records_exact']
        assert real['ay_ticks'] == volume['frames']*5
        assert sha(build/volume['file']) == volume['sha256']
        records.append(dict(file=volume['file'], sha256=volume['sha256'],
            frames=volume['frames'], ay_ticks=real['ay_ticks'], used_sectors=volume['used_sectors'],
            free_sectors=volume['free_sectors'], maximum_deviation_tstates=measured['maximum_deviation_tstates']))
    assert sum(row['frames'] for row in records) == count
    assert sum(row['ay_ticks'] for row in records) == count*5
    destination = args.destination
    if destination.exists():
        prior = json.loads((destination/'qualification.json').read_bytes())
        assert prior['volumes'] == records, 'different archive already exists'
    shutil.copytree(build, destination, dirs_exist_ok=True)
    shutil.copyfile(args.tests, destination/'tests.log')
    shutil.copyfile(build.with_suffix('.log'), destination/'conversion.log')
    shutil.copyfile(args.baseline/'source.json', destination/'source.json')
    producers = [ROOT/'toolkit'/name for name in ('texture_colour.py', 'test_texture_colour.py',
        'stable_colour.py', 'generic_cell_codebook.py', 'test_generic_cell_codebook.py',
        'convert_video.py', 'convert_cb41.py', 'guarded_cb46.py',
        'cell_palette_quality.py', 'monochrome_five_level.py', 'five_level_dither.py')]
    producers += sorted(HERE.glob('*.py'))
    producers += [ROOT/'toolkit/analysis/sea_foam'/name for name in ('build_prefix.py', 'preview.py')]
    qualification = dict(complete=True, date='2026-10-13', frames=count, duration_seconds=count/10,
        ay_ticks=count*5, disks=len(records), volumes=records, all_nominal_deadlines_met=True,
        missed_nominal_frames=0, full_fuse_screens_exact=True, independent_dirty_boot_exact=True,
        every_ay_record_exact=True, actual_ay_50hz=True, exact_source_and_ay_unchanged=True,
        continuous_original_rgb_and_ay_prefix_exact=True,
        previous_qualified_comparison_frames=comparison['frames'],
        baseline_commit='db07319e', native_instruction_delta_tstates=0, physical_hardware_tested=False,
        implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        scope='Complete qualification of selected source prefix. Prior-disk image comparison covers its matching leading frames only; full source frame metrics cover every new frame. Rejected and superseded attempts remain separate.',
        producer_sources_sha256_lf={p.relative_to(ROOT).as_posix():hashlib.sha256(
            p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in producers})
    qualification['producer_source_snapshots'] = {}
    for path in producers:
        relative = path.relative_to(ROOT)
        target = destination/'producer-sources'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
        qualification['producer_source_snapshots'][relative.as_posix()] = target.relative_to(destination).as_posix()
    (destination/'qualification.json').write_text(json.dumps(qualification, indent=2)+'\n', encoding='utf-8', newline='\n')
    files = {p.relative_to(destination).as_posix():dict(bytes=p.stat().st_size, sha256=sha(p))
             for p in destination.rglob('*') if p.is_file() and p != destination/'manifest.json'}
    (destination/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, files=len(files), bytes=sum(f['bytes'] for f in files.values()), volumes=records)))


if __name__ == '__main__':main()
