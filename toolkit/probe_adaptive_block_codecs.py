"""Compare lossless outer codecs on exact cold-start blocks from three TRDs.

This is a PC storage experiment, not a mixed-codec player or a speed claim.
The fixed-bootstrap sector projections exclude new decoder/bootstrap bytes.
Raw DEFLATE is reported separately: no small, resumable Z80 decoder is built.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import tempfile
import zlib

from benchmark_bank_local_zx0 import disk_blocks
import disk_layout
import zx0_codec
import zx0_speed


CODECS = ('zx0', 'zx0_min2', 'zx0_min3', 'zx0_min4', 'zx1', 'lzsa2',
          'rle', 'stored', 'deflate')
LIGHT = CODECS[:-1]
ZX0_ONLY = CODECS[:4]


def sha(data):
    return sha256(data).hexdigest()


def rle_encode(raw):
    """Greedy byte RLE, NOT an optimal parser. Tokens cover 1..128 bytes.

    Low tag: tag+1 literal bytes. High tag: (tag&127)+1 copies of next byte.
    The encoder uses runs of at least three; output length comes from header.
    """
    out = bytearray()
    literal = bytearray()

    def flush():
        if literal:
            out.append(len(literal)-1)
            out.extend(literal)
            literal.clear()

    at = 0
    while at < len(raw):
        end = at+1
        while end < min(len(raw), at+128) and raw[end] == raw[at]:
            end += 1
        if end-at >= 3:
            flush()
            out.extend((128+end-at-1, raw[at]))
            at = end
        else:
            literal.append(raw[at])
            at += 1
            if len(literal) == 128:
                flush()
    flush()
    return bytes(out)


def rle_decode(packed, expected_size):
    out = bytearray()
    at = 0
    while at < len(packed):
        tag = packed[at]
        at += 1
        count = (tag & 127)+1
        consumed = 1 if tag & 128 else count
        if at+consumed > len(packed) or len(out)+count > expected_size:
            raise ValueError('invalid RLE token or output bound')
        out.extend(packed[at:at+1]*count if tag & 128 else packed[at:at+count])
        at += consumed
    if len(out) != expected_size:
        raise ValueError('incomplete RLE output')
    return bytes(out)


def geometry(size, start):
    logical = (size+255)//256
    physical = disk_layout.required_sectors(logical, start % 16)
    used = start-16+physical
    return dict(stream_bytes=size, logical_video_sectors=logical,
                physical_video_sectors=physical, fixed_bootstrap_used_sectors=used,
                free_sectors=2544-used, fits_fixed_bootstrap=used <= 2544)


def selection(rows, allowed, *, tag_bytes, mixed=False):
    selected = []
    for row in rows:
        candidates = [name for name in allowed if row['candidates'][name]['slot_fits']]
        if not candidates:
            return None
        selected.append(min(candidates, key=lambda name: row['candidates'][name]['bytes']))
    size = sum(row['candidates'][name]['bytes']+4+tag_bytes
               for row, name in zip(rows, selected))
    return dict(stream_bytes=size, selected_counts=dict(Counter(selected)),
                selected_codecs=selected, additional_tag_bytes_per_block=tag_bytes,
                mixed_codec_format_required=mixed)


def summarize_volume(volume):
    rows = volume['blocks']
    start = volume['video_start_sector']
    base = sum(row['candidates']['zx0']['bytes']+4 for row in rows)
    summary = dict(blocks=len(rows), candidates={})
    for codec in CODECS:
        sizes = [row['candidates'][codec]['bytes'] for row in rows]
        summary['candidates'][codec] = dict(
            **geometry(sum(sizes)+4*len(rows), start),
            delta_from_zx0_bytes=sum(sizes)+4*len(rows)-base,
            smaller_blocks=sum(n < row['candidates']['zx0']['bytes']
                               for n, row in zip(sizes, rows)),
            slot_oversize_blocks=sum(not row['candidates'][codec]['slot_fits'] for row in rows),
            largest_payload_bytes=max(sizes, default=0))
    choices = (('zx0_tokenizations', ZX0_ONLY, 0, False),
               ('light_optimistic_zero_tag', LIGHT, 0, True),
               ('light_explicit_tag', LIGHT, 1, True),
               ('including_deflate_zero_tag', CODECS, 0, True),
               ('including_deflate_explicit_tag', CODECS, 1, True))
    summary['size_selections'] = {}
    for name, allowed, tag, mixed in choices:
        selected = selection(rows, allowed, tag_bytes=tag, mixed=mixed)
        if selected is None:
            raise AssertionError('baseline ZX0 must fit slots')
        selected.update(geometry(selected['stream_bytes'], start))
        selected['delta_from_zx0_bytes'] = selected['stream_bytes']-base
        summary['size_selections'][name] = selected
    volume['summary'] = summary


class ExternalCodec:
    def __init__(self, name, encoder, decoder, revision):
        self.name = name
        self.encoder, self.decoder = encoder.resolve(), decoder.resolve()
        self.encflags = ['-f'] if name == 'zx1' else ['-r', '-f', '2', '--prefer-ratio']
        self.decflags = ['-f'] if name == 'zx1' else ['-d', '-r', '-f', '2']
        self.identity = dict(source_revision=revision, encoder_sha256=sha(encoder.read_bytes()),
            decoder_sha256=sha(decoder.read_bytes()), encoder_flags=self.encflags,
            decoder_flags=self.decflags)

    def encode_verified(self, raw, cached, cache):
        with tempfile.TemporaryDirectory(dir=cache) as tmp:
            src, packed, restored = [Path(tmp)/name for name in ('in.raw', 'out.bin', 'decoded.raw')]
            if cached is None:
                src.write_bytes(raw)
                subprocess.run([str(self.encoder), *self.encflags, str(src), str(packed)],
                               check=True, capture_output=True)
            else:
                packed.write_bytes(cached)
            subprocess.run([str(self.decoder), *self.decflags, str(packed), str(restored)],
                           check=True, capture_output=True)
            if restored.read_bytes() != raw:
                raise AssertionError(f'{self.name} author PC decoder differs')
            return packed.read_bytes()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('directory', 'cache', 'output', 'zx1_encoder', 'zx1_decoder', 'lzsa2'):
        parser.add_argument('--'+name.replace('_', '-'), type=Path, required=True)
    parser.add_argument('--zx1-revision', required=True)
    parser.add_argument('--lzsa2-revision', required=True)
    parser.add_argument('--jobs', type=int, choices=range(1, 5), default=2)
    args = parser.parse_args()
    cache = args.cache.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    external = {
        'zx1': ExternalCodec('zx1', args.zx1_encoder, args.zx1_decoder, args.zx1_revision),
        'lzsa2': ExternalCodec('lzsa2', args.lzsa2, args.lzsa2, args.lzsa2_revision),
    }
    identity = dict(probe_sha256=sha(Path(__file__).read_bytes()),
                    zx0_speed_sha256=sha(Path(zx0_speed.__file__).read_bytes()),
                    zlib_version=zlib.ZLIB_VERSION, zlib_runtime=zlib.ZLIB_RUNTIME_VERSION,
                    deflate=dict(level=9, wbits=-13, memLevel=8, strategy=zlib.Z_DEFAULT_STRATEGY),
                    external={name: codec.identity for name, codec in external.items()})
    report = dict(scope=__doc__, complete=False, release=False, player_changed=False,
        player_delta_tstates=0, speed_measured=False, provenance=identity,
        verification='ZX0 Python decoder; author ZX1/LZSA2 PC decoders; Python RLE; zlib DEFLATE. Byte exact, not Z80.',
        fixed_bootstrap_only=True, extra_decoder_bootstrap_bytes=None,
        codec_dispatch_tstates=None, all_frame_deadlines_verified=False,
        assumptions=['same decoded blocks including cold-start edits and boundaries',
                     '4-byte baseline header, optional 1-byte codec tag on every block',
                     'zero-tag mixed case is optimistic; no container implementation',
                     'payload and decoded block must each fit an 8192-byte half-slot',
                     'baseline bootstrap retained only for sector projection',
                     'per-block size minimum among tested candidates; no speed or global-optimum claim'],
        volumes=[])

    def save():
        for volume in report['volumes']:
            summarize_volume(volume)
        args.output.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')

    def worker(item):
        index, (source, raw) = item
        row = dict(index=index, decoded_bytes=len(raw), decoded_sha256=sha(raw), candidates={})
        for codec in CODECS:
            key = sha(json.dumps(dict(identity=identity, codec=codec, raw=sha(raw),
                                     source=sha(source)), sort_keys=True).encode())
            filename = key+'.'+codec
            path = cache/filename
            packed = path.read_bytes() if path.exists() else None
            if codec in external:
                packed = external[codec].encode_verified(raw, packed, cache)
            else:
                if packed is None:
                    if codec == 'zx0':
                        packed = source
                    elif codec.startswith('zx0_min'):
                        packed = zx0_speed.rewrite(source, int(codec[-1]))
                    elif codec == 'rle':
                        packed = rle_encode(raw)
                    elif codec == 'stored':
                        packed = raw
                    else:
                        compressor = zlib.compressobj(**identity['deflate'])
                        packed = compressor.compress(raw)+compressor.flush()
                if codec.startswith('zx0'):
                    restored = zx0_codec.decompress(packed, limit=len(raw))
                elif codec == 'rle':
                    restored = rle_decode(packed, len(raw))
                elif codec == 'stored':
                    restored = packed
                else:
                    decoder = zlib.decompressobj(wbits=-13)
                    restored = decoder.decompress(packed)+decoder.flush()
                    if not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
                        raise AssertionError('DEFLATE stream not consumed exactly')
                if restored != raw:
                    raise AssertionError(f'{codec} round trip differs')
                if codec == 'zx0' and packed != source:
                    raise AssertionError('cached baseline differs')
            if not path.exists():
                with tempfile.NamedTemporaryFile(dir=cache, delete=False) as stream:
                    stream.write(packed)
                    temporary = Path(stream.name)
                temporary.replace(path)
            row['candidates'][codec] = dict(bytes=len(packed), sha256=sha(packed),
                slot_fits=1 <= len(packed) <= 8192 and 1 <= len(raw) <= 8192,
                cache_file=filename)
        return row

    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        for part in (1, 2, 3):
            meta, stream, blocks = disk_blocks(args.directory, part)
            if meta['used_sectors'] != geometry(len(stream), meta['video_start_sector'])['fixed_bootstrap_used_sectors']:
                raise AssertionError('baseline sector projection differs')
            volume = dict(part=part, trd_sha256=meta['trd_sha256'], raw_sha256=meta['raw_sha256'],
                states_sha256=meta['states_sha256'], frame_start=meta['frame_start'],
                frame_end_exclusive=meta['frame_end_exclusive'], stream_sha256=sha(stream),
                stream_bytes=len(stream), video_start_sector=meta['video_start_sector'],
                blocks_expected=len(blocks), complete=False, blocks=[])
            report['volumes'].append(volume)
            for row in pool.map(worker, enumerate(blocks)):
                volume['blocks'].append(row)
                if len(volume['blocks']) % 20 == 0:
                    save()
                    print(f"Disk {part}: {len(volume['blocks'])}/{len(blocks)} blocks, all codecs byte exact", flush=True)
            volume['complete'] = True
            save()
            print(json.dumps(dict(part=part, candidates=volume['summary']['candidates'],
                choices={name: {k:v for k,v in choice.items() if k != 'selected_codecs'}
                         for name, choice in volume['summary']['size_selections'].items()})), flush=True)
    report['complete'] = True
    save()


if __name__ == '__main__':
    main()
