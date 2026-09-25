"""Cross-check completed storage, CPU and assembled-layout experiment reports."""
import json
from pathlib import Path
from build_fap3_trd import sha


def main():
    root=Path(__file__).parent
    def read(name):return json.loads((root/name).read_bytes())
    p=read('fragment_cost_selection_probe.json')
    c=read('fragment_cost_selection_cpu.json')
    d=read('fragment_cost_selection_capacity.json')
    model=read('uncontended_frame_cpu.json')
    if not all(x['complete'] for x in (p,c,d,model)):raise AssertionError('partial report')
    if sha((root/'fragment_cost_selection_probe.json').read_bytes())!=d['probe_sha256']:
        raise AssertionError('capacity source hash')
    if sha((root/'uncontended_frame_cpu.json').read_bytes())!=c['baseline_report_sha256']:
        raise AssertionError('CPU baseline hash')
    baseline=next(v for v in model['volumes'] if v['part']==c['part'])
    if (p['source_sha256']!=baseline['raw_sha256'] or c['states_sha256']!=p['states_sha256']
            or c['states_sha256']!=model['states_sha256'] or not p['baseline_reencode_byte_identical']):
        raise AssertionError('baseline input differs')
    if (c['start'],c['end'],c['checked_frames'])!=(2921,4221,1300):raise AssertionError('CPU scope differs')
    if [f['frame'] for f in c['frames']]!=list(range(c['start'],c['end'])):raise AssertionError('frame gap')
    for actual,old in zip(c['frames'],baseline['frames'],strict=True):
        if actual['baseline_tstates']!=old['tstates'] or actual['tstates']-actual['baseline_tstates']!=actual['delta_tstates']:
            raise AssertionError('per-frame timing comparison')
    for key in ('baseline_tstates','tstates','delta_tstates'):
        if sum(f[key] for f in c['frames'])!=c[key]:raise AssertionError('CPU sum')
    if not c['full_volume_compact_and_both_native_exact']:raise AssertionError('pixel coverage')
    if sum(f['delta_tstates']>0 for f in c['frames'])!=c['slower_frames']:raise AssertionError('slow frame count')
    candidate=next(v for v in p['variants'] if v['allowance_bits']==64)
    if candidate['sha256']!=c['raw_sha256']:raise AssertionError('CPU candidate differs')
    for volume in d['variants']:
        measured=p['baseline'] if volume['name']=='baseline' else next(
            v for v in p['variants'] if volume['name']==f"allowance-{v['allowance_bits']}")
        if (volume['source_sha256']!=measured['sha256'] or volume['video_bytes']!=measured['stream_bytes']
                or volume['video_sectors']!=measured['sectors'] or not measured['all_zx0_blocks_exact']
                or volume['free_sectors']!=2544-volume['used_sectors']
                or volume['fits']!=(volume['used_sectors']<=2544)):
            raise AssertionError('assembled capacity differs')
        if volume['used_sectors']!=volume['video_start_sector']-16+volume['video_physical_sectors']:
            raise AssertionError('disk overhead sum')
    if len(p['variants'])!=3 or not all(v['whole_movie_scalar_video_ay_exact'] for v in p['variants']):
        raise AssertionError('scalar verification scope')
    print('Verified: three ZX0 candidates, 4221-frame scalar comparisons, 1300-frame CPU run and four disk layouts.')


if __name__=='__main__':main()
