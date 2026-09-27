"""Archive and audit the complete lossless positional-run experiment.

Every compact/native frame is checked in the CPU harness. Fuse covers all
actual publications, AY records and sectors, with 80 pixel samples/frame.
CPU counts remain separate from ROM/IRQ/ULA and physical-time emulation.
"""
import argparse
import gzip
import json
from pathlib import Path
import struct
from fractions import Fraction
from audit_irq_fields import audit
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze,stats
from summarize_fast_return_irq import rom_invariants
from summarize_uncontended_frame import metrics
from tagged_noop_player import transcode_video
from verify_streaming_zx0_input import validate_histogram
from zx0_codec import decompress

ROOT=Path(__file__).parent
FOLDER=ROOT/'tagged_noop_evidence'
OUTPUT=ROOT/'tagged_noop_summary.json'
REPORTS=('tagged_noop_build.json','tagged_noop_cpu.json','tagged_noop_delivery_cpu.json','tagged_noop_size.json')


def archive(directory,traces):
    reports={n:json.loads((ROOT/n).read_bytes()) for n in REPORTS}
    if not all(r['complete'] for r in reports.values()): raise ValueError('incomplete reports')
    sources=sorted({n for r in reports.values() for n in r['source_sha256_lf']}|
                   {'summarize_tagged_noop_runs.py','test_tagged_noop_runs.py'})
    files={n:(ROOT/n).read_bytes() for n in REPORTS}
    files.update({'source-'+n:(ROOT/n).read_bytes() for n in sources})
    for part in (1,2,3):
        stem=f'part{part:02}'
        files[stem+'.metadata.json']=(directory/f'ZX-video-huffman-preview_part{part:02}.json').read_bytes()
        files[stem+'.stream']=disk_blocks(directory,part)[1]
        for suffix in ('.json','.trace.txt','.debugger.txt'):
            files[stem+suffix]=(traces/(stem+suffix)).read_bytes()
    FOLDER.mkdir(exist_ok=True); entries=[]
    for name,data in sorted(files.items()):
        packed=gzip.compress(data,mtime=0); filename=name+'.gz'; (FOLDER/filename).write_bytes(packed)
        entries.append(dict(file=filename,sha256=sha(packed),decoded_sha256=sha(data),
                            decoded_bytes=len(data),bytes=len(packed)))
    (FOLDER/'manifest.json').write_text(json.dumps(dict(complete=True,release=False,files=entries),indent=2)+'\n',encoding='utf-8',newline='\n')


