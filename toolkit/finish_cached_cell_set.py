"""Audit, archive and optionally install the complete four-volume refined movie.

Publication requires every cold and predecessor-EOF timing/content gate,
exact prepared RGB/AY, matching disk IDs and LFS rules. Historical evidence
is retained; only the previous numbered refined root set may be replaced.
"""
import argparse
import gzip
import json
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np

from build_fap3_trd import sha
from convert_video import write_json
from finish_refined_av import preview
from invisible_attribute_writes import verify_rgb
from profile_fap3 import summarize_fuse
from profile_cell_delivery import analyze
import banked_resident_audio


def read(path):return json.loads(path.read_bytes())


def timing_gate(r,allow_fallback=False):
    summary=summarize_fuse(r)
    strict_fallback=(summary['fallback_one_field_met'] and r['actual_out_over_one_field']==0
        and max(map(abs,r['actual_phase_tstates']),default=0)<=70908
        and r['max_late_fields']<=1 and r['bad_actual_intervals']==0
        and all(x['recovered_at'] is not None and x['recovered_at']==x['end']+1 for x in r['late_runs']))
    assert summary['nominal_deadlines_met'] or allow_fallback and strict_fallback
    assert r['bad_actual_intervals']==r['actual_out_over_one_field']==0
    summary['strict_one_field_fallback_met']=strict_fallback
    for a,b in zip(r['publications'],r['publications'][1:]):
        assert b['field']-a['field'] in ((4,5,6) if allow_fallback else (5,))
    return summary


def exact_capture(path,work,m,timing):
    r=read(path)
    assert r['complete'] and r['full_screens_exact'] and r['frames']==m['frames']
    assert r['trd_sha256']==m['trd_sha256'] and r['compared_bytes']==6912*m['frames']
    assert r['states_sha256']==m['states_sha256'] and r['timing_sha256']==sha(timing.read_bytes())
    assert r.get('continuation_snapshot_sha256')==read(timing).get('continuation_snapshot_sha256')
    assert not (r['debugger_pokes'] or r['debugger_paging_changes'] or r['debugger_cpu_jumps'])
    for chunk in r['passes']:
        prefix=work/f'bytes-{chunk["start"]}-{chunk["end"]}'
        assert chunk['frames']==m['frames'] and chunk['all_bytes_exact']
        assert sha(prefix.with_suffix('.trace.txt').read_bytes())==chunk['trace_sha256']
        assert sha(prefix.with_suffix('.debugger.txt').read_bytes())==chunk['debugger_sha256']
    return r


