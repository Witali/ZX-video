"""Byte-exact host decoder acceleration; no waveform rendering or Z80 edits.

Compile the frozen878c578e C producer and current C producer with identical
flags. Compare all original and matched compressed streams, probe every IMA
transition and its predictor boundaries, then time alternating complete CLI
invocations including identical file I/O. Preserve fresh immutable evidence.
"""
import argparse
import ctypes
from ctypes import wintypes
import gzip
import hashlib
import json
from pathlib import Path
import platform
import statistics
import subprocess
import time

import numpy as np

from ima_codec import STEPS, INDEX, decode
import waveform_kernel

HERE = Path(__file__).resolve().parent
BASELINE_SHA = '743304464f415024a289514b9cf49987d55af56524453a103509fc683d37a9ef'
NAMES = ('silence', 'quiet440', 'loud3000', 'steps', 'quiet997',
         'multitone', 'speech', 'entertainer', 'sea_foam')
OUTPUTS = ('words.u16', 'states.u8', 'decoded.pcm16')


def sha(raw): return hashlib.sha256(raw).hexdigest()
def save(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def build(source, destination, *, dll=False):
    destination.mkdir(parents=True, exist_ok=True)
    (destination/'kernel.c').write_bytes(source)
    command = waveform_kernel._command()
    if not isinstance(command, str):
        raise RuntimeError('This retained benchmark requires the installed Windows MSVC toolchain')
    if not dll:
        command = command.replace('/LD /MT', '/MT').replace('/OUT:kernel.dll', '/OUT:kernel.exe')
    started = time.perf_counter()
    result = subprocess.run(command, cwd=destination, capture_output=True, creationflags=0x08000000)
    metadata = dict(command=command, seconds=time.perf_counter()-started,
                    returncode=result.returncode, stdout=result.stdout.decode(errors='replace'),
                    stderr=result.stderr.decode(errors='replace'))
    if result.returncode:
        raise RuntimeError(metadata)
    binary = destination/('kernel.dll' if dll else 'kernel.exe')
    metadata['binary_sha256'] = sha(binary.read_bytes())
    metadata['source_sha256'] = sha(source)
    return binary, metadata


class IOCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in (
        'read_operations', 'write_operations', 'other_operations',
        'read_bytes', 'write_bytes', 'other_bytes')]


def invoke(binary, model, packed, folder):
    folder.mkdir(parents=True, exist_ok=True)
    command = [str(binary), str(model), str(packed), *(str(folder/name) for name in OUTPUTS)]
    started = time.perf_counter()
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=0x08000000)
    stdout, stderr = process.communicate()
    elapsed = time.perf_counter()-started
    # The process handle remains open after communicate(), so these Windows
    # counters measure the child, including startup and actual CRT/file I/O.
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel32.GetProcessTimes.argtypes = [wintypes.HANDLE, *([ctypes.POINTER(wintypes.FILETIME)]*4)]
    kernel32.GetProcessTimes.restype = wintypes.BOOL
    kernel32.QueryProcessCycleTime.argtypes = [wintypes.HANDLE, ctypes.POINTER(ctypes.c_uint64)]
    kernel32.QueryProcessCycleTime.restype = wintypes.BOOL
    kernel32.GetProcessIoCounters.argtypes = [wintypes.HANDLE, ctypes.POINTER(IOCounters)]
    kernel32.GetProcessIoCounters.restype = wintypes.BOOL
    values = [wintypes.FILETIME() for _ in range(4)]
    assert kernel32.GetProcessTimes(int(process._handle), *(ctypes.byref(x) for x in values))
    ticks = [(x.dwHighDateTime << 32)+x.dwLowDateTime for x in values]
    cycles = ctypes.c_uint64(); io = IOCounters()
    assert kernel32.QueryProcessCycleTime(int(process._handle), ctypes.byref(cycles))
    assert kernel32.GetProcessIoCounters(int(process._handle), ctypes.byref(io))
    return dict(seconds=elapsed, child_CPU_seconds=(ticks[2]+ticks[3])/10_000_000,
                child_CPU_cycles=cycles.value,
                child_IO={name: getattr(io, name) for name, _ in io._fields_},
                returncode=process.returncode, stdout=stdout.decode(), stderr=stderr.decode())


def result_bytes(folder):
    return [(folder/name).read_bytes() if (folder/name).exists() else None for name in OUTPUTS]


def compare_pair(old, new, model, packed, folder, expected_return=0):
    rows = []
    previous = None
    for version, binary in (('baseline', old), ('accelerated', new)):
        dest = folder/version
        row = invoke(binary, model, packed, dest)
        actual = result_bytes(dest)
        assert row['returncode'] == expected_return, row
        signature = (row['returncode'], row['stdout'], row['stderr'], actual)
        if previous is not None:
            assert signature == previous, ('decoder CLI mismatch', str(packed))
        previous = signature
        rows.append(dict(version=version, execution=row))
    return rows, previous[3]


