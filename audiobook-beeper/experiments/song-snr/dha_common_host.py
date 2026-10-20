"""Compile/run the fixed C DHA adapter with one common 8-kHz model.

The pinned tester-library snapshot is shared read-only with the default trial.
No Python encoding, model refit, waveform transform or player port occurs.
"""
import argparse
import gzip
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np

from dha_host_probe import HERE, dll_validate, pcm_wav, save, scan_packets, sha
from probe_reconstruction_error import wav8
import waveform_kernel

MODEL_SHA='199a17a9967bfbb941099039f32a47192af8933faf37cf015047abb51bfb9a7b'
ANS_SHA='af7cef130c9edf04d1da1944678314a4cd5e2c7d6957ded64f0cc5f028fa7ce8'
NAMES=('sea_foam','silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer')


def build(snapshot,scratch,out):
    scratch.mkdir(parents=True,exist_ok=True)
    source=Path(__file__).with_suffix('.c')
    core=[snapshot/'src'/name for name in ('dha_common.c','dha_decode.c','dha_encode.c')]
    sources=' '.join('"'+str(path)+'"' for path in core+[source])
    includes='/I "'+str(snapshot/'include')+'" /I "'+str(snapshot/'src')+'" /DDHA_HAS_ENCODER=1 '
    command=waveform_kernel._command().replace('/LD /MT','/MT').replace('kernel.c',includes+sources).replace('/OUT:kernel.dll','/OUT:dha_common_host.exe')
    started=time.perf_counter()
    result=subprocess.run(command,cwd=scratch,capture_output=True,timeout=120,creationflags=0x08000000)
    (out/'build.log').write_bytes(result.stdout+result.stderr)
    assert result.returncode==0,result.stdout+result.stderr
    executable=scratch/'dha_common_host.exe'
    record=dict(command=command,returncode=result.returncode,elapsed_seconds=time.perf_counter()-started,
        executable_sha256=sha(executable.read_bytes()),adapter_sha256=sha(source.read_bytes()),
        compiler='Installed MSVC x64 /O2 /std:c11 /fp:strict /MT',
        pinned_snapshot='../../dha-host/producer-source',original_library_unchanged=True)
    save(out/'build.json',record)
    return executable,record


def run(executable,model,source,folder,label):
    folder.mkdir(parents=True)
    command=list(map(str,(executable,model,source,folder/'audio.dhaf',folder/'decoded-pcm16.bin',folder/'frames.jsonl')))
    started=time.perf_counter()
    stdout=open(folder/'stdout.jsonl','wb');stderr=open(folder/'stderr.txt','wb')
    process=subprocess.Popen(command,stdout=stdout,stderr=stderr,creationflags=0x08000000)
    save(folder/'job.json',dict(command=command,pid=process.pid,started=True))
    last=0
    while process.poll() is None:
        elapsed=time.perf_counter()-started
        if elapsed-last>=10:
            lines=(folder/'frames.jsonl').read_text().splitlines() if (folder/'frames.jsonl').exists() else []
            completed=json.loads(lines[-1]) if lines else None
            print(json.dumps(dict(source=label,elapsed_seconds=elapsed,progress=completed)),flush=True)
            last=elapsed
        time.sleep(.2)
    stdout.close();stderr.close()
    result=dict(command=command,returncode=process.returncode,elapsed_seconds=time.perf_counter()-started)
    save(folder/'run.json',result)
    assert process.returncode==0,(folder/'stderr.txt').read_text()
    return result


