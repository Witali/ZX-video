"""Rebuild frozen format-preserving C trials on one authenticated workset.

Run with the project's NumPy/runtime environment. Worksets are generated with
the retained original analytic model, not a subsequently optimized producer.
The output directory must be new. No existing evidence is overwritten.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import types

import numpy as np

HERE = Path(__file__).resolve().parent
EXPERIMENT = HERE.parents[1]
AUDIO = EXPERIMENT.parents[1]
for folder in (AUDIO, EXPERIMENT, AUDIO.parent / 'toolkit'):
    sys.path.insert(0, str(folder))


def sha(content):
    return hashlib.sha256(content).hexdigest()


def load_original(name, relative):
    module = types.ModuleType('speed_profile_original_' + name)
    module.__file__ = str(AUDIO / relative)
    content = gzip.decompress((HERE / 'producer-source' / (name + '.gz')).read_bytes())
    exec(compile(content, module.__file__, 'exec'), module.__dict__)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--song', action='store_true', help='Use the full original song instead of the bounded prefix')
    parser.add_argument('--workset-only', action='store_true')
    parser.add_argument('--variant', action='append', choices=[p.name[:-5] for p in sorted((HERE / 'variants').glob('*.c.gz'))])
    parser.add_argument('--rounds', type=int, default=1)
    args = parser.parse_args()
    if args.rounds < 1:
        parser.error('rounds must be positive')
    scratch = args.scratch.resolve()
    if scratch.exists() and any(scratch.iterdir()):
        parser.error('scratch must be empty; preserve prior output')
    scratch.mkdir(parents=True, exist_ok=True)
    context = json.loads((HERE / 'context.json').read_bytes())
    wave = load_original('ima_waveform_encoder.py', 'ima_waveform_encoder.py')
    clock = load_original('experiments__song-snr__clock_control.py', 'experiments/song-snr/clock_control.py')
    packets = load_original('probe_feedback_packets.py', 'probe_feedback_packets.py')
    wrapper = load_original('native_waveform_encoder.py', 'native_waveform_encoder.py')
    kernel = load_original('waveform_kernel.py', 'waveform_kernel.py')
    clock.WaveformModel = wave.WaveformModel
    clock.integral_table = packets.integral_table
    from probe_reconstruction_error import wav8
    source = wav8(EXPERIMENT / 'evidence/general/inputs/sea_foam.wav')
    assert sha(source.tobytes()) == context['source_pcm8_sha256']
    if not args.song:
        source = np.r_[source[:16384], np.full(512, 128, np.uint8)]
    started = time.perf_counter()
    times = np.arange(len(source) * 16 + 1, dtype=np.float64) * (3546900 / 8000 / 16)
    model = dict(holds=[28] * 16, beta=.5, extent=.5, pcm_origin=0)
    desired, features, ids, nxt, _ = clock.prepare(source, times, model)
    prepared = time.perf_counter()
    workset = scratch / 'workset.bin'
    wrapper.write_workset(workset, source, desired, features, ids, nxt)
    written = time.perf_counter()
    expected = context['full_workset' if args.song else 'prefix']
    assert workset.stat().st_size == expected['workset_bytes']
    assert sha(workset.read_bytes()) == expected['workset_sha256']
    result = dict(samples=len(source), features=len(features),
        workset_sha256=expected['workset_sha256'], preparation_seconds=prepared-started,
        workset_write_seconds=written-prepared, runs=[])
    if not args.workset_only:
        dll = Path(context['matrix_library']['path'])
        assert sha(dll.read_bytes()) == context['matrix_library']['sha256']
        command = kernel._command()
        assert isinstance(command, str) and '/LD /MT' in command
        command = command.replace('/LD /MT', '/DNWF_STANDALONE /MT').replace('/OUT:kernel.dll', '/OUT:kernel.exe')
        variants = args.variant or ['baseline', 'selector']
        executables = {}
        for variant in variants:
            build = scratch / variant
            build.mkdir()
            content = gzip.decompress((HERE / 'variants' / (variant + '.c.gz')).read_bytes())
            (build / 'kernel.c').write_bytes(content)
            compiled = subprocess.run(command, cwd=build, capture_output=True,
                timeout=120, creationflags=0x08000000)
            (build / 'build.log').write_bytes(compiled.stdout + compiled.stderr)
            assert compiled.returncode == 0, build / 'build.log'
            executables[variant] = build / 'kernel.exe'
        for turn in range(args.rounds):
            for variant in variants if turn % 2 == 0 else list(reversed(variants)):
                output = scratch / (variant + '.ima')
                before = time.perf_counter()
                child = subprocess.run([str(executables[variant]), str(workset), str(output), str(dll)],
                    capture_output=True, text=True, creationflags=0x08000000)
                elapsed = time.perf_counter()-before
                assert child.returncode == 0, child.stderr
                row = dict(variant=variant, elapsed_seconds=elapsed,
                    statistics=json.loads(child.stdout), packed_sha256=sha(output.read_bytes()))
                if not args.song:
                    assert row['packed_sha256'] == context['prefix']['expected_output_sha256']
                result['runs'].append(row)
                print(json.dumps(row), flush=True)
        assert len({row['packed_sha256'] for row in result['runs']}) == 1
    (scratch / 'report.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
