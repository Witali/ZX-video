"""Frozen-IMA quality control for the native seven-uniform-hold mechanism.

Both controls use exactly448 T/sample, seven64-T pulse holds and accumulator
32767. Full16 mirrors the native CPU; floor6 changes only input precision on
the same clock. No bank/page delay, EOF, ULA, boot, new encoder or optimization
is simulated. Complete host results are not an integrated player acceptance.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import time
import uuid

import numpy as np

from artifact_diagnostics import compare_reports, tone_diagnostics, waveform_diagnostics
from build_pdm import CPU_CLOCK, write_wav
from convert_mulaw_audio import STABLE_FILTER
from ima_codec import decode
from pacing448_spectrum import spectrum
from probe_reconstruction_error import wav8
from study import filtered, metrics, uniform
import waveform_kernel


HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
SOURCE=HERE/'sdm16_uniform7_host.c'
NAMES=('sea_foam','silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer')
LONG_NAMES=('long_silence','long_quiet997')
FREQUENCIES=(8000/32768,2.,5.,10.,8000/512,25.,50.,8000/128,100.,8000/64)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def producer_files():
    names=('sdm16_uniform7_host.py','sdm16_uniform7_host.c','sdm16_uniform7.py',
           'artifact_diagnostics.py','pacing448_spectrum.py','study.py')
    files={'experiments/song-snr/'+name:HERE/name for name in names}
    for name in ('ima_codec.py','probe_reconstruction_error.py','convert_mulaw_audio.py',
                 'assess_snr.py','build_pdm.py','waveform_kernel.py'):
        files[name]=AUDIO/name
    return files


def build_executable():
    command=waveform_kernel._command()
    if command is None:raise RuntimeError('An installed C compiler is required')
    if os.name=='nt':
        if not isinstance(command,str) or '/LD /MT' not in command:
            raise RuntimeError('Need the installed strict MSVC command')
        command=command.replace('/LD /MT','/MT').replace('/OUT:kernel.dll','/OUT:kernel.exe')
        binary_name='kernel.exe'
    else:
        command=[shutil.which('cc'),'-O3','-std=c99','-fno-fast-math','kernel.c','-o','kernel']
        binary_name='kernel'
    key=sha(SOURCE.read_bytes()+repr(command).encode()+platform.machine().encode())[:24]
    cache=AUDIO/'.native-cache'/('uniform7-host-'+key);binary=cache/binary_name
    if not binary.exists():
        private=cache/('build-'+uuid.uuid4().hex);private.mkdir(parents=True)
        (private/'kernel.c').write_bytes(SOURCE.read_bytes())
        result=subprocess.run(command,cwd=private,capture_output=True,timeout=120,
            creationflags=0x08000000 if os.name=='nt' else 0)
        (private/'build.log').write_bytes(result.stdout+result.stderr)
        if result.returncode or not (private/binary_name).exists():
            raise RuntimeError('Uniform7 C compiler failed: '+str(private/'build.log'))
        try:(private/binary_name).rename(binary)
        except FileExistsError:pass
    return binary


def execute(binary,mode,pcm_file,words_file,states_file,initial=32767):
    result=subprocess.run([str(binary),mode,str(pcm_file),str(words_file),str(states_file),
        'uniform7x64',str(initial)],capture_output=True,text=True,
        creationflags=0x08000000 if os.name=='nt' else 0)
    if result.returncode:raise RuntimeError(('Uniform7 C failed',result.returncode,result.stderr))
    words=np.fromfile(words_file,'u1');states=np.fromfile(states_file,'<u2')
    assert len(words)==len(states) and np.all(words<128)
    return words,states,json.loads(result.stdout)


def bits_of(words):
    return ((words[:,None]>>np.arange(6,-1,-1,dtype=np.uint8))&1).astype('u1').ravel()


def parity(binary,evidence,output,scratch):
    native_dir=evidence/'sdm16-uniform7';native=json.loads((native_dir/'report.json').read_bytes())['uniform7']
    packed=(native_dir/'uniform7/trajectory.ima').read_bytes();pcm,_=decode(packed)
    raw=pcm.astype('<i2').tobytes();(scratch/'parity-pcm16.bin').write_bytes(raw)
    words,states,statistics=execute(binary,'full16',scratch/'parity-pcm16.bin',scratch/'parity-words.bin',scratch/'parity-states.bin')
    actual_bits=np.frombuffer(gzip.decompress((native_dir/'uniform7/trajectory-bits.u8.gz').read_bytes()),'u1')
    actual_times=np.frombuffer(gzip.decompress((native_dir/'uniform7/trajectory-times.u32.gz').read_bytes()),'<u4')
    samples=native['reference_trajectory']['samples']
    np.testing.assert_array_equal(bits_of(words[:samples]),actual_bits)
    assert len(actual_bits)==samples*7 and np.all(np.diff(actual_times.astype(np.int64))==64)
    assert int(states[samples-1])==native['reference_trajectory']['final_accumulator']
    cases=[]
    # Reuse the saved actual native extreme and one-LSB runs, with their own
    # explicit accumulators; these special seeds never enter quality scoring.
    for row in native['extreme_vectors']+native['one_LSB_output_witness']:
        value=row.get('unsigned_pcm16',row.get('signed_pcm16',0)+32768)
        report=row['report'];count=report['samples']
        initial=32767 if 'unsigned_pcm16' in row else 65536-(32768+38)
        np.full(count,value-32768,dtype='<i2').tofile(scratch/'vector-pcm16.bin')
        w,s,stat=execute(binary,'full16',scratch/'vector-pcm16.bin',scratch/'vector-words.bin',scratch/'vector-states.bin',initial)
        np.testing.assert_array_equal(bits_of(w),np.array(report['bits_values'],dtype='u1'))
        assert int(s[-1])==report['final_accumulator']
        cases.append(dict(unsigned_pcm16=value,initial_accumulator=initial,samples=count,
            actual_native_bits_match=True,final_accumulator=int(s[-1])))
    # Independent integer recurrence checks the whole C stream, including the
    # two source-prefetch guards not included in the native trajectory run.
    state=32767;reference=[];states_reference=[]
    for value in pcm:
        word=0
        for _ in range(7):
            total=state+int(value)+32768;word=(word<<1)|(total>>16);state=total&65535
        reference.append(word);states_reference.append(state)
    np.testing.assert_array_equal(words,np.array(reference,dtype='u1'))
    np.testing.assert_array_equal(states,np.array(states_reference,dtype='<u2'))
    report=dict(complete=True,native_samples=samples,native_source_bits=len(actual_bits),
        every_actual_native_source_bit_matches_C=True,every_native_hold_tstates=64,
        native_first_OUT_tstates=int(actual_times[0]),first_OUT_origin_normalized_to_zero=True,
        native_bits_sha256=sha(actual_bits.tobytes()),native_times_sha256=sha(actual_times.tobytes()),
        native_kernel_sha256=sha((native_dir/'uniform7/kernel.bin').read_bytes()),
        complete_C_stream_integer_reference_parity=True,extreme_and_oneLSB_cases=cases,
        fixed_quality_accumulator=32767,statistics=statistics,
        native_scope='Ordinary flat one-bank CPU proof only. No banked/Fuse/source quality acceptance.')
    save(output/'parity.json',report)
    return report


def source_input(evidence,name):
    if name in NAMES:
        source_path=evidence/'general/inputs'/(name+'.wav')
        folder=evidence/'clock-joint'/name;host=json.loads((folder/'host.json').read_bytes())
        packed_path=folder/'soundtrack.ima.gz';expected_packed=host['packed_sha256']
        expected_source=host['source_sha256'];kind='Archived clock-joint449 stream; frozen, not optimized for uniform7'
    else:
        folder=evidence/'pacing448-control'/name;source_path=folder/'source-preview.wav'
        host=json.loads((folder/'host.json').read_bytes());packed_path=folder/'before449.ima.gz'
        expected_packed=host['variants']['before449']['packed_sha256'];expected_source=host['source_sha256']
        kind='Archived long before449 control; frozen, not optimized for uniform7'
    source=wav8(source_path).astype('u1');packed=gzip.decompress(packed_path.read_bytes())
    assert sha(source.tobytes())==expected_source and sha(packed)==expected_packed
    assert len(source)==2*len(packed)
    return source_path,source,packed_path,packed,dict(provenance=kind,
        archived_host_sha256=sha(json.dumps(host,sort_keys=True).encode()),
        source_sha256=expected_source,packed_sha256=expected_packed)


def run_source(name,evidence,output,scratch,binary,ffmpeg):
    started=time.perf_counter();path,source,packed_path,packed,identity=source_input(evidence,name)
    dest=output/name;dest.mkdir();local=scratch/name;local.mkdir(parents=True,exist_ok=True)
    (dest/'source-preview.wav').write_bytes(path.read_bytes())
    (dest/'soundtrack.ima.gz').write_bytes(packed_path.read_bytes())
    pcm,_=decode(packed);pcm.astype('<i2').tofile(local/'pcm16.bin')
    # Exact8-kHz source and56-kHz pulse clocks, expressed in the project's
    # renderer units. No bank/page term or fitted time/phase adjustment exists.
    times=np.arange(7*len(pcm)+1,dtype=np.int64)*64*(CPU_CLOCK/3584000)
    sample_edges=times[::7]
    decoded=filtered((pcm.astype(float)+32768)/65536,sample_edges,ffmpeg,local)
    values,edges=uniform(source/256.,times[-1]);original=filtered(values,edges,ffmpeg,local)
    write_wav(dest/'decoded-reference.wav',decoded*.5)
    write_wav(dest/'original-reference.wav',original*.5)
    np.save(local/'decoded-reference.npy',decoded);np.save(local/'original-reference.npy',original)
    controls={};diagnostics={}
    for mode in ('floor6','full16'):
        words,states,stat=execute(binary,mode,local/'pcm16.bin',local/(mode+'-words.bin'),local/(mode+'-states.bin'))
        assert len(words)==len(source) and stat['samples']==len(source)
        bits=bits_of(words);actual=filtered(bits,times,ffmpeg,local)
        fixed,pdm=metrics(original,actual),metrics(decoded,actual)
        diag=dict(source=name,variant=mode,
            waveform=waveform_diagnostics(original,actual,frequencies=FREQUENCIES),
            fullband_error_spectrum=spectrum(actual-original),pdm_error_spectrum=spectrum(actual-decoded),
            actual_float64_sha256=sha(actual.astype('<f8').tobytes()),
            original_float64_sha256=sha(original.astype('<f8').tobytes()),
            decoded_float64_sha256=sha(decoded.astype('<f8').tobytes()),
            bank_free_uniform_clock_counterfactual=True,emulator_quality_verified=False)
        base=name.removeprefix('long_')
        if base in ('quiet440','quiet997','loud3000'):
            diag['known_tone']=tone_diagnostics(original,actual,dict(quiet440=440,quiet997=997,loud3000=3000)[base],frequencies=FREQUENCIES)
        save(dest/(mode+'-diagnostics.json'),diag);diagnostics[mode]=diag
        (dest/(mode+'-words7.u8.gz')).write_bytes(gzip.compress(words.tobytes(),mtime=0))
        (dest/(mode+'-accumulators.u16le.gz')).write_bytes(gzip.compress(states.astype('<u2').tobytes(),mtime=0))
        write_wav(dest/(mode+'-actual.wav'),actual*.5);np.save(local/(mode+'-actual.npy'),actual)
        controls[mode]=dict(fixed_clock=fixed,pdm_only_decoded_ima16_diagnostic=pdm,
            statistics=stat,word_sha256=sha(words.tobytes()),accumulator_sha256=sha(states.astype('<u2').tobytes()),
            c_model_matches_native=mode=='full16',input_mapping='u' if mode=='full16' else 'u&0xFC00',
            pcm_samples=len(pcm),source_decisions=len(bits))
        print(json.dumps(dict(source=name,variant=mode,total_snr_db=fixed['snr_db'],
            pdm_snr_db=pdm['snr_db'],error_rms=fixed['error_rms'],bank_free_host_only=True)),flush=True)
    comparison=compare_reports(diagnostics['floor6'],diagnostics['full16'])
    report=dict(source=name,source_samples=len(source),**identity,source_file_sha256=sha(path.read_bytes()),
        decoded_pcm16_sha256=sha(pcm.astype('<i2').tobytes()),controls=controls,comparison=comparison,
        ideal_decoded_IMA16_control=metrics(original,decoded),source_8khz_frozen=True,
        original_IMA_nibbles_frozen=True,IMA_reoptimized_for_uniform7=False,
        source_gain_bandwidth_filter_edges_unchanged=True,elapsed_seconds=time.perf_counter()-started,
        scope='Whole source, pure uniform448T bank-free host model; original-source unfitted total and shared decodedIMA16 PDM diagnostic. No new physical bank clock or actual emulator audio-quality proof.',
        fitted_gain_delay_clock=False,physical_hardware_tested=False,release_accepted=False)
    save(dest/'host.json',report)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=HERE/'evidence')
    parser.add_argument('--output',type=Path,default=HERE/'evidence/sdm16-uniform7-host')
    parser.add_argument('--scratch',type=Path,required=True)
    parser.add_argument('--no-long',action='store_true')
    parser.add_argument('--source',action='append',choices=NAMES+LONG_NAMES)
    args=parser.parse_args();evidence=args.evidence.resolve();out=args.output.resolve();scratch=args.scratch.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be empty; preserve incomplete experiments')
    out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    files=producer_files();hashes={name:sha(path.read_bytes()) for name,path in files.items()}
    binary=build_executable();ffmpeg=Path(shutil.which('ffmpeg')).resolve()
    parity_report=parity(binary,evidence,out,scratch)
    configuration=dict(producer_sha256=hashes,executable=str(binary),executable_sha256=sha(binary.read_bytes()),
        ffmpeg=str(ffmpeg),ffmpeg_sha256=sha(ffmpeg.read_bytes()),initial_accumulator=32767,
        pulses_per_source_sample=7,uniform_hold_tstates=64,ordinary_period_tstates=448,
        physical_cpu_hz=3584000,source_rate_hz=8000,decision_rate_hz=56000,
        modes=['floor6','full16'],source_specific_parameters=False,
        listening_filter=STABLE_FILTER,integration_rate_hz=768000,edge_exclusion_seconds=.1,
        diagnostic_frequencies_hz=list(FREQUENCIES),gain_delay_clock_fit=False,
        bank_free_counterfactual=True,IMA_reoptimized=False,scope='Only full16 has native ordinary-kernel parity; floor6 is a matched host precision control')
    save(out/'configuration.json',configuration)
    for name,path in files.items():
        target=out/'producer-source'/(name+'.gz');target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    names=args.source or list(NAMES)+(list(LONG_NAMES) if not args.no_long else [])
    assert len(names)==len(set(names))
    rows=[]
    for name in names:
        rows.append(run_source(name,evidence,out,scratch,binary,ffmpeg))
        save(out/'partial.json',dict(complete=False,rows=rows))
        if hashes!={name:sha(path.read_bytes()) for name,path in files.items()}:
            raise RuntimeError('Frozen host/measurement producer changed during the run')
    regressions={}
    for row in rows:
        for key,value in row['comparison']['numeric_regressions'].items():regressions[key]=regressions.get(key,0)+value
    report=dict(complete=True,date='2026-10-19',sources=names,whole_original9_source_corpus=all(name in names for name in NAMES),
        long_bank_period_controls_included=all(name in names for name in LONG_NAMES),rows=rows,
        parity=parity_report,regression_counts=regressions,
        native_ordinary_bit_parity_does_not_prove_audio_quality=True,bank_free_uniform_clock_counterfactual=True,
        actual_banked_OUT_clock_verified=False,actual_emulator_quality_verified=False,
        physical_hardware_tested=False,release_accepted=False,
        decision='Assess full16 benefit against matched floor6 on the same uniform clock; original IMA paths are frozen and not optimality/ceiling evidence. Banked transport timing and complete actual-clock quality remain required before implementation or release.')
    save(out/'report.json',report)
    artifacts=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts:
            raw=path.read_bytes();artifacts.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(files=len(artifacts),artifacts=artifacts))
    print(json.dumps(dict(complete=True,sources=names,artifacts=len(artifacts),release_accepted=False)),flush=True)


if __name__=='__main__':main()
