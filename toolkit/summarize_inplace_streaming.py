"""Archive and audit all three in-place sector-streaming experiments.

Full Fuse runs cover every publication, AY record and sector, with 80 pixel
samples per frame. Native block tests check every decompressed byte. Unchanged
frame reconstruction reuses the earlier full-screen CPU proof. Not a release.
"""
import argparse
import gzip
import json
from pathlib import Path

from audit_irq_fields import audit
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze,stats
from summarize_fast_return_irq import rom_invariants
from summarize_uncontended_frame import metrics
from verify_streaming_zx0_input import validate_histogram

ROOT=Path(__file__).parent
FOLDER=ROOT/'inplace_streaming_evidence'
OUTPUT=ROOT/'inplace_streaming_summary.json'
REPORTS=('inplace_streaming_build.json','inplace_streaming_cpu.json','inplace_streaming_queue_cpu.json')


def archive(directory,traces):
    reports={name:json.loads((ROOT/name).read_bytes()) for name in REPORTS}
    if not all(r['complete'] for r in reports.values()):raise ValueError('incomplete reports')
    source_names=sorted({n for r in reports.values() for n in r['source_sha256_lf']}|
        {'summarize_inplace_streaming.py','test_inplace_streaming.py'})
    files={name:(ROOT/name).read_bytes() for name in REPORTS}
    files.update({'source-'+n:(ROOT/n).read_bytes() for n in source_names})
    for part in (1,2,3):
        files[f'part{part:02}.metadata.json']=(directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
        for suffix in ('.json','.trace.txt','.debugger.txt'):
            name=f'part{part:02}'+suffix;files[name]=(traces/name).read_bytes()
    FOLDER.mkdir(exist_ok=True);entries=[]
    for name,data in sorted(files.items()):
        packed=gzip.compress(data,mtime=0);filename=name+'.gz';(FOLDER/filename).write_bytes(packed)
        entries.append(dict(file=filename,sha256=sha(packed),decoded_sha256=sha(data),
            decoded_bytes=len(data),bytes=len(packed)))
    manifest=dict(complete=True,release=False,files=entries)
    (FOLDER/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')


def summarize():
    manifest_path=FOLDER/'manifest.json';manifest=json.loads(manifest_path.read_bytes());blobs={}
    if not manifest['complete']:raise ValueError('incomplete archive')
    for item in manifest['files']:
        packed=(FOLDER/item['file']).read_bytes();data=gzip.decompress(packed)
        if (sha(packed)!=item['sha256'] or sha(data)!=item['decoded_sha256'] or
                len(data)!=item['decoded_bytes'] or len(packed)!=item['bytes']):raise ValueError('archive changed')
        blobs[item['file'][:-3]]=data
    build,cpu,queue=[json.loads((ROOT/n).read_bytes()) for n in REPORTS]
    previous_path=ROOT/'inplace_keepalive_build.json';previous=json.loads(previous_path.read_bytes())
    baseline_path=ROOT/'inplace_keepalive_summary.json';baseline=json.loads(baseline_path.read_bytes())
    frame_path=ROOT/'cached_huffman_lookahead_cpu.json';frame=json.loads(frame_path.read_bytes())
    if (not all(r['complete'] for r in (build,cpu,queue,previous,baseline,frame)) or frame['checked_frames']!=4221
            or build['baseline_build_sha256']!=sha(previous_path.read_bytes())
            or cpu['build_sha256']!=sha(previous_path.read_bytes())
            or cpu['streaming_build_sha256']!=sha((ROOT/REPORTS[0]).read_bytes())):
        raise ValueError('incomplete or mismatched report references')
    for name,report in zip(REPORTS,(build,cpu,queue),strict=True):
        if blobs[name]!=(ROOT/name).read_bytes():raise ValueError('archived report differs')
        for source,digest in report['source_sha256_lf'].items():
            if (sha((ROOT/source).read_bytes().replace(b'\r\n',b'\n'))!=digest or
                    sha(blobs['source-'+source].replace(b'\r\n',b'\n'))!=digest):raise ValueError(('source changed',source))
    for name,v in queue['variants'].items():
        actual=(previous if name=='baseline' else build)['volumes'][0]
        if v['trd_sha256']!=actual['trd_sha256'] or v['metadata_sha256']!=actual['metadata_sha256']:
            raise ValueError('queue-control code is from a different image')
        for row in v['cases']:
            if sum(r['tstates']*r['count'] for r in row['instruction_histogram'])!=row['tstates']:
                raise ValueError('queue-control CPU arithmetic differs')
    swaps=build['mocked_rom_swaps']
    if ([(v['from_part'],v['to_part']) for v in swaps]!=[(1,2),(2,3)] or not all(v[k] for v in swaps for k in
        ('prompt_exact','wrong_disk_rejected','wrong_series_rejected','correct_disk_accepted','bootstrap_ram_exact','rom_mocked'))):
        raise ValueError('incomplete independent-disk handoff')
    volumes=[]
    for part in (1,2,3):
        stem=f'part{part:02}';m=json.loads(blobs[stem+'.metadata.json']);r=json.loads(blobs[stem+'.json'])
        built=build['volumes'][part-1];old=previous['volumes'][part-1];native=cpu['volumes'][part-1]
        if (not r['complete'] or r['failure'] or r['errors'] or r['debugger_installed_bytes'] or r['fast_read_retries']
                or not r['trace_nonce_exact'] or not r['ay_records_exact'] or not r['progress_100_percent']
                or r['frames']!=m['frames'] or r['native_frames_sampled']!=m['frames'] or r['pixel_samples_per_frame']!=80
                or r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors']
                or r['trd_sha256']!=m['trd_sha256'] or m['trd_sha256']!=built['trd_sha256']
                or sha(blobs[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256']
                or sha(blobs[stem+'.metadata.json'])!=built['metadata_sha256']
                or m['streaming_input']!=built['streaming_input'] or m['used_sectors']>2544
                or not all(built[k] for k in ('independently_bootable','dirty_ram_boot_exact','first_native_screen_exact',
                    'second_compact_frame_exact','audio_bank_immutable_exact','exact_video_field_roundtrip'))):
            raise ValueError(('incomplete playback or build',part))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            if sha(blobs[stem+suffix])!=r[key]:raise ValueError('trace identity differs')
        for key in ('frames','video_bytes','video_sectors','stream_sha256','raw_video_sha256','audio_sha256'):
            if built[key]!=old[key]:raise ValueError(('payload changed',part,key))
        if (native['stream_sha256']!=built['stream_sha256'] or native['video_start_sector']!=old['video_start_sector']
                or native['streaming_video_start_sector']!=built['video_start_sector']):raise ValueError('CPU fixture differs')
        for before,after in zip(native['baseline'],native['streaming'],strict=True):
            if any(before[k]!=after[k] for k in ('index','decoded_bytes','payload_bytes','raw_sha256','payload_sha256','exact')):
                raise ValueError('paired native blocks differ')
        for variant in ('baseline','streaming'):
            summary=native[variant+'_summary'];rows=native[variant]
            if (not summary['complete'] or not summary['sectors_exact_once'] or
                    not summary['decoder_instruction_table_checked'] or not all(v['exact'] for v in rows)):
                raise ValueError('native proof incomplete')
            for row in rows:
                if row['producer_tstates']!=row['begin_tstates']+sum(row['step_tstates']) or row['decoder_tstates']!=sum(row['slice_tstates']):
                    raise ValueError('block CPU arithmetic differs')
            for key in ('producer_tstates','decoder_tstates','carry_copy_bytes'):
                if sum(v[key] for v in rows)!=summary[key]:raise ValueError(('CPU sum differs',key))
            if (sum(v['sectors'] for v in rows)!=summary['sector_reads'] or summary['sector_reads']!=built['video_sectors']
                    or summary['total_tstates']!=summary['producer_tstates']+summary['decoder_tstates']
                    or sum(v['tstates']*v['count'] for v in summary['instruction_histogram'])!=summary['producer_tstates']):
                raise ValueError('sector or producer instruction totals differ')
            ticks=sum(validate_histogram(bytes.fromhex(v['opcode_hex']),v['pc'],[v]) for v in summary['decoder_instruction_histogram'])
            if ticks!=summary['decoder_tstates']:raise ValueError('decoder table total differs')
        for region in m['streaming_input']['regions']:
            if sha(bytes.fromhex(region['code_hex']))!=region['sha256']:raise ValueError('installed code digest differs')
        core=frame['volumes'][part-1]
        if core['checked_frames']!=m['frames'] or core['raw_sha256']!=m['raw_sha256']:raise ValueError('different frame CPU proof')
        irq=audit(r,m);irq.pop('actual_phase_tstates')
        gates=summarize_fuse(r);gates.pop('publication_intervals_tstates')
        profile=analyze(r,m,core);worst=sorted(profile.pop('frames'),key=lambda f:f['work_elapsed'],reverse=True)[:8]
        result=dict(metrics(r),timing_gates=gates,irq=irq,rom=rom_invariants(r,True),
            used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],video_start_sector=m['video_start_sector'],
            video_bytes=m['video_bytes'],read_service=stats([v['tstates'] for v in r['reads']]),
            delivery_profile=profile,worst_work_frames=worst)
        before=baseline['volumes'][part-1]['keepalive']
        delta={k:result[k]-before[k] for k in ('nominal_late_frames','audio_underruns','runtime_sectors',
            'publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
        volumes.append(dict(part=part,streaming=result,delta=delta))
    for variant in ('baseline','streaming'):
        for key,value in cpu['totals'][variant].items():
            if value!=sum(v[variant+'_summary'][key] for v in cpu['volumes']):raise ValueError('whole CPU total differs')
    keys=('frames','nominal_late_frames','audio_underruns','ay_ticks','runtime_sectors','publication_span_tstates',
        'bad_actual_intervals','used_sectors','video_bytes')
    totals={k:sum(v['streaming'][k] for v in volumes) for k in keys}
    if totals['frames']!=4221 or totals['ay_ticks']!=25326:raise ValueError('incomplete movie')
    totals.update(nominal_schedule_met=all(v['streaming']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['streaming']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['streaming']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True,release=False,scope=__doc__,baseline_commit='a84451d',totals=totals,volumes=volumes,
        cpu_totals=cpu['totals'],decision='Reject as the default: full-input keepalive has fewer late frames and bad intervals.',
        references={p.name:sha(p.read_bytes()) for p in
            (*[ROOT/n for n in REPORTS],previous_path,baseline_path,frame_path,manifest_path)},
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('summarize_inplace_streaming.py','profile_fap3.py','profile_integrated_timing.py','audit_irq_fields.py',
             'summarize_fast_return_irq.py','summarize_uncontended_frame.py')},
        all_video_and_audio_bytes_unchanged=True,full_fuse_pixel_comparison=False,
        full_integrated_cpu_total_measured=False,physical_drive_verified=False,
        initial_disk_and_irq_phases_not_matched=True)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive-directory',type=Path)
    p.add_argument('--trace-directory',type=Path);p.add_argument('--write',action='store_true');a=p.parse_args()
    if bool(a.archive_directory)!=bool(a.trace_directory):raise ValueError('both archive inputs are required')
    if a.archive_directory:archive(a.archive_directory,a.trace_directory)
    result=json.loads(json.dumps(summarize()))
    if a.write:OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()):raise ValueError('saved summary differs')
    print(json.dumps(result['totals']),flush=True)


if __name__=='__main__':main()
