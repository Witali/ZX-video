"""Measure exact reference-preparation acceleration, without encoding changes.

Each engine runs in a fresh process. Identical NWFB001 and NWFB002 hashes,
including all features, targets and successor tables, are required. Windows
peak working-set measurements include imports, preparation and serialization;
they are process peaks rather than allocator measurements or a release claim.
"""
import argparse
import ctypes
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import numpy as np

from build_pdm import CPU_CLOCK
import clock_control
from ima_waveform_encoder import WaveformModel
from native_waveform_encoder import write_workset
import native_waveform_prepare
from pacing448_control import NAMES,instruction_timeline,model_for
from precompensate_voice import compensate
from probe_reconstruction_error import wav8
from table_pdm_uniform16_encode import timeline,MODEL

HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
SOURCES=('native_waveform_prepare.c','native_waveform_prepare.py',
    'test_native_waveform_prepare.py',
    'ima_waveform_encoder.py','native_waveform_encoder.py','waveform_kernel.py',
    'precompensate_voice.py','probe_feedback_packets.py','build_pdm.py',
    'experiments/song-snr/native_prepare_speed.py',
    'experiments/song-snr/clock_control.py','experiments/song-snr/pacing448_control.py',
    'experiments/song-snr/table_pdm_uniform16_encode.py')


def sha(content):return hashlib.sha256(content).hexdigest()
def save(path,data):Path(path).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def file_sha(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024):value.update(chunk)
    return value.hexdigest()


def peak_memory():
    if os.name!='nt':return None
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_uint32),('PageFaultCount',ctypes.c_uint32)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    result=Counters();result.cb=ctypes.sizeof(result)
    current=ctypes.windll.kernel32.GetCurrentProcess
    current.restype=ctypes.c_void_p
    get=ctypes.windll.psapi.GetProcessMemoryInfo
    get.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_uint32]
    if not get(current(),ctypes.byref(result),ctypes.sizeof(result)):
        raise ctypes.WinError()
    return int(result.PeakWorkingSetSize)


