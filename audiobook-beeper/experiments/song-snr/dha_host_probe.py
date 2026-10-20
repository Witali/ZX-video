"""Pin and exercise the unmodified external DHA C library on this corpus.

The external tester checkout is read-only. All compilation, files and reports
remain in ZX-video. DHAF is a host container, distinct from compiled Z80 wire.
This stage measures sizes, complete decoding and runtime, not filtered SNR.
"""
import argparse
import ctypes as ct
import gzip
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import time
import wave
import zlib

import numpy as np

from probe_reconstruction_error import wav8
import waveform_kernel


HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]


def sha(raw):return hashlib.sha256(raw).hexdigest()


def save(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def pin_source(tester,out):
    library=tester/'audio/lib/dha-codec';target=out/'producer-source';target.mkdir()
    relative=['CMakeLists.txt','README.md','FORMAT.md']
    for folder in ('include','src','tools','cmake'):
        relative += [path.relative_to(library).as_posix() for path in (library/folder).rglob('*')
                     if path.is_file() and path.suffix in ('.c','.h','.in')]
    relative += ['tests/'+name for name in ('test_codec.c','test_decode_only.c','test_trajectory.c','integration.py')]
    files={}
    for name in sorted(set(relative)):
        raw=(library/name).read_bytes();dest=target/name;dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(raw);files[name]=dict(bytes=len(raw),sha256=sha(raw))
    # A second read catches source changes during the snapshot itself. All
    # subsequent compiler and codec inputs refer exclusively to this copy.
    for name,record in files.items():assert sha((library/name).read_bytes())==record['sha256']
    docs={}
    for label,path in [('tester-AGENTS.md',tester/'AGENTS.md'),
        ('model-training-audio.md',tester/'audio/music/sea-foam/recorded-difference-history/src/audio.md')]:
        raw=path.read_bytes();(out/label).write_bytes(raw);docs[label]=sha(raw)
    manifest=dict(external_library_read_only=str(library),snapshot_files=files,provenance_documents=docs,
        source_model_provenance='The unchanged default1024-byte predictor tables were fitted on the selected15-second sea-foam25kHz trajectory. This same-source-family song trial does not establish source-independent quality.',
        expected_model_sha256='70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f',
        expected_ANS_sha256='af7cef130c9edf04d1da1944678314a4cd5e2c7d6957ded64f0cc5f028fa7ce8')
    save(out/'source-snapshot.json',manifest)
    return target,manifest


def compile_tools(snapshot,scratch,out):
    scratch.mkdir(parents=True,exist_ok=True)
    command=waveform_kernel._command()
    if os.name!='nt' or not isinstance(command,str) or '/LD /MT' not in command:
        raise RuntimeError('This pinned integration harness currently requires the installed MSVC x64 toolchain')
    core=[snapshot/'src'/name for name in ('dha_common.c','dha_decode.c','dha_encode.c')]
    sources=' '.join('"'+str(path)+'"' for path in core)
    includes='/I "'+str(snapshot/'include')+'" /I "'+str(snapshot/'src')+'" /DDHA_HAS_ENCODER=1 '
    commands={}
    builds=[('dha_codec.dll',sources,True),('dha.exe',sources+' "'+str(snapshot/'tools/dha.c')+'"',False)]
    for test in ('test_decode_only','test_codec','test_trajectory'):
        builds.append((test+'.exe',sources+' "'+str(snapshot/'tests'/(test+'.c'))+'"',False))
    for filename,source_list,dll in builds:
        current=command.replace('kernel.c',includes+('/DDHA_SHARED /DDHA_BUILDING ' if dll else '')+source_list)
        if not dll:current=current.replace('/LD /MT','/MT')
        current=current.replace('/OUT:kernel.dll','/OUT:'+filename)
        started=time.perf_counter()
        result=subprocess.run(current,cwd=scratch,capture_output=True,timeout=120,creationflags=0x08000000)
        (out/('build-'+filename+'.log')).write_bytes(result.stdout+result.stderr)
        if result.returncode or not (scratch/filename).exists():raise RuntimeError('DHA build failed: '+filename)
        commands[filename]=dict(command=current,returncode=result.returncode,
            elapsed_seconds=time.perf_counter()-started,sha256=sha((scratch/filename).read_bytes()))
    tests=[]
    for test in ('test_decode_only','test_codec','test_trajectory'):
        started=time.perf_counter();result=subprocess.run([str(scratch/(test+'.exe'))],cwd=scratch,
            capture_output=True,timeout=180,creationflags=0x08000000)
        (out/(test+'.log')).write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,(test,result.returncode,result.stdout,result.stderr)
        tests.append(dict(test=test,passed=True,elapsed_seconds=time.perf_counter()-started))
    save(out/'build.json',dict(complete=True,compiled_from_pinned_copy=True,
        compiler='Installed MSVC x64, /O2 /std:c11 /fp:strict /MT',builds=commands,tests=tests))
    return scratch/'dha.exe',scratch/'dha_codec.dll'


def pcm_wav(path,pcm):
    with wave.open(str(path),'wb') as file:
        file.setnchannels(1);file.setsampwidth(2);file.setframerate(8000);file.writeframes(pcm.astype('<i2').tobytes())


def scan_packets(raw,*,complete):
    if len(raw)<1572:return []
    assert raw[:4]==b'DHAF';at=1572;rows=[]
    while at+32<=len(raw):
        assert raw[at:at+4]==b'DHF1';size=struct.unpack_from('<I',raw,at+4)[0]
        if at+size>len(raw):break
        packet=raw[at:at+size];bits=struct.unpack_from('<I',packet,24)[0]
        crc=zlib.crc32(packet[:28]+packet[32:])&0xFFFFFFFF
        assert crc==struct.unpack_from('<I',packet,28)[0]
        sequence=struct.unpack_from('<I',packet,8)[0];samples=struct.unpack_from('<H',packet,12)[0]
        assert packet[14]==0 and sequence==len(rows)
        rows.append(dict(sequence=sequence,file_offset=at,packet_bytes=size,samples=samples,
            kind='DHA' if packet[15]==1 else 'PCM16',payload_bits=bits,payload_bytes=size-32))
        at+=size
    if complete:assert at==len(raw),('trailing/incomplete packet',at,len(raw))
    return rows


def run_cli(cli,arguments,dest,label,*,monitor=False,total_samples=None):
    started=time.perf_counter();command=[str(cli)]+list(map(str,arguments))
    if monitor:
        process=subprocess.Popen(command,cwd=cli.parent,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=0x08000000)
        save(dest/(label+'-job.json'),dict(pid=process.pid,command=command,started=True))
        last=0
        while process.poll() is None:
            elapsed=time.perf_counter()-started
            if elapsed-last>=10:
                path=Path(arguments[2]);rows=scan_packets(path.read_bytes(),complete=False) if path.exists() else []
                completed=sum(row['samples'] for row in rows)
                print(json.dumps(dict(stage=label,completed_frames=len(rows),completed_samples=completed,
                    elapsed_seconds=elapsed,estimated_remaining_seconds=(elapsed*(total_samples-completed)/completed if completed else None))),flush=True)
                last=elapsed
            time.sleep(.5)
        stdout,stderr=process.communicate();code=process.returncode
    else:
        result=subprocess.run(command,cwd=cli.parent,capture_output=True,creationflags=0x08000000)
        stdout,stderr,code=result.stdout,result.stderr,result.returncode
    (dest/(label+'-stdout.txt')).write_bytes(stdout);(dest/(label+'-stderr.txt')).write_bytes(stderr)
    record=dict(command=command,returncode=code,elapsed_seconds=time.perf_counter()-started)
    save(dest/(label+'-run.json'),record)
    if code:raise RuntimeError(('DHA CLI failed',label,code,stderr.decode(errors='replace')))
    return record,stdout.decode()


def dll_validate(dll_path,raw):
    class Stream(ct.Structure):
        _fields_=[('rate',ct.c_uint32),('channels',ct.c_uint16),('frame_samples',ct.c_uint16),
                  ('total_samples',ct.c_uint64),('model',ct.c_int8*1024),('ans',ct.c_uint8*512)]
    library=ct.CDLL(str(dll_path));library.dha_header_read.argtypes=[ct.POINTER(Stream),ct.c_void_p,ct.c_size_t]
    library.dha_header_read.restype=ct.c_int
    library.dha_decode_frame.argtypes=[ct.POINTER(Stream),ct.c_void_p,ct.c_size_t,ct.POINTER(ct.c_int16),ct.c_size_t,ct.POINTER(ct.c_size_t),ct.c_void_p]
    library.dha_decode_frame.restype=ct.c_int
    info=Stream();header=ct.create_string_buffer(raw[:1572]);assert library.dha_header_read(ct.byref(info),header,1572)==0
    values=[]
    for row in scan_packets(raw,complete=True):
        packet=ct.create_string_buffer(raw[row['file_offset']:row['file_offset']+row['packet_bytes']])
        pcm=(ct.c_int16*4096)();written=ct.c_size_t(0)
        assert library.dha_decode_frame(ct.byref(info),packet,row['packet_bytes'],pcm,4096,ct.byref(written),None)==0
        assert written.value==row['samples'];values.append(np.ctypeslib.as_array(pcm)[:written.value].copy())
    decoded=np.concatenate(values).astype('<i2')
    assert len(decoded)==info.total_samples
    return decoded,dict(sample_rate=info.rate,channels=info.channels,declared_samples=info.total_samples)


def run_source(name,evidence,out,scratch,cli,dll):
    folder=out/name;folder.mkdir();source_path=evidence/'general/inputs'/(name+'.wav')
    source=wav8(source_path).astype('u1');pcm=((source.astype(np.int32)-128)*256).astype('<i2')
    assert len(source)>4096
    (folder/'source-preview.wav').write_bytes(source_path.read_bytes())
    (folder/'source-pcm16.bin').write_bytes(pcm.tobytes());pcm_wav(folder/'source-pcm16.wav',pcm)
    pilot=folder/'pilot-first-frame';pilot.mkdir();pcm_wav(pilot/'input.wav',pcm[:4096])
    pilot_run,_=run_cli(cli,['encode',pilot/'input.wav',pilot/'audio.dhaf'],pilot,'encode')
    pilot_info_run,pilot_info=run_cli(cli,['info',pilot/'audio.dhaf'],pilot,'info')
    estimate=pilot_run['elapsed_seconds']*((len(pcm)+4095)//4096)
    save(folder/'pilot-estimate.json',dict(first_frame_samples=4096,first_frame_seconds=pilot_run['elapsed_seconds'],
        whole_frame_count=(len(pcm)+4095)//4096,naive_whole_estimated_seconds=estimate,
        caveat='First-frame extrapolation only; different gains, fallback and source content can change runtime'))
    print(json.dumps(dict(source=name,pilot_seconds=pilot_run['elapsed_seconds'],estimated_whole_seconds=estimate,
        source_samples=len(source),settings='default beam64/gains8/lookahead2/ratePenalty82/frame4096/fallbackON')),flush=True)
    encode,_=run_cli(cli,['encode',folder/'source-pcm16.wav',folder/'audio.dhaf'],folder,'encode',monitor=True,total_samples=len(pcm))
    info_run,info_text=run_cli(cli,['info',folder/'audio.dhaf'],folder,'info')
    decode_run,_=run_cli(cli,['decode',folder/'audio.dhaf',folder/'decoded.wav'],folder,'decode')
    raw=(folder/'audio.dhaf').read_bytes();frames=scan_packets(raw,complete=True)
    assert sum(row['samples'] for row in frames)==len(source)
    with wave.open(str(folder/'decoded.wav'),'rb') as file:
        assert (file.getframerate(),file.getnchannels(),file.getsampwidth(),file.getnframes())==(8000,1,2,len(source))
        decoded=np.frombuffer(file.readframes(file.getnframes()),'<i2').copy()
    dll_pcm,dll_info=dll_validate(dll,raw);np.testing.assert_array_equal(dll_pcm,decoded)
    (folder/'decoded-pcm16.bin').write_bytes(decoded.astype('<i2').tobytes())
    counts=dict(dha_frames=sum(row['kind']=='DHA' for row in frames),pcm16_fallback_frames=sum(row['kind']=='PCM16' for row in frames))
    parsed={}
    for line in info_text.splitlines():
        key,_,value=line.partition(': ')
        if value.isdigit():parsed[key]=int(value)
    assert parsed['dha_frames']==counts['dha_frames'] and parsed['pcm16_fallback_frames']==counts['pcm16_fallback_frames']
    assert parsed['validated_samples_per_channel']==len(source) and parsed['file_bytes']==len(raw)
    report=dict(complete=True,source=name,source_u8_sha256=sha(source.tobytes()),source_wav_sha256=sha(source_path.read_bytes()),
        source_pcm16_sha256=sha(pcm.tobytes()),decoded_pcm16_sha256=sha(decoded.tobytes()),sample_rate_hz=8000,
        channels=1,input_samples=len(source),decoded_samples=len(decoded),prepared_source_unmodified=True,
        conversion='Exact PCM16=(prepared_unsigned8-128)*256; no resampling/filter/gain normalization',
        source_content_duration_seconds=len(source)/8000,settings=dict(frame_samples=4096,beam_width=64,gain_candidates=8,lookahead=2,rate_penalty=82,allow_pcm_fallback=True),
        container='DHAFv1 host independent-frame container; NOT compiled-first Z80 wire or playable TRD',
        default_model_training='Unchanged predictor tables trained on selected15s sea-foam25kHz trajectory; this song alone cannot establish source-independent benefit',
        predictive_output_precision='DHA frames emit PCM8-rounded signedPCM16; fallback retains originalPCM16',
        file_bytes=len(raw),file_sha256=sha(raw),file_header_bytes=1572,frame_header_total_bytes=32*len(frames),
        payload_bits=sum(row['payload_bits'] for row in frames),payload_bytes=sum(row['payload_bytes'] for row in frames),
        original_pcm16_bytes=2*len(source),prepared_pcm8_bytes=len(source),IMA4_raw_reference_bytes=len(source)//2,
        DHAF_bits_per_sample=8*len(raw)/len(source),ratio_to_PCM16=len(raw)/(2*len(source)),
        **counts,channel_frames=len(frames),frames=frames,CLI_info_fully_validated=True,DLL_decode_matches_every_CLI_sample=True,
        DLL_stream_info=dll_info,encode=encode,info=info_run,decode=decode_run,
        model_sha256=sha(raw[32:1056]),ANS_sha256=sha(raw[1056:1568]),
        no_SNR_or_reconstruction_filter_measurement=True,no_Z80_CPU_or_disk_player_proof=True,release_accepted=False,physical_hardware_tested=False)
    save(folder/'report.json',report)
    print(json.dumps(dict(source=name,complete=True,file_bytes=len(raw),**counts,decoded_samples=len(decoded),encode_seconds=encode['elapsed_seconds'])),flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tester',type=Path,default=Path('C:/Work/z80-tester'))
    parser.add_argument('--evidence',type=Path,default=HERE/'evidence')
    parser.add_argument('--output',type=Path,default=HERE/'evidence/dha-host')
    parser.add_argument('--scratch',type=Path,required=True)
    parser.add_argument('--source',action='append',default=[])
    args=parser.parse_args();out=args.output.resolve();scratch=args.scratch.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Use an empty experiment directory; preserve failures')
    out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    snapshot,source_manifest=pin_source(args.tester.resolve(),out)
    cli,dll=compile_tools(snapshot,scratch/'build',out)
    names=args.source or ['sea_foam'];assert len(names)==len(set(names))
    rows=[]
    for name in names:
        rows.append(run_source(name,args.evidence.resolve(),out,scratch,cli,dll))
        save(out/'partial.json',dict(complete=False,rows=rows))
    save(out/'report.json',dict(complete=True,date='2026-10-19',sources=names,rows=rows,
        all_codec_sources_pinned_before_build=True,tester_checkout_unmodified=True,
        no_resampling=True,no_input_gain_or_filters=True,unmodified_library_defaults=True,
        host_container_is_not_Z80_wire=True,source_independent_quality_claim=False,
        no_SNR_measurement=True,physical_hardware_tested=False,release_accepted=False))
    (out/'harness.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(),mtime=0))
    files=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json' and '__pycache__' not in path.parts:
            raw=path.read_bytes();files.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(files=len(files),artifacts=files))
    print(json.dumps(dict(complete=True,sources=names,files=len(files))),flush=True)


if __name__=='__main__':main()
