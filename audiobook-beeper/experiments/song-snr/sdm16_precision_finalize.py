"""Audit the complete frozen precision experiment and seal its saved evidence."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from ima_codec import decode
from probe_reconstruction_error import wav8
from sdm16_precision import (AUDIO, LABELS, NAMES, original_stream,
                             producer_files, save, sha)
from study import metrics


def audit(output, cache=None):
    output = Path(output).resolve()
    cache = None if cache is None else Path(cache).resolve()
    configuration = json.loads((output/'configuration.json').read_bytes())
    report = json.loads((output/'report.json').read_bytes())
    assert report['complete'] and report['whole9_source_corpus']
    assert [row['source'] for row in report['rows']] == list(NAMES)
    assert configuration['beta'] == .5 and not configuration['order_changed']
    assert not configuration['input_gain_changed'] and configuration['archived_ima_frozen']
    sources = producer_files()
    assert configuration['producers'] == {name:sha(path.read_bytes()) for name,path in sources.items()}
    for name, digest in configuration['producers'].items():
        assert sha(gzip.decompress((output/'producer-source'/(name+'.gz')).read_bytes())) == digest
    assert sha(Path(configuration['executable']).read_bytes()) == configuration['executable_sha256']
    samples = packets = actual_arrays = 0
    for row in report['rows']:
        name = row['source']; dest = output/name
        assert json.loads((dest/'host.json').read_bytes()) == row
        source = wav8(dest/'source-preview.wav')
        assert sha(source.tobytes()) == row['source_sha256']
        assert sha((dest/'source-preview.wav').read_bytes()) == row['source_file_sha256']
        packed = gzip.decompress((dest/'soundtrack.ima.gz').read_bytes())
        assert sha(packed) == row['packed_sha256'] and len(packed)*2 == len(source)
        pcm, _ = decode(packed)
        assert sha(pcm.astype('<i2').tobytes()) == row['decoded_pcm16_sha256']
        expected_words, expected_states = original_stream(pcm)
        if cache:
            wanted = np.load(cache/name/'original-reference.npy')
            decoded = np.load(cache/name/'decoded-reference.npy')
        for mode, label in LABELS.items():
            if label not in row['variants']:
                continue
            variant = row['variants'][label]
            word_bytes = gzip.decompress((dest/(label+'-words.bin.gz')).read_bytes())
            state_bytes = gzip.decompress((dest/(label+'-states.bin.gz')).read_bytes())
            assert sha(word_bytes) == variant['word_bytes_sha256']
            assert sha(state_bytes) == variant['next_state_sha256']
            assert len(word_bytes) == len(pcm)*2 and len(state_bytes) == len(pcm)
            words, states = np.frombuffer(word_bytes, '>u2'), np.frombuffer(state_bytes, 'u1')
            if mode == 'a':
                np.testing.assert_array_equal(words, expected_words)
                np.testing.assert_array_equal(states, expected_states)
            elif mode == 'c':
                np.testing.assert_array_equal(states, 255)
                assert not variant['packet_state_quantized']
            assert variant['beta'] == .5 and variant['table_generation_ordinary_tstates'] == 449
            if cache:
                actual = np.load(cache/name/(label+'-actual.npy'))
                diag = json.loads((dest/(label+'-diagnostics.json')).read_bytes())
                assert sha(actual.astype('<f8').tobytes()) == diag['actual_float64_sha256']
                assert sha(wanted.astype('<f8').tobytes()) == diag['reference_float64_sha256']
                assert sha(decoded.astype('<f8').tobytes()) == diag['decoded_reference_float64_sha256']
                measured = metrics(wanted,actual)
                assert abs(measured['error_rms']-variant['fixed_clock']['error_rms']) < 1e-14
                actual_arrays += 1
            packets += len(pcm)
        samples += len(pcm)
    result = dict(complete=True, frozen_producers=len(sources), source_count=len(report['rows']),
        original_pcm_samples=samples, modulated_packets=packets,
        whole_original_a_word_and_successor_parity_rechecked=True,
        actual_unscaled_arrays_hash_checked=actual_arrays,
        independent_fraction_cell_and_trajectory_tests='focused-tests.log',
        unchanged_order_beta=.5, unchanged_gain_filter_clock_edges=True,
        new_z80_player_or_emulator_claim=False, release_accepted=False,
        audit_producer_sha256=sha(Path(__file__).read_bytes()))
    save(output/'audit.json', result)
    files = {str(path.relative_to(output)).replace('\\','/'):dict(bytes=path.stat().st_size,
            sha256=sha(path.read_bytes())) for path in sorted(output.rglob('*'))
            if path.is_file() and path.name != 'manifest.json'}
    save(output/'manifest.json', dict(complete=True, artifact_files=files,
        artifact_count=len(files), audit=result,
        external_producers={str(Path(__file__).relative_to(AUDIO)).replace('\\','/'):sha(Path(__file__).read_bytes())}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--cache', type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(args.output,args.cache)))
