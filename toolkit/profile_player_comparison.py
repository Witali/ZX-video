"""Audit full archived playback and combine it with fresh CPU profiles.

Fuse stage intervals include IRQs and contention. Partition the publication
span without double-counting disk service or suspended packet calls. Time
outside instrumented stages is unclassified background/control/wait work,
not demonstrated idle CPU. CPU fixtures and wall intervals are separate.
No new Fuse playback or changed player is implied by this report.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).parent
FIELD = 70908
VARIANTS = {'inplace_keepalive':'keepalive', 'inplace_streaming':'streaming',
    'resident_fragments':'candidate', 'native_mask_selection':'candidate',
    'tagged_noop':'tagged', 'resumable_packet':'candidate', 'optional_packet':'candidate'}


def sha(blob): return hashlib.sha256(blob).hexdigest()


def stats(values):
    values = sorted(values); n = len(values)
    return dict(count=n, total=sum(values), mean=sum(values)/n if n else 0,
        p50=values[(n-1)//2] if n else 0, p90=values[(n-1)*90//100] if n else 0,
        p99=values[(n-1)*99//100] if n else 0, max=max(values, default=0))


def load_archive(folder):
    manifest = json.loads((folder/'manifest.json').read_bytes())
    if not manifest['complete']: raise ValueError('incomplete archive')
    blobs, hashes = {}, {}
    for item in manifest['files']:
        packed = (folder/item['file']).read_bytes(); blob = gzip.decompress(packed)
        if sha(packed) != item['sha256'] or sha(blob) != item['decoded_sha256']:
            raise ValueError(('archive hash differs', item['file']))
        if len(blob) != item['decoded_bytes'] or ('bytes' in item and len(packed) != item['bytes']):
            raise ValueError('archive size differs')
        name = item['file'].removesuffix('.gz'); hashes[name] = sha(blob)
        if name.startswith('part') and (name.endswith('.metadata.json') or
                name in ('part01.json', 'part02.json', 'part03.json')):
            blobs[name] = json.loads(blob)
    return blobs, hashes


def partition(r):
    """Disjoint elapsed contexts inside first-to-last actual publication."""
    grouped = defaultdict(list)
    for e in r['pipeline_events']: grouped[e['kind']].append(e['tstate'])
    pairs = [('transfer','packet_start','video_payload_ready'),
             ('metadata','video_payload_ready','packet_ready'),
             ('prepare','prepare_start','prepare_end'), ('draw','draw_start','native_done')]
    intervals, durations = [], {}
    for stage, lo, hi in pairs:
        if len(grouped[lo]) != r['frames'] or len(grouped[hi]) != r['frames']:
            raise ValueError('missing stage boundaries')
        for a, b in zip(grouped[lo], grouped[hi], strict=True):
            if b < a: raise ValueError('negative stage')
            intervals.append((a, b, stage))
        durations[stage] = stats([b-a for a, b in zip(grouped[lo], grouped[hi], strict=True)])
    for service in r['reads']+r['seek_calls']:
        a, b = service['start_tstate'], service['end_tstate']
        if b-a != service['tstates']: raise ValueError('service duration differs')
        intervals.append((a, b, 'disk'))
    lo, hi = r['publications'][0]['tstate'], r['publications'][-1]['tstate']
    changes = defaultdict(Counter)
    for start, end, stage in intervals:
        start, end = max(lo, start), min(hi, end)
        if start < end: changes[start][stage] += 1; changes[end][stage] -= 1
    changes[lo]; changes[hi]
    active, bins, disk_contexts = Counter(), Counter(), Counter()
    previous, overlapping = lo, 0
    for at, delta in sorted(changes.items()):
        span = at-previous
        high = [s for s in ('draw','prepare','metadata') if active[s]]
        if len(high) > 1 or any(active[s] > 1 for s in ('draw','prepare','metadata')):
            raise ValueError('overlapping non-suspendable frame stages')
        context = high[0] if high else 'transfer' if active['transfer'] else 'outside_stages'
        if active['disk']:
            bins['disk_service'] += span; disk_contexts[context] += span
        else: bins[context] += span
        if high and active['transfer']: overlapping += span
        active.update(delta)
        if any(v < 0 for v in active.values()): raise ValueError('unmatched boundaries')
        previous = at
    if any(active.values()) or sum(bins.values()) != hi-lo:
        raise ValueError('elapsed partition differs')
    return dict(scope=partition.__doc__, first_publication=lo, last_publication=hi,
        span=hi-lo, disjoint_elapsed_tstates=dict(bins),
        disk_service_by_context=dict(disk_contexts),
        suspended_transfer_overlapping_other_stages=overlapping,
        full_stage_lifetime_stats=durations,
        all_captured_read_service=stats([x['tstates'] for x in r['reads']]),
        all_captured_seek_service=stats([x['tstates'] for x in r['seek_calls']]))


def cpu_profile(path, frame=False):
    r = json.loads(path.read_bytes())
    if not r['complete']: raise ValueError(('incomplete CPU profile', path))
    reference = 'direct_motion_target_cpu.json' if frame else 'resumable_packet_cpu.json'
    if r['reference_sha256'] != sha((ROOT/reference).read_bytes()):
        raise ValueError('CPU reference differs')
    stages, instructions, counts, frames = Counter(), Counter(), Counter(), []
    copy_bytes, copy_runs, copy_ticks = Counter(), Counter(), Counter()
    for v in r['volumes']:
        stage_sum = Counter()
        for f in v['frames']: stage_sum.update(f['stages']); frames.append(f['tstates'])
        if dict(stage_sum) != v['stages'] or sum(stage_sum.values()) != v['tstates']:
            raise ValueError('CPU stage/frame mismatch')
        stages.update(stage_sum)
        for row in v['instruction_histogram']:
            if row['total'] != row['tstates']*row['count']: raise ValueError('CPU row mismatch')
            instructions[row['stage'], row['instruction']] += row['total']
            counts[row['stage'], row['instruction']] += row['count']
            if row['stage'] == 'zx0' and row['instruction'] == 'opcode edb0':
                # LDIR repeats at 21 T; the final byte of each call takes 16 T.
                at = row['address']; copy_bytes[at] += row['count']; copy_ticks[at] += row['total']
                if row['tstates'] == 16: copy_runs[at] += row['count']
        if sum(row['total'] for row in v['instruction_histogram']) != v['tstates']:
            raise ValueError('CPU histogram mismatch')
    if len(frames) != 4221 or sum(frames) != r['tstates']: raise ValueError('incomplete CPU frames')
    for key, normalize in (('source_sha256',False), ('source_sha256_lf',True)):
        for name, digest in r.get(key,{}).items():
            blob = (ROOT/name).read_bytes()
            if normalize: blob = blob.replace(b'\r\n', b'\n')
            if sha(blob) != digest: raise ValueError(('CPU source differs',name))
    result = dict(scope=r['scope'], total=r['tstates'], frames=stats(frames),
        stages=[dict(stage=k,tstates=v,percent=100*v/r['tstates']) for k,v in stages.most_common()],
        instruction_groups=[dict(stage=k[0],instruction=k[1],tstates=v)
            for k,v in instructions.most_common(40)],
        indexed_memory=[dict(stage=k[0],instruction=k[1],count=counts[k],tstates=v)
            for k,v in instructions.most_common() if '(IX' in k[1] or '(IY' in k[1]],
        block_copy_instructions=[dict(stage=k[0],instruction=k[1],count=counts[k],tstates=v)
            for k,v in instructions.most_common() if k[1] in ('LDI','LDIR','opcode edb0','opcode eda0')],
        volumes=[dict(part=v['part'],frames=stats([f['tstates'] for f in v['frames']]),
                      tstates=v['tstates'],stages=v['stages']) for v in r['volumes']])
    if frame:
        phases = Counter()
        for name, ticks in stages.items(): phases[name.split('/')[0]] += ticks
        result['phases'] = dict(phases)
        result['frames_over_six_field_cpu_budget'] = sum(t > 6*FIELD for t in frames)
        result['retained_baseline_tstates'] = sum(f['retained_baseline_tstates'] for v in r['volumes'] for f in v['frames'])
    else:
        result['video_sector_reads'] = sum(v['reads'] for v in r['volumes'])
        result['packet_body_bytes'] = sum(f['bytes'] for v in r['volumes'] for f in v['frames'])
        result['zx0_copy_runs'] = [dict(address=at,bytes=n,runs=copy_runs[at],
            mean_bytes=n/copy_runs[at],tstates=copy_ticks[at]) for at,n in sorted(copy_bytes.items())]
        if sum(copy_bytes.values()) != result['packet_body_bytes']+2*len(frames):
            raise ValueError('ZX0 copied-byte count differs from stored packets')
    return result


def build(include_cpu=True):
    references, variants = {}, []
    for name, key in VARIANTS.items():
        summary_path = ROOT/(name+'_summary.json'); folder = ROOT/(name+'_evidence')
        summary = json.loads(summary_path.read_bytes())
        for p in (summary_path,folder/'manifest.json'): references[p.relative_to(ROOT).as_posix()] = sha(p.read_bytes())
        expected = summary['references'].get(name+'_evidence/manifest.json', summary['references'].get('manifest.json'))
        if expected != sha((folder/'manifest.json').read_bytes()) or not summary['complete']:
            raise ValueError('unmatched summary/archive')
        blobs, hashes = load_archive(folder); volumes = []
        for part in (1,2,3):
            stem = f'part{part:02}'; r, m = blobs[stem+'.json'], blobs[stem+'.metadata.json']
            s = summary['volumes'][part-1][key]
            if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact'] or
                    r['debugger_installed_bytes'] or not r['ay_records_exact'] or r['fast_read_retries'] or
                    r['trd_sha256'] != m['trd_sha256'] or not m['independently_bootable']):
                raise ValueError('incomplete or changed playback')
            for suffix, field in (('.trace.txt','trace_sha256'), ('.debugger.txt','debugger_script_sha256'),
                                  ('.metadata.json','integrated_bootstrap_metadata_sha256')):
                if hashes[stem+suffix] != r[field]: raise ValueError('trace provenance differs')
            late = [i for i,p in enumerate(r['publications']) if p['late_fields']]
            if late != s['missed_nominal_frame_indices'] or len(late) != r['nominal_late_frames']:
                raise ValueError('publication count differs')
            for field in ('frames','nominal_late_frames','max_late_fields','bad_actual_intervals','ay_ticks','audio_underruns'):
                if s[field] != r[field]: raise ValueError(('metric differs',field))
            timing = partition(r)
            if timing['span'] != s['publication_span_tstates']: raise ValueError('publication span differs')
            volumes.append(dict(part=part, frames=r['frames'], trd_sha256=r['trd_sha256'],
                missed_nominal_global_frames=[m['frame_start']+i for i in late],
                max_late_fields=r['max_late_fields'], max_actual_deviation_tstates=r['max_actual_deviation_tstates'],
                late_runs=r['late_runs'], recovered_late_runs=s['recovered_late_runs'],
                fallback_met=s['timing_gates']['fallback_one_field_met'],
                ay_50hz_met=s['timing_gates']['actual_ay_50hz'], timing=timing))
        bins = Counter()
        for v in volumes: bins.update(v['timing']['disjoint_elapsed_tstates'])
        variants.append(dict(name=name, totals=summary['totals'], volumes=volumes,
                             disjoint_elapsed_tstates=dict(bins)))
        print(f'{name}: all 4221 archived frames, stage partition exact', flush=True)
    reservoir_path = ROOT/'late_reservoir_profile.json'
    reservoir = json.loads(reservoir_path.read_bytes())
    if not reservoir['complete']: raise ValueError('incomplete reservoir profile')
    for name,digest in reservoir['references'].items():
        if sha((ROOT/name).read_bytes()) != digest: raise ValueError('reservoir reference differs')
    references[reservoir_path.name] = sha(reservoir_path.read_bytes())
    result = dict(complete=include_cpu, release=False, scope=__doc__, variants=variants,
        new_fuse_playback=False, player_cpu_delta_tstates=0, stream_delta_bytes=0,
        references=references, source_sha256=sha(Path(__file__).read_bytes()),
        baseline_reservoir=[{k:v[k] for k in ('part','decoded_reserve','packets_without_completed_slot',
            'packets_with_at_most_six_ready_bytes','worst_work_windows')} for v in reservoir['volumes']])
    if include_cpu:
        for name, frame in (('current_frame_profile.json',True),('packet_cpu_profile.json',False)):
            result['frame_cpu' if frame else 'packet_cpu'] = cpu_profile(ROOT/name, frame)
            references[name] = sha((ROOT/name).read_bytes())
        # Metadata is deliberately duplicated between these independent fixtures.
        a = sum(v['stages']['metadata/compiled_metadata'] for v in result['frame_cpu']['volumes'])
        b = sum(v['stages']['compiled_metadata'] for v in result['packet_cpu']['volumes'])
        if a != b: raise ValueError('shared metadata fixture differs')
        result['duplicate_metadata_tstates_do_not_add_twice'] = a
        packet = json.loads((ROOT/'packet_cpu_profile.json').read_bytes())
        for v, retained in zip(packet['volumes'],variants[0]['volumes'],strict=True):
            if v['trd_sha256'] != retained['trd_sha256'] or not v['complete']:
                raise ValueError('packet profile used a different player')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'player_comparison_profile.json')
    p.add_argument('--traces-only',action='store_true',help='Partial smoke without CPU fixtures')
    p.add_argument('--check',action='store_true',help='Recompute and compare with the saved report')
    a = p.parse_args(); result = build(not a.traces_only)
    if a.check:
        if json.loads(a.output.read_bytes()) != result: raise ValueError('saved comparison differs')
        print('Saved comparison, references, all stage/CPU sums verified',flush=True)
    else:
        if a.output.exists(): p.error('output already exists; use --check or a new path')
        a.output.parent.mkdir(parents=True,exist_ok=True)
        a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')


if __name__ == '__main__': main()
