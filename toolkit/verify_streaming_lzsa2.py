"""Archive rejected/partial streaming-decoder experiments without release claims."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
import resumable_lzsa2


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output','evidence'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True);tmp=a.root/'.tmp';artifacts=[]
    def archive(path,name):
        raw=path.read_bytes();data=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz')
        (a.evidence/filename).write_bytes(data)
        artifacts.append(dict(file=filename,raw_sha256=sha(raw),archive_sha256=sha(data),raw_bytes=len(raw),archive_bytes=len(data)))
    baseline=read(tmp/'sector-cache-window/ZX-video-front_part07.json')
    generated,_,_=resumable_lzsa2.build(core=baseline['decoder_labels']['start'],core_limit=0x8e80)
    assert [dict(address=at,code_hex=data.hex()) for at,data in generated]==[
        {k:r[k] for k in ('address','code_hex')} for r in baseline['lzsa2']['regions']]
    tests=read(tmp/'streaming-lzsa2-tests.json');assert tests['complete'] and tests['cases']==40
    assert all(x['exact'] for c in tests['independent'] for x in c['full_flags'])
    variants={};stem='ZX-video-front_part07'
    for name in ('window','fast-window','hybrid-window','bypass-window'):
        folder=tmp/('streaming-lzsa2-'+name);work=folder/'work'/stem
        m=read(folder/(stem+'.json'));cold=read(folder/'timing.json')['disks'][0]['cold']
        assert cold['dirty_ram_boot_exact'] and m['used_sectors']==781
        assert sha((folder/(stem+'.trd')).read_bytes())==m['trd_sha256']
        for file in ('codebook.raw','codebook.stream','audio.ayh1'):
            assert (work/file).read_bytes()==(tmp/'sector-cache-window/work'/stem/file).read_bytes()
        row=dict(cold=cold,used_sectors=m['used_sectors'],trd_sha256=m['trd_sha256'],video_bytes=m['video_bytes'],
            full_native_verified=False,full_fuse_verified=False)
        selected=[folder/(stem+'.json'),folder/(stem+'.trd'),folder/'timing.json']
        if (work/'cpu.json').exists():
            cpu=read(work/'cpu.json');assert cpu['complete'] and cpu['all_native_screens_exact']
            assert cpu['streaming_lzsa2_input_frontier_guarded'] and cpu['sector_cache_fifo_bounds_guarded']
            row['full_native_verified']=True;selected.append(work/'cpu.json')
        if (work/'timing.json').exists():
            fuse=read(work/'timing.json');assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['audio_underruns']
            assert fuse['trd_sha256']==m['trd_sha256'] and fuse['runtime_sectors_checked']==726
            row.update(full_fuse_verified=True,full_fuse_screens_verified=False,
                timing={k:fuse[k] for k in ('frames','ay_ticks','nominal_late_frames','actual_out_over_one_field','max_late_fields','bad_actual_intervals','late_runs')})
            selected += [work/'timing.json',work/'timing.trace.txt',work/'timing.debugger.txt',work/'timing.stderr.txt']
        for path in selected:archive(path,name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
        variants[name]=row
    for name in ('streaming-lzsa2-tests.json','streaming-lzsa2-tests.log','streaming-lzsa2-tests-initial.log',
            'streaming-lzsa2-tests-slow.json','streaming-lzsa2-tests-fast.json',
            'resumable_lzsa2-slow.py','resumable_lzsa2-fast.py','inplace_streaming_core-fast.py','streaming-lzsa2-fast-profile.json'):
        archive(tmp/name,name)
    sources=('resumable_lzsa2.py','streaming_lzsa2_player.py','streaming_slot_queue.py','inplace_streaming_core.py',
        'test_streaming_lzsa2.py','build_cell_codebook_trd.py','cell_codebook_player.py','rebuild_cell_player.py','verify_streaming_lzsa2.py')
    result=dict(complete=True,release=False,baseline_commit='bc615ab',date='2026-10-01',
        scope=__doc__,variants=variants,all_compressed_and_raw_media_unchanged=True,default_decoder_code_unchanged=True,
        component_cases=40,independent_full_flags_cases=240,component_cpu_baseline=tests['baseline']['total_tstates'],
        component_cpu_candidate=tests['candidate']['total_tstates'],
        component_cpu_delta=tests['total_tstates_delta'],
        decoder_guard_tstates=dict(available_header_including_call=96,available_long_literals_including_call=135,
            completed_token_branches_delta=0,completed_long16_branch_delta=0,completed_long8_branch_delta=-2),
        decision='Keep opt-in prototype only. Eager and hybrid measured variants regress timing versus the sector-cache baseline. '
            'Final branch-bypass variant has component and cold checks only; playback remains unverified. '
            'User redirected work to better compression at unchanged decoding cost; stop decoder experiments.',
        limitations=['No new release; root TRDs unchanged.','No final-bypass native whole-window or Fuse run.',
            'Component totals deliberately force prefix waits; they are not playback or full-set timing.',
            'Measured variants compare all native screens but only sampled Fuse pixels.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result);print(json.dumps(dict(complete=True,artifacts=len(artifacts),variants=list(variants),release=False)))


if __name__=='__main__':main()
