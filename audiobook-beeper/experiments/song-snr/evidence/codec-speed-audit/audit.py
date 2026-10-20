"""Audit retained speed evidence without encoding, decoding or filtering audio."""
import argparse
import ast
import gzip
import hashlib
import json
from pathlib import Path
import re
import statistics
import struct
import wave

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
AUDIO = EVIDENCE.parents[2]
ROOT = AUDIO.parent


def sha(content):
    return hashlib.sha256(content).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def rows_for(manifest):
    value = manifest.get('files', manifest.get('artifact_files'))
    assert value is not None, 'Unrecognized manifest schema'
    if isinstance(value, dict):
        return [dict(path=name, **item) for name, item in value.items()]
    return value


def audit_manifest(path):
    data = read(path)
    assert data.get('complete', True), path
    indexed = set()
    total = 0
    for row in rows_for(data):
        target = (path.parent / row['path']).resolve()
        assert target.is_relative_to(path.parent.resolve()), row['path']
        relative = target.relative_to(path.parent).as_posix()
        assert relative not in indexed, (path, relative)
        indexed.add(relative)
        content = target.read_bytes()
        assert len(content) == row['bytes'], target
        assert sha(content) == row['sha256'], target
        if target.suffix == '.gz':
            gzip.decompress(content)
        total += len(content)
    actual = {p.relative_to(path.parent).as_posix() for p in path.parent.rglob('*') if p.is_file()}
    uncovered = actual-indexed-{path.name}
    historical = path.name == 'initial-manifest.json'
    if historical:
        assert uncovered == {'README.md', 'manifest.json'}, (path, uncovered)
    else:
        assert not uncovered, (path, uncovered)
    return dict(path=path.relative_to(EVIDENCE).as_posix(), sha256=sha(path.read_bytes()),
        indexed_files=len(indexed), indexed_bytes=total, historical_initial_index=historical,
        explicitly_covered_by_final_index=sorted(uncovered), all_hashes_and_gzip_pass=True)


def audit_producers(folder):
    path = folder/'configuration.json'
    if not path.exists():
        return None
    producers = read(path).get('producers')
    if not producers:
        return None
    for name, expected in producers.items():
        snapshot = folder/'producer-source'/(name.replace('/', '__')+'.gz')
        assert sha(gzip.decompress(snapshot.read_bytes())) == expected, snapshot
    return dict(directory=folder.name, producers=len(producers), all_snapshot_source_hashes_pass=True)


def audit_originals():
    prior = EVIDENCE/'table-pdm-uniform16-matched/producer-source'
    names = ['ima_waveform_encoder.py', 'ima_beam.py', 'ima_codec.py',
        'waveform_kernel.py', 'native_waveform_encoder.py', 'precompensate_voice.py',
        'probe_feedback_packets.py', 'verify_direct.py', 'build_pdm.py']
    rows = []
    for name in names:
        before = gzip.decompress((prior/(name+'.gz')).read_bytes())
        current = (AUDIO/name).read_bytes()
        assert current == before, name
        rows.append(dict(path=name, sha256=sha(current), baseline_and_live_identical=True))
    historical = EVIDENCE/'table-pdm-uniform16-final-audit/report.json'
    old_index = read(historical.parent/'manifest.json')
    record = next(row for row in rows_for(old_index) if row['path']=='report.json')
    assert sha(historical.read_bytes()) == record['sha256']
    old_files = {row['path']:row for row in read(historical)['original_files']}
    for name in ['direct_player.py','stream-player.asm','build_stream_trd.py']:
        expected = old_files['audiobook-beeper/'+name]
        content = (AUDIO/name).read_bytes()
        assert len(content)==expected['bytes'] and sha(content)==expected['sha256']
        rows.append(dict(path=name,sha256=sha(content),baseline_and_live_identical=True,
            authenticated_prior_report_sha256=sha(historical.read_bytes())))
    return rows


def audit_disks():
    expected = {
        'ZX-music-Sea-Foam-SNR20-RAM-auto.trd': 'b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e',
        'ZX-music-Sea-Foam-RAM-auto.trd': '226388fb795ac70cfd940545a9eb73e3e81b6c7e96533dc6deb0c215257338ea'}
    rows = []
    for name, identity in expected.items():
        path = Path('C:/Work/ZX-video')/name
        content = path.read_bytes()
        assert len(content) == 655360 and sha(content) == identity, path
        rows.append(dict(path=str(path), bytes=len(content), sha256=identity, unchanged=True))
    return rows


