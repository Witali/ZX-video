"""Qualify shared waveform searches against unchanged complete references.

Reuse archived baseline clocks only for host search. Every candidate disk
gets new phase calibration and two complete native/cold-Fuse executions.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from quality_search import host_search, search_plan, ranked_hosts
from convert_ima3_audio import stage
from build_ima3_direct import build_verified
from convert_audio import calibrate, validate, pcm_wav, independent_ima_check, snapshot_sources
from precompensate_voice import compensate
from verify_direct import sample_positions
from probe_reconstruction_error import wav8
from verify_pcm import save
from probe import CASES

HERE = Path(__file__).resolve().parent
MODULES = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def four_bit(source, packed, out, fuse, ffmpeg, hot):
    out.mkdir(parents=True, exist_ok=False)
    snapshot_sources(out)
    selected, meta = calibrate(out/'calibration', packed, source, fuse, hot)
    quality = validate(selected, fuse, ffmpeg)
    times = np.frombuffer(gzip.decompress((selected/'output-times.u32.gz').read_bytes()), '<u4').astype(np.int64)
    pcm_wav(selected/'compensated-pcm.wav', compensate(source, times[sample_positions(meta)], period=3546900/8000))
    for path in selected.iterdir():
        if path.is_file():shutil.copy2(path, out/path.name)
    shutil.copytree(selected/'assembly', out/'assembly')
    independent = independent_ima_check(packed, ffmpeg)
    save(out/'independent-ima.json', independent)
    report = dict(complete=True, quality=quality, source_sha256=hashlib.sha256(source.tobytes()).hexdigest(),
                  selected=str(selected.relative_to(out)), native_mean_tstates=423,
                  physical_hardware_tested=False)
    save(out/'report.json', report)
    return report


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', required=True)
    p.add_argument('--fuse', type=Path, required=True)
    p.add_argument('--case', choices=CASES, required=True)
    p.add_argument('--attempts', type=int, choices=(1, 2, 3), default=3)
    p.add_argument('--resume', action='store_true')
    p.add_argument('--clock', type=Path, help='refine from a completely verified candidate with the exact same source')
    p.add_argument('--reuse-search', type=Path,
                   help='reuse authenticated host searches; always rerun disk checks with the requested emulator')
    a = p.parse_args()
    out = a.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    folder, bits = CASES[a.case]; baseline = HERE.parent/folder
    codec = f'ima{bits}'
    plan=search_plan(codec,'best',a.attempts)
    reference = wav8(baseline/'source-preview.wav')
    meta = json.loads((baseline/'player.json').read_bytes())
    clock = a.clock.resolve() if a.clock else baseline
    if a.clock:
        assert np.array_equal(wav8(clock/'source-preview.wav'),reference)
        for name in ('native.json','fuse.json'):
            proof=json.loads((clock/name).read_bytes())
            assert proof['complete'] and proof['cycles_verified']==2
            if name=='fuse.json':assert proof['trd_sha256']==sha(clock/'audiobook-preview.trd')
        clock_meta=json.loads((clock/'player.json').read_bytes())
        assert clock_meta['model']==meta['model']
        meta=clock_meta
        if (clock.parent/'host-search.json').exists() and clock.name.startswith('disk-'):
            selected_host=next(h for h in json.loads((clock.parent/'host-search.json').read_bytes())
                               if h['directory']==clock.name[5:])
            assert a.attempts==1,'clock refinement repeats only the winning search'
            plan=((selected_host['beam_width'],selected_host['control_regularization'],selected_host['block_size']),)
    identity = dict(case=a.case, attempts=a.attempts, search_plan=[list(item) for item in plan], source=sha(baseline/'source-preview.wav'),
                    baseline_trd=sha(baseline/'audiobook-preview.trd'),
                    baseline_clock=sha(clock/'output-times.u32.gz'),
                    fuse=sha(a.fuse), ffmpeg=sha(Path(a.ffmpeg)),
                    producers={p.name:sha(p) for p in MODULES.glob('*.py')})
    marker = out/'identity.json'
    if marker.exists():
        if not a.resume or json.loads(marker.read_bytes()) != identity:
            raise ValueError('output identity changed')
    else:save(marker, identity)
    baseline_quality = json.loads((baseline/'quality.json').read_bytes())
    hosts = []
    if a.reuse_search:
        old_identity = json.loads((a.reuse_search/'identity.json').read_bytes())
        for key in ('case', 'attempts', 'source', 'baseline_trd', 'baseline_clock', 'ffmpeg'):
            if old_identity[key] != identity[key]:raise ValueError(f'host reuse mismatch: {key}')
        if 'search_plan' in old_identity and old_identity['search_plan'] != identity['search_plan']:
            raise ValueError('host reuse mismatch: search_plan')
        for name in ('ima_waveform_encoder.py', 'waveform_kernel.py', 'quality_search.py',
                     'ima_codec.py', 'ima_beam.py', 'probe_packet_area.py',
                     'probe_reconstruction_error.py', 'verify_direct.py', 'build_pdm.py',
                     'probe_feedback_packets.py', 'assess_snr.py'):
            if old_identity['producers'][name] != identity['producers'][name]:
                raise ValueError(f'host producer changed: {name}')
        for number in range(1, a.attempts+1):
            old = a.reuse_search/f'encode-{number}'
            if not (old/'stage-complete.json').is_file():raise ValueError('host search is incomplete')
            stage(old, lambda _: (_ for _ in ()).throw(ValueError('host search is incomplete')))
            new = out/old.name
            if not new.exists():shutil.copytree(old, new)
        save(out/'host-reuse.json', dict(source=str(a.reuse_search.resolve()),
             old_identity=old_identity, player_verification_reused=False))
    for number, (width, weight, horizon) in enumerate(plan, 1):
        folder = out/f'encode-{number}'
        host = stage(folder, lambda path:host_search(clock, path, width, weight, horizon, a.ffmpeg, codec))
        hosts.append(dict(directory=folder.name, **host)); save(out/'host-search.json', hosts)
    candidates = []
    for host in ranked_hosts(hosts):
        folder = out/f'disk-{host["directory"]}'
        packed = gzip.decompress((out/host['directory']/'soundtrack.ima.gz').read_bytes())
        report = stage(folder, lambda path:build_verified(reference, packed, path, a.fuse, a.ffmpeg, meta['model'])
                       if bits == 3 else four_bit(reference, packed, path, a.fuse, a.ffmpeg, meta['hot_indices']))
        candidates.append(dict(directory=folder.name, **report)); save(out/'candidates.json', candidates)
    passing = [c for c in candidates if c['quality']['speed_within_two_percent']]
    best = max(passing, key=lambda c:c['quality']['minimum_snr_db'])
    options=[(baseline_quality['minimum_snr_db'],baseline),
             (json.loads((clock/'quality.json').read_bytes())['minimum_snr_db'],clock),
             (best['quality']['minimum_snr_db'],out/best['directory'])]
    score,selected=max(options,key=lambda item:item[0])
    gain=score-baseline_quality['minimum_snr_db']
    dest = out/'selected'
    if not dest.exists():
        dest.mkdir()
        for path in selected.iterdir():
            if path.is_file():shutil.copy2(path, dest/path.name)
        shutil.copytree(selected/'assembly', dest/'assembly')
    recording = stage(out/'sound-128', lambda path:record(dest, path, a.fuse))
    shutil.copy2(out/'sound-128/fuse-preview.wav', dest/'result-preview.wav')
    report = dict(complete=True, case=a.case, codec=codec, samples=len(reference),
                  source_sha256=hashlib.sha256(reference.tobytes()).hexdigest(),
                  baseline_quality=baseline_quality, best_candidate=best,
                  improvement_db=max(0, gain), selected_baseline=selected==baseline,
                  selected_source=str(selected),
                  recording=recording, trd_sha256=sha(dest/'audiobook-preview.trd'),
                  native_tstates_delta=0, physical_hardware_tested=False)
    save(out/'report.json', report); print(json.dumps(report), flush=True)


def record(source, out, fuse):
    subprocess.run([sys.executable, str(MODULES/'record_pcm.py'), str(source), '--output', str(out),
                    '--fuse', str(fuse), '--machine', '128'], check=True)
    result = json.loads((out/'report.json').read_bytes())
    assert result['recording_complete'] and result['paging_latches_match'] and result['secondary_paging_unchanged']
    return result


if __name__ == '__main__':
    main()
