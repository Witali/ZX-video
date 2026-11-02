"""Independently validate SCR address order, attributes, shared footer and PNGs.

Pillow reads PNGs independently of compile.mjs. This is artwork verification;
emulator presentation and native player timing are separate qualifications.
"""
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image

from sanitize_sources import chunks, NONVISUAL


ROOT = Path(__file__).resolve().parent


def digest(data):
    return sha256(data).hexdigest()


def verify():
    compiled = json.loads((ROOT / 'compiled.json').read_text())
    assert len(compiled['images']) == 14
    wordmark_bytes = (ROOT / 'wordmark-mask.json').read_bytes()
    wordmark = json.loads(wordmark_bytes)
    assert wordmark['width'] == 256 and wordmark['height'] == 32
    expected_footer = [bytes.fromhex(row) for row in wordmark['rows']]
    assert len(expected_footer) == 32 and all(len(row) == 32 for row in expected_footer)
    sanitized = json.loads((ROOT / 'source-sanitization.json').read_text())
    source_records = {item['source']: item for item in sanitized['images']}
    results = []
    for item in compiled['images']:
        name = item['name']
        screen = (ROOT / f'{name}.scr').read_bytes()
        source = (ROOT / 'sources' / f'{name}.png').read_bytes()
        assert len(screen) == 6912 and digest(screen) == item['scr_sha256']
        assert digest(source) == item['source_sha256']
        assert not any(kind in NONVISUAL for kind, _, _ in chunks(source))
        source_image = Image.open(ROOT / 'sources' / f'{name}.png')
        record = source_records[f'sources/{name}.png']
        assert digest(source_image.tobytes()) == record['decoded_pixel_sha256']
        assert digest(source) == record['published_source_sha256']
        assert all(not attr & 128 for attr in screen[6144:]), 'FLASH is forbidden'
        assert 0 <= item['border'] <= 7
        decoded = []
        for y in range(192):
            for x in range(256):
                # Independent explicit divisions preserve Spectrum's thirds,
                # character-row interleave and within-character scanline order.
                offset = (y % 8) * 256 + ((y // 8) % 8) * 32 + (y // 64) * 2048 + x // 8
                attr = screen[6144 + (y // 8) * 32 + x // 8]
                is_ink = screen[offset] & (128 >> (x % 8))
                color = attr & 7 if is_ink else (attr >> 3) & 7
                level = 255 if attr & 64 else 205
                decoded.append((level if color & 2 else 0,
                                level if color & 4 else 0,
                                level if color & 1 else 0))
        native = Image.open(ROOT / f'{name}-native.png').convert('RGB')
        assert native.size == (256, 192)
        assert native.tobytes() == bytes(c for pixel in decoded for c in pixel)
        for row in range(24):
            for column in range(32):
                colors = {decoded[(row * 8 + dy) * 256 + column * 8 + dx]
                          for dy in range(8) for dx in range(8)}
                assert len(colors) <= 2
        for y in range(160, 192):
            offset = (y % 8) * 256 + ((y // 8) % 8) * 32 + (y // 64) * 2048
            assert screen[offset:offset + 32] == expected_footer[y - 160]
            for column in range(32):
                attr = screen[6144 + (y // 8) * 32 + column]
                assert (attr >> 3) & 7 == 0 and attr & 7 != 0
                assert attr & 64 and (y >= 176 or attr & 7 == 7)
        preview = Image.open(ROOT / f'{name}-preview.png').convert('RGB')
        assert preview.size == (768, 576)
        assert preview.tobytes() == native.resize((768, 576), Image.Resampling.NEAREST).tobytes()
        results.append(dict(name=name, bytes=len(screen), scr_sha256=digest(screen),
                            native_pixels_checked=256 * 192, preview_pixels_checked=768 * 576,
                            attribute_cells_checked=768, flash_cells=0, exact_shared_wordmark=True,
                            sanitized_source_pixel_hash_matches=True, border=item['border']))
    report = dict(scope='Independent native artwork validation; TRD and emulator timing not assessed',
                  wordmark_mask_sha256=digest(wordmark_bytes), images=results)
    (ROOT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps(dict(screens=len(results), native_pixels_checked=sum(r['native_pixels_checked'] for r in results),
                          preview_pixels_checked=sum(r['preview_pixels_checked'] for r in results),
                          attribute_cells_checked=sum(r['attribute_cells_checked'] for r in results),
                          exact_shared_wordmark=True, flash_cells=0)))


if __name__ == '__main__':
    verify()
