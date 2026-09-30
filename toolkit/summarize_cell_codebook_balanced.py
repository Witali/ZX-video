"""Audit and archive the selected full CB41 set; optionally install root TRDs."""
import argparse
import gzip
import json
from pathlib import Path
import shutil

from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_bytes())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('work','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--install-root',action='store_true')
    a = p.parse_args()
    plan = read(a.work/'windows/plan.json')
    measured = read(a.work/'measured/measurements.json')
    capacity = read(a.work/'build/capacity.json')
    continuation = read(a.work/'continuation/continuation.json')
    swaps = read(a.work/'continuation/swaps.json')
    assert all(r['complete'] for r in (plan,measured,capacity,continuation))
    assert capacity['all_volumes_fit'] and plan['boundaries']==[0]+[v['end'] for v in capacity['volumes']]
    assert measured['boundary_selection']['plan_sha256']==sha((a.work/'windows/plan.json').read_bytes())
    assert capacity['measurements_sha256']==sha((a.work/'measured/measurements.json').read_bytes())
    for report in (plan,measured,capacity,continuation):
        for name,value in report['source_sha256_lf'].items():
            assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==value, name
    assert len(swaps)==len(capacity['volumes'])-1
    assert all(row[key] for row in swaps for key in ('prompt_exact','wrong_disk_rejected',
        'wrong_series_rejected','correct_disk_accepted','bootstrap_ram_exact'))
    volumes = []
    previous_native = read(ROOT/'cell_codebook_sustained_profile.json')
    previous_meta = json.loads(gzip.decompress((ROOT/'cell_codebook_sustained_evidence/metadata.json.gz').read_bytes()))
    for row, continued in zip(capacity['volumes'],continuation['volumes'],strict=True):
        part = row['volume']
        folder = a.work/f'build/volume-{part}'
        metadata, timing, screens = [read(folder/name) for name in ('metadata.json','timing.json','full-screens.json')]
        identity = sha((folder/'candidate.trd').read_bytes())
        assert identity==row['trd_sha256']==timing['trd_sha256']==screens['trd_sha256']==continued['trd_sha256']
        assert timing['complete'] and screens['complete'] and screens['full_screens_exact']
        assert row['frames']==timing['frames']==screens['frames']==continued['frames']
        assert screens['compared_bytes']==row['frames']*6912
        assert screens['timing_sha256']==sha((folder/'timing.json').read_bytes())
        assert timing['trace_sha256']==sha((folder/'timing.trace.txt').read_bytes())
        assert continued['report_sha256']==sha((a.work/f'continuation/part-{part}.json').read_bytes())
        for tested in (timing,continued):
            assert tested['nominal_late_frames']==0 and tested['audio_underruns']==0 and tested['ay_records_exact']
        assert timing['ay_record_field_gaps']==timing['ay_record_field_duplicates']==0
        assert continued['ay_gaps']==continued['ay_duplicates']==0
        assert timing['runtime_sectors_checked']==row['video_sectors'] and timing['fast_read_retries']==0
        assert not timing['errors'] and not timing['late_runs']
        pubs = timing['publications']
        fields = [b['field']-a['field'] for a,b in zip(pubs,pubs[1:])]
        assert set(fields)=={6}
        intervals = [b['tstate']-a['tstate'] for a,b in zip(pubs,pubs[1:])]
        assert all(abs(delta-6*70908)<=64 for delta in intervals)
        assert metadata['cell_codebook']['native']==previous_meta['cell_codebook']['native']
        assert metadata['cell_codebook']['packet_listing']==previous_meta['cell_codebook']['packet_listing']
        for name,value in screens['source_sha256_lf'].items():
            assert sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))==value
        for item in screens['passes']:
            prefix=folder/f'full-captures/bytes-{item["start"]}-{item["end"]}'
            assert item['trace_sha256']==sha(prefix.with_suffix('.trace.txt').read_bytes())
            assert item['debugger_sha256']==sha(prefix.with_suffix('.debugger.txt').read_bytes())
        volumes.append(dict(part=part,frame_start=row['start'],frames=row['frames'],
            trd_sha256=identity,root_file=f'ZX-video-five-level_part{part:02}.trd',
            used_sectors=row['used_sectors'],free_sectors=row['free_sectors'],
            video_sectors=row['video_sectors'],ay_ticks=timing['ay_ticks'],
            all_six_field_intervals=True,nominal_late_frames=0,
            fps_at_50hz=(len(pubs)-1)*70908*50/(pubs[-1]['tstate']-pubs[0]['tstate']),
            actual_interval_tstates=[min(intervals),max(intervals)],
            actual_phase_tstates=[min(timing['actual_phase_tstates']),max(timing['actual_phase_tstates'])],
            late_runs=[],full_screen_bytes_compared=screens['compared_bytes'],
            ay_records_exact=True,sector_bytes_exact=True,elapsed_timing=timing['elapsed_timing'],
            sectors_before_first_publication=sum(r['end_tstate']<=pubs[0]['tstate'] for r in timing['reads']),
            sectors_after_first_publication=sum(r['start_tstate']>=pubs[0]['tstate'] for r in timing['reads'])))
    a.evidence.mkdir(parents=True,exist_ok=True)
    artifacts = []
    def archive(path, name):
        data=path.read_bytes();coded=gzip.compress(data,mtime=0)
        (a.evidence/name).write_bytes(coded)
        artifacts.append(dict(file=name,raw_bytes=len(data),archive_bytes=len(coded),
            raw_sha256=sha(data),archive_sha256=sha(coded)))
    for name in ('windows/plan.json','measured/measurements.json','build/capacity.json','continuation/swaps.json',
                 'continuation/continuation.json'):
        archive(a.work/name,name.replace('/','-')+'.gz')
    for part in range(1,len(volumes)+1):
        folder=a.work/f'build/volume-{part}'
        for name in ('metadata.json','states.npz','timing.json','timing.trace.txt','timing.debugger.txt','full-screens.json'):
            archive(folder/name,f'volume-{part}-{name}.gz')
        for name in ('codebook.raw','codebook.stream','row-dictionary.json','audio.ayh1'):
            archive(a.work/f'measured/volume-{part}'/name,f'volume-{part}-{name}.gz')
        for path in sorted((folder/'full-captures').glob('bytes-*.txt')):
            if path.stat().st_size:
                archive(path,f'volume-{part}-'+path.name+'.gz')
        for path in sorted((a.work/'continuation').glob(f'part-{part}.*')):
            archive(path,'continuation-'+path.name+'.gz')
    for path in sorted((a.work/'continuation').glob('*.ram')):
        archive(path,'continuation-'+path.name+'.gz')
    for path in sorted((a.work/'continuation').glob('*.szx')):
        archive(path,'continuation-'+path.name+'.gz')
    if a.install_root:
        for v in volumes:
            target=ROOT.parent/v['root_file']
            shutil.copyfile(a.work/f'build/volume-{v["part"]}/candidate.trd',target)
            assert sha(target.read_bytes())==v['trd_sha256']
    result=dict(complete=True,release=False,goal_achieved=False,date='2026-09-30',baseline_commit='2a1686d',
        scope='Complete authorized five-level movie on three independently bootable TRDs; native Fuse cadence/full screens and snapshot continuation verified. Generic converter integration remains.',
        movie_playback_verified=True,generic_converter_integrated=False,
        frames=sum(v['frames'] for v in volumes),ay_ticks=sum(v['ay_ticks'] for v in volumes),
        compared_screen_bytes=sum(v['full_screen_bytes_compared'] for v in volumes),
        nominal_late_frames=0,late_runs=[],full_screens_exact=True,ay_records_exact=True,
        video_bytes=sum(v['compressed_bytes'] for v in measured['volumes']),
        previous_video_bytes=1840522,compressed_byte_delta=sum(v['compressed_bytes'] for v in measured['volumes'])-1840522,
        native_instruction_delta_tstates=0,previous_native_reference_trd=previous_native['trd_sha256'],
        selected_boundaries=plan['boundaries'],boundary_window_frames=plan['windows_frames'],
        previous_window_bytes=plan['previous_window_bytes'],candidate_window_bytes=plan['candidate_window_bytes'],
        volumes=volumes,continuation=continuation['volumes'],physical_drive_swap_verified=False,
        source_preparation_sha256=measured['preparation_sha256'],root_images_installed=a.install_root,artifacts=artifacts)
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('frames','ay_ticks','compared_screen_bytes','nominal_late_frames','video_bytes')}))


if __name__=='__main__':
    main()
