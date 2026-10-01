"""Verify and archive side-only disk reads against exact saved media baselines."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from profile_cell_delivery import analyze
from test_side_only_seek import timings


def read(path):return json.loads(path.read_bytes())


def trajectory(trace):
    sectors=[r['sector'] for r in trace['reads']]
    tracks=[]
    for sector in sectors:
        track=sector//16
        if not tracks or tracks[-1]!=track:tracks.append(track)
    assert all(b==a+1 for a,b in zip(tracks,tracks[1:])),tracks
    cylinders=[x//2 for x in tracks]
    distance=sum(abs(b-a) for a,b in zip(cylinders,cylinders[1:]))
    assert distance==max(cylinders)-min(cylinders)
    calls=Counter(r['kind'] for r in trace['seek_calls'])
    side_switches=sum(a==b for a,b in zip(cylinders,cylinders[1:]))
    return dict(first_sector=sectors[0],last_sector=sectors[-1],sectors=len(sectors),
        logical_tracks=tracks,first_cylinder=cylinders[0],last_cylinder=cylinders[-1],
        cylinder_steps=distance,minimum_cylinder_steps=distance,backward_steps=0,
        same_cylinder_side_changes=side_switches,rom_calls=dict(calls),
        read_elapsed_tstates=sum(r['tstates'] for r in trace['reads']),
        rom_call_elapsed_tstates={k:sum(r['tstates'] for r in trace['seek_calls'] if r['kind']==k) for k in calls},
        scope='Runtime sector traversal; cold bootstrap and physical drive experiments are separate.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','evidence','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    artifacts=[];variants={}
    def archive(path,name):
        raw=path.read_bytes();packed=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz')
        (a.evidence/filename).write_bytes(packed)
        artifacts.append(dict(file=filename,raw_bytes=len(raw),raw_sha256=sha(raw),
            archive_bytes=len(packed),archive_sha256=sha(packed)))
    for scope,previous,current,stem in (
        ('window','direct-lzsa2-header-window','side-only-seek-window-fixed','ZX-video-front_part07'),
        ('part04','invisible-attributes-playback-part04','side-only-seek-part04','part04')):
        before=tmp/previous;folder=tmp/current;work=folder/'work'/stem
        old=read(before/(stem+'.json'));m=read(folder/(stem+'.json'))
        identities={}
        for name in ('codebook.raw','codebook.stream','audio.ayh1','states.npz','rows.json'):
            original=(before/'work'/stem/name).read_bytes();actual=(work/name).read_bytes()
            assert original==actual,name
            identities[name]=sha(actual)
        assert old['lzsa2']['regions']==m['lzsa2']['regions']
        assert old['cell_codebook']['native']==m['cell_codebook']['native']
        assert old['cell_codebook']['packet_listing']==m['cell_codebook']['packet_listing']
        assert old['used_sectors']==m['used_sectors']<=2544
        cpu=read(work/'cpu.json');fuse=read(work/'timing.json');screens=read(work/'screens.json')
        baseline=read(before/'work'/stem/'timing.json')
        assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['retired_runtime_reads_writes_or_fetches']==0
        assert cpu['frames_checked']==m['frames']
        assert cpu['metadata_sha256']==sha((folder/(stem+'.json')).read_bytes())
        assert cpu['trd_sha256']==screens['trd_sha256']==fuse['trd_sha256']==m['trd_sha256']
        assert sha((folder/(stem+'.trd')).read_bytes())==m['trd_sha256']
        assert fuse['complete'] and fuse['frames']==m['frames'] and fuse['trace_nonce_exact']
        assert fuse['ay_records_exact'] and fuse['ay_ticks']==m['frames']*5 and not fuse['audio_underruns']
        assert not fuse['errors'] and not fuse['failure'] and fuse['fast_read_retries']==0
        assert fuse['nominal_late_frames']==fuse['bad_actual_intervals']==0 and not fuse['late_runs']
        assert fuse['actual_out_over_one_field']==0
        assert fuse['debugger_installed_bytes']==0
        assert fuse['trace_sha256']==sha((work/'timing.trace.txt').read_bytes())
        assert screens['complete'] and screens['full_screens_exact'] and screens['compared_bytes']==m['frames']*6912
        cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
        profile=analyze(fuse,m,cpu);write_json(folder/'profile.json',profile)
        paths=dict(before=trajectory(baseline),after=trajectory(fuse))
        assert paths['after']['rom_calls']['seek']==paths['after']['cylinder_steps']
        timing_keys=('nominal_late_frames','max_late_fields','max_actual_deviation_tstates',
                     'actual_out_over_one_field','bad_actual_intervals','late_runs')
        variants[scope]=dict(frames=m['frames'],frame_start=m['frame_start'],frame_end_exclusive=m['frame_end_exclusive'],
            video_bytes=m['video_bytes'],used_sectors=m['used_sectors'],runtime_sectors=fuse['runtime_sectors_checked'],
            exact_media_sha256=identities,decoder_renderer_packet_code_identical=True,cold=cold,
            native_screens_exact=True,fuse_screen_bytes=screens['compared_bytes'],ay_ticks=fuse['ay_ticks'],
            timing={name:{k:trace[k] for k in timing_keys} for name,trace in [('before',baseline),('after',fuse)]},
            trajectory=paths,elapsed_profile=profile['summary'] if 'summary' in profile else {k:v for k,v in profile.items() if k!='frames'})
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(x in ('lzsa','zx0') for x in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.raw','.stream','.npz','.ayh1','.txt','.trd'):
                archive(path,scope+'-'+path.relative_to(folder).as_posix().replace('/','-'))
        for path in (before/(stem+'.json'),before/'work'/stem/'timing.json'):
            archive(path,scope+'-baseline-'+path.name)
    generic=read(tmp/'side-only-seek-generic-report.json');assert generic['complete']
    conversion=read(tmp/'side-only-seek-generic/colour-out/conversion.json')
    assert conversion['complete'] and conversion['timing_verified']
    generic_checks=[]
    folder=tmp/'side-only-seek-generic/colour-out'
    for v in conversion['volumes']:
        m=read(folder/v['metadata']);assert m['side_only_seek']['enabled']
        work=folder/'work'/Path(v['file']).stem
        t=read(work/'timing.json');s=read(work/'screens.json')
        assert t['complete'] and t['nominal_late_frames']==0 and s['full_screens_exact']
        generic_checks.append(dict(file=v['file'],frames=m['frames'],used_sectors=m['used_sectors'],zero_late=True))
    swaps=read(folder/'disk-swaps.json');assert len(swaps)==2 and all(x['bootstrap_ram_exact'] for x in swaps)
    for path in sorted(folder.rglob('*')):
        if not path.is_file() or any(x in ('lzsa','zx0') for x in path.relative_to(folder).parts):continue
        if path.suffix in ('.json','.raw','.stream','.npz','.ayh1','.txt','.trd'):
            archive(path,'generic-'+path.relative_to(folder).as_posix().replace('/','-'))
    archive(tmp/'side-only-seek-generic/colour.mkv','generic-source.mkv')
    archive(tmp/'side-only-seek-generic-report.json','generic-checks.json')
    log=tmp/'side-only-seek-tests.log';assert log.read_text().strip().endswith('OK');archive(log,'unit-tests.log')
    archive(tmp/'side-only-seek-window-build.log','initial-metadata-guard-failure.log')
    sources=('fap3_disk_z80.py','side_only_seek.py','test_side_only_seek.py','benchmark_fap3_disk.py',
        'cell_codebook_player.py','rebuild_cell_player.py','guarded_cb46.py','check_generic_cb41.py',
        'analyze_side_only_seek.py','measure_fap3_fuse.py','profile_cell_delivery.py')
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='23dc128',scope=__doc__,
        variants=variants,unit_tests=8,geometry_cases=2560,independent_full_flags_cases=1024,
        ram_instruction_timings=timings(),settle_loop_tstates=717,extra_stack_bytes=2,
        generic_fixture=generic_checks,modeled_rom_swaps=swaps,
        sources=dict(drive='https://deramp.com/downloads/floppy_drives/shugart/SA410-460%20Service%20manual.pdf',
            controller='https://www.abc80.net/archive/luxor/diskdrives/drives/western-digital-FD1791.pdf',
            rom='https://github.com/programandala-net/tr-dos',z80='https://www.zilog.com/docs/z80/um0080.pdf'),
        limitations=['Only the saved window and full part 4 have sustained new-player evidence.',
            'Parts 1..3 and actual preceding-EOF continuation gates remain open; root releases unchanged.',
            'Drive settling is based on the SA460 200 us contract at standard 3.5469 MHz; no physical drive tested.',
            'Runtime cylinder distance already was minimal. The saving removes redundant commands and settle delays, not physical forward steps.',
            'ROM/physical/IRQ/ULA elapsed time is separate from deterministic RAM instruction counts.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,release=False,artifacts=len(artifacts),variants={k:dict(frames=v['frames'],timing=v['timing'],trajectory=v['trajectory']) for k,v in variants.items()})))


if __name__=='__main__':main()
