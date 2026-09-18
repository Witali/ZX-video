"""Check complete dictionary/ZX0 evidence against the unchanged FHF1 selection."""
import argparse
import json
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reports', type=Path, default=Path(__file__).parent)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()

    def load(name):
        result = json.loads((args.reports/(name+'.json')).read_text(encoding='utf-8'))
        if not result['complete']:
            raise ValueError('incomplete '+name)
        return result

    experiment = load('fragment_dictionary_measurements')
    profile = load('fragment_word_widths_profile')
    baseline = load('fast_fragments_target_300000_zx0')
    choices = load('fast_fragments_targets')
    old = next(r for r in choices['rows'] if r['name'] == 'target_300000')
    if (old['sha256'] != baseline['input_sha256']
            or experiment['states_sha256'] != profile['states_sha256']
            or experiment['states_sha256'] != choices['states_sha256']
            or experiment['selection_sha256'] != profile['selection_sha256']):
        raise AssertionError('different baseline/selection/states')
    rows = []
    for source in experiment['rows']:
        bits = source['index_bits']
        s = load(f'fragment_dictionary_{bits}_zx0')
        estimate = next(r for r in profile['width_variants'] if r['index_bits'] == bits)
        if (s['input_sha256'] != source['sha256'] or s['input_bytes'] != source['raw_bytes']
                or s['block_bytes'] != 8192 or s['encoder_sha256'] != baseline['encoder_sha256']
                or s['encoder_mode'] != baseline['encoder_mode']
                or source['frames'] != 4971 or source['values'] != old['values']
                or source['fast_kinds']['89'] != estimate['adopted_tiles']
                or source['fast_kinds']['85']+source['fast_kinds']['89'] != old['fast_kinds']['85']
                or any(source['fast_kinds'][v] != old['fast_kinds'][v] for v in ('86', '87', '88'))
                or len(s['blocks']) != s['blocks_expected']
                or sum(b['decoded_bytes'] for b in s['blocks']) != s['input_bytes']
                or sum(b['zx0_bytes']+4 for b in s['blocks']) != s['zx0_with_headers_bytes']):
            raise AssertionError('inconsistent dictionary/storage coverage')
        video = s['zx0_with_headers_bytes']
        rows.append(dict(index_bits=bits, dictionary_bytes=source['dictionary_bytes'],
            raw_bytes=source['raw_bytes'], raw_delta_bytes=source['raw_bytes']-old['raw_bytes'],
            zx0_blocks=s['blocks_expected'], video_bytes=video,
            zx0_delta_bytes=video-baseline['zx0_with_headers_bytes'], video_plus_ay_bytes=video+77696,
            preliminary_three_trd_margin_bytes=1937664-video-77696))
    report = dict(scope=__doc__, complete=True, baseline_commit='d17f2ab',
        states_sha256=experiment['states_sha256'], selection_sha256=experiment['selection_sha256'],
        baseline_fhf_video_bytes=baseline['zx0_with_headers_bytes'],
        baseline_fhf_raw_bytes=old['raw_bytes'], rows=rows,
        z80_dictionary_decoder_not_implemented=True, player_changed=False,
        integrated_player_delta_tstates=0, full_frame_delivery_measured=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
