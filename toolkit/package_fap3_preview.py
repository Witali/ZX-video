"""Install a measured experimental preview, without replacing the release.

Requires EOF, exact AY records, verified sector bytes, image samples and
100% progress for every volume, plus all mocked disk-change checks. Timing
failures are retained and explicitly disqualify this package as a release.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('build',type=Path);p.add_argument('--repository',type=Path,required=True)
    args=p.parse_args(); root=args.repository.resolve(); build=args.build.resolve()
    output=root/'toolkit/fap3_preview'; output.mkdir(exist_ok=True)
    volumes=json.loads((build/'volumes.json').read_text()); swaps=json.loads((build/'swap_checks.json').read_text())
    if len(swaps)!=len(volumes)-1 or not all(all(v for k,v in row.items() if k.endswith(('_exact','_rejected','_accepted'))) for row in swaps):
        raise ValueError('incomplete disk change checks')
    rows=[]; next_frame=0
    for row in volumes:
        part=row['part']; stem=f'ZX-video-optimized-preview_part{part:02}'
        meta=json.loads((build/(stem+'.json')).read_text())
        report=json.loads((build/f'fuse_part{part:02}.json').read_text())
        image=(build/(stem+'.trd')).read_bytes(); digest=hashlib.sha256(image).hexdigest()
        if len(image)!=655360 or digest!=meta['trd_sha256'] or digest!=report['trd_sha256']:
            raise ValueError('image differs from measured file')
        if not report['complete'] or report['errors'] or meta['frame_start']!=next_frame:
            raise ValueError('incomplete or discontinuous movie')
        next_frame=meta['frame_end_exclusive']
        pubs=report['publications']; elapsed=(pubs[-1]['tstate']-pubs[0]['tstate'])/(50*70908)
        rom=[r['tstates']-17 for r in report['reads']]
        rows.append(dict(file=stem+'.trd',sha256=digest,frames=meta['frames'],
            frame_start=meta['frame_start'],frame_end_exclusive=next_frame,
            free_sectors=meta['free_sectors'],video_bytes=meta['video_bytes'],
            actual_average_fps=(len(pubs)-1)/elapsed,playback_first_to_last_seconds=elapsed,
            nominal_late_frames=report['nominal_late_frames'],max_late_fields=report['max_late_fields'],
            actual_out_over_one_field=report['actual_out_over_one_field'],
            max_actual_deviation_seconds=report['max_actual_deviation_tstates']/(50*70908),
            audio_underruns=report['audio_underruns'],runtime_sectors_checked=report['runtime_sectors_checked'],
            trdos_total_seconds=sum(rom)/(50*70908),trdos_mean_tstates=sum(rom)/len(rom),trdos_max_tstates=max(rom),
            unrecovered_late_runs=sum(r['recovered_at'] is None for r in report['late_runs'])))
        shutil.copyfile(build/(stem+'.trd'),root/(stem+'.trd'))
        shutil.copyfile(build/(stem+'.json'),output/f'part{part:02}.json')
        shutil.copyfile(build/f'fuse_part{part:02}.json',output/f'fuse_part{part:02}.json')
    if next_frame!=4221: raise ValueError('preview must include the authorized edit through EOF')
    shutil.copyfile(build/'swap_checks.json',output/'swap_checks.json')
    summary=dict(status='experimental preview; timing and three-disk target FAILED',release=False,
        baseline_commit='2e95b6d',frames=next_frame,ay_records=next_frame*6,volumes=rows,
        full_pixel_comparison=False,pixel_samples_per_frame=80,
        nominal_deadlines_pass=False,fallback_jitter_pass=False,ay_cadence_pass=False,
        disk_changes_cpu_verified=True,disk_changes_rom_mocked=True,physical_drive_verified=False,
        adapter_cpu=dict(timing_source='https://www.zilog.com/docs/z80/um0080.pdf',
            excludes='ROM, physical disk latency, IRQ and ULA contention',
            refill_4_bytes=dict(old=810,new=855,delta=45),
            refill_256_bytes=dict(old=4961,new=5717,delta=756),
            hook_call_tstates=17,adapter_no_completed_sector=28,adapter_eof=74,
            adapter_read_base=739,upper_ring_bank_extra=4,track_wrap_extra=11,ring_bank_wrap_extra=44,
            ay_normal_path_delta=0,ay_full_queue_retry_tstates=73))
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
