"""Audit the complete in-place producer, cold boots and three-volume Fuse run.

Producer/coroutine CPU measurements exclude ROM, physical disk latency,
ULA waits and IRQ. Fuse delivery includes emulated waits and interrupts.
The unchanged renderer reuses the earlier full-frame CPU comparison;
this experiment's Fuse run samples 80 screen bytes per frame.
"""
import argparse
import gzip
import json
from pathlib import Path
import struct

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze
from summarize_fast_return_irq import rom_invariants
from summarize_resident_audio_player import saved_attempt
from summarize_uncontended_frame import metrics

ROOT = Path(__file__).parent
OUTPUT = ROOT/'inplace_slot_summary.json'


def archive(name):
    folder = ROOT/'inplace_slot_evidence'/name; manifest_path = folder/'manifest.json'
    manifest = json.loads(manifest_path.read_bytes()); blobs = {}
    for item in manifest['files']:
        packed = (folder/item['file']).read_bytes(); raw = gzip.decompress(packed)
        if sha(packed)!=item['sha256'] or sha(raw)!=item['decoded_sha256'] or len(raw)!=item['decoded_bytes']:
            raise ValueError(('archive changed', item['file']))
        blobs[item['file'][:-3]] = raw
    if not manifest['complete']: raise ValueError('incomplete snapshot')
    build = json.loads(blobs['build.json'])
    if not build['complete']: raise ValueError('incomplete archived build')
    for name, digest in build['source_sha256_lf'].items():
        if sha(blobs['source-'+name].replace(b'\r\n', b'\n'))!=digest:
            raise ValueError('archived generator changed')
    return blobs, manifest_path


