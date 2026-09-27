"""Audit periodic drive maintenance against the full pre-read recovery attempt.

CPU helper counts exclude ROM/IRQ/ULA. Saved Fuse traces include complete
disk service, publication and AY timing; screen sampling is 80 bytes/frame.
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
OUTPUT = ROOT/'inplace_keepalive_summary.json'


def summarize():
    folder=ROOT/'inplace_keepalive_evidence'; manifest_path=folder/'manifest.json'
    manifest=json.loads(manifest_path.read_bytes()); blobs={}
    for item in manifest['files']:
        packed=(folder/item['file']).read_bytes(); raw=gzip.decompress(packed)
        if sha(packed)!=item['sha256'] or sha(raw)!=item['decoded_sha256'] or len(raw)!=item['decoded_bytes']:
            raise ValueError(('archive changed',item['file']))
        blobs[item['file'][:-3]]=raw
    paths=[ROOT/n for n in ('inplace_keepalive_build.json','inplace_keepalive_cpu.json',
                            'inplace_slot_summary.json','inplace_slot_player_build.json','cached_huffman_lookahead_cpu.json')]
    build,cpu,baseline,old_build,frame_cpu=[json.loads(p.read_bytes()) for p in paths]
    if (not manifest['complete'] or not all(r['complete'] for r in (build,cpu,baseline,old_build,frame_cpu))
            or build['baseline_build_sha256']!=sha(paths[3].read_bytes()) or blobs['build.json']!=paths[0].read_bytes()
            or frame_cpu['checked_frames']!=4221):raise ValueError('incomplete or mismatched evidence')
    for report in (build,cpu):
        for name,digest in report['source_sha256_lf'].items():
            if sha((ROOT/name).read_bytes().replace(b'\r\n',b'\n'))!=digest:raise ValueError(('source differs',name))
    for name,digest in build['source_sha256_lf'].items():
        if sha(blobs['source-'+name].replace(b'\r\n',b'\n'))!=digest:raise ValueError('archived source differs')
    for case in cpu['cases']:
        if (not case['preserves_state'] or sum(v['tstates']*v['count'] for v in case['instruction_histogram'])!=case['tstates']
                or case['wrapper_delta_tstates']!=case['tstates']+27):raise ValueError('CPU arithmetic differs')
    swaps=build['mocked_rom_swaps']
    if ([(v['from_part'],v['to_part']) for v in swaps]!=[(1,2),(2,3)]
            or not all(v[k] for v in swaps for k in ('prompt_exact','wrong_disk_rejected','wrong_series_rejected',
                'correct_disk_accepted','bootstrap_ram_exact','rom_mocked'))):raise ValueError('swap checks incomplete')
    volumes=[]
    for part in (1,2,3):
        stem=f'part{part:02}'; m=json.loads(blobs[stem+'.metadata.json']); r=json.loads(blobs[stem+'.json'])
        built=build['volumes'][part-1]; previous=old_build['volumes'][part-1]
        before=baseline['volumes'][part-1]['inplace']; core=frame_cpu['volumes'][part-1]
        if (not r['complete'] or r['failure'] or r['errors'] or not r['trace_nonce_exact']
                or not r['ay_records_exact'] or not r['progress_100_percent'] or r['debugger_installed_bytes'] or r['fast_read_retries']
                or r['frames']!=m['frames'] or r['native_frames_sampled']!=m['frames'] or r['pixel_samples_per_frame']!=80
                or r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors']
                or not m['independently_bootable'] or m['used_sectors']>2544 or m['raw_sha256']!=core['raw_sha256']
                or core['checked_frames']!=m['frames'] or r['trd_sha256']!=m['trd_sha256'] or m['trd_sha256']!=built['trd_sha256']
                or sha(blobs[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256']
                or m['inplace_keepalive']!=built['inplace_keepalive'] or m['inplace_video']!=built['inplace_video']
                or not all(built[k] for k in ('dirty_ram_boot_exact','first_native_screen_exact','second_compact_frame_exact',
                    'audio_bank_immutable_exact','exact_video_field_roundtrip'))):raise ValueError(('incomplete playback',part))
        for key in ('video_bytes','video_sectors','stream_sha256','raw_video_sha256','audio_sha256','frames'):
            if built[key]!=previous[key]:raise ValueError(('payload differs',part,key))
        keep=m['inplace_keepalive']; installed=keep['regions'][0]; measured=cpu['implementation']
        # The fixture uses a harmless fixed-RAM counter at 8005. Relocate only
        # its two absolute counter loads before comparing every opcode byte.
        expected=bytearray.fromhex(measured['code_hex'])
        for row in measured['listing']:
            if row['instruction']=='LD HL,(32773)':
                at=row['address']-measured['address']
                if expected[at:at+3]!=b'\x2a\x05\x80':raise ValueError('unexpected fixture counter operand')
                expected[at+1:at+3]=m['player_labels']['elapsed_fields'].to_bytes(2,'little')
        if installed['address']!=measured['address'] or bytes.fromhex(installed['code_hex'])!=expected:
            raise ValueError('measured keepalive differs from installed code')
        if len(keep['hook_addresses'])!=5 or keep['additional_wrapper_tstates']!=27:
            raise ValueError('unexpected hook contract')
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            if sha(blobs[stem+suffix])!=r[key]:raise ValueError('trace changed')
        irq=audit(r,m);irq.pop('actual_phase_tstates')
        gate=summarize_fuse(r);gate.pop('publication_intervals_tstates')
        profile=analyze(r,m,core);worst=sorted(profile.pop('frames'),key=lambda v:v['work_elapsed'],reverse=True)[:8]
        keepalive=[v for v in r['seek_calls'] if v['kind']=='keepalive']
        after=dict(metrics(r),timing_gates=gate,irq=irq,rom=rom_invariants(r,True),
            used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'],trd_sha256=m['trd_sha256'],
            ay_record_field_gaps=r['ay_record_field_gaps'],ay_record_field_duplicates=r['ay_record_field_duplicates'],
            read_service=stats([v['tstates'] for v in r['reads']]),keepalive_service=stats([v['tstates'] for v in keepalive]),
            delivery_profile=profile,worst_work_frames=worst)
        delta={k:after[k]-before[k] for k in ('nominal_late_frames','audio_underruns','runtime_sectors',
                'publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
        volumes.append(dict(part=part,keepalive=after,delta=delta))
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','publication_span_tstates',
          'bad_actual_intervals','used_sectors','video_bytes')
    totals={k:sum(v['keepalive'][k] for v in volumes) for k in keys}
    if totals['frames']!=4221 or totals['ay_ticks']!=25326:raise ValueError('incomplete movie')
    totals.update(nominal_schedule_met=all(v['keepalive']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['keepalive']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['keepalive']['timing_gates']['actual_ay_50hz'] for v in volumes),
        keepalive_calls=sum(v['keepalive']['keepalive_service']['count'] for v in volumes),
        keepalive_rom_elapsed_tstates=sum(v['keepalive']['keepalive_service']['total'] for v in volumes))
    return dict(complete=True,release=False,scope=__doc__,baseline_commit='1d3ac46',totals=totals,volumes=volumes,
        references={p.name:sha(p.read_bytes()) for p in (*paths,manifest_path)},
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('summarize_inplace_keepalive.py','measure_fap3_fuse.py','profile_integrated_timing.py',
             'profile_fap3.py','audit_irq_fields.py','summarize_fast_return_irq.py','summarize_uncontended_frame.py')},
        video_and_audio_payload_unchanged=True,full_fuse_pixel_comparison=False,
        full_integrated_cpu_total_measured=False,physical_drive_verified=False,initial_disk_and_irq_phases_not_matched=True,
        note='Frame and block-decoder full-byte verification is reused for unchanged code/data. '
             'New CPU tests cover maintenance paths; the frequency and total CPU cost of skipped hooks are not replayed.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--write',action='store_true');args=p.parse_args()
    result=json.loads(json.dumps(summarize()))
    if args.write:OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()):raise ValueError('saved summary differs')
    print(json.dumps(result['totals']),flush=True)


if __name__=='__main__':main()
