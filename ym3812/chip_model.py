"""Select the physical DAC/envelope target for one synchronous codec call.

The process environment also reaches all joined candidate-render workers.
Movie conversion already runs the common engine in its isolated PCM process.
Restore the prior selection after each call, including failed conversions.
"""
from contextlib import contextmanager
import os

CHOICES=('AY-3-8910','YM2149')


def current():
    value=os.environ.get('ZX_SOUND_CHIP','AY-3-8910')
    if value not in CHOICES:raise ValueError('chip must be AY-3-8910 or YM2149')
    return value


def render_name(chip=None):return 'YM' if (chip or current())=='YM2149' else 'AY'


@contextmanager
def select(chip):
    if chip not in CHOICES:raise ValueError('chip must be AY-3-8910 or YM2149')
    previous=os.environ.get('ZX_SOUND_CHIP')
    os.environ['ZX_SOUND_CHIP']=chip
    try:yield chip
    finally:
        if previous is None:os.environ.pop('ZX_SOUND_CHIP',None)
        else:os.environ['ZX_SOUND_CHIP']=previous
