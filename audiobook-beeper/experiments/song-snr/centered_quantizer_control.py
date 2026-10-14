"""Frozen-stream host control for centered64-bin predictor lookup.

Apply one512-PCM16 offset to every source in each of the two saved joint
streams. IMA bytes, predictors, indices, PDM table, feedback recurrence and
deterministic Pentagon clock stay unchanged. Only the packet input bucket
changes. These are newly mapped host predictions, not new C-optimized streams,
assembled disks or emulator proofs. The legacy baseline remains untouched.
"""
import argparse
import gzip
import json
from pathlib import Path
import shutil
import time

import numpy as np

from artifact_diagnostics import compare_reports,clock_diagnostics
from build_pdm import CPU_CLOCK,write_wav
from general import timeline
from ima_codec import decode,require_unclipped
from midpoint_control import diagnostics,NAMES,sha
from probe_feedback_packets import model_table
from probe_reconstruction_error import wav8
from study import filtered,metrics
from verify_direct import reference
from verify_packet import rational_tables
from verify_pcm import save


FORMULA='min(63,(predictor+32768+512)//1024)'
STAGES=('clock-joint','midpoint-control')
SETTINGS=dict(pcm16_offset=512,pcm_bins=64,minimum_bin=0,maximum_bin=63,
              source_rate_hz=8000,profile='pentagon',source_specific_selection=False,
              source_gain_bandwidth_length_changed=False,encoded_bytes_changed=False,
              pdm_table_changed=False,initial_feedback_state=16,
              new_encoder_optimization=False,host_mapping_only=True)