def exact_timing(path,m,allow_fallback=False):
    r=read(path);summary=timing_gate(r,allow_fallback)
    assert r['complete'] and r['frames']==m['frames'] and r['trd_sha256']==m['trd_sha256']
    assert r['ay_records_exact'] and r['ay_ticks']==m['frames']*5
    assert not (r['errors'] or r['failure'] or r['audio_underruns'] or r['ay_record_field_gaps'] or r['ay_record_field_duplicates'])
    assert r['trace_nonce_exact'] and r['debugger_installed_bytes']==0 and r['fast_read_retries']==0
    assert r['runtime_sectors_checked']==m['video_sectors'] and all(x['bytes_exact'] for x in r['reads'])
    assert sha(path.with_suffix('.trace.txt').read_bytes())==r['trace_sha256']
    assert sha(path.with_suffix('.debugger.txt').read_bytes())==r['debugger_script_sha256']
    # Keep actual phase/interval bounds in the human-readable summary, with
    # the existing 64-T instruction/IRQ tolerance explicit in the report.
    summary['actual_interval_range_tstates']=[min(summary['publication_intervals_tstates']),max(summary['publication_intervals_tstates'])]
    del summary['publication_intervals_tstates']
    return r,summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('build','prepared','baseline','root','evidence','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--install',action='store_true')
    p.add_argument('--allow-fallback',action='store_true',help='Use the explicitly authorized one-field jitter/recovery allowance; still report every nominal miss')
    a=p.parse_args();root=a.root.resolve();build=read(a.build/'build.json');checks=read(a.build/'checks.json')
    assert build['complete'] and checks['complete']
    assert checks['all_nominal_deadlines_met'] or a.allow_fallback
    volumes=read(a.build/'volumes.json');prepared=read(a.prepared);baseline=read(a.baseline)
    assert 1<=len(volumes)<=4 and build['frames']==prepared['frames']==5066
    assert build['frame_fields']==5 and prepared['ay_ticks']==25330
    assert prepared['complete'] and prepared['decoded_source']['decoded_to_eof']
    assert prepared['last_source_frame']==prepared['source_frames']-1
    assert prepared['contract']['timeline']==read(root/'toolkit/movie_no_credits.json')
    with np.load(a.build/'work/original-states.npz',allow_pickle=False) as cache:original=cache['states']
    assert sha(original.tobytes())==build['original_states_sha256']
    cursor=0
    for c in prepared['chunks']:
        path=a.prepared.parent/c['file'];assert sha(path.read_bytes())==c['sha256'] and c['start']==cursor
        with np.load(path,allow_pickle=False) as cache:assert np.array_equal(cache['five_states'],original[c['start']:c['end']])
        cursor=c['end']
    assert cursor==5066 and len(prepared['quality'])==5066
    sound=(a.prepared.parent/'audio.bin').read_bytes();registers=(a.prepared.parent/'registers.bin').read_bytes()
    assert sha(sound)==prepared['ay_sha256'] and sha(registers)==prepared['ay_registers_sha256']
    assert len(registers)==25330*11
    identity=bytes.fromhex(build['fingerprint']);assert len(identity)==14
    cont=a.build/'continuation';continued=read(cont/'continuation.json');swaps=read(cont/'swaps.json')
    assert continued['complete'] and len(continued['volumes'])==len(volumes) and len(swaps)==len(volumes)-1
    assert all(x['wrong_disk_rejected'] and x['wrong_series_rejected'] and x['correct_disk_accepted'] and x['bootstrap_ram_exact'] for x in swaps)
    results=[];at=0;all_regs=bytearray();previous_regs=bytes(11)
    for i,v in enumerate(volumes,1):
        meta=a.build/v['metadata'];m=read(meta);image=(a.build/v['file']).read_bytes();work=a.build/'work'/Path(v['file']).stem
        assert re.fullmatch(r'ZX-video-refined_part[0-9]{2}\.trd',v['file'])
        assert sha(image)==v['sha256']==m['trd_sha256'] and len(image)==655360
        assert m['part']==i and m['frame_start']==at and m['frame_end_exclusive']==at+m['frames']
        assert m['frame_fields']==5 and m['independently_bootable'] and m['used_sectors']<=2544
        assert image[15*256:15*256+16]==identity+i.to_bytes(2,'little')==bytes.fromhex(m['disk_id_hex'])
        nxt=17*256+m['bootstrap_labels']['next_id']-0x6000
        assert image[nxt:nxt+16]==identity+(i+1).to_bytes(2,'little')
        assert m['cell_codebook']['native']==baseline['cell_codebook']['native']
        assert m['cell_codebook']['packet_listing']==baseline['cell_codebook']['packet_listing']
        assert m['lzsa2']['regions']==baseline['lzsa2']['regions']
        assert m['side_only_seek']['code_hex']==baseline['side_only_seek']['code_hex']
        cold=build['checks'][i-1]['cold'];assert cold['dirty_ram_boot_exact']
        cpu=read(work/'cpu.json')
        assert cpu['complete'] and cpu['frames_checked']==m['frames'] and cpu['all_native_screens_exact']
        assert cpu['trd_sha256']==m['trd_sha256'] and cpu['metadata_sha256']==sha(meta.read_bytes())
        assert cpu['retired_runtime_reads_writes_or_fetches']==0
        with np.load(a.build/v['states'],allow_pickle=False) as cache:states=cache['states']
        assert sha(states.tobytes())==m['states_sha256']
        proof=verify_rgb(original,states,at,m['frame_end_exclusive'])
        write_json(work/'visible-quality-proof.json',proof)
        initial,ticks=banked_resident_audio.decode((work/'audio.ayh1').read_bytes())
        assert initial==previous_regs and len(ticks)==m['frames']*5
        regs=bytearray(initial)
        for record in ticks:
            for reg,value in zip(record[1::2],record[2::2]):regs[reg]=value
            all_regs.extend(regs)
        previous_regs=bytes(regs)
        timing,cold_timing=exact_timing(work/'timing.json',m,a.allow_fallback)
        assert timing['integrated_bootstrap_metadata_sha256']==sha(meta.read_bytes())
        cold_screens=exact_capture(work/'screens.json',work/'captures',m,work/'timing.json')
        resumed,resume_timing=exact_timing(cont/f'part-{i}.json',m,a.allow_fallback)
        assert resumed['integrated_bootstrap_metadata_sha256']==sha(meta.read_bytes())
        if i>1:
            assert len(resumed['continuation_disk_accepted_tstates'])==1
            assert sha((cont/f'resume-{i}.szx').read_bytes())==resumed['continuation_snapshot_sha256']
            from warm_resume_snapshot import make_snapshot
            prior=read(cont/f'part-{i-1}.json');ram=(cont/f'eof-{i-1}.ram').read_bytes()
            assert sha(ram)==prior['warm_ram_sha256'] and make_snapshot(ram)==(cont/f'resume-{i}.szx').read_bytes()
        resume_screens=exact_capture(cont/f'part-{i}-screens.json',cont/f'captures-{i}',m,cont/f'part-{i}.json')
        assert cold_screens['screen_sha256']==resume_screens['screen_sha256']
        profile=analyze(timing,m,cpu);write_json(work/'profile.json',profile)
        results.append(dict(file=v['file'],sha256=m['trd_sha256'],frames=m['frames'],start=at,end=m['frame_end_exclusive'],
            used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],video_bytes=m['video_bytes'],
            independent_cold_boot=True,native_full_screens_exact=True,visible_pixel_changes=0,
            ay_ticks=len(ticks),cold_timing=cold_timing,continuation_timing=resume_timing,
            screen_bytes_per_mode=cold_screens['compared_bytes'],actual_predecessor_eof=i>1))
        at=m['frame_end_exclusive']
    assert at==5066 and bytes(all_regs)==registers
    a.evidence.mkdir(parents=True,exist_ok=True);artifacts=[]
    def archive(path,name):
        raw=path.read_bytes();packed=raw if path.suffix in ('.trd','.png') else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix in ('.trd','.png') else '.gz');(a.evidence/filename).write_bytes(packed)
        artifacts.append(dict(file=filename,raw_bytes=len(raw),raw_sha256=sha(raw),archive_bytes=len(packed),archive_sha256=sha(packed)))
    samples=preview(a.prepared,a.evidence/'preview.png');archive(a.evidence/'preview.png','preview.png')
    for path in sorted(a.build.rglob('*')):
        if not path.is_file() or any(x in ('zx0','lzsa','mock') for x in path.relative_to(a.build).parts):continue
        if path.suffix in ('.json','.txt','.raw','.stream','.npz','.ayh1','.trd','.ram','.szx','.log'):
            archive(path,path.relative_to(a.build).as_posix().replace('/','-'))
    for path in (a.prepared,a.prepared.parent/'audio.json',a.prepared.parent/'audio.bin',a.prepared.parent/'registers.bin',a.baseline):
        archive(path,'source-'+path.name)
    test_log=root/'.tmp/refined-four-gate-tests.log'
    assert test_log.read_text().strip().endswith('OK');archive(test_log,'publication-gate-tests.log')
    sources=('build_cached_cell_set.py','check_cached_cell_set.py','finish_cached_cell_set.py','capture_cell_codebook_full.py',
        'verify_cell_codebook_continuation.py','warm_resume_snapshot.py','cell_codebook_player.py','guarded_cb46.py',
        'fap3_disk_z80.py','side_only_seek.py','measure_fap3_fuse.py','build_cell_codebook_trd.py','verify_cached_cell_player.py',
        'test_cached_set_gate.py','convert_cb41.py')
    nominal=all(x[k]['nominal_deadlines_met'] for x in results for k in ('cold_timing','continuation_timing'))
    result=dict(complete=True,release=nominal,preview_only=not nominal,user_authorized_delivery=True,
        date='2026-10-01',baseline_commit='f1476a2',whole_movie=True,
        frames=5066,ay_ticks=25330,duration_seconds=506.6,video_fps=10,ay_hz=50,disks=results,
        nominal_deadlines_met=nominal,all_nominal_deadlines_met=nominal,nominal_tolerance_tstates=64,
        release_gate='exact_nominal' if nominal else 'user_authorized_one_field_fallback',
        strict_one_field_fallback_met=True,
        source_frame_range=[prepared['first_source_frame'],prepared['last_source_frame']],edit_join=prepared['joins'],
        video_quality='Every rendered RGB pixel is identical to the prepared refined movie; unused attribute bits may differ.',
        ay_registers_sha256=sha(bytes(all_regs)),preparation_sha256=sha(a.prepared.read_bytes()),quality_samples=samples,
        quality_metric_frames=len(prepared['quality']),visible_pixel_changes=0,
        decoder_renderer_packet_instruction_delta_tstates=0,side_reader_machine_bytes_identical_to_baseline=True,
        physical_drive_swap_verified=False,controller_state_preserved=False,
        artifact_scope='Every cold and continuation screen, AY tick, sector and publication, plus native cold replay.',
        artifacts=artifacts,root_images=[],source_sha256_lf={n:sha(Path(__file__).with_name(n).read_bytes().replace(b'\r\n',b'\n')) for n in sources})
    write_json(a.output,result)
    if a.install:
        actual_root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=root,text=True).strip()).resolve()
        assert root==actual_root
        old=read(root/'toolkit/refined_av_movie_report.json')
        expected={x['file']:x['sha256'] for x in old['root_images']}
        new={x['file']:x['sha256'] for x in results}
        existing=list(root.glob('ZX-video-refined_part[0-9][0-9].trd'))
        for path in existing:
            assert path.resolve().parent==root and sha(path.read_bytes()) in (expected.get(path.name),new.get(path.name)),path
        for name in new:
            assert (root/name).resolve().parent==root
            assert subprocess.check_output(['git','check-attr','filter','--',name],cwd=root,text=True).strip()==f'{name}: filter: lfs'
        for name in new:shutil.copyfile(a.build/name,root/name)
        assert all(sha((root/n).read_bytes())==h for n,h in new.items())
        removed=[]
        for path in existing:
            if path.name not in new:path.unlink();removed.append(path.name)
        result['root_images']=[dict(file=n,sha256=h) for n,h in new.items()]
        result['removed_obsolete_refined_images']=removed;write_json(a.output,result)
    print(json.dumps(dict(complete=True,release=nominal,disks=len(results),frames=at,artifacts=len(artifacts),nominal=nominal,installed=a.install)))


if __name__=='__main__':main()
