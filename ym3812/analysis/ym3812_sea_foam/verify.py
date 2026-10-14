"""Independently re-export and replay every sample of the complete song."""
import argparse
import gzip
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave

import numpy as np
import ymfm

CORE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(CORE))
import experimental_ym3812 as opl
from support import save
from test_experimental_ym3812 import audit


def pcm(path, frames, rate=44100):
    with wave.open(str(path), 'rb') as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate(), stream.getnframes()) == (1, 2, rate, frames)
        return stream.readframes(frames)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--tests', type=Path, required=True)
    parser.add_argument('--song', type=Path, required=True)
    parser.add_argument('--ffmpeg', required=True)
    args = parser.parse_args()
    evidence = args.evidence
    report = json.loads((evidence / 'report.json').read_bytes())
    assert report['complete'] and report['seconds'] == 90 and report['fields'] == 4500
    assert report['selected'] == 'smooth' and not report['source_pcm_in_output']
    assert report['nominal_transition_ms'] == 2 and report['transition_steps'] == 8 and report['ordered_pitch']
    assert opl.sha(args.song.read_bytes()) == report['original_song_sha256']
    assert importlib.metadata.version('ymfm-py') == report['ymfm_py_version'] == '0.2.0'
    assert opl.sha(next(Path(ymfm.__file__).parent.glob('*.pyd')).read_bytes()) == report['native_core_sha256']
    for name, expected in report['artifacts_sha256'].items():
        assert opl.sha((evidence / name).read_bytes()) == expected, name
    for name, expected in report['producer_sources_sha256_lf'].items():
        assert opl.sha((CORE / name).read_bytes().replace(b'\r\n', b'\n')) == expected, name
    # Recreate both reference-rate files from the authenticated stereo source.
    # No source data enters a YM3812 replay below.
    temporary = CORE.parent / '.tmp'; temporary.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=temporary, prefix='song-verify-') as directory:
        folder = Path(directory)
        for rate, target, source in ((22050, 'reference.wav', args.song),
                                     (44100, 'comparison-source.wav', evidence / 'reference.wav')):
            command = [args.ffmpeg, '-hide_banner', '-loglevel', 'error', '-i', str(source)]
            command += ['-af', 'pan=mono|c0=0.5*c0+0.5*c1,aresample=22050'] if rate == 22050 else ['-ar', '44100']
            subprocess.run(command + ['-c:a', 'pcm_s16le', '-bitexact', str(folder / target)], check=True)
            assert (folder / target).read_bytes() == (evidence / target).read_bytes(), target
    with np.load(evidence / 'controls.npz') as stored:
        controls = {key: stored[key] for key in stored.files}
    assert opl.validate(controls) == 4500 and np.isin(controls['patch'], [0, 14]).all()
    streams = []
    for trial in report['trials']:
        name = trial['name']
        data = gzip.decompress((evidence / (name + '.vgz')).read_bytes())
        encoded, writes = opl.smooth_vgm(controls) if name == 'smooth' else opl.vgm(controls)
        assert data == encoded and writes == trial['writes']
        assert len(data) == trial['vgm_bytes'] and opl.sha(data) == trial['vgm_sha256']
        checked = audit(data, controls)
        assert checked['fields'] == 4500 and checked['writes'] == writes
        raw, samples, parsed = opl.replay(data)
        assert samples == 3969000 and parsed == writes and len(raw) == 4474431
        assert not np.any(abs(raw) >= 1)
        audio = opl.playback(raw, samples) * report['global_playback_gain']
        assert not np.any(abs(audio) >= 1)
        expected_pcm = np.clip(np.rint(audio * 32767), -32768, 32767).astype('<i2').tobytes()
        wave_name = 'ym3812-preview.wav' if name == 'smooth' else 'abrupt.wav'
        assert pcm(evidence / wave_name, samples) == expected_pcm, wave_name
        if name == 'smooth':
            assert (evidence / 'ym3812.vgm').read_bytes() == data
            assert gzip.decompress((evidence / 'ym3812.vgz').read_bytes()) == data
        streams.append(dict(name=name, **checked, native_samples=len(raw), output_samples=samples,
                            independently_reexported_and_full_wav_replayed_exact=True))
        print(json.dumps(dict(stage='independent_song_replay', name=name, fields=4500, samples=samples)), flush=True)
    assert {item['name'] for item in streams} == {'abrupt', 'smooth'}
    comparison = pcm(evidence / 'source-versus-ym3812.wav', 181 * 44100)
    assert comparison == pcm(evidence / 'comparison-source.wav', 90 * 44100) + bytes(88200) + pcm(evidence / 'ym3812-preview.wav', 90 * 44100)
    tests = args.tests.read_text(encoding='utf-8')
    assert 'Ran 8 tests' in tests and tests.rstrip().endswith('OK')
    (evidence / 'tests.log').write_bytes(args.tests.read_bytes())
    save(evidence / 'verification.json', dict(complete=True, date='2026-10-14', streams=streams,
         source_preparation_recreated_byte_exact=True, comparison_all_segments_exact=True,
         all_artifact_and_producer_hashes_match=True, unit_tests=8, unit_tests_pass=True,
         verification_source_sha256_lf=opl.sha(Path(__file__).read_bytes().replace(b'\r\n', b'\n')),
         artifacts_sha256={p.name: opl.sha(p.read_bytes()) for p in sorted(evidence.iterdir()) if p.is_file() and p.name != 'verification.json'}))
    print(json.dumps(dict(complete=True, streams=2, fields_each=4500, output_samples_each=3969000, tests=8)), flush=True)


if __name__ == '__main__': main()
