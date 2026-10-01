"""Archive same-stream sector-cache correctness, CPU costs and real timing."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
from test_compressed_sector_cache import SectorCacheTests
import compressed_sector_cache


def read(path):return json.loads(path.read_bytes())


def check_events(events,sectors):
    count=first=last=0;counts=Counter();wraps=Counter();pending=False
    for e in events:
        assert (e['count'],e['read_index'],e['write_index'])==(count,first,last),e
        kind=e['kind'];counts[kind]+=1
        if kind=='loaded':
            assert count<sectors and not pending
            count+=1;wraps['write']+=last==sectors-1;last=(last+1)%sectors
        elif kind=='take':
            assert not pending;pending=count>0
        elif kind=='copied':
            assert pending and count>0;pending=False
            count-=1;wraps['read']+=first==sectors-1;first=(first+1)%sectors
    assert not pending and count==0 and counts['loaded']==counts['copied']
    assert wraps['read'] and wraps['write']
    return dict(complete=True,events=dict(counts),wraps=dict(wraps),final_count=count)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','capacity','gap','tests','failed-tests','profile','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    record,=read(a.after/'volumes.json');m=read(a.after/record['metadata']);work=a.after/'work'/Path(record['file']).stem
    prior,=read(a.before/'volumes.json');old=read(a.before/prior['metadata']);old_work=a.before/'work'/Path(prior['file']).stem
    assert sha((a.after/record['file']).read_bytes())==m['trd_sha256']==record['sha256']
    streams={}
    for name in ('codebook.raw','codebook.stream','audio.ayh1','states.npz'):
        data=(work/name).read_bytes();assert data==(old_work/name).read_bytes();streams[name]=sha(data)
    for key in ('native','packet_listing','clock_listing'):assert old['cell_codebook'][key]==m['cell_codebook'][key]
    assert old['resident_audio']['compiled']==m['resident_audio']['compiled']
    regions,labels,listing=compressed_sector_cache.build(m)
    cache=m['compressed_sector_cache']
    assert labels==cache['labels'] and listing==cache['listing']
    assert [dict(address=at,code_hex=data.hex()) for at,data in regions]==cache['regions']
    cpu=read(work/'cpu-cache-guard.json');fuse=read(work/'timing.json');trace=read(work/'cache-timing.json');screens=read(work/'screens.json')
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['sector_cache_fifo_bounds_guarded']
    assert cpu['immutable_audio_bank_guarded']==6 and not cpu['retired_runtime_reads_writes_or_fetches']
    for r in (fuse,trace):
        assert r['complete'] and r['ay_records_exact'] and not r['audio_underruns']
        assert not r['ay_record_field_gaps'] and not r['ay_record_field_duplicates']
        assert r['trd_sha256']==m['trd_sha256'] and r['integrated_bootstrap_metadata_sha256']==sha((a.after/record['metadata']).read_bytes())
    assert screens['complete'] and screens['full_screens_exact'] and screens['trd_sha256']==m['trd_sha256']
    events=check_events(trace['sector_cache_events'],cache['sectors'])
    cold=read(a.after/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
    gap=read(a.gap);assert gap['complete'] and gap['extra_bank']==7 and gap['extra_guard']==[0xe300,0x10000]
    assert gap['additional_banked_guards']==[dict(bank=7,start=0xe300,end=0x10000)]
    assert a.tests.read_text().strip().endswith('OK')
    tests=SectorCacheTests();tests.test_fifo_wrap_full_empty_and_paging()
    profile=read(a.profile);assert profile['complete'] and profile['trd_sha256']==m['trd_sha256']
    cap_record,=read(a.capacity/'volumes.json');cap=read(a.capacity/cap_record['metadata'])
    cap_cold=read(a.capacity/'timing.json')['disks'][0]['cold'];assert cap_cold['dirty_ram_boot_exact']
    assert cap['used_sectors']<=2544 and cap['compressed_sector_cache']['enabled']
    assert sha((a.capacity/cap_record['file']).read_bytes())==cap['trd_sha256']==cap_record['sha256']
    artifacts=[]
    def archive(path,key):
        raw=path.read_bytes();packed=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        target=a.evidence/(key if path.suffix=='.trd' else key+'.gz');target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(packed),raw_bytes=len(raw),archive_bytes=len(packed)))
    for folder in (a.after,a.capacity):
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(k in ('zx0','lzsa') for k in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1','.log'):
                archive(path,folder.name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    for path in (a.gap,a.tests,a.failed_tests,a.profile):archive(path,path.name)
    sources=('compressed_sector_cache.py','test_compressed_sector_cache.py','cell_codebook_player.py','rebuild_cell_player.py',
        'build_cell_codebook_trd.py','audit_cell_fixed_gap.py','measure_fap3_fuse.py','verify_sector_cache.py','profile_cell_delivery.py')
    result=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='dd71448',scope=__doc__,
        frames=m['frames'],frame_start=m['frame_start'],trd_sha256=m['trd_sha256'],cold=cold,
        stream_sha256=streams,video_changed=False,ay_changed=False,pixel_changes=0,
        cache_bytes=cache['bytes'],cache_events=events,fifo_bounds_guarded=True,
        full_fuse_screen_bytes=screens['compared_bytes'],used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
        cycles=dict(cached_take=tests.cycles,prefetch=tests.prefetch_cycles,
            miss_extra=27,full_idle_before=14,full_idle_after=44,eof_idle_before=14,eof_idle_after=78,
            cached_header=4718,cached_body=8991,cursor_wrap_extra=4,prefetch_excluding_read=219,
            excludes='physical-read body including producer/ROM/disk, outer caller, IRQ and contention; cached hits include copy/page bodies'),
        timing_before=summarize_fuse(read(old_work/'timing.json')),timing_after=summarize_fuse(fuse),timing_cache_trace=summarize_fuse(trace),
        profile={k:v for k,v in profile.items() if k not in ('frames','inputs')},
        largest_volume_capacity=dict(part=cap['part'],frames=cap['frames'],sectors=cap['used_sectors'],cold=cap_cold,
            complete_playback_verified=False),
        limitations=['Same-stream bounded window and fourth-volume cold capacity only; no full-set timing or actual EOF continuation.',
            'Both nominal and fallback timing still fail. This trades extra copying for earlier disk acquisition.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),cache=events,late=fuse['nominal_late_frames'],
        maximum=fuse['max_late_fields'],trace_maximum=trace['max_late_fields'],largest_volume_sectors=cap['used_sectors'])))


if __name__=='__main__':main()
