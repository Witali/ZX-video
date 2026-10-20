"""Audit matched uniform-table encodes and diagnose retained filtered arrays.

No encoder, compiler, FFmpeg or renderer is executed. Source-correlated fits
are indicators only; all scores retain the unfitted original8k source clock.
The canonical frozen-IMA control shares the new flat uniform table/clock and
is distinct from the delivered player's separately measured449T schedule.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np

from artifact_diagnostics import compare_reports, tone_diagnostics, waveform_diagnostics
from ima_codec import decode
from pacing448_spectrum import spectrum
from pdm_player import CPU_CLOCK
from probe_reconstruction_error import wav8
from study import metrics
from table_pdm_uniform16_audit import NAMES, SAMPLES, authenticate

HERE=Path(__file__).resolve().parent
AUDIO=HERE.parents[1]
FREQUENCIES=(8000/32768,8000/16384,2.,5.,10.,8000/512,25.,8000/256,50.,8000/128,100.,8000/64)
TONES=dict(quiet440=440,quiet997=997,loud3000=3000)


def sha(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_bytes())
def save(path,value):path.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8')
def fingerprint(value):return sha(json.dumps(value,sort_keys=True,allow_nan=False).encode())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,
        default=HERE/'evidence/table-pdm-uniform16-quality-audit')
    parser.add_argument('--matched-cache',type=Path,default=AUDIO.parents[0]/'.tmp/table-pdm-uniform16-matched-quality')
    parser.add_argument('--canonical-cache',type=Path,default=AUDIO.parents[0]/'.tmp/table-pdm-uniform16-host-8k')
    args=parser.parse_args();out=args.output.resolve()
    if out.exists():raise FileExistsError('Preserve completed or partial audit: '+str(out))
    out.mkdir(parents=True);evidence=HERE/'evidence'
    matched=evidence/'table-pdm-uniform16-matched';quality=evidence/'table-pdm-uniform16-matched-quality'
    canonical=evidence/'table-pdm-uniform16-host-8k';component=evidence/'table-pdm-uniform16-component'
    prior=evidence/'table-pdm-uniform16-audit'
    authenticated=[authenticate(folder) for folder in (matched,quality,canonical,component,prior)]
    configuration=read(matched/'configuration.json');identity=fingerprint(configuration)
    aggregate=read(matched/'report.json');quality_all=read(quality/'report.json')
    assert aggregate['complete'] and aggregate['all_nine_sources_encoded']
    assert aggregate['configuration_sha256']==identity
    assert configuration['model']==dict(holds=[28]*16,beta=.5,extent=.5,pcm_origin=0)
    assert configuration['search']==dict(width=32,horizon=128,commit=64,regularization=.1,final_silent_guard_samples=128)
    assert configuration['source_rate_hz']==8000 and configuration['physical_CPU_hz']==3584000
    assert configuration['physical_hold_T']==28 and configuration['physical_period_T']==448
    assert configuration['renderer_interval_reference_units']==CPU_CLOCK/128000
    assert configuration['no_clock_gain_delay_fit'] and configuration['original_reference_samples_changed']==0
    assert configuration['source_independent_parameters'] and not configuration['full_player_verified']
    producer_checks=[]
    for name,expected in configuration['producers'].items():
        frozen=gzip.decompress((matched/'producer-source'/(name.replace('/','__')+'.gz')).read_bytes())
        assert sha(frozen)==expected and (AUDIO/name).read_bytes()==frozen
        producer_checks.append(dict(path=name,sha256=expected,current_matches_frozen=True))
    old_host=gzip.decompress((canonical/'producer-source/table_pdm_uniform16_host.py.gz').read_bytes())
    new_host=gzip.decompress((quality/'producer-source/table_pdm_uniform16_host.py.gz').read_bytes())
    assert old_host!=new_host and b'--packed-dir' not in old_host and b'--packed-dir' in new_host
    assert new_host==(HERE/'table_pdm_uniform16_host.py').read_bytes()
    assert (canonical/'host.c').read_bytes()==(quality/'host.c').read_bytes()==(HERE/'table_pdm_uniform16_host.c').read_bytes()
    assert (canonical/'model.bin').read_bytes()==(quality/'model.bin').read_bytes()
    model=np.frombuffer((quality/'model.bin').read_bytes(),'u1').reshape(64,32,3)
    rows=[];regressions={};total=0
    archived=read(evidence/'clock-joint/report.json')
    own_clock_song=next(row for row in archived['rows'] if row['source']=='sea_foam')
    for name in NAMES:
        source_path=evidence/'general/inputs'/(name+'.wav');source=wav8(source_path)
        encode_report=read(matched/name/'report.json');score=read(quality/name/'report.json')
        control=read(canonical/name/'report.json');marker=read(matched/name/'complete.json')
        assert marker['configuration_sha256']==identity
        assert encode_report['configuration_sha256']==identity and encode_report['model']==configuration['model']
        assert len(source)==SAMPLES[name] and np.all(source[-128:]==128)
        source_identity=configuration['sources'][name]
        assert source_identity['pcm8_sha256']==encode_report['source_sha256']==sha(source.tobytes())
        assert source_identity['wav_sha256']==sha(source_path.read_bytes())
        prior_source=wav8(matched/name/'encoding-prior.wav');np.testing.assert_array_equal(prior_source,source)
        assert encode_report['prior_differs_original_samples']==0
        assert encode_report['encoded_prior_pcm8_sha256']==sha(source.tobytes())
        packed=gzip.decompress((matched/name/'packed.ima.gz').read_bytes());decoded,indices=decode(packed)
        assert len(packed)==len(source)//2==encode_report['packed_bytes']
        assert len(decoded)==len(source)==encode_report['decoded_samples']
        assert encode_report['packed_sha256']==score['frozen_uniform_IMA_sha256']==sha(packed)
        assert encode_report['decoded_pcm16_sha256']==score['decoded_PCM16_sha256']==sha(decoded.astype('<i2').tobytes())
        assert (int(decoded[-1]),int(indices[-1]))==(0,0)
        assert score['encoded_for_this_player'] and not score['release_accepted']
        assert score['source_PCM8_sha256']==sha(source.tobytes()) and score['samples']==len(source)
        assert score['reference_ticks_per_sample']==CPU_CLOCK/8000
        assert score['reference_ticks_per_pulse']==CPU_CLOCK/128000
        assert not score['source_clock_gain_delay_filter_or_edges_fitted']
        statistics=encode_report['encoding']['statistics']
        assert statistics['backend']=='standalone-c' and not statistics['child_python_runtime']
        assert statistics['samples']==len(source)
        actual_words=np.frombuffer(gzip.decompress((quality/name/'words.u16.gz').read_bytes()),'<u2')
        actual_states=np.frombuffer(gzip.decompress((quality/name/'states.u8.gz').read_bytes()),'u1')
        expected_words=np.empty(len(decoded),'u2');expected_states=np.empty(len(decoded),'u1');state=16
        for index,value in enumerate(decoded):
            row=model[(int(value)+32768)>>10,state]
            expected_words[index]=int(row[0])+256*int(row[1]);state=int(row[2]);expected_states[index]=state
        np.testing.assert_array_equal(actual_words,expected_words);np.testing.assert_array_equal(actual_states,expected_states)
        variants={};references=[]
        for label,cache,score_row in (('canonical_frozen_IMA_uniform_table',args.canonical_cache,control),
                                    ('matched_IMA_uniform_table',args.matched_cache,score)):
            actual=np.load(cache/name/'actual.npy');reference=np.load(cache/name/'source.npy');ideal=np.load(cache/name/'ideal.npy')
            assert actual.dtype==reference.dtype==ideal.dtype==np.dtype('float64')
            assert actual.ndim==reference.ndim==ideal.ndim==1 and len(actual)==len(reference)==len(ideal)
            assert np.all(np.isfinite(actual)) and np.all(np.isfinite(reference)) and np.all(np.isfinite(ideal))
            assert metrics(reference,actual)==score_row['SNR']['total']
            assert metrics(ideal,actual)==score_row['SNR']['modulator']
            assert metrics(reference,ideal)==score_row['SNR']['ideal_IMA']
            data=dict(source=name,variant=label,reference_float64_sha256=sha(reference.tobytes()),
                actual_float64_sha256=sha(actual.tobytes()),ideal_float64_sha256=sha(ideal.tobytes()),
                waveform=waveform_diagnostics(reference,actual,frequencies=FREQUENCIES),
                whole_error_spectrum=spectrum(actual-reference),
                source_clock_hz=8000,host_counterfactual=True,integrated_native_player=False)
            if name in TONES:data['known_tone']=tone_diagnostics(reference,actual,TONES[name],frequencies=FREQUENCIES)
            save(out/(name+'-'+label+'.json'),data);variants[label]=data;references.append(data['reference_float64_sha256'])
            print(json.dumps(dict(source=name,variant=label,complete=True)),flush=True)
        assert references[0]==references[1]
        comparison=compare_reports(*variants.values());save(out/(name+'-comparison.json'),comparison)
        for key,value in comparison['numeric_regressions'].items():regressions[key]=regressions.get(key,0)+int(value)
        before=control['SNR']['total']['snr_db'];after=score['SNR']['total']['snr_db']
        rows.append(dict(source=name,samples=len(source),IMA_bytes=len(packed),configuration_sha256=identity,
            canonical_frozen_IMA_SNR_dB=before,matched_IMA_SNR_dB=after,
            matched_minus_canonical_dB=after-before if before is not None and after is not None else None,
            matched_PDM_only_SNR_dB=score['SNR']['modulator']['snr_db'],
            matched_error_rms=score['SNR']['total']['error_rms'],
            reference_float64_sha256=references[0],numeric_regressions=comparison['numeric_regressions'],
            matched_tone_phase_reliable=variants['matched_IMA_uniform_table'].get('known_tone',{}).get('phase_tracking_reliable')))
        total+=len(source)
        save(out/'partial.json',dict(complete=False,rows=rows,numeric_regression_counts=regressions))
    assert total==quality_all['samples']==1195520 and quality_all['source_count']==9 and quality_all['complete']
    assert not quality_all['uniform_IMA_frozen_no_joint_reencoding']
    song=next(row for row in rows if row['source']=='sea_foam')
    report=dict(complete=True,date='2026-10-20',configuration_sha256=identity,
        authenticated=authenticated,artifact_count=sum(row['artifacts'] for row in authenticated),
        producer_checks=producer_checks,host_wrapper_versions=dict(canonical_sha256=sha(old_host),
            matched_sha256=sha(new_host),different_because_explicit_packed_dir_added=True,
            original_C_and_table_unchanged=True,old_frozen_producer_retained=True),
        source_count=9,samples=total,decisions=total*16,rows=rows,numeric_regression_counts=regressions,
        frequencies_hz=FREQUENCIES,frequency_meanings=dict(IMA_bank_32768_samples=8000/32768,
            resident_PCM8_bank_16384_samples=8000/16384,IMA_page_512_samples=8000/512,
            resident_PCM8_page_256_samples=8000/256,horizon_128_samples=8000/128,commit_64_samples=8000/64),
        matched_song=dict(host_SNR_dB=song['matched_IMA_SNR_dB'],
            same_uniform_table_canonical_IMA_SNR_dB=song['canonical_frozen_IMA_SNR_dB'],
            source_own_clock_delivered449_SNR_dB=own_clock_song['fixed_clock']['snr_db'],
            own_clock_delivered_comparison_is_separate_player_schedule=True),
        all_original_source_samples_preserved=True,shared_preset_on_all_sources=True,
        no_encoder_compiler_filter_or_renderer_rerun=True,all_fits_diagnostic_only=True,
        source_clock_gain_delay_filter_and_edges_unfitted=True,
        release_accepted=False,artifact_acceptance=False,
        limitations=['Host counterfactual: C decoding is not an integrated native IMA player.',
            'ResidentPCM8 native component and static paging bridge have separate register/precondition contracts.',
            'Canonical frozen-IMA same-uniform-table control is not the delivered449T player.',
            'Short synthetic controls do not establish low-frequency periodic absence or long-term stability.',
            'Rank-deficient or inapplicable fits and unreliable tone phase estimates are inconclusive.',
            'Every numerical diagnostic increase is disclosed; no audibility threshold or unconditional artifact gate is invented.',
            'Cold boot, all bank boundaries/EOF, clone timing and full emulator playback remain unproved.'])
    save(out/'report.json',report)
    lines=['# Matched uniform-table quality audit','','Executed2026-10-20 from existing cachedfloat64 arrays. No audio was re-encoded or rendered.','',
        '|Source|Canonical frozen IMA / uniform table dB|Matched IMA / uniform table dB|Change dB|',
        '|---|---:|---:|---:|']
    number=lambda x:'n/a' if x is None else f'{x:.6f}'
    for row in rows:lines.append('|'+row['source']+'|'+number(row['canonical_frozen_IMA_SNR_dB'])+'|'+number(row['matched_IMA_SNR_dB'])+'|'+number(row['matched_minus_canonical_dB'])+'|')
    lines+=['','The delivered449T player has its own measured song score20.250315887dB. Its schedule is separate from both flat-uniform host controls above; no full native player claim follows. Silence uses absolute error RMS rather than SNR.','',
        'All9 sources retain original hashes, full sample counts and the final128 original silent samples. One frozen C preset uses width32, horizon128, commit64, regularization0.1, beta0.5 and extent0.5. The song remains360192 IMA bytes. All predictors, words and successor states are independently checked.','',
        'Waveform, known-tone and whole-error spectral diagnostics cover both same-clock controls at the declared bank/page/search/field frequencies, including0.48828125Hz for residentPCM8 banks. Fits are diagnostic only and never modify SNR. Short controls, rank-deficient fits and unreliable fundamental tracking remain inconclusive. Every numerical increase is retained in the comparison files; this is not unconditional artifact acceptance.','',
        'The host wrapper gained an explicit --packed-dir input after the canonical frozen-IMA archives. Both versions are frozen; their Python hashes differ intentionally while the C decoder and table bytes remain identical. The original incorrectly scaled host render is preserved by the prior audit and is not used in this comparison.','',
        'There is no integrated native IMA decode/bank/EOF/bootable-disk proof in this host quality result. Release and artifact acceptance remain false.']
    (out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    for producer in (Path(__file__),HERE/'table_pdm_uniform16_audit.py',HERE/'artifact_diagnostics.py',HERE/'pacing448_spectrum.py',HERE/'study.py'):
        target=out/'producer-source'/(producer.name+'.gz');target.parent.mkdir(exist_ok=True)
        target.write_bytes(gzip.compress(producer.read_bytes(),mtime=0))
    records=[]
    for path in sorted(out.rglob('*')):
        if path.is_file():
            raw=path.read_bytes();records.append(dict(path=path.relative_to(out).as_posix(),bytes=len(raw),sha256=sha(raw)))
    save(out/'manifest.json',dict(complete=True,files=records))
    print(json.dumps(dict(complete=True,sources=9,samples=total,numeric_regressions=regressions)),flush=True)


if __name__=='__main__':main()
