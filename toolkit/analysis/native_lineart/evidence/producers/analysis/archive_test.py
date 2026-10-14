"""Archive a fully checked experimental native prefix, preserving failed attempts."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[3]


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffprobe',required=True);args=p.parse_args()
    build=args.build.resolve();output=args.output.resolve()
    if output.exists():raise ValueError('archive must be new')
    m=json.loads((build/'conversion.json').read_bytes());v=m['volumes'][0]
    assert m['complete'] and len(m['volumes'])==1 and v['frames']==300
    t=json.loads((build/'timing.json').read_bytes());full=json.loads((build/'work'/Path(v['file']).stem/'screens.json').read_bytes())
    assert t['complete'] and full['full_screens_exact'] and full['compared_bytes']==300*6912
    assert t['disks'][0]['cold']['dirty_ram_boot_exact'] and t['disks'][0]['disk_timing']['actual_ay_50hz']
    output.mkdir(parents=True)
    def copy(src,relative):
        dst=output/relative;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    def tree(src,relative):
        for path in sorted(src.rglob('*')):
            if path.is_file():copy(path,Path(relative)/path.relative_to(src))
    for path in sorted(build.iterdir()):
        if path.is_file():copy(path,path.name)
    for name in ('frames.rgb','native-states.npy','states.npy','conversion.npz','stream.raw','ay.bin','audio-preview.wav'):
        copy(build/'work'/name,Path('work')/name)
    tree(build/'work'/Path(v['file']).stem,Path('work')/Path(v['file']).stem)
    copy(build.parent/(build.name+'-source.mkv'),'source-clip.mkv')
    for name in ('native-final-tests.log','legacy-byte-compatibility.json'):
        copy(ROOT/'.tmp'/name,name)
    sources=['native_lineart.py','native_cell_codebook.py','native_video.py','cell_codebook_z80.py',
        'cell_codebook_player.py','convert_video.py','convert_cb41.py','fixed_resident_audio.py',
        'streaming_lzsa2_player.py','compressed_sector_cache.py','row_dictionary_video.py',
        'build_cell_codebook_trd.py','verify_cell_codebook_z80.py','test_native_cell_codebook.py']
    for name in sources:copy(ROOT/'toolkit'/name,Path('producers')/name)
    for path in sorted((ROOT/'toolkit/analysis/native_lineart').glob('*.py')):
        copy(path,Path('producers/analysis')/path.name)
    attempts=['native-test-300','native-test-300-rgb','native-test-300-player','native-test-300-thin',
        'native-test-300-raster','native-test-300-readable','native-test-300-final','native-test-300-speed']
    for name in attempts:
        src=ROOT/'.tmp'/name
        log=src.with_suffix('.log')
        if log.exists():copy(log,Path('attempts')/name/'build.log')
        if not src.exists():continue
        for filename in ('conversion.json','timing.json','video-quality.json','video-preview.png'):
            if (src/filename).exists():copy(src/filename,Path('attempts')/name/filename)
        for path in src.glob('*.trd'):copy(path,Path('attempts')/name/path.name)
        for path in src.glob('ZX-video-*.json'):copy(path,Path('attempts')/name/path.name)
        work=src/'work'/Path(v['file']).stem
        if work.exists():
            for filename in ('codebook.raw','codebook.stream','states.npz','timing.json','timing.trace.txt',
                'timing.debugger.txt','timing.stderr.txt','screens.json','dynamic-rows.json'):
                if (work/filename).exists():copy(work/filename,Path('attempts')/name/filename)
    for name in ('native-readability-review','native-readability-core-review','native-raster-producers'):
        tree(ROOT/'.tmp'/name,Path('attempts')/name)
    for name in ('native-unfiltered-thin-producer.py','native-outlined-thin-producer.py','native-raster-probe.log',
        'native-raster-tests.log','raster-diagnosis.log','raster-diagnosis.trace.txt','native-speed-cli.raw'):
        if (ROOT/'.tmp'/name).exists():copy(ROOT/'.tmp'/name,Path('attempts')/name)
    probe=subprocess.check_output([args.ffprobe,'-v','error','-count_frames','-show_entries',
        'stream=codec_name,nb_read_frames,duration,width,height,sample_rate:format=duration','-of','json',str(output/'native-preview.mp4')])
    (output/'media-check.json').write_bytes(probe)
    media=json.loads(probe);assert media['streams'][0]['nb_read_frames']=='300' and float(media['format']['duration'])==30
    measured=t['disks'][0]['disk_timing'];runtime=json.loads((build/'work'/Path(v['file']).stem/'timing.json').read_bytes())
    comparison=json.loads((build/'accuracy-comparison.json').read_bytes())
    report=dict(date='2026-10-14',checks_complete=True,release_qualified=False,
        reason='Full pixels and AY pass; exact nominal 10-fps deadlines and one-field fallback fail.',
        frames=300,nominal_seconds=30,ay_ticks=1500,active_resolution=[256,144],native_resolution=[256,192],
        disk=v,independent_dirty_boot_exact=True,all_native_screen_bytes_exact=True,compared_bytes=300*6912,
        all_ay_records_exact=runtime['ay_records_exact'],actual_ay_50hz=True,audio_underruns=runtime['audio_underruns'],
        missed_nominal_frames=measured['missed_nominal_frames'],fallback_one_field_met=measured['fallback_one_field_met'],
        maximum_deviation_tstates=measured['maximum_deviation_tstates'],maximum_deviation_fields=runtime['max_late_fields'],
        late_runs=measured['late_runs'],late_runs_recovered=measured['late_runs_recovered'],
        actual_publication_span_seconds=(runtime['publications'][-1]['tstate']-runtime['publications'][0]['tstate'])/(50*70908),
        runtime_reads=measured['runtime_disk_reads'],rom_disk_irq_ula_read_service_tstates=measured['disk_read_service_tstates'],
        seek_service_tstates=measured['seek_service_tstates'],native_path_tstates=m['native_path_tstates'],
        accuracy=comparison['metrics'],preview='Nominal host-reference cadence, not actual TRD timing.',
        continuation='The native format/readability prototype is reviewable; sustained delivery remains an unresolved release requirement.')
    (output/'experiment.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    files=[dict(path=path.relative_to(output).as_posix(),bytes=path.stat().st_size,sha256=sha(path))
        for path in sorted(output.rglob('*')) if path.is_file()]
    manifest=dict(files=files,file_count=len(files),total_bytes=sum(f['bytes'] for f in files))
    (output/'archive-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(archive=str(output),files=len(files),bytes=manifest['total_bytes'],release_qualified=False)))


if __name__=='__main__':main()
