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
    args = parser.parse_args();build = args.build
    conversion = json.loads((build/'conversion.json').read_bytes())
    timing = json.loads((build/'timing.json').read_bytes())
    comparison = json.loads((build/'pattern-comparison.json').read_bytes())
    assert conversion['complete'] and conversion['timing_verified']
    assert conversion['frames'] == 507 and conversion['ay_ticks'] == 2535
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
    assert sum(row['frames'] for row in records) == 507
    assert sum(row['ay_ticks'] for row in records) == 2535
    destination = HERE/'evidence'
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
    qualification = dict(complete=True, date='2026-10-13', frames=507, duration_seconds=50.7,
        ay_ticks=2535, disks=len(records), volumes=records, all_nominal_deadlines_met=True,
        missed_nominal_frames=0, full_fuse_screens_exact=True, independent_dirty_boot_exact=True,
        every_ay_record_exact=True, actual_ay_50hz=True, exact_source_and_ay_unchanged=True,
        baseline_commit='db07319e', native_instruction_delta_tstates=0, physical_hardware_tested=False,
        implementation_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        scope='Complete qualification of selected excerpt only; rejected whole-image density draft is independently preserved and never qualified.',
        producer_sources_sha256_lf={p.relative_to(ROOT).as_posix():hashlib.sha256(
            p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in producers})
    (destination/'qualification.json').write_text(json.dumps(qualification, indent=2)+'\n', encoding='utf-8', newline='\n')
    files = {p.relative_to(destination).as_posix():dict(bytes=p.stat().st_size, sha256=sha(p))
             for p in destination.rglob('*') if p.is_file() and p != destination/'manifest.json'}
    (destination/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, files=len(files), bytes=sum(f['bytes'] for f in files.values()), volumes=records)))


if __name__ == '__main__':main()