def audit_full_search():
    folder = EVIDENCE/'codec-speed-full'
    context, report = read(folder/'context.json'), read(folder/'report.json')
    assert report['complete'] and report['all_outputs_exact'] and len(report['runs']) == 6
    expected = '44a07e303522dfc4eef31d4654ba35dc6f275d82f6a07d2b3e723155a4d58d06'
    for variant in ['baseline', 'selector']:
        content = gzip.decompress((folder/(variant+'.c.gz')).read_bytes())
        assert sha(content) == context[variant]['source_sha256']
        packed = gzip.decompress((folder/(variant+'.ima.gz')).read_bytes())
        assert len(packed) == 360192 and sha(packed) == expected
    for row in report['runs']:
        assert row['packed_sha256'] == expected and row['packed_bytes'] == 360192
        assert row['statistics'] == dict(samples=720384, search_iterations=1440448,
            final_predictor=0, final_index=0)
    for metric, summary in report['summary'].items():
        old = statistics.median(row[metric] for row in report['runs'] if row['variant']=='baseline')
        new = statistics.median(row[metric] for row in report['runs'] if row['variant']=='selector')
        assert old == summary['baseline_median'] and new == summary['selector_median']
        assert abs(summary['median_reduction_percent']-100*(1-new/old)) < 1e-12
    return dict(whole_song_runs=6, samples_each=720384, packed_bytes_each=360192,
        expected_packed_sha256=expected, all_statistics_source_and_packed_hashes_exact=True,
        saved_timing_summaries_recomputed=True)


def audit_prepare(folder):
    report = read(folder/'report.json')
    assert report['complete'] and report['all22_complete_worksets_match']
    assert report['compared_workset_pairs'] == 22 and len(report['rows']) == 11
    full_sources = set()
    for row in report['rows']:
        assert row['both_complete_worksets_byte_identical'] and row['all_float64_target_bits_exact']
        before, after = row['engines']['python'], row['engines']['native']
        for key in ('samples', 'prior_sha256', 'desired_sha256', 'ids_sha256',
            'successors_sha256', 'feature_shapes', 'workset_sha256_by_bias', 'workset_bytes_by_bias'):
            assert before[key] == after[key], (folder, row['source'], key)
        assert set(before['workset_sha256_by_bias']) == {'0', '512'}
        if row['profile'] == 'uniform':
            full_sources.add(row['source'])
            archived = read(EVIDENCE/'table-pdm-uniform16-matched'/row['source']/'report.json')
            assert before['workset_sha256_by_bias']['0'] == archived['encoding']['statistics']['workset_sha256']
    assert len(full_sources) == 9
    return dict(directory=folder.name, complete_sources=9, nonuniform_controls=2,
        workset_pairs=22, all_recorded_arrays_and_worksets_match=True)


