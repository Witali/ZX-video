"""Archive only the completely qualified source-matched dark-fill improvement."""
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
    p.add_argument('build', type=Path);p.add_argument('--probe', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True);p.add_argument('--tests', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True);p.add_argument('--ffprobe', type=Path, required=True)
    args = p.parse_args();build = args.build
    conversion = json.loads((build/'conversion.json').read_bytes())
    timing = json.loads((build/'timing.json').read_bytes());proof = timing['disks'][0]
    accuracy = json.loads((build/'accuracy-comparison.json').read_bytes())
    assert conversion['complete'] and conversion['timing_verified'] and conversion['lineart_dark_fills']
    assert conversion['frames'] == 977 and conversion['ay_ticks'] == 4885 and len(conversion['volumes']) == 1
    assert timing['complete'] and timing['all_nominal_deadlines_met']
    assert proof['full_fuse_screens_exact'] and proof['cold']['dirty_ram_boot_exact']
    measured = proof['disk_timing'];assert measured['complete'] and measured['nominal_deadlines_met']
    assert measured['missed_nominal_frames'] == measured['ay_missing_fields'] == 0 and measured['actual_ay_50hz']
    assert accuracy['complete'] and accuracy['full_native_qualified']
    for key in ('every_changed_pixel_strictly_closer_to_original', 'every_source_line_black',
                'every_existing_coloured_pixel_exact', 'every_black_or_colour_fill_source_matched',
                'no_dither', 'entire_original_rgb_and_ay_and_model_wav_exact'):assert accuracy[key]
    assert accuracy['used_sectors_after'] < accuracy['used_sectors_before']
    assert accuracy['compressed_stream_bytes_after'] < accuracy['compressed_stream_bytes_before']
    volume = conversion['volumes'][0];assert sha(build/volume['file']) == volume['sha256']
    old_conversion = json.loads((args.baseline/'conversion.json').read_bytes());old_volume = old_conversion['volumes'][0]
    old_meta = json.loads((args.baseline/old_volume['metadata']).read_bytes())
    new_meta = json.loads((build/volume['metadata']).read_bytes())
    for name in ('packet_listing', 'clock_listing'):
        assert old_meta['cell_codebook'][name] == new_meta['cell_codebook'][name]
    assert old_meta['cell_codebook']['native']['instruction_listing'] == new_meta['cell_codebook']['native']['instruction_listing']
    media = {}
    for name in ('native-preview.mp4', 'accuracy-comparison.mp4'):
        result = json.loads(subprocess.check_output([str(args.ffprobe), '-v', 'error', '-count_frames',
            '-show_entries', 'stream=codec_type,width,height,avg_frame_rate,nb_read_frames,duration', '-of', 'json', str(build/name)]))
        video = next(s for s in result['streams'] if s['codec_type'] == 'video')
        audio = next(s for s in result['streams'] if s['codec_type'] == 'audio')
        assert int(video['nb_read_frames']) == 977 and video['avg_frame_rate'] == '10/1'
        assert float(video['duration']) == float(audio['duration']) == 97.7
        media[name] = result
    if args.destination.exists():raise ValueError('archive already exists')
    destination = args.destination;shutil.copytree(build, destination)
    shutil.copyfile(build.with_suffix('.log'), destination/'conversion.log')
    shutil.copyfile(args.tests, destination/'tests.log')
    probe_dir = destination/'host-probe';probe_dir.mkdir()
    for name in ('states.npz', 'images.json', 'compression.json', 'comparison.png', 'dark.raw', 'dark.stream'):
        shutil.copyfile(args.probe/name, probe_dir/name)
    shutil.copyfile(args.probe.with_suffix('.log'), probe_dir/'probe.log')
    attempts = destination/'attempts';attempts.mkdir()
    for name in ('dark-fills-977.log', 'dark-fills-977-fixed-contract.log', 'dark-tests.log',
                 'dark-unguarded-lineart_colour.py', 'dark-unguarded-probe.py', 'dark_fixture.py'):
        shutil.copyfile(ROOT/'.tmp'/name, attempts/name)
    shutil.copyfile(HERE/'dark-fixtures/regression460.npz', attempts/'regression460.npz')
    source = json.loads((args.baseline/'source.json').read_bytes())
    source['selected_source_interval_seconds'] = [0, 97.7]
    (destination/'source.json').write_text(json.dumps(source, indent=2)+'\n', encoding='utf-8')
    plan = json.loads((destination/'selected-plan.json').read_bytes())
    plan.update(lineart_dark_fills=True,selection_reason='Same qualified977-frame prefix with accuracy-guarded source-matched dark fills; actual2399 sectors and full nominal timing pass.',
        inherited_plan_scope='Historical120-second window estimates describe the old image model, not this measured disk.',
        actual_used_sectors=volume['used_sectors'], actual_free_sectors=volume['free_sectors'])
    (destination/'selected-plan.json').write_text(json.dumps(plan, indent=2)+'\n', encoding='utf-8')
    producers = [ROOT/'toolkit'/name for name in ('lineart_colour.py','test_lineart_colour.py',
        'generic_cell_codebook.py','convert_video.py','convert_cb41.py','guarded_cb46.py',
        'cell_palette_quality.py','stable_colour.py','five_level_dither.py')]
    producers += [HERE/name for name in ('dark_probe.py','build_dark_disk.py','compare_dark_disk.py','archive_dark_disk.py')]
    producers += [ROOT/'toolkit/analysis/attribute_pattern/rebuild.py', ROOT/'toolkit/analysis/sea_foam/build_prefix.py', ROOT/'toolkit/analysis/sea_foam/preview.py']
    snapshots = {};hashes = {}
    for path in producers:
        name = path.relative_to(ROOT).as_posix();target = destination/'producer-sources'/name
        target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
        snapshots[name] = target.relative_to(destination).as_posix();hashes[name] = sha(target)
    old_selection = json.loads((args.baseline/'work'/Path(old_volume['file']).stem/'compression-selection.json').read_bytes())
    new_selection = json.loads((build/'work'/Path(volume['file']).stem/'compression-selection.json').read_bytes())
    qualification = dict(date='2026-10-14', complete=True, frames=977, duration_seconds=97.7, ay_ticks=4885,
        disks=1, volume=volume, baseline_commit='78b7a7be', baseline_disk_sha256=old_volume['sha256'],
        independent_dirty_boot_exact=True, full_fuse_screens_exact=True, compared_screen_bytes=977*6912,
        every_ay_record_exact=True, actual_ay_50hz=True, missed_nominal_frames=0, late_runs=[],
        maximum_deviation_tstates=measured['maximum_deviation_tstates'], accuracy=accuracy,
        native_instruction_delta_tstates=0, native_packet_clock_cell_listings_identical=True,
        deterministic_lzsa2_decoder_tstates_before=old_selection['decoder_tstates_after'],
        deterministic_lzsa2_decoder_tstates_after=new_selection['decoder_tstates_after'],
        deterministic_cost_scope=new_selection['cost_scope'], actual_disk_timing=measured,
        media=media, tests=57, producer_source_snapshots=snapshots, producer_sources_sha256_lf=hashes,
        implementation_source_snapshots_are_authoritative=True, implementation_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),
        physical_hardware_tested=False, source_contour_resolution_native_pixels=2,
        scope='Complete accuracy/compression improvement for the user-selected line-drawing style. No claim of global, photographic, semantic or maximum-duration optimality.')
    (destination/'qualification.json').write_text(json.dumps(qualification, indent=2)+'\n', encoding='utf-8')
    files = {path.relative_to(destination).as_posix():dict(bytes=path.stat().st_size,sha256=sha(path))
        for path in destination.rglob('*') if path.is_file() and '__pycache__' not in path.parts}
    (destination/'manifest.json').write_text(json.dumps(dict(files=files), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(complete=True, files=len(files),bytes=sum(f['bytes'] for f in files.values()),volume=volume,
        decoder_tstates_before=old_selection['decoder_tstates_after'],decoder_tstates_after=new_selection['decoder_tstates_after']),indent=2))


if __name__ == '__main__':main()
