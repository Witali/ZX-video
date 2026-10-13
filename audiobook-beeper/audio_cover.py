"""Convert a supplied cover to an actual Spectrum screen with a loading footer."""
from pathlib import Path

import numpy as np
from PIL import Image,ImageDraw,ImageFont

from pcm_player import spectrum_bitmap_offset

COLORS=np.array([[0,0,0],[0,0,1],[1,0,0],[1,0,1],[0,1,0],[0,1,1],[1,1,0],[1,1,1]],dtype=float)


def encode(image):
    """Choose one legal ink/paper/BRIGHT pair per8x8 cell, without dithering text.

    Ink and paper share one BRIGHT bit. Exhaustive pair selection minimizes
    pixel squared error; bitmap addressing uses the real interleaved layout.
    """
    pixels=np.asarray(image.convert('RGB'),dtype=float)
    assert pixels.shape==(192,256,3)
    output=bytearray(6912)
    for cy in range(24):
        for cx in range(32):
            tile=pixels[cy*8:cy*8+8,cx*8:cx*8+8].reshape(64,3)
            best=None
            for bright,intensity in ((0,205),(1,255)):
                palette=COLORS*intensity
                distances=np.sum((tile[:,None,:]-palette[None,:,:])**2,axis=2)
                for ink in range(8):
                    for paper in range(ink,8):
                        select=distances[:,ink]<=distances[:,paper]
                        cost=float(np.sum(np.minimum(distances[:,ink],distances[:,paper])))
                        if best is None or cost<best[0]:best=(cost,ink|paper<<3|bright<<6,select)
            _,attribute,mask=best
            output[6144+cy*32+cx]=attribute
            for row,value in enumerate(np.packbits(mask.reshape(8,8),axis=1).ravel()):
                output[spectrum_bitmap_offset(cx,cy*8+row)]=int(value)
    return bytes(output)


def render(screen):
    """Independent visible preview of all6912 screen bytes."""
    assert len(screen)==6912
    rgb=np.empty((192,256,3),dtype='u1')
    for y in range(192):
        for x in range(256):
            attribute=screen[6144+y//8*32+x//8]
            bit=screen[spectrum_bitmap_offset(x//8,y)]&(128>>(x&7))
            color=attribute&7 if bit else attribute>>3&7
            rgb[y,x]=COLORS[color]*(255 if attribute&64 else 205)
    return Image.fromarray(rgb)


def prepare(path=None,*,title='AUDIO DISK'):
    """Reserve the bottom32 pixels before encoding the image, then install
    an exact ROM-font/status area and a full-width outlined progress bar.
    A supplied SCR retains its top160 pixels verbatim.
    """
    if path and Path(path).suffix.lower()=='.scr':
        screen=bytearray(Path(path).read_bytes())
        if len(screen)!=6912:raise ValueError('Spectrum cover must contain6912 bytes')
    else:
        image=Image.new('RGB',(256,192),'black')
        if path:
            source=Image.open(path).convert('RGB').resize((256,192),Image.Resampling.LANCZOS)
            image.paste(source.crop((0,0,256,160)),(0,0))
        else:
            draw=ImageDraw.Draw(image);font=ImageFont.load_default(size=20)
            box=draw.textbbox((0,0),title,font=font)
            draw.text((max(8,(256-box[2])/2),65),title,font=font,fill='white')
        screen=bytearray(encode(image))
    for y in range(160,192):
        for x in range(32):screen[spectrum_bitmap_offset(x,y)]=255 if y in (176,183) else 0
    screen[6144+20*32:]=bytes([7]*128)
    screen[6144+22*32:6144+23*32]=bytes([4]*32)
    return bytes(screen)
