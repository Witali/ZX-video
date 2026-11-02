"""Decode the documented uncompressed standard-screen stereo FMF subset.

Format: https://sourceforge.net/p/fuse-emulator/wiki/FMF%20File%20Format/
Slices contain bitmap and per-raster-line attribute bytes, including border.
Their coordinates are byte columns in a 320x240 image, not Spectrum SCR order.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import wave
import numpy as np
from PIL import Image


def blocks(blob):
    assert blob[:8] == b'FMF_V1eU' and blob[8:12] == b'\x01$BP'
    rate = int.from_bytes(blob[12:14], 'little')
    channels = {ord('M'): 1, ord('S'): 2}[blob[14]]
    pos, frame = 16, 0
    bitmap = np.zeros((240, 40), dtype=np.uint8)
    attributes = np.zeros_like(bitmap)

    def rle(count):
        nonlocal pos
        result = bytearray()
        while len(result) < count:
            value = blob[pos]
            pos += 1
            result.append(value)
            if len(result) < count and blob[pos] == value:
                result.extend(bytes([value]) * (blob[pos + 1] + 1))
                pos += 2
        assert len(result) == count, 'Invalid FMF run length'
        return np.frombuffer(result, dtype=np.uint8)

    while pos < len(blob):
        tag = chr(blob[pos])
        if tag == '$':
            x = blob[pos + 1]
            y = int.from_bytes(blob[pos + 2:pos + 4], 'little')
            width = blob[pos + 4]
            height = int.from_bytes(blob[pos + 5:pos + 7], 'little')
            assert 0 <= x < x + width <= 40 and 0 <= y < y + height <= 240
            pos += 7
            bitmap[y:y + height, x:x + width] = rle(width * height).reshape(height, width)
            attributes[y:y + height, x:x + width] = rle(width * height).reshape(height, width)
        elif tag == 'S':
            assert blob[pos + 1] == ord('P')
            assert int.from_bytes(blob[pos + 2:pos + 4], 'little') == rate
            assert blob[pos + 4] == blob[14]
            count = int.from_bytes(blob[pos + 5:pos + 7], 'little') + 1
            pos += 7
            data = blob[pos:pos + count * channels * 2]
            assert len(data) == count * channels * 2
            pos += len(data)
            yield 'audio', frame, data, (rate, channels)
        elif tag in ('N', 'X'):
            yield 'frame', frame, bitmap, attributes
            if tag == 'X':
                pos += 1
                assert pos == len(blob), 'Trailing FMF data'
                return
            assert blob[pos + 1:pos + 4] == b'\x01$B', 'Mixed/skipped frame timing'
            frame += 1
            pos += 4
        else:
            raise ValueError(f'Unexpected FMF tag {tag!r} at {pos}')
    raise ValueError('FMF has no end marker')


def rgb(bitmap, attributes, frame):
    bits = np.unpackbits(bitmap, axis=1)
    attr = np.repeat(attributes, 8, axis=1)
    if frame // 16 & 1:
        bits = bits ^ (attr >> 7)
    color = np.where(bits, attr & 7, (attr >> 3) & 7)
    level = np.where(attr & 64, 255, 205).astype(np.uint8)
    return np.stack([np.where(color & mask, level, 0)
                     for mask in (2, 4, 1)], axis=2).astype(np.uint8)


def decode(movie, output):
    output.mkdir(parents=True, exist_ok=True)
    command = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pixel_format', 'rgb24',
        '-video_size', '480x270', '-framerate', '3546900/70908', '-i', '-',
        '-an', '-c:v', 'libx264rgb', '-crf', '0', '-preset', 'veryfast',
        str(output / 'native-lossless.mkv')]
    log = (output / 'decode-ffmpeg.log').open('wb')
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=log)
    chunks, sounds, cursor, frames = [], [], 0, 0
    sample_rate = channels = None
    root = Path(__file__).resolve().parents[2]
    art = root / 'music-menu/artwork'
    expected = {}
    for path in [*art.glob('*-native.png'), *art.joinpath('proposals').glob('*-native.png')]:
        expected[hashlib.sha256(Image.open(path).convert('RGB').tobytes()).digest()] = path.stem.removesuffix('-native')
    assert len(expected) == 18
    matched = {}
    try:
        for kind, frame, data, other in blocks(movie.read_bytes()):
            if kind == 'audio':
                sample_rate, channels = other
                count = len(data) // (2 * channels)
                chunks.append([frame, cursor, count])
                cursor += count
                sounds.append(data)
            else:
                image = rgb(data, other, frame)
                if frame % 50 == 0:
                    name = expected.get(hashlib.sha256(image[24:216, 32:288].tobytes()).digest())
                    if name and name not in matched:
                        matched[name] = frame
                # Extend the actual hardware border to 16:9. Every source pixel
                # is still one pixel here; the final encoder enlarges it 4x.
                canvas = np.empty((270, 480, 3), dtype=np.uint8)
                canvas[:] = image[0, 0]
                canvas[15:255, 80:400] = image
                encoder.stdin.write(canvas.tobytes())
                if frame % 500 == 0:
                    print('Decoded native field', frame, flush=True)
                frames += 1
        encoder.stdin.close()
        assert encoder.wait() == 0, 'Lossless encoder failed'
    except BaseException:
        encoder.kill()
        raise
    finally:
        log.close()
    with wave.open(str(output / 'native.wav'), 'wb') as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b''.join(sounds))
    metadata = dict(frames=frames, sample_rate=sample_rate, channels=channels,
                    audio_samples=cursor, chunks=chunks, exact_native_artwork_matches=matched)
    assert len(matched) == 18, ('Missing artwork in actual FMF capture', sorted(matched))
    (output / 'decoded.json').write_text(json.dumps(metadata) + '\n')
    return metadata


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('movie', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    decode(args.movie, args.output)
