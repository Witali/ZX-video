"""Repeatable title, ending and thumbnail layouts using checked-in native art."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
GOLD = '#e2c689'
PAPER = '#eee6d7'
INK = '#0c1119'
FONT = ROOT / 'music-menu/artwork/font/Cinzel.ttf'
URL_FONT = Path('C:/Windows/Fonts/consola.ttf')


def font(size):
    return ImageFont.truetype(str(FONT), size)


def title(output, ending=False):
    canvas = Image.new('RGB', (1920, 1080), INK)
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((0, 0, 1919, 7), fill=GOLD)
    # Original 256x192 Spectrum render, exact integer enlargement. The native
    # Cinzel footer is retained so this is recognizably the actual demo art.
    art = Image.open(ROOT / 'music-menu/artwork/city-native.png').convert('RGB')
    art = art.resize((1024, 768), Image.Resampling.NEAREST)
    canvas.paste(art, (824, 156))
    draw.rectangle((823, 155, 1848, 924), outline='#3e4146', width=2)
    draw.text((80, 190), 'CLAIR OBSCUR', font=font(33), fill=GOLD, anchor='ls')
    draw.text((72, 338), 'EXPEDITION', font=font(91), fill=PAPER, anchor='ls')
    draw.text((72, 510), '33', font=font(184), fill=GOLD, anchor='ls')
    draw.line((80, 561, 720, 561), fill='#75684c', width=2)
    draw.text((80, 630), 'DEMO FOR', font=font(34), fill=GOLD, anchor='ls')
    draw.text((77, 695), 'ZX SPECTRUM', font=font(46), fill=PAPER, anchor='ls')
    draw.text((80, 742), '128K  /  AY MUSIC', font=font(27), fill=GOLD, anchor='ls')
    for i, color in enumerate(('#d83d47', '#e6cf43', '#4fbf80', '#4eb9ce')):
        x = 80 + i * 38
        draw.polygon([(x, 796), (x + 31, 796), (x + 51, 772), (x + 20, 772)], fill=color)
    subtitle = 'PLAY IT IN YOUR BROWSER' if ending else 'LUMIÈRE  +  ALICIA'
    draw.text((80, 872), subtitle, font=font(27), fill=PAPER, anchor='ls')
    draw.line((80, 969, 1840, 969), fill='#34373d', width=2)
    draw.text((80, 1023), 'witali.github.io/ZX-video',
              font=ImageFont.truetype(str(URL_FONT), 29), fill=PAPER, anchor='ls')
    draw.text((1840, 1023), '18 NATIVE SCREENS', font=font(23), fill=GOLD, anchor='rs')
    canvas.save(output)


def create(folder):
    folder.mkdir(parents=True, exist_ok=True)
    title(folder / 'opening.png')
    title(folder / 'ending.png', ending=True)
    image = Image.open(folder / 'opening.png')
    image.resize((1280, 720), Image.Resampling.LANCZOS).save(folder / 'thumbnail.png')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    create(parser.parse_args().output)
