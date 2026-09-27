"""Audit both complete resident-AY attempts from immutable saved evidence.

Measured publication, IRQ and disk intervals are elapsed Fuse time. They are
not deterministic instruction costs or real-drive measurements. Fuse checks
80 screen bytes per frame; priming separately checks one complete native
screen and the following complete compact frame per independently booted disk.
"""
import argparse
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze, stats
from summarize_fast_return_irq import rom_invariants
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent
OUTPUT = ROOT/'resident_audio_player_summary.json'


def saved_attempt(name):
    folder = ROOT/'resident_audio_player_evidence'/name
    manifest_bytes = (folder/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    if not manifest['complete'] or manifest['release']:
        raise ValueError('unexpected snapshot scope')
    blobs = {}
    for entry in manifest['files']:
        packed = (folder/entry['file']).read_bytes()
        raw = gzip.decompress(packed)
        if (sha(packed) != entry['sha256'] or sha(raw) != entry['decoded_sha256']
                or len(raw) != entry['decoded_bytes']):
            raise ValueError(('archive changed', name, entry['file']))
        blobs[entry['file'][:-3]] = raw
    build = json.loads(blobs['build.json'])
    swaps = build['mocked_rom_swaps']
    if (not build['complete'] or len(swaps) != 2
            or [(s['from_part'], s['to_part']) for s in swaps] != [(1, 2), (2, 3)]
            or not all(s[k] for s in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact', 'rom_mocked'))):
        raise ValueError('incomplete build or swaps')
    for source, digest in build['source_sha256_lf'].items():
        if sha(blobs['source-'+source].replace(b'\r\n', b'\n')) != digest:
            raise ValueError(('historical generator differs', name, source))
    return blobs, build, sha(manifest_bytes)


def summarize():
    baseline_path = ROOT/'lookahead_player_summary.json'
    baseline = json.loads(baseline_path.read_bytes())
    reference_path = ROOT/'cached_huffman_lookahead_cpu.json'
    reference = json.loads(reference_path.read_bytes())
    prime_path = ROOT/'resident_audio_player_prime.json'
    prime = json.loads(prime_path.read_bytes())
    if (not baseline['complete'] or not reference['complete'] or not prime['complete']
            or reference['checked_frames'] != 4221
            or prime['source_sha256_lf'] != sha((ROOT/'verify_resident_audio_player.py').read_bytes().replace(b'\r\n', b'\n'))):
        raise ValueError('incomplete/different baseline or priming verification')
    variants = {}
    manifests = {}
    for name in ('queue-only', 'foreground'):
        blobs, build, manifests[name] = saved_attempt(name)
        if name == 'foreground':
            if prime['build_sha256'] != sha(blobs['build.json']):
                raise ValueError('priming build differs')
            for source, digest in build['source_sha256_lf'].items():
                if sha((ROOT/source).read_bytes().replace(b'\r\n', b'\n')) != digest:
                    raise ValueError(('current generator differs', source))
        volumes = []
        for part in (1, 2, 3):
            stem = f'part{part:02}'
            r = json.loads(blobs[stem+'.json'])
            m = json.loads(blobs[stem+'.metadata.json'])
            built = build['volumes'][part-1]
            cpu = reference['volumes'][part-1]
            if (not r['complete'] or r['failure'] or r['errors'] or not r['trace_nonce_exact']
                    or not r['ay_records_exact'] or not r['progress_100_percent']
                    or r['debugger_installed_bytes'] or r['fast_read_retries']
                    or r['frames'] != m['frames'] or r['native_frames_sampled'] != m['frames']
                    or r['ay_ticks'] != 6*m['frames'] or r['pixel_samples_per_frame'] != 80
                    or r['runtime_sectors_checked'] != m['video_sectors']
                    or r['trd_sha256'] != m['trd_sha256'] or m['trd_sha256'] != built['trd_sha256']
                    or sha(blobs[stem+'.metadata.json']) != r['integrated_bootstrap_metadata_sha256']
                    or m['raw_sha256'] != cpu['raw_sha256'] or m['frames'] != cpu['checked_frames']
                    or m['resident_audio'] != built['resident_audio']
                    or not built['dirty_ram_boot_exact']
                    or not m['independently_bootable'] or m['used_sectors'] > 2544):
                raise ValueError(('inexact/incomplete evidence', name, part))
            if name == 'foreground':
                primed = prime['volumes'][part-1]
                if (primed['part'] != part or primed['prepared_audio_records'] != 31
                        or not all(primed[k] for k in ('exact_all_video_packets', 'audio_initial_state_exact',
                            'audio_bank_immutable_exact', 'first_native_screen_exact', 'second_compact_frame_exact'))):
                    raise ValueError(('inexact priming/payload evidence', part))
            for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
                if sha(blobs[stem+suffix]) != r[key]:
                    raise ValueError(('trace identity differs', name, part))
            if any(line.startswith('se ') and line[3:].split(' ', 1)[0].isdigit()
                   for line in blobs[stem+'.debugger.txt'].decode().splitlines()):
                raise ValueError('unexpected debugger RAM patch')
            irq = audit(r, m)
            irq.pop('actual_phase_tstates')
            gate = summarize_fuse(r)
            gate.pop('publication_intervals_tstates')
            profile = analyze(r, m, cpu)
            worst = sorted(profile.pop('frames'), key=lambda f: f['work_elapsed'], reverse=True)[:8]
            for frame in worst:
                frame.pop('stage_cpu_reference')
            resident = m['resident_audio']
            volumes.append(dict(part=part, **metrics(r), timing_gates=gate, irq=irq,
                rom=rom_invariants(r, True), trd_sha256=m['trd_sha256'], rom_sha256=r['rom_sha256'],
                used_sectors=m['used_sectors'], free_sectors=m['free_sectors'],
                video_bytes=m['video_bytes'], video_start_sector=m['video_start_sector'],
                audio_bank_bytes=len(bytes.fromhex(resident['compiled']['image_hex'])),
                audio_bank_spare=16384-len(bytes.fromhex(resident['compiled']['image_hex'])),
                audio_batch=resident['compiled']['batch'],
                foreground_audio=resident.get('foreground_audio', False),
                ay_record_field_gaps=r['ay_record_field_gaps'],
                ay_record_field_duplicates=r['ay_record_field_duplicates'],
                read_service=stats([v['tstates'] for v in r['reads']]),
                seek_service=stats([v['tstates'] for v in r['seek_calls']]),
                delivery_profile=profile, worst_work_frames=worst))
        keys = ('frames', 'nominal_late_frames', 'audio_underruns', 'ay_ticks', 'runtime_sectors',
                'publication_span_tstates', 'bad_actual_intervals', 'video_bytes', 'used_sectors',
                'free_sectors', 'read_service_tstates', 'seek_service_tstates')
        totals = {key: sum(v[key] for v in volumes) for key in keys}
        totals.update(missed_nominal_frames=sum(v['timing_gates']['missed_nominal_frames'] for v in volumes),
            missing_irq_fields=sum(len(v['irq']['missing_irq_fields']) for v in volumes),
            recovered_late_runs=sum(v['recovered_late_runs'] for v in volumes),
            all_late_runs_recovered=all(v['timing_gates']['late_runs_recovered'] for v in volumes),
            nominal_schedule_met=all(v['timing_gates']['nominal_deadlines_met'] for v in volumes),
            fallback_met=all(v['timing_gates']['fallback_one_field_met'] for v in volumes),
            ay_50hz_met=all(v['timing_gates']['actual_ay_50hz'] for v in volumes))
        if totals['frames'] != 4221 or totals['ay_ticks'] != 25326:
            raise ValueError('incomplete movie')
        variants[name] = dict(volumes=volumes, totals=totals)
    old = baseline['totals']['lookahead']
    new = variants['foreground']['totals']
    delta = {k: new[k]-old[k] for k in ('nominal_late_frames', 'audio_underruns', 'runtime_sectors',
                                       'publication_span_tstates', 'bad_actual_intervals')}
    sources = ('summarize_resident_audio_player.py', 'snapshot_resident_audio_player.py',
        'verify_resident_audio_player.py', 'test_resident_audio_player.py', 'measure_fap3_fuse.py',
        'measure_integrated_bootstrap.py', 'audit_irq_fields.py', 'profile_fap3.py',
        'profile_integrated_timing.py', 'summarize_fast_return_irq.py', 'summarize_uncontended_frame.py')
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='8a49d3c',
        baseline_summary_sha256=sha(baseline_path.read_bytes()), reference_frame_cpu_sha256=sha(reference_path.read_bytes()),
        priming_report_sha256=sha(prime_path.read_bytes()), manifests_sha256=manifests,
        source_sha256_lf={n: sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in sources},
        variants=variants, baseline_totals=old, foreground_minus_baseline=delta,
        full_current_frame_cpu_replay=False, full_fuse_pixel_comparison=False,
        physical_drive_verified=False, initial_disk_and_irq_phases_not_matched=True,
        coverage='All video packet fields are byte-exact; all AY records are exact. Full cold RAM and priming '
                 'are checked separately. Full Fuse runs reach EOF on all independently booted volumes. '
                 'Pipeline stages exclude audio hooks outside their traced boundaries; residuals include '
                 'IRQ/ULA and producer work. No complete new deterministic CPU total is claimed.',
        decision='Retain resident AY with foreground service as an experimental baseline: capacity and '
                 'AY cadence pass; nominal and fallback video timing fail. Root releases stay unchanged.')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--write', action='store_true')
    a = p.parse_args()
    # Histograms have integer keys in memory and string keys in JSON.
    result = json.loads(json.dumps(summarize()))
    if a.write:
        OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()):
        raise ValueError('saved summary differs')
    print(json.dumps({name: v['totals'] for name, v in result['variants'].items()}), flush=True)


if __name__ == '__main__':
    main()
