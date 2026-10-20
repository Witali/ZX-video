"""Run the integrated faster C pipeline against all frozen matched encodes.

The existing complete nine-source encoding driver is reused verbatim. Every
result must retain the original IMA bytes, complete native input workset and
encoding-prior WAV. No quality rendering, timing-clock adjustment or TRD build
is performed. Historical timing is labelled separately from same-host pairs.
"""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from table_pdm_uniform16_encode import AUDIO,ORDER,PRODUCERS,MODEL

HERE=Path(__file__).resolve().parent
EXTRA_PRODUCERS=('native_waveform_prepare.c','native_waveform_prepare.py',
    'convert_snr_audio.py','native_ima_encoder.c','native_ima_encoder.py',
    'experiments/song-snr/table_pdm_uniform16.py',
    'experiments/song-snr/table_pdm_uniform16_encode.py',
    'experiments/song-snr/codec_speed_integration.py')


def sha(raw):return hashlib.sha256(raw).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def file_sha(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024):result.update(chunk)
    return result.hexdigest()


def audit_manifest(root):
    manifest=json.loads((root/'manifest.json').read_bytes())
    if not manifest['complete']:raise ValueError('Baseline evidence is not complete')
    for item in manifest['files']:
        path=root/item['path']
        assert path.stat().st_size==item['bytes'],path
        assert file_sha(path)==item['sha256'],path
    return dict(manifest_sha256=file_sha(root/'manifest.json'),files=len(manifest['files']))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'evidence/codec-speed-integration')
    parser.add_argument('--scratch',type=Path,default=AUDIO.parents[0]/'.tmp/codec-speed-integration')
    args=parser.parse_args();out=args.output.resolve();scratch=args.scratch.resolve()
    if out.exists() and any(out.iterdir()):raise ValueError('Preserve old evidence; choose a fresh output')
    out.mkdir(parents=True,exist_ok=True);scratch.mkdir(parents=True,exist_ok=True)
    baseline=HERE/'evidence/table-pdm-uniform16-matched'
    old_audit=audit_manifest(baseline)
    old_config=json.loads((baseline/'configuration.json').read_bytes())
    assert old_config['model']==MODEL and old_config['source_order']==list(ORDER)
    producers={name:sha((AUDIO/name).read_bytes()) for name in dict.fromkeys((*PRODUCERS,*EXTRA_PRODUCERS))}
    snapshot=out/'producer-source';snapshot.mkdir()
    for name,expected in producers.items():
        content=(AUDIO/name).read_bytes();assert sha(content)==expected
        (snapshot/(name.replace('/','__')+'.gz')).write_bytes(gzip.compress(content,mtime=0))
    save(out/'configuration.json',dict(producers=producers,baseline=str(baseline.relative_to(HERE)),
        baseline_audit=old_audit,source_order=list(ORDER),model=MODEL,
        preparation_backend='native',waveform_encoder='standalone C',
        no_source_gain_clock_delay_or_search_parameter_change=True,
        source_count=9,expected_samples=1195520,quality_rendering=False,TRD_construction=False))
    command=[sys.executable,str(HERE/'table_pdm_uniform16_encode.py'),
        '--output',str(out/'optimized'),'--scratch',str(scratch)]
    started=time.perf_counter()
    with (out/'encoding.log').open('w',encoding='utf-8') as log:
        child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            text=True,encoding='utf-8',creationflags=0x08000000 if os.name=='nt' else 0)
        for line in child.stdout:
            log.write(line);log.flush();print(line,end='',flush=True)
        status=child.wait()
    child_seconds=time.perf_counter()-started
    if status:raise RuntimeError(f'Integrated encoding driver exited{status}; preserve this attempt')
    assert producers=={name:sha((AUDIO/name).read_bytes()) for name in producers}
    assert old_audit==audit_manifest(baseline)
    audit_manifest(out/'optimized')
    new_config=json.loads((out/'optimized/configuration.json').read_bytes())
    for key in ('model','parameters','search','source_order','sources','words_sha256',
        'successors_sha256','timeline','source_rate_hz','physical_CPU_hz',
        'physical_hold_T','physical_period_T','physical_PDM_hz'):
        assert old_config[key]==new_config[key],key
    rows=[]
    for name in ORDER:
        old=json.loads((baseline/name/'report.json').read_bytes())
        new=json.loads((out/'optimized'/name/'report.json').read_bytes())
        old_packed=gzip.decompress((baseline/name/'packed.ima.gz').read_bytes())
        new_packed=gzip.decompress((out/'optimized'/name/'packed.ima.gz').read_bytes())
        assert old_packed==new_packed and sha(new_packed)==old['packed_sha256']==new['packed_sha256']
        assert (baseline/name/'encoding-prior.wav').read_bytes()==(out/'optimized'/name/'encoding-prior.wav').read_bytes()
        for key in ('source_identity','source_sha256','source_samples','packed_bytes',
            'decoded_samples','decoded_pcm16_sha256','final_predictor','final_index',
            'encoded_prior_pcm8_sha256','prior_differs_original_samples',
            'every_physical_hold_T','physical_period_T','reference_time_units'):
            assert old[key]==new[key],(name,key)
        for key in ('workset_sha256','workset_bytes','search_iterations','final_predictor','final_index'):
            assert old['encoding']['statistics'][key]==new['encoding']['statistics'][key],(name,key)
        assert old['encoding']['saturation_guard']==new['encoding']['saturation_guard']
        rows.append(dict(source=name,samples=new['source_samples'],packed_bytes=len(new_packed),
            packed_sha256=sha(new_packed),workset_sha256=new['encoding']['statistics']['workset_sha256'],
            complete_workset_and_packed_bytes_identical=True,prior_WAV_bytes_identical=True,
            decoded_PCM16_bytes_identical=True,search_iterations_identical=True,
            baseline_elapsed_seconds=old['elapsed_seconds'],optimized_elapsed_seconds=new['elapsed_seconds'],
            baseline_model_preparation_seconds=old['encoding']['model_preparation_seconds'],
            optimized_model_preparation_seconds=new['encoding']['model_preparation_seconds'],
            baseline_c_encoding_and_workset_seconds=old['encoding']['c_encoding_and_workset_seconds'],
            optimized_c_encoding_and_workset_seconds=new['encoding']['c_encoding_and_workset_seconds']))
    assert sum(row['samples'] for row in rows)==1195520
    save(out/'report.json',dict(complete=True,all_nine_original_complete_streams_identical=True,
        total_samples=sum(row['samples'] for row in rows),rows=rows,
        child_driver_wall_seconds=child_seconds,
        total_baseline_reported_encoding_seconds=sum(row['baseline_elapsed_seconds'] for row in rows),
        total_optimized_reported_encoding_seconds=sum(row['optimized_elapsed_seconds'] for row in rows),
        timing_scope='Historical baseline from the prior complete matched experiment versus current integrated source times using the same driver workload. These are not simultaneous controlled timing pairs; separate phase benchmarks establish isolated speedups.',
        current_native_backend_with_original_python_reference_preserved=True,
        format_and_every_encoded_audio_byte_unchanged=True,
        quality_rendering_repeated=False,actual_player_execution_repeated=False,
        release_or_new_TRD_claim=False))
    text='''# Integrated encoding acceleration: complete corpus\n\nOn 2026-10-20 the user requested faster encoding and decoding while preserving the data format. This run uses the integrated native preparation and faster standalone C waveform selection through the original nine-source matched encoding driver. It authenticates the entire previous matched experiment before and after running.\n\nEvery complete IMA stream, complete NWFB001 workset, encoding-prior WAV, decoded PCM16 hash, final predictor/index, search iteration count and clipping guard remains identical for all nine original sources. The total is1,195,520 samples. The model, source clock, search parameters, source bytes and original silent guards are unchanged. No quality filter rendering or emulator playback is repeated because the audio bytes are identical; this is no new TRD or release acceptance.\n\nSee report.json for all source times. The old elapsed times are historical observations from the previous matched experiment; they are not simultaneous paired timing measurements. This driver has the same workload in both runs. Separate native preparation and C search benchmarks document controlled phase comparisons.\n\nReproduce with `python audiobook-beeper/experiments/song-snr/codec_speed_integration.py --output NEW_EMPTY_DIRECTORY`. All source producers and their SHA256 values are frozen in producer-source/ and configuration.json; optimized/ contains the original driver snapshots, per-source reports and compressed IMA outputs.\n'''
    (out/'README.md').write_text(text,encoding='utf-8')
    records=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path!=out/'manifest.json':
            records.append(dict(path=path.relative_to(out).as_posix(),bytes=path.stat().st_size,sha256=file_sha(path)))
    save(out/'manifest.json',dict(complete=True,files=records))
    audit_manifest(out)
    print(json.dumps(dict(integration_complete=True,sources=len(rows),samples=1195520,
        every_audio_and_workset_byte_unchanged=True,optimized_seconds=sum(row['optimized_elapsed_seconds'] for row in rows))),flush=True)


if __name__=='__main__':main()
