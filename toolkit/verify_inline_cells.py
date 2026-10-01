"""Verify same-stream unrolled CB46 delivery and archive the complete window."""
import argparse
import gzip
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
from profile_integrated_timing import stats
import cell_codebook_z80


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('before','after','gap','tests','profile','capacity','evidence','output'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True);runs=[]
    for folder in (a.before,a.after):
        record,=read(folder/'volumes.json');m=read(folder/record['metadata']);work=folder/'work'/Path(record['file']).stem
        assert sha((folder/record['file']).read_bytes())==m['trd_sha256']==record['sha256']
        cpu,fuse,screens=[read(work/(name+'.json')) for name in ('cpu','timing','screens')]
        assert cpu['complete'] and cpu['all_native_screens_exact']
        assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['audio_underruns']
        assert not fuse['ay_record_field_gaps'] and not fuse['ay_record_field_duplicates']
        assert screens['complete'] and screens['full_screens_exact']
        assert screens['trd_sha256']==fuse['trd_sha256']==m['trd_sha256']
        assert fuse['integrated_bootstrap_metadata_sha256']==sha((folder/record['metadata']).read_bytes())
        cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
        runs.append((m,work,cpu,fuse,screens,cold))
    old,new=runs;m,work,cpu,fuse,screens,cold=new
    assert m['states_sha256']==old[0]['states_sha256']
    streams={}
    for name in ('codebook.raw','codebook.stream','audio.ayh1'):
        data=(work/name).read_bytes();assert data==(old[1]/name).read_bytes();streams[name]=sha(data)
    assert m['resident_audio']['compiled']==old[0]['resident_audio']['compiled']
    for run,enabled in ((old,False),(new,True)):
        _,labels,native=cell_codebook_z80.build(front_reuse=True,fast_masks=True,partial_rows=True,inline_cells=enabled)
        assert labels==run[0]['cell_codebook']['native_labels'] and native==run[0]['cell_codebook']['native']
    gap=read(a.gap);assert gap['complete'] and gap['extra_guard']==[0x8e80,0x9000]
    assert not gap['retired_runtime_reads_writes_or_fetches']
    assert cpu['immutable_audio_bank_guarded']==6 and not cpu['retired_runtime_reads_writes_or_fetches']
    counts=[];data=(work/'codebook.raw').read_bytes();at=2056
    while at<len(data):
        size=struct.unpack_from('<H',data,at)[0];at+=2
        if size&32768:at+=3*(size&32767);continue
        counts.append(sum(b.bit_count() for b in data[at:at+72]));at+=size
    assert len(counts)==m['frames'];frames=[]
    for i,(before,after) in enumerate(zip(old[2]['frames'],cpu['frames'],strict=True),1):
        assert before['frame']==after['frame']
        kernels=[sum(v for k,v in r['draw']['new_component_stages'].items() if k!='cb41_packet') for r in (before,after)]
        assert kernels[1]-kernels[0]==-17*counts[i],(i,kernels,counts[i])
        frames.append(dict(frame=after['frame'],changed_cells=counts[i],kernel_before=kernels[0],kernel_after=kernels[1],
            delta=kernels[1]-kernels[0],draw_before=before['draw']['tstates'],draw_after=after['draw']['tstates']))
    profile=read(a.profile);assert profile['complete'] and profile['trd_sha256']==m['trd_sha256']
    assert a.tests.read_text().strip().endswith('OK')
    # Largest startup/full volume: actual rebuild, not an extrapolated size.
    cap_record,=read(a.capacity/'volumes.json');cap=read(a.capacity/cap_record['metadata'])
    cap_cold=read(a.capacity/'timing.json')['disks'][0]['cold'];assert cap_cold['dirty_ram_boot_exact']
    assert cap['used_sectors']<=2544 and cap['cell_codebook']['native']['inline_cells']
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
    for path in (a.gap,a.tests,a.profile):archive(path,path.name)
    sources=('cell_codebook_z80.py','cell_codebook_player.py','rebuild_cell_player.py','verify_cell_codebook_z80.py',
        'test_inline_cells.py','verify_inline_cells.py','audit_cell_fixed_gap.py','profile_cell_delivery.py')
    result=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='d4e878c',scope=__doc__,
        frames=m['frames'],frame_start=m['frame_start'],trd_sha256=m['trd_sha256'],cold=cold,
        stream_sha256=streams,pixel_changes=0,ay_changed=False,used_sectors_before=old[0]['used_sectors'],used_sectors_after=m['used_sectors'],
        full_fuse_screen_bytes=screens['compared_bytes'],component_cases=28,
        cycles=dict(formula='-17*changed_bitmap_cells',changed_dispatch_before=27,changed_dispatch_after=10,
            unchanged_dispatch_before=10,unchanged_dispatch_after=10,
            no_refill_including_dispatch_before=dict(book=305,literal=334,front=316,partial=203),
            no_refill_including_dispatch_after=dict(book=288,literal=317,front=299,partial=186),
            excludes='unchanged RRCA/INC E and mode-byte refills, IRQ, ULA, ROM/disk, outer frame service',
            code_bytes_before=old[0]['cell_codebook']['native']['code_bytes'],code_bytes_after=m['cell_codebook']['native']['code_bytes'],
            kernel_before=stats([r['kernel_before'] for r in frames]),kernel_after=stats([r['kernel_after'] for r in frames]),frames=frames),
        timing_before=summarize_fuse(old[3]),timing_after=summarize_fuse(fuse),
        largest_volume_capacity=dict(part=cap['part'],frames=cap['frames'],sectors=cap['used_sectors'],cold=cap_cold,
            complete_playback_verified=False),profile={k:v for k,v in profile.items() if k not in ('frames','inputs')},
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),late=result['timing_after']['missed_nominal_frames'],
        sectors=m['used_sectors'],largest_volume_sectors=cap['used_sectors'])))


if __name__=='__main__':main()
