"""Final read-only audit of all retained uniform-table experiment milestones.

No native CPU, encoder, filter or renderer is rerun. Historical producers and
failed attempts remain immutable; current original players/disks are compared
to Git55b0f007. The new paged component is a static two-bank PCM8 mechanism.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess

import numpy as np

from table_pdm_uniform16_audit import authenticate

HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
WORKTREE=AUDIO.parent
BASELINE='55b0f007'
ORIGINALS=('ima_waveform_encoder.py','ima_beam.py','ima_codec.py',
    'native_waveform_encoder.c','native_waveform_encoder.py','waveform_kernel.py',
    'direct_player.py','stream-player.asm','build_stream_trd.py')
DISKS=('ZX-music-Sea-Foam-RAM-auto.trd','ZX-music-Sea-Foam-SNR20-RAM-auto.trd')


def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def git(*args):return subprocess.check_output(['git',*args],cwd=WORKTREE)
def bits(word):return bytes((word>>shift)&1 for shift in range(15,-1,-1))


def replay(source,state,model):
    result=bytearray()
    for value in source[:-1]:
        row=model[value>>2,state];result.extend(bits(int(row[0])+256*int(row[1])));state=int(row[2])
    return bytes(result),state


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,
        default=HERE/'evidence/table-pdm-uniform16-final-audit')
    parser.add_argument('--delivered-root',type=Path,default=Path('C:/Work/ZX-video'))
    args=parser.parse_args();out=args.output.resolve()
    if out.exists():raise FileExistsError('Preserve completed or failed final audit: '+str(out))
    evidence=HERE/'evidence'
    folders=sorted(path for path in evidence.glob('table-pdm-uniform16-*') if path.is_dir() and path!=out)
    authenticated=[authenticate(folder) for folder in folders]
    required={'table-pdm-uniform16-component','table-pdm-uniform16-bank-component',
        'table-pdm-uniform16-bank-component-attempt-1','table-pdm-uniform16-host',
        'table-pdm-uniform16-host-8k','table-pdm-uniform16-audit',
        'table-pdm-uniform16-audit-attempt-1','table-pdm-uniform16-matched',
        'table-pdm-uniform16-matched-quality','table-pdm-uniform16-quality-audit',
        'table-pdm-uniform16-paged-component','table-pdm-uniform16-paged-component-attempt-1',
        'table-pdm-uniform16-paged-boundaries'}
    assert {path.name for path in folders}==required
    model=np.frombuffer((evidence/'table-pdm-uniform16-matched-quality/model.bin').read_bytes(),'u1').reshape(64,32,3)
    paged=evidence/'table-pdm-uniform16-paged-component';paged_report=read(paged/'report.json')
    assert paged_report['complete'] and paged_report['states']==[8,12,16,17,21,25]
    assert paged_report['all_actual_speaker_holds_tstates']==28
    assert paged_report['ordinary_page_bank_source_period_tstates']==448
    assert paged_report['new_static_bank_extra_tstates']==0
    assert paged_report['total_outputs']==647136 and paged_report['fixed_allocation_bytes']==31986
    labels=next(ast.literal_eval(line) for line in (paged/'assembler.log').read_text(encoding='utf-8').splitlines() if line.startswith('{'))
    table=(paged/'lookup.bin').read_bytes();states=paged_report['states'];checked_cells=0
    for value in range(64):
        for index,state in enumerate(states):
            first,second=struct.unpack_from('<HH',table,value*256+index*4)
            row=model[value,state];word=int(row[0])+256*int(row[1]);offset=states.index(int(row[2]))*4
            assert first==labels[f'first_{word>>8}'] and second==labels[f'second_{word&255}_{offset}']
            checked_cells+=1
    assert (paged/'pcm-high.bin').read_bytes()==bytes(0x40+(value>>2) for value in range(256))
    source=(paged/'trajectory-pcm8.bin').read_bytes();native_bits=gzip.decompress((paged/'trajectory-bits.u8.gz').read_bytes())
    expected,_=replay(source,16,model);assert expected==native_bits and len(native_bits)==524256
    native_times=np.frombuffer(gzip.decompress((paged/'trajectory-times.u32.gz').read_bytes()),'<u4')
    np.testing.assert_array_equal(native_times,11+np.arange(len(native_bits),dtype='<u4')*28)
    assert sha(native_bits)==paged_report['trajectory']['bits_sha256']
    assert sha(native_times.tobytes())==paged_report['trajectory']['times_sha256']
    assert paged_report['trajectory']['samples']==32766
    event=paged_report['trajectory']['page_events'];assert len(event)==1
    assert event[0]['after_speaker_outputs']==16384*16-17 and event[0]['value']==0x19
    assert event[0]['already_prefetched_old_final_PCM']==source[16383]
    cases=read(paged/'all-cells.json');assert len(cases)==1536
    boundary=evidence/'table-pdm-uniform16-paged-boundaries';boundary_report=read(boundary/'report.json')
    boundary_cases=read(boundary/'all-cells.json');assert len(boundary_cases)==1536
    for collection,address,outputs_before_page in ((cases,0xFFFD,31),(boundary_cases,0xFFFE,15)):
        for index,case in enumerate(collection):
            state=states[index//256];value=index%256
            source=bytes([value,(value*73+17)&255,(value*29+state)&255,(value*41+3)&255,(value*7+state)&255,0xA5])
            expected,_=replay(source,state,model)
            assert case['initial_state']==state and case['initial_address']==address
            assert case['samples']==5 and case['outputs']==80 and case['actual_source_banks']==2
            assert case['bits_sha256']==sha(expected)
            assert case['times_sha256']==sha((11+np.arange(80,dtype='<u4')*28).tobytes())
            assert case['bits_exact'] and case['successor_lookup_exact'] and case['source_order_exact']
            assert case['source_RAM_CPU_unchanged'] and case['fixed_RAM_CPU_mutable_bytes']==194
            assert len(case['page_events'])==1 and case['page_events'][0]['value']==0x19
            assert case['page_events'][0]['after_speaker_outputs']==outputs_before_page
    assert boundary_report['effective_model_cells_at_actual_bank_decision']==checked_cells==384
    assert boundary_report['outputs']==122880 and boundary_report['source_sample_tstates']==448
    original_manifest_hash=boundary_report['component_manifest_sha256']
    retained_manifest_hashes=[sha((paged/'manifest.json').read_bytes())]
    if (paged/'initial-manifest.json').exists():retained_manifest_hashes.append(sha((paged/'initial-manifest.json').read_bytes()))
    assert original_manifest_hash in retained_manifest_hashes
    failed=read(evidence/'table-pdm-uniform16-paged-component-attempt-1/failure.json')
    assert not failed['complete'] and failed['trajectory_source_bytes']==32768
    assert 'EOF' in failed['observed_failure']
    current_producers=[]
    for filename,folder in (('table_pdm_uniform16.py','table-pdm-uniform16-component'),
        ('table_pdm_uniform16_bank.py','table-pdm-uniform16-bank-component'),
        ('table_pdm_uniform16_paged.py','table-pdm-uniform16-paged-component'),
        ('table_pdm_uniform16_paged_boundaries.py','table-pdm-uniform16-paged-boundaries')):
        frozen=gzip.decompress((evidence/folder/'producer.py.gz').read_bytes())
        assert frozen==(HERE/filename).read_bytes()
        current_producers.append(dict(path=filename,sha256=sha(frozen),current_matches_frozen=True))
    host_versions=[]
    for folder in ('table-pdm-uniform16-host','table-pdm-uniform16-host-8k','table-pdm-uniform16-matched-quality'):
        frozen=gzip.decompress((evidence/folder/'producer-source/table_pdm_uniform16_host.py.gz').read_bytes())
        host_versions.append(dict(folder=folder,sha256=sha(frozen),supports_packed_dir=b'--packed-dir' in frozen))
    assert len({row['sha256'] for row in host_versions})==3
    assert [row['supports_packed_dir'] for row in host_versions]==[False,False,True]
    assert gzip.decompress((evidence/'table-pdm-uniform16-matched-quality/producer-source/table_pdm_uniform16_host.py.gz').read_bytes())==(HERE/'table_pdm_uniform16_host.py').read_bytes()
    assert len({(evidence/folder/'host.c').read_bytes() for folder in ('table-pdm-uniform16-host','table-pdm-uniform16-host-8k','table-pdm-uniform16-matched-quality')})==1
    matched=read(evidence/'table-pdm-uniform16-matched/report.json')
    quality=read(evidence/'table-pdm-uniform16-matched-quality/report.json')
    quality_audit=read(evidence/'table-pdm-uniform16-quality-audit/report.json')
    assert matched['complete'] and matched['all_nine_sources_encoded'] and len(matched['rows'])==9
    assert quality['complete'] and quality['samples']==quality_audit['samples']==1195520
    assert quality_audit['complete'] and quality_audit['artifact_acceptance'] is False
    assert len(quality_audit['producer_checks'])==19
    song=next(row for row in matched['rows'] if row['source']=='sea_foam')
    assert song['packed_bytes']==360192 and song['decoded_samples']==720384
    baseline=git('rev-parse',BASELINE).decode().strip();original_checks=[]
    for name in ORIGINALS:
        path='audiobook-beeper/'+name;old=git('show',baseline+':'+path);now=(AUDIO/name).read_bytes()
        assert old==now,path
        original_checks.append(dict(path=path,bytes=len(now),sha256=sha(now),byte_identical_to_baseline=True))
    disk_checks=[]
    for name in DISKS:
        pointer=git('show',baseline+':'+name).decode('ascii')
        expected=re.search(r'(?m)^oid sha256:([0-9a-f]{64})$',pointer).group(1)
        size=int(re.search(r'(?m)^size ([0-9]+)$',pointer).group(1));path=args.delivered_root/name;raw=path.read_bytes()
        assert len(raw)==size and sha(raw)==expected
        disk_checks.append(dict(path=path.as_posix(),bytes=size,sha256=expected,matches_baseline_LFS_oid=True))
    document=AUDIO/'TABLE_PDM_UNIFORM.md';links=[]
    for match in re.finditer(r'\[[^\]]+\]\(([^)]+)\)',document.read_text(encoding='utf-8')):
        target=match.group(1).strip('<>');local=target.split('#',1)[0]
        if '://' in local or not local:continue
        resolved=document.parent/local;assert resolved.exists(),str(resolved)
        links.append(dict(target=target,exists=True))
    report=dict(complete=True,date='2026-10-20',authenticated=authenticated,
        evidence_sets=len(authenticated),artifacts=sum(row['artifacts'] for row in authenticated),
        original_baseline_commit=baseline,original_files=original_checks,delivered_disks=disk_checks,
        current_native_producers=current_producers,historical_host_producer_versions=host_versions,
        historical_clock_error_retained=True,current_host_C_algorithm_unchanged=True,
        paged=dict(model_cells=checked_cells,forced_bank_cases=len(cases),boundary_model_cases=len(boundary_cases),
            trajectory_samples=32766,trajectory_outputs=len(native_bits),all_trajectory_bits_and_times_exact=True,
            all_specialized_record_words_and_successors_match_host_model=True,
            static_bank_transition='bank0->bank1 via one exact7FFD/19 write',
            ordinary_page_bank_sample_T=448,all_speaker_holds_T=28,
            fixed_allocation_B=31986,remaining_fixed_bank_bytes_before_integration=32768-31986,
            guard_FFFF_failed_attempt_retained=True),
        matched_sources=9,matched_samples=1195520,matched_song_IMA_bytes=360192,
        matched_song_host_SNR_dB=quality_audit['matched_song']['host_SNR_dB'],
        artifact_numeric_regressions=quality_audit['numeric_regression_counts'],
        document_links=links,no_new_native_encoder_filter_or_renderer_runs=True,
        release_accepted=False,artifact_acceptance=False,
        remaining=['Only a static two-bank residentPCM8 transition is implemented; dynamic descriptors and EOF are unproved.',
            'The final guard atFFFF attempted a second page switch; the bounded passing trajectory stops with guardFFFE.',
            'The song needs720384 residentPCM8 bytes, exceeding512KiB before overhead;1024KiB requires a complete RAM/loader map.',
            'Full IMA decoding remains host-side; the compressed native uniform schedule is not integrated.',
            'Cover, progress, independent boot, refills, clone contention and full installed-Fuse playback are unproved.',
            'The31,986B fixed component precedes complete loader/screen/UI allocation; unused lookup holes are not a verified integrated memory budget.',
            'Same-clock source diagnostics retain numerical modulation/coherent-line increases and inconclusive fits.'])
    out.mkdir(parents=True);save(out/'report.json',report)
    (out/'README.md').write_text(f'''# Final uniform-table evidence audit

Completed2026-10-20 without rerunning native execution, encoders, compilation,
filters or rendering. All{report['artifacts']} artifacts in{report['evidence_sets']}
retained milestone directories pass full manifest coverage and SHA256 checks,
including failed attempts and all three historical host-producer versions.

The new paged component has1536 forced-bank cases,1536 additional cases whose
initial model cell occupies the bank-decision sample, and a32766-sample varied
two-bank trajectory. Its524256 retained trajectory bits and every28T timestamp
match the same host model. All384 specialized lookup cells compose exact host
words/successors. Ordinary pages and this one static bank switch retain448T
per sample. This adds no dynamic bank sequence, EOF or full-song native claim.

The guard-atFFFF failure remains retained. The passing bounded trajectory
uses a guard atFFFE. The31,986-byte fixed component leaves782 fixed bytes
before integration; loader, screen and UI still need an actual allocation.
The720384-byte residentPCM8 song exceeds512KiB before overhead. Pentagon1024
residency is a possibility requiring a complete loader/RAM/boot implementation.
Its compressed IMA payload remains360192 bytes.

Nine original C/Python/player files are byte-identical to Git{baseline}.
Both delivered TRDs match that baseline's GitLFS SHA256 identities; the current
SNR20 disk is unchanged. Matched nine-source host encodes/quality and the prior
diagnostic audit remain separate from the native residentPCM8 mechanism.
Song host quality is22.781483124dB, but numerical artifact regressions and
inconclusive controls remain. Release and artifact acceptance are false.

The wrong-clock first host render, corrected canonical render and later
explicit-packed-input wrapper have distinct frozen Python producer hashes.
Their shared C output algorithm is unchanged. Historical snapshots are not
required to equal the current extended CLI source.
''',encoding='utf-8')
    for source in (Path(__file__),HERE/'table_pdm_uniform16_audit.py'):
        target=out/'producer-source'/(source.name+'.gz');target.parent.mkdir(exist_ok=True)
        target.write_bytes(gzip.compress(source.read_bytes(),mtime=0))
    files=[]
    for path in sorted(out.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();files.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(complete=True,files=files))
    print(json.dumps(dict(complete=True,evidence_sets=report['evidence_sets'],artifacts=report['artifacts'],
        originals=len(original_checks),disks=len(disk_checks),paged_bits_exact=True)),flush=True)


if __name__=='__main__':main()
