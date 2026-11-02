"""Independently decode the three Spectrum proposal screens and verify PNGs.

This is image-format validation, not native player timing qualification.
Pillow reads the PNGs independently of the compiler's hand-written PNG codec.
"""
from hashlib import sha256
import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent


def digest(data):
    return sha256(data).hexdigest()


def verify():
    compiled = json.loads((ROOT / 'compiled.json').read_text())
    wordmark_bytes = (ROOT / 'wordmark-mask.json').read_bytes()
    wordmark = json.loads(wordmark_bytes)
    assert compiled['wordmark_mask_sha256'] == digest(wordmark_bytes)
    assert [a['name'] for a in compiled['images']] == ['paintress', 'sirene', 'gestral-village']
    expected_footer = [bytes.fromhex(row) for row in wordmark['rows']]
    results = []
    for item in compiled['images']:
        name = item['name']
        screen = (ROOT / f'{name}.scr').read_bytes()
        assert len(screen) == 6912
        assert digest(screen) == item['scr_sha256']
        assert digest((ROOT / 'sources' / f'{name}.png').read_bytes()) == item['source_sha256']
        assert all(not attr & 128 for attr in screen[6144:]), 'FLASH is forbidden'
        assert 0 <= item['border'] <= 7
        decoded = []
        for y in range(192):
            for x in range(256):
                # Character rows are interleaved: line-within-character,
                # character-row-within-third, then the 64-scanline third.
                byte_offset = (y % 8) * 256 + ((y // 8) % 8) * 32 + (y // 64) * 2048 + x // 8
                attr = screen[6144 + (y // 8) * 32 + x // 8]
                ink = screen[byte_offset] & (0x80 >> (x % 8))
                color = attr & 7 if ink else (attr >> 3) & 7
                level = 255 if attr & 64 else 205
                decoded.append((level if color & 2 else 0,
                                level if color & 4 else 0,
                                level if color & 1 else 0))
        native = Image.open(ROOT / f'{name}-native.png').convert('RGB')
        assert native.size == (256, 192)
        assert native.tobytes() == bytes(c for pixel in decoded for c in pixel), 'Native PNG differs from actual SCR'
        for row in range(24):
            for column in range(32):
                colors = {decoded[(row * 8 + dy) * 256 + column * 8 + dx]
                          for dy in range(8) for dx in range(8)}
                assert len(colors) <= 2
        for y in range(160, 192):
            base = (y % 8) * 256 + ((y // 8) % 8) * 32 + (y // 64) * 2048
            assert screen[base:base + 32] == expected_footer[y - 160], 'Shared font shape changed'
        preview = Image.open(ROOT / f'{name}-preview.png').convert('RGB')
        assert preview.size == (768, 576)
        assert preview.tobytes() == native.resize((768, 576), Image.Resampling.NEAREST).tobytes()
        results.append(dict(name=name, bytes=len(screen), native_pixels_checked=256 * 192,
                            preview_pixels_checked=768 * 576, attribute_cells_checked=768,
                            flash_cells=0, exact_shared_wordmark=True, border=item['border'],
                            scr_sha256=digest(screen)))
    report = dict(scope='Independent SCR/PNG/attribute/wordmark validation; TRD integration pending',
                  wordmark_mask_sha256=digest(wordmark_bytes), images=results)
    (ROOT / 'verification.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    verify()
