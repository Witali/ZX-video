"""Convert a local video supported by FFmpeg to numbered Spectrum 128 TRDs."""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

import ay_fidelity as ay
import build_long_video_trd as video
from build_fap3_trd import Builder, sha
from encode_fap3 import encode
import fap3_disk_z80 as disk

FPS = Fraction(25, 3)
HERE = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')


def executable(value, name):
    found = shutil.which(str(value or name))
    if not found:
        raise ValueError(f'{name} not found: install it in PATH or pass --{name} PATH')
    return str(Path(found).resolve())


def run(command):
    result = subprocess.run(command, capture_output=True)
    if result.returncode:
        raise RuntimeError(f'{Path(command[0]).name} failed:\n'+result.stderr.decode(errors='replace')[-6000:])
    return result.stdout


def probe_media(source, ffprobe):
    probe = json.loads(run([ffprobe, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(source)]))
    pictures = [s for s in probe['streams'] if s['codec_type'] == 'video'
                and not s.get('disposition', {}).get('attached_pic')]
    sounds = [s for s in probe['streams'] if s['codec_type'] == 'audio']
    if not pictures:
        raise ValueError('input has no playable video stream')
    picture = next((s for s in pictures if s.get('disposition', {}).get('default')), pictures[0])
    sound = next((s for s in sounds if s.get('disposition', {}).get('default')), sounds[0] if sounds else None)
    return probe, picture, sound


def rational(value, default=Fraction(0)):
    try:
        return Fraction(value)
    except (ValueError, TypeError, ZeroDivisionError):
        return default


def decode_video(source, ffmpeg, directory, probe, picture, sound):
    # Fit display aspect (including non-square source pixels); never crop/zoom.
    # EOF pass + upward rounding retains even a one-frame, sub-120 ms clip.
    filters = ("setpts=PTS-STARTPTS,fps=25/3:start_time=0:round=up:eof_action=pass,"
               "scale=w='max(1,round(min(128,72*dar)))':h='max(1,round(min(72,128/dar)))':flags=area,"
               "setsar=1,pad=128:72:(ow-iw)/2:(oh-ih)/2:black")
    path = directory/'frames.rgb'
    command = [ffmpeg, '-v', 'error', '-nostdin', '-y', '-i', str(source), '-map', f'0:{picture["index"]}',
               '-an', '-vf', filters, '-pix_fmt', 'rgb24', '-f', 'rawvideo', str(path)]
    run(command)
    size = 128*72*3
    count, remainder = divmod(path.stat().st_size, size)
    if not count or remainder:
        raise ValueError('FFmpeg did not return complete video frames')
    start = rational(picture.get('start_time'))
    ends = [rational(s.get('start_time'), start)+rational(s.get('duration'))-start
            for s in (picture, sound) if s and rational(s.get('duration')) > 0]
    if not ends:
        ends = [rational(probe.get('format', {}).get('duration'))]
    wanted = max(count, math.ceil(max(ends, default=Fraction(0))*FPS))
    if wanted > 0xffffffff:
        raise ValueError('input exceeds the 32-bit FAP3 frame count')
    if wanted > count:
        with path.open('r+b') as stream:
            stream.seek(-size, 2)
            last = stream.read(size)
            for _ in range(wanted-count):
                stream.write(last)
    return np.memmap(path, dtype=np.uint8, mode='r', shape=(wanted, 72, 128, 3)), dict(
        video_stream=picture['index'], audio_stream=sound['index'] if sound else None,
        decoded_frames=count, encoded_frames=wanted, tail_repeated_frames=wanted-count,
        encoded_seconds=float(Fraction(wanted, 1)/FPS), fit='contain', crop=False, command=command)