def audit_decode(folder):
    report = read(folder/'report.json')
    assert report['complete'] and report['whole_streams'] == 18
    assert report['original_samples_per_family'] == 1195520
    assert report['all_whole_stream_files_byte_exact'] and len(report['rows']) == 18
    assert not report['compressed_format_changed'] and not report['decoded_semantics_changed']
    assert not report['Z80_hot_path_changed'] and report['Z80_Tstate_delta'] == 0
    for name, key in [('baseline.c','baseline_source_sha256'), ('accelerated.c','accelerated_source_sha256'), ('model.bin','model_sha256')]:
        assert sha((folder/name).read_bytes()) == report[key]
    cases = gzip.decompress((folder/'boundary-cases.i32.gz').read_bytes())
    assert sha(cases) == report['transition_probe']['cases_sha256']
    # The saved records contain index, code, seed, raw predictor, acceptance,
    # and resulting index. They are six int32 fields, not an audio stream.
    assert len(cases) == report['transition_probe']['boundary_cases']*6*4
    constants = {}
    tree = ast.parse(gzip.decompress((folder/'ima_codec.py.gz').read_bytes()))
    for statement in tree.body:
        if isinstance(statement, ast.Assign):
            for target in statement.targets:
                if isinstance(target, ast.Name) and target.id in ('STEPS','INDEX'):
                    constants[target.id] = ast.literal_eval(statement.value)
    for index, code, seed, value, accepted, actual_index in struct.iter_unpack('<6i', cases):
        step = constants['STEPS'][index]
        delta = (step>>3)+(step if code&4 else 0)+(step>>1 if code&2 else 0)+(step>>2 if code&1 else 0)
        if code&8:delta=-delta
        wanted_value = seed+delta
        wanted_acceptance = -32768 <= wanted_value <= 32767
        wanted_index = min(88,max(0,index+constants['INDEX'][code&7])) if wanted_acceptance else index
        assert value == wanted_value and bool(accepted) == wanted_acceptance and actual_index == wanted_index
    totals = {}
    for row in report['rows']:
        assert row['old_new_all_files_and_CLI_exact'] and row['independent_Python_PCM16_exact']
        matched = row['family'] == 'matched'
        packed_file = (EVIDENCE/'table-pdm-uniform16-matched'/row['source']/'packed.ima.gz') if matched else (EVIDENCE/'general/inputs'/(row['source']+'.ima.gz'))
        packed = gzip.decompress(packed_file.read_bytes())
        assert len(packed) == row['compressed_bytes'] and sha(packed) == row['compressed_sha256']
        old = EVIDENCE/('table-pdm-uniform16-matched-quality' if matched else 'table-pdm-uniform16-host-8k')/row['source']
        prior = read(old/'report.json')
        assert row['samples'] == prior['samples']
        for binary in ('words.u16','states.u8'):
            raw = gzip.decompress((old/(binary+'.gz')).read_bytes())
            assert len(raw)==row['output_files'][binary]['bytes'] and sha(raw)==row['output_files'][binary]['sha256']
        assert row['output_files']['decoded.pcm16']['sha256'] == prior['decoded_PCM16_sha256']
        totals[row['family']] = totals.get(row['family'],0)+row['samples']
    assert totals == {'canonical':1195520,'matched':1195520}, totals
    return dict(directory=folder.name, complete_streams=18, source_samples_per_family=1195520,
        historical_words_states_pcm_and_compressed_hashes_match=True, transition_cases=14192,
        Z80_Tstate_delta=0)


def audit_integration():
    folder = EVIDENCE/'codec-speed-integration'
    report = read(folder/'report.json')
    assert report['complete'] and report['all_nine_original_complete_streams_identical']
    assert report['total_samples'] == 1195520 and len(report['rows']) == 9
    samples = 0
    for row in report['rows']:
        name = row['source']
        before_folder = EVIDENCE/'table-pdm-uniform16-matched'/name
        after_folder = folder/'optimized'/name
        before, after = read(before_folder/'report.json'), read(after_folder/'report.json')
        source_file=EVIDENCE/'general/inputs'/(name+'.wav')
        assert sha(source_file.read_bytes())==before['source_identity']['wav_sha256']
        with wave.open(str(source_file),'rb') as reader:
            assert (reader.getnchannels(),reader.getsampwidth(),reader.getframerate())==(1,1,8000)
            original_pcm=reader.readframes(reader.getnframes())
        assert len(original_pcm)==row['samples'] and sha(original_pcm)==before['source_sha256']
        old_packed = gzip.decompress((before_folder/'packed.ima.gz').read_bytes())
        new_packed = gzip.decompress((after_folder/'packed.ima.gz').read_bytes())
        assert old_packed == new_packed and sha(new_packed) == row['packed_sha256']
        assert len(new_packed) == row['packed_bytes'] and len(new_packed)*2 == row['samples']
        assert (before_folder/'encoding-prior.wav').read_bytes() == (after_folder/'encoding-prior.wav').read_bytes()
        for key in ('source_sha256','source_samples','packed_sha256','packed_bytes',
            'decoded_pcm16_sha256','final_predictor','final_index','encoded_prior_pcm8_sha256'):
            assert before[key] == after[key], (name,key)
        for key in ('workset_sha256','workset_bytes','samples','search_iterations','final_predictor','final_index'):
            assert before['encoding']['statistics'][key] == after['encoding']['statistics'][key]
        marker = read(after_folder/'complete.json')
        for file, identity in marker['files'].items():
            raw=(after_folder/file).read_bytes()
            assert len(raw)==identity['bytes'] and sha(raw)==identity['sha256']
        samples += row['samples']
    assert samples==1195520
    return dict(whole_sources=9,total_samples=samples,every_original_source_WAV_and_PCM8_hash_exact=True,
        every_compressed_byte_prior_and_workset_hash_exact=True,
        recorded_decoded_pcm_and_statistics_match=True,per_source_completion_markers_pass=True)


