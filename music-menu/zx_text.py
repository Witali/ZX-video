"""ASCII menu strings and standard Spectrum PRINT AT control bytes.

Glyphs are provided by the user's ROM. No font bitmap is packaged on disk.
"""
MENU_LINES = (
    (1,6,'SPECTRUM MUSIC'),
    (4,2,'CLAIR OBSCUR: EXPEDITION 33'),
    (9,4,'1  LUMIERE'),
    (13,4,'2  ALICIA'),
    (17,5,'AY ONLY / SOFT BASS'),
    (19,2,'READY'),
    (19,10,'LOADING'),
    (19,20,'PLAYING'),
    (21,1,'1/2  6/7+ENTER  SPACE: STOP'),
)


def menu_stream():
    data = bytearray()
    for row,column,text in MENU_LINES:
        if not 0<=row<22 or not 0<=column<32 or column+len(text)>32:
            raise ValueError('Text does not fit the upper Spectrum display')
        data.extend((22,row,column))
        data.extend(text.encode('ascii'))
    data.append(255)
    return bytes(data)
