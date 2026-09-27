"""Preserve and audit complete cost-selected playback against the retained player.

Archived source packets permit independent scalar video/AY replay. Native
CPU checks every compact/native byte, and Fuse checks all publications,
AY records, disk sectors and 80 pixels/frame. Physical hardware is untested.
"""
import argparse
import gzip
import json
from fractions import Fraction
from pathlib import Path
import struct
from audit_irq_fields import audit
from benchmark_bank_local_zx0 import disk_blocks
from build_fap3_trd import sha
from bulk_frame_stream import read_packet,unpack as unpack_bulk
from cell_audio_stream import unpack as unpack_audio
from frame_packet_stream import unpack
from probe_motion_entropy import Reader
from probe_sparse_motion_cache import unpack as unpack_cache
from probe_spatial_contexts import read_header
from profile_fap3 import summarize_fuse
from profile_integrated_timing import analyze,stats
from raw_attribute_stream import decode
from summarize_fast_return_irq import rom_invariants
from summarize_uncontended_frame import metrics
from verify_streaming_zx0_input import validate_histogram
from zx0_codec import decompress

ROOT=Path(__file__).parent
FOLDER=ROOT/'resident_fragments_evidence'
OUTPUT=ROOT/'resident_fragments_summary.json'
REPORTS=('resident_fragments_build.json','resident_fragments_cpu.json',
         'resident_fragments_delivery_cpu.json','resident_fragments_probe.json')
INTERRUPTED=('resident_fragments_interrupted_build.json','resident_fragments_interrupted_cpu.json')


def separated_video(raw,start,end):
    r=Reader(raw); _,_,count,_,_=read_header(r,magic=b'FAP3'); header=raw[:r.pos]; result=bytearray()
    for index in range(count):
        _,packet=read_packet(r,stored_guards=False)
        if not start<=index<end: continue
        body=packet['payload'][sum(map(len,packet['ticks'])):]
        if start and index<start+2:
            at=200+packet['mask_bytes']; body=body[:at]+b'\xff'*80+body[at+80:]
        result+=struct.pack('<H',len(body))+body
    r.end(); return header,bytes(result)


def scalar(raw):
    video,ay,_=unpack_audio(unpack_cache(unpack(unpack_bulk(raw)),32,4))
    return decode(video),ay


def archive(directory,traces,sources,baseline_sources):
    reports={n:json.loads((ROOT/n).read_bytes()) for n in REPORTS}
    if not all(r['complete'] for r in reports.values()): raise ValueError('incomplete reports')
    source_names=sorted({n for r in reports.values() for n in r['source_sha256_lf']}|
        {'summarize_resident_fragments.py','test_fragment_cost_selection.py','raw_attribute_stream.py'})
    files={n:(ROOT/n).read_bytes() for n in (*REPORTS,*INTERRUPTED)}
    files.update({'source-'+n:(ROOT/n).read_bytes() for n in source_names})
    original=json.loads((ROOT/'inplace_keepalive_build.json').read_bytes())
    for part in (1,2,3):
        stem=f'part{part:02}'; src=(sources/f'volume-{part}.raw').read_bytes()
        if sha(src)!=reports[REPORTS[3]]['volumes'][part-1]['raw_sha256']: raise ValueError('candidate changed')
        files[stem+'.source.raw']=src
        old=(baseline_sources/f'volume-{part}.raw').read_bytes()
        if sha(old)!=original['contract']['raw_sha256'][part-1]: raise ValueError('baseline changed')
        r=Reader(old); read_header(r,magic=b'FAP3'); files[stem+'.baseline_header']=old[:r.pos]
        if part==3: files['baseline.source.raw']=old
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


def read_archive(folder,*,packed_sizes=True):
    manifest=json.loads((folder/'manifest.json').read_bytes()); blobs={}
    if not manifest['complete']: raise ValueError('incomplete archive')
    for item in manifest['files']:
        packed=(folder/item['file']).read_bytes(); data=gzip.decompress(packed)
        if (sha(packed)!=item['sha256'] or sha(data)!=item['decoded_sha256'] or
                len(data)!=item['decoded_bytes']): raise ValueError('archive changed')
        # The retained archive predates the optional packed-length field;
        # its packed hash and decoded hash/length remain mandatory.
        if (packed_sizes or 'bytes' in item) and len(packed)!=item['bytes']:
            raise ValueError('packed archive length changed')
        blobs[item['file'][:-3]]=data
    return blobs