def worker(engine,name,profile,scratch,output):
    original=wav8(HERE/'evidence/general/inputs'/(name+'.wav'))
    source=original
    if profile!='uniform':
        source=original[:16384].copy();source[-128:]=128
    times=timeline(len(source)) if profile=='uniform' else instruction_timeline(len(source),int(profile))
    model=MODEL if profile=='uniform' else model_for(int(profile))
    if engine=='native':native_waveform_prepare._load()
    started=time.perf_counter()
    prior=compensate(source,times[::16],radius=16,period=CPU_CLOCK/8000)
    prior[-128:]=128
    compensated=time.perf_counter()
    if engine=='native':
        original_unique=np.unique
        def unique_rows(values,*args,**kwargs):
            if not args and kwargs==dict(axis=0,return_inverse=True):
                return native_waveform_prepare.unique_holds(values)
            return original_unique(values,*args,**kwargs)
        with patch.object(WaveformModel,'reference',native_waveform_prepare.reference),\
             patch.object(np,'unique',unique_rows):
            desired,features,ids,nxt,quantization=clock_control.prepare(source,times,model)
    else:desired,features,ids,nxt,quantization=clock_control.prepare(source,times,model)
    prepared=time.perf_counter()
    hashes={};writes={};sizes={}
    for bias in (0,512):
        work=scratch/f'{name}-{profile}-{engine}-{bias}.nwf'
        timer=time.perf_counter()
        write_workset(work,prior,desired,features,ids,nxt,width=32,block_size=128,
            commit_size=64,regularization=.1,pcm_quantization_bias=bias)
        writes[str(bias)]=time.perf_counter()-timer
        sizes[str(bias)]=work.stat().st_size;hashes[str(bias)]=file_sha(work)
        work.unlink()
    report=dict(source=name,profile=profile,engine=engine,samples=len(source),
        original_PCM8_sha256=sha(original.tobytes()),source_fixture_sha256=sha(source.tobytes()),
        fixture='entire original source' if profile=='uniform' else 'first16384 samples with explicit128-sample silent test guard; no quality claim',
        prior_sha256=sha(prior.tobytes()),desired_sha256=sha(desired.astype('<f8').tobytes()),
        ids_sha256=sha(ids.astype('<i8').tobytes()),successors_sha256=sha(nxt.astype('<i8').tobytes()),
        feature_shapes=len(features),max_query_quantization_seconds=quantization,
        compensate_seconds=compensated-started,prepare_seconds=prepared-compensated,
        total_model_preparation_seconds=prepared-started,
        write_seconds_by_bias=writes,workset_sha256_by_bias=hashes,workset_bytes_by_bias=sizes,
        peak_process_working_set_bytes=peak_memory(),
        timing_scope='Warm compiled module; fresh process. Model preparation includes unchanged Lanczos, analytic features and target preparation. Serialization is separate. No encoding, rendering or TRD construction.',
        format_unchanged=True,original_Python_reference_changed=False)
    if engine=='native':
        lib=native_waveform_prepare._load()
        report['native_binary_sha256']=file_sha(lib._prepare_binary)
        report['native_source_sha256']=lib._prepare_source_sha256
        report['blas_sha256']=file_sha(lib._prepare_blas)
    save(output,report)
    print(json.dumps(dict(source=name,profile=profile,engine=engine,
        preparation_seconds=prepared-started,peak_bytes=report['peak_process_working_set_bytes'])),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/native-prepare-speed')
    parser.add_argument('--scratch',type=Path,default=AUDIO.parents[0]/'.tmp/native-prepare-speed')
    parser.add_argument('--worker',choices=('python','native'))
    parser.add_argument('--source',choices=NAMES)
    parser.add_argument('--profile',choices=('uniform','448','449'),default='uniform')
    parser.add_argument('--worker-output',type=Path)
    args=parser.parse_args();scratch=args.scratch.resolve();scratch.mkdir(parents=True,exist_ok=True)
    if args.worker:
        worker(args.worker,args.source,args.profile,scratch,args.worker_output);return
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve existing evidence; select a fresh output')
    out.mkdir(parents=True,exist_ok=True)
    frozen={name:sha((AUDIO/name).read_bytes()) for name in SOURCES}
    snapshot=out/'producer-source';snapshot.mkdir()
    for name,expected in frozen.items():
        content=(AUDIO/name).read_bytes();assert sha(content)==expected
        (snapshot/(name.replace('/','__')+'.gz')).write_bytes(gzip.compress(content,mtime=0))
    save(out/'configuration.json',dict(producers=frozen,all_nine_sources=True,
        extra_cases=['sea_foam_prefix16384@448','sea_foam_prefix16384@449'],
        workset_biases=[0,512],source_and_reference_gain_clock_delay_fit=False,
        independent_process_per_engine=True))
    rows=[]
    for name,profile in [(name,'uniform') for name in NAMES]+[('sea_foam','448'),('sea_foam','449')]:
        pair={}
        for engine in ('python','native'):
            dest=out/f'{name}-{profile}-{engine}.json'
            result=subprocess.run([sys.executable,str(Path(__file__).resolve()),
                '--worker',engine,'--source',name,'--profile',profile,'--scratch',str(scratch),
                '--worker-output',str(dest)],capture_output=True,text=True,timeout=120)
            (out/f'{name}-{profile}-{engine}.log').write_text(result.stdout+result.stderr,encoding='utf-8')
            if result.returncode:raise RuntimeError(f'Worker failed: {dest}')
            pair[engine]=json.loads(dest.read_bytes());print(result.stdout,end='',flush=True)
        for field in ('original_PCM8_sha256','source_fixture_sha256','prior_sha256',
            'desired_sha256','ids_sha256','successors_sha256','feature_shapes',
            'workset_sha256_by_bias','workset_bytes_by_bias'):
            assert pair['python'][field]==pair['native'][field],(name,profile,field)
        rows.append(dict(source=name,profile=profile,all_float64_target_bits_exact=True,
            both_complete_worksets_byte_identical=True,engines=pair,
            preparation_speedup=pair['python']['total_model_preparation_seconds']/pair['native']['total_model_preparation_seconds']))
        save(out/'partial.json',dict(complete=False,rows=rows))
    assert frozen=={name:sha((AUDIO/name).read_bytes()) for name in SOURCES}
    save(out/'report.json',dict(complete=True,all22_complete_worksets_match=True,
        compared_workset_pairs=len(rows)*2,all_nine_whole_sources=True,
        nonuniform448_449_prefix_controls=True,rows=rows,original_Python_reference_unchanged=True,
        no_quality_render_or_encoding_repeated=True))
    manifest=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':
            manifest.append(dict(path=path.relative_to(out).as_posix(),bytes=path.stat().st_size,sha256=file_sha(path)))
    save(out/'manifest.json',dict(complete=True,files=manifest))


if __name__=='__main__':main()
