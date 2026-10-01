"""Integer 50-Hz video cadence and the legacy build-only FAP3 envelope."""
from fractions import Fraction


def fields_for_fps(value):
    rate = Fraction(value)
    if rate not in (Fraction(25, 3), Fraction(10)):
        raise ValueError('supported video rates are 25/3 and 10 fps')
    return int(50 / rate)


def scaffold_audio(audio, frame_fields):
    """Pad each five-tick group to the old six-tick build scaffold.

    CB41 replaces this envelope before writing runtime video/audio streams.
    Repeating the last state adds an empty change record, so checkpoints at
    every frame boundary still match the actual resident AY stream.
    """
    if frame_fields not in (5, 6) or len(audio) % frame_fields:
        raise ValueError('expected complete five- or six-field audio groups')
    if frame_fields == 6:
        return audio
    result = []
    for lo in range(0, len(audio), frame_fields):
        group = audio[lo:lo+frame_fields]
        result.extend(group)
        result.append(group[-1])
    return result