def summarize():
    blobs=read_archive(FOLDER)
    build,frame,delivery,probe=[json.loads((ROOT/n).read_bytes()) for n in REPORTS]
    baseline_build_path=ROOT/'inplace_keepalive_build.json'; old_build=json.loads(baseline_build_path.read_bytes())
    baseline_path=ROOT/'inplace_keepalive_summary.json'; baseline=json.loads(baseline_path.read_bytes())
    reference_path=ROOT/'cached_huffman_lookahead_cpu.json'; reference=json.loads(reference_path.read_bytes())
    delivery_reference_path=ROOT/'inplace_streaming_cpu.json'
    old_delivery=json.loads(delivery_reference_path.read_bytes())
    old_folder=ROOT/'inplace_keepalive_evidence'
    if sha((old_folder/'manifest.json').read_bytes())!=baseline['references']['manifest.json']:
        raise ValueError('baseline archive differs')
    old_blobs=read_archive(old_folder,packed_sizes=False)
    if (not all(r['complete'] for r in (build,frame,delivery,probe,baseline,old_build,reference,old_delivery)) or
            frame['checked_frames']!=4221 or not frame['full_compact_and_both_native_exact'] or
            frame['reference_sha256']!=sha(reference_path.read_bytes()) or
            frame['probe_sha256']!=sha((ROOT/REPORTS[3]).read_bytes()) or
            build['probe_sha256']!=sha((ROOT/REPORTS[3]).read_bytes()) or
            probe['baseline_build_sha256']!=sha(baseline_build_path.read_bytes()) or
            build['baseline_build_sha256']!=sha(baseline_build_path.read_bytes()) or
            delivery['build_sha256']!=sha((ROOT/REPORTS[0]).read_bytes()) or
            delivery['reference_sha256']!=sha(delivery_reference_path.read_bytes()) or
            delivery['baseline']!=old_delivery['totals']['baseline']):
        raise ValueError('incomplete or mismatched references')
    for name,report in zip(REPORTS,(build,frame,delivery,probe),strict=True):
        if blobs[name]!=(ROOT/name).read_bytes(): raise ValueError('archived report differs')
        for source,digest in report['source_sha256_lf'].items():
            if (sha((ROOT/source).read_bytes().replace(b'\r\n',b'\n'))!=digest or
                    sha(blobs['source-'+source].replace(b'\r\n',b'\n'))!=digest): raise ValueError(('source changed',source))
    stopped_build,stopped_cpu=[json.loads(blobs[n]) for n in INTERRUPTED]
    if (stopped_build['complete'] or stopped_cpu['complete'] or stopped_build['volumes'] or
            len(stopped_cpu['volumes'])!=1 or len(stopped_cpu['volumes'][0]['frames'])!=101 or
            stopped_cpu['volumes'][0]['frames']!=frame['volumes'][0]['frames'][:101]):
        raise ValueError('interrupted attempt no longer matches the complete replay')
    for name in INTERRUPTED:
        if blobs[name]!=(ROOT/name).read_bytes(): raise ValueError('interrupted report changed')
    swaps=build['mocked_rom_swaps']
    if ([(v['from_part'],v['to_part']) for v in swaps]!=[(1,2),(2,3)] or
            not all(v[k] for v in swaps for k in ('prompt_exact','wrong_disk_rejected','wrong_series_rejected',
                        'correct_disk_accepted','bootstrap_ram_exact','rom_mocked'))): raise ValueError('handoffs incomplete')
    if sha(blobs['baseline.source.raw'])!=old_build['contract']['raw_sha256'][2]: raise ValueError('wrong baseline movie')
    states,original_ay=scalar(blobs['baseline.source.raw'])
    if sha(states)!=old_build['contract']['states_sha256']: raise ValueError('baseline pixels differ')
    volumes=[]
    for part in (1,2,3):
        stem=f'part{part:02}'; m=json.loads(blobs[stem+'.metadata.json']); r=json.loads(blobs[stem+'.json'])
        built=build['volumes'][part-1]; old=old_build['volumes'][part-1]
        native=frame['volumes'][part-1]; transport=delivery['volumes'][part-1]; selected=probe['volumes'][part-1]
        old_transport=old_delivery['volumes'][part-1]
        if (not r['complete'] or r['failure'] or r['errors'] or r['debugger_installed_bytes'] or r['fast_read_retries'] or
                not r['trace_nonce_exact'] or not r['ay_records_exact'] or not r['progress_100_percent'] or
                r['frames']!=m['frames'] or r['native_frames_sampled']!=m['frames'] or r['pixel_samples_per_frame']!=80 or
                r['ay_ticks']!=6*m['frames'] or r['runtime_sectors_checked']!=m['video_sectors'] or
                r['trd_sha256']!=m['trd_sha256'] or m['trd_sha256']!=built['trd_sha256'] or
                sha(blobs[stem+'.metadata.json'])!=r['integrated_bootstrap_metadata_sha256'] or
                sha(blobs[stem+'.metadata.json'])!=built['metadata_sha256'] or m['used_sectors']>2544 or
                Fraction(str(m['fps']))!=Fraction(25,3) or m['ay_hz']!=50 or
                native['checked_frames']!=m['frames'] or native['raw_sha256']!=m['raw_sha256'] or
                (native['start'],native['end'])!=(m['frame_start'],m['frame_end_exclusive']) or
                transport['baseline_summary']!=old_transport['baseline_summary'] or
                native['raw_sha256']!=selected['raw_sha256'] or
                not all(built[k] for k in ('independently_bootable','dirty_ram_boot_exact','first_native_screen_exact',
                    'second_compact_frame_exact','audio_bank_immutable_exact','exact_candidate_video_bytes','exact_ay_bytes'))):
            raise ValueError(('incomplete playback/build/frame proof',part))
        for suffix,key in (('.trace.txt','trace_sha256'),('.debugger.txt','debugger_script_sha256')):
            if sha(blobs[stem+suffix])!=r[key]: raise ValueError('trace changed')
        source=blobs[stem+'.source.raw']
        if sha(source)!=selected['raw_sha256'] or scalar(source)!=(states,original_ay):
            raise ValueError('source video/AY differs')
        header,expected_video=separated_video(source,native['start'],native['end'])
        if header!=blobs[stem+'.baseline_header']: raise ValueError('Huffman header differs')
        stream=blobs[stem+'.stream']; video=bytearray(); at=0; count=0
        if sha(stream)!=built['stream_sha256'] or sha(stream)!=selected['compressed_stream_sha256']:
            raise ValueError('runtime stream differs')
        while at<len(stream):
            n,length=struct.unpack_from('<HH',stream,at); at+=4
            payload=stream[at:at+length]; at+=length; raw=decompress(payload,limit=n); video+=raw
            block=transport['blocks'][count]; count+=1
            if (sha(payload)!=block['payload_sha256'] or sha(raw)!=block['raw_sha256'] or not block['exact'] or
                    block['producer_tstates']!=block['begin_tstates']+sum(block['step_tstates']) or
                    block['decoder_tstates']!=sum(block['slice_tstates'])): raise ValueError('block CPU mismatch')
        if (at!=len(stream) or count!=len(transport['blocks']) or bytes(video)!=expected_video or
                sha(video)!=built['raw_video_sha256'] or built['audio_sha256']!=old['audio_sha256']):
            raise ValueError('runtime pixels/audio differ')
        for actual,ref in zip(native['frames'],reference['volumes'][part-1]['frames'],strict=True):
            if (actual['frame']!=ref['frame'] or actual['baseline_tstates']!=ref['tstates'] or
                    actual['tstates']-actual['baseline_tstates']!=actual['delta_tstates'] or
                    sum(actual['stages'].values())!=actual['tstates']): raise ValueError('frame arithmetic differs')
        for key in ('tstates','baseline_tstates','delta_tstates'):
            if sum(f[key] for f in native['frames'])!=native[key]: raise ValueError('frame sums differ')
        cpu=transport['summary']
        if not cpu['complete'] or not cpu['sectors_exact_once'] or not cpu['decoder_instruction_table_checked']:
            raise ValueError('incomplete transport CPU')
        for key in ('producer_tstates','decoder_tstates','carry_copy_bytes'):
            if sum(b[key] for b in transport['blocks'])!=cpu[key]: raise ValueError('transport sums differ')
        if (sum(b['sectors'] for b in transport['blocks'])!=cpu['sector_reads'] or cpu['sector_reads']!=m['video_sectors'] or
                cpu['total_tstates']!=cpu['producer_tstates']+cpu['decoder_tstates'] or
                sum(x['tstates']*x['count'] for x in cpu['instruction_histogram'])!=cpu['producer_tstates'] or
                sum(validate_histogram(bytes.fromhex(x['opcode_hex']),x['pc'],[x]) for x in cpu['decoder_instruction_histogram'])!=cpu['decoder_tstates']):
            raise ValueError('instruction counts differ')
        irq=audit(r,m); irq.pop('actual_phase_tstates')
        gates=summarize_fuse(r); gates.pop('publication_intervals_tstates')
        profile=analyze(r,m,native); worst=sorted(profile.pop('frames'),key=lambda f:f['work_elapsed'],reverse=True)[:8]
        result=dict(metrics(r),timing_gates=gates,irq=irq,rom=rom_invariants(r,True),
            used_sectors=m['used_sectors'],free_sectors=m['free_sectors'],video_bytes=m['video_bytes'],
            video_start_sector=m['video_start_sector'],read_service=stats([v['tstates'] for v in r['reads']]),
            delivery_profile=profile,worst_work_frames=worst)
        previous=baseline['volumes'][part-1]['keepalive']
        old_work=analyze(json.loads(old_blobs[stem+'.json']),json.loads(old_blobs[stem+'.metadata.json']),
                         reference['volumes'][part-1])['frames']
        groups={}
        for name,over in (('baseline_work_above_six_fields',True),('baseline_work_within_six_fields',False)):
            chosen=[new for new,old_frame in zip(native['frames'],old_work,strict=True)
                    if (old_frame['work_elapsed']>425448)==over]
            groups[name]=dict(frames=len(chosen),frame_cpu_delta_tstates=sum(f['delta_tstates'] for f in chosen),
                slower_frames=sum(f['delta_tstates']>0 for f in chosen))
        delta={k:result[k]-previous[k] for k in ('nominal_late_frames','audio_underruns','runtime_sectors',
            'publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
        volumes.append(dict(part=part,candidate=result,delta=delta,baseline_work_groups=groups))
    totals={k:sum(v['candidate'][k] for v in volumes) for k in ('frames','nominal_late_frames','audio_underruns',
        'ay_ticks','runtime_sectors','publication_span_tstates','bad_actual_intervals','used_sectors','video_bytes')}
    if totals['frames']!=4221 or totals['ay_ticks']!=25326: raise ValueError('incomplete movie')
    if frame['slower_frames']!=sum(f['delta_tstates']>0 for v in frame['volumes'] for f in v['frames']):
        raise ValueError('slower-frame count differs')
    for key in ('tstates','baseline_tstates','delta_tstates'):
        if sum(v[key] for v in frame['volumes'])!=frame[key]: raise ValueError('whole frame sums differ')
    for key in delivery['candidate']:
        if sum(v['summary'][key] for v in delivery['volumes'])!=delivery['candidate'][key]: raise ValueError('whole transport sums differ')
        if delivery['candidate'][key]-delivery['baseline'][key]!=delivery['delta'][key]: raise ValueError('transport delta differs')
    totals.update(nominal_schedule_met=all(v['candidate']['timing_gates']['nominal_deadlines_met'] for v in volumes),
        fallback_met=all(v['candidate']['timing_gates']['fallback_one_field_met'] for v in volumes),
        ay_50hz_met=all(v['candidate']['timing_gates']['actual_ay_50hz'] for v in volumes))
    return dict(complete=True,release=False,scope=__doc__,baseline_commit='a84451d',totals=totals,volumes=volumes,
        frame_cpu_delta_tstates=frame['delta_tstates'],transport_cpu_delta_tstates=delivery['delta']['total_tstates'],
        measured_component_cpu_delta_tstates=frame['delta_tstates']+delivery['delta']['total_tstates'],
        references={p.name:sha(p.read_bytes()) for p in (*[ROOT/n for n in REPORTS],baseline_build_path,
            baseline_path,reference_path,delivery_reference_path,FOLDER/'manifest.json')},
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in
            ('summarize_resident_fragments.py','profile_fap3.py','profile_integrated_timing.py','audit_irq_fields.py',
             'summarize_fast_return_irq.py','summarize_uncontended_frame.py','raw_attribute_stream.py')},
        all_source_pixels_and_ay_replayed=True,full_native_cpu_pixel_comparison=True,full_fuse_pixel_comparison=False,
        interrupted_attempt_preserved=True,interrupted_frame_prefix_exactly_replayed=101,
        full_integrated_cpu_total_measured=False,physical_drive_verified=False,initial_disk_and_irq_phases_not_matched=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('archive-directory','trace-directory','source-directory','baseline-raw-directory'):
        p.add_argument('--'+key,type=Path)
    p.add_argument('--write',action='store_true'); a=p.parse_args()
    paths=(a.archive_directory,a.trace_directory,a.source_directory,a.baseline_raw_directory)
    if any(paths) and not all(paths): raise ValueError('all four archive inputs required')
    if a.archive_directory: archive(*paths)
    result=json.loads(json.dumps(summarize()))
    if a.write: OUTPUT.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    elif result!=json.loads(OUTPUT.read_bytes()): raise ValueError('saved summary differs')
    print(json.dumps(dict(result['totals'],measured_component_cpu_delta_tstates=result['measured_component_cpu_delta_tstates'])),flush=True)


if __name__=='__main__': main()
