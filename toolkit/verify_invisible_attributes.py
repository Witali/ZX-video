"""Archive exact-pixel host savings and complete fourth-volume playback evidence."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('root','output','evidence'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    artifacts=[]
    def archive(path,name):
        raw=path.read_bytes();packed=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz')
        (a.evidence/filename).write_bytes(packed)
        artifacts.append(dict(file=filename,raw_bytes=len(raw),raw_sha256=sha(raw),
            archive_bytes=len(packed),archive_sha256=sha(packed)))
    cases={}
    folders={'window-unfitted':'invisible-attributes-window',
        'window-budgeted':'invisible-attributes-budgeted',
        'part04-before-fallback':'invisible-attributes-part04-guarded/round00',
        'part04-selected':'invisible-attributes-part04-guarded/round01'}
    selected=None
    keys=('start','end','frames','raw_bytes_before','raw_bytes_after','stream_bytes_before','stream_bytes_after',
        'sectors_before','sectors_after','decoder_tstates_before','decoder_tstates_after',
        'removed_attribute_writes','renderer_tstates_saved','host_candidate_eligible')
    for name,relative in folders.items():
        folder=tmp/relative;r=read(folder/'report.json')
        assert r['complete'] and r['rgb_proof']['visible_pixel_changes']==0
        assert r['rgb_proof']['bitmap_bytes_identical'] and r['proof']['both_screens_exact']
        assert all(d['attribute_stage_delta_tstates']<=0 for d in r['details'])
        assert sha((folder/'video.raw').read_bytes())==r['raw_sha256']
        assert sha((folder/'video.stream').read_bytes())==r['stream_sha256']
        cases[name]={k:r[k] for k in keys}
        cases[name]['failed_blocks']=[b['index'] for b in r['blocks'] if not b['budget_met']]
        archive(folder/'report.json',name+'-report.json')
        for file in ('video.raw','video.stream','rows.json'):
            archive(folder/file,name+'-'+file)
        if name=='part04-selected':selected=r
    assert selected['every_block_no_larger_or_slower'] and selected['host_candidate_eligible']
    fallback=read(tmp/'invisible-attributes-part04-guarded/report.json')
    assert fallback['complete'] and fallback['selected']=='round01'
    archive(tmp/'invisible-attributes-part04-guarded/report.json','fallback-report.json')
    unit=tmp/'invisible-attributes-tests.log';assert unit.read_text().strip().endswith('OK')
    archive(unit,unit.name)
    folder=tmp/'invisible-attributes-playback-part04';work=folder/'work/part04'
    oldfolder=tmp/'direct-lzsa2-header-part04';oldwork=oldfolder/'work/part04'
    m=read(folder/'part04.json');old=read(oldfolder/'part04.json')
    cpu=read(work/'cpu.json');fuse=read(work/'timing.json');before=read(oldwork/'timing.json')
    screens=read(work/'screens.json');profile=read(folder/'profile.json')
    assert m['states_sha256']==selected['states_sha256']
    assert old['states_sha256']==selected['original_states_sha256']
    assert m['video_bytes']==selected['stream_bytes_after']
    assert m['cell_codebook']['native']==old['cell_codebook']['native']
    assert m['lzsa2']['regions']==old['lzsa2']['regions']
    for name in ('audio.ayh1','rows.json'):
        assert (work/name).read_bytes()==(oldwork/name).read_bytes()
    assert (folder/'work/stream.raw').read_bytes()==(oldfolder/'work/stream.raw').read_bytes()
    assert sha((work/'codebook.raw').read_bytes())==selected['raw_sha256']
    assert sha((work/'codebook.stream').read_bytes())==selected['stream_sha256']
    cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['frames_checked']==m['frames']
    assert cpu['streaming_lzsa2_input_frontier_guarded'] and cpu['sector_cache_fifo_bounds_guarded']
    assert cpu['retired_runtime_reads_writes_or_fetches']==0
    assert fuse['complete'] and not fuse['errors'] and not fuse['failure'] and fuse['trace_nonce_exact']
    assert fuse['ay_records_exact'] and fuse['runtime_sectors_checked']==m['video_sectors']
    assert not fuse['audio_underruns'] and not fuse['ay_record_field_gaps'] and not fuse['ay_record_field_duplicates']
    assert screens['complete'] and screens['full_screens_exact'] and screens['compared_bytes']==m['frames']*6912
    assert profile['complete']
    for r in (cpu,fuse,screens,profile):assert r['trd_sha256']==m['trd_sha256']
    assert sha((folder/'part04.trd').read_bytes())==m['trd_sha256']
    assert sha((work/'timing.trace.txt').read_bytes())==fuse['trace_sha256']
    assert sha((folder/'part04.json').read_bytes())==cpu['metadata_sha256']==fuse['integrated_bootstrap_metadata_sha256']
    fields=('nominal_late_frames','actual_out_over_one_field','max_late_fields',
        'max_actual_deviation_tstates','bad_actual_intervals','late_runs')
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or any(x in ('lzsa','zx0') for x in path.relative_to(folder).parts):continue
        if path.suffix in ('.json','.trd','.raw','.stream','.ayh1','.npz','.txt'):
            archive(path,'playback-'+path.relative_to(folder).as_posix().replace('/','-'))
    for name,path in (('original-states.npz',oldwork/'states.npz'),
            ('baseline-part04.json',oldfolder/'part04.json'),
            ('baseline-timing.json',oldwork/'timing.json'),
            ('baseline-window.json',tmp/'sector-cache-window/ZX-video-front_part07.json'),
            ('baseline-window.raw',tmp/'sector-cache-window/work/ZX-video-front_part07/codebook.raw'),
            ('baseline-window.stream',tmp/'sector-cache-window/work/ZX-video-front_part07/codebook.stream'),
            ('baseline-part04.raw',oldwork/'codebook.raw'),('baseline-part04.stream',oldwork/'codebook.stream'),
            ('host-input-part04.json',tmp/'sector-cache-part04-capacity/part04.json')):
        archive(path,name)
    sources=('invisible_attribute_writes.py','probe_invisible_attributes.py','fit_invisible_attribute_budgets.py',
        'test_invisible_attributes.py','verify_invisible_attributes.py','rebuild_cell_player.py',
        'fit_lzsa2_cpu_budget.py','lzsa2_distance_cost.py','cell_codebook_z80.py','resumable_lzsa2.py')
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='32c6649',
        scope=__doc__,cases=cases,fallback=fallback,cold=cold,rendered_pixel_changes=0,bitmap_changes=0,ay_changes=0,
        decoder_instructions_changed=False,renderer_instructions_changed=False,
        decoder_measurement_scope='Identical non-streaming LZSA2 core, independent 256-byte quota calls, CPU only. '
            'Streaming guard/paging/IRQ/ULA/disk work is measured separately in complete Fuse playback.',
        attribute_stage_costs=dict(nonempty_group_base=233,per_write=23,empty_group_no_carry=94,empty_group_carry=93,
            native_cases=24,exhaustive_colour_usage_cases=49152),
        frames=m['frames'],full_fuse_screen_bytes=screens['compared_bytes'],ay_ticks=m['ay_ticks'],
        runtime_sectors_before=old['video_sectors'],runtime_sectors_after=m['video_sectors'],
        used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
        timing_before={k:before[k] for k in fields},timing_after={k:fuse[k] for k in fields},
        profile={k:profile[k] for k in ('active_elapsed','active_disk_service','active_decode_elapsed','empty_wait','queue_at_packet')},
        selected_for_release=False,
        limitations=['Only the fourth-volume candidate has complete playback evidence; window is host/component-only.',
            'Physical attribute bytes differ where their RGB colour is unused. Full bitmap/dither and rendered RGB are exact.',
            'No new four-volume release or preceding-EOF continuation verification. Generic converter defaults remain unchanged.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps({k:result[k] for k in ('complete','release','used_sectors_before','used_sectors_after','timing_after')}))


if __name__=='__main__':main()