def probe_transitions(source, folder):
    wrapper = source + b'''
__declspec(dllexport) void probe_tables(int *delta,unsigned char *successor) {
    transitions(delta,successor);
}
__declspec(dllexport) int probe_advance(int *predictor,int *index,int code) {
    static int delta[89*16];static unsigned char successor[89*16];
    static int ready=0;if(!ready){transitions(delta,successor);ready=1;}
    return advance(predictor,index,code,delta,successor);
}
'''
    binary, metadata = build(wrapper, folder, dll=True)
    library = ctypes.CDLL(str(binary))
    library.probe_tables.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_ubyte)]
    library.probe_advance.argtypes = [ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int), ctypes.c_int]
    library.probe_advance.restype = ctypes.c_int
    delta = (ctypes.c_int*1424)(); successor = (ctypes.c_ubyte*1424)()
    library.probe_tables(delta, successor)
    cases = []
    for index, step in enumerate(STEPS):
        for code in range(16):
            difference = (step >> 3)+(step if code & 4 else 0)+(step >> 1 if code & 2 else 0)+(step >> 2 if code & 1 else 0)
            difference *= -1 if code & 8 else 1
            next_index = min(88, max(0, index+INDEX[code & 7]))
            assert delta[index*16+code] == difference
            assert successor[index*16+code] == next_index
            # Both exact acceptance edges and immediately outside them, plus
            # extrema/zero, cover every guarded addition decision per cell.
            seeds = {-32768, -32767, -1, 0, 1, 32766, 32767}
            for boundary in (-32768-difference, 32767-difference):
                seeds.update(boundary+d for d in (-1, 0, 1))
            for seed in sorted(x for x in seeds if -32768 <= x <= 32767):
                predictor = ctypes.c_int(seed); actual_index = ctypes.c_int(index)
                accepted = bool(library.probe_advance(ctypes.byref(predictor), ctypes.byref(actual_index), code))
                value = seed+difference; wanted = -32768 <= value <= 32767
                assert accepted == wanted and predictor.value == value
                assert actual_index.value == (next_index if wanted else index)
                cases.append((index, code, seed, value, int(accepted), actual_index.value))
    raw = np.asarray(cases, dtype='<i4').tobytes()
    return dict(build=metadata, transition_cells=1424, boundary_cases=len(cases),
                cases_sha256=sha(raw), exact_shift_add_delta=True,
                exact_clamped_next_index=True, exact_overflow_rejection=True), raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    parser.add_argument('--pairs', type=int, default=3)
    args = parser.parse_args()
    out = args.output.resolve(); scratch = args.scratch.resolve()
    if out.exists(): raise FileExistsError('Preserve previous evidence: '+str(out))
    if args.pairs < 3: raise ValueError('At least three alternating pairs are required')
    out.mkdir(parents=True); scratch.mkdir(parents=True, exist_ok=True)
    old_source = (HERE/'evidence/table-pdm-uniform16-matched-quality/host.c').read_bytes()
    assert sha(old_source) == BASELINE_SHA
    source_path = HERE/'table_pdm_uniform16_host.c'; source = source_path.read_bytes()
    model_path = HERE/'evidence/table-pdm-uniform16-matched-quality/model.bin'
    model = model_path.read_bytes(); assert len(model) == 6144
    (out/'baseline.c').write_bytes(old_source); (out/'accelerated.c').write_bytes(source)
    (out/'model.bin').write_bytes(model)
    baseline, old_build = build(old_source, scratch/'baseline-build')
    accelerated, new_build = build(source, scratch/'accelerated-build')
    probe, raw_cases = probe_transitions(source, scratch/'probe-build')
    (out/'boundary-cases.i32.gz').write_bytes(gzip.compress(raw_cases, mtime=0))
    save(out/'transition-probe.json', probe)
    rows = []
    for family in ('canonical', 'matched'):
        for name in NAMES:
            path = (HERE/'evidence/general/inputs'/(name+'.ima.gz') if family == 'canonical'
                    else HERE/'evidence/table-pdm-uniform16-matched'/name/'packed.ima.gz')
            packed = gzip.decompress(path.read_bytes())
            local = scratch/'corpus'/family/name; local.mkdir(parents=True, exist_ok=True)
            input_path = local/'input.ima'; input_path.write_bytes(packed)
            runs, values = compare_pair(baseline, accelerated, out/'model.bin', input_path, local)
            pcm, indices = decode(packed)
            assert values[2] == pcm.astype('<i2').tobytes()
            final = json.loads(runs[-1]['execution']['stdout'])
            assert final['samples'] == len(pcm) and final['final_predictor'] == int(pcm[-1]) and final['final_index'] == int(indices[-1])
            rows.append(dict(family=family, source=name, compressed_bytes=len(packed), samples=len(pcm),
                compressed_sha256=sha(packed), compressed_artifact_sha256=sha(path.read_bytes()),
                output_files={n: dict(bytes=len(v), sha256=sha(v)) for n, v in zip(OUTPUTS, values)},
                old_new_all_files_and_CLI_exact=True, independent_Python_PCM16_exact=True, runs=runs))
            print(json.dumps(dict(family=family, source=name, samples=len(pcm), byte_exact=True)), flush=True)
    controls = []
    fixture = scratch/'controls'; fixture.mkdir(exist_ok=True)
    for label, packed, expected in (
        ('empty', b'', 6), ('positive-overflow', b'\x77'*64, 4),
        ('negative-overflow', b'\xff'*64, 4), ('chunk-exact', b'\x88'*32768, 0),
        ('chunk-plus-one', b'\x88'*32769, 0),
        ('overflow-after-complete-chunk', b'\x88'*32768+b'\x77'*64, 4)):
        packed_path = fixture/(label+'.ima'); packed_path.write_bytes(packed)
        runs, values = compare_pair(baseline, accelerated, out/'model.bin', packed_path, fixture/label, expected)
        controls.append(dict(case=label, expected_return=expected, runs=runs,
            output_files={n: None if v is None else dict(bytes=len(v), sha256=sha(v)) for n, v in zip(OUTPUTS, values)}))
    # Invalid successor preserves the old partial-word/error behaviour.
    invalid = bytearray(model)
    for at in range(2, len(invalid), 3): invalid[at] = 32
    bad_model = fixture/'invalid-successor.bin'; bad_model.write_bytes(invalid)
    normal_input = fixture/'normal.ima'; normal_input.write_bytes(b'\x88')
    runs, values = compare_pair(baseline, accelerated, bad_model, normal_input, fixture/'invalid-successor', 5)
    controls.append(dict(case='invalid-successor', expected_return=5, runs=runs,
        partial_word_bytes=len(values[0]), state_bytes=len(values[1]), PCM16_bytes=len(values[2])))
    for label, data in (('short-model', model[:-1]), ('long-model', model+b'\0')):
        path = fixture/(label+'.bin'); path.write_bytes(data)
        runs, _ = compare_pair(baseline, accelerated, path, normal_input, fixture/label, 3)
        controls.append(dict(case=label, expected_return=3, runs=runs))
    # Same filenames, same compressed source, same model, same total I/O. Warm
    # both programs once, then alternate their order to limit cache bias.
    timed = scratch/'timed'; timed.mkdir(exist_ok=True)
    song = scratch/'corpus/matched/sea_foam/input.ima'
    warm = [dict(version=label, execution=invoke(binary, out/'model.bin', song, timed))
            for label, binary in (('baseline', baseline), ('accelerated', accelerated))]
    timings = []
    for pair in range(args.pairs):
        order = (('baseline', baseline), ('accelerated', accelerated))
        if pair & 1: order = order[::-1]
        for version, binary in order:
            run = invoke(binary, out/'model.bin', song, timed)
            assert run['returncode'] == 0
            timings.append(dict(pair=pair, version=version, execution=run))
    summary = {}
    for version in ('baseline', 'accelerated'):
        selected = [r['execution'] for r in timings if r['version'] == version]
        summary[version] = {field: statistics.median(r[field] for r in selected)
                            for field in ('seconds', 'child_CPU_seconds', 'child_CPU_cycles')}
    summary['elapsed_speedup'] = summary['baseline']['seconds']/summary['accelerated']['seconds']
    summary['CPU_cycle_speedup'] = summary['baseline']['child_CPU_cycles']/summary['accelerated']['child_CPU_cycles']
    assert source_path.read_bytes() == source and model_path.read_bytes() == model
    report = dict(complete=True, date='2026-10-20', baseline_commit='878c578e',
        baseline_source_sha256=BASELINE_SHA, accelerated_source_sha256=sha(source),
        model_sha256=sha(model), host=dict(platform=platform.platform(), processor=platform.processor()),
        builds=dict(baseline=old_build, accelerated=new_build), transition_probe=probe,
        whole_streams=len(rows), original_samples_per_family=sum(r['samples'] for r in rows if r['family']=='canonical'),
        all_whole_stream_files_byte_exact=True, rows=rows, controls=controls,
        benchmark=dict(scope='Warm complete CLI invocation, process startup plus identical compressed/model reads and all five output bytes per sample; excludes compilation, hashing and reference verification',
            warmups=warm, alternating_pairs=args.pairs, rows=timings, medians=summary),
        no_audio_rendering_or_encoding_repeated=True, compressed_format_changed=False,
        decoded_semantics_changed=False, Z80_hot_path_changed=False, Z80_Tstate_delta=0,
        player_or_release_claim=False)
    save(out/'report.json', report)
    (out/'producer.py.gz').write_bytes(gzip.compress(Path(__file__).read_bytes(), mtime=0))
    for dependency in (Path(waveform_kernel.__file__), HERE.parent.parent/'ima_codec.py'):
        (out/(dependency.name+'.gz')).write_bytes(gzip.compress(dependency.read_bytes(), mtime=0))
    artifact_files = {path.relative_to(out).as_posix(): dict(bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
                      for path in sorted(out.rglob('*')) if path.is_file()}
    save(out/'manifest.json', dict(complete=True, artifact_files=artifact_files))
    print(json.dumps(dict(complete=True, whole_streams=len(rows), benchmark_medians=summary)), flush=True)


if __name__ == '__main__': main()
