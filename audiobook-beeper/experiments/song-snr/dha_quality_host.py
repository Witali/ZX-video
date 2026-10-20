"""One bounded bridge2 pilot: original model and rate_penalty82 ->0 only."""
import argparse
import ctypes as ct
import gzip
import json
from pathlib import Path
import subprocess
import time

import numpy as np

from dha_bridge2_pilot import select_even, write_wav
from dha_common_host import run
from dha_host_probe import HERE, dll_validate, save, scan_packets, sha
import waveform_kernel


MODEL_SHA='70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f'
ANS_SHA='af7cef130c9edf04d1da1944678314a4cd5e2c7d6957ded64f0cc5f028fa7ce8'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/dha-bridge2-quality0-pilot')
    parser.add_argument('--scratch',type=Path,required=True)
    args=parser.parse_args();out=args.output.resolve();scratch=args.scratch.resolve()
    if out.exists():raise FileExistsError('Preserve trial evidence: '+str(out))
    out.mkdir(parents=True);scratch.mkdir(parents=True,exist_ok=True)
    old=HERE/'evidence/dha-bridge2-pilot'
    original=HERE/'evidence/dha-host'
    baseline=json.loads((old/'report.json').read_bytes())
    frozen={str(path):sha(path.read_bytes()) for path in (
        old/'manifest.json',old/'report.json',old/'coded-targets-pcm16.bin',old/'source-physical-pcm16.bin',
        original/'source-snapshot.json',original/'build.json')}
    coded=np.fromfile(old/'coded-targets-pcm16.bin','<i2')
    physical=np.fromfile(old/'source-physical-pcm16.bin','<i2')
    assert len(coded)==32768 and len(physical)==16384
    assert sha(coded.tobytes())==baseline['coded_targets_sha256']
    assert sha(physical.tobytes())==baseline['source_physical_sha256']
    np.testing.assert_array_equal(coded[::2],physical)
    old_file=(old/'audio.dhaf').read_bytes()
    model=old_file[32:1056]
    assert sha(model)==MODEL_SHA and sha(old_file[1056:1568])==ANS_SHA
    (out/'model.bin').write_bytes(model)
    for name in ('source-physical-pcm16.bin','coded-targets-pcm16.bin','source-physical.wav','coded-targets.wav'):
        (out/name).write_bytes((old/name).read_bytes())
    settings=dict(frame_samples=4096,beam_width=64,gain_candidates=8,lookahead=2,rate_penalty=0,allow_pcm_fallback=True)
    save(out/'configuration.json',dict(source='sea_foam',physical_rate_hz=8000,coded_helper_rate_hz=16000,
        physical_samples=16384,coded_samples=32768,model_sha256=MODEL_SHA,ANS_sha256=ANS_SHA,
        original_model_same_song25k_training_overlap_disclosed=True,
        only_change_vs_default_bridge='rate_penalty82 ->0',settings=settings,
        frozen_baseline_files=frozen,no_full_song_encoding=True,no_other_sweep=True))
    snapshot=original/'producer-source'
    source_manifest=json.loads((original/'source-snapshot.json').read_bytes())
    for relative,row in source_manifest['snapshot_files'].items():
        assert sha((snapshot/relative).read_bytes())==row['sha256']
    c_source=Path(__file__).with_suffix('.c')
    (out/c_source.name).write_bytes(c_source.read_bytes())
    sources=' '.join('"'+str(path)+'"' for path in [snapshot/'src'/name for name in ('dha_common.c','dha_decode.c','dha_encode.c')]+[out/c_source.name])
    includes='/I "'+str(snapshot/'include')+'" /I "'+str(snapshot/'src')+'" /DDHA_HAS_ENCODER=1 '
    command=waveform_kernel._command().replace('/LD /MT','/MT').replace('kernel.c',includes+sources).replace('/OUT:kernel.dll','/OUT:dha_quality_host.exe')
    started=time.perf_counter()
    built=subprocess.run(command,cwd=scratch,capture_output=True,timeout=120,creationflags=0x08000000)
    (out/'build.log').write_bytes(built.stdout+built.stderr)
    assert built.returncode==0,built.stdout+built.stderr
    executable=scratch/'dha_quality_host.exe'
    build=dict(command=command,returncode=built.returncode,elapsed_seconds=time.perf_counter()-started,
        executable_sha256=sha(executable.read_bytes()),C_source_sha256=sha(c_source.read_bytes()),
        original_pinned_library_unchanged=True)
    save(out/'build.json',build)
    encoded=out/'native'
    execution=run(executable,out/'model.bin',out/'coded-targets-pcm16.bin',encoded,'bridge2-quality0-pilot')
    raw=(encoded/'audio.dhaf').read_bytes();frames=scan_packets(raw,complete=True)
    assert sha(raw[32:1056])==MODEL_SHA and sha(raw[1056:1568])==ANS_SHA
    assert len(frames)==8 and sum(frame['samples'] for frame in frames)==32768
    decoded=np.fromfile(encoded/'decoded-pcm16.bin','<i2')
    dll=HERE.parents[2]/'.tmp/dha-host-scratch/build/dha_codec.dll'
    prior_build=json.loads((original/'build.json').read_bytes())
    assert sha(dll.read_bytes())==prior_build['builds']['dha_codec.dll']['sha256']
    external_decoded,info=dll_validate(dll,raw)
    assert info==dict(sample_rate=16000,channels=1,declared_samples=32768)
    np.testing.assert_array_equal(decoded,external_decoded)
    bridge_dll=HERE.parents[2]/'.tmp/dha-bridge2-pilot-scratch/bridge2.dll'
    bridge_proof=json.loads((old/'build-transform.json').read_bytes())
    assert sha(bridge_dll.read_bytes())==bridge_proof['DLL_sha256']
    bridge=ct.CDLL(str(bridge_dll))
    bridge.bridge2_select_even.argtypes=[ct.POINTER(ct.c_int16),ct.c_size_t,ct.POINTER(ct.c_int16)]
    bridge.bridge2_select_even.restype=ct.c_size_t
    selected=select_even(bridge,decoded)
    np.testing.assert_array_equal(selected,decoded[::2])
    assert len(selected)==16384
    progress=[json.loads(line) for line in (encoded/'frames.jsonl').read_text().splitlines()]
    assert len(progress)==len(frames)
    cursor=0
    for row,frame in zip(progress,frames):
        assert row['sequence']==frame['sequence'] and row['samples']==frame['samples']
        assert row['packet_bytes']==frame['packet_bytes'] and row['payload_bits']==frame['payload_bits']
        if frame['kind']=='PCM16':np.testing.assert_array_equal(decoded[cursor:cursor+frame['samples']],coded[cursor:cursor+frame['samples']])
        cursor+=frame['samples']
    (out/'audio.dhaf').write_bytes(raw)
    (out/'decoded-coded-pcm16.bin').write_bytes(decoded.tobytes())
    (out/'decoded-physical-pcm16.bin').write_bytes(selected.tobytes())
    write_wav(out/'decoded-coded.wav',decoded,16000)
    write_wav(out/'decoded-physical.wav',selected,8000)
    report=dict(complete=True,date='2026-10-19',source='sea_foam',
        scope='First16384 physical samples only; original model and lambda0 causal control; no whole-song encode',
        physical_samples=16384,coded_samples=32768,physical_rate_hz=8000,coded_helper_rate_hz=16000,
        physical_duration_seconds=2.048,decoded_physical_samples=len(selected),decoded_coded_samples=len(decoded),
        source_physical_sha256=sha(physical.tobytes()),coded_targets_sha256=sha(coded.tobytes()),
        decoded_physical_sha256=sha(selected.tobytes()),decoded_coded_sha256=sha(decoded.tobytes()),
        model_sha256=MODEL_SHA,ANS_sha256=ANS_SHA,settings=settings,
        default_model_trained_on_same_song_family=True,
        only_changed_search_parameter='rate_penalty82 ->0',
        old_DLL_matches_every_C_decoded_coded_sample=True,old_bridge_DLL_matches_Python_even_selection=True,
        all_helpers_and_headers_charged=True,all_source_physical_positions_retained_before_codec=True,
        file_bytes=len(raw),file_sha256=sha(raw),header_bytes=1572,frame_headers_bytes=32*len(frames),
        payload_bytes=sum(frame['payload_bytes'] for frame in frames),payload_bits=sum(frame['payload_bits'] for frame in frames),
        dha_frames=sum(frame['kind']=='DHA' for frame in frames),pcm16_fallback_frames=sum(frame['kind']=='PCM16' for frame in frames),
        frames=frames,bits_per_physical_sample=8*len(raw)/16384,
        original_default_bridge_file_bytes=baseline['file_bytes'],original_default_bridge_report_sha256=sha((old/'report.json').read_bytes()),
        no_source_clock_gain_delay_or_filter_fit=True,no_SNR_measurement=True,no_Z80_player_or_TRD_proof=True,
        encode_and_C_decode=execution,physical_hardware_tested=False,release_accepted=False)
    assert all(sha(Path(path).read_bytes())==digest for path,digest in frozen.items())
    save(out/'report.json',report)
    (out/'harness.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    artifacts=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            data=path.read_bytes();artifacts.append(dict(path=path.relative_to(out).as_posix(),bytes=len(data),sha256=sha(data)))
    save(out/'manifest.json',dict(files=len(artifacts),artifacts=artifacts))
    print(json.dumps(dict(complete=True,file_bytes=len(raw),dha_frames=report['dha_frames'],
        pcm16_fallback_frames=report['pcm16_fallback_frames'],encode_and_C_decode_seconds=execution['elapsed_seconds'],
        DLL_parity=True,even_selection_parity=True)),flush=True)


if __name__=='__main__':main()