def summarize():
    blobs, manifest_path = archive('reload')
    paths = [ROOT/n for n in ('inplace_slot_player_build.json', 'inplace_slot_cpu.json',
                             'resident_audio_player_summary.json', 'inplace_zx0_probe.json',
                             'cached_huffman_lookahead_cpu.json')]
    build, cpu, baseline, probe, frame_cpu = [json.loads(p.read_bytes()) for p in paths]
    old_blobs, old_build, old_manifest_sha = saved_attempt('foreground')
    if (not all(r['complete'] for r in (build, cpu, baseline, probe, frame_cpu))
            or frame_cpu['checked_frames']!=4221 or blobs['build.json']!=paths[0].read_bytes()
            or build['baseline_build_sha256']!=sha(old_blobs['build.json'])
            or cpu['probe_sha256']!=sha(paths[3].read_bytes())
            or cpu['build_sha256']!=sha(paths[0].read_bytes())):
        raise ValueError('incomplete or mismatched evidence')
    for report in (build, cpu):
        for name, digest in report['source_sha256_lf'].items():
            if sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))!=digest:
                raise ValueError(('source changed', name))
    for name, digest in build['source_sha256_lf'].items():
        if sha(blobs['source-'+name].replace(b'\r\n', b'\n'))!=digest:
            raise ValueError('archived source changed')
    swaps = build['mocked_rom_swaps']
    if ([(v['from_part'], v['to_part']) for v in swaps]!=[(1, 2), (2, 3)]
            or not all(v[k] for v in swaps for k in ('prompt_exact', 'wrong_disk_rejected',
                'wrong_series_rejected', 'correct_disk_accepted', 'bootstrap_ram_exact', 'rom_mocked'))):
        raise ValueError('disk swaps incomplete')
    cpu_keys = ('producer_tstates', 'decoder_tstates', 'total_tstates', 'sector_reads', 'carry_copy_bytes')
    for variant in cpu['variants']:
        for volume in variant['volumes']:
            size, part = variant['block_bytes'], volume['part']; summary = volume['summary']
            filename = f'block{size}-part{part:02}.stream.gz'
            packed = (ROOT/'inplace_zx0_evidence'/filename).read_bytes()
            entry = next(v for v in probe['archives'] if v['file']==filename)
            if sha(packed)!=entry['sha256']: raise ValueError('reference stream changed')
            stream = gzip.decompress(packed); at = 0
            for index, block in enumerate(volume['blocks']):
                n, count = struct.unpack_from('<HH', stream, at); at += 4
                payload = stream[at:at+count]; at += count
                if (not block['exact'] or block['index']!=index or block['decoded_bytes']!=n
                        or block['payload_bytes']!=count or block['payload_sha256']!=sha(payload)
                        or block['producer_tstates']!=block['begin_tstates']+sum(block['step_tstates'])
                        or block['decoder_tstates']!=sum(block['slice_tstates'])):
                    raise ValueError('CPU block differs from archived stream')
            if (at!=len(stream) or not summary['complete'] or not summary['sectors_exact_once']
                    or summary['sector_reads']!=(len(stream)+255)//256
                    or sum(v['count']*v['tstates'] for v in summary['instruction_histogram'])!=summary['producer_tstates']
                    or summary['total_tstates']!=summary['producer_tstates']+summary['decoder_tstates']):
                raise ValueError('CPU instruction or sector accounting differs')
            for key, block_key in (('producer_tstates', 'producer_tstates'), ('decoder_tstates', 'decoder_tstates'),
                                   ('sector_reads', 'sectors'), ('carry_copy_bytes', 'carry_copy_bytes')):
                if sum(v[block_key] for v in volume['blocks'])!=summary[key]: raise ValueError('CPU sum differs')
        if any(sum(v['summary'][k] for v in variant['volumes'])!=variant['totals'][k] for k in cpu_keys):
            raise ValueError('CPU variant total differs')
    if [v['block_bytes'] for v in cpu['variants']]!=[8192, 15872]: raise ValueError('wrong CPU variants')
    volumes = []
    for part in (1, 2, 3):
        stem = f'part{part:02}'; m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
        built = build['volumes'][part-1]; old = old_build['volumes'][part-1]
        before = baseline['variants']['foreground']['volumes'][part-1]
        core = cpu['variants'][1]['volumes'][part-1]; old_core = cpu['variants'][0]['volumes'][part-1]
        prior_frames = frame_cpu['volumes'][part-1]
        if (not r['complete'] or r['errors'] or r['failure'] or not r['trace_nonce_exact']
                or r['debugger_installed_bytes'] or r['fast_read_retries'] or not r['ay_records_exact']
                or not r['progress_100_percent'] or not m['independently_bootable'] or m['used_sectors']>2544
                or r['frames']!=m['frames'] or prior_frames['checked_frames']!=m['frames']
                or m['raw_sha256']!=prior_frames['raw_sha256']
                or r['native_frames_sampled']!=m['frames'] or r['pixel_samples_per_frame']!=80
                or r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors']
                or core['summary']['sector_reads']!=m['video_sectors']
                or core['video_start_sector']!=m['video_start_sector']
                or r['trd_sha256']!=m['trd_sha256'] or m['trd_sha256']!=built['trd_sha256']
                or sha(blobs[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256']
                or m['inplace_video']!=built['inplace_video']
                or not all(built[k] for k in ('dirty_ram_boot_exact', 'first_native_screen_exact',
                    'second_compact_frame_exact', 'audio_bank_immutable_exact', 'exact_video_field_roundtrip'))):
            raise ValueError(('incomplete/mismatched playback', part))
        if any(built[k]!=old[k] for k in ('raw_video_sha256', 'audio_sha256', 'frames')):
            raise ValueError('video or audio payload changed')
        if core['regions']!=m['inplace_video']['regions']: raise ValueError('different measured/installed producer')
        if len(core['blocks'])!=len(m['blocks']): raise ValueError('block count differs')
        for block, info in zip(core['blocks'], m['blocks'], strict=True):
            if (block['raw_sha256']!=info['sha256'] or block['decoded_bytes']!=info['decoded_bytes']
                    or not info['inplace_layout']['sector_aligned_fits']):
                raise ValueError('native block proof differs')
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            if sha(blobs[stem+suffix])!=r[key]: raise ValueError('trace changed')
        irq = audit(r, m); irq.pop('actual_phase_tstates')
        gate = summarize_fuse(r); gate.pop('publication_intervals_tstates')
        profile = analyze(r, m, prior_frames)
        worst = sorted(profile.pop('frames'), key=lambda v:v['work_elapsed'], reverse=True)[:8]
        after = dict(metrics(r), timing_gates=gate, irq=irq, rom=rom_invariants(r, True),
            used_sectors=m['used_sectors'], free_sectors=m['free_sectors'], video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'], trd_sha256=m['trd_sha256'],
            ay_record_field_gaps=r['ay_record_field_gaps'], ay_record_field_duplicates=r['ay_record_field_duplicates'],
            delivery_profile=profile, worst_work_frames=worst)
        delta = {k:after[k]-before[k] for k in ('nominal_late_frames', 'audio_underruns', 'runtime_sectors',
                 'publication_span_tstates', 'bad_actual_intervals', 'used_sectors', 'video_bytes')}
        volumes.append(dict(part=part, inplace=after, delta=delta,
            cpu_before={k:old_core['summary'][k] for k in cpu_keys},
            cpu_after={k:core['summary'][k] for k in cpu_keys},
            cpu_delta={k:core['summary'][k]-old_core['summary'][k] for k in cpu_keys}))
    keys = ('frames', 'nominal_late_frames', 'audio_underruns', 'runtime_sectors', 'publication_span_tstates',
            'bad_actual_intervals', 'used_sectors', 'video_bytes', 'ay_ticks')
    totals = {k:sum(v['inplace'][k] for v in volumes) for k in keys}
    if totals['frames']!=4221 or totals['ay_ticks']!=25326: raise ValueError('incomplete movie')
    totals.update(nominal_schedule_met=all(v['inplace']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['inplace']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['inplace']['timing_gates']['actual_ay_50hz'] for v in volumes),
        cpu_before=cpu['variants'][0]['totals'], cpu_after=cpu['variants'][1]['totals'],
        cpu_delta={k:cpu['variants'][1]['totals'][k]-cpu['variants'][0]['totals'][k] for k in cpu_keys})
    initial, initial_manifest = archive('initial'); attempts = []
    initial_cpu_path = ROOT/'inplace_slot_evidence/initial/cpu.json.gz'
    initial_cpu = json.loads(gzip.decompress(initial_cpu_path.read_bytes()))
    if not initial_cpu['complete']: raise ValueError('incomplete initial CPU fixture')
    for name, digest in initial_cpu['source_sha256_lf'].items():
        archived = initial.get('source-'+name)
        if archived is None: archived = (ROOT/name).read_bytes()
        if sha(archived.replace(b'\r\n', b'\n'))!=digest:
            raise ValueError('initial CPU source differs')
    for part in (1, 2, 3):
        stem = f'part{part:02}'; m = json.loads(initial[stem+'.metadata.json']); r = json.loads(initial[stem+'.json'])
        if (not r['complete'] or r['failure'] or r['errors'] or not r['ay_records_exact']
                or r['debugger_installed_bytes'] or not r['trace_nonce_exact']
                or r['trd_sha256']!=m['trd_sha256'] or r['frames']!=m['frames']
                or r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors']
                or sha(initial[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256']):
            raise ValueError('initial attempt evidence differs')
        for suffix, key in (('.trace.txt', 'trace_sha256'), ('.debugger.txt', 'debugger_script_sha256')):
            if sha(initial[stem+suffix])!=r[key]: raise ValueError('initial trace differs')
        gate = summarize_fuse(r); gate.pop('publication_intervals_tstates')
        failed_reads = []
        for index, read in enumerate(r['reads']):
            if read.get('retried'):
                failed_reads.append(dict(sector=read['sector'], failed_read_tstates=read['tstates'],
                    preceding_idle_fields=(read['start_tstate']-r['reads'][index-1]['end_tstate'])/70908,
                    fallback_tstates=r['reads'][index+1]['tstates']))
        attempts.append(dict(part=part, **metrics(r), fast_read_retries=r['fast_read_retries'],
            timing_gates=gate, max_read_service_tstates=max(v['tstates'] for v in r['reads']),
            failed_reads=failed_reads,
            ay_record_field_gaps=r['ay_record_field_gaps'], ay_record_field_duplicates=r['ay_record_field_duplicates']))
    return dict(complete=True, release=False, scope=__doc__, baseline_commit='da369e6',
        references={p.name:sha(p.read_bytes()) for p in paths},
        manifests={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (manifest_path, initial_manifest)},
        baseline_manifest_sha256=old_manifest_sha,
        initial_cpu_archive_sha256=sha(initial_cpu_path.read_bytes()),
        initial_cpu_scope='No idle check, both variants use the baseline sector starts 106/107/108; actual first TRDs use 106/108/109.',
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n', b'\n')) for n in
            ('summarize_inplace_slot.py', 'measure_fap3_fuse.py', 'audit_irq_fields.py', 'profile_fap3.py',
             'profile_integrated_timing.py', 'summarize_uncontended_frame.py', 'summarize_fast_return_irq.py')},
        totals=totals, volumes=volumes, initial_attempt=attempts, source_video_and_audio_exact=True,
        all_block_native_bytes_checked=True, full_fuse_pixel_comparison=False,
        full_integrated_cpu_total_measured=False, physical_drive_verified=False,
        initial_disk_and_irq_phases_not_matched=True,
        note='Full frame CPU reference is reused for the unchanged renderer, not a rerun of this integrated player. '
             'CPU deltas cover all sector/header/carry producer and 256-byte-quota decoder work; '
             'actual queue quota selection, AY, ULA, ROM and disk waits remain outside that CPU fixture. '
             'The CPU fixture clock stays at zero; rare head reload branches are counted separately in boundary tests.')


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--write', action='store_true')
    args = p.parse_args(); result = json.loads(json.dumps(summarize()))
    if args.write: OUTPUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8', newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps(result['totals']), flush=True)


if __name__ == '__main__': main()
