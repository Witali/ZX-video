"""Audit and archive only a fully verified automatic direct-IMA3 delivery."""
from pathlib import Path
import gzip,hashlib,json,shutil
import numpy as np
from probe_reconstruction_error import wav8
from convert_ima3_audio import stage
from verify_pcm import save
src=Path('.tmp/ima3-automatic-final');out=Path('audiobook-beeper/experiments/ima-3bit-direct')
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read(src/'report.json');m=read(src/'player.json');q=read(src/'quality.json');n=read(src/'native.json');f=read(src/'fuse.json')
assert r['complete'] and r['quality_gate_passed'] and r['target_met'] and r['target_snr_db']==20
assert q['snr_at_least_20_db'] and min(q['two_loop_clock_aware_snr_db'])>=20
assert abs(q['mean_speed_error_percent'])<=2 and q['complete_trace_phase_deltas_tstates'][1]==0
assert abs(q['complete_trace_phase_deltas_tstates'][0])<=3
source=wav8(src/'source-preview.wav');original=wav8(Path('audiobook-beeper/experiments/ima-3bit-waveform/source-preview.wav'))
assert np.array_equal(source,original) and len(source)==186880
assert m['packed_ima3_direct'] and m['memory']['resident_ima4_bytes']==0
assert m['resident_audio_bytes']==70080 and m['memory']['maximum_ima3_bytes']==93432
assert m['memory']['pcm_buffer_bytes']==m['memory']['pdm_buffer_bytes']==0
assert m['ordinary_tstates']==427.375 and m['ordinary_delta_tstates']==4.375
for x in (n,f):
    assert x['complete'] and x['cycles_verified']==2 and x['every_pdm_bit_exact'] and x['every_predictor_and_index_exact']
    assert x['bits_verified']==5981841 and x['pcm16_samples_verified']==373760
assert n['memory_guards_passed'] and n['every_output_port_uncontended'] and n['rational_table_cases']==4096
assert f['runtime_disk_reads']==0 and f['loading_progress_steps_verified']==32 and f['loading_message']['hidden_before_playback']
assert f['trd_sha256']==r['trd_sha256']==sha(src/'audiobook-preview.trd')
independent=read(src/'independent-ima.json');assert independent['every_sample_exact'] and independent['samples']==186880
recording=r['recording'];assert recording and recording['recording_complete'] and recording['two_wraps_observed']
assert recording['paging_latches_match'] and recording['secondary_paging_unchanged'] and recording['all_half_second_windows_have_signal']
assert recording['startup_seconds']<=60 and recording['source_trd_sha256']==r['trd_sha256']
assert (src/'assembly/player.asm').read_bytes()==Path('audiobook-beeper/ima3-direct-player.asm').read_bytes()
for key in ('pilot','encode-1','disk-encode-1','sound-128'):
    stage(src/key,lambda _:(_ for _ in ()).throw(AssertionError('missing stage')))
# Save the release files plus the pilot needed for deterministic PC re-encoding.
for p in src.iterdir():
    if p.is_file() and p.suffix not in ('.trd',):shutil.copy2(p,out/p.name)
for name in ('assembly','pilot','encode-1','sound-128'):
    dst=out/name;dst.mkdir(exist_ok=True)
    for p in (src/name).iterdir():
        if p.is_file() and p.name!='capture.fmf.gz' and not (name=='sound-128' and p.name=='stage-complete.json'):
            shutil.copy2(p,dst/p.name)
    if (src/name/'assembly').is_dir():shutil.copytree(src/name/'assembly',dst/'assembly',dirs_exist_ok=True)
for name in ('ima3-direct-final-alphabet-check.json','ima3-pilot-cache-check.json'):
    shutil.copy2(Path('.tmp')/name,out/name)
for name,label in [('ima3-automatic-short-final','automatic-short-final'),('ima3-direct-lookahead128','lookahead-host')]:
    p=Path('.tmp')/name;dst=out/label;dst.mkdir(exist_ok=True)
    for name in ('report.json','quality.json','native.json','fuse.json','run.json','soundtrack.ima.gz'):
        if (p/name).is_file():shutil.copy2(p/name,dst/name)
for name in ('encode-1','encode-2'):
    p=Path('.tmp/ima3-automatic-full')/name;dst=out/'automatic-first-search'/name;dst.mkdir(exist_ok=True)
    for f in ('report.json','soundtrack.ima.gz'):shutil.copy2(p/f,dst/f)
shutil.copy2('.tmp/ima3-lookahead128.py',out/'lookahead-host'/'reproduce.py')
# Keep the exact producer bytes, including line endings, under their run hashes.
producer=out/'producer-source';producer.mkdir(exist_ok=True)
identity=read(src/'run.json')
for name,expected in identity['producer_sha256'].items():
    p=Path('audiobook-beeper')/name;assert sha(p)==expected,name
    (producer/(name+'.gz')).write_bytes(gzip.compress(p.read_bytes(),mtime=0))
# Large raw event traces and FMF remain local, authenticated here.
selected=src/'disk-encode-1';selected=selected/read(selected/'report.json')['selected']
raw=[selected/'verification-work/fuse-trace.txt.gz',src/'sound-128/capture.fmf.gz']
root=Path('ZX-audiobook-IMA3-direct-test.trd');shutil.copy2(src/'audiobook-preview.trd',root)
audit=dict(complete=True,date='2026-10-04',source_samples=len(source),source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
    source_unchanged=True,quality=q,normal_recording=recording,root_trd=str(root),trd_sha256=sha(root),
    native_bits=n['bits_verified'],fuse_bits=read(src/'fuse.json')['bits_verified'],native_full_capacity_report='attempts/ima3-direct-uniform128-capacity/native.json',
    raw_evidence=[dict(path=str(p.resolve()),sha256=sha(p),bytes=p.stat().st_size) for p in raw],
    requested_25_db_achieved=False,physical_hardware_tested=False)
save(out/'completion-audit.json',audit)
files={str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file() and p.name!='artifact-hashes.json'}
save(out/'artifact-hashes.json',files)
print(json.dumps(dict(complete=True,snr=q['two_loop_clock_aware_snr_db'],startup_seconds=recording['startup_seconds'],trd_sha256=sha(root),archived_files=len(files))),flush=True)
