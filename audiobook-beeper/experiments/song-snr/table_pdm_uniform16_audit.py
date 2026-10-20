"""Audit retained uniform-output evidence without encoding or rendering again.

The first host render used native Pentagon ticks as Spectrum-reference ticks.
It is preserved and explicitly invalid for the canonical8k comparison. This
audit authenticates both attempts and the corrected physical-clock conversion.
"""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import struct

import numpy as np

from ima_codec import decode
from pdm_player import CPU_CLOCK
from probe_reconstruction_error import wav8

HERE=Path(__file__).resolve().parent
NAMES=('sea_foam','silence','quiet440','loud3000','steps','quiet997','multitone','speech','entertainer')
SAMPLES={name:16896 for name in NAMES}
SAMPLES.update(sea_foam=720384,speech=186880,entertainer=186880)


def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def authenticate(folder):
    manifest=read(folder/'manifest.json')
    records=manifest.get('files')
    if records is None:records=[dict(path=name,**record) for name,record in manifest['artifact_files'].items()]
    seen=set()
    for record in records:
        relative=record['path'];assert relative not in seen;seen.add(relative)
        raw=(folder/relative).read_bytes()
        assert len(raw)==record['bytes'] and sha(raw)==record['sha256'],str(folder/relative)
    actual={path.relative_to(folder).as_posix() for path in folder.rglob('*') if path.is_file() and path.name!='manifest.json'}
    assert actual==seen,(folder,actual-seen,seen-actual)
    return dict(folder=folder.as_posix(),artifacts=len(records),manifest_sha256=sha((folder/'manifest.json').read_bytes()))


