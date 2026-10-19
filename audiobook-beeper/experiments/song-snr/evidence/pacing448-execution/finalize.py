"""Seal completed 448-T execution evidence without promoting a release."""
import gzip
import hashlib
import json
from pathlib import Path
import platform


ROOT = Path(__file__).resolve().parent
AUDIO = ROOT.parents[3]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def main():
    sources = ['sea_foam', 'long_silence', 'long_quiet997']
    native_profiles = ['128', 'scorpion', 'pentagon512', 'pentagon1024']
    rows = []
    for name in sources:
        dest = ROOT / name
        identity, meta = read(dest / 'identity.json'), read(dest / 'player.json')
        assert sha((dest / 'audio.trd').read_bytes()) == identity['trd_sha256'] == meta['trd_sha256']
        assert sha(gzip.decompress((dest / 'soundtrack.ima.gz').read_bytes())) == identity['packed_sha256']
        assert sha((dest / 'host.json').read_bytes()) == identity['host_sha256']
        native = {}
        for profile in native_profiles:
            report = read(dest / 'verification' / ('native-' + profile + '.json'))
            assert report['complete'] and report['every_bit_predictor_index_exact']
            assert report['every_continuous_native_hold_exact'] and report['memory_guards_passed']
            assert report['ordinary_tstates'] == (448 if profile.startswith('pentagon') else 423)
            native[profile] = report
        actual = {}
        for profile in (['pentagon512', 'pentagon1024'] if name == 'sea_foam' else ['pentagon512']):
            root = dest / 'verification' / profile
            report, quality = read(root / 'report.json'), read(root / 'quality.json')
            assert report['complete'] and report['independently_cold_booted'] and report['end_of_audio_reached']
            assert report['trd_sha256'] == meta['trd_sha256']
            assert report['reloads'] == report['runtime_disk_reads_during_live_audio'] == 0
            assert quality['every_source_timestamp_matches_independently_counted_448_schedule']
            assert quality['maximum_timestamp_error_tstates'] == 0 and quality['host_prediction_reproduced']
            raw = gzip.decompress((root / 'times.u32.gz').read_bytes())
            assert sha(raw) == quality['relative_source_timestamps_sha256']
            assert len(raw) == 4 * report['bits_verified']
            assert quality['audio_progress_ui_captured'] == (name == 'sea_foam')
            if name == 'sea_foam':
                assert report['audio_progress_ui']['complete']
                assert len(quality['exact_progress_geometry']) == 22
            actual[profile] = dict(fuse=report, quality=quality)
        rows.append(dict(source=name, identity=identity, native=native, actual=actual))
    song_actual = rows[0]['actual']
    assert song_actual['pentagon512']['quality']['relative_source_timestamps_sha256'] == song_actual['pentagon1024']['quality']['relative_source_timestamps_sha256']
    producer_names = [
        'build_stream_trd.py', 'direct_player.py', 'stream-player.asm',
        'stream-worker.asm', 'stream-progress.asm', 'stream-audio-ui.asm',
        'stream-audio-ui-helper.asm', 'stream-playback-progress.asm',
        'ram-cache.asm', 'ram_cache.py', 'ram_machine.py',
        'verify_stream_trd.py', 'verify_direct.py', 'verify_pcm.py',
        'probe_feedback_packets.py', 'ima_codec.py', 'build_pdm.py',
        'audio_cover.py', 'convert_mulaw_audio.py',
        'experiments/song-snr/study.py',
        'experiments/song-snr/pacing448_execute.py',
    ]
    producers = {}
    for name in producer_names:
        raw = (AUDIO / name).read_bytes()
        target = ROOT / 'producer-source' / (name + '.gz')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(gzip.compress(raw, mtime=0))
        producers[name] = sha(raw)
    report = dict(
        complete=True, date='2026-10-19', rows=rows,
        complete_native_runs=12, complete_independent_cold_fuse_runs=4,
        capture_recheck_of_final_execution_script=True,
        python_version=platform.python_version(), producer_sha256=producers,
        installed_fuse_sha256='e7aba457ea405f8e2fcab9d4bc703e9f1013453726e178d8c7333ce9685a1266',
        source_modulation_table_weights_sum=449, physical_pentagon_ordinary_tstates=448,
        source_modulation_table_changed=False,
        hot_path_delta_tstates=dict(pentagon=-1, spectrum128=0, scorpion=0),
        page_extra_tstates=14, bank_extra_tstates=dict(pentagon=243, scorpion=267),
        source_specific_fitted_gain_delay_clock=False,
        ui_scope='Whole song on Pentagon512 and1024: light-gray LOADING cycle and22 exact source-position green updates. Shorter long-tone controls explicitly disable UI because their per-bank progress jump exceeds the preserved two-cell live update limit.',
        failed_attempt='long_silence/failure-build-ui.json preserves the rejected enabled-UI short-source build; no emulator ran for that attempt.',
        scope='Whole song plus16.448-second silence and quiet997 controls. All four native profiles check bits, states, continuous holds, RAM and refills; actual cold Fuse coverage is the listed four Pentagon runs. No whole-corpus or128/Scorpion actual audio-quality claim.',
        artifact_acceptance_not_established=True,
        release_accepted=False, main_release_modified=False, physical_hardware_tested=False,
        reproduction=[
            'python audiobook-beeper/experiments/song-snr/pacing448_execute.py --phase native --source sea_foam --scratch .tmp/pacing448-execution-native-scratch --jobs 2',
            'python audiobook-beeper/experiments/song-snr/pacing448_execute.py --phase fuse --source sea_foam --scratch .tmp/pacing448-execution-scratch --jobs 2',
            'python audiobook-beeper/experiments/song-snr/pacing448_execute.py --phase all --source long_silence --source long_quiet997 --without-ui --scratch .tmp/pacing448-execution-long-scratch --jobs 2',
            'python audiobook-beeper/experiments/song-snr/pacing448_execute.py --phase fuse --source sea_foam --captured --scratch .tmp/pacing448-execution-recheck-scratch --jobs 2',
            'python audiobook-beeper/experiments/song-snr/evidence/pacing448-execution/finalize.py',
        ])
    save(ROOT / 'report.json', report)
    artifacts = {}
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and path.name != 'manifest.json' and '__pycache__' not in path.parts:
            raw = path.read_bytes()
            artifacts[path.relative_to(ROOT).as_posix()] = dict(bytes=len(raw), sha256=sha(raw))
    save(ROOT / 'manifest.json', dict(complete=True, artifact_files=artifacts))
    print(json.dumps(dict(complete=True, native_runs=12, cold_fuse_runs=4,
                          artifacts=len(artifacts), release_accepted=False)))


if __name__ == '__main__':
    main()
