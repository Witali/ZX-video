"""Complete uniform16 host control using unmodified uniform8k IMA inputs.

Use canonical general/inputs IMA, not the old449-clock compensated payloads.
Native proof covers a residentPCM8 component; host C decoding here does not
prove concurrent IMA decoding, banks, boot, EOF or a complete player.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np

from build_pdm import CPU_CLOCK, write_wav
from ima_codec import decode, require_unclipped
from probe_reconstruction_error import wav8
from study import filtered, metrics
from table_pdm_uniform16 import model
import waveform_kernel

HERE=Path(__file__).resolve().parent
NAMES=('sea_foam','silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def bits(words):return ((words[:,None]>>np.arange(15,-1,-1,dtype='u2'))&1).astype('u1').ravel()


def invoke(binary,table,packed,work):
    work.mkdir(parents=True,exist_ok=True)
    (work/'input.ima').write_bytes(packed)
    command=[str(binary),str(table),str(work/'input.ima'),str(work/'words.u16'),str(work/'states.u8'),str(work/'decoded.pcm16')]
    started=time.perf_counter();result=subprocess.run(command,capture_output=True,check=True,creationflags=0x08000000)
    return (np.fromfile(work/'words.u16','<u2'),np.fromfile(work/'states.u8','u1'),
            np.fromfile(work/'decoded.pcm16','<i2'),dict(seconds=time.perf_counter()-started,
            returncode=result.returncode,statistics=json.loads(result.stdout)))


def manifest(folder):
    files=[]
    for path in sorted(folder.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            raw=path.read_bytes();files.append(dict(path=path.relative_to(folder).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(folder/'manifest.json',dict(files=files))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/table-pdm-uniform16-host-8k')
    parser.add_argument('--scratch',type=Path,required=True)
    parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg'))
    parser.add_argument('--reuse-words',type=Path,help='Authenticate and reuse complete C outputs; rerender only')
    parser.add_argument('--packed-dir',type=Path,help='Matched C encodes, each SOURCE/packed.ima.gz; original WAVs stay frozen')
    args=parser.parse_args();out=args.output.resolve();scratch=args.scratch.resolve()
    if out.exists():raise FileExistsError('Preserve completed/failed evidence: '+str(out))
    if args.reuse_words and args.packed_dir:raise ValueError('Use frozen output reuse or newly matched streams separately')
    out.mkdir(parents=True);scratch.mkdir(parents=True,exist_ok=True)
    words,nxt,states,_,_=model();table=np.empty((64,32,3),dtype='u1')
    table[:,:,0]=words&255;table[:,:,1]=words>>8;table[:,:,2]=nxt
    (out/'model.bin').write_bytes(table.tobytes())
    source=Path(__file__).with_suffix('.c');(out/'host.c').write_bytes(source.read_bytes())
    if args.reuse_words:
        prior=args.reuse_words.resolve()
        previous_manifest=json.loads((prior/'manifest.json').read_bytes())
        for record in previous_manifest['files']:
            raw=(prior/record['path']).read_bytes()
            assert len(raw)==record['bytes'] and sha(raw)==record['sha256']
        assert (prior/'model.bin').read_bytes()==table.tobytes()
        assert (prior/'host.c').read_bytes()==source.read_bytes()
        save(out/'reuse.json',dict(directory=str(prior),all_prior_artifacts_authenticated=True,
            manifest_sha256=sha((prior/'manifest.json').read_bytes()),
            C_model_and_source_unchanged=True,no_repeated_C_encoding=True,
            previous_clock_error='Unscaled Pentagon T were interpreted as3546900-Hz reference ticks; actual7917.1875Hz, incorrectly labelled8k.',
            corrected_reference_units_per_Pentagon_T=CPU_CLOCK/3584000,
            original_ref_hz=CPU_CLOCK,Pentagon_hz=3584000))
        (out/'build.json').write_bytes((prior/'build.json').read_bytes())
        binary=None
    else:
        command=waveform_kernel._command().replace('/LD /MT','/MT').replace('kernel.c','"'+str(out/'host.c')+'"').replace('/OUT:kernel.dll','/OUT:uniform16.exe')
        started=time.perf_counter();built=subprocess.run(command,cwd=scratch,capture_output=True,creationflags=0x08000000)
        (out/'build.log').write_bytes(built.stdout+built.stderr)
        assert built.returncode==0,built.stdout+built.stderr
        binary=scratch/'uniform16.exe'
        save(out/'build.json',dict(command=command,returncode=built.returncode,seconds=time.perf_counter()-started,executable_sha256=sha(binary.read_bytes())))
    # C state/output parity with every native-proved cell, plus the exact
    # retained whole trajectory. These are lookup checks, not a new Z80 run.
    native=HERE/'evidence/table-pdm-uniform16-component'
    native_source=(native/'trajectory-pcm8.bin').read_bytes()
    native_bits=np.frombuffer(gzip.decompress((native/'trajectory-bits.u8.gz').read_bytes()),'u1')
    state=16;reference=[]
    for value in native_source[:-1]:
        word=int(words[value>>2,state]);reference.extend((word>>shift)&1 for shift in range(15,-1,-1));state=int(nxt[value>>2,state])
    np.testing.assert_array_equal(np.array(reference,'u1'),native_bits)
    save(out/'native-parity.json',dict(samples=len(native_source)-1,outputs=len(native_bits),every_bit_exact=True,
        source_sha256=sha(native_source),bits_sha256=sha(native_bits.tobytes()),model_sha256=sha(table.tobytes()),
        scope='Independent host table replay of retained native outputs; C complete source parity checked below'))
    rows=[];start=time.perf_counter()
    for name in NAMES:
        destination=out/name;destination.mkdir();work=scratch/name;work.mkdir(exist_ok=True)
        source_path=HERE/'evidence/general/inputs'/(name+'.wav')
        packed_path=(args.packed_dir.resolve()/name/'packed.ima.gz') if args.packed_dir else source_path.with_suffix('.ima.gz')
        source_values=wav8(source_path).astype('u1');packed=gzip.decompress(packed_path.read_bytes())
        if args.packed_dir:
            matching=json.loads((packed_path.parent/'report.json').read_bytes())
            assert matching['source_sha256']==sha(source_values.tobytes())
        guard=require_unclipped(packed);wanted_pcm,_=decode(packed)
        if args.reuse_words:
            before=json.loads((prior/name/'report.json').read_bytes())
            assert before['source_PCM8_sha256']==sha(source_values.tobytes()) and before['frozen_uniform_IMA_sha256']==sha(packed)
            actual_words=np.frombuffer(gzip.decompress((prior/name/'words.u16.gz').read_bytes()),'<u2')
            actual_states=np.frombuffer(gzip.decompress((prior/name/'states.u8.gz').read_bytes()),'u1')
            actual_pcm=wanted_pcm
            assert sha(actual_pcm.astype('<i2').tobytes())==before['decoded_PCM16_sha256']
            execution=dict(reused=True,previous_execution=before['execution'],returncode=0,seconds=0.)
        else:
            actual_words,actual_states,actual_pcm,execution=invoke(binary,out/'model.bin',packed,work)
        np.testing.assert_array_equal(actual_pcm,wanted_pcm);assert len(actual_pcm)==len(source_values)
        state=16;expected_words=[];expected_states=[]
        for value in actual_pcm:
            level=(int(value)+32768)>>10;expected_words.append(int(words[level,state]));state=int(nxt[level,state]);expected_states.append(state)
        np.testing.assert_array_equal(actual_words,np.array(expected_words,'u2'))
        np.testing.assert_array_equal(actual_states,np.array(expected_states,'u1'))
        # study.filtered accepts Spectrum-reference ticks, not native Pentagon
        # CPU ticks. Convert once using physical clocks; this is not a fitted
        # rate.16 equal decisions make the same canonical8k sample boundaries.
        sample_period=CPU_CLOCK/8000
        pulses=bits(actual_words);times=np.arange(len(pulses)+1,dtype='f8')*(sample_period/16)
        sample_times=np.arange(len(source_values)+1,dtype='f8')*sample_period
        assert times[-1]==sample_times[-1]
        reference=filtered(source_values/256,sample_times,args.ffmpeg,work)
        ideal=filtered((actual_pcm.astype('f8')+32768)/65536,sample_times,args.ffmpeg,work)
        actual=filtered(pulses,times,args.ffmpeg,work)
        report=dict(complete=True,source=name,samples=len(source_values),source_clock_hz=8000,
            source_PCM8_sha256=sha(source_values.tobytes()),source_WAV_sha256=sha(source_path.read_bytes()),
            frozen_uniform_IMA_sha256=sha(packed),IMA_bytes=len(packed),saturation_guard=guard,
            decoded_PCM16_sha256=sha(actual_pcm.tobytes()),C_decoder_and_all_words_and_states_match_Python=True,
            outputs=len(pulses),every_host_hold_tstates=28,sample_period_tstates=448,
            native_Pentagon_hz=3584000,render_reference_hz=CPU_CLOCK,
            reference_ticks_per_sample=sample_period,reference_ticks_per_pulse=sample_period/16,
            SNR=dict(total=metrics(reference,actual),modulator=metrics(ideal,actual),ideal_IMA=metrics(reference,ideal)),
            execution=execution,encoded_for_this_player=bool(args.packed_dir),
            packed_input_path=str(packed_path),
            source_clock_gain_delay_filter_or_edges_fitted=False,
            scope='Entire canonical uniform8k frozen IMA, native-matched table on a flat uniform clock. This is a host counterfactual, not integrated IMA/native banked/Fuse playback.',
            release_accepted=False)
        for label,signal in (('actual',actual),('source',reference),('ideal',ideal)):
            np.save(work/(label+'.npy'),signal)
        (destination/'words.u16.gz').write_bytes(gzip.compress(actual_words.astype('<u2').tobytes(),mtime=0))
        (destination/'states.u8.gz').write_bytes(gzip.compress(actual_states.tobytes(),mtime=0))
        write_wav(destination/'PDM.wav',actual*.5)
        save(destination/'report.json',report);rows.append(report)
        save(out/'partial.json',dict(complete=False,rows=rows))
        print(json.dumps(dict(source=name,total_SNR=report['SNR']['total']['snr_db'],PDM_SNR=report['SNR']['modulator']['snr_db'],seconds=execution['seconds'])),flush=True)
    save(out/'report.json',dict(complete=True,date='2026-10-20',source_count=len(rows),
        samples=sum(row['samples'] for row in rows),rows=rows,host_total_seconds=time.perf_counter()-start,
        all_sources_complete=True,uniform_IMA_frozen_no_joint_reencoding=not bool(args.packed_dir),
        model_sha256=sha(table.tobytes()),release_accepted=False))
    for path in (Path(__file__),source,HERE/'table_pdm_uniform16.py',HERE/'study.py'):
        target=out/'producer-source'/(path.name+'.gz');target.parent.mkdir(exist_ok=True)
        target.write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    manifest(out)


if __name__=='__main__':main()
