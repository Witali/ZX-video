"""Measure one three-volume CB41 partition against exact row and AY RAM limits.

The same prepared five-level frames and soundtrack are retained. Count both
screen checkpoints, round-trip every coded frame and LZSA2 block, and keep
disk size estimates separate from native playback and boot verification.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import ay_huffman_stream
import ay_interrupt
import build_long_video_trd as video
import five_level_dither as five
from build_five_level_test_trd import save
from lzsa2_oracle_host import Author
from prepare_cell_codebook_movie import file_sha, sha
from probe_cell_codebook import changes, encode, decode_check, compress
from row_dictionary_video import encode_states
import resident_audio_z80 as resident


def audio_size(frames, start, end, labels):
    # Retain the actual global change records; initialize from the prior tick.
    records = ay_interrupt.encode_ticks(frames)
    selected = records[start*6:end*6]
    initial = ay_interrupt.registers(frames[start*6-1]) if start else bytes(11)
    data, metadata = ay_huffman_stream.encode(selected, initial)
    decoded_initial, decoded = ay_huffman_stream.decode(data)
    assert decoded_initial == initial and decoded == selected
    registers = bytearray(initial)
    for tick, frame in zip(decoded, frames[start*6:end*6], strict=True):
        for i in range(1, len(tick), 2):
            registers[tick[i]] = tick[i+1]
        assert bytes(registers) == ay_interrupt.registers(frame)
    first, ticks, trees, payload = resident.tables(data)
    blob, layout, _ = resident.code(labels, len(ticks), first, 0, 0)
    roots = (layout['end']+255) & ~255
    _, nodes = resident.tree_bytes(trees, roots+26)
    size = roots-resident.ORIGIN+26+len(nodes)+len(payload)
    fits = size <= 16384
    if fits:
        actual = resident.build(data, labels)
        assert actual['image_bytes'] == size
    return data, dict(ayh1_bytes=len(data), resident_bytes=size, resident_fits=fits,
                      spare_bank_bytes=16384-size, trees_bytes=len(nodes)+26,
                      code_state_alignment_bytes=roots-resident.ORIGIN,
                      register_roundtrip_exact=True, initial_sha256=sha(initial), **metadata)


def minimum_row_segments(words):
    """Greedy maximal prefixes for the monotone union-of-rows constraint."""
    result, start = [], 0
    while start < len(words):
        used = {0} | set(map(int, words[max(0, start-2):start].ravel()))
        end = start
        while end < len(words):
            candidate = used | set(map(int, words[end]))
            if len(candidate)>256:
                break
            used, end = candidate, end+1
        if end == start:
            return dict(possible=False, first_unrepresentable_frame=start, segments=result)
        result.append(dict(start=start, end=end, rows=len(used)))
        start = end
    return dict(possible=True, minimum_volumes=len(result), segments=result,
                excludes='video bytes, audio bank limits, startup/player and timing')


def select_partition(words, equal):
    """Move only boundaries in a small window if equal thirds overflow rows.

    No candidate movies are compressed: use prefix counts for exact row-set
    membership, including both checkpoints. Compress one selected partition.
    """
    if all(part['row_table_fits'] for part in equal):
        return equal, dict(method='equal thirds already fit', row_boundary_candidates=0)
    present = np.stack([np.bincount(row, minlength=625)>0 for row in words])
    prefix = np.vstack([np.zeros(625, dtype=np.int32), np.cumsum(present, axis=0, dtype=np.int32)])
    def count(start, end):
        used = prefix[end]-prefix[max(0, start-2)]
        used[0] = 1
        return int(np.count_nonzero(used))
    first, second = equal[0]['end'], equal[1]['end']
    candidates = []
    tested = 0
    for a in range(max(64, (first-256+63)//64*64), min(len(words), first+256)+1, 64):
        for b in range(max(a+64, (second-256+63)//64*64), min(len(words), second+256)+1, 64):
            if b>=len(words):
                continue
            tested += 1
            boundaries = [0,a,b,len(words)]
            rows = [count(lo, hi) for lo, hi in zip(boundaries,boundaries[1:])]
            if max(rows)<=256:
                score = abs(a-first)+abs(b-second)
                candidates.append((score, max(np.diff(boundaries)), a, b, rows))
    if not candidates:
        return equal, dict(method='no fitting row partition in bounded search', row_boundary_candidates=tested)
    _, _, a, b, rows = min(candidates)
    boundaries = [0,a,b,len(words)]
    parts = [dict(start=lo,end=hi,rows_including_two_checkpoints=n,row_table_fits=True)
             for lo,hi,n in zip(boundaries,boundaries[1:],rows)]
    return parts, dict(method='closest 64-frame-aligned cuts within 256 frames of each equal-third boundary',
                       row_boundary_candidates=tested, fitting_candidates=len(candidates),
                       compressed_candidates=1, equal_thirds=equal, selected_boundaries=boundaries)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'metadata', 'author', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    prepared = json.loads(a.prepared.read_bytes())
    work = a.prepared.parent
    with np.load(work/'words.npz', allow_pickle=False) as cache:
        words = cache['words']
        mapping = cache['source_frames']
    frames = []
    for chunk in prepared['chunks']:
        path = work/chunk['file']
        assert file_sha(path) == chunk['sha256']
        with np.load(path, allow_pickle=False) as cache:
            frames.extend(frame.tobytes() for frame in cache['five_states'])
    assert len(frames) == len(mapping) == prepared['frames']
    for i, frame in enumerate(frames):
        assert np.array_equal(five.unpack_words(frame[:3840]).ravel(), words[i]), ('word cache differs', i)
    # A compact reproducible input archive; RGB stays in the local chunk cache.
    np.savez_compressed(a.output/'five-states.npz',
        five_states=np.stack([np.frombuffer(frame, dtype=np.uint8) for frame in frames]),
        source_frames=mapping)
    sound = (work/'audio.bin').read_bytes()
    assert sha(sound) == prepared['ay_sha256']
    audio = [video.AyFrame.deserialize(sound[i:i+9]) for i in range(0, len(sound), 9)]
    (a.output/'audio.bin').write_bytes(sound)
    labels = json.loads(a.metadata.read_bytes())['audio_labels']
    author = Author(a.author)
    parts, selection = select_partition(words, prepared['three_equal_frame_partitions'])
    print(json.dumps(dict(boundary_selection=selection)), flush=True)
    results = []
    for volume, part in enumerate(parts, 1):
        start, end = part['start'], part['end']
        target = a.output/f'volume-{volume}'
        target.mkdir(exist_ok=True)
        coded_audio, audio_report = audio_size(audio, start, end, labels)
        (target/'audio.ayh1').write_bytes(coded_audio)
        item = dict(volume=volume, **part, audio=audio_report)
        if part['row_table_fits']:
            first = max(0, start-2)
            states, rows = encode_states(frames[first:end])
            local = start-first
            changed = changes(states, local, end-start)
            counts = Counter(row['patterns'][i] for row in changed for i in row['changed'])
            book = sorted(counts, key=lambda key: (-counts[key], key))[:256]
            if len(book) != 256:
                raise ValueError('this CB41 experiment requires 256 observed patterns')
            raw, table, details = encode(changed, book, rows['words'])
            initial, checks = decode_check(raw, states, local, end-start, rows['words'], rows)
            stream, blocks = compress(raw, author)
            (target/'codebook.raw').write_bytes(raw)
            (target/'codebook.stream').write_bytes(stream)
            (target/'initial-screens.bin').write_bytes(initial)
            np.savez_compressed(target/'states.npz', states=states)
            save(target/'row-dictionary.json', rows)
            item.update(raw_bytes=len(raw), compressed_bytes=len(stream),
                        video_sectors=(len(stream)+255)//256,
                        raw_sha256=sha(raw), stream_sha256=sha(stream),
                        blocks=blocks, full_host_screens_exact=True,
                        screen_sha256=checks, frames=details,
                        dictionary_rows=rows['entries'],
                        unique_changed_patterns=len(counts),
                        book_cells=sum(row['book_cells'] for row in details),
                        changed_cells=sum(row['changed_cells'] for row in details),
                        # Only video is counted; even a pass cannot prove disk fit.
                        video_alone_fits_trd=(len(stream)+255)//256 <= 2544)
        results.append(item)
        print(json.dumps({k:v for k,v in item.items() if k not in ('blocks','frames','screen_sha256')}), flush=True)
    report = dict(complete=True, release=False, scope=__doc__, baseline_commit='2a9fa05',
                  preparation_sha256=file_sha(a.prepared), frames=len(frames),
                  first_source_frame=int(mapping[0]), last_source_frame=int(mapping[-1]),
                  minimum_row_only_partition=minimum_row_segments(words),
                  volumes=results, partitions_evaluated=1,
                  boundary_selection=selection,
                  equal_frame_boundaries=[0]+[p['end'] for p in prepared['three_equal_frame_partitions']],
                  all_row_tables_fit=all(v['row_table_fits'] for v in results),
                  all_audio_banks_fit=all(v['audio']['resident_fits'] for v in results),
                  source_sha256_lf={name:sha(Path(__file__).with_name(name).read_bytes().replace(b'\r\n',b'\n'))
                      for name in ('measure_cell_codebook_movie.py', 'probe_cell_codebook.py',
                                   'row_dictionary_video.py', 'ay_huffman_stream.py', 'resident_audio_z80.py')},
                  author_dll_sha256=file_sha(a.author),
                  player_changed=False, player_instruction_delta_tstates=0,
                  actual_playback_measured=False, independently_bootable_verified=False,
                  trd_images_built=False)
    save(a.output/'measurements.json', report)
    print(json.dumps({k:report[k] for k in ('all_row_tables_fit','all_audio_banks_fit','minimum_row_only_partition')}), flush=True)


if __name__ == '__main__':
    main()
