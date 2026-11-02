"""Remove nonvisual PNG metadata without changing image data or decoded pixels.

Original files stay in the ignored task-local .tmp/artwork-originals directory.
The report contains hashes and chunk names only, never metadata contents.
"""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import struct
import zlib

from PIL import Image


ROOT = Path(__file__).resolve().parent
REPORT = ROOT / 'source-sanitization.json'
NONVISUAL = {b'caBX', b'tEXt', b'zTXt', b'iTXt', b'eXIf', b'tIME'}


def digest(data):
    return sha256(data).hexdigest()


def chunks(data):
    assert data[:8] == b'\x89PNG\r\n\x1a\n'
    offset = 8
    while offset < len(data):
        size = struct.unpack_from('>I', data, offset)[0]
        end = offset + size + 12
        assert end <= len(data)
        kind = data[offset + 4:offset + 8]
        payload = data[offset + 8:offset + size + 8]
        assert zlib.crc32(kind + payload) == struct.unpack_from('>I', data, end - 4)[0]
        yield kind, payload, data[offset:end]
        offset = end
    assert offset == len(data)


def sanitize():
    compiled = json.loads((ROOT / 'compiled.json').read_text())
    assert len(compiled['images']) == 14
    previous = json.loads(REPORT.read_text())['images'] if REPORT.exists() else []
    records = {item['source']: item for item in previous}
    for asset in compiled['images']:
        name = asset['name']
        file = ROOT / 'sources' / f'{name}.png'
        raw = file.read_bytes()
        entries = list(chunks(raw))
        clean = raw[:8] + b''.join(chunk for kind, _, chunk in entries if kind not in NONVISUAL)
        omitted = [kind.decode('ascii') for kind, _, _ in entries if kind in NONVISUAL]
        if omitted:
            backup = ROOT.parents[1] / '.tmp' / 'artwork-originals' / file.name
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                assert backup.read_bytes() == raw, 'Preserve earlier original; investigate changes'
            else:
                backup.write_bytes(raw)
            before = Image.open(BytesIO(raw))
            after = Image.open(BytesIO(clean))
            assert before.size == after.size and before.mode == after.mode
            assert before.tobytes() == after.tobytes()
            old_idat = b''.join(payload for kind, payload, _ in entries if kind == b'IDAT')
            new_idat = b''.join(payload for kind, payload, _ in chunks(clean) if kind == b'IDAT')
            assert old_idat == new_idat
            record = dict(source=f'sources/{name}.png', original_generated_sha256=digest(raw),
                          published_source_sha256=digest(clean), omitted_chunks=omitted,
                          omitted_bytes=len(raw) - len(clean), idat_bytes=len(old_idat),
                          idat_sha256=digest(old_idat), idat_preserved_byte_exact=True,
                          source_width=before.width, source_height=before.height,
                          decoded_mode=before.mode, decoded_pixels_checked=before.width * before.height,
                          decoded_pixel_sha256=digest(before.tobytes()), decoded_pixels_preserved=True)
            file.write_bytes(clean)
            records[record['source']] = record
        asset['source_sha256'] = digest(file.read_bytes())
    report = dict(scope='Nonvisual metadata excluded; IDAT and decoded pixels unchanged; originals local only',
                  images=list(records.values()))
    REPORT.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8', newline='\n')
    (ROOT / 'compiled.json').write_text(json.dumps(compiled, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps(dict(sources=len(compiled['images']), sanitized_sources=len(records),
                          all_decoded_pixels_preserved=all(r['decoded_pixels_preserved'] for r in records.values()))))


if __name__ == '__main__':
    sanitize()
