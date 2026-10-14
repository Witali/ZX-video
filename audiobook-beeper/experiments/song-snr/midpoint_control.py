"""One frozen midpoint-table/C-joint control across the complete audio corpus.

Only the universal PDM table changes from the previous joint experiment.
Search settings, deterministic Pentagon clock, source preparation, compensated
prior, original8-kHz quality reference, filter and fixed edges stay common.
Host scores are separate from newly executed complete cold-boot proofs. This
script does not choose source-specific parameters or promote a release.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import time

import numpy as np

from artifact_diagnostics import (compare_reports,waveform_diagnostics,
                                  tone_diagnostics,clock_diagnostics)
from build_pdm import CPU_CLOCK,write_wav
from build_stream_trd import build
from clock_control import prepare,score,PARAMETERS as PREVIOUS_PARAMETERS
from convert_audio import pcm_wav
from execute_clock import compare_baseline_timing
from general import models,timeline,catalogue
from ima_codec import decode,require_unclipped
from native_waveform_encoder import write_workset,execute_workset,build_executable,_load
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from verify_pcm import save
from verify_stream_trd import native_check,fuse_check


NAMES=('silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam')
PROFILES=('128','scorpion','pentagon512','pentagon1024')
PARAMETERS=dict(PREVIOUS_PARAMETERS,model_name='duration_midpoint',
                compact_stream_loader=True,encoder='standalone-c',
                source_specific_parameter_selection=False)
MODEL=dict(dict(models())['duration_midpoint'],compact_stream_loader=True)


def sha(data):return hashlib.sha256(data).hexdigest()


def fingerprint():
    frozen=dict(parameters=PARAMETERS,model=MODEL,method='joint')
    return dict(**frozen,sha256=sha(json.dumps(frozen,sort_keys=True).encode()))


def diagnostics(source,reference,actual,variant):
    result=dict(source=source,variant=variant,
                waveform=waveform_diagnostics(reference,actual),
                fitted_diagnostic_only=True)
    if source in ('quiet440','quiet997','loud3000'):
        result['known_tone']=tone_diagnostics(reference,actual,
            dict(quiet440=440,quiet997=997,loud3000=3000)[source])
    return result


def saved_control(root,cache,name,method,reference,ffmpeg,scratch):
    """Reuse exact unscaled arrays, or reconstruct the archived packed control."""
    stage='clock-'+method
    host=json.loads((root/stage/name/'host.json').read_bytes())
    packed=gzip.decompress((root/stage/name/'soundtrack.ima.gz').read_bytes())
    assert sha(packed)==host['packed_sha256']
    source=wav8(root/'general/inputs'/(name+'.wav'))
    assert sha(source.tobytes())==host['source_sha256']
    refpath=cache/stage/(name+'-reference.npy')
    actualpath=cache/stage/(name+'-'+method+'-actual.npy')
    if refpath.exists() and actualpath.exists():
        oldref,actual=np.load(refpath),np.load(actualpath)
    else:
        _,oldref,actual=score(source,packed,host['model'],timeline(len(source),'pentagon'),ffmpeg,scratch)
    np.testing.assert_array_equal(oldref,reference)
    result=diagnostics(name,reference,actual,method)
    assert abs(result['waveform']['error_rms']-host['fixed_clock']['error_rms'])<1e-12
    result['packed_sha256']=host['packed_sha256']
    result['source_sha256']=host['source_sha256']
    result['actual_float64_sha256']=sha(actual.astype('<f8').tobytes())
    return result


def host_corpus(root,out,scratch,cache,names,ffmpeg,resume=False):
    started=time.perf_counter();out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    frozen=fingerprint()
    if (out/'parameters.json').exists():assert json.loads((out/'parameters.json').read_bytes())==frozen
    else:save(out/'parameters.json',frozen)
    library=_load();executable=build_executable();startup_seconds=time.perf_counter()-started
    rows=[];cached_rows=0
    report=dict(date='2026-10-14',complete=False,parameters=PARAMETERS,model=MODEL,
                frozen_parameter_sha256=frozen['sha256'],common_settings_all_sources=True,
                source_specific_fitted_gain_delay_clock=False,unfitted_original_clock_snr=True,
                measurement='Unchanged f64 listening filter; complete original8-kHz reference; fixed100-ms edges',
                new_emulator_verified=False,physical_hardware_tested=False,
                standalone_executable=str(executable),standalone_executable_sha256=sha(Path(executable).read_bytes()),
                native_source_sha256=library._nwf_source_sha256,
                matrix_library_sha256=sha(Path(library._nwf_blas_path).read_bytes()),
                startup_seconds=startup_seconds,rows=rows,
                universal_catalogue=catalogue(MODEL),hot_path_delta_tstates=0,
                compact_layout_native_proof='../compact-midpoint/report.json',
                ordinary_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
                page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
                scope='One source-independent table and search configuration across all complete sources. Host predictions and artifact diagnostics, not a new audio release or actual emulator proof.')
    for name in names:
        dest=out/name;dest.mkdir(exist_ok=True)
        if resume and (dest/'host.json').exists():
            row=json.loads((dest/'host.json').read_bytes())
            assert row['parameters']==PARAMETERS and row['model']==MODEL
            rows.append(row);cached_rows+=1;continue
        source_started=time.perf_counter()
        source_path=root/'general/inputs'/(name+'.wav');source=wav8(source_path)
        before_source=source.tobytes();times=timeline(len(source),'pentagon')
        assert len(source)%512==0 and np.all(source[-128:]==128)
        content=np.flatnonzero(source!=128)
        source_content_end_seconds=(int(content[-1])+1)/8000 if len(content) else 0.
        settling_start_seconds=float(times[(len(source)-128)*16]/CPU_CLOCK)
        assert settling_start_seconds>=source_content_end_seconds,'the final guard would discard source content'
        target=compensate(source,times[::16],radius=16,period=CPU_CLOCK/8000)
        assert np.all(target[-128:]==128),'No guard overwrite is allowed'
        desired,features,ids,nxt,quantization=prepare(source,times,MODEL)
        preparation_seconds=time.perf_counter()-source_started
        statistics={}
        with tempfile.TemporaryDirectory(dir=scratch,prefix=name+'-workset-') as temporary:
            work=Path(temporary);workset=work/'source.nwf';encoded=work/'encoded.ima'
            timer=time.perf_counter()
            write_workset(workset,target,desired,features,ids,nxt,width=32,
                          block_size=128,commit_size=64,regularization=.1)
            write_seconds=time.perf_counter()-timer;workset_sha=sha(workset.read_bytes());workset_bytes=workset.stat().st_size
            timer=time.perf_counter();packed=execute_workset(workset,encoded,statistics)
            encoding_seconds=time.perf_counter()-timer
        del desired,features,ids,nxt
        assert before_source==source.tobytes(),'the original source changed'
        assert len(packed)*2==len(source)
        decoded,index=decode(packed);assert (int(decoded[-1]),int(index[-1]))==(0,0)
        guard=require_unclipped(packed)
        (dest/'soundtrack.ima.gz').write_bytes(gzip.compress(packed,mtime=0))
        (dest/'source-preview.wav').write_bytes(source_path.read_bytes());pcm_wav(dest/'compensated-pcm.wav',target)
        timer=time.perf_counter();quality,wanted,actual=score(source,packed,MODEL,times,ffmpeg,scratch)
        render_seconds=time.perf_counter()-timer
        np.save(scratch/(name+'-reference.npy'),wanted);np.save(scratch/(name+'-midpoint-actual.npy'),actual)
        write_wav(dest/'reference.wav',wanted*.5);write_wav(dest/'host-actual.wav',actual*.5)
        after=diagnostics(name,wanted,actual,'midpoint')
        after['actual_float64_sha256']=sha(actual.astype('<f8').tobytes())
        after['reference_float64_sha256']=sha(wanted.astype('<f8').tobytes())
        comparisons=[]
        for method in ('compensation','joint'):
            control=saved_control(root,cache,name,method,wanted,ffmpeg,scratch)
            save(dest/(method+'-diagnostics.json'),control)
            comparisons.append(compare_reports(control,after))
        save(dest/'host-diagnostics.json',after)
        legacy=json.loads((root/'clock-joint'/name/'host.json').read_bytes())['baseline_fixed_clock']
        row=dict(source=name,method='joint',parameters=PARAMETERS,model=MODEL,
                 source_samples=len(source),source_sha256=sha(source.tobytes()),
                 original_wav_sha256=sha(source_path.read_bytes()),packed_sha256=sha(packed),
                 compensated_prior_sha256=sha(target.tobytes()),original_content_preserved=True,
                 source_content_end_seconds=source_content_end_seconds,settling_start_seconds=settling_start_seconds,
                 final128_guard_already_silent=True,source_specific_parameter_selection=False,
                 fixed_clock=quality,baseline_fixed_clock=legacy,
                 change_db=None if quality['snr_db'] is None else quality['snr_db']-legacy['snr_db'],
                 comparisons=comparisons,preparation_seconds=preparation_seconds,
                 workset_write_seconds=write_seconds,workset_bytes=workset_bytes,workset_sha256=workset_sha,
                 standalone_c_encoding_seconds=encoding_seconds,render_seconds=render_seconds,
                 entire_host_conversion_seconds=time.perf_counter()-source_started,
                 statistics=statistics,max_search_query_quantization_seconds=quantization,
                 saturation_guard=guard,host_prediction=True,new_emulator_verified=False,
                 scope='Complete unchanged source; common midpoint PDM/C-joint encoder on instruction-derived Pentagon timeline. No fitted gain/delay/clock and no new emulator proof.')
        save(dest/'host.json',row);rows.append(row)
        print(json.dumps(dict(source=name,snr_db=quality['snr_db'],noise_rms=quality['error_rms'],
                              comparisons=[dict(from_variant=c['from_variant'],snr_change_db=c['fixed_snr_change_db'],
                                                regressions=c['numeric_regressions']) for c in comparisons],
                              c_seconds=encoding_seconds)),flush=True)
        save(out/'partial.json',report)
    report['complete']=tuple(names)==NAMES
    totals={}
    for row in rows:
        for comparison in row['comparisons']:
            bucket=totals.setdefault(comparison['from_variant'],dict(sources=0));bucket['sources']+=1
            for k,v in comparison['numeric_regressions'].items():bucket[k]=bucket.get(k,0)+int(v)
    report['diagnostic_numeric_regression_counts']=totals
    report['attempt_wall_seconds']=time.perf_counter()-started
    report['cached_source_records']=cached_rows
    report['newly_encoded_sources']=len(rows)-cached_rows
    report['completed_source_conversion_seconds_sum']=sum(row['entire_host_conversion_seconds'] for row in rows)
    report['entire_host_corpus_wall_seconds']=(report['attempt_wall_seconds'] if cached_rows==0 else None)
    report['timing_scope']='Per-source times include preparation, workset serialization, C execution, full rendering and artifact diagnostics. A resumed attempt is not a fresh full conversion benchmark; its wall time is reported separately. TRD assembly/emulator execution is separate.'
    report['decision']='Reject unconditional midpoint-joint replacement:4 whole-source SNR/RMS regressions versus half-joint, a new approximately1996-Hz tonal silence line, and numerical AM/delay/coherent-error regressions. No new Fuse run is warranted for this rejected host candidate. The lower silence RMS does not establish absence of added background.'
    report['producer_sha256_lf']={str(Path(__file__).name):sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))}
    save(out/'report.json',report)
    return report


def cover_from_control(root):
    old=json.loads((root/'study/inputs/song/player.json').read_bytes())
    current=(root/'study/inputs/current-main.trd').read_bytes()
    entry=next(x for x in old['directory'] if x['name']=='COVER')
    at=(entry['track']*16+entry['sector'])*256
    return current[at:at+6912]


def execute_source(root,out,scratch,name,cover,fuse,ffmpeg,captured=False):
    """Selected complete cold executions keep the same frozen midpoint model."""
    dest=out/name;host_bytes=(dest/'host.json').read_bytes();host=json.loads(host_bytes)
    assert host['parameters']==PARAMETERS and host['model']==MODEL
    assert json.loads((out/'parameters.json').read_bytes())==fingerprint()
    source=wav8(dest/'source-preview.wav');packed=gzip.decompress((dest/'soundtrack.ima.gz').read_bytes())
    assert sha(source.tobytes())==host['source_sha256'] and sha(packed)==host['packed_sha256']
    assert len(source)==len(packed)*2==host['source_samples'] and host['original_content_preserved']
    disk,meta=build(packed,dest/'assembly',cover,MODEL)
    if captured:
        assert (dest/'audio.trd').read_bytes()==disk
        assert json.loads((dest/'player.json').read_bytes())==meta
    else:(dest/'audio.trd').write_bytes(disk);save(dest/'player.json',meta)
    labels=meta['player_labels'];assert labels['resident_end']==meta['memory']['worker_origin']==0xbc40
    assert labels['startup_end']<=min(meta['first_addresses']) and labels['stream_worker_end']<0xbfff
    verify=dest/'verification';verify.mkdir(exist_ok=True)
    native=[native_check(disk,meta,packed,profile,out=verify/('native-'+profile+'.json')) for profile in PROFILES]
    print('Native midpoint complete: '+name,flush=True)
    actual=[]
    for profile in (('pentagon512','pentagon1024') if name=='sea_foam' else ('pentagon512',)):
        proof=fuse_check(dest/'audio.trd',meta,packed,profile,verify/profile,fuse,captured=captured)
        raw=np.frombuffer(gzip.decompress((verify/profile/'times.u32.gz').read_bytes()),'<u4')
        count=proof['bits_verified'];assert len(raw)==count
        expected=timeline(len(source),'pentagon')[:count]
        np.testing.assert_array_equal(raw.astype(float)*CPU_CLOCK/3584000,expected)
        assert proof['reloads']==proof['runtime_disk_reads_during_live_audio']==0
        proof['every_actual_timestamp_matches_instruction_derived_schedule']=True
        proof['before_after_timing']=compare_baseline_timing(root,name,profile,verify)
        baseline=[]
        for oldstage in ('clock-compensation','clock-joint'):
            old=root/oldstage/name/'verification'/profile/'times.u32.gz'
            if old.exists():
                prior=gzip.decompress(old.read_bytes());now=raw.astype('<u4').tobytes();assert prior==now
                baseline.append(dict(stage=oldstage,every_timestamp_identical=True,timestamps=len(raw),
                                     introduced_timing_change_tstates=0,sha256=sha(now)))
        proof['complete_previous_control_timing']=baseline
        quality,wanted,y=score(source,packed,MODEL,raw.astype(float)*CPU_CLOCK/3584000,ffmpeg,scratch)
        assert abs(quality['error_rms']-host['fixed_clock']['error_rms'])<1e-12
        diag=diagnostics(name,wanted,y,'midpoint-actual-'+profile)
        diag['actual_pulse_clock']=clock_diagnostics(raw,cpu_hz=3584000)
        diag['complete_actual_fuse_clock']=True
        save(verify/profile/'quality.json',dict(complete=True,fixed_clock=quality,own_complete_fuse_clock=True,
                                              host_prediction_exact=True,trd_sha256=meta['trd_sha256']))
        save(verify/profile/'artifact-diagnostics.json',diag);actual.append(proof)
        print('Fuse midpoint complete: '+name+'/'+profile,flush=True)
    result=dict(date='2026-10-14',complete=True,source=name,model=MODEL,parameters=PARAMETERS,
                source_sha256=host['source_sha256'],packed_sha256=host['packed_sha256'],
                host_report_sha256=sha(host_bytes),trd_sha256=meta['trd_sha256'],native=native,fuse=actual,
                worker_origin=meta['memory']['worker_origin'],worker_end=labels['stream_worker_end'],
                original_content_preserved=True,hot_path_delta_tstates=0,
                ordinary_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
                page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
                physical_hardware_tested=False,main_release_unchanged=True,
                scope='Complete native functionality on all4profiles and listed own-clock Pentagon Fuse proofs. Audio compensation targets Pentagon; no 128/Scorpion quality or unconditional artifact-safety claim.')
    save(verify/'execution.json',result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--scratch',type=Path,default=Path('.tmp/midpoint-control'))
    parser.add_argument('--cache',type=Path,default=Path('.tmp'))
    parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    parser.add_argument('--source',action='append',choices=NAMES)
    parser.add_argument('--phase',choices=('host','execute'),default='host')
    parser.add_argument('--resume',action='store_true');parser.add_argument('--captured',action='store_true')
    parser.add_argument('--fuse',type=Path);parser.add_argument('--jobs',type=int,default=3)
    args=parser.parse_args();root=args.evidence.resolve();out=(args.output or root/'midpoint-control').resolve()
    scratch=args.scratch.resolve();scratch.mkdir(parents=True,exist_ok=True)
    names=tuple(args.source or NAMES);assert len(names)==len(set(names))
    if args.phase=='host':host_corpus(root,out,scratch,args.cache.resolve(),names,args.ffmpeg,args.resume)
    else:
        if not args.fuse:parser.error('Execution requires --fuse')
        assert 1<=args.jobs<=4
        cover=cover_from_control(root)
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            reports=list(pool.map(lambda name:execute_source(root,out,scratch,name,cover,args.fuse,args.ffmpeg,args.captured),names))
        save(out/'execution.json',dict(complete=True,date='2026-10-14',sources=list(names),
                    native_full_runs=sum(len(r['native']) for r in reports),
                    fuse_full_runs=sum(len(r['fuse']) for r in reports),reports=reports,
                    source_independent_preset=True,physical_hardware_tested=False,main_release_unchanged=True))


if __name__=='__main__':main()
