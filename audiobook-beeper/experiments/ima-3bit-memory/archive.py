import gzip, hashlib, json, shutil
from pathlib import Path
from verify_pcm import save

root=Path.cwd()
src=root/'.tmp/ima3-memory-check'
dest=root/'audiobook-beeper/experiments/ima-3bit-memory'
report=json.loads((src/'comparison.json').read_bytes())
assert report['actual_fuse_verified'] and report['full_capacity_fuse']['complete']
if 'instruction_bytes_identical' in report:
    report['pulse_and_extraction_instruction_bytes_identical']=report.pop('instruction_bytes_identical')
assert report['pulse_and_extraction_instruction_bytes_identical']
report['source_identity']={}
old=root/'audiobook-beeper/experiments/ima-3bit-direct'
for name in ('player.json','quality.json','source-preview.wav','soundtrack.ima.gz','output-times.u32.gz'):
    path=old/name
    report['source_identity'][str(path.relative_to(root)).replace('\\','/')]=hashlib.sha256(path.read_bytes()).hexdigest()
report['model64_native']=json.loads((src/'model64-regression/native.json').read_bytes())
save(src/'comparison.json',report)
dest.mkdir(parents=True,exist_ok=False)
for path in src.rglob('*'):
    if not path.is_file():continue
    rel=path.relative_to(src)
    if rel.parts[0]=='baseline-assembly':continue
    if path.suffix in ('.wav','.trd'):continue
    if path.name in ('soundtrack.ima.gz','soundtrack.ima3.gz'):continue
    target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(path.read_bytes())
for name in ('ima3_direct_player.py','ima3-direct-player.asm','verify_ima3_memory.py'):
    target=dest/'producer-source'/(name+'.gz');target.parent.mkdir(exist_ok=True)
    target.write_bytes(gzip.compress((root/'audiobook-beeper'/name).read_bytes(),mtime=0))
for name in ('audiobook-preview.trd','capacity/audiobook-preview.trd'):
    path=src/name
    (dest/(name+'.gz')).write_bytes(gzip.compress(path.read_bytes(),mtime=0))
disk=root/'ZX-audiobook-IMA3-compact-tables.trd'
disk.write_bytes((src/'audiobook-preview.trd').read_bytes())
assert hashlib.sha256(disk.read_bytes()).hexdigest()==report['candidate_disk_sha256']
for name in ('ima3-memory-check.log','ima3-memory-capacity.log'):
    (dest/name).write_bytes((root/'.tmp'/name).read_bytes())
shutil.copy2(__file__,dest/'archive.py')
save(dest/'completion-audit.json',dict(complete=True,date='2026-10-04',
    disk=str(disk.relative_to(root)),disk_sha256=report['candidate_disk_sha256'],
    ordinary_tstates=report['ordinary_tstates_after'],ordinary_delta_tstates=0,
    physical_ram_bytes_reclaimed=report['memory']['bank2_bytes_reclaimed'],
    source_bitstream_and_relative_timing_identical=True,
    reference_bits=report['timestamps_compared'],full_capacity_bits=report['full_capacity_fuse']['bits_verified'],
    maximum_capacity_source='Original reference plus synthetic silence, not a longer real recording',
    quality='Reused original SNR after complete bit/timestamp equivalence; no new encoder search or listening claim',
    physical_hardware_tested=False))
for path in dest.rglob('*.json'):
    path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
artifacts={str(path.relative_to(dest)).replace('\\','/'):dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
           for path in sorted(dest.rglob('*')) if path.is_file()}
save(dest/'artifact-hashes.json',artifacts)
print(json.dumps(dict(artifacts=len(artifacts),bytes=sum(a['bytes'] for a in artifacts.values()),disk_sha256=report['candidate_disk_sha256'])))
