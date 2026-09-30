"""Archive a rejected row-motion comparison; do not infer a playback rate."""
import argparse
import gzip
import json
from pathlib import Path
from build_fap3_trd import sha
from build_five_level_test_trd import save

ROOT = Path(__file__).resolve().parent


def load(path): return json.loads(path.read_bytes())
def archived(path): return json.loads(gzip.decompress(path.read_bytes()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--work', type=Path, required=True)
    p.add_argument('--evidence', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    probe, frame, transport = [load(a.work/(n+'.json')) for n in ('probe', 'frame', 'transport')]
    old = load(ROOT/'borrowed_literals_profile.json')
    before_frame = archived(ROOT/'lzsa2_stage_evidence/frame.json.gz')
    before_transport = archived(ROOT/'lzsa2_stage_evidence/transport.json.gz')
    for row in (probe, frame, transport, before_frame, before_transport):
        if not row['complete']: raise ValueError('incomplete evidence')
    assert frame['full_compact_and_both_native_exact'] and transport['all_instruction_timings_verified']
    assert before_transport['all_instruction_timings_verified']
    assert probe['default_encoder_exact'] and probe['exact_ay']
    assert old['raw_sha256'] == probe['baseline_raw_sha256'] == before_frame['raw_sha256']
    assert frame['states_sha256'] == probe['states_sha256'] == before_frame['states_sha256']
    assert probe['raw_sha256'] == frame['raw_sha256'] == sha((a.work/'input.fap3').read_bytes())
    assert probe['decoded_sha256'] == transport['raw_sha256'] == sha((a.work/'video.raw').read_bytes())
    assert probe['stream_sha256'] == transport['stream_sha256'] == sha((a.work/'video.stream').read_bytes())
    assert before_transport['stream_sha256'] == old['stream_sha256']
    assert before_transport['native'] == transport['native'], 'LZSA2 implementation differs'
    assert sum(frame['stages'].values()) == frame['tstates']
    assert len(frame['frames']) == probe['frame_count'] == 192
    unchanged_trd = ROOT.parent/'ZX-video-five-level-lzsa2-test.trd'
    assert sha(unchanged_trd.read_bytes()) == old['trd_sha256']
    rows = []
    for lo, hi in ((0,64), (64,128), (128,192)):
        rows.append(dict(start=lo, end_exclusive=hi,
            baseline_frame_tstates=sum(r['tstates'] for r in before_frame['frames'][lo:hi]),
            candidate_frame_tstates=sum(r['tstates'] for r in frame['frames'][lo:hi]),
            motion=sum(r['motion'] for r in probe['commands']['packets'][lo:hi])))
    baseline_pool = (old['frame_cpu']['frame_tstates'] + old['copy_cpu']['tstates']
                     + before_transport['total_tstates'])
    candidate_pool = frame['tstates'] + transport['total_tstates'] + probe['decoded_bytes']*16
    paths = ['input.fap3','video.raw','video.stream','probe.json','frame.json','transport.json']
    a.evidence.mkdir(parents=True, exist_ok=True); evidence = []
    for name in paths:
        raw = (a.work/name).read_bytes(); blob = gzip.compress(raw, mtime=0)
        (a.evidence/(name+'.gz')).write_bytes(blob)
        evidence.append(dict(file=name+'.gz', sha256=sha(blob), raw_sha256=sha(raw)))
    result = dict(complete=True, release=False, baseline_commit='d0e4731', scope=__doc__,
        frames=probe['frame_count'], states_sha256=frame['states_sha256'],
        candidate_raw_sha256=frame['raw_sha256'], candidate_stream_sha256=transport['stream_sha256'],
        baseline_trd_sha256=old['trd_sha256'], root_trd_unchanged=True,
        video_bytes=dict(baseline=old['unchanged_video_bytes'], candidate=probe['video_bytes']),
        sectors=dict(baseline=old['unchanged_video_sectors'], candidate=probe['video_sectors']),
        decoded_bytes=dict(baseline=before_transport['decoded_bytes'], candidate=probe['decoded_bytes']),
        original_frame_tstates=before_frame['tstates'], candidate_frame_tstates=frame['tstates'],
        frame_delta_tstates=frame['tstates']-before_frame['tstates'],
        original_transport_tstates=before_transport['total_tstates'], candidate_transport_tstates=transport['total_tstates'],
        transport_delta_tstates=transport['total_tstates']-before_transport['total_tstates'],
        original_decoder_tstates=before_transport['decoder_tstates'], candidate_decoder_tstates=transport['decoder_tstates'],
        candidate_motion_tstates=frame['stages']['reconstruct/motion'],
        candidate_cache_tstates=frame['stages']['reconstruct/cache'],
        candidate_huffman_tstates=sum(v for k,v in frame['stages'].items() if 'huffman' in k),
        motion_commands=probe['commands']['motion'], cache_frames=probe['commands']['cache_frames'],
        latest_baseline_component_pool_tstates=baseline_pool,
        candidate_component_pool_with_copy_lower_bound_tstates=candidate_pool,
        estimated_component_delta_tstates=candidate_pool-baseline_pool, windows=rows,
        native_implementation_changed=False, per_instruction_timing_delta=0,
        exact_all_compact_and_both_native_frames=True, exact_ay=True,
        actual_candidate_playback_measured=False, candidate_fps=None,
        decision='Reject this existing-cache motion selection for realtime adoption. Keep experimental opt-in and exact evidence; root TRD unchanged.',
        assumptions='Frame model excludes IRQ/ULA/ROM/disk. Transport uses fixed 256-byte demands and mocked ROM. Candidate packet copy is a 16-T-per-byte lower bound; latest baseline has measured borrowed bridges. Component pools are not elapsed playback or a cadence proof.',
        next='Optimize native output on the retained borrowed-literal image. Revisit motion only with explicit cache/patch costs and fewer correction bytes.',
        evidence=evidence,
        source_sha256_lf={n:sha((ROOT/n).read_bytes().replace(b'\r\n',b'\n')) for n in (
            'encode_fap3.py','row_aligned_motion.py','probe_row_aligned_motion.py','test_row_aligned_motion.py',
            'summarize_row_aligned_motion.py','profile_row_cpu.py','benchmark_row_lzsa.py','causal_tile_z80.py',
            'resumable_lzsa2.py','lzsa2_row_player.py')})
    save(a.output, result)
    print(json.dumps({k:result[k] for k in ('frame_delta_tstates','transport_delta_tstates',
        'estimated_component_delta_tstates','motion_commands','cache_frames','root_trd_unchanged')}))


if __name__ == '__main__': main()