def audit_z80():
    folder=EVIDENCE/'codec-speed-z80-review'
    report=read(folder/'report.json')
    assert report['complete'] and report['no_new_TRD_or_full_player_or_hardware_claim']
    for name, identity in report['source_files'].items():
        raw=(AUDIO/name).read_bytes()
        assert len(raw)==identity['bytes'] and sha(raw)==identity['sha256']
    core=report['live_decoder_core']
    assert sum(row['tstates'] for row in core['ledger'])==core['total_tstates']==49
    assert core['with_register_exchange_tstates']==49+2*4==57
    cases=report['bounded_native_confirmation']['cases']
    assert len(cases)==32 and report['bounded_native_confirmation']['actual_machine_cases']==32
    for row in cases:
        assert row['exact_register_result'] and row['actual_tstates']==(57 if row['surrounding_EXX'] else 49)
    old=report['unchanged_player']
    assert old['instruction_changes']==old['core_Tstate_delta']==0
    assert (old['ordinary_Pentagon_Tstates'],old['page_extra_Tstates'],old['bank_extra_Pentagon_Tstates'])==(449,14,243)
    previous=EVIDENCE/'table-pdm-uniform16-paged-component/report.json'
    assert sha(previous.read_bytes())==report['existing_uniform_component']['report_sha256']
    assert not report['existing_uniform_component']['includes_live_IMA_decode']
    return dict(source_hashes=len(report['source_files']),saved_native_cases=32,core_Tstates=49,
        with_register_exchange_Tstates=57,actual_player_instruction_or_Tstate_delta=0,
        no_native_execution_repeated=True,retained_initial_harness_failure=True)


def audit_links():
    path=AUDIO/'CODEC_SPEED.md'
    links=[]
    for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
        if '://' in target or target.startswith('#'):continue
        target=target.strip('<>').split('#',1)[0]
        assert (path.parent/target).resolve().exists(), target
        links.append(target)
    return dict(path='audiobook-beeper/CODEC_SPEED.md',sha256=sha(path.read_bytes()),
        local_links=links,all_local_targets_exist=True)


def audit_conversion():
    folder=EVIDENCE/'codec-speed-conversion'
    report=read(folder/'report.json')
    assert report['complete'] and report['old_and_new_TRD_identical_to_delivered_disk']
    assert not report['format_changed'] and report['exact_player_hot_path_delta_tstates']==0
    assert len(report['rows'])==2 and not report['optional_full_Fuse_repeated']
    artifacts=read(folder/'artifacts.json')
    before,after=read(folder/'baseline.json'),read(folder/'optimized.json')
    assert before['complete'] and after['complete']
    for key in ['parameters','model','source_sha256','packed_sha256','trd_sha256']:
        assert before[key]==after[key], key
    expected_packed='2b30481f7340698b26e256bfea6636adfd8b8a162bf5030dc5b08d16078f49f1'
    expected_trd='b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e'
    assert before['packed_sha256']==expected_packed and before['trd_sha256']==expected_trd
    assert before['preparation']['prepared_samples']==after['preparation']['prepared_samples']==720384
    assert before['preparation']['prepared_pcm_unchanged'] and after['preparation']['prepared_pcm_unchanged']
    verified_files=0
    for engine in ['baseline','optimized']:
        for name,identity in artifacts[engine].items():
            actual=ROOT/'.tmp/codec-speed-conversion'/engine/name
            content=actual.read_bytes()
            assert len(content)==identity['bytes'] and sha(content)==identity['sha256'],actual
            if name!='conversion.json':assert artifacts['baseline'][name]==artifacts['optimized'][name],name
            verified_files+=1
        packed=gzip.decompress((ROOT/'.tmp/codec-speed-conversion'/engine/'soundtrack.ima.gz').read_bytes())
        assert len(packed)==360192 and sha(packed)==expected_packed
        assert (ROOT/'.tmp/codec-speed-conversion'/engine/'audio.trd').read_bytes()==Path('C:/Work/ZX-video/ZX-music-Sea-Foam-SNR20-RAM-auto.trd').read_bytes()
    seconds={row['engine']:row['external_complete_process_seconds'] for row in report['rows']}
    assert abs(report['ratio']-seconds['baseline']/seconds['optimized'])<1e-14
    assert sha(gzip.decompress((folder/'baseline.c.gz').read_bytes()))==read(EVIDENCE/'codec-speed-full/context.json')['baseline']['source_sha256']
    return dict(full_public_conversions=2,whole_source_samples_each=720384,
        original449_packed_sha256=expected_packed,entire_TRD_sha256=expected_trd,
        actual_scratch_artifact_files_rehashed=verified_files,
        payload_prior_preview_and_disk_bytes_identical=True,
        metadata_conversion_reports_may_differ=True,distinct_from_uniform16_experiment=True,
        single_pair_wall_seconds=seconds,complete_conversion_ratio_recomputed=True)


