"""Verify unchanged-media branch-bypass LZSA2 playback on a window and part 4."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output','evidence'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--direct-header',action='store_true',help='verify direct guard against the saved branch-bypass player')
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    cases=[('window','streaming-lzsa2-bypass-window','sector-cache-window','ZX-video-front_part07','cache-timing.json'),
           ('part04','streaming-bypass-part04','sector-cache-part04-capacity','part04','timing.json')]
    if a.direct_header:
        cases=[('window','direct-lzsa2-header-window','streaming-lzsa2-bypass-window','ZX-video-front_part07','timing.json'),
               ('part04','direct-lzsa2-header-part04','streaming-bypass-part04','part04','timing.json')]
    artifacts=[];variants={}
    def archive(path,name):
        raw=path.read_bytes();data=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz');(a.evidence/filename).write_bytes(data)
        artifacts.append(dict(file=filename,raw_sha256=sha(raw),archive_sha256=sha(data),raw_bytes=len(raw),archive_bytes=len(data)))
    def timing(r):return {k:r[k] for k in ('nominal_late_frames','actual_out_over_one_field','max_late_fields',
        'max_actual_deviation_tstates','bad_actual_intervals','late_runs')}
    for name,directory,baseline,stem,tracefile in cases:
        folder=tmp/directory;oldfolder=tmp/baseline;work=folder/'work'/stem;oldwork=oldfolder/'work'/stem
        m=read(folder/(stem+'.json'));old=read(oldfolder/(stem+'.json'))
        if a.direct_header:assert m['lzsa2']['layout']['direct_header_guard']
        assert m['cell_codebook']['native']==old['cell_codebook']['native']
        hashes={}
        for file in ('codebook.raw','codebook.stream','audio.ayh1','rows.json','states.npz'):
            raw=(work/file).read_bytes();assert raw==(oldwork/file).read_bytes();hashes[file]=sha(raw)
        assert m['video_bytes']==old['video_bytes'] and m['frames']==old['frames']
        cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
        cpu=read(work/'cpu.json');fuse=read(work/'timing.json');before=read(oldwork/tracefile)
        screens=read(work/'screens.json');profile=read(folder/'profile.json')
        assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['frames_checked']==m['frames']
        assert cpu['streaming_lzsa2_input_frontier_guarded'] and cpu['sector_cache_fifo_bounds_guarded']
        assert cpu['retired_runtime_reads_writes_or_fetches']==0
        assert fuse['complete'] and not fuse['errors'] and not fuse['failure'] and fuse['trace_nonce_exact']
        assert fuse['ay_records_exact'] and fuse['runtime_sectors_checked']==m['video_sectors']
        assert not fuse['audio_underruns'] and not fuse['ay_record_field_gaps'] and not fuse['ay_record_field_duplicates']
        assert screens['complete'] and screens['full_screens_exact'] and screens['compared_bytes']==m['frames']*6912
        assert profile['complete']
        for r in (cpu,fuse,screens,profile):assert r['trd_sha256']==m['trd_sha256']
        assert sha((folder/(stem+'.trd')).read_bytes())==m['trd_sha256']
        assert sha((work/'timing.trace.txt').read_bytes())==fuse['trace_sha256']
        assert sha((folder/(stem+'.json')).read_bytes())==cpu['metadata_sha256']==fuse['integrated_bootstrap_metadata_sha256']
        variants[name]=dict(frames=m['frames'],frame_start=m['frame_start'],frame_end_exclusive=m['frame_end_exclusive'],
            trd_sha256=m['trd_sha256'],exact_media_hashes=hashes,renderer_code_identical=True,
            cold=cold,full_native_frames=m['frames'],full_fuse_screen_bytes=screens['compared_bytes'],
            ay_ticks=m['ay_ticks'],runtime_sectors=m['video_sectors'],
            used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
            timing_before=timing(before),timing_after=timing(fuse),
            profile={k:profile[k] for k in ('active_elapsed','active_disk_service','active_decode_elapsed','empty_wait','queue_at_packet')})
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(k in ('zx0','lzsa') for k in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.stream','.raw','.npz','.ayh1','.txt'):
                archive(path,name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='2c3bf78',scope=__doc__,
        variants=variants,all_compressed_and_raw_media_unchanged=True,pixel_changes=0,ay_changes=0,
        decoder_costs=dict(completed_token_branches_delta_tstates=0,completed_long16_delta_tstates=0,
            completed_long8_delta_tstates=-2,available_prefix_header_including_call_tstates=96,
            available_prefix_long_literals_including_call_tstates=135,
            scope='Instruction counts from the existing branch-bypass component report; incomplete-input guards still cost time. '
                  'Actual decoder bridge elapsed costs, including paging/IRQ/ULA, are reported separately per run.'),
        previous_component_report='toolkit/streaming_lzsa2_report.json',
        selected=False,
        decision='Do not select the branch-bypass player for release: the complete window improves to two isolated misses, '
            'but full part 4 has 31 nominal misses versus 29, with sustained queue starvation. Full content is exact. '
            'Retain the unchanged-stream builds and profile. Next inspect token-entry prefix guard work; do not infer full-volume '
            'or four-disk readiness from the shorter window.',
        limitations=['No complete four-volume set or preceding-EOF continuation gates yet.',
                     'A one-field counter delay does not imply actual-OUT compliance: inspect max_actual_deviation_tstates.'],
        artifacts=artifacts,source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('resumable_lzsa2.py','streaming_lzsa2_player.py','inplace_streaming_core.py','streaming_slot_queue.py',
             'build_cell_codebook_trd.py','verify_cached_cell_player.py','profile_cell_delivery.py','verify_streaming_bypass_playback.py')})
    if a.direct_header:
        previous=read(tmp/'streaming-lzsa2-tests.json');current=read(tmp/'direct-lzsa2-header-tests.json')
        assert previous['complete'] and current['complete'] and previous['stream_sha256']==current['stream_sha256']
        assert current['cases']==40 and all(x['exact'] for c in current['independent'] for x in c['full_flags'])
        assert (tmp/'direct-lzsa2-header-unit.log').read_text().strip().endswith('OK')
        for name in ('direct-lzsa2-header-unit.log','direct-lzsa2-header-tests.json','direct-lzsa2-header-tests.log'):
            archive(tmp/name,name)
        result.update(baseline_commit='ca70859',scope='Direct AF-dead header guard: same compressed/media bytes on window and full part 4.',
            component_cases=40,independent_full_flags_cases=240,
            component_previous_tstates=previous['candidate']['total_tstates'],
            component_current_tstates=current['candidate']['total_tstates'],
            component_delta_tstates=current['candidate']['total_tstates']-previous['candidate']['total_tstates'],
            component_scope='Same 40 blocks; deliberately forced one-sector supplies and fixed output quotas, mocked ROM. Not real playback costs.',
            header_liveness_cases=512,default_streaming_code_unchanged=True,
            decision='Retain the opt-in direct header optimization with exact content evidence; assess complete-volume actual OUT deadlines separately. '
                'Do not replace root images or claim the four-volume objective from this single-volume result.')
        result['decoder_costs'].update(previous_available_prefix_header_tstates=96,
            available_prefix_header_tstates=46,available_prefix_header_delta_tstates=-50,
            direct_guard_has_call=False,
            input_wait_entry_tstates=dict(previous=98,current=63,delta=-35),
            overflow_wait_entry_tstates=dict(previous=89,current=51,delta=-38),
            partial_resume_low_high_tstates=dict(previous=12,current=31,delta=19),
            partial_resume_equal_high_tstates=dict(previous=12,current=59,delta=47),
            scope='Independent Z80 measurements at guard/body/input_wait boundaries. Resume now rechecks the output quota '
                'so completed input follows the patched direct path. CALL/RET/AF saves are eliminated on available headers; '
                'long-literal guards are unchanged. Quota/producer/IRQ/ULA/physical effects are measured separately.')
        result['decoder_costs'].pop('available_prefix_header_including_call_tstates')
        for name in ('test_direct_lzsa2_header.py','test_streaming_lzsa2.py','cell_codebook_player.py','rebuild_cell_player.py'):
            result['source_sha256_lf'][name]=sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),variants={name:v['timing_after'] for name,v in variants.items()},release=False)))


if __name__=='__main__':main()
