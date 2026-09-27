"""Audit separate optional-consumer playback without claiming a release.

The deterministic parser CPU test covers explicit prefixes. Full Fuse
checks every publication/AY tick/sector and 80 screen bytes per frame.
Transfer wall intervals may now contain another frame's native drawing;
they must not be summed as exclusive CPU stages.
"""
import argparse
from collections import defaultdict
from fractions import Fraction
import gzip
import json
from pathlib import Path
import struct

from audit_irq_fields import audit
from build_fap3_trd import sha
import disk_layout
from profile_fap3 import summarize_fuse
from profile_integrated_timing import stats
from summarize_fast_return_irq import rom_invariants
from summarize_native_mask_selection import read_archive
from summarize_uncontended_frame import metrics
from zx0_codec import decompress

ROOT = Path(__file__).parent
FOLDER = ROOT/'optional_packet_evidence'
OUTPUT = ROOT/'optional_packet_summary.json'
REPORTS = ('optional_packet_build.json', 'optional_packet_cpu.json')


def archive(directory, traces, baseline_directory):
    build, cpu = [json.loads((ROOT/n).read_bytes()) for n in REPORTS[:2]]
    if not build['complete'] or not cpu['complete']: raise ValueError('incomplete evidence')
    names = set(build['source_sha256_lf']) | set(cpu['source_sha256_lf']) | {
        'summarize_optional_packet.py', 'measure_fap3_fuse.py', 'profile_fap3.py',
        'audit_irq_fields.py', 'summarize_fast_return_irq.py', 'summarize_uncontended_frame.py'}
    files = {n:(ROOT/n).read_bytes() for n in REPORTS}
    files.update({'source-'+n:(ROOT/n).read_bytes() for n in names})
    baseline_build = json.loads((ROOT/'inplace_keepalive_build.json').read_bytes())
    baseline_archive = read_archive(ROOT/'inplace_keepalive_evidence',packed_sizes=False)
    for part in (1,2,3):
        stem = f'part{part:02}'; image = f'ZX-video-huffman-preview_part{part:02}'
        files[stem+'.trd'] = (directory/(image+'.trd')).read_bytes()
        files[stem+'.metadata.json'] = (directory/(image+'.json')).read_bytes()
        for suffix in ('.json','.trace.txt','.debugger.txt'):
            files[stem+suffix] = (traces/(stem+suffix)).read_bytes()
        old_image = (baseline_directory/(image+'.trd')).read_bytes()
        old_m = json.loads(baseline_archive[stem+'.metadata.json'])
        if sha(old_image) != baseline_build['volumes'][part-1]['trd_sha256']:
            raise ValueError('baseline image differs')
        section = next(s for s in old_m['sections'] if s['bank'] == 7)
        at = section['sector']*256+section.get('source_offset',0)
        files[stem+'.baseline-bank7.bin'] = decompress(old_image[at:at+section['compressed_bytes']],limit=section['decoded_bytes'])
    FOLDER.mkdir(exist_ok=True); entries = []
    for name,data in sorted(files.items()):
        blob = gzip.compress(data,mtime=0); path = FOLDER/(name+'.gz'); path.write_bytes(blob)
        entries.append(dict(file=path.name,sha256=sha(blob),decoded_sha256=sha(data),
                            decoded_bytes=len(data),bytes=len(blob)))
    (FOLDER/'manifest.json').write_text(json.dumps(dict(complete=True,release=False,files=entries),indent=2)+'\n',encoding='utf-8',newline='\n')


def cooperative_draws(r, m):
    events = defaultdict(list)
    for row in r['pipeline_events']: events[row['kind']].append(row['tstate'])
    kinds = ('packet_start','video_payload_ready','packet_ready','prepare_start','prepare_end','draw_start','native_done')
    if any(len(events[k]) != m['frames'] for k in kinds): raise ValueError('missing frame stage events')
    for i,pub in enumerate(r['publications']):
        times = [events[k][i] for k in kinds]+[pub['tstate']]
        if times != sorted(times): raise ValueError('invalid frame lifetime')
    draws = []; remaining = []
    for i in range(2,m['frames']):
        start,end = events['packet_start'][i],events['video_payload_ready'][i]
        pub = r['publications'][i-2]['tstate']; draw = events['draw_start'][i-1]
        if events['prepare_end'][i-1] <= start < pub < end:
            row = dict(packet_frame=m['frame_start']+i,ready_frame=m['frame_start']+i-1,
                packet_start=start,packet_transfer_end=end,preceding_publication=pub,
                next_draw=draw,draw_after_publication_tstates=draw-pub,
                ready_frame_late_fields=r['publications'][i-1]['late_fields'])
            (draws if draw < end else remaining).append(row)
    return dict(draws_before_packet_completion=draws,remaining_blocking_reads=remaining,
        resumed_calls=len(draws),remaining_calls=len(remaining),
        resumed_draw_delay=stats([r['draw_after_publication_tstates'] for r in draws]),
        remaining_draw_delay=stats([r['draw_after_publication_tstates'] for r in remaining]),
        transfer_intervals_are_not_exclusive_work=True)


