"""Four musical roles, adapted from z80-tester's Expedition 33 sampler.

The imported JSON preserves that project's complete simplified arrangements.
See SOURCES.md for attribution, source hashes and adaptation limits.
"""
from fractions import Fraction
import math
import re

CHORDS = {
    'Bm': (35, [59, 62, 66]), 'Gmaj7': (43, [55, 59, 62, 66]),
    'Em': (40, [55, 59, 64]), 'F#m': (42, [57, 61, 66]),
    'F#': (42, [58, 61, 66]), 'C#m7b5': (37, [55, 59, 61, 64]),
    'Cm': (36, [55, 60, 63]), 'Fm': (41, [56, 60, 65]),
    'Bb': (46, [58, 62, 65]), 'Eb': (39, [55, 58, 63]),
    'C7b9': (36, [58, 61, 64]), 'Gsus4': (43, [55, 60, 62]),
    'G7': (43, [55, 59, 62, 65]), 'Abmaj7': (44, [56, 60, 63, 67]),
    'Ab': (44, [56, 60, 63]), 'Am7b5': (45, [57, 60, 63, 67]),
    'Bb7': (46, [56, 62, 65]), 'G7/B': (47, [55, 59, 62]),
    'Bb/D': (38, [58, 62, 65]), 'Cm/Eb': (39, [55, 60, 63]),
    'Dm7b5': (38, [53, 56, 60]), 'G7b9': (43, [53, 56, 59]),
    'Ddim7': (38, [53, 56, 59]), 'Cm/G': (43, [55, 60, 63]),
    'Fm7': (41, [56, 60, 63, 65]), 'Fm/Ab': (44, [56, 60, 65]),
    'F5': (41, [53, 60, 65]), 'Cmadd9': (36, [55, 62, 63]),
}


def midi_number(name):
    if name == 'R':
        return 0
    match = re.fullmatch(r'([A-G])([#b]?)(-?\d+)', name)
    if not match:
        raise ValueError(f'Invalid note {name}')
    letter, accidental, octave = match.groups()
    pitch = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[letter]
    pitch += {'': 0, '#': 1, 'b': -1}[accidental]
    note = (int(octave)+1)*12+pitch
    if not 1 <= note <= 127:
        raise ValueError(f'Note outside supported range: {name}')
    return note


def notes_for_pattern(score, name):
    if isinstance(score['patterns'][name], dict):
        return notes_for_bars(score['patterns'][name])
    bars = score['patterns'][name]
    voices = [[] for _ in range(4)]
    beat, tied = 0., False
    for bar in bars:
        total = 0.
        for token in bar.split():
            pitch, value = token.split(':')
            tie = value.endswith('~')
            duration = float(Fraction(value.rstrip('~')))
            if not math.isfinite(duration) or duration <= 0:
                raise ValueError('Finite positive duration required')
            note = midi_number(pitch)
            if tied:
                if not note or not voices[0] or voices[0][-1][2] != note:
                    raise ValueError('A tie must extend the same pitch')
                previous = voices[0][-1]
                voices[0][-1] = (previous[0], previous[1]+duration, *previous[2:])
            elif note:
                voices[0].append((beat, duration, note, 0 if name == 'intro' else 1, 1.))
            tied = tie
            beat += duration
            total += duration
        if abs(total-score['beats_per_bar']) > 1e-9:
            raise ValueError(f'{name}: incorrect bar length')
    if tied:
        raise ValueError('Unresolved tie at pattern end')
    pairs = score.get('chord_overrides', {}).get(name, score['chord_pairs'])
    for bar_index in range(len(bars)):
        for half, chord in enumerate(pairs[bar_index % len(pairs)]):
            root, pitches = CHORDS[chord]
            start = bar_index*4+half*2
            for step in range(4):
                voices[1].append((start+step*.5, .47, pitches[[0, 1, 2, 1][step]], 0, .74))
            voices[2].append((start, 1.94, root, 2, .55))
            voices[3].append((start, 1.94, pitches[1], 1, .40))
            if name == 'F':
                for step in range(2):
                    voices[0].append((start+step, .92, pitches[step+1]+12, 0, .74))
    return voices, beat


def notes_for_bars(pattern):
    voices, offset = [[] for _ in range(4)], 0.
    for bar in pattern['bars']:
        beats = bar.get('beats', pattern['beats_per_bar'])
        instrument = bar.get('lead_instrument', pattern.get('lead_instrument', 1))
        transpose = bar.get('lead_transpose', pattern.get('lead_transpose', 0))
        total = 0.
        for token in bar['melody'].split():
            pitch, value = token.split(':')
            duration = float(Fraction(value))
            if duration <= 0:
                raise ValueError('Positive duration required')
            note = midi_number(pitch)
            if note:
                voices[0].append((offset+total, duration, note+transpose, instrument, 1.))
            total += duration
        if abs(total-beats) > 1e-8:
            raise ValueError('Incorrect bar length')
        cursor = offset
        chords = bar['chords']
        if chords and abs(sum(duration for _, duration in chords)-beats) > 1e-8:
            raise ValueError('Incorrect chord durations')
        for chord, duration in chords:
            root, pitches = CHORDS[chord]
            for step in range(round(duration*2)):
                voices[1].append((cursor+step*.5, min(.47, duration-step*.5),
                                  pitches[[0, 1, 2, 1][step % 4]], 0, .74))
            voices[2].append((cursor, duration-.06, root, 2, .55))
            voices[3].append((cursor, duration-.06, pitches[1], 1, .40))
            cursor += duration
        offset += beats
    return voices, offset


def timeline(score):
    """Use absolute seconds, so rounding never accumulates between patterns."""
    voices = [[] for _ in range(4)]
    cursor = 0.
    for name in score['playlist']:
        notes, beats = notes_for_pattern(score, name)
        definition = score['patterns'][name]
        tempo = definition['tempo_bpm'] if isinstance(definition, dict) else score['tempo_bpm']
        scale = 60/tempo
        for role, entries in enumerate(notes):
            for start, duration, pitch, instrument, gain in entries:
                voices[role].append((cursor+start*scale, duration*scale, pitch, instrument, gain))
        cursor += beats*scale
    return voices, cursor
