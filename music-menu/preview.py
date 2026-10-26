"""Render the actual Z80 menu framebuffer, including attributes and cursor."""
import json
from pathlib import Path

from PIL import Image

from build import ROOT, spectrum_bitmap_offset
from verify import Machine


def render(output):
    output = Path(output)
    meta = json.loads((output/'build.json').read_text())
    machine = Machine((output/'assembly/player.bin').read_bytes(), meta['player_labels'])
    machine.run_to(meta['player_labels']['start'], [meta['player_labels']['menu_ready']], 500000)
    memory = machine.cpu.memory
    im = Image.new('RGB', (256, 192))
    for y in range(192):
        for x in range(256):
            attr = memory[0x5800+(y//8)*32+x//8]
            bit = memory[0x4000+spectrum_bitmap_offset(x//8, y)] & (128 >> (x&7))
            colour = attr&7 if bit else (attr >> 3)&7
            level = 255 if attr&64 else 205
            im.putpixel((x,y), (level if colour&2 else 0, level if colour&4 else 0, level if colour&1 else 0))
    im.resize((768,576), Image.Resampling.NEAREST).save(output/'menu.png')
    return im


if __name__ == '__main__':
    render(ROOT/'build/music-menu')
