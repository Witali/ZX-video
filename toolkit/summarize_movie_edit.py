"""Bind edit, causal decoding, actual ZX0 storage and partial Z80 evidence."""
import argparse
import json
from pathlib import Path

from probe_lossless_layouts import sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    names = ('no_credits_timeline', 'no_credits_fragments', 'no_credits_zx0',
             'no_credits_join_cpu', 'cache_aware_fragments_summary')
    reports = [json.loads((args.directory/(n+'.json')).read_text(encoding='utf-8')) for n in names]
    timeline, fragments, storage, cpu, baseline = reports
    if (not all(r['complete'] for r in reports)
            or timeline['source_states_sha256'] != baseline['states_sha256']
            or timeline['states_sha256'] != fragments['states_sha256']
            or cpu['states_sha256'] != timeline['states_sha256']
            or not storage['input_sha256'] == fragments['sha256'] == cpu['input_sha256']
            or not timeline['frames_after'] == fragments['frames'] == cpu['frames_total']
            or sum(b['decoded_bytes'] for b in storage['blocks']) != fragments['raw_bytes']
            or len(storage['blocks']) != storage['blocks_expected']
            or sum(b['zx0_bytes']+4 for b in storage['blocks']) != storage['zx0_with_headers_bytes']):
        raise ValueError('reports differ or are incomplete')
    video = storage['zx0_with_headers_bytes']
    total = video+timeline['ay_pair_bytes']
    report = dict(scope=__doc__, complete=True, baseline_commit='f4a3d85',
        frames=timeline['frames_after'], duration_seconds=timeline['duration_seconds'],
        removed_frames=timeline['removed_frames'], removed_seconds=timeline['removed_seconds'],
        states_sha256=timeline['states_sha256'], ay_sha256=timeline['ay_sha256'],
        video_zx0_bytes=video, video_delta_bytes=video-baseline['video_bytes'],
        video_reduction_percent=100*(baseline['video_bytes']-video)/baseline['video_bytes'],
        ay_uncompressed_register_pairs_bytes=timeline['ay_pair_bytes'],
        video_plus_ay_bytes=total, preliminary_two_trd_margin_bytes=2*645888-total,
        preliminary_three_trd_margin_bytes=3*645888-total,
        budget_note='Unsplit streams; excludes new player size, volume resets, sector rounding and interleave holes. AY pairs are uncompressed, not the former 77696-byte estimate.',
        full_pc_frame_decode_verified=True, full_ay_register_replay_verified=True,
        cpu_frames_verified=cpu['frames_verified'], full_movie_cpu_verified=False,
        join_two_stages_tstates=[dict(frame=j, tstates=next(r['two_stages_tstates'] for r in cpu['rows'] if r['index'] == j)) for j in cpu['joins']],
        sampled_two_stages_max_tstates=cpu['two_stages_max_tstates'],
        full_frame_delivery_measured=False, player_changed=False, release_disks_changed=False,
        evidence_sha256={n: sha((args.directory/(n+'.json')).read_bytes()) for n in names})
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
