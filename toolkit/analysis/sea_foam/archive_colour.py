"""Preserve a completely qualified colour rebuild without replacing history."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--first', type=Path, required=True)
    parser.add_argument('--second', type=Path, required=True)
    parser.add_argument('--third', type=Path, required=True)
    parser.add_argument('--fourth', type=Path, required=True)
    args = parser.parse_args()
    build = args.build
    conversion = json.loads((build/'conversion.json').read_bytes())
    timing = json.loads((build/'timing.json').read_bytes())
    comparison = json.loads((build/'colour-comparison.json').read_bytes())
    assert conversion['complete'] and conversion['timing_verified']
    assert conversion['frames'] == 507 and conversion['ay_ticks'] == 2535
    assert len(conversion['volumes']) == 1
    assert timing['complete'] and timing['all_nominal_deadlines_met']
    proof = timing['disks'][0]
    assert proof['full_fuse_screens_exact'] and proof['cold']['dirty_ram_boot_exact']
    measured = proof['disk_timing']
    assert measured['complete'] and measured['actual_ay_50hz']
    assert measured['missed_nominal_frames'] == measured['ay_missing_fields'] == 0
    volume = conversion['volumes'][0]
    real = json.loads((build/'work'/Path(volume['file']).stem/'timing.json').read_bytes())
    assert real['complete'] and real['ay_records_exact'] and real['ay_ticks'] == 2535
    assert comparison['complete'] and comparison['exact_source_and_ay_unchanged']
    assert sha(build/volume['file']) == volume['sha256']
    destination = HERE/'evidence-colour'
    if destination.exists():
        prior = json.loads((destination/'qualification.json').read_bytes())
        assert prior['trd_sha256'] == volume['sha256'], 'different archive already exists'
    shutil.copytree(build, destination, dirs_exist_ok=True)
    shutil.copyfile(args.tests, destination/'tests.log')
    shutil.copyfile(build.with_suffix('.log'), destination/'conversion.log')
    shutil.copyfile(HERE/'evidence/source.json', destination/'source.json')
    drafts = destination/'superseded';drafts.mkdir(exist_ok=True)
    for label, candidate in [('averaged-only', args.first), ('quiet-cell-hold', args.second),
                             ('strict-physical-colour', args.third),
                             ('local-boundary-only', args.fourth)]:
        saved = drafts/label;saved.mkdir(exist_ok=True)
        for filename in ('video-quality.json', 'conversion.json', 'timing.json'):
            shutil.copyfile(candidate/filename, saved/filename)
        shutil.copyfile(candidate.with_suffix('.log'), saved/'run.log')
    shutil.copyfile(ROOT/'.tmp/stable-colour-v3-check.png', drafts/'physical-rgb-only-check.png')
    smoke = destination/'monochrome-smoke';smoke.mkdir(exist_ok=True)
    for profile in ('cb41', 'fap3'):
        source = ROOT/'.tmp'/('monochrome-smoke-'+profile)
        saved = smoke/profile;saved.mkdir(exist_ok=True)
        for filename in ('conversion.json', 'video-quality.json', 'timing.json'):
            shutil.copyfile(source/filename, saved/filename)
        shutil.copyfile(source.with_suffix('.log'), saved/'run.log')
    producers = [ROOT/'toolkit'/name for name in ('stable_colour.py', 'test_stable_colour.py',
        'generic_cell_codebook.py', 'convert_video.py', 'cell_palette_quality.py',
        'monochrome_five_level.py', 'five_level_dither.py')]
    producers += sorted(HERE.glob('*.py'))
    qualification = dict(complete=True, date='2026-10-13', frames=507, duration_seconds=50.7,
        ay_ticks=2535, disks=1, trd_sha256=volume['sha256'], used_sectors=volume['used_sectors'],
        all_nominal_deadlines_met=True, missed_nominal_frames=0,
        maximum_deviation_tstates=measured['maximum_deviation_tstates'],
        full_fuse_screens_exact=True, independent_dirty_boot_exact=True,
        every_ay_record_exact=True, actual_ay_50hz=True,
        exact_source_and_ay_unchanged=True, baseline_commit='fe3bb2cf',
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        native_instruction_delta_tstates=0, physical_hardware_tested=False,
        scope='Fully checked selected excerpt only. Monochrome CLI smoke checks are CPU/content proofs, not full Fuse qualification.',
        producer_sources_sha256_lf={p.relative_to(ROOT).as_posix():hashlib.sha256(
            p.read_bytes().replace(b'\r\n',b'\n')).hexdigest() for p in producers})
    (destination/'qualification.json').write_text(json.dumps(qualification,indent=2)+'\n',encoding='utf-8',newline='\n')
    files = {p.relative_to(destination).as_posix():dict(bytes=p.stat().st_size,sha256=sha(p))
             for p in destination.rglob('*') if p.is_file() and p!=destination/'manifest.json'}
    (destination/'manifest.json').write_text(json.dumps(dict(files=files),indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(complete=True, files=len(files), bytes=sum(f['bytes'] for f in files.values()),
        used_sectors=volume['used_sectors'], disk=volume['file'])))


if __name__ == '__main__':
    main()
