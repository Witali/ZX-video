"""Prepare the complete authorized five-level edit before choosing CB41 volumes.

Cache small sequential chunks without resetting palette history. Decode the
source through EOF, verify the existing edited AY, and count exact row-table
requirements. This is preparation evidence, not a playback or release check.
"""
import argparse
import hashlib
import json
from fractions import Fraction
import math
from pathlib import Path
import subprocess
import time

import numpy as np

import ay_interrupt
import build_long_video_trd as video
import five_level_dither as five
import hybrid_five_level as hybrid
from build_five_level_test_trd import save, source_audio
from prepare_edited_movie import frame_map
from probe_hybrid_five_level import error

ROOT = Path(__file__).resolve().parent
CHUNK = 64
FRAME_BYTES = 256 * 144 * 3


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'ffmpeg', 'audio-raw', 'work', 'report'):
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--timeline', type=Path, default=ROOT/'movie_no_credits.json')
    p.add_argument('--audio-reference', type=Path, default=ROOT/'no_credits_timeline.json')
    a = p.parse_args()
    a.work.mkdir(parents=True, exist_ok=True)
    timeline = json.loads(a.timeline.read_bytes())
    reference = json.loads(a.audio_reference.read_bytes())
    if timeline['frame_rate'] != [25, 3] or timeline['audio_rate_hz'] != 50:
        raise ValueError('this preparation uses exactly six AY ticks per video frame')
    mapping = frame_map(timeline['source_frames'], timeline['remove_frames'])
    if reference['timeline'] != timeline:
        raise ValueError('audio reference belongs to a different timeline')
    source_hash = file_sha(a.source)
    if source_hash != timeline['source_video_sha256']:
        raise ValueError('source video identity differs')
    audio = source_audio(a.audio_raw.read_bytes())
    sound = b''.join(frame.serialize() for frame in audio)
    if len(audio) != len(mapping)*6 or sha(sound) != reference['ay_sha256']:
        raise ValueError('edited soundtrack differs from the reviewed AY reference')
    registers = b''.join(map(ay_interrupt.registers, audio))
    (a.work/'audio.bin').write_bytes(sound)
    (a.work/'registers.bin').write_bytes(registers)
    sources = ('prepare_cell_codebook_movie.py', 'build_long_video_trd.py',
               'build_zxv_trd.py', 'five_level_dither.py', 'hybrid_five_level.py',
               'dither_phase.py', 'probe_hybrid_five_level.py', 'prepare_edited_movie.py')
    contract = dict(source_sha256=source_hash, ffmpeg_sha256=file_sha(a.ffmpeg),
                    timeline=timeline, zoom=1.25, attr_change_penalty=100000,
                    quantizer='ordered4 followed by exact hybrid five-level refinement',
                    palette_history='continuous across retained frames, including the edit join',
                    final_interval='same ceil-to-six-fields policy as build_full_movie.py; hold source EOF',
                    chunk_frames=CHUNK,
                    source_sha256_lf={name: sha((ROOT/name).read_bytes().replace(b'\r\n', b'\n'))
                                      for name in sources})
    contract_path = a.work/'contract.json'
    if contract_path.exists() and json.loads(contract_path.read_bytes()) != contract:
        raise ValueError('preparation cache contract changed; use a new work directory')
    save(contract_path, contract)
    decoded = a.work/'analysis.rgb'
    decode_report = a.work/'decode.json'
    if not decode_report.exists():
        partial = a.work/'analysis.partial.rgb'
        ffprobe = a.ffmpeg.with_name('ffprobe.exe')
        probe = json.loads(subprocess.check_output([str(ffprobe.resolve()), '-v', 'error',
            '-show_entries', 'format=duration:stream=codec_type,duration', '-of', 'json', str(a.source.resolve())]))
        durations = [Fraction(s['duration']) for s in probe['streams']
                     if s['codec_type'] in ('audio', 'video') and s.get('duration') not in (None, 'N/A')]
        duration = max(durations) if durations else Fraction(probe['format']['duration'])
        if math.ceil(duration*Fraction(25, 3)) != timeline['source_frames']:
            raise ValueError('source duration differs from reviewed full-movie frame count')
        command = [str(a.ffmpeg.resolve()), '-v', 'error', '-nostdin', '-y',
                   '-i', str(a.source.resolve()), '-an', '-vf',
                   'tpad=stop_mode=clone:stop_duration=0.12,fps=25/3,scale=256:144:flags=area',
                   '-frames:v', str(timeline['source_frames']), '-pix_fmt', 'rgb24',
                   '-f', 'rawvideo', str(partial.resolve())]
        print('Decoding source through EOF', flush=True)
        subprocess.run(command, check=True)
        size = partial.stat().st_size
        if size != timeline['source_frames']*FRAME_BYTES:
            raise ValueError(('source EOF/frame count mismatch', size, timeline['source_frames']))
        partial.replace(decoded)
        save(decode_report, dict(frames=size//FRAME_BYTES, sha256=file_sha(decoded), bytes=size,
                                decoded_to_eof=True, command=command, source_duration_seconds=float(duration),
                                tail_hold_seconds=float(Fraction(timeline['source_frames']*3, 25)-duration),
                                duration_probe=probe, ffprobe_sha256=file_sha(ffprobe)))
    decoded_meta = json.loads(decode_report.read_bytes())
    if (decoded.stat().st_size != timeline['source_frames']*FRAME_BYTES
            or file_sha(decoded) != decoded_meta['sha256']):
        raise ValueError('decoded RGB cache changed')
    rgb = np.memmap(decoded, dtype=np.uint8, mode='r',
                    shape=(timeline['source_frames'], 144, 256, 3))
    attrs = None
    chunks, rows, qualities = [], [], []
    started = time.monotonic()
    for lo in range(0, len(mapping), CHUNK):
        hi = min(lo+CHUNK, len(mapping))
        cached = a.work/f'frames-{lo:05d}.npz'
        info = a.work/f'frames-{lo:05d}.json'
        if cached.exists() and info.exists():
            meta = json.loads(info.read_bytes())
            if file_sha(cached) != meta['cache_sha256']:
                raise ValueError(('chunk cache changed', lo))
            with np.load(cached, allow_pickle=False) as data:
                frames = data['five_states'].copy()
                attrs = data['last_attrs'].copy()
                if not np.array_equal(data['source_frames'], mapping[lo:hi]):
                    raise ValueError('chunk timeline differs')
        else:
            frames, images, quality = [], [], []
            for index in range(lo, hi):
                image = video.apply_reframe(rgb[mapping[index]], video.ReframeWindow(.5, .5, 1.25))
                compact, attrs = video.encode_compact_frame(image, attrs, 100000, 'ordered4')
                refined = bytearray(hybrid.refine_compact(compact, image))
                refined[3840:3936] = bytes([1])*96
                refined[4512:] = bytes([1])*96
                refined = bytes(refined)
                before = error(hybrid.from_compact(compact), image)
                after = error(hybrid.from_five(refined, adaptive=False), image)
                if after > before+1e-9:
                    raise AssertionError(('refinement increased RGB error', index))
                if any(refined[3840+i] & 128 for i in range(768)):
                    raise AssertionError('FLASH must stay disabled')
                quality.append(dict(frame=index, source_frame=int(mapping[index]),
                                    four_mse=before, five_mse=after,
                                    screen_sha256=sha(b''.join(five.expand(refined)))))
                frames.append(np.frombuffer(refined, dtype=np.uint8))
                images.append(image)
            frames = np.stack(frames)
            np.savez_compressed(cached, five_states=frames, images=np.stack(images),
                                source_frames=mapping[lo:hi], last_attrs=attrs)
            meta = dict(start=lo, end=hi, cache_sha256=file_sha(cached), quality=quality)
            save(info, meta)
        chunks.append(dict(start=lo, end=hi, file=cached.name, sha256=meta['cache_sha256']))
        qualities.extend(meta['quality'])
        rows.append(np.stack([five.unpack_words(frame[:3840].tobytes()).ravel() for frame in frames]))
        print(f'Prepared {hi}/{len(mapping)} frames, elapsed {time.monotonic()-started:.1f}s', flush=True)
    words = np.concatenate(rows)
    counts = np.bincount(words.ravel(), minlength=625)
    windows = []
    for lo in range(0, len(mapping), CHUNK):
        hi = min(lo+CHUNK, len(mapping))
        local = set(map(int, words[max(0, lo-2):hi].ravel())) | {0}
        windows.append(dict(start=lo, end=hi, rows_including_two_checkpoints=len(local)))
    partitions = []
    for lo, hi in zip(np.linspace(0, len(mapping), 4, dtype=int)[:-1],
                      np.linspace(0, len(mapping), 4, dtype=int)[1:]):
        local = set(map(int, words[max(0, lo-2):hi].ravel())) | {0}
        partitions.append(dict(start=int(lo), end=int(hi), rows_including_two_checkpoints=len(local),
                               row_table_fits=len(local)<=256))
    np.savez_compressed(a.work/'words.npz', words=words, source_frames=mapping)
    report = dict(complete=True, release=False, scope=__doc__, baseline_commit='2a9fa05',
                  contract=contract, frames=len(mapping), source_frames=timeline['source_frames'],
                  first_source_frame=int(mapping[0]), last_source_frame=int(mapping[-1]),
                  source_frame_map_sha256=sha(mapping.astype('<i8').tobytes()),
                  decoded_source=decoded_meta, chunks=chunks, quality=qualities,
                  ay_ticks=len(audio), ay_sha256=sha(sound), ay_registers_sha256=sha(registers),
                  edited_audio_reference_sha256=file_sha(a.audio_reference),
                  input_audio_fap3_sha256=file_sha(a.audio_raw),
                  joins=[dict(output_frame=int(i), before=int(mapping[i-1]), after=int(mapping[i]))
                         for i in np.flatnonzero(np.diff(mapping)!=1)+1],
                  unique_rows=int(np.count_nonzero(counts)), row_histogram=counts.tolist(),
                  all_five_levels_used=sorted(set(map(int, (words[..., None]//np.array([125,25,5,1])%5).ravel())))==list(range(5)),
                  windows=windows, three_equal_frame_partitions=partitions,
                  refinement_never_increased_rgb_error=True, brightness_before_fixed_dither=True,
                  player_changed=False, player_instruction_delta_tstates=0,
                  actual_playback_measured=False, disk_capacity_measured=False)
    save(a.report, report)
    print(json.dumps({k:report[k] for k in ('frames', 'last_source_frame', 'ay_ticks', 'unique_rows',
                                          'three_equal_frame_partitions')}), flush=True)


if __name__ == '__main__':
    main()
