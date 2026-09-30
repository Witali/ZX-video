"""Archive the compiled-row feasibility result with explicit model limits."""
import argparse,gzip,json
from pathlib import Path
import numpy as np
from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('work','evidence','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    probe=json.loads((a.work/'probe.json').read_bytes());cpu=json.loads((a.work/'transport.json').read_bytes())
    old=json.loads((ROOT/'borrowed_literals_profile.json').read_bytes())
    before=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/transport.json.gz').read_bytes()))
    frame=json.loads(gzip.decompress((ROOT/'lzsa2_stage_evidence/frame.json.gz').read_bytes()))
    assert probe['complete'] and cpu['complete'] and probe['packet_workspace_fits']
    assert probe['all_bitmaps_exact'] and probe['native_instruction_timings_exact']
    assert cpu['all_instruction_timings_verified'] and cpu['native']==before['native']
    assert probe['states_sha256']==frame['states_sha256']
    assert probe['baseline_video_sha256']==old['video_sha256']
    assert probe['raw_sha256']==cpu['raw_sha256']==sha((a.work/'video.raw').read_bytes())
    assert probe['stream_sha256']==cpu['stream_sha256']==sha((a.work/'video.stream').read_bytes())
    assert sha((ROOT.parent/'ZX-video-five-level-lzsa2-test.trd').read_bytes())==old['trd_sha256']
    stages=frame['stages'];old_output=sum(v for k,v in stages.items() if k.startswith('output/'))
    with np.load(ROOT/'five_level_test_evidence/states.npz',allow_pickle=False) as saved:states=saved['states']
    assert sha(states.tobytes())==probe['states_sha256']
    previous=np.zeros_like(states[:,:3072]);previous[2:]=states[:-2,:3072]
    required=int(np.count_nonzero(states[:,:3072]!=previous))
    assert stages['output/dense_pixels']%51==0 and stages['output/cell_pixels']%43==0
    written=stages['output/dense_pixels']//51+stages['output/cell_pixels']//43
    shared=sum(stages['output/'+n] for n in ('attributes','paging','control'))
    optimistic_output=probe['bitmap_cpu_tstates']+shared
    output_delta=optimistic_output-old_output
    transport_delta=cpu['total_tstates']-before['total_tstates']
    result=dict(complete=True,release=False,baseline_commit='42bcc0f',
        baseline_trd_sha256=old['trd_sha256'],root_trd_unchanged=True,
        states_sha256=probe['states_sha256'],frames=len(probe['rows']),
        required_changed_row_symbols=required,baseline_written_row_symbols=written,
        candidate_written_row_symbols=sum(r.get(k,0) for r in probe['rows'] for k in ('copy_symbols','pattern_symbols','solid_symbols')),
        video_bytes=dict(baseline=old['unchanged_video_bytes'],candidate=probe['video_bytes']),
        sectors=dict(baseline=old['unchanged_video_sectors'],candidate=probe['video_sectors']),
        decoded_bytes=dict(baseline=before['decoded_bytes'],candidate=probe['decoded_bytes']),
        command_bytes=probe['command_bytes'],stub_bytes=probe['stub_bytes'],max_packet_bytes=probe['max_packet_bytes'],
        candidate_bitmap_tstates=probe['bitmap_cpu_tstates'],baseline_output_tstates=old_output,
        optimistic_candidate_output_tstates=optimistic_output,estimated_output_delta_tstates=output_delta,
        command_copy_ldir_tstates=probe['command_copy_ldir_tstates'],
        decoder_tstates=dict(baseline=before['decoder_tstates'],candidate=cpu['decoder_tstates']),
        producer_tstates=dict(baseline=before['producer_tstates'],candidate=cpu['producer_tstates']),
        measured_transport_delta_tstates=transport_delta,
        optimistic_component_delta_tstates=output_delta+probe['command_copy_ldir_tstates']+transport_delta,
        all_192_bitmaps_and_both_screen_histories_exact=True,attributes_and_reconstruction_packet_bytes_unchanged=True,
        targeted_native_cases=1152,actual_candidate_playback_measured=False,candidate_fps=None,
        decision='Reject this compiled COPY/FILL row program format for integration: command volume and its transport/copy CPU exceed the renderer saving.',
        limitations='Prototype only: no boot, full frame pipeline, real queues, AY interrupts, ULA or physical disk run. Output estimate keeps baseline attribute/paging/control work, drops all old bitmap dispatch, adds measured compiled bitmap CPU and LDIR command copies. It omits new copy/dispatch helper overhead and changed queue-copy costs. CPU pools are not elapsed playback.',
        next='Measure native LZ4-HC decode costs on saved blocks as a possible selective fast block mode; its known size increase must be charged to total delivery and the disk budget before adoption.')
    a.evidence.mkdir(parents=True,exist_ok=True);result['evidence']=[]
    for n in ('probe.json','transport.json','video.raw','video.stream'):
        raw=(a.work/n).read_bytes();blob=gzip.compress(raw,mtime=0);(a.evidence/(n+'.gz')).write_bytes(blob)
        result['evidence'].append(dict(file=n+'.gz',sha256=sha(blob),raw_sha256=sha(raw)))
    result['source_sha256_lf']={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
        'probe_compiled_row_output.py','test_compiled_row_output.py','summarize_compiled_row_output.py',
        'benchmark_row_lzsa.py','resumable_lzsa2.py')}
    save(a.output,result)
    print(json.dumps({k:result[k] for k in ('estimated_output_delta_tstates','measured_transport_delta_tstates',
        'command_copy_ldir_tstates','optimistic_component_delta_tstates','root_trd_unchanged')}))


if __name__=='__main__':main()