def audit_tests():
    folder=EVIDENCE/'codec-speed-tests'
    report=read(folder/'report.json')
    assert report['complete'] and report['exit_code']==0 and report['unittest_success']
    assert report['tests']==28 and not report['skipped_lines']
    log=(folder/'tests.log').read_text(encoding='utf-8')
    assert re.search(r'Ran 28 tests in [0-9.]+s',log) and re.search(r'\nOK\s*$',log)
    assert not re.search(r'^(FAILED|ERROR:|FAIL:)',log,re.MULTILINE)
    snapshots=[]
    for path in sorted((folder/'producer-source').glob('*.gz')):
        relative=path.name[:-3].replace('__','/')
        snapshot=gzip.decompress(path.read_bytes())
        assert snapshot==(AUDIO/relative).read_bytes(),relative
        snapshots.append(dict(path=relative,sha256=sha(snapshot),live_bytes_equal_tested_snapshot=True))
    assert sha(Path(report['FFmpeg']).read_bytes())==report['FFmpeg_sha256']
    return dict(tests=28,exit_code=0,skips=0,recorded_log_success=True,
        tested_producers=snapshots,FFmpeg_binary_sha256_verified=True,
        no_test_or_emulator_rerun=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',type=Path,default=HERE/'configuration.json')
    parser.add_argument('--output',type=Path,default=HERE/'report.json')
    args=parser.parse_args()
    config=read(args.configuration)
    manifests=[]
    producer_sets=[]
    files=set()
    for name in config['evidence_sets']:
        folder=EVIDENCE/name
        paths=sorted(folder.rglob('*manifest.json'))
        assert paths and (folder/'manifest.json').exists(), folder
        manifests.extend(audit_manifest(path) for path in paths)
        entry=audit_producers(folder)
        if entry:producer_sets.append(entry)
        files.update(p.relative_to(EVIDENCE).as_posix() for p in folder.rglob('*') if p.is_file())
    report=dict(complete=True,date='2026-10-20',scope=__doc__,configuration_sha256=sha(args.configuration.read_bytes()),
        audit_source_sha256=sha(Path(__file__).read_bytes()),
        manifests=manifests,manifest_count=len(manifests),unique_artifact_files_including_indexes=len(files),
        producer_snapshot_sets=producer_sets,original_unchanged_sources=audit_originals(),
        delivered_disks=audit_disks(),full_search=audit_full_search(),
        preparation=[audit_prepare(EVIDENCE/name) for name in ['native-prepare-speed','native-prepare-hash-speed']],
        decoder=[audit_decode(EVIDENCE/name) for name in ['table-pdm-decode-speed','table-pdm-decode-speed-final']],
        integration=audit_integration(),Z80_review=audit_z80(),documentation_links=audit_links(),
        public_conversion=audit_conversion(),final_tests=audit_tests(),
        no_codec_native_emulator_filter_or_encode_rerun=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(complete=True,manifests=len(manifests),unique_artifact_files=len(files),
        all_hashes_and_semantic_crosschecks_pass=True)),flush=True)


if __name__=='__main__':main()
