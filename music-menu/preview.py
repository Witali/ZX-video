"""Capture the real Fuse framebuffer and optionally authenticate stock ROM glyphs."""
import argparse
import json
from pathlib import Path
import re

from PIL import Image

from build import ROOT, spectrum_bitmap_offset, sha
from verify import Machine, boot, run_fuse
from zx_text import MENU_LINES


def render(output, *, fuse=None, rom=None):
    output = Path(output).resolve()
    meta = json.loads((output/'build.json').read_text())
    if fuse:
        screen = bytearray()
        # Four bounded cold-boot reads keep each Windows command below 32 KiB.
        # Only the requested 6912-byte display is read, never unrelated memory.
        for offset in range(0,6912,1728):
            count = min(1728,6912-offset)
            script = '\n'.join([f'br {meta["player_labels"]["ready"]}','com 1','pr 12345',
                *(f'pr [{0x4000+offset+i}]' for i in range(count)),'ex 77','end'])
            result,trace = run_fuse(fuse,output,script,timeout=60)
            assert result.returncode==77,('Fuse screen capture failed',result.returncode)
            values = [int(m.group(1),0) for m in re.finditer(rb'(?m)^(-?\d+|0x[\da-fA-F]+)\r*$',trace)]
            assert len(values)==count+1 and values[0]==12345
            screen.extend(values[1:])
        scope = 'Actual Fuse cold-boot display at ready, assembled from four bounded screen-memory reads.'
    else:
        if rom is None:
            raise ValueError('Use --fuse for an actual screen or --rom for native ROM-output-stub preview')
        font = rom.read_bytes()
        assert len(font)==16384
        machine = Machine((output/'assembly/player.bin').read_bytes(),meta['player_labels'],rom_font=font)
        boot(machine,(output/'ZX-Music-Menu.trd').read_bytes())
        screen = bytearray(machine.cpu.memory[0x4000:0x5B00])
        scope = 'Native Z80 with an explicit ROM-print stub and the supplied stock ROM glyphs.'
    matched = 0
    if rom:
        font = rom.read_bytes()
        assert len(font)==16384
        for row,column,text in MENU_LINES:
            for i,ch in enumerate(text):
                glyph = bytes(screen[spectrum_bitmap_offset(column+i,row*8+y)] for y in range(8))
                assert glyph==font[0x3C00+ord(ch)*8:0x3C00+ord(ch)*8+8],('ROM glyph mismatch',row,column+i,ch)
                matched += 1
    image = Image.new('RGB',(256,192))
    for y in range(192):
        for x in range(256):
            attr = screen[6144+(y//8)*32+x//8]
            bit = screen[spectrum_bitmap_offset(x//8,y)]&(128>>(x&7))
            colour = attr&7 if bit else (attr>>3)&7
            level = 255 if attr&64 else 205
            image.putpixel((x,y),(level if colour&2 else 0,level if colour&4 else 0,level if colour&1 else 0))
    image.resize((768,576),Image.Resampling.NEAREST).save(output/'menu.png')
    (output/'menu.scr').write_bytes(screen)
    report = dict(trd_sha256=meta['trd_sha256'],screen_sha256=sha(screen),
        stock_rom_glyphs_checked=matched,reference_rom_sha256=sha(rom.read_bytes()) if rom else None,
        rom_bundled=False,scope=scope)
    (output/'menu-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,indent=2))
    return image


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'build/music-menu-click-fix')
    parser.add_argument('--fuse',type=Path)
    parser.add_argument('--rom',type=Path)
    args = parser.parse_args()
    render(args.output,fuse=args.fuse,rom=args.rom)
