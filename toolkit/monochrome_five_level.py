"""Host-only fixed black/BRIGHT-white quantization for the existing CB41 ABI.

Use encoded-RGB Rec.709 luma (not linear-light luminance), then quantize to
five area coverages. No per-cell palette selection or contrast stretch.
"""
import numpy as np

import five_level_dither as five


def luma_numerator(image):
    image = np.asarray(image)
    if image.shape != (96, 128, 3) or image.dtype != np.uint8:
        raise ValueError('expected uint8 RGB 128x96')
    return image.astype(np.uint32) @ np.array([2126, 7152, 722], dtype=np.uint32)


def encode(image):
    # Round 4*Y/255 to nearest, with exact integer coefficients summing to 1.
    levels = ((8*luma_numerator(image)+2550000)//5100000).astype(np.uint8)
    levels[:12] = 0
    levels[84:] = 0
    attrs = np.full(768, 0x47, dtype=np.uint8)
    # Preserve the existing static-border ABI; these pixels stay black.
    attrs[:96] = 1
    attrs[672:] = 1
    return five.pack_levels(levels)+attrs.tobytes()


def quality(image, state):
    levels = five.unpack_levels(bytes(state[:3840]))[12:84]
    source = luma_numerator(image)[12:84].astype(float)/10000
    return dict(luma_mse=float(np.mean((levels.astype(float)*255/4-source)**2)),
                solid_black_percent=float(100*np.mean(levels==0)),
                solid_white_percent=float(100*np.mean(levels==4)),
                level_counts=np.bincount(levels.ravel(), minlength=5).tolist())


def preview(images, states, frame_start, path):
    from PIL import Image, ImageDraw
    from build_zxv_trd import render_spectrum_screen
    indices = sorted(set(np.linspace(0, len(states)-1, 4, dtype=int)))
    sheet = Image.new('RGB', (768, len(indices)*218), '#202020')
    draw = ImageDraw.Draw(sheet)
    for row, index in enumerate(indices):
        source = images[index]
        gray = np.rint(luma_numerator(source)/10000).astype(np.uint8)
        rendered = render_spectrum_screen(*five.expand(states[index].tobytes()))
        assert np.array_equal(rendered[:,:,0], rendered[:,:,1])
        assert np.array_equal(rendered[:,:,1], rendered[:,:,2])
        assert set(np.unique(rendered)) <= {0, 255}
        panels = (Image.fromarray(source), Image.fromarray(gray).convert('RGB'), Image.fromarray(rendered))
        for column, (title, image) in enumerate(zip(('Source', 'Grayscale source', 'Spectrum monochrome'), panels)):
            draw.text((column*256+4, row*218+4), f'{frame_start+index}: {title}', fill='white')
            sheet.paste(image.resize((256,192), Image.Resampling.NEAREST), (column*256,row*218+22))
    sheet.save(path)
    return [frame_start+int(i) for i in indices]