def validate(folder,source,model,dll):
    raw=(folder/'audio.dhaf').read_bytes()
    assert sha(raw[32:1056])==sha(model) and sha(raw[1056:1568])==ANS_SHA
    frames=scan_packets(raw,complete=True)
    decoded=np.frombuffer((folder/'decoded-pcm16.bin').read_bytes(),'<i2').copy()
    independently,dll_info=dll_validate(dll,raw)
    np.testing.assert_array_equal(decoded,independently)
    assert len(source)==len(decoded)==sum(row['samples'] for row in frames)
    rows=[json.loads(line) for line in (folder/'frames.jsonl').read_text().splitlines()]
    assert len(rows)==len(frames)
    cursor=0
    for reported,frame in zip(rows,frames):
        assert reported['sequence']==frame['sequence'] and reported['samples']==frame['samples']
        assert reported['packet_bytes']==frame['packet_bytes'] and reported['payload_bits']==frame['payload_bits']
        assert reported['kind']==(1 if frame['kind']=='DHA' else 0)
        if frame['kind']=='PCM16':np.testing.assert_array_equal(decoded[cursor:cursor+frame['samples']],source[cursor:cursor+frame['samples']])
        cursor+=frame['samples']
    pcm_wav(folder/'decoded.wav',decoded)
    return decoded,dict(file_bytes=len(raw),file_sha256=sha(raw),frames=frames,
        dha_frames=sum(row['kind']=='DHA' for row in frames),pcm16_fallback_frames=sum(row['kind']=='PCM16' for row in frames),
        payload_bits=sum(row['payload_bits'] for row in frames),payload_bytes=sum(row['payload_bytes'] for row in frames),
        DLL_decode_matches_every_C_adapter_sample=True,DLL_stream_info=dll_info,
        all_PCM16_fallback_samples_exact=True,all_C_progress_rows_match_serialized_frames=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,default=HERE/'evidence/dha-common-model/model.bin')
    parser.add_argument('--output',type=Path,default=HERE/'evidence/dha-common-host')
    parser.add_argument('--scratch',type=Path,required=True)
    parser.add_argument('--source',action='append')
    args=parser.parse_args();out=args.output.resolve();scratch=args.scratch.resolve()
    if out.exists():raise FileExistsError('Preserve evidence: '+str(out))
    out.mkdir(parents=True)
    model=args.model.resolve().read_bytes();assert len(model)==1024 and sha(model)==MODEL_SHA
    (out/'model.bin').write_bytes(model)
    protocol=args.model.resolve().parent/'report.json'
    shutil.copyfile(protocol,out/'model-training.json')
    original=HERE/'evidence/dha-host';snapshot=original/'producer-source'
    source_manifest=json.loads((original/'source-snapshot.json').read_bytes())
    for relative,identity in source_manifest['snapshot_files'].items():
        assert sha((snapshot/relative).read_bytes())==identity['sha256']
    old_build=json.loads((original/'build.json').read_bytes())
    dll=HERE.parents[2]/'.tmp/dha-host-scratch/build/dha_codec.dll'
    assert sha(dll.read_bytes())==old_build['builds']['dha_codec.dll']['sha256']
    names=args.source or list(NAMES)
    assert len(names)==len(set(names)) and all(name in NAMES for name in names)
    configuration=dict(model_sha256=MODEL_SHA,ANS_sha256=ANS_SHA,
        model_training_report_sha256=sha(protocol.read_bytes()),
        pinned_source_manifest_sha256=sha((original/'source-snapshot.json').read_bytes()),
        old_library_DLL_sha256=sha(dll.read_bytes()),
        settings=dict(frame_samples=4096,beam_width=64,gain_candidates=8,lookahead=2,rate_penalty=82,allow_pcm_fallback=True),
        sources=names,only_codec_parameter_change='One common1024-byte model trained on speech+Entertainer8k, before holdout encoding',
        input_mapping='signedPCM16=(authenticatedPCM8-128)*256; no resampling/normalization/filter/content change')
    save(out/'configuration.json',configuration)
    executable,compiler=build(snapshot,scratch,out)
    rows=[]
    for name in names:
        folder=out/name;folder.mkdir()
        source_path=HERE/'evidence/general/inputs'/(name+'.wav')
        unsigned=wav8(source_path).astype('u1')
        source=((unsigned.astype(np.int32)-128)*256).astype('<i2')
        (folder/'source-preview.wav').write_bytes(source_path.read_bytes())
        (folder/'source-pcm16.bin').write_bytes(source.tobytes());pcm_wav(folder/'source-pcm16.wav',source)
        pilot=folder/'pilot-first-frame'
        pilot_source=folder/'pilot-pcm16.bin';pilot_source.write_bytes(source[:4096].tobytes())
        pilot_run=run(executable,out/'model.bin',pilot_source,pilot,name+'-pilot')
        _,pilot_result=validate(pilot,source[:4096],model,dll)
        save(pilot/'report.json',dict(complete=True,run=pilot_run,**pilot_result))
        print(json.dumps(dict(source=name,pilot_seconds=pilot_run['elapsed_seconds'],
            estimated_whole_seconds=pilot_run['elapsed_seconds']*((len(source)+4095)//4096),
            estimate_only=True)),flush=True)
        # The pilot uses its own packet; the full source is always encoded
        # afresh with identical settings and the complete declared length.
        full=folder/'full';full_run=run(executable,out/'model.bin',folder/'source-pcm16.bin',full,name)
        decoded,result=validate(full,source,model,dll)
        for filename in ('audio.dhaf','decoded-pcm16.bin','decoded.wav'):
            shutil.copyfile(full/filename,folder/filename)
        report=dict(complete=True,source=name,input_samples=len(source),decoded_samples=len(decoded),sample_rate_hz=8000,
            source_u8_sha256=sha(unsigned.tobytes()),source_pcm16_sha256=sha(source.tobytes()),
            source_wav_sha256=sha(source_path.read_bytes()),decoded_pcm16_sha256=sha(decoded.tobytes()),
            settings=configuration['settings'],model_sha256=MODEL_SHA,ANS_sha256=ANS_SHA,
            common_model_frozen_before_holdout=True,model_training_names=['speech','entertainer'],
            source_is_training_member=name in ('speech','entertainer'),
            adapter_compiler=compiler,pilot=pilot_run,encode_and_C_decode=full_run,
            container='DHAFv1 independent-frame host container; not Spectrum/player wire',
            no_source_gain_clock_delay_fit=True,no_SNR_measurement=True,no_Z80_or_TRD_proof=True,
            release_accepted=False,physical_hardware_tested=False,**result)
        save(folder/'report.json',report);rows.append(report)
        save(out/'partial.json',dict(complete=False,rows=rows))
        print(json.dumps(dict(source=name,complete=True,bytes=result['file_bytes'],
            dha_frames=result['dha_frames'],fallback_frames=result['pcm16_fallback_frames'],
            encode_and_C_decode_seconds=full_run['elapsed_seconds'])),flush=True)
    save(out/'report.json',dict(complete=True,date='2026-10-19',configuration=configuration,rows=rows,
        C_library_search_and_packet_code_unchanged=True,only_common_model_changed=True,
        all_sources_whole_and_unscaled=True,no_SNR_or_Z80_player_claim=True,release_accepted=False))
    for path in (Path(__file__),Path(__file__).with_suffix('.c')):
        (out/(path.name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
    artifacts=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            raw=path.read_bytes();artifacts.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(files=len(artifacts),artifacts=artifacts))
    print(json.dumps(dict(complete=True,sources=names,files=len(artifacts))),flush=True)


if __name__=='__main__':main()
