"""Source-supported bass/melody FM groups with continuous real TL transitions."""
import itertools
import struct
import numpy as np
import coherent_ym3812 as coherent
import experimental_ym3812 as opl


class GroupedLattice(coherent.SourceLattice):
    def __init__(self, *args):
        super().__init__(*args)
        seed = self.seed[:, :, None]
        base = self.patch[:, :, None]
        groups = np.where(base == 14, 21, 7).astype(np.uint8)
        real = self.frequency[seed] * np.where(base == 14, 2, 1)
        # Restrict stronger1:1 FM to supported low/mid fundamentals. This avoids
        # using a dense patch to approximate unrelated high-frequency noise.
        groups = np.where((real <= 1500) & (self.confidence[:, :, :1] >= .2), groups, base)
        for name, extra in (('indices', seed), ('patches', groups), ('actual_frequency', real),
                            ('levels', self.original['level'][:, :, None]), ('confidence', self.confidence[:, :, :1])):
            value = getattr(self, name)
            setattr(self, name, np.concatenate((value[:, :, :-1], extra, value[:, :, -1:]), axis=2))


def export(c, transition_ms=2., steps=8, ordered_pitch=True):
    """Ramp carrier and modulator TL; preserve target fields and bus settling.

    Only sine-carrier1:1 groups are permitted. Their modulator multiplier
    follows the carrier, so a patch transition changes TL rather than a new
    modulation ratio. Both envelopes/oscillators stay native and continuous.
    With historical patches0/14 this is byte-identical to smooth_vgm().
    """
    count = opl.validate(c)
    if not np.isin(c['patch'], [0, 7, 14, 21]).all(): raise ValueError('unsupported coherent FM group')
    if not np.isfinite(transition_ms) or not 1 <= transition_ms <= 8 or steps not in (4, 8, 16): raise ValueError('invalid transition')
    body = bytearray(); state = {}; writes = 0; elapsed = 0
    def write(address, value, timed=True):
        nonlocal writes, elapsed
        address, value = int(address), int(value)
        if state.get(address) == value: return
        body.extend((0x5a, address, value)); state[address] = value; writes += 1
        if timed: body.append(0x71); elapsed += 2
    def until(deadline):
        nonlocal elapsed
        if elapsed < deadline:
            body.extend(struct.pack('<BH', 0x61, deadline - elapsed)); elapsed = deadline
    for address, value in opl.initial_registers(): write(address, value, False)
    old_level = np.full(9, 64); old_mod = np.full(9, 63)
    for tick in range(count):
        elapsed = 0; target = c['level'][tick]
        mod_target = np.array([opl.PATCHES[int(p)]['mod_tl'] for p in c['patch'][tick]])
        for ch, mod in enumerate(opl.MOD_OFFSETS):
            p = opl.PATCHES[int(c['patch'][tick, ch])]
            if old_level[ch] == 64: write(0x43 + mod, 63)
            write(0x20 + mod, 0x20 | p['mod_mul']); write(0xe3 + mod, p['wave'])
            key = old_level[ch] < 64 or target[ch] < 64
            changes = [(0x23 + mod, 0x20 | p['car_mul']), (0xa0 + ch, int(c['fnum'][tick, ch]) & 255),
                       (0xb0 + ch, (0x20 if key else 0) | int(c['block'][tick, ch]) << 2 | int(c['fnum'][tick, ch]) >> 8)]
            if ordered_pitch and old_level[ch] < 64:
                def frequency(s):
                    high = s.get(0xb0 + ch, 0)
                    return (s.get(0xa0 + ch, 0) | (high & 3) << 8) * 2 ** ((high >> 2) & 7) * (s[0x23 + mod] & 15)
                old = frequency(state); destination = dict(state); destination.update(changes)
                new = frequency(destination); low, high = sorted((old, new))
                def cost(order):
                    intermediate = dict(state); excursion = []; travel = []; previous = old
                    for address, value in order:
                        intermediate[address] = value; current = frequency(intermediate)
                        excursion.append(max(low - current, current - high, 0)); travel.append(abs(current - previous)); previous = current
                    return max(excursion), sum(travel)
                changes = min(itertools.permutations(changes), key=cost)
            for address, value in changes: write(address, value)
        for step in range(1, steps + 1):
            until(round(opl.OUT_RATE * transition_ms / 1000 * step / steps))
            blend = .5 - .5 * np.cos(np.pi * step / steps)
            amplitude = (1 - blend) * opl.LEVELS[old_level] + blend * opl.LEVELS[target]
            mod_amp = (1 - blend) * opl.LEVELS[old_mod] + blend * opl.LEVELS[mod_target]
            code = abs(amplitude[:, None] - opl.LEVELS).argmin(axis=1)
            mod_code = abs(mod_amp[:, None] - opl.LEVELS[:64]).argmin(axis=1)
            for ch, mod in enumerate(opl.MOD_OFFSETS):
                write(0x43 + mod, min(int(code[ch]), 63)); write(0x40 + mod, mod_code[ch])
                if step == steps and target[ch] == 64:
                    write(0xb0 + ch, int(c['block'][tick, ch]) << 2 | int(c['fnum'][tick, ch]) >> 8)
        if elapsed > 882: raise ValueError('write burst exceeds20ms')
        until(882); old_level = target.copy(); old_mod = mod_target.copy()
    body.append(0x66)
    header = bytearray(0x100); header[:4] = b'Vgm '
    for offset, value in ((4, len(header) + len(body) - 4), (8, 0x171), (0x18, count * 882), (0x34, 0xcc), (0x50, opl.CLOCK)):
        struct.pack_into('<I', header, offset, value)
    return bytes(header + body), writes