def convert_frames(images, directory):
    states = np.lib.format.open_memmap(directory/'states.npy', mode='w+', dtype=np.uint8, shape=(len(images), 3840))
    previous = None
    errors = []
    image = np.zeros((96, 128, 3), dtype=np.uint8)
    for index, active in enumerate(images):
        image[12:84] = active
        data, previous = video.encode_compact_frame(image, previous, 100000, 'ordered4')
        states[index] = np.frombuffer(data, dtype=np.uint8)
        # Enforce the player format's fixed black bands, including their palette.
        states[index, :384] = states[index, 2688:3072] = 0
        states[index, 3072:3168] = states[index, 3744:] = 1
        previous = states[index, 3072:].copy()
        errors.append(video.reconstructed_error(states[index].tobytes(), image))
        if index % 100 == 0:
            print(f'Image conversion: {index+1}/{len(images)}', flush=True)
    states.flush()
    # Existing diagnostic tools consume this portable checkpoint format.
    np.savez(directory/'conversion.npz', states=states)
    return states, dict(metric='mean squared linear RGB error after native dithering, per frame',
        measured_against='scaled source before Spectrum palette quantization',
        mean_mse=float(np.mean(errors)), maximum_mse=max(errors), frame_mse=errors,
        compression_additional_pixel_changes=False, perceptual_percent_claimed=False)


def write_video_preview(images, states, quality, path):
    from PIL import Image, ImageDraw
    worst = np.argsort(quality['frame_mse'])[-4:]
    indices = sorted({0, len(states)-1, *map(int, worst)})
    sheet = Image.new('RGB', (512, len(indices)*216), (24, 24, 24))
    labels = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        source = np.zeros((96, 128, 3), dtype=np.uint8)
        source[12:84] = images[index]
        sheet.paste(Image.fromarray(source).resize((256, 192), Image.Resampling.NEAREST), (0, row*216+24))
        bitmap, attrs = video.expand_compact_screen(states[index].tobytes())
        rendered = video.base.render_spectrum_screen(bitmap, attrs)
        sheet.paste(Image.fromarray(rendered), (256, row*216+24))
        labels.text((4, row*216+4), f'Frame {index}: scaled source', fill='white')
        labels.text((260, row*216+4), 'Spectrum', fill='white')
    sheet.save(path)
    quality['preview_frames'] = indices
    quality['preview'] = path.name


