"""Derive paired storage/timing totals and verify generic stream identity."""
import argparse
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('measurement','generic','generic-baseline','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();measured=json.loads(a.measurement.read_text());generic=json.loads(a.generic.read_text())
    baseline=json.loads(a.generic_baseline.read_text())
    if not measured['complete'] or not generic['complete']:raise ValueError('incomplete runs')
    old,new=measured['variants'];pairs=[]
    for before,after in zip(old['volumes'],new['volumes'],strict=True):
        if before['video_sha256']!=after['video_sha256']:raise AssertionError('video changed')
        pairs.append(dict(part=before['part'],frames=before['frames'],
            sectors_before=before['used_sectors'],sectors_after=after['used_sectors'],
            sectors_delta=after['used_sectors']-before['used_sectors'],
            boot_mocked_tstates_before=before['boot_mocked_tstates'],boot_mocked_tstates_after=after['boot_mocked_tstates'],
            boot_mocked_tstates_delta=after['boot_mocked_tstates']-before['boot_mocked_tstates'],
            video_sha256=after['video_sha256']))
    totals=[]
    for variant in measured['variants']:
        rows=variant['volumes'];totals.append(dict(name=variant['name'],
            used_sectors=sum(r['used_sectors'] for r in rows),
            nominal_misses=sum(r['timing']['missed_nominal_frames'] for r in rows),
            ay_missing_fields=sum(r['timing']['ay_missing_fields'] for r in rows),
            runtime_sectors=sum(r['timing']['runtime_disk_reads'] for r in rows),
            video_bytes=sum(r['video_bytes'] for r in rows),
            bootstrap_seconds=sum(r['timing']['startup_and_playback_timing']['bootstrap_tstates'] for r in rows)/3546900,
            playback_seconds=sum(r['timing']['startup_and_playback_timing']['playback_tstates'] for r in rows)/3546900))
    old_cases={r['source']:r for r in baseline['cases']};checks=[]
    for case in generic['cases']:
        original=old_cases[case['source']]
        if case['stream_sha256']!=original['stream_sha256']:raise AssertionError('generic stream differs')
        checks.append(dict(source=case['source'],frames=case['frames'],disks=case['disks'],
            filtered_boot_tables=case['filtered_boot_tables'],stream_identical=True,
            all_cpu_frames_verified=all(c['complete'] and c['full_compact_and_native_comparison'] for c in case['cpu']),
            full_fuse=all(d.get('disk_timing',{}).get('complete',False) for d in case['timing']['disks']),
            nominal_met=case['timing']['all_nominal_deadlines_met']))
    report=dict(complete=True,release=False,pairs=pairs,totals=totals,generic=checks,
        size_controls=measured['size_controls'],
        nominal_and_fallback_failed=all(not r['timing']['nominal_deadlines_met'] and not r['timing']['fallback_one_field_met']
            for v in measured['variants'] for r in v['volumes']),default_enabled=False,
        startup_cycles=dict(table_pass=541409,call=17,total=541426),
        cpu_boot_excludes='ROM execution, physical latency, IRQ and ULA; not a real-time boot duration')
    a.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