def packet_bits(word):return bytes((word>>shift)&1 for shift in range(15,-1,-1))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,
        default=HERE/'evidence/table-pdm-uniform16-audit');args=parser.parse_args()
    out=args.output.resolve()
    if out.exists():raise FileExistsError('Preserve completed audit: '+str(out))
    out.mkdir(parents=True)
    evidence=HERE/'evidence';component=evidence/'table-pdm-uniform16-component'
    bank=evidence/'table-pdm-uniform16-bank-component';bank_failed=evidence/'table-pdm-uniform16-bank-component-attempt-1'
    wrong=evidence/'table-pdm-uniform16-host';fixed=evidence/'table-pdm-uniform16-host-8k'
    prior_audit=evidence/'table-pdm-uniform16-audit-attempt-1'
    authenticated=[authenticate(folder) for folder in (component,bank,bank_failed,wrong,fixed,prior_audit)]
    component_report=read(component/'report.json');states=component_report['states']
    assert states==[8,12,16,17,21,25]
    assert component_report['complete'] and component_report['total_native_outputs']==286704
    labels=next(ast.literal_eval(line) for line in (component/'assembler.log').read_text(encoding='utf-8').splitlines() if line.startswith('{'))
    table=np.frombuffer((fixed/'model.bin').read_bytes(),'u1').reshape(64,32,3)
    assert (fixed/'model.bin').read_bytes()==(wrong/'model.bin').read_bytes()
    lookup=(component/'lookup.bin').read_bytes();native_cells=0
    for value in range(64):
        for index,state in enumerate(states):
            first,second,flags,next_offset=struct.unpack_from('<HHBB',lookup,value*256+index*6)
            word=int(table[value,state,0])+256*int(table[value,state,1])
            assert first==labels[f'first_{word>>8}'] and second==labels[f'second_{word&255}']
            assert flags==0 and next_offset==states.index(int(table[value,state,2]))*6
            native_cells+=1
    assert (component/'pcm-high.bin').read_bytes()==bytes(0x40+(value>>2) for value in range(256))
    cases=read(component/'all-cells.json');assert len(cases)==1536
    for case in cases:
        value=case['pcm8']>>2;state=case['initial_state']
        word=int(table[value,state,0])+256*int(table[value,state,1])
        assert case['bits_sha256']==sha(packet_bits(word))
        assert case['bits_exact'] and case['successor_and_next_pointer_exact']
        assert case['no_RAM_writes'] and case['every_hold_tstates']==28
    native_pcm=(component/'trajectory-pcm8.bin').read_bytes()
    native_bits=gzip.decompress((component/'trajectory-bits.u8.gz').read_bytes())
    native_times=np.frombuffer(gzip.decompress((component/'trajectory-times.u32.gz').read_bytes()),'<u4')
    replay=bytearray();state=16
    for value in native_pcm[:-1]:
        row=table[value>>2,state];replay.extend(packet_bits(int(row[0])+256*int(row[1])));state=int(row[2])
    assert bytes(replay)==native_bits and len(native_bits)==16383*16
    assert len(native_times)==len(native_bits) and np.all(np.diff(native_times)==28)
    assert component_report['trajectory']['bits_sha256']==sha(native_bits)
    assert component_report['trajectory']['OUT_times_sha256']==sha(native_times.tobytes())
    bank_report=read(bank/'report.json');assert bank_report['complete'] and not bank_report['quick_subset']
    assert bank_report['native']['cases']==128*256*64+128
    assert bank_report['native']['speaker_writes']==bank_report['native']['cases']*7
    assert bank_report['native']['all_speaker_holds_tstates']==28
    assert bank_report['timing']['additional_OUT_hold_tstates_in_this_component']==0
    for example in bank_report['examples']:
        speaker=[event for event in example['events'] if event[1]&255==254]
        page=[event for event in example['events'] if event[1]&255!=254]
        assert [event[0] for event in speaker]==[11,39,67,95,123,151,179]
        assert page==[[107,0x7FFD,example['paging_byte']]]
    assert (bank_failed/'failure.json').is_file()
    wrong_producer=gzip.decompress((wrong/'producer-source/table_pdm_uniform16_host.py.gz').read_bytes())
    fixed_producer=gzip.decompress((fixed/'producer-source/table_pdm_uniform16_host.py.gz').read_bytes())
    assert b"times=np.arange(len(pulses)+1,dtype='f8')*28" in wrong_producer
    assert b'sample_period=CPU_CLOCK/8000' in fixed_producer
    assert b"*(sample_period/16)" in fixed_producer
    assert fixed_producer==(HERE/'table_pdm_uniform16_host.py').read_bytes()
    assert gzip.decompress((component/'producer.py.gz').read_bytes())==(HERE/'table_pdm_uniform16.py').read_bytes()
    assert gzip.decompress((bank/'producer.py.gz').read_bytes())==(HERE/'table_pdm_uniform16_bank.py').read_bytes()
    assert (wrong/'host.c').read_bytes()==(fixed/'host.c').read_bytes()==(HERE/'table_pdm_uniform16_host.c').read_bytes()
    reuse=read(fixed/'reuse.json');assert reuse['all_prior_artifacts_authenticated'] and reuse['no_repeated_C_encoding']
    assert reuse['manifest_sha256']==sha((wrong/'manifest.json').read_bytes())
    assert reuse['corrected_reference_units_per_Pentagon_T']==CPU_CLOCK/3584000
    rows=[];total=0
    for name in NAMES:
        before=read(wrong/name/'report.json');after=read(fixed/name/'report.json')
        source=evidence/'general/inputs'/(name+'.wav');pcm8=wav8(source)
        packed=gzip.decompress(source.with_suffix('.ima.gz').read_bytes());decoded,_=decode(packed)
        assert len(pcm8)==len(decoded)==SAMPLES[name] and len(packed)*2==SAMPLES[name]
        for report in (before,after):
            assert report['source']==name and report['samples']==SAMPLES[name] and report['complete']
            assert report['source_PCM8_sha256']==sha(pcm8.tobytes()) and report['source_WAV_sha256']==sha(source.read_bytes())
            assert report['frozen_uniform_IMA_sha256']==sha(packed)
            assert report['decoded_PCM16_sha256']==sha(decoded.astype('<i2').tobytes())
            assert report['outputs']==16*SAMPLES[name] and not report['release_accepted']
            assert not report['encoded_for_this_player'] and not report['source_clock_gain_delay_filter_or_edges_fitted']
        assert before['decoded_PCM16_sha256']==after['decoded_PCM16_sha256']
        for field in ('words.u16.gz','states.u8.gz'):
            assert (wrong/name/field).read_bytes()==(fixed/name/field).read_bytes()
        words=np.frombuffer(gzip.decompress((fixed/name/'words.u16.gz').read_bytes()),'<u2')
        actual_states=np.frombuffer(gzip.decompress((fixed/name/'states.u8.gz').read_bytes()),'u1')
        expected_words=np.empty(len(decoded),'u2');expected_states=np.empty(len(decoded),'u1');state=16
        for index,value in enumerate(decoded):
            row=table[(int(value)+32768)>>10,state]
            expected_words[index]=int(row[0])+256*int(row[1]);state=int(row[2]);expected_states[index]=state
        np.testing.assert_array_equal(words,expected_words);np.testing.assert_array_equal(actual_states,expected_states)
        assert after['native_Pentagon_hz']==3584000 and after['render_reference_hz']==CPU_CLOCK
        assert after['reference_ticks_per_sample']==CPU_CLOCK/8000
        assert after['reference_ticks_per_pulse']==CPU_CLOCK/128000
        assert after['execution']['reused'] and after['execution']['seconds']==0
        rows.append(dict(source=name,samples=len(decoded),all_words_states_and_source_hashes_exact=True,
            no_repeated_C_encoding=True,physical_source_hz=8000,
            retained_wrong_render_source_hz=CPU_CLOCK/448,
            corrected_total_SNR_dB=after['SNR']['total']['snr_db'],
            corrected_modulator_SNR_dB=after['SNR']['modulator']['snr_db']))
        total+=len(decoded)
    aggregate=read(fixed/'report.json');assert aggregate['complete'] and aggregate['source_count']==9 and aggregate['samples']==total==1195520
    report=dict(complete=True,date='2026-10-20',authenticated=authenticated,
        artifact_count=sum(row['artifacts'] for row in authenticated),native_table_cells=native_cells,
        native_PCM8_state_cases=len(cases),native_trajectory_outputs=len(native_bits),
        native_component_total_outputs=component_report['total_native_outputs'],
        isolated_bank_native_cases=bank_report['native']['cases'],
        host_source_count=9,host_samples=total,host_decisions=total*16,rows=rows,
        first_host_clock_invalid=True,first_host_inferred_source_hz=CPU_CLOCK/448,
        corrected_physical_source_hz=8000,clock_conversion_is_physical_not_fitted=True,
        original_IMA_and_C_words_preserved=True,no_new_encoder_or_renderer_execution=True,
        source_gain_filter_delay_edges_unchanged=True,
        scope='Manifest, source/hash, decoded-table composition and clock-unit audit. Retained native component and isolated static bank bridge are separate mechanisms; host C IMA decoding is a counterfactual, not concurrent native IMA playback.',
        no_integrated_player_quality_or_release_acceptance=True)
    save(out/'report.json',report)
    (out/'README.md').write_text('''# Uniform table-output evidence audit

Completed2026-10-20 without re-encoding or rendering audio. The report
authenticates every file in the native residentPCM8 component, isolated static
bank bridge, retained failed bank attempt, both complete host render sets and
the first failed audit attempt. It verifies the entire canonical9-source corpus
and all1195520 decoded samples against the frozen C words/states and table.

The first host render incorrectly treated native Pentagon ticks as3546900-Hz
Spectrum-reference ticks. Its source rate was7917.1875Hz despite an8k label.
That attempt remains indexed; its scores are invalid for the canonical8k gate.
The corrected render converts clocks using referenceTicksPerSample=CPU/8000
and referenceTicksPerPulse=CPU/128000. C, model, compressed inputs, decoded
predictors, words and successor states remain unchanged.

The first audit rejected a bank README added after the bank manifest. That
bookkeeping failure is preserved separately. The final audit requires complete
artifact coverage as well as hashes, so a new unindexed document cannot pass.

Native table records are independently composed into packet words and compared
against the host model for all384 reachable level/state cells. All1536 native
PCM8/state cases and262128 trajectory outputs are checked from retained bytes;
native times have exactly28T differences. The bank bridge is an isolated static
I/O mechanism with its own preconditions. None of these records proves an
integrated compressed player, full banked playback, boot or quality acceptance.
''',encoding='utf-8')
    producer=Path(__file__).read_bytes();(out/'producer.py.gz').write_bytes(gzip.compress(producer,mtime=0))
    records=[]
    for path in sorted(out.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();records.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(complete=True,files=records))
    print(json.dumps(dict(complete=True,artifacts=report['artifact_count'],sources=9,samples=total,clock_error_retained=True)))


if __name__=='__main__':main()
