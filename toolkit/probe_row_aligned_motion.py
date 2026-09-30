"""One lossless row-aligned-motion candidate on saved five-level windows.

Build stream bytes and overlap proofs only; profile frame/transport CPU with
the existing harnesses before deciding whether to build a timing-test disk.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import struct
import numpy as np
from build_fap3_trd import sha
from build_five_level_test_trd import source_audio, save
from encode_fap3 import encode
from lzsa2_row_player import Builder
from probe_hybrid_tiles import OFFSETS
from row_dictionary_video import reference_tables


def packet_counts(video):
    at = 0; vectors = Counter(); rows = []
    while at < len(video):
        n = struct.unpack_from('<H', video, at)[0]
        body = video[at + 2:at + 2 + n]
        if len(body) != n or n < 288:
            raise ValueError('truncated video packet')
        flags, masks, coded = struct.unpack_from('<BHH', body)
        counts = Counter(body[8:200]); vectors.update(counts)
        rows.append(dict(bytes=n, motion=sum(v for k, v in counts.items() if 0 < k < 81),
                         cache=bool(flags & 128), coded_bytes=coded, mask_bytes=masks))
        at += 2 + n
    if at != len(video): raise ValueError('trailing video bytes')
    return dict(vectors=dict(vectors), motion=sum(r['motion'] for r in rows),
                cache_frames=sum(r['cache'] for r in rows), packets=rows)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('baseline', 'states', 'metadata', 'options', 'zx0', 'lzsa', 'output'):
        p.add_argument('--' + key, type=Path, required=True)
    a = p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
    original = a.baseline.read_bytes(); m = json.loads(a.metadata.read_bytes())
    with np.load(a.states, allow_pickle=False) as saved: states = saved['states']
    if sha(original) != m['raw_sha256'] or sha(states.tobytes()) != m['states_sha256']:
        raise ValueError('input identity differs from metadata')
    audio = source_audio(original)
    before, _ = encode(states, audio, fragment_byte_slack=16)
    if before != original: raise AssertionError('default path changed baseline bytes')
    raw, details = encode(states, audio, fragment_byte_slack=16, row_aligned_motion=True)
    (a.output/'input.fap3').write_bytes(raw)
    options = json.loads(a.options.read_bytes())['contract']['options']
    options['startup_delta'] = False
    with reference_tables(m['row_dictionary']):
        b = Builder(raw, states, a.zx0.resolve(), a.output/'cache', row_dictionary=m['row_dictionary'],
                    lzsa=a.lzsa.resolve(), series_fingerprint=b'AYH1R5M1'+bytes.fromhex(sha(raw))[:6], **options)
        video, _ = b.separated(0, len(states)); stream, blocks = b.stream(0, len(states))
    counts = packet_counts(video)
    for vector in counts['vectors']:
        if 0 < vector < 81 and OFFSETS[vector][0] % 4:
            raise AssertionError('unaligned native motion vector')
        if 81 <= vector < 85: raise AssertionError('unexpected spatial prediction')
    if source_audio(raw) != audio: raise AssertionError('AY differs')
    (a.output/'video.raw').write_bytes(video); (a.output/'video.stream').write_bytes(stream)
    report = dict(complete=True, release=False, baseline_commit='d0e4731', scope=__doc__,
        baseline_raw_sha256=sha(original), raw_sha256=sha(raw), states_sha256=sha(states.tobytes()),
        decoded_sha256=sha(video), stream_sha256=sha(stream), frame_count=len(states),
        decoded_bytes=len(video), video_bytes=len(stream), video_sectors=(len(stream)+255)//256,
        default_encoder_exact=True, exact_ay=True, codec=details, commands=counts, blocks=blocks,
        native_implementation_changed=False, new_instruction_timing_delta=0,
        actual_playback_measured=False)
    save(a.output/'probe.json', report)
    print(json.dumps({k:report[k] for k in ('frame_count','decoded_bytes','video_bytes','video_sectors')} |
                     {'motion':counts['motion'], 'cache_frames':counts['cache_frames']}), flush=True)


if __name__ == '__main__': main()
