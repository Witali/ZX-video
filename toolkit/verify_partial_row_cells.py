"""Verify and archive CB46 host sizes, native cycles and complete window playback."""
import argparse
import gzip
import json
from pathlib import Path
import struct

from build_fap3_trd import sha
from convert_video import write_json
from profile_fap3 import summarize_fuse
from profile_integrated_timing import stats
from test_partial_row_cells import PartialRowTests


def read(path):return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('before','after','probe','full','capacity','profile','tests','failed-tests','evidence','output'):
        p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--service-failure',type=Path,help='Preserved initial whole-wrapper cycle comparison failure')
    a=p.parse_args();a.evidence.mkdir(parents=True,exist_ok=True);inputs=[]
    for folder in (a.before,a.after):
        r=read(folder/'volumes.json')[0];m=read(folder/r['metadata']);work=folder/'work'/Path(r['file']).stem
        assert sha((folder/r['file']).read_bytes())==m['trd_sha256']==r['sha256']
        cpu=read(work/'cpu.json');fuse=read(work/'timing.json');screens=read(work/'screens.json')
        assert cpu['complete'] and cpu['all_native_screens_exact']
        assert fuse['complete'] and fuse['ay_records_exact'] and not fuse['audio_underruns']
        assert screens['complete'] and screens['full_screens_exact']
        assert screens['trd_sha256']==fuse['trd_sha256']==m['trd_sha256']
        cold=read(folder/'timing.json')['disks'][0]['cold'];assert cold['dirty_ram_boot_exact']
        inputs.append((m,work,cpu,fuse,screens,cold))
    old,new=inputs;m,work,cpu,fuse,screens,cold=new
    assert old[0]['states_sha256']==m['states_sha256']
    assert (old[1]/'audio.ayh1').read_bytes()==(work/'audio.ayh1').read_bytes()
    assert old[0]['resident_audio']['compiled']==m['resident_audio']['compiled']
    assert cpu['retired_runtime_reads_writes_or_fetches']==0 and cpu['immutable_audio_bank_guarded']==6
    raw=(work/'codebook.raw').read_bytes();at=2056;costs=[]
    while at<len(raw):
        n=struct.unpack_from('<H',raw,at)[0];at+=2
        if n&32768:at+=3*(n&32767);continue
        packet=raw[at:at+n];at+=n;count=sum(b.bit_count() for b in packet[:72]);modes=packet[144:144+(count+3)//4]
        values=[(modes[i//4]>>((i%4)*2))&3 for i in range(count)]
        costs.append(7*values.count(1)-131*values.count(3))
    assert len(costs)==m['frames']
    measured=[]
    for i,(b,c) in enumerate(zip(old[2]['frames'],cpu['frames'],strict=True),1):
        assert b['frame']==c['frame']
        before,after=b['draw']['tstates'],c['draw']['tstates']
        kernels=[sum(v for k,v in draw['new_component_stages'].items() if k!='cb41_packet') for draw in (b['draw'],c['draw'])]
        assert kernels[1]-kernels[0]==costs[i],(i,kernels,costs[i])
        measured.append(dict(frame=b['frame'],before=before,after=after,delta=after-before,
            kernel_before=kernels[0],kernel_after=kernels[1],kernel_delta=kernels[1]-kernels[0],
            outer_service_delta=after-before-costs[i]))
    tests=PartialRowTests();tests.test_rows_modes_and_full_flag_timings()
    assert a.tests.read_text().strip().endswith('OK')
    probe=read(a.probe/'report.json');full=read(a.full/'report.json');capacity=read(a.capacity/'capacity.json')
    assert probe['complete'] and full['complete'] and capacity['complete']
    assert full['frames_sha256']==m['states_sha256'] and sum(v['end']-v['start'] for v in full['volumes'])==5066
    profile=read(a.profile);assert profile['complete'] and profile['trd_sha256']==m['trd_sha256']
    artifacts=[]
    def archive(path,key):
        data=path.read_bytes();prepacked=path.suffix=='.gz';image=path.suffix=='.trd'
        raw=gzip.decompress(data) if prepacked else data
        blob=data if prepacked or image else gzip.compress(raw,mtime=0)
        target=a.evidence/(key if prepacked or image else key+'.gz');target.write_bytes(blob)
        artifacts.append(dict(file=target.name,raw_sha256=sha(raw),archive_sha256=sha(blob),raw_bytes=len(raw),archive_bytes=len(blob)))
    for folder in (a.after,a.probe,a.full,a.capacity):
        for path in sorted(folder.rglob('*')):
            if not path.is_file() or any(k in ('zx0','lzsa') for k in path.relative_to(folder).parts):continue
            if path.suffix in ('.json','.trd','.npz','.raw','.stream','.txt','.ayh1','.gz'):
                archive(path,folder.name+'-'+path.relative_to(folder).as_posix().replace('/','-'))
    for path in (a.tests,a.failed_tests,a.profile):archive(path,path.name)
    if a.service_failure:archive(a.service_failure,a.service_failure.name)
    sources=('partial_row_cells.py','dynamic_row_dictionary.py','probe_partial_row_cells.py','measure_partial_row_four.py',
        'cell_codebook_z80.py','cell_codebook_player.py','rebuild_cell_player.py','fixed_resident_audio.py',
        'verify_cell_codebook_z80.py','test_partial_row_cells.py','verify_partial_row_cells.py')
    report=dict(complete=True,release=False,whole_movie_timing_verified=False,baseline_commit='a6a2081',scope=__doc__,
        wire='CB46',pixel_changes=0,ay_changed=False,frames=m['frames'],trd_sha256=m['trd_sha256'],cold=cold,
        full_fuse_screen_bytes=screens['compared_bytes'],used_sectors_before=old[0]['used_sectors'],used_sectors_after=m['used_sectors'],
        video_bytes_before=old[0]['video_bytes'],video_bytes_after=m['video_bytes'],
        timing_before=summarize_fuse(old[3]),timing_after=summarize_fuse(fuse),
        cycles=dict(formula='7*book_cells - 131*partial_cells',no_refill_before=dict(book=281,literal=317,front=299),
            no_refill_after=dict(book=288,literal=317,front=299,partial=186),
            excludes='outer caller, mode-byte refills, IRQ, contention, ROM/disk; same-mask full-frame difference is exact',
            cases=tests.cases,frames=measured,before_draw=stats([f['before'] for f in measured]),
            after_draw=stats([f['after'] for f in measured]),slower_frames=sum(f['delta']>0 for f in measured)),
        bounded_probe=probe,full_host=full,capacity=capacity,profile={k:v for k,v in profile.items() if k not in ('frames','inputs')},
        artifacts=artifacts,source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,report)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),capacity=capacity['total_used_sectors'],
        fits=capacity['all_volumes_fit'],draw_mean_before=report['cycles']['before_draw']['mean'],
        draw_mean_after=report['cycles']['after_draw']['mean'],slower_frames=report['cycles']['slower_frames'])))


if __name__=='__main__':main()
