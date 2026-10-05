"""Archive and audit complete quality comparisons without rerunning audio."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np
from analyze_ima_boundaries import read_wav, boundary_metrics
from probe_reconstruction_error import wav8
from verify_pcm import save
from probe import CASES

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
NAMES = {case:f'ZX-{ "music-Entertainer" if case.startswith("music") else "audiobook" }-quality-IMA{case[-1]}.trd'
         for case in CASES}


def read(path):return json.loads(path.read_bytes())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def copy(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def history(run):
    """Keep initial IMA4 decisions when a later clock refinement supersedes them."""
    dest=HERE/'history'/run.name
    for name in ('report.json','identity.json','host-search.json','candidates.json','host-reuse.json'):
        if (run/name).exists():copy(run/name,dest/name)
    for folder in run.glob('encode-*'):
        for name in ('report.json','soundtrack.ima.gz','stage-complete.json'):
            copy(folder/name,dest/folder.name/name)
    for folder in run.glob('disk-*'):
        for name in ('report.json','quality.json','native.json','fuse.json','independent-ima.json',
                     'phase-probe.json','player.json','soundtrack.ima.gz','audiobook-preview.trd'):
            copy(folder/name,dest/folder.name/name)
        if (folder/'producer-source').exists():
            shutil.copytree(folder/'producer-source',dest/folder.name/'producer-source',dirs_exist_ok=True)


def measurements(folder):
    meta = read(folder/'player.json')
    times = np.frombuffer(gzip.decompress((folder/'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)[:meta['outputs_per_cycle']+1]
    source = read_wav(folder/'uniform-clock-source-preview.wav')
    output = read_wav(folder/'clock-aware-output-preview.wav')
    return [boundary_metrics(source, output, times, period) for period in (64, 128, 256)]


def archive(run):
    report = read(run/'report.json'); assert report['complete']
    case = report['case']; dest = HERE/case
    baseline = HERE.parent/CASES[case][0]
    for name in ('report.json', 'identity.json', 'host-search.json', 'candidates.json', 'host-reuse.json'):
        if (run/name).exists():copy(run/name, dest/name)
    for folder in run.glob('encode-*'):
        for name in ('report.json', 'soundtrack.ima.gz', 'stage-complete.json'):
            copy(folder/name, dest/folder.name/name)
    for folder in run.glob('disk-*'):
        for name in ('report.json', 'quality.json', 'native.json', 'fuse.json', 'independent-ima.json',
                     'phase-probe.json', 'player.json', 'soundtrack.ima.gz'):
            copy(folder/name, dest/folder.name/name)
    selected = run/'selected'
    for path in selected.iterdir():
        if path.is_file():copy(path, dest/'selected'/path.name)
    for path in (selected/'assembly').iterdir():
        if path.suffix != '.lst':copy(path, dest/'selected/assembly'/path.name)
    for path in (run/'sound-128').iterdir():
        if path.is_file() and path.suffix != '.fmf':copy(path, dest/'sound-128'/path.name)
    if not report['selected_baseline']:
        chosen = Path(report.get('selected_source',str(run/report['best_candidate']['directory'])))
        trace = chosen/read(chosen/'report.json')['selected']/'verification-work'
        for path in trace.iterdir():
            if path.is_file():copy(path, dest/'verification-work'/path.name)
        for path in (chosen/'producer-source').glob('*'):
            if path.is_file():copy(path,dest/'producer-source'/path.name)
    comparison = dict(scope='First-loop diagnostic, fixed filter and 100-ms exclusions; not a universal flutter gate',
                      before=measurements(baseline), after=measurements(selected),
                      native_before=read(baseline/'native.json')['cycle_tstates'],
                      native_after=read(selected/'native.json')['cycle_tstates'])
    save(dest/'comparison.json', comparison)
    copy(selected/'audiobook-preview.trd', ROOT/NAMES[case])


def audit():
    results = {}
    for case, name in NAMES.items():
        directory = HERE/case
        if not (directory/'report.json').exists():continue
        report = read(directory/'report.json'); selected = directory/'selected'
        quality = read(selected/'quality.json'); native = read(selected/'native.json'); fuse = read(selected/'fuse.json')
        assert quality['minimum_snr_db'] >= report['baseline_quality']['minimum_snr_db']
        assert native['complete'] and fuse['complete'] and fuse['cold_boot']
        assert native['cycles_verified'] == fuse['cycles_verified'] == 2
        for proof in (native, fuse):
            assert proof['every_pdm_bit_exact'] and proof['every_predictor_and_index_exact']
            assert proof['pcm16_samples_verified'] == 2*report['samples']
        assert native['memory_guards_passed'] and native['every_output_port_uncontended']
        assert fuse['runtime_disk_reads'] == 0 and quality['speed_within_two_percent']
        assert fuse['paging_latches_verified']
        assert abs(quality['mean_speed_error_percent']) <= 2
        deltas=quality['complete_trace_phase_deltas_tstates']
        assert abs(deltas[0])<=3 and deltas[1]==0
        assert read(selected/'independent-ima.json')['every_sample_exact']
        assert hashlib.sha256(wav8(selected/'source-preview.wav').tobytes()).hexdigest() == report['source_sha256']
        assert digest(ROOT/name) == digest(selected/'audiobook-preview.trd') == report['trd_sha256']
        assert fuse['trd_sha256']==report['trd_sha256']
        assert (ROOT/name).stat().st_size==655360
        recording = read(directory/'sound-128/report.json')
        assert recording['recording_complete'] and recording['paging_latches_match'] and recording['secondary_paging_unchanged']
        assert recording['source_trd_sha256'] == report['trd_sha256']
        results[case] = dict(before=report['baseline_quality']['minimum_snr_db'],
                            after=quality['minimum_snr_db'], speed_error_percent=quality['mean_speed_error_percent'],
                            trd=name, trd_sha256=report['trd_sha256'], bits_verified=fuse['bits_verified'],
                            source_sha256=report['source_sha256'], selected_baseline=report['selected_baseline'])
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run', type=Path, action='append')
    p.add_argument('--history-run',type=Path,action='append')
    p.add_argument('--write-manifest', action='store_true')
    a = p.parse_args()
    for run in a.history_run or []:history(run.resolve())
    for run in a.run or []:archive(run.resolve())
    results = audit()
    if a.write_manifest:
        save(HERE/'results.json', results)
        files = sorted(path for path in HERE.rglob('*') if path.is_file()
                       and '__pycache__' not in path.parts and path.name != 'artifact-hashes.json')
        save(HERE/'artifact-hashes.json', {p.relative_to(HERE).as_posix():digest(p) for p in files})
    if (HERE/'artifact-hashes.json').exists():
        for name, expected in read(HERE/'artifact-hashes.json').items():assert digest(HERE/name) == expected, name
    print(json.dumps(results), flush=True)


if __name__ == '__main__':main()
