"""Publish only a fully qualified line-art disk; retain failed/aborted attempts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

HERE = Path(__file__).resolve().parent;ROOT = HERE.parents[2]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('build', type=Path);p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--tests', type=Path, required=True)
    p.add_argument('--destination', type=Path, default=HERE/'disk-evidence')
    args = p.parse_args();build = args.build
    conversion = json.loads((build/'conversion.json').read_bytes())
    timing = json.loads((build/'timing.json').read_bytes())
    compared = json.loads((build/'lineart-comparison.json').read_bytes())
    assert conversion['complete'] and conversion['timing_verified']
    assert conversion['colour_policy'] == 'lineart' and len(conversion['volumes']) == 1
    count = conversion['frames'];assert conversion['ay_ticks'] == count*5
    assert timing['complete'] and timing['all_nominal_deadlines_met']
    assert compared['complete'] and compared['frames'] == count
    assert all(compared[key] for key in ('every_source_line_black', 'every_matched_black_fill_exact',
        'every_paper_sample_exact', 'every_output_colour_source_matched', 'no_dither', 'exact_common_rgb_and_ay_and_model_wav'))
    volume = conversion['volumes'][0];proof = timing['disks'][0]
    assert proof['full_fuse_screens_exact'] and proof['cold']['dirty_ram_boot_exact']
    measured = proof['disk_timing']
    assert measured['complete'] and measured['actual_ay_50hz']
    assert measured['missed_nominal_frames'] == measured['ay_missing_fields'] == 0
    real = json.loads((build/'work'/Path(volume['file']).stem/'timing.json').read_bytes())
    assert real['complete'] and real['ay_records_exact'] and real['ay_ticks'] == count*5
    assert sha(build/volume['file']) == volume['sha256'] and volume['used_sectors'] <= 2544
    destination = args.destination
    if destination.exists():raise ValueError('archive destination already exists')
    shutil.copytree(build, destination)
    shutil.copyfile(args.tests, destination/'tests.log')
    shutil.copyfile(build.with_suffix('.log'), destination/'conversion.log')
    source = json.loads((args.baseline/'source.json').read_bytes())
    source['selected_source_interval_seconds'] = [0, count/10]
    (destination/'source.json').write_text(json.dumps(source, indent=2)+'\n', encoding='utf-8', newline='\n')
    plan = json.loads((destination/'selected-plan.json').read_bytes())
    plan.update(colour_policy='lineart', selection_reason='Explicit source prefix after actual line-art disk capacity probes; all nominal deadlines completely verified.',
        inherited_plan_scope='Earlier 120-second window estimates describe the old image model, not the selected line-art size.',
        actual_used_sectors=volume['used_sectors'], actual_free_sectors=volume['free_sectors'])
    (destination/'selected-plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8', newline='\n')
    names = ('lineart_colour.py', 'test_lineart_colour.py', 'flat_colour.py',
        'generic_cell_codebook.py', 'convert_video.py', 'convert_cb41.py', 'guarded_cb46.py',
        'cell_palette_quality.py', 'stable_colour.py', 'five_level_dither.py')
    producers = [ROOT/'toolkit'/name for name in names]
    producers += [HERE/name for name in ('build_disk.py', 'lineart_probe.py', 'compare_disk.py', 'archive_disk.py')]
    producers += [ROOT/'toolkit/analysis/attribute_pattern/rebuild.py',
        ROOT/'toolkit/analysis/sea_foam/build_prefix.py', ROOT/'toolkit/analysis/sea_foam/preview.py']
    snapshots = {};hashes = {}
    for path in producers:
        name = path.relative_to(ROOT).as_posix();target = destination/'producer-sources'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
        snapshots[name] = target.relative_to(destination).as_posix();hashes[name] = sha(target)
    qualification = dict(complete=True, date='2026-10-14', frames=count, duration_seconds=count/10,
        ay_ticks=count*5, disks=1, volumes=[dict(volume, maximum_deviation_tstates=measured['maximum_deviation_tstates'])],
        all_nominal_deadlines_met=True, missed_nominal_frames=0, full_fuse_screens_exact=True,
        independent_dirty_boot_exact=True, every_ay_record_exact=True, actual_ay_50hz=True,
        continuous_original_rgb_and_ay_prefix_exact=True, previous_qualified_comparison_frames=compared['common_frames'],
        every_source_line_and_fill_rule_checked=True, no_dither=True,
        baseline_commit='96fcec79', baseline_disk_sha256='df986063d6cc6e5ff9048cea074e642759fc6140ca911ecd86064b7fe1c399cb',
        native_instruction_delta_tstates=0, physical_hardware_tested=False,
        implementation_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip(),
        implementation_source_snapshots_are_authoritative=True,
        producer_sources_sha256_lf=hashes, producer_source_snapshots=snapshots,
        scope='Complete independent native/Fuse qualification of user-requested stylized source-line drawing with matched colour fills. No photographic/semantic quality or mathematical maximum-duration claim.')
    (destination/'qualification.json').write_text(json.dumps(qualification, indent=2)+'\n', encoding='utf-8', newline='\n')
    files = {path.relative_to(destination).as_posix():dict(bytes=path.stat().st_size, sha256=sha(path))
        for path in destination.rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    (destination/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(complete=True, files=len(files), bytes=sum(row['bytes'] for row in files.values()), volume=volume)))


if __name__ == '__main__':main()
