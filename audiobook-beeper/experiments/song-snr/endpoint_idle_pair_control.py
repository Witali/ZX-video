"""One frozen endpoint-idle-pair-table/C-joint control across the complete audio corpus.

One source-free analytically selected endpoint-consistent zero-mean pair replaces only bin32 packet words at states16 and17. It derives the retained17/16 successor cycle under exact Fraction recurrence. Total on-time is449 of898T; every other word and successor remain unchanged. Both literals are frozen before opening sources.
Search settings, deterministic Pentagon clock, source preparation, compensated
prior, original8-kHz quality reference, filter and fixed edges stay common.
Host scores are separate from newly executed complete cold-boot proofs. This
script does not choose source-specific parameters or promote a release.
"""
import argparse
from fractions import Fraction
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
from clock_control import score,PARAMETERS as PREVIOUS_PARAMETERS
from ima_waveform_encoder import WaveformModel
from probe_feedback_packets import integral_table
from endpoint_idle_pair_model import apply_endpoint_idle_pair,ENDPOINT_IDLE_PAIR_WORDS
from convert_audio import pcm_wav
from execute_clock import compare_baseline_timing
from general import models,timeline
from ima_codec import decode,require_unclipped
from native_waveform_encoder import write_workset,execute_workset,build_executable,_load
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from verify_pcm import save
from verify_stream_trd import native_check,fuse_check
from centered_quantizer_control import fullband_silence_peaks


NAMES=('silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer','sea_foam')
PROFILES=('128','scorpion','pentagon512','pentagon1024')
PARAMETERS=dict(PREVIOUS_PARAMETERS,model_name='duration_zero',
                compact_stream_loader=True,pcm_quantization_bias=512,encoder='standalone-c',
                endpoint_idle_pair_words=list(ENDPOINT_IDLE_PAIR_WORDS),
                source_specific_parameter_selection=False)
MODEL=dict(dict(models())['duration_zero'],compact_stream_loader=True,pcm_quantization_bias=512,
           endpoint_idle_pair_words=list(ENDPOINT_IDLE_PAIR_WORDS))


def sha(data):return hashlib.sha256(data).hexdigest()


def packet_table(model):
    """Apply the frozen two-word pair to the original all64-by32 table."""
    words,nxt,peak=integral_table(64,2,holds=model['holds'],beta=model['beta'],
                                extent=model['extent'],pcm_origin=model.get('pcm_origin',.5))
    original_successors=nxt.copy()
    words,nxt=apply_endpoint_idle_pair(words,nxt,model)
    np.testing.assert_array_equal(nxt,original_successors)
    return words,nxt,peak


def prepare(source,times,model):
    """Unchanged analytic clock features using the literal neutral table.

    Source clock, filter model and quadrature query grid match clock_control;
    only packet words and successors are supplied by this new fixed table.
    """
    count=len(source)-128
    assert np.all(source[-128:]==128),'settling tail must contain no source content'
    holds=np.diff(times)[:count*16].reshape(count,16)
    unique,ids=np.unique(holds,axis=0,return_inverse=True)
    words,nxt,_=packet_table(model)
    shifts=np.arange(15,-1,-1)
    signed=((words.ravel()[:,None]>>shifts)&1).astype(float)*2-1
    analog=WaveformModel();features=[]
    for row in unique:
        a,b,l,r=analog.packet(row)
        features.append((a,l,signed@r.T,signed@b.T,row/(CPU_CLOCK/8000)))
    queries=((times[:count*16]+times[1:count*16+1])/2).reshape(count,16)
    rounded=np.rint(queries*80)/80
    desired=analog.reference(source,rounded)
    return desired,features,ids,nxt,float(np.max(abs(queries-rounded))/CPU_CLOCK)