def summarize():
    manifest_path=FOLDER/'manifest.json'; manifest=json.loads(manifest_path.read_bytes()); blobs={}
    if not manifest['complete']: raise ValueError('incomplete archive')
    for item in manifest['files']:
        packed=(FOLDER/item['file']).read_bytes(); data=gzip.decompress(packed)
        if (sha(packed)!=item['sha256'] or sha(data)!=item['decoded_sha256'] or
                len(data)!=item['decoded_bytes'] or len(packed)!=item['bytes']): raise ValueError('archive changed')
        blobs[item['file'][:-3]]=data
    build,frame,delivery,size=[json.loads((ROOT/n).read_bytes()) for n in REPORTS]
    baseline_build_path=ROOT/'inplace_keepalive_build.json'; baseline_build=json.loads(baseline_build_path.read_bytes())
    baseline_path=ROOT/'inplace_keepalive_summary.json'; baseline=json.loads(baseline_path.read_bytes())
    baseline_folder=ROOT/'inplace_keepalive_evidence'
    baseline_manifest_path=baseline_folder/'manifest.json'
    baseline_manifest=json.loads(baseline_manifest_path.read_bytes())
    if sha(baseline_manifest_path.read_bytes())!=baseline['references']['manifest.json']:
        raise ValueError('baseline evidence manifest differs')
    def baseline_blob(name):
        record=next(x for x in baseline_manifest['files'] if x['file']==name+'.gz')
        packed=(baseline_folder/(name+'.gz')).read_bytes(); data=gzip.decompress(packed)
        if sha(packed)!=record['sha256'] or sha(data)!=record['decoded_sha256']:
            raise ValueError('baseline trace changed')
        return data
    reference_path=ROOT/'cached_huffman_lookahead_cpu.json'; reference=json.loads(reference_path.read_bytes())
    delivery_reference_path=ROOT/'inplace_streaming_cpu.json'
    if (not all(r['complete'] for r in (build,frame,delivery,size,baseline,baseline_build,reference)) or
            frame['checked_frames']!=4221 or not frame['full_compact_and_both_native_exact'] or
            frame['reference_sha256']!=sha(reference_path.read_bytes()) or
            size['baseline_build_sha256']!=sha(baseline_build_path.read_bytes()) or
            build['baseline_build_sha256']!=sha(baseline_build_path.read_bytes()) or
            build['size_report_sha256']!=sha((ROOT/REPORTS[3]).read_bytes()) or
            delivery['build_sha256']!=sha((ROOT/REPORTS[0]).read_bytes()) or
            delivery['reference_sha256']!=sha(delivery_reference_path.read_bytes()) or
            not frame['minimum_run']==size['minimum_run']==build['contract']['minimum_run']==4):
        raise ValueError('incomplete or mismatched references')
    for name,report in zip(REPORTS,(build,frame,delivery,size),strict=True):
        if blobs[name]!=(ROOT/name).read_bytes(): raise ValueError('archived report differs')
        for source,digest in report['source_sha256_lf'].items():
            if (sha((ROOT/source).read_bytes().replace(b'\r\n',b'\n'))!=digest or
                    sha(blobs['source-'+source].replace(b'\r\n',b'\n'))!=digest): raise ValueError(('source changed',source))
    swaps=build['mocked_rom_swaps']
    if ([(v['from_part'],v['to_part']) for v in swaps]!=[(1,2),(2,3)] or
            not all(v[k] for v in swaps for k in ('prompt_exact','wrong_disk_rejected','wrong_series_rejected',
                        'correct_disk_accepted','bootstrap_ram_exact','rom_mocked'))): raise ValueError('handoff checks incomplete')
    volumes=[]
    for part in (1,2,3):
        stem=f'part{part:02}'; m=json.loads(blobs[stem+'.metadata.json']); r=json.loads(blobs[stem+'.json'])
        built=build['volumes'][part-1]; old=baseline_build['volumes'][part-1]
        native=frame['volumes'][part-1]; transport=delivery['volumes'][part-1]; predicted=size['volumes'][part-1]
        if (not r['complete'] or r['failure'] or r['errors'] or r['debugger_installed_bytes'] or r['fast_read_retries'] or
                not r['trace_nonce_exact'] or not r['ay_records_exact'] or not r['progress_100_percent'] or
                r['frames']!=m['frames'] or r['native_frames_sampled']!=m['frames'] or r['pixel_samples_per_frame']!=80 or
                r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors'] or
                r['trd_sha256']!=m['trd_sha256'] or m['trd_sha256']!=built['trd_sha256'] or
                sha(blobs[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256'] or
                sha(blobs[stem+'.metadata.json'])!=built['metadata_sha256'] or
                m['used_sectors']>2544 or Fraction(str(m['fps']))!=Fraction(25,3) or m['ay_hz']!=50 or
                native['checked_frames']!=m['frames'] or native['raw_sha256']!=m['raw_sha256'] or
                m['tagged_noop_runs']!=built['tagged_noop_runs'] or
                not all(built[k] for k in ('independently_bootable','dirty_ram_boot_exact','first_native_screen_exact',
                    'second_compact_frame_exact','audio_bank_immutable_exact','exact_original_video_inverse','exact_ay_bytes'))):
            raise ValueError(('incomplete playback/build/frame proof',part))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            if sha(blobs[stem+suffix])!=r[key]: raise ValueError('trace changed')
        stream=blobs[stem+'.stream']; video=bytearray(); at=0; block_count=0
        if sha(stream)!=built['stream_sha256'] or sha(stream)!=predicted['compressed_stream_sha256']:
            raise ValueError('runtime stream differs')
        while at<len(stream):
            n,length=struct.unpack_from('<HH',stream,at); at+=4
            payload=stream[at:at+length]; at+=length; raw=decompress(payload,limit=n); video+=raw
            block=transport['blocks'][block_count]; block_count+=1
            if (sha(payload)!=block['payload_sha256'] or sha(raw)!=block['raw_sha256'] or not block['exact'] or
                    block['producer_tstates']!=block['begin_tstates']+sum(block['step_tstates']) or
                    block['decoder_tstates']!=sum(block['slice_tstates'])): raise ValueError('block CPU/input mismatch')
        if (at!=len(stream) or block_count!=len(transport['blocks']) or sha(video)!=built['raw_video_sha256'] or
                sha(transcode_video(bytes(video),inverse=True))!=old['raw_video_sha256'] or
                built['audio_sha256']!=old['audio_sha256']): raise ValueError('video/audio identity differs')
        for actual,estimate in zip(native['frames'],predicted['frame_cycle_predictions'],strict=True):
            if any(actual[k]!=value for k,value in estimate.items()): raise ValueError('frame prediction differs')
            if actual['tstates']-actual['baseline_tstates']!=actual['delta_tstates']: raise ValueError('frame arithmetic differs')
        for key in ('tstates','baseline_tstates','delta_tstates','runs','skipped_tiles','fast_fragments'):
            if sum(f[key] for f in native['frames'])!=native[key]: raise ValueError('frame totals differ')
        cpu=transport['summary']
        if not cpu['complete'] or not cpu['sectors_exact_once'] or not cpu['decoder_instruction_table_checked']:
            raise ValueError('incomplete transport CPU')
        for key in ('producer_tstates','decoder_tstates','carry_copy_bytes'):
            if sum(b[key] for b in transport['blocks'])!=cpu[key]: raise ValueError('transport total differs')
        if (sum(b['sectors'] for b in transport['blocks'])!=cpu['sector_reads'] or cpu['sector_reads']!=m['video_sectors'] or
                cpu['total_tstates']!=cpu['producer_tstates']+cpu['decoder_tstates'] or
                sum(x['tstates']*x['count'] for x in cpu['instruction_histogram'])!=cpu['producer_tstates'] or
                sum(validate_histogram(bytes.fromhex(x['opcode_hex']),x['pc'],[x]) for x in cpu['decoder_instruction_histogram'])!=cpu['decoder_tstates']):
            raise ValueError('transport instruction counts differ')
        irq=audit(r,m); irq.pop('actual_phase_tstates')
        gates=summarize_fuse(r); gates.pop('publication_intervals_tstates')
        profile=analyze(r,m,native); worst=sorted(profile.pop('frames'),key=lambda f:f['work_elapsed'],reverse=True)[:8]
        result=dict(metrics(r),timing_gates=gates,irq=irq,rom=rom_invariants(r,True),
            used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'],read_service=stats([v['tstates'] for v in r['reads']]),
            delivery_profile=profile,worst_work_frames=worst)
        previous=baseline['volumes'][part-1]['keepalive']
        previous_trace=json.loads(baseline_blob(stem+'.json'))
        previous_meta=json.loads(baseline_blob(stem+'.metadata.json'))
        old_work=analyze(previous_trace,previous_meta,reference['volumes'][part-1])['frames']
        groups={}
        for name,over in (('baseline_work_above_six_fields',True),('baseline_work_within_six_fields',False)):
            selected=[new for new,old_frame in zip(native['frames'],old_work,strict=True)
                      if (old_frame['work_elapsed']>425448)==over]
            groups[name]=dict(frames=len(selected),frame_cpu_delta_tstates=sum(f['delta_tstates'] for f in selected),
                tagged_runs=sum(f['runs'] for f in selected),slower_frames=sum(f['delta_tstates']>0 for f in selected))
        delta={k:result[k]-previous[k] for k in ('nominal_late_frames','audio_underruns','runtime_sectors',
            'publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
        volumes.append(dict(part=part,tagged=result,delta=delta,baseline_work_groups=groups))
    totals={k:sum(v['tagged'][k] for v in volumes) for k in ('frames','nominal_late_frames','audio_underruns',
        'ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
    if totals['frames']!=4221 or totals['ay_ticks']!=25326: raise ValueError('incomplete movie')
    for key in ('tstates','baseline_tstates','delta_tstates','runs','skipped_tiles','fast_fragments'):
        if sum(v[key] for v in frame['volumes'])!=frame[key]: raise ValueError('whole-frame sums differ')
    for key in delivery['tagged']:
        if sum(v['summary'][key] for v in delivery['volumes'])!=delivery['tagged'][key]: raise ValueError('whole transport sums differ')
        if delivery['tagged'][key]-delivery['baseline'][key]!=delivery['delta'][key]: raise ValueError('transport delta differs')
    totals.update(nominal_schedule_met=all(v['tagged']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['tagged']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['tagged']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True,release=False,scope=__doc__,baseline_commit='a84451d',totals=totals,volumes=volumes,
        frame_cpu_delta_tstates=frame['delta_tstates'],transport_cpu_delta_tstates=delivery['delta']['total_tstates'],
        measured_component_cpu_delta_tstates=frame['delta_tstates']+delivery['delta']['total_tstates'],
        decision='Do not adopt: negligible nominal-deadline improvement, more bad intervals and 172 extra video sectors; retain the roomier baseline.',
        references={p.name:sha(p.read_bytes()) for p in (*[ROOT/n for n in REPORTS],baseline_build_path,
            baseline_path,reference_path,delivery_reference_path,manifest_path)},
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('summarize_tagged_noop_runs.py','profile_fap3.py','profile_integrated_timing.py','audit_irq_fields.py',
             'summarize_fast_return_irq.py','summarize_uncontended_frame.py')},
        exact_original_video_and_audio=True,full_native_cpu_pixel_comparison=True,full_fuse_pixel_comparison=False,
        full_integrated_cpu_total_measured=False,physical_drive_verified=False,initial_disk_and_irq_phases_not_matched=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive-directory',type=Path); p.add_argument('--trace-directory',type=Path)
    p.add_argument('--write',action='store_true'); a=p.parse_args()
    if bool(a.archive_directory)!=bool(a.trace_directory): raise ValueError('both archive inputs required')
    if a.archive_directory: archive(a.archive_directory,a.trace_directory)
    result=json.loads(json.dumps(summarize()))
    if a.write: OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps(dict(result['totals'],measured_component_cpu_delta_tstates=result['measured_component_cpu_delta_tstates'])),flush=True)


if __name__=='__main__': main()