def summarize():
    blobs = read_archive(FOLDER)
    build, cpu = [json.loads(blobs[n]) for n in REPORTS[:2]]
    baseline_build = json.loads((ROOT/'inplace_keepalive_build.json').read_bytes())
    baseline = json.loads((ROOT/'inplace_keepalive_summary.json').read_bytes())
    if not all(r['complete'] for r in (build,cpu,baseline_build,baseline)) or cpu['parts'] != [1,2,3]:
        raise ValueError('incomplete cases')
    if build['baseline_build_sha256'] != sha((ROOT/'inplace_keepalive_build.json').read_bytes()):
        raise ValueError('different baseline')
    global_cpu = json.loads((ROOT/'resumable_packet_cpu.json').read_bytes())
    global_summary = json.loads((ROOT/'resumable_packet_summary.json').read_bytes())
    if (not global_cpu['complete'] or not global_summary['complete'] or
            cpu['reference_sha256'] != sha((ROOT/'resumable_packet_cpu.json').read_bytes()) or
            global_summary['references']['resumable_packet_cpu.json'] != cpu['reference_sha256'] or
            cpu['source_sha256_lf']['test_resumable_packet.py'] != global_cpu['source_sha256_lf']['test_resumable_packet.py']):
        raise ValueError('historical CPU reference or fixture changed')
    for name in REPORTS:
        if blobs[name] != (ROOT/name).read_bytes(): raise ValueError('report changed')
    for r in (build,cpu):
        for name,digest in r['source_sha256_lf'].items():
            if (sha(blobs['source-'+name].replace(b'\r\n',b'\n')) != digest or
                    sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n')) != digest):
                raise ValueError(('source changed',name))
    swaps = build['mocked_rom_swaps']
    if [(s['from_part'],s['to_part']) for s in swaps] != [(1,2),(2,3)] or not all(
            s[k] for s in swaps for k in ('prompt_exact','wrong_disk_rejected','wrong_series_rejected',
                                         'correct_disk_accepted','bootstrap_ram_exact','rom_mocked')):
        raise ValueError('incomplete handoff checks')
    old_archive = read_archive(ROOT/'inplace_keepalive_evidence',packed_sizes=False)
    if sha((ROOT/'inplace_keepalive_evidence/manifest.json').read_bytes()) != baseline['references']['manifest.json']:
        raise ValueError('baseline archive changed')
    volumes = []
    for part in (1,2,3):
        stem = f'part{part:02}'; image = blobs[stem+'.trd']
        m = json.loads(blobs[stem+'.metadata.json']); r = json.loads(blobs[stem+'.json'])
        built = build['volumes'][part-1]; old = baseline_build['volumes'][part-1]
        if (sha(image) != built['trd_sha256'] or sha(image) != m['trd_sha256'] or r['trd_sha256'] != sha(image)
                or sha(blobs[stem+'.metadata.json']) != built['metadata_sha256']
                or built['metadata_sha256'] != r['integrated_bootstrap_metadata_sha256']
                or not r['complete'] or r['failure'] or r['errors'] or r['debugger_installed_bytes']
                or not r['trace_nonce_exact'] or not r['ay_records_exact'] or not r['progress_100_percent']
                or r['frames'] != m['frames'] or r['native_frames_sampled'] != m['frames']
                or r['pixel_samples_per_frame'] != 80 or r['ay_ticks'] != 6*m['frames']
                or r['runtime_sectors_checked'] != m['video_sectors'] or r['fast_read_retries']
                or m['used_sectors'] > 2544 or Fraction(str(m['fps'])) != Fraction(25,3) or m['ay_hz'] != 50
                or not all(built[k] for k in ('independently_bootable','dirty_ram_boot_exact','first_native_screen_exact',
                    'second_compact_frame_exact','audio_bank_immutable_exact','exact_video_and_ay_bytes'))):
            raise ValueError(('incomplete build/playback',part))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            if sha(blobs[stem+suffix]) != r[key]: raise ValueError('trace changed')
        bank7 = next(s for s in m['sections'] if s['bank'] == 7)
        at = bank7['sector']*256+bank7.get('source_offset',0)
        ram = decompress(image[at:at+bank7['compressed_bytes']],limit=bank7['decoded_bytes'])
        if sha(ram) != bank7['sha256']: raise ValueError('bank-7 startup payload differs')
        for patch in m['resumable_packet']['patches']+m['resumable_packet']['regions']:
            code = bytes.fromhex(patch['code_hex']); offset = patch['address']-bank7['address']
            if offset < 0 or ram[offset:offset+len(code)] != code: raise ValueError('installed reader patch differs')
        old_m = json.loads(old_archive[stem+'.metadata.json']); old_r = json.loads(old_archive[stem+'.json'])
        old_section = next(s for s in old_m['sections'] if s['bank'] == 7)
        old_ram = blobs[stem+'.baseline-bank7.bin']
        q = m['queue_labels']; optional = m['resumable_packet']; labels = optional['labels']
        original = old_ram[q['take']-old_section['address']:q['fatal']-old_section['address']]
        installed = ram[q['take']-bank7['address']:q['fatal']-bank7['address']]
        if (sha(old_ram) != old_section['sha256'] or installed != original or
                sha(installed) != optional['original_required_consumer_sha256'] or
                not optional['optional_consumer'] or not optional['shared_queue_state'] or
                optional['dynamic_routing'] or optional['extra_stack_bytes'] != 0):
            raise ValueError('original required consumer changed')
        # Check every copied opcode and relocated destination against the
        # actual baseline bootstrap, independently of the clone builder.
        for row in optional['copied_instructions']:
            before = bytes.fromhex(row['previous_hex']); pc = row['original_address']
            if original[pc-q['take']:pc-q['take']+len(before)] != before:
                raise ValueError('copied source opcode differs')
            expected = before
            if before[0] in (0xc3,0xca,0xc2,0xda,0xd2,0xcd):
                target = int.from_bytes(before[1:],'little')
                if q['take'] <= target < q['fatal']:
                    target = labels['gate'] if target == q['take_next'] else labels[f'original_{target}']
                elif target == q['demand']: target = labels['partial']
                expected = bytes([before[0]])+target.to_bytes(2,'little')
            offset = row['address']-bank7['address']
            if ram[offset:offset+len(expected)] != expected: raise ValueError('copied consumer opcode differs')
        first = m['video_start_sector']
        stream = b''.join(image[(first+n)*256:(first+n+1)*256] for n in disk_layout.positions(m['video_sectors'],first%16))[:m['video_bytes']]
        if sha(stream) != old['stream_sha256'] or sha(stream) != built['stream_sha256']:
            raise ValueError('compressed movie stream changed')
        decoded = bytearray(); pos = 0
        while pos < len(stream):
            size,length = struct.unpack_from('<HH',stream,pos); pos += 4
            decoded += decompress(stream[pos:pos+length],limit=size); pos += length
        if (pos != len(stream) or sha(decoded) != old['raw_video_sha256'] or
                old['audio_sha256'] != built['audio_sha256'] or built['raw_video_sha256'] != sha(decoded)):
            raise ValueError('video/audio payload differs')
        prefix = cpu['volumes'][part-1]
        global_prefix = global_cpu['volumes'][part-1]
        if prefix['baseline'] != global_prefix['baseline'] or not prefix['required_consumer_exact']:
            raise ValueError('saved baseline or cold consumer verification differs')
        for name in ('baseline','required','resumed','irq','split_length'):
            case = prefix[name]
            if (not all(case[k] for k in ('every_packet_exact','every_packet_byte_written_once','stack_and_bank_restored'))
                    or sum(f['tstates'] for f in case['frames']) != case['tstates']
                    or sum(h['tstates']*h['count'] for h in case['instruction_histogram']) != case['tstates']):
                raise ValueError('prefix CPU evidence differs')
            if name != 'baseline' and case['trd_sha256'] != sha(image): raise ValueError('CPU checked a different disk')
            if name == 'baseline' and case['trd_sha256'] != old['trd_sha256']: raise ValueError('CPU baseline disk differs')
            if len(case['frames']) != (8 if name == 'irq' else 1 if name == 'split_length' else 256):
                raise ValueError('unexpected CPU coverage')
        for name in ('required','resumed'):
            if prefix[name+'_delta_tstates'] != prefix[name]['tstates']-prefix['baseline']['tstates']:
                raise ValueError('prefix CPU delta differs')
            if prefix[name+'_delta_from_global_gate_tstates'] != prefix[name]['tstates']-global_prefix[name]['tstates']:
                raise ValueError('global-gate CPU delta differs')
        required = prefix['required']; labels = m['resumable_packet']['labels']
        counts = {name:sum(h['count'] for h in required['instruction_histogram'] if h['address'] == labels[name])
                  for name in ('take_dispatch','resume_dispatch','gate','partial')}
        if counts != dict(take_dispatch=2*len(required['frames']),resume_dispatch=0,gate=0,partial=0) or any(
                h['count'] for h in required['instruction_histogram']
                if labels['optional_take'] <= h['address'] < labels['stage']):
            raise ValueError('required CPU unexpectedly entered optional consumer')
        delivery_addresses = {r['address'] for r in m['inplace_video']['producer_listing']}
        delivery_addresses.update(r['address'] for r in m['slot_queue_instruction_listing']
                                  if r.get('phase') in ('disk_adapter','cached_seek','interleaved_cursor'))
        delivery_cost = {name:sum(h['tstates']*h['count'] for h in prefix[name]['instruction_histogram']
                                 if h['address'] in delivery_addresses or h['address'] < 0x4000)
                         for name in ('baseline','required')}
        layout_delta = delivery_cost['required']-delivery_cost['baseline']
        # The test enters required directly. Real legacy CALL sites first
        # execute an additional 10-T JP trampoline. No such JP is hidden here.
        predicted = 245*len(required['frames'])
        if predicted+layout_delta != prefix['required_delta_tstates']:
            raise ValueError('mandatory parser instruction formula differs')
        if not prefix['split_length']['paused'] or not prefix['split_length']['irq_calls']:
            raise ValueError('split length/EOF/IRQ case was not exercised')
        gates = summarize_fuse(r); gates.pop('publication_intervals_tstates')
        interrupts = audit(r,m); interrupts.pop('actual_phase_tstates')
        result = dict(metrics(r),timing_gates=gates,irq=interrupts,rom=rom_invariants(r,True),
            used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],video_bytes=m['video_bytes'],
            video_start_sector=first,cooperative=cooperative_draws(r,m),
            required_consumer_bytes_unchanged=True,helper_bytes=optional['helper_bytes'],
            required_prefix_cpu_delta_tstates=prefix['required_delta_tstates'],
            forced_prefix_cpu_delta_tstates=prefix['resumed_delta_tstates'],
            required_prefix_formula=dict(frames=len(required['frames']),counts=counts,parser_delta_tstates=predicted,
                producer_disk_cpu_tstates=delivery_cost,layout_delta_tstates=layout_delta,
                delta_tstates=predicted+layout_delta))
        previous = baseline['volumes'][part-1]['keepalive']
        delta = {k:result[k]-previous[k] for k in ('nominal_late_frames','audio_underruns','runtime_sectors',
                  'publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
        previous_global = global_summary['volumes'][part-1]['candidate']
        delta_global = {k:result[k]-previous_global[k] for k in delta}
        volumes.append(dict(part=part,candidate=result,delta=delta,delta_from_global_gate=delta_global,
                            baseline_blocking=cooperative_draws(old_r,old_m)))
    totals = {k:sum(v['candidate'][k] for v in volumes) for k in ('frames','nominal_late_frames','audio_underruns',
        'ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
    if totals['frames'] != 4221 or totals['ay_ticks'] != 25326: raise ValueError('incomplete movie')
    totals.update(nominal_schedule_met=all(v['candidate']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['candidate']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['candidate']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True,release=False,scope=__doc__,baseline_commit='a84451d',global_gate_commit='25780a9',totals=totals,volumes=volumes,
        compressed_movie_bytes_unchanged=True,full_integrated_native_pixel_comparison=False,
        full_integrated_cpu_total_measured=False,physical_drive_verified=False,initial_disk_and_irq_phases_not_matched=True,
        references={n:sha((ROOT/n).read_bytes()) for n in (*REPORTS,'inplace_keepalive_build.json',
                    'inplace_keepalive_summary.json','inplace_keepalive_evidence/manifest.json','optional_packet_evidence/manifest.json',
                    'resumable_packet_cpu.json','resumable_packet_summary.json')},
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
                    ('summarize_optional_packet.py','profile_fap3.py','audit_irq_fields.py','summarize_fast_return_irq.py')})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-directory',type=Path); p.add_argument('--trace-directory',type=Path)
    p.add_argument('--baseline-directory',type=Path,default=Path('.tmp/inplace-keepalive-player'))
    p.add_argument('--write',action='store_true'); a = p.parse_args()
    if bool(a.archive_directory) != bool(a.trace_directory): raise ValueError('both archive paths required')
    if a.archive_directory: archive(a.archive_directory,a.trace_directory,a.baseline_directory)
    result = json.loads(json.dumps(summarize()))
    if a.write: OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif result != json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps(result['totals']),flush=True)


if __name__ == '__main__': main()