def fraction_endpoints(model,words,nxt):
    """Independently replay forced pulse words in the exact q/recent recurrence.

    q is encoded on the original1/8 grid and recent has two midpoint states.
    Normalized hold weight is16*hold/449. The endpoint rounds q to the nearest
    original grid code and floors recent into its original half-open bin;
    the original1e-12 endpoint epsilon is represented as an exact Fraction.
    The primary helper does not derive this certificate.
    """
    assert model['beta']==.5 and model['extent']==1 and model['pcm_origin']==0
    total=sum(model['holds']);assert total==449
    epsilon=Fraction(1,10**12)
    result=[]
    for state,word in zip((16,17),model['endpoint_idle_pair_words']):
        q=Fraction(state//2-8,8);recent=Fraction(2*(state%2)-1,2)
        rows=[];active=0;maximum=abs(recent)
        for slot,hold in enumerate(model['holds']):
            weight=Fraction(16*int(hold),total);bit=(int(word)>>(15-slot))&1
            u=Fraction(1,2)+q/weight+Fraction(1,2)*recent
            recent=u-bit;q+=weight*(Fraction(1,2)-bit)
            maximum=max(maximum,abs(recent));active+=int(hold)*bit
            rows.append(dict(slot=slot,hold_tstates=int(hold),bit=bit,
                             q_after=str(q),recent_after=str(recent)))
        qcode=min(15,max(0,(q*8+Fraction(17,2)+epsilon).numerator//(q*8+Fraction(17,2)+epsilon).denominator))
        r=min(1,max(0,(recent+1+epsilon).numerator//(recent+1+epsilon).denominator))
        derived=qcode*2+r;expected=int(nxt[32,state])
        assert derived==expected==({16:17,17:16}[state])
        assert int(words[32,state])==word
        result.append(dict(state_before=state,word=int(word),word_hex=f'{word:04x}',
                           active_tstates=active,total_tstates=total,
                           q_end=str(q),recent_end=str(recent),q_end_float=float(q),
                           recent_end_float=float(recent),q_code=qcode,recent_code=r,
                           derived_successor=derived,stored_successor=expected,
                           maximum_absolute_recent=str(maximum),slots=rows))
    assert [row['active_tstates'] for row in result]==[224,225]
    return dict(complete=True,source_audio_opened=False,independent_fraction_arithmetic=True,
                recurrence='weight=16*hold/449;u=1/2+q/weight+recent/2;recent=u-bit;q+=weight*(1/2-bit)',
                quantizer='epsilon=1/10^12;qcode=clip(floor(8*q+8.5+epsilon),0,15);recentcode=clip(floor(recent+1+epsilon),0,1);next=2*qcode+recentcode',
                original_endpoint_epsilon_fraction=str(epsilon),
                endpoints=result,pair_nominal_on_tstates=449,pair_nominal_total_tstates=898,
                pair_nominal_duty=.5,derived_original_successors_retained=True,
                scope='Exact endpoint and nominal area certificate only; no source/quality, continuous-filter or actual transport proof.')


def catalogue(model):
    """Close the overridden table over all64 bins before reading a source."""
    words,nxt,peak=packet_table(model)
    assert [int(words[32,16]),int(words[32,17])]==model['endpoint_idle_pair_words']
    assert int(nxt[32,16])==17 and int(nxt[32,17])==16
    original_words,original_next,_=integral_table(64,2,holds=model['holds'],beta=model['beta'],extent=model['extent'],pcm_origin=model['pcm_origin'])
    mask=np.ones(words.shape,dtype=bool);mask[32,[16,17]]=False
    np.testing.assert_array_equal(words[mask],original_words[mask])
    np.testing.assert_array_equal(nxt,original_next)
    reachable={16}
    while True:
        expanded=reachable|set(map(int,nxt[:,sorted(reachable)].ravel()))
        if expanded==reachable:break
        reachable=expanded
    used=words[:,sorted(reachable)]
    first=len(np.unique(used>>8));second=len(np.unique(used&255))
    code=first*42+second*64;fixed=256+1024+1088;startup=0x340
    reserve=((startup+code+255)//256)*256+fixed
    assert len(reachable)<=18
    endpoints=fraction_endpoints(model,words,nxt)
    return dict(fraction_endpoint_certificate=endpoints,reachable_feedback_states=len(reachable),reachable_state_ids=sorted(reachable),
                first_patterns=first,second_patterns=second,unrolled_pattern_code_bytes=code,
                packet_bytes_per_bin=len(reachable)*6,current_protected_state_limit_passed=True,
                resident_bytes_before_worker=reserve,compact_estimated_worker_origin=0x8000+reserve,
                worker_end_requires_assembly=True,q_clip=[0,15],table_internal_peak=peak,
                packet_table_sha256=sha(words.astype('<u2').tobytes()),
                successor_table_sha256=sha(nxt.astype('<u2').tobytes()),
                endpoint_idle_pair_words=model['endpoint_idle_pair_words'],only_idle_word_states=[16,17],all_successors_unchanged=True,
                bound_scope='Overridden table; all64 input bins and all reachable feedback states, independent of sources. Resident estimate requires builder/native confirmation.')


def fingerprint():
    frozen=dict(parameters=PARAMETERS,model=MODEL,method='joint')
    return dict(**frozen,sha256=sha(json.dumps(frozen,sort_keys=True).encode()))


def producer_snapshot(out):
    """Authenticate and archive producer bytes before opening any corpus input."""
    repo=Path(__file__).resolve().parents[3]
    names=('audiobook-beeper/experiments/song-snr/endpoint_idle_pair_control.py',
           'audiobook-beeper/endpoint_idle_pair_model.py','audiobook-beeper/build_stream_trd.py',
           'audiobook-beeper/direct_player.py','audiobook-beeper/verify_direct.py',
           'audiobook-beeper/verify_stream_trd.py','audiobook-beeper/verify_packet.py',
           'audiobook-beeper/native_waveform_encoder.py','audiobook-beeper/native_waveform_encoder.c',
           'audiobook-beeper/waveform_kernel.py','audiobook-beeper/probe_feedback_packets.py',
           'audiobook-beeper/ima_codec.py','audiobook-beeper/precompensate_voice.py',
           'audiobook-beeper/stream-player.asm','audiobook-beeper/stream-worker.asm',
           'audiobook-beeper/experiments/song-snr/clock_control.py',
           'audiobook-beeper/experiments/song-snr/general.py',
           'audiobook-beeper/experiments/song-snr/study.py',
           'audiobook-beeper/experiments/song-snr/artifact_diagnostics.py',
           'audiobook-beeper/experiments/song-snr/centered_quantizer_control.py',
           'audiobook-beeper/experiments/song-snr/midpoint_control.py',
           'audiobook-beeper/experiments/song-snr/execute_clock.py')
    rows=[]
    for name in names:
        data=(repo/name).read_bytes()
        rows.append(dict(path=name,bytes=len(data),sha256_exact=sha(data),
                         sha256_lf=sha(data.replace(b'\r\n',b'\n'))))
    frozen=dict(date='2026-10-14',complete=True,before_any_corpus_input_read=True,
                frozen_parameters=fingerprint(),producer_files=rows)
    path=out/'producer-snapshot.json'
    if path.exists():assert json.loads(path.read_bytes())==frozen
    else:
        for row in rows:
            dest=out/'producer-source'/(row['path']+'.gz');dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(gzip.compress((repo/row['path']).read_bytes(),mtime=0))
        save(path,frozen)
    return sha(path.read_bytes())


def diagnostics(source,reference,actual,variant):
    result=dict(source=source,variant=variant,
                waveform=waveform_diagnostics(reference,actual),
                fitted_diagnostic_only=True)
    if source in ('quiet440','quiet997','loud3000'):
        result['known_tone']=tone_diagnostics(reference,actual,
            dict(quiet440=440,quiet997=997,loud3000=3000)[source])
    if source=='silence':result['fullband_silence_peaks']=fullband_silence_peaks(actual)
    return result


def saved_control(root,cache,name,method,reference,ffmpeg,scratch):
    """Reuse exact unscaled arrays, or reconstruct the archived packed control."""
    stage={'matched-centered':'matched-centered-control','idle-cycle':'idle-cycle-control','idle-pair':'idle-pair-control'}.get(method,'clock-'+method)
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
    snapshot_sha256=producer_snapshot(out)
    bounds=catalogue(MODEL)
    save(out/'frozen-fraction-endpoints.json',bounds['fraction_endpoint_certificate'])
    library=_load();executable=build_executable();startup_seconds=time.perf_counter()-started
    rows=[];cached_rows=0
    report=dict(date='2026-10-14',complete=False,parameters=PARAMETERS,model=MODEL,
                frozen_parameter_sha256=frozen['sha256'],producer_snapshot_sha256=snapshot_sha256,
                producer_archived_before_any_corpus_input=True,common_settings_all_sources=True,
                source_specific_fitted_gain_delay_clock=False,unfitted_original_clock_snr=True,
                measurement='Unchanged f64 listening filter; complete original8-kHz reference; fixed100-ms edges',
                new_emulator_verified=False,physical_hardware_tested=False,
                standalone_executable=str(executable),standalone_executable_sha256=sha(Path(executable).read_bytes()),
                native_source_sha256=library._nwf_source_sha256,
                matrix_library_sha256=sha(Path(library._nwf_blas_path).read_bytes()),
                startup_seconds=startup_seconds,rows=rows,
                universal_catalogue=bounds,hot_path_delta_tstates=0,
                compact_layout_native_proof='../compact-midpoint/report.json',
                compact_layout_proof_scope='Previous startup relocation proof; current centered duration_zero image requires its own execution phase.',
                centered_mapping='min(63,(signedPCM+32768+512)//1024);bin32 covers[-512,511];table pcm_origin0 maps bin32 to duty32/64',
                same_cpu_instructions=True,lookup_data_changed=True,
                ordinary_tstates={'128':423,'scorpion':423,'pentagon512':449,'pentagon1024':449},
                page_extra_tstates=14,bank_extra_tstates={'128':243,'scorpion':267,'pentagon512':243,'pentagon1024':243},
                scope='One frozen two-word zero-mean endpoint-idle-pair override and unchanged search configuration across all complete sources. Host predictions and artifact diagnostics, not a new audio release or actual emulator proof.')
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
                          block_size=128,commit_size=64,regularization=.1,pcm_quantization_bias=512)
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
        np.save(scratch/(name+'-reference.npy'),wanted);np.save(scratch/(name+'-endpoint-idle-pair-actual.npy'),actual)
        write_wav(dest/'reference.wav',wanted*.5);write_wav(dest/'host-actual.wav',actual*.5)
        after=diagnostics(name,wanted,actual,'endpoint-idle-pair')
        after['actual_float64_sha256']=sha(actual.astype('<f8').tobytes())
        after['reference_float64_sha256']=sha(wanted.astype('<f8').tobytes())
        comparisons=[]
        for method in ('compensation','joint','matched-centered','idle-cycle','idle-pair'):
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
                 scope='Complete unchanged source; common endpoint-idle-pair PDM/C-joint encoder on instruction-derived Pentagon timeline. No fitted gain/delay/clock and no new emulator proof.')
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
    report['artifact_accepted']=False
    report['new_fuse_verified']=False
    report['decision']='Reject unconditional endpoint-idle-pair promotion:valid exact17/16 endpoints recover speech, entertainer and matched song slightly, but song remains0.137209677dB below half-joint. Steps, multitone and loud3000 regress versus matched-centered; silence is noisier than both prior idle controls. Approximately3991-Hz and11972-Hz residual lines and numeric AM/delay/background increases leave artifact acceptance unresolved. Endpoint correctness and nominal zero-mean area are mechanism evidence, not universal quality or artifact-absence proof. No new Fuse run or release promotion is warranted for this rejected candidate.'
    report['artifact_acceptance_scope']='Compare compensation and half-joint at the unchanged original source clock. Legacy fitted modulation is inapplicable when drift breaks coherence. Regression counters disclose every numeric increase with arithmetic tolerance only; no user-supplied audibility threshold exists.'
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
    """Selected complete cold executions keep the same frozen endpoint-idle-pair model."""
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
    labels=meta['player_labels'];assert labels['resident_end']==meta['memory']['worker_origin']
    assert meta['memory']['worker_origin']%64==0
    assert labels['startup_end']<=min(meta['first_addresses']) and labels['stream_worker_end']<0xbfff
    verify=dest/'verification';verify.mkdir(exist_ok=True)
    native=[native_check(disk,meta,packed,profile,out=verify/('native-'+profile+'.json')) for profile in PROFILES]
    print('Native endpoint-idle-pair complete: '+name,flush=True)
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
        for oldstage in ('clock-compensation','clock-joint','matched-centered-control','idle-cycle-control','idle-pair-control'):
            old=root/oldstage/name/'verification'/profile/'times.u32.gz'
            if old.exists():
                prior=gzip.decompress(old.read_bytes());now=raw.astype('<u4').tobytes();assert prior==now
                baseline.append(dict(stage=oldstage,every_timestamp_identical=True,timestamps=len(raw),
                                     introduced_timing_change_tstates=0,sha256=sha(now)))
        proof['complete_previous_control_timing']=baseline
        quality,wanted,y=score(source,packed,MODEL,raw.astype(float)*CPU_CLOCK/3584000,ffmpeg,scratch)
        assert abs(quality['error_rms']-host['fixed_clock']['error_rms'])<1e-12
        diag=diagnostics(name,wanted,y,'endpoint-idle-pair-actual-'+profile)
        diag['actual_pulse_clock']=clock_diagnostics(raw,cpu_hz=3584000)
        diag['complete_actual_fuse_clock']=True
        save(verify/profile/'quality.json',dict(complete=True,fixed_clock=quality,own_complete_fuse_clock=True,
                                              host_prediction_exact=True,trd_sha256=meta['trd_sha256']))
        save(verify/profile/'artifact-diagnostics.json',diag);actual.append(proof)
        print('Fuse endpoint-idle-pair complete: '+name+'/'+profile,flush=True)
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
    parser.add_argument('--scratch',type=Path,default=Path('.tmp/endpoint-idle-pair-control'))
    parser.add_argument('--cache',type=Path,default=Path('.tmp'))
    parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    parser.add_argument('--source',action='append',choices=NAMES)
    parser.add_argument('--phase',choices=('host','execute'),default='host')
    parser.add_argument('--resume',action='store_true');parser.add_argument('--captured',action='store_true')
    parser.add_argument('--fuse',type=Path);parser.add_argument('--jobs',type=int,default=3)
    args=parser.parse_args();root=args.evidence.resolve();out=(args.output or root/'endpoint-idle-pair-control').resolve()
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
