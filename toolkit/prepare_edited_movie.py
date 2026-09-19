"""Apply a reviewed frame edit to converted screens and absolute 50 Hz AY states.

Retained bytes are never requantized. Regenerate legacy video deltas so a
splice cannot reference a deleted frame. Outputs feed build_fast_sparse_trd;
they are verified build inputs, not a tested release or disk-speed result.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import build_long_video_trd as video
import ay_interrupt
from probe_lossless_layouts import sha


def frame_map(count, ranges):
    if not isinstance(count, int) or count <= 0:
        raise ValueError('invalid source frame count')
    keep = np.ones(count, dtype=bool)
    previous_end = 0
    for start, end in ranges:
        if (type(start) is not int or type(end) is not int
                or not previous_end <= start < end <= count):
            raise ValueError('cuts must be ordered, disjoint, nonempty and within source')
        keep[start:end] = False
        previous_end = end
    indices = np.flatnonzero(keep)
    if not len(indices):
        raise ValueError('edit removes every frame')
    return indices


def edit(states, audio, ranges):
    if states.dtype != np.uint8 or states.ndim != 2 or states.shape[1] != 3840:
        raise ValueError('expected compact uint8 screens')
    if len(audio) != len(states)*54:
        raise ValueError('expected exactly six nine-byte AY ticks per source frame')
    indices = frame_map(len(states), ranges)
    sound = np.frombuffer(audio, dtype=np.uint8).reshape(len(states), 54)[indices].tobytes()
    return states[indices].copy(), sound, indices


def legacy_stream(states, audio):
    packets, previous = [], None
    for index, state in enumerate(states):
        current = state.tobytes()
        sound = audio[index*54:index*54+9]
        video.AyFrame.deserialize(sound)
        packets.append(video.make_packet(current, previous, sound))
        previous = current
    stream = video.serialize_video(packets, 25/3, 25/3)
    video.verify_video(stream, [s.tobytes() for s in states])
    return stream, packets


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--states', type=Path, required=True)
    p.add_argument('--ay', type=Path, required=True)
    p.add_argument('--timeline', type=Path, default=Path(__file__).with_name('movie_no_credits.json'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    timeline = json.loads(args.timeline.read_text(encoding='utf-8'))
    with np.load(args.states, allow_pickle=False) as saved:
        source = saved['states']
    audio = args.ay.read_bytes()
    if (timeline['frame_rate'] != [25, 3] or timeline['audio_rate_hz'] != 50
            or len(source) != timeline['source_frames']
            or sha(source.tobytes()) not in timeline['accepted_states_sha256']
            or sha(audio) != timeline['source_ay_sha256']):
        raise ValueError('timeline belongs to a different source/rate')
    states, sound, indices = edit(source, audio, timeline['remove_frames'])
    stream, packets = legacy_stream(states, sound)
    out = args.output
    (out/'source').mkdir(parents=True, exist_ok=True)
    (out/'audio/50Hz').mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out/'source/conversion.npz', states=states, source_frames=indices)
    (out/'source/VIDEO_full.C.bin').write_bytes(stream)
    (out/'audio/50Hz/raw.bin').write_bytes(sound)
    audio_frames = [video.AyFrame.deserialize(sound[i:i+9]) for i in range(0, len(sound), 9)]
    records = ay_interrupt.encode_ticks(audio_frames)
    registers = bytearray(11)
    for frame, record in zip(audio_frames, records):
        if len(record) != 1+2*record[0]:
            raise AssertionError('invalid AY register record')
        for offset in range(1, len(record), 2):
            registers[record[offset]] = record[offset+1]
        if registers != ay_interrupt.registers(frame):
            raise AssertionError('AY register replay differs')
    pairs = b''.join(records)
    (out/'audio/50Hz/register_pairs.bin').write_bytes(pairs)
    # Validate persisted data, not only the pre-write arrays.
    with np.load(out/'source/conversion.npz', allow_pickle=False) as saved:
        if not np.array_equal(saved['states'], source[indices]):
            raise AssertionError('saved screens changed')
    if (out/'audio/50Hz/raw.bin').read_bytes() != sound:
        raise AssertionError('saved AY changed')
    joins = (np.flatnonzero(np.diff(indices) != 1)+1).tolist()
    stats = dict(frames=len(states), fps=25/3, screen_fps=25/3,
        duration_seconds=len(states)*3/25, video_bytes=len(stream),
        packet_sectors=[x.sectors for x in packets],
        raw_packets=sum(x.raw for x in packets), delta_packets=sum(not x.raw for x in packets))
    report = dict(scope=__doc__, complete=True, timeline=timeline,
        source_states_sha256=sha(source.tobytes()), source_ay_sha256=sha(audio),
        frames_before=len(source), frames_after=len(states),
        removed_frames=len(source)-len(states), removed_seconds=(len(source)-len(states))*3/25,
        duration_seconds=len(states)*3/25, audio_ticks=len(sound)//9,
        ay_pair_bytes=len(pairs), ay_pairs_sha256=sha(pairs), ay_register_replay_verified=True,
        states_sha256=sha(states.tobytes()), ay_sha256=sha(sound),
        legacy_stream_sha256=sha(stream),
        last_source_frame=int(indices[-1]), last_frame_sha256=sha(states[-1].tobytes()),
        source_frame_map_sha256=sha(indices.astype('<u4').tobytes()),
        joins=[dict(output_frame=i, previous_source_frame=int(indices[i-1]),
                    next_source_frame=int(indices[i]), audio_tick=i*6) for i in joins],
        retained_screens_byte_exact=True, retained_ay_ticks_byte_exact=True,
        legacy_stream_full_decode_verified=True, player_changed=False,
        integrated_player_delta_tstates=0, full_frame_delivery_measured=False,
        release_disks_changed=False)
    metadata = dict(source=report, stats=stats, logical_states_sha256=report['states_sha256'],
        last_state_sha256=report['last_frame_sha256'],
        ay=dict(update_rate_hz=50, source=str((out/'audio/50Hz/raw.bin').resolve()), sha256=sha(sound)))
    (out/'source/build_metadata.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
