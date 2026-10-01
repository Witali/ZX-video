"""Verify the fixed AY overflow allocation and archive a complete selected volume.

This proves allocation/content and records timing failures. It cannot establish
a four-disk release or predecessor-EOF continuation from one volume.
"""
import argparse
import gzip
import json
from pathlib import Path

from benchmark_resident_audio_z80 import Harness
from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
import fixed_resident_audio


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('build','before','native','gap','tests','profile','evidence','output'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True)
    record,=read(a.build/'volumes.json');m=read(a.build/record['metadata']);old=read(a.before)
    work=a.build/'work'/Path(record['file']).stem;image=(a.build/record['file']).read_bytes()
    assert sha(image)==m['trd_sha256']==record['sha256']
    assert old['states_sha256']==m['states_sha256']
    for key in ('frame_start','frame_end_exclusive','blocks','video_bytes','video_sectors'):
        assert old[key]==m[key],key
    for key in ('native','packet_listing','clock_listing','raw_sha256'):
        assert old['cell_codebook'][key]==m['cell_codebook'][key],key
    assert old['resident_audio']['coded_audio_sha256']==m['resident_audio']['coded_audio_sha256']
    audio=(work/'audio.ayh1').read_bytes();assert sha(audio)==m['resident_audio']['coded_audio_sha256']
    c=m['resident_audio']['compiled']
    assert fixed_resident_audio.build(audio,m['audio_labels'],core_limit=m['decoder_labels']['start'],
        batch=c['batch'],single_bank=6,fixed_tail=True)==c
    assert c['banks']==[6] and c['fixed_payload_bytes']>0 and not c['bank6_reserved_bytes']
    assert m['resident_audio']['video_slot_banks']==[0,1,3,4]
    gap=read(a.gap);assert gap['complete'] and gap['extra_guard']==[0xb700,0xba00]
    assert not gap['retired_runtime_reads_writes_or_fetches']
    native=read(a.native);assert native['complete'];n,=native['parts']
    assert n['input_sha256']==sha(audio)
    for key in ('records','initial','records_sha256','consumer_tstates'):assert n['before'][key]==n['after'][key]
    assert n['after']['records']==m['frames']*m['frame_fields']
    assert n['before']['all_records_and_ay_exact'] and n['after']['all_records_and_ay_exact']
    # The earlier benchmark predates a metadata wording correction. Verify all
    # executable bytes/listings against the current compiler without replaying it.
    for key,options in (('before',{}),('after',dict(single_bank=6,fixed_tail=True))):
        current=Harness(audio,paging=True,batch=c['batch'],fixed=True,**options).build
        expected=n[key]['compiled']
        assert {k:v for k,v in current.items() if k!='timing_scope'}=={k:v for k,v in expected.items() if k!='timing_scope'}
    assert n['fill_delta_tstates']==-6*len(n['after']['refills'])-177-27
    assert n['after']['init_tstates']-n['before']['init_tstates']==-20
    cpu=read(work/'cpu.json');fuse=read(work/'timing.json');screens=read(work/'screens.json')
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['frames_checked']==m['frames']
    assert cpu['immutable_audio_bank_guarded']==6
    assert cpu['immutable_fixed_audio_payload_guarded']==c['fixed_payload_range']
    assert not cpu['retired_runtime_reads_writes_or_fetches']
    assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['audio_underruns']
    assert not fuse['ay_record_field_gaps'] and not fuse['ay_record_field_duplicates']
    assert screens['complete'] and screens['full_screens_exact']
    assert screens['trd_sha256']==cpu['trd_sha256']==fuse['trd_sha256']==m['trd_sha256']
    assert cpu['metadata_sha256']==fuse['integrated_bootstrap_metadata_sha256']==sha((a.build/record['metadata']).read_bytes())
    capacity=read(a.build/'capacity.json');assert capacity['complete'] and not capacity['whole_partition']
    volume,=capacity['volumes'];cold=volume['cold'];assert cold['dirty_ram_boot_exact']
    profile=read(a.profile);assert profile['complete'] and profile['trd_sha256']==m['trd_sha256']
    assert a.tests.read_text().strip().endswith('OK')
    artifacts=[]
    def archive(path,key):
        raw=path.read_bytes();packed=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        target=a.evidence/(key if path.suffix=='.trd' else key+'.gz');target.write_bytes(packed)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(packed),
            raw_bytes=len(raw),archive_bytes=len(packed)))
    for path in sorted(a.build.rglob('*')):
        if not path.is_file() or any(k in ('zx0','lzsa') for k in path.relative_to(a.build).parts):continue
        if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1','.log'):
            archive(path,a.build.name+'-'+path.relative_to(a.build).as_posix().replace('/','-'))
    for path in (a.before,a.native,a.gap,a.tests,a.profile):archive(path,path.parent.name+'-'+path.name)
    sources=('resident_audio_z80.py','fixed_resident_audio.py','four_video_slots.py',
        'benchmark_resident_audio_z80.py','benchmark_fixed_resident_audio.py','test_fixed_resident_audio.py',
        'audit_cell_fixed_gap.py','build_cell_codebook_trd.py','verify_cached_cell_player.py',
        'measure_shared_audio_capacity.py','rebuild_cell_player.py','verify_fixed_audio_tail.py','profile_cell_delivery.py')
    result=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='13879a8',scope=__doc__,
        frames=m['frames'],frame_start=m['frame_start'],trd_sha256=m['trd_sha256'],cold=cold,
        video_bytes=m['video_bytes'],video_stream_changed=False,ay_changed=False,pixel_changes=0,
        used_sectors_before=old['used_sectors'],used_sectors_after=m['used_sectors'],
        fixed_payload_range=c['fixed_payload_range'],fixed_payload_bytes=c['fixed_payload_bytes'],fixed_bytes=c['fixed_bytes'],
        video_banks=m['resident_audio']['video_slot_banks'],gap_guard_frames=gap['frames_checked'],
        full_native_screens_exact=True,full_fuse_screens_exact=True,compared_screen_bytes=screens['compared_bytes'],
        native_audio=dict(ticks=n['after']['records'],init_before=n['before']['init_tstates'],init_after=n['after']['init_tstates'],
            fill_before=n['before']['fill_tstates'],fill_after=n['after']['fill_tstates'],fill_delta=n['fill_delta_tstates'],
            fifo_and_ay_exact=True,consumer_tstates=n['after']['consumer_tstates']),
        byte_cycles=dict(ordinary_before=65,ordinary_after=65,first_wrap_before=251,first_wrap_after=74,
            final_byte_before=92,final_byte_after=65,bridge_before=442,bridge_after=436,
            formula='-6*refills -177*first_wraps -27*final_wraps',
            excludes='outer service, IRQ, contention, ROM and physical disk latency'),
        timing=summarize_fuse(fuse),profile={k:v for k,v in profile.items() if k not in ('frames','inputs')},
        limitations=['Only the selected fourth volume is tested here; not full-set timing or predecessor-EOF continuation.',
            'Both nominal and one-field fallback timing still fail. Root release disks remain unchanged.'],
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),frames=m['frames'],
        late=result['timing']['missed_nominal_frames'],used_sectors=m['used_sectors'])))


if __name__=='__main__':main()
