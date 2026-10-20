"""One bounded default-DHA trial with midpoint helper targets charged in full.

This is an internal codec representation: physical PCM remains 8 kHz and
every original sample is retained at an even coded position. The 16-kHz DHAF
header describes the helper lattice, not a new quality reference or bandwidth.
Only the first 16,384 physical samples are encoded by this pilot.
"""
import argparse
import ctypes as ct
import gzip
import json
import os
from pathlib import Path
import subprocess
import time
import wave

import numpy as np

from dha_host_probe import HERE, dll_validate, run_cli, save, scan_packets, sha
import waveform_kernel


def write_wav(path, pcm, rate):
    with wave.open(str(path), 'wb') as file:
        file.setnchannels(1); file.setsampwidth(2); file.setframerate(rate)
        file.writeframes(pcm.astype('<i2').tobytes())


def build_transform(scratch, out):
    source = Path(__file__).with_suffix('.c')
    frozen = out / source.name
    frozen.write_bytes(source.read_bytes())
    command = waveform_kernel._command()
    if os.name != 'nt' or not isinstance(command, str):
        raise RuntimeError('This harness requires the installed MSVC toolchain')
    command = command.replace('kernel.c', '"' + str(frozen) + '"')
    command = command.replace('/OUT:kernel.dll', '/OUT:bridge2.dll')
    started = time.perf_counter()
    result = subprocess.run(command, cwd=scratch, capture_output=True,
                            timeout=120, creationflags=0x08000000)
    (out / 'build-transform.log').write_bytes(result.stdout + result.stderr)
    assert result.returncode == 0, result.stderr
    binary = scratch / 'bridge2.dll'
    save(out / 'build-transform.json', dict(command=command,
        elapsed_seconds=time.perf_counter()-started, returncode=result.returncode,
        source_sha256=sha(frozen.read_bytes()), DLL_sha256=sha(binary.read_bytes())))
    library = ct.CDLL(str(binary))
    for name in ('bridge2_transform', 'bridge2_select_even'):
        fn = getattr(library, name)
        fn.argtypes = [ct.POINTER(ct.c_int16), ct.c_size_t, ct.POINTER(ct.c_int16)]
        fn.restype = ct.c_size_t
    return library


def transform(library, pcm):
    pcm = np.ascontiguousarray(pcm, dtype='<i2')
    result = np.empty(2 * len(pcm), dtype='<i2')
    assert library.bridge2_transform(pcm.ctypes.data_as(ct.POINTER(ct.c_int16)),
        len(pcm), result.ctypes.data_as(ct.POINTER(ct.c_int16))) == len(result)
    return result