def convert_audio(source, ffmpeg, directory, picture, sound, count):
    ticks, rate = count*6, 22050
    if sound is None:
        frames = [video.AyFrame((1, 1, 1), (0, 0, 0))]*ticks
        report = dict(source_audio=False, ticks=ticks, silence=True)
    else:
        duration = Fraction(count, 1)/FPS
        start = rational(picture.get('start_time'))
        # Keep audio offsets relative to the first video PTS; fill gaps and tail.
        filters = f'asetpts=PTS-({float(start):.12g})/TB,aresample={rate}:async=1:first_pts=0,apad'
        command = [ffmpeg, '-v', 'error', '-nostdin', '-copyts', '-i', str(source),
            '-map', f'0:{sound["index"]}', '-vn', '-af', filters, '-t', f'{float(duration):.12g}',
            '-ac', '1', '-ar', str(rate), '-f', 'f32le', '-']
        samples = np.frombuffer(run(command), dtype='<f4').astype(np.float64)
        sample_count = round(duration*rate)
        samples = np.pad(samples[:sample_count], (0, max(0, sample_count-len(samples))))
        print(f'AY analysis: {ticks} updates at 50 Hz', flush=True)
        magnitude, rms = ay.spectra(samples, rate, 50, ticks)
        amplitude, explained = ay.decompose(magnitude, rate)
        periods, volumes, _ = ay.arrange(amplitude, rms, explained)
        noise, volumes, _ = ay.arrange_noise(magnitude, rms, explained, volumes, rate)
        previous = 1
        for i in range(ticks):
            if noise[i]: periods[i, 1] = previous
            else: previous = periods[i, 1]
        frames = [video.AyFrame(tuple(map(int, p)), tuple(map(int, v)), int(n))
                  for p, v, n in zip(periods, volumes, noise)]
        import compare_ay_fidelity as quality
        rendered = ay.render(frames, 50, rate)
        quality.write_wav(directory/'audio-preview.wav', rendered, rate)
        metrics = quality.compare(quality.features(samples, rate, float(FPS), count),
                                  quality.features(rendered, rate, float(FPS), count))
        report = dict(source_audio=True, ticks=ticks, noise_ticks=int(np.count_nonzero(noise)),
            synthesis='three AY voices, optional noise on B, 50 Hz', metrics=metrics,
            metric_note='signal proxies, not a perceptual accuracy percentage', command=command)
    (directory/'ay.bin').write_bytes(b''.join(frame.serialize() for frame in frames))
    return frames, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='local video file; format detected by FFmpeg')
    parser.add_argument('--output', type=Path, required=True, help='new or empty output directory')
    parser.add_argument('--prefix', default='ZX-video', help='safe basename of numbered TRD files')
    for name in ('ffmpeg', 'ffprobe', 'zx0'):
        parser.add_argument('--'+name, help='executable path; defaults to PATH')
    parser.add_argument('--max-frames-per-disk', type=int, default=4096, help='upper bound, 1..10922; size may split sooner')
    parser.add_argument('--disk-profile', choices=('portable', 'trdos503'), default='portable',
        help='trdos503 enables the latest direct reads, cached seek and sector interleave')
    parser.add_argument('--trdos-rom', type=Path, help='verified TR-DOS 5.03 ROM, required for trdos503')
    parser.add_argument('--inline-matches', action='store_true', help='Optional faster ZX0 match copies; keeps the compressed stream unchanged')
    parser.add_argument('--fast-noop-scan', action='store_true', help='Optional combined unchanged-tile checks; keeps zero-copy vectors')
    parser.add_argument('--static-cache-borders', action='store_true', help='Skip virtual motion rows for unchanged edge stripes')
    parser.add_argument('--carry-huffman', action='store_true', help='Use carry for Huffman bit positions; unchanged video stream')
    parser.add_argument('--register-fragments', action='store_true', help='Write repeated fragment rows directly from registers')
    parser.add_argument('--irq-safe-paging', action='store_true', help='Optional restartable bank changes without disabling IRQ')
    parser.add_argument('--startup-delta', action='store_true', help='Smaller boot tables when adjacent-byte differences save disk sectors')
    parser.add_argument('--verify', choices=('cpu', 'fuse', 'none'), default='cpu',
        help='cpu: every instruction and full images; fuse: also real disk timing; none: host roundtrip only')
    parser.add_argument('--fuse', type=Path, help='Fuse executable for --verify fuse')
    parser.add_argument('--verification-timeout', type=float, default=1800, help='Fuse timeout in seconds per disk')
    parser.add_argument('--cached-huffman-byte', action='store_true', help='Cache current Huffman byte in B; requires --carry-huffman')
    args = parser.parse_args(argv)
    if args.cached_huffman_byte and not args.carry_huffman: parser.error('--cached-huffman-byte requires --carry-huffman')
    try:
        if not args.input.is_file(): raise ValueError('input video file does not exist')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', args.prefix):
            raise ValueError('--prefix must be 1..64 ASCII letters, digits, underscores or hyphens')
        if not 1 <= args.max_frames_per_disk <= 10922: raise ValueError('--max-frames-per-disk must be 1..10922')
        if args.verification_timeout <= 0: raise ValueError('--verification-timeout must be positive')
        if args.output.exists() and (not args.output.is_dir() or any(args.output.iterdir())):
            raise ValueError('--output must be new or empty; existing files are never overwritten')
        executables = {name: executable(getattr(args, name), name) for name in ('ffmpeg', 'ffprobe', 'zx0')}
        fast = args.disk_profile == 'trdos503'
        if fast and (not args.trdos_rom or sha(args.trdos_rom.read_bytes()) != disk.TRDOS_503_SHA256):
            raise ValueError('trdos503 requires --trdos-rom with the verified TR-DOS 5.03 hash')
        if args.verify == 'fuse' and (not args.fuse or not args.fuse.is_file()):
            raise ValueError('--verify fuse requires --fuse PATH')
        source, output = args.input.resolve(), args.output.resolve()
        probe, picture, sound = probe_media(source, executables['ffprobe'])
    except (ValueError, OSError, RuntimeError) as error:
        parser.error(str(error))
    output.mkdir(parents=True, exist_ok=True)
    work = output/'work'; work.mkdir()
    with source.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = dict(source=str(source), source_sha256=source_hash, complete=False, release=False,
        video_fps='25/3', ay_hz=50, native_resolution=[256, 192], active_resolution=[256, 144],
        logical_resolution=[128, 96], disk_profile=args.disk_profile, executables=executables,
        player_baseline='ab76fa1' if args.cached_huffman_byte else '7152e10' if args.register_fragments else '0cf64be' if args.carry_huffman else '6e724f4' if args.static_cache_borders else '00fb0fd' if args.irq_safe_paging else '491db7b' if args.fast_noop_scan else '80ab9d9' if args.inline_matches else '00313d3',
        player_hot_path_changed=args.inline_matches or args.fast_noop_scan or args.irq_safe_paging or args.static_cache_borders or args.carry_huffman or args.register_fragments or args.cached_huffman_byte,
        player_hot_path_delta_tstates=None if args.inline_matches or args.fast_noop_scan or args.irq_safe_paging or args.static_cache_borders or args.carry_huffman or args.register_fragments or args.cached_huffman_byte else 0,
        inline_matches=args.inline_matches,
        fast_noop_scan=args.fast_noop_scan,
        static_cache_borders=args.static_cache_borders,
        carry_huffman=args.carry_huffman,
        register_fragments=args.register_fragments,
        cached_huffman_byte=args.cached_huffman_byte,
        irq_safe_paging=args.irq_safe_paging,
        startup_delta=args.startup_delta,
        timing_verified=False, verification=args.verify)
    write_json(output/'conversion.json', manifest)
    try:
        images, manifest['input'] = decode_video(source, executables['ffmpeg'], work, probe, picture, sound)
        states, quality = convert_frames(images, work)
        write_video_preview(images, states, quality, output/'video-preview.png')
        write_json(output/'video-quality.json', quality)
        ay_frames, audio = convert_audio(source, executables['ffmpeg'], work, picture, sound, len(states))
        write_json(output/'audio-quality.json', audio)
        raw, codec = encode(states, ay_frames)
        (work/'stream.raw').write_bytes(raw)
        write_json(output/'codec.json', codec)
        builder = Builder(raw, states, Path(executables['zx0']), work/'zx0',
            fast_disk=fast, cached_seek=fast, interleaved=fast, inline_matches=args.inline_matches,
            startup_delta=args.startup_delta,fast_noop_scan=args.fast_noop_scan,irq_safe_paging=args.irq_safe_paging,static_cache_borders=args.static_cache_borders,carry_huffman=args.carry_huffman,register_fragments=args.register_fragments,cached_huffman_byte=args.cached_huffman_byte)
        ends = builder.automatic_ends(args.max_frames_per_disk)
        records = []
        start = 0
        for part, end in enumerate(ends, 1):
            print(f'Building disk {part}/{len(ends)}: frames {start}..{end-1}', flush=True)
            image, metadata = builder.volume(start, end, part)
            if image is None: raise ValueError('final disk exceeds capacity after checkpoint convergence')
            stem = f'{args.prefix}_part{part:02}'
            (output/(stem+'.trd')).write_bytes(image)
            write_json(output/(stem+'.json'), metadata)
            records.append(dict(file=stem+'.trd', metadata=stem+'.json', frames=end-start,
                frame_start=start, frame_end_exclusive=end, used_sectors=metadata['used_sectors'],
                free_sectors=metadata['free_sectors'], sha256=metadata['trd_sha256']))
            start = end
        write_json(output/'volumes.json', records)
        manifest.update(frames=len(states), ay_ticks=len(ay_frames), volumes=records,
            duration_seconds=len(states)*3/25, stream_sha256=sha(raw), states_sha256=sha(states.tobytes()))
        if args.verify != 'none':
            from profile_fap3 import verify_volumes
            timing = verify_volumes(builder, records, output, args.fuse if args.verify == 'fuse' else None,
                                    args.verification_timeout)
            manifest['timing_verified'] = timing['all_nominal_deadlines_met']
        else:
            write_json(output/'timing.json', dict(complete=False, all_nominal_deadlines_met=False,
                release=False, reason='Instruction and disk measurements skipped by --verify none'))
        manifest['complete'] = True
    except Exception as error:
        manifest['failure'] = f'{type(error).__name__}: {error}'
        write_json(output/'conversion.json', manifest)
        raise
    write_json(output/'conversion.json', manifest)
    print(f'Created {len(records)} TRD(s) in {output}', flush=True)
    print('Exact 8 1/3 fps: '+('verified in Fuse' if manifest['timing_verified'] else 'not verified; see timing.json'), flush=True)


if __name__ == '__main__':
    main()