def bins(predictors,offset):
    values=np.asarray(predictors,dtype=np.int64)
    if np.any(values<-32768) or np.any(values>32767):raise ValueError('Predictor must be PCM16')
    if offset not in (0,512):raise ValueError('Only archived floor and frozen centered mapping are supported')
    return np.minimum(63,(values+32768+offset)//1024).astype('u1')


def self_check():
    """Check every PCM16 input against the proposed256-byte high-byte LUT."""
    values=np.arange(-32768,32768,dtype=np.int64)
    old,new=bins(values,0),bins(values,512)
    lut=np.minimum(63,(np.arange(256,dtype=np.int64)+2)//4)
    np.testing.assert_array_equal(new,lut[(values+32768)>>8])
    assert int(new.min())==0 and int(new.max())==63 and np.all(np.diff(new.astype(int))>=0)
    assert np.all((new.astype(int)-old.astype(int)>=0)&(new.astype(int)-old.astype(int)<=1))
    assert bins([-1,0],0).tolist()==[31,32] and bins([-1,0],512).tolist()==[32,32]
    assert bins([-512,511],512).tolist()==[32,32]
    assert bins([-513,512],512).tolist()==[31,33]
    assert bins([-32768,32767],512).tolist()==[0,63]
    assert np.count_nonzero((values+32768+512)//1024==64)==512
    return dict(complete=True,all_pcm16_inputs=65536,
                zero_crossing_before=[31,32],zero_crossing_after=[32,32],
                centered_zero_bin_predictor_range=[-512,511],
                upper_clamped_predictor_range=[32256,32767],
                lower_bin_predictor_range=[-32768,-32257],
                hardware_lut_equivalent='pcm_high[IXH] -> packet_pages[min(63,(IXH+2)//4)]',
                all_inputs_exactly_match_256_byte_lut=True,
                opcode_delta_premise=0,
                premise_only='No instructions need be added if a future opt-in changes only this pointer LUT; no new assembly/native/Fuse execution has occurred.')


def packets(levels,words,successors):
    """Exact rational-table packet recurrence; feedback carries across EOF scope."""
    state=16;output=np.empty(len(levels),dtype='>u2');states=np.empty(len(levels),dtype='u1')
    for i,value in enumerate(levels):
        states[i]=state;output[i]=words[int(value),state];state=int(successors[int(value),state])
    return np.unpackbits(output.view('u1')),states,state


def fullband_silence_peaks(actual):
    """Disclose residual carriers above4500 Hz as well as audible-band lines."""
    values=np.asarray(actual)[4410:-4410];size=min(32768,2**int(np.floor(np.log2(len(values)))))
    window=np.hanning(size);power=np.zeros(size//2+1)
    starts=list(range(0,len(values)-size+1,size//2))
    if starts[-1]+size<len(values):starts.append(len(values)-size)
    for first in starts:power+=np.abs(np.fft.rfft(values[first:first+size]*window))**2
    power[1:-1]*=2
    frequency=np.fft.rfftfreq(size,1/44100)
    eligible=np.flatnonzero(frequency>=20);ids=eligible[np.argsort(power[eligible])[-8:][::-1]]
    return dict(scope='Complete silence except fixed100-ms edges;20..22050Hz;Hann Welch bins;no fitted transfer',
                window_samples=size,windows=len(starts),bin_width_hz=44100/size,
                strongest_bins=[dict(hz=float(frequency[i]),
                    three_bin_total_noise_power_fraction=float(power[max(0,i-1):i+2].sum()/max(power.sum(),1e-30))) for i in ids])


def control(root,out,scratch,cache,stages,names,ffmpeg,resume=False):
    out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    settings=dict(settings=SETTINGS,formula=FORMULA,stages=list(stages),sources=list(names))
    frozen=sha(json.dumps(settings,sort_keys=True).encode())
    if (out/'parameters.json').exists():assert json.loads((out/'parameters.json').read_bytes())==dict(**settings,sha256=frozen)
    else:save(out/'parameters.json',dict(**settings,sha256=frozen))
    started=time.perf_counter();rows=[];cached=0
    report=dict(date='2026-10-14',complete=False,settings=SETTINGS,formula=FORMULA,
                frozen_parameter_sha256=frozen,self_check=self_check(),rows=rows,
                host_mapped_prediction=True,new_encoder_optimized=False,new_disk_built=False,
                emulator_verified=False,physical_hardware_tested=False,
                full_source_clock='Original uniform8-kHz reference, unchanged f64 filter, fixed100-ms edges, no fitted gain/delay/clock',
                common_mapping_all_sources=True,legacy_baseline_unchanged=True,
                deterministic_pentagon_clock_unchanged=True,
                hot_path_instruction_delta_premise=0,
                table_words_and_successors_independently_checked=True,
                scope='Same complete encoded streams on the same deterministic clock, oldfloor versus fixedcentered lookup. This isolates quantizer bin selection; it is not optimized new encoder/player output or release proof.')
    for stage in stages:
        example=json.loads((root/stage/names[0]/'host.json').read_bytes())
        model=example['model'];floating=model_table(model)
        words,nxt=rational_tables(model['holds'],floating,model['beta'],model['extent'],
            tuple(model.get('q_clip',(0,15))),pcm_origin=model.get('pcm_origin',.5))
        table_sha=sha(words.astype('<u2').tobytes()+nxt.astype('u1').tobytes())
        for name in names:
            dest=out/stage/name;dest.mkdir(parents=True,exist_ok=True)
            if resume and (dest/'host.json').exists():
                row=json.loads((dest/'host.json').read_bytes());assert row['settings']==SETTINGS and row['formula']==FORMULA
                rows.append(row);cached+=1;continue
            source_started=time.perf_counter();host_path=root/stage/name/'host.json';host_bytes=host_path.read_bytes()
            host=json.loads(host_bytes);assert host['model']==model
            packed_bytes=(root/stage/name/'soundtrack.ima.gz').read_bytes();packed=gzip.decompress(packed_bytes)
            original_sha=sha(packed);assert original_sha==host['packed_sha256']
            source=wav8(root/'general/inputs'/(name+'.wav'))
            assert sha(source.tobytes())==host['source_sha256'] and len(source)==len(packed)*2==host['source_samples']
            pcm,index=decode(packed);guard=require_unclipped(packed);assert (int(pcm[-1]),int(index[-1]))==(0,0)
            floor,center=bins(pcm,0),bins(pcm,512)
            oldbits,_,oldstate=packets(floor,words,nxt)
            _,_,_,independent=reference(packed,cycles=1,model=model)
            np.testing.assert_array_equal(oldbits,independent[:len(oldbits)])
            newbits,states,newstate=packets(center,words,nxt)
            times=timeline(len(source),'pentagon');count=(len(source)-3)*16+15;edges=times[:count]
            # Authenticate the old unscaled source/output arrays against the
            # frozen host score, with an independent full floor recurrence.
            folder=cache/('clock-joint' if stage=='clock-joint' else 'midpoint-control')
            suffix='joint' if stage=='clock-joint' else 'midpoint'
            oldref=np.load(folder/(name+'-reference.npy'))
            oldactual=np.load(folder/(name+'-'+suffix+'-actual.npy'))
            oldrender=filtered(oldbits[:count-1],edges,ffmpeg,scratch)
            np.testing.assert_array_equal(oldrender,oldactual)
            oldquality=metrics(oldref,oldactual)
            assert abs(oldquality['error_rms']-host['fixed_clock']['error_rms'])<1e-12
            actual=filtered(newbits[:count-1],edges,ffmpeg,scratch)
            quality=metrics(oldref,actual)
            np.save(scratch/(stage+'-'+name+'-reference.npy'),oldref)
            np.save(scratch/(stage+'-'+name+'-centered-actual.npy'),actual)
            write_wav(dest/'host-centered.wav',actual*.5);write_wav(dest/'reference.wav',oldref*.5)
            before=diagnostics(name,oldref,oldactual,'floor')
            after=diagnostics(name,oldref,actual,'centered')
            before['actual_float64_sha256']=sha(oldactual.astype('<f8').tobytes())
            after['actual_float64_sha256']=sha(actual.astype('<f8').tobytes())
            if name=='silence':
                before['fullband_silence_peaks']=fullband_silence_peaks(oldactual)
                after['fullband_silence_peaks']=fullband_silence_peaks(actual)
            comparison=compare_reports(before,after)
            save(dest/'floor-diagnostics.json',before);save(dest/'centered-diagnostics.json',after)
            # No source bytes/guard/music are re-encoded or overwritten.
            assert sha(packed)==original_sha and (root/stage/name/'soundtrack.ima.gz').read_bytes()==packed_bytes
            row=dict(stage=stage,source=name,settings=SETTINGS,formula=FORMULA,model=model,
                source_samples=len(source),source_sha256=host['source_sha256'],packed_sha256=original_sha,
                saved_host_report_sha256=sha(host_bytes),same_frozen_encoded_bytes=True,
                pdm_rational_table_sha256=table_sha,pdm_table_unchanged=True,
                entire_original_source_preserved=True,source_specific_mapping=False,
                floor_fixed_clock=oldquality,centered_fixed_clock=quality,comparison=comparison,
                legacy_baseline_fixed_clock=host['baseline_fixed_clock'],
                changed_bucket_samples=int(np.count_nonzero(floor!=center)),
                upper_clamp_samples=int(np.count_nonzero((pcm.astype(np.int64)+32768+512)//1024==64)),
                floor_feedback_end_state=oldstate,centered_feedback_end_state=newstate,
                centered_reachable_states=sorted(map(int,np.unique(states))),
                floor_levels_sha256=sha(floor.tobytes()),centered_levels_sha256=sha(center.tobytes()),
                floor_pdm_bits_sha256=sha(oldbits.tobytes()),centered_pdm_bits_sha256=sha(newbits.tobytes()),
                complete_floor_reference_matches_independent_exact_recurrence=True,
                original_floor_output_matches_saved_renderer_exactly=True,
                deterministic_pulse_clock_sha256=sha(edges.astype('<f8').tobytes()),
                saturation_guard=guard,elapsed_seconds=time.perf_counter()-source_started,
                emulator_verified=False,new_c_optimized_payload=False,host_mapped_prediction=True,
                scope='Complete old encoded source; different fixedPCM16 bucket lookup on identical PDM table/clock. No source-specific settings, gain/delay/clock fitting or new execution.')
            if name=='silence':
                row['decoded_predictor_min_max']=[int(pcm.min()),int(pcm.max())]
                row['decoded_predictor_last128_before_guard']=pcm[-256:-128].astype(int).tolist()
            save(dest/'host.json',row);rows.append(row)
            print(json.dumps(dict(stage=stage,source=name,old_snr_db=oldquality['snr_db'],new_snr_db=quality['snr_db'],
                old_noise_rms=oldquality['error_rms'],new_noise_rms=quality['error_rms'],
                regressions=comparison['numeric_regressions'])),flush=True)
            save(out/'partial.json',report)
    report['complete']=tuple(stages)==STAGES and tuple(names)==NAMES
    totals={}
    for row in rows:
        bucket=totals.setdefault(row['stage'],dict(sources=0));bucket['sources']+=1
        for key,value in row['comparison']['numeric_regressions'].items():bucket[key]=bucket.get(key,0)+int(value)
    report['diagnostic_regression_counts']=totals
    report['attempt_wall_seconds']=time.perf_counter()-started
    report['cached_source_records']=cached;report['newly_mapped_sources']=len(rows)-cached
    report['sum_completed_source_seconds']=sum(row['elapsed_seconds'] for row in rows)
    report['decision']='Reject unconditional centered-LUT-only replacement on frozen floor-optimized payloads:all8 non-silent sources regress in both models. Midpoint silence confirms the negative-zero bin-discontinuity mechanism and removes the approximately1996-Hz line, but matched encoder re-optimization and actual execution are required before considering midpoint+centered lookup. No new disk or release is accepted.'
    report['producer_sha256_lf']={Path(__file__).name:sha(Path(__file__).read_bytes().replace(b'\r\n',b'\n'))}
    save(out/'report.json',report);return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence',type=Path);parser.add_argument('--output',type=Path)
    parser.add_argument('--scratch',type=Path,default=Path('.tmp/centered-quantizer'))
    parser.add_argument('--cache',type=Path,default=Path('.tmp'));parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    parser.add_argument('--source',action='append',choices=NAMES);parser.add_argument('--stage',action='append',choices=STAGES)
    parser.add_argument('--resume',action='store_true');parser.add_argument('--self-check',action='store_true')
    args=parser.parse_args()
    if args.self_check:print(json.dumps(self_check(),indent=2));return
    root=args.evidence.resolve();out=(args.output or root/'centered-quantizer').resolve()
    names=tuple(args.source or NAMES);stages=tuple(args.stage or STAGES)
    assert len(names)==len(set(names)) and len(stages)==len(set(stages))
    control(root,out,args.scratch.resolve(),args.cache.resolve(),stages,names,args.ffmpeg,args.resume)


if __name__=='__main__':main()