def select_even(library, coded):
    assert len(coded) % 2 == 0
    coded = np.ascontiguousarray(coded, dtype='<i2')
    result = np.empty(len(coded)//2, dtype='<i2')
    assert library.bridge2_select_even(coded.ctypes.data_as(ct.POINTER(ct.c_int16)),
        len(result), result.ctypes.data_as(ct.POINTER(ct.c_int16))) == len(result)
    return result


def reference(pcm):
    integer = pcm.astype(np.int32)
    after = np.concatenate((integer[1:], integer[-1:]))
    sums = integer + after
    half = np.where(sums < 0, -((-sums)//2), sums//2)
    result = np.empty(2*len(pcm), dtype='<i2')
    result[0::2] = pcm; result[1::2] = half
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'evidence/dha-bridge2-pilot')
    parser.add_argument('--scratch', type=Path, required=True)
    parser.add_argument('--build', type=Path, required=True)
    args = parser.parse_args(); out = args.output.resolve(); scratch = args.scratch.resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty directory; preserve previous trial evidence')
    out.mkdir(parents=True, exist_ok=True); scratch.mkdir(parents=True, exist_ok=True)
    baseline = HERE/'evidence/dha-host'
    first = baseline/'sea_foam'
    build = json.loads((baseline/'build.json').read_bytes())
    cli = args.build.resolve()/'dha.exe'; dll = args.build.resolve()/'dha_codec.dll'
    for binary in (cli, dll):
        assert sha(binary.read_bytes()) == build['builds'][binary.name]['sha256']
    frozen = {name: sha((baseline/name).read_bytes()) for name in
        ('manifest.json', 'source-snapshot.json', 'sea_foam/report.json')}
    save(out/'configuration.json', dict(source='sea_foam', physical_rate_hz=8000,
        coded_helper_rate_hz=16000, pilot_physical_samples=16384,
        representation='coded[2*i]=source[i]; coded[2*i+1]=(source[i]+source[min(i+1,N-1)])/2',
        midpoint_rounding='C99 signed division truncates toward zero; all actual source sums even',
        settings=dict(frame_samples=4096, beam_width=64, gain_candidates=8,
                      lookahead=2, rate_penalty=82, allow_pcm_fallback=True),
        original_default_evidence=frozen,
        CLI_sha256=sha(cli.read_bytes()), DLL_sha256=sha(dll.read_bytes()),
        one_representation_no_parameter_sweep=True,
        default_model_same_song_training_overlap_disclosed=True))
    library = build_transform(scratch, out)
    vectors = [np.array([-32768], dtype='<i2'),
        np.array([-32768,32767,-3,0,-2,1,32767,-32768], dtype='<i2'),
        np.random.default_rng(802).integers(-32768,32768,10000,dtype=np.int16)]
    for pcm in vectors:
        coded = transform(library, pcm)
        np.testing.assert_array_equal(coded, reference(pcm))
        np.testing.assert_array_equal(select_even(library,coded), pcm)
    pcm = np.frombuffer((first/'source-pcm16.bin').read_bytes(), '<i2').copy()
    full = transform(library, pcm)
    np.testing.assert_array_equal(full, reference(pcm))
    np.testing.assert_array_equal(select_even(library,full), pcm)
    physical = pcm[:16384].copy(); coded = full[:32768].copy()
    assert np.all((pcm.astype(np.int32) + np.roll(pcm,-1).astype(np.int32)) % 2 == 0)
    # Transform the full source before slicing so the last pilot helper uses
    # source[16384], exactly as a later full-song representation would do.
    for name, data in [('source-physical-pcm16.bin',physical), ('coded-targets-pcm16.bin',coded)]:
        (out/name).write_bytes(data.astype('<i2').tobytes())
    write_wav(out/'source-physical.wav', physical, 8000)
    write_wav(out/'coded-targets.wav', coded, 16000)
    save(out/'transform-proof.json', dict(complete=True,
        native_independent_reference_vectors=len(vectors), random_samples=10000,
        entire_source_samples=len(pcm), entire_coded_samples=len(full),
        entire_physical_pcm16_sha256=sha(pcm.tobytes()),
        entire_coded_pcm16_sha256=sha(full.tobytes()),
        full_C_even_decimation_restores_original_exactly=True,
        every_original_sample_retained=True,
        pilot_original_sha256=sha(physical.tobytes()),
        pilot_transformed_sha256=sha(coded.tobytes()),
        pilot_even_sha256=sha(select_even(library,coded).tobytes()),
        last_pilot_helper_uses_next_full_source_sample=True,
        exact_midpoint_on_actual_source=True))
    print(json.dumps(dict(stage='encode_start', physical_samples=len(physical),
        coded_samples=len(coded), original_source_preserved=True)), flush=True)
    encode,_ = run_cli(cli,['encode',out/'coded-targets.wav',out/'audio.dhaf'],out,
                      'encode', monitor=True,total_samples=len(coded))
    info,info_text = run_cli(cli,['info',out/'audio.dhaf'],out,'info')
    decode,_ = run_cli(cli,['decode',out/'audio.dhaf',out/'decoded-coded.wav'],out,'decode')
    raw=(out/'audio.dhaf').read_bytes(); frames=scan_packets(raw,complete=True)
    assert len(frames)==8 and sum(frame['samples'] for frame in frames)==len(coded)
    with wave.open(str(out/'decoded-coded.wav'),'rb') as file:
        assert (file.getframerate(),file.getnchannels(),file.getsampwidth(),file.getnframes())==(16000,1,2,len(coded))
        decoded=np.frombuffer(file.readframes(file.getnframes()),'<i2').copy()
    dll_pcm,dll_info=dll_validate(dll,raw); np.testing.assert_array_equal(decoded,dll_pcm)
    physical_decoded=select_even(library,decoded)
    np.testing.assert_array_equal(physical_decoded,decoded[0::2])
    assert len(physical_decoded)==len(physical)
    (out/'decoded-coded-pcm16.bin').write_bytes(decoded.tobytes())
    (out/'decoded-physical-pcm16.bin').write_bytes(physical_decoded.tobytes())
    write_wav(out/'decoded-physical.wav',physical_decoded,8000)
    direct=json.loads((first/'report.json').read_bytes())
    old=direct['frames'][:4]
    direct_prefix_bytes=1572+sum(frame['packet_bytes'] for frame in old)
    assert sum(frame['samples'] for frame in old)==len(physical)
    counts=dict(dha_frames=sum(frame['kind']=='DHA' for frame in frames),
        pcm16_fallback_frames=sum(frame['kind']=='PCM16' for frame in frames))
    report=dict(complete=True,date='2026-10-19',source='sea_foam',
        scope='First16384 physical samples only; full-song encoding not launched',
        physical_samples=len(physical),coded_samples=len(coded),physical_rate_hz=8000,
        coded_helper_rate_hz=16000,physical_duration_seconds=len(physical)/8000,
        decoded_physical_samples=len(physical_decoded),decoded_coded_samples=len(decoded),
        source_physical_sha256=sha(physical.tobytes()), coded_targets_sha256=sha(coded.tobytes()),
        decoded_physical_sha256=sha(physical_decoded.tobytes()), decoded_coded_sha256=sha(decoded.tobytes()),
        input_all_original_samples_exactly_retained_before_lossy_codec=True,
        no_new_audio_rate_quality_reference=True,no_gain_or_listening_filter_changed=True,
        file_bytes=len(raw),file_sha256=sha(raw),header_bytes=1572,
        frame_headers_bytes=32*len(frames),payload_bytes=sum(frame['payload_bytes'] for frame in frames),
        all_helper_payload_and_header_bytes_charged=True,**counts,frames=frames,
        bits_per_physical_sample=8*len(raw)/len(physical),
        ratio_to_physical_PCM16=len(raw)/(2*len(physical)),
        direct_default_same_prefix=dict(physical_samples=len(physical),charged_file_header_bytes=1572,
            file_header_plus_first4_packet_bytes=direct_prefix_bytes,
            dha_frames=sum(frame['kind']=='DHA' for frame in old),
            pcm16_fallback_frames=sum(frame['kind']=='PCM16' for frame in old),
            derived_from_complete_frozen_default_song=True),
        estimated_full_song=dict(physical_samples=len(pcm),coded_samples=len(full),
            encode_seconds=encode['elapsed_seconds']*len(pcm)/len(physical),
            file_bytes=1572+(len(raw)-1572)*len(pcm)/len(physical),
            caveat='Pilot extrapolation only: content/fallback may change both runtime and storage'),
        CLI_info_validated=True,DLL_every_decoded_sample_matches_CLI=True,
        DLL_stream_info=dll_info,encode=encode,info=info,decode=decode,
        model_sha256=sha(raw[32:1056]),ANS_sha256=sha(raw[1056:1568]),
        default_model_trained_on_same_song_family=True,
        no_SNR_measurement=True,no_Z80_player_or_disk_proof=True,
        physical_hardware_tested=False,release_accepted=False)
    save(out/'report.json',report)
    assert all(sha((baseline/name).read_bytes())==value for name,value in frozen.items())
    (out/'harness.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    artifacts=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            data=path.read_bytes();artifacts.append(dict(path=path.relative_to(out).as_posix(),bytes=len(data),sha256=sha(data)))
    save(out/'manifest.json',dict(files=len(artifacts),artifacts=artifacts))
    print(json.dumps(dict(complete=True,file_bytes=len(raw),**counts,
        encode_seconds=encode['elapsed_seconds'],estimated_full=report['estimated_full_song'])),flush=True)


if __name__=='__main__':main()
