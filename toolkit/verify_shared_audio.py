"""Archive fixed AY correctness/capacity evidence without claiming a release."""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
import fixed_resident_audio


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('before','window','capacity','benchmark','gap','tests','evidence','output'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--failed-tests',type=Path)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    record=read(a.window/'volumes.json')[0];m=read(a.window/record['metadata'])
    work=a.window/'work'/Path(record['file']).stem
    old_record=read(a.before/'volumes.json')[0];old=read(a.before/old_record['metadata'])
    old_work=a.before/'work'/Path(old_record['file']).stem
    assert sha((a.window/record['file']).read_bytes())==m['trd_sha256']==record['sha256']
    streams={}
    for name in ('codebook.raw','codebook.stream','audio.ayh1'):
        raw=(work/name).read_bytes();assert raw==(old_work/name).read_bytes();streams[name]=sha(raw)
    assert old['states_sha256']==m['states_sha256']
    for key in ('native','packet_listing','clock_listing'):
        assert old['cell_codebook'][key]==m['cell_codebook'][key],key
    compiled=m['resident_audio']['compiled']
    assert fixed_resident_audio.build((work/'audio.ayh1').read_bytes(),m['audio_labels'],
        core_limit=m['decoder_labels']['start'],batch=compiled['batch'])==compiled
    cpu=read(work/'cpu.json');fuse=read(work/'timing.json');screens=read(work/'screens.json')
    cold=read(a.window/'timing.json')['disks'][0]['cold']
    assert cpu['complete'] and cpu['all_native_screens_exact']
    assert cpu['retired_runtime_reads_writes_or_fetches']==0 and cold['dirty_ram_boot_exact']
    assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['audio_underruns']
    assert screens['complete'] and screens['full_screens_exact']
    assert screens['trd_sha256']==fuse['trd_sha256']==m['trd_sha256']
    gap=read(a.gap);assert gap['complete'] and gap['retired_runtime_reads_writes_or_fetches']==0
    assert gap['trd_sha256']==old['trd_sha256']
    capacity=read(a.capacity/'capacity.json');assert capacity['complete'] and len(capacity['volumes'])==4
    benchmark=read(a.benchmark);assert benchmark['complete'] and len(benchmark['parts'])==4
    for c,b in zip(capacity['volumes'],benchmark['parts'],strict=True):
        assert c['source_audio_sha256']==b['input_sha256']
        assert b['after']['all_records_and_ay_exact'] and b['before']['all_records_and_ay_exact']
        for key in ('records','initial','records_sha256','consumer_tstates'):
            assert b['after'][key]==b['before'][key]
        assert b['after']['records']==5*(c['end']-c['start'])
        if c['fits']:assert c['cold']['dirty_ram_boot_exact']
    assert a.tests.read_text().strip().endswith('OK')
    artifacts=[]
    def archive(path,key):
        raw=path.read_bytes();blob=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        target=a.evidence/(key if path.suffix=='.trd' else key+'.gz');target.write_bytes(blob)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(blob),
            raw_bytes=len(raw),archive_bytes=len(blob)))
    for path in sorted(a.window.rglob('*')):
        if not path.is_file() or any(k in ('zx0','lzsa') for k in path.relative_to(a.window).parts):continue
        if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1','.szx','.ram','.log'):
            archive(path,a.window.name+'-'+path.relative_to(a.window).as_posix().replace('/','-'))
    for path in sorted(a.capacity.glob('*.json')):archive(path,'capacity-'+path.name)
    for path in (a.benchmark,a.gap,a.tests,a.failed_tests):
        if path:archive(path,path.name)
    sources=('fixed_resident_audio.py','resident_audio_z80.py','resident_audio_player.py',
        'benchmark_resident_audio_z80.py','benchmark_fixed_resident_audio.py','test_fixed_resident_audio.py',
        'cell_codebook_player.py','rebuild_cell_player.py','measure_shared_audio_capacity.py',
        'audit_cell_fixed_gap.py','validate_fast_sparse.py','verify_shared_audio.py')
    result=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='9893f79',
        scope=__doc__,window=dict(start=m['frame_start'],frames=m['frames'],
            compared_bytes=screens['compared_bytes'],stream_sha256=streams,
            used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
            trd_sha256=m['trd_sha256'],cold=cold,timing=summarize_fuse(fuse)),
        additional_fixed_guard=dict(start=0xb100,end=0xb700,frames=gap['frames_checked'],accesses=0),
        capacity=capacity,all_native_ay_ticks=sum(b['after']['records'] for b in benchmark['parts']),
        native_ay_fill_before=sum(b['before']['fill_tstates'] for b in benchmark['parts']),
        native_ay_fill_after=sum(b['after']['fill_tstates'] for b in benchmark['parts']),
        limitations=['No full movie timing or actual EOF continuation for this layout.',
            'Bank-6 overflow verified in CPU tests, not yet in integrated Fuse playback.',
            'Video queue still has three slots; bank 6 is not yet reused.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),sectors=capacity['total_used_sectors'],
        all_volumes_fit=capacity['all_volumes_fit'],late=result['window']['timing']['missed_nominal_frames'])))


if __name__=='__main__':main()
