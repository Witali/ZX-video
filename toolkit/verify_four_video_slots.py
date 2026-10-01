"""Guard a complete four-slot replay and archive exact full Fuse comparisons."""
import argparse
import gzip
import json
from pathlib import Path
import numpy as np

from build_cell_codebook_trd import verify
from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
import fixed_resident_audio


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('before','window','profile','tests','evidence','output'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    record=read(a.window/'volumes.json')[0];m=read(a.window/record['metadata'])
    work=a.window/'work'/Path(record['file']).stem
    old_record=read(a.before/'volumes.json')[0];old=read(a.before/old_record['metadata'])
    old_work=a.before/'work'/Path(old_record['file']).stem
    image=(a.window/record['file']).read_bytes();assert sha(image)==m['trd_sha256']==record['sha256']
    streams={}
    for name in ('codebook.raw','codebook.stream','audio.ayh1'):
        raw=(work/name).read_bytes();assert raw==(old_work/name).read_bytes();streams[name]=sha(raw)
    assert old['states_sha256']==m['states_sha256']
    for key in ('native','packet_listing','clock_listing'):
        assert old['cell_codebook'][key]==m['cell_codebook'][key],key
    compiled=m['resident_audio']['compiled']
    assert fixed_resident_audio.build((work/'audio.ayh1').read_bytes(),m['audio_labels'],
        core_limit=m['decoder_labels']['start'],batch=compiled['batch'],single_bank=6)==compiled
    assert m['resident_audio']['video_slot_banks']==[0,1,3,4] and compiled['banks']==[6]
    assert len(m['four_video_slots']['patches'])==4
    with np.load(a.window/record['states'],allow_pickle=False) as saved:states=saved['states']
    assert sha(states.tobytes())==m['states_sha256']
    # Rerun only when the original build predates the new immutable-bank guard.
    original=read(work/'cpu.json');guard_file=work/'cpu-bank-guard.json'
    if original.get('immutable_audio_bank_guarded')==6:cpu=original
    elif guard_file.exists():cpu=read(guard_file)
    else:
        cpu=verify(image,m,states);cpu['trd_sha256']=sha(image);write_json(guard_file,cpu)
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['immutable_audio_bank_guarded']==6
    assert cpu['retired_runtime_reads_writes_or_fetches']==0
    fuse=read(work/'timing.json');screens=read(work/'screens.json')
    cold=read(a.window/'timing.json')['disks'][0]['cold']
    assert cold['dirty_ram_boot_exact']
    assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['audio_underruns']
    assert screens['complete'] and screens['full_screens_exact']
    assert screens['trd_sha256']==fuse['trd_sha256']==m['trd_sha256']
    assert fuse['integrated_bootstrap_metadata_sha256']==sha((a.window/record['metadata']).read_bytes())
    profile=read(a.profile);assert profile['complete'] and profile['trd_sha256']==m['trd_sha256']
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
    for path in (a.tests,a.profile):archive(path,path.name)
    sources=('fixed_resident_audio.py','resident_audio_z80.py','four_video_slots.py',
        'benchmark_resident_audio_z80.py','test_fixed_resident_audio.py','cell_codebook_player.py',
        'rebuild_cell_player.py','build_cell_codebook_trd.py','verify_four_video_slots.py','profile_cell_delivery.py')
    result=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='5751e6e',
        scope=__doc__,frames=m['frames'],frame_start=m['frame_start'],trd_sha256=m['trd_sha256'],
        compared_screen_bytes=screens['compared_bytes'],stream_sha256=streams,
        used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
        memory=m['four_video_slots'],cold=cold,immutable_audio_bank_guarded=6,
        timing_before=summarize_fuse(read(old_work/'timing.json')),timing_after=summarize_fuse(fuse),
        profile={k:v for k,v in profile.items() if k not in ('frames','inputs')},
        limitations=['Complete difficult-window test only; not full movie or actual EOF continuation.',
            'Fourth slot requires one-bank AY; selected full part 4 still needs another audio allocation.',
            'Nominal and one-field fallback timing both still fail.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),frames=m['frames'],
        late=result['timing_after']['missed_nominal_frames'],used_sectors=m['used_sectors'])))


if __name__=='__main__':main()
