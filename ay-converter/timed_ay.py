"""Separate real-register subframe ramp probe; not a native player format."""
import struct
import numpy as np
import music_profile


def stream(registers, width=11, transition_ms=0., steps=8):
    if width not in (11, 14) or not registers or len(registers) % width or transition_ms not in (0., 2., 4., 8.) or steps != 8: raise ValueError('invalid timed probe controls')
    rows = np.frombuffer(registers, np.uint8).reshape(-1, width)
    if np.any(rows[:, 1:6:2] > 15) or np.any(rows[:, 6] > 31) or np.any(rows[:, 7] > 63) or np.any(rows[:, 8:11] > (31 if width == 14 else 15)): raise ValueError('invalid AY registers')
    if width == 14 and not np.isin(rows[:, 13], np.r_[np.arange(16), 255]).all(): raise ValueError('invalid shape actions')
    # AYE1 is explicitly an AY probe, independent of ambient target settings.
    levels = music_profile.chip_levels('AY'); events = []; state = np.zeros(14, np.uint8); state[7] = 63
    for tick, target in enumerate(rows):
        elapsed = 0; old = state.copy()
        def write(reg, value):
            nonlocal elapsed
            if reg == 13 and value == 255: return
            events.append((tick * 882 + elapsed, reg, int(value))); state[reg] = value; elapsed += 1
        # Shared envelope and tone/noise routing cannot independently fade
        # three voices. Probe only fixed-to-fixed levels with unchanged gates.
        eligible = np.array([transition_ms and not (old[8 + ch] & 16 or target[8 + ch] & 16) and
                             not ((old[7] ^ target[7]) & ((1 << ch) | (1 << (ch + 3)))) for ch in range(3)], bool)
        for reg, value in enumerate(target): write(reg, old[reg] if 8 <= reg <= 10 and eligible[reg - 8] else value)
        if transition_ms:
            for step in range(1, steps + 1):
                elapsed = max(elapsed, round(44.1 * transition_ms * step / steps))
                fraction = .5 - .5 * np.cos(np.pi * step / steps)
                for ch in np.flatnonzero(eligible):
                    amp = (1 - fraction) * levels[old[8 + ch]] + fraction * levels[target[8 + ch]]
                    value = int(abs(levels - amp).argmin())
                    if state[8 + ch] != value: write(8 + ch, value)
        if elapsed > 882: raise ValueError('overrun20-ms deadline')
        assert np.array_equal(state[:min(width, 13)], target[:min(width, 13)])
    data = b'AYE1' + struct.pack('<III', 44100, len(rows) * 882, width)
    data += b''.join(struct.pack('<IBB', *event) for event in events)
    return data


def audit(data, registers):
    """Independent final-state and nonzero serial spacing check on every field."""
    assert data[:4] == b'AYE1'; rate, samples, width = struct.unpack_from('<III', data, 4)
    assert rate == 44100 and samples == len(registers) // width * 882 and (len(data) - 16) % 6 == 0
    targets = np.frombuffer(registers, np.uint8).reshape(-1, width)
    state = [0] * 14; state[7] = 63; previous = -1; fields = 0; writes = 0
    def check():
        for reg in range(min(width, 13)): assert state[reg] == targets[fields, reg]
        if width == 14 and targets[fields, 13] != 255: assert state[13] == targets[fields, 13]
    for offset in range(16, len(data), 6):
        time, reg, value = struct.unpack_from('<IBB', data, offset)
        assert time > previous and time < samples and reg < width
        frame = time // 882
        if frame != fields: check(); fields += 1; assert frame == fields
        state[reg] = value; previous = time; writes += 1
    check(); fields += 1; assert fields == len(targets)
    return dict(fields=fields, samples=samples, writes=writes, all_target_states_exact=True,
                serial_spacing_output_samples_min=1, native_scheduler_qualified=False)
