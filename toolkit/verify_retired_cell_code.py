"""Archive exact cached-stream reuse, retired-RAM guards and full Fuse checks."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
from profile_integrated_timing import stats


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('before','after','fixture','capacity','audio-probe','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    runs=[];artifacts=[]
    def archive(path,key):
        raw=path.read_bytes();blob=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        target=a.evidence/(key if path.suffix=='.trd' else key+'.gz');target.write_bytes(blob)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(blob),
            raw_bytes=len(raw),archive_bytes=len(blob)))
    for folder in (a.after,a.fixture):
        records=read(folder/'volumes.json');cold=read(folder/'timing.json')['disks']
        for record,boot in zip(records,cold,strict=True):
            m=read(folder/record['metadata']);work=folder/'work'/Path(record['file']).stem
            cpu=read(work/'cpu.json');timing=read(work/'timing.json');screens=read(work/'screens.json')
            assert sha((folder/record['file']).read_bytes())==m['trd_sha256']==timing['trd_sha256']==screens['trd_sha256']
            assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['retired_ranges_guarded']
            assert cpu['retired_runtime_reads_writes_or_fetches']==0
            assert boot['cold']['dirty_ram_boot_exact']
            assert timing['complete'] and timing['ay_records_exact'] and not timing['audio_underruns']
            assert screens['complete'] and screens['full_screens_exact']
            runs.append(dict(build=folder.name,part=m['part'],frames=m['frames'],used_sectors=m['used_sectors'],
                guarded_ranges=cpu['retired_ranges_guarded'],runtime_accesses_to_retired_memory=0,
                full_fuse_screen_bytes=screens['compared_bytes'],cold=boot['cold'],timing=summarize_fuse(timing)))
    previous=read(a.before/'volumes.json')[0];current=read(a.after/'volumes.json')[0]
    old=read(a.before/previous['metadata']);new=read(a.after/current['metadata'])
    old_work=a.before/'work'/Path(previous['file']).stem;new_work=a.after/'work'/Path(current['file']).stem
    for key in ('native','packet_listing','clock_listing'):
        assert old['cell_codebook'][key]==new['cell_codebook'][key],key
    streams={}
    for name in ('codebook.raw','codebook.stream','audio.ayh1'):
        raw=(old_work/name).read_bytes();assert raw==(new_work/name).read_bytes();streams[name]=sha(raw)
    assert old['states_sha256']==new['states_sha256']
    before_cpu=read(old_work/'cpu.json');after_cpu=read(new_work/'cpu.json')
    assert len(before_cpu['frames'])==len(after_cpu['frames'])==new['frames']-1
    packet_delta=[]
    for b,c in zip(before_cpu['frames'],after_cpu['frames'],strict=True):
        assert b['frame']==c['frame'] and b['draw']['tstates']==c['draw']['tstates']
        if b['next_packet']:packet_delta.append(c['next_packet']['tstates']-b['next_packet']['tstates'])
    continuation=read(a.fixture/'continuation/continuation.json')
    assert continuation['complete'] and len(continuation['volumes'])==2
    for v in continuation['volumes']:
        assert v['complete'] and v['ay_records_exact']
        assert not any(v[k] for k in ('nominal_late_frames','audio_underruns','ay_gaps','ay_duplicates'))
    assert continuation['volumes'][1]['from_actual_previous_eof']
    failure=read(a.capacity/'conversion.json');assert not failure['complete']
    probe=read(a.audio_probe);assert probe['complete'] and all(v['records_exact'] for v in probe['parts'])
    for folder in (a.after,a.fixture,a.capacity):
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(k in ('zx0','lzsa','continuation-input') for k in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1','.szx','.ram','.log'):
                archive(path,folder.name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    archive(a.audio_probe,'shared-audio-probe.json')
    sources=('cell_codebook_player.py','build_cell_codebook_trd.py','rebuild_cell_player.py',
        'verify_retired_cell_code.py','probe_shared_resident_audio.py','cell_codebook_z80.py',
        'measure_fap3_fuse.py','capture_cell_codebook_full.py','verify_cell_codebook_continuation.py','warm_resume_snapshot.py')
    report=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='e747b02',scope=__doc__,
        runs=runs,stream_sha256=streams,states_sha256=new['states_sha256'],
        unchanged_renderer_and_packet_instruction_listings=True,measured_draw_delta_tstates=0,
        next_packet_delta_tstates=stats(packet_delta),next_packet_note='Track/side crossings move with the shorter startup',
        used_sectors_before=old['used_sectors'],used_sectors_after=new['used_sectors'],
        capacity_failure=failure,fixture_continuation=continuation,shared_audio_host_probe=probe,
        artifacts=artifacts,source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in sources})
    write_json(a.output,report)
    print(json.dumps(dict(complete=True,runs=len(runs),guarded_frames=sum(r['frames'] for r in runs),
        used_before=old['used_sectors'],used_after=new['used_sectors'],artifacts=len(artifacts))))


if __name__=='__main__':main()
