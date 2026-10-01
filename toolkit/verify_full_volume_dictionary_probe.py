"""Archive the full-volume dictionary rejection and complete baseline profiling.

This is an experiment checkpoint, not release acceptance. No candidate TRD
is built when an original per-block byte or CPU budget is exceeded.
"""
import argparse
import gzip
import json
from pathlib import Path

from build_fap3_trd import sha
from convert_video import write_json


def read(path):
    return json.loads(path.read_bytes())


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('root','output','evidence'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();tmp=a.root/'.tmp';a.evidence.mkdir(parents=True,exist_ok=True)
    folder=tmp/'sector-cache-part04-capacity';work=folder/'work/part04'
    m=read(folder/'part04.json');cpu=read(work/'cpu.json');timing=read(work/'timing.json')
    numbering=read(tmp/'dictionary-part04/report.json');candidate=numbering['variants']['budgeted']
    assert numbering['complete'] and not candidate['host_candidate_eligible']
    assert sha((folder/'part04.json').read_bytes())==numbering['metadata_sha256']==cpu['metadata_sha256']
    assert cpu['complete'] and cpu['all_native_screens_exact'] and cpu['frames_checked']==m['frames']==1322
    assert cpu['sector_cache_fifo_bounds_guarded'] and cpu['retired_runtime_reads_writes_or_fetches']==0
    assert timing['complete'] and not timing['errors'] and not timing['failure']
    assert timing['trace_nonce_exact'] and timing['ay_records_exact'] and timing['runtime_sectors_checked']==m['video_sectors']
    assert not timing['audio_underruns'] and not timing['ay_record_field_gaps'] and not timing['ay_record_field_duplicates']
    assert timing['trd_sha256']==cpu['trd_sha256']==m['trd_sha256']==sha((folder/'part04.trd').read_bytes())
    assert sha((work/'timing.trace.txt').read_bytes())==timing['trace_sha256']
    bad=[]
    for i,(block,change) in enumerate(zip(candidate['blocks'],candidate['changes'])):
        if not change['budget_met']:
            bad.append(dict(block=i,bytes=block['compressed_bytes'],byte_budget=change['byte_budget'],
                byte_excess=block['compressed_bytes']-change['byte_budget'],
                decoder_tstates=block['native']['tstates'],cpu_budget=change['cpu_budget']))
    assert [b['block'] for b in bad]==[2,5,17,18,32,33]
    assert all(b['decoder_tstates']<=b['cpu_budget'] and b['byte_excess']>0 for b in bad)
    profile=read(tmp/'sector-cache-part04-profile.json');bursts=read(tmp/'part04-delivery-windows.json')
    short=read(tmp/'dictionary-delivery-windows.json')
    assert profile['complete'] and bursts['complete'] and short['complete']
    extra=next(f for f in short['late_frames'] if f['local_frame']==123)
    assert extra['packet_disk']==extra['packet_empty_wait']==0 and extra['queue_count_at_packet']==3
    artifacts=[]
    def archive(path,name):
        raw=path.read_bytes();data=raw if path.suffix=='.trd' else gzip.compress(raw,mtime=0)
        filename=name+('' if path.suffix=='.trd' else '.gz')
        (a.evidence/filename).write_bytes(data)
        artifacts.append(dict(file=filename,raw_sha256=sha(raw),archive_sha256=sha(data),raw_bytes=len(raw),archive_bytes=len(data)))
    for name in ('part04.json','part04.trd','timing.json','partition.json','cache-checks.json'):
        archive(folder/name,'baseline-'+name)
    for name in ('cpu.json','timing.json','timing.trace.txt','timing.debugger.txt','timing.stderr.txt',
                 'codebook.raw','codebook.stream','rows.json','states.npz','audio.ayh1'):
        archive(work/name,'baseline-work-'+name)
    for path in sorted((tmp/'dictionary-part04').rglob('*')):
        if path.is_file() and 'lzsa' not in path.relative_to(tmp/'dictionary-part04').parts:
            archive(path,'dictionary-'+path.relative_to(tmp/'dictionary-part04').as_posix().replace('/','-'))
    for name in ('dictionary-part04.log','dictionary-part04-budgeted.log','sector-cache-part04-profile.json',
                 'part04-delivery-windows.json','dictionary-delivery-windows.json','baseline-delivery-windows.json'):
        archive(tmp/name,name)
    result=dict(complete=True,release=False,date='2026-10-01',baseline_commit='3237312',scope=__doc__,
        frames=m['frames'],frame_start=m['frame_start'],frame_end_exclusive=m['frame_end_exclusive'],
        baseline_trd_sha256=m['trd_sha256'],baseline_used_sectors=m['used_sectors'],
        baseline_video_bytes=m['video_bytes'],candidate_video_bytes=candidate['bytes'],
        baseline_video_sectors=m['video_sectors'],candidate_video_sectors=candidate['sectors'],
        baseline_decoder_tstates=numbering['baseline_decoder_tstates'],candidate_decoder_tstates=candidate['decoder_tstates'],
        failing_blocks=bad,candidate_built=False,candidate_selected=False,
        native_screens_exact=cpu['frames_checked'],fuse_timing_frames=len(timing['publications']),
        fuse_runtime_sectors=timing['runtime_sectors_checked'],fuse_ay_ticks=m['ay_ticks'],
        fuse_full_screen_capture=False,
        timing={k:timing[k] for k in ('nominal_late_frames','actual_out_over_one_field','max_late_fields','bad_actual_intervals','late_runs')},
        profile={k:profile[k] for k in ('active_elapsed','active_disk_service','active_decode_elapsed','stages','queue_at_packet')},
        isolated_window_miss=extra,
        decision='Reject full-volume renumbering: six blocks exceed their original byte budgets. Do not relax the guards or build a candidate disk. '
            'The complete existing four-slot/cache baseline preserves all native screens and real AY/sectors but fails timing. '
            'Isolated misses occur with ready data while background physical reads delay the next draw; prolonged late runs exhaust the queue. '
            'Next isolate optional read admission near publication on the saved 256-frame window, retaining original compressed bytes, then address sustained burst supply.',
        artifacts=artifacts,source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n')) for name in
            ('probe_dictionary_numbering.py','fit_lzsa2_cpu_budget.py','verify_cached_cell_player.py',
             'profile_cell_delivery.py','analyze_cb46_delivery_windows.py','verify_full_volume_dictionary_probe.py')})
    write_json(a.output,result)
    print(json.dumps(dict(complete=True,artifacts=len(artifacts),failing_blocks=bad,release=False)))


if __name__=='__main__':main()
