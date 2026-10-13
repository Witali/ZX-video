"""AY9 states, and AY12 hardware-envelope states with explicit restart actions."""
from dataclasses import dataclass

AY_STATE_BYTES = 9


@dataclass(frozen=True)
class AyFrame:
    periods: tuple[int, int, int]
    # R8..R10 controls: fixed levels 0..15; bit 4 selects the shared envelope.
    volumes: tuple[int, int, int]
    # Zero: three tones. 1..31: channel B becomes noise-only (ZXFC v10).
    noise_period: int = 0
    # AY9 extension: optional six-bit R7, allowing tone AND noise on a channel.
    # Legacy records have no marker and keep their original mixer semantics.
    mixer_override: int | None = None
    envelope_period: int = 0
    # 255 means keep the running envelope phase; 0..15 explicitly restart it.
    envelope_shape: int = 255
    state_bytes: int = 9

    @property
    def mixer(self) -> int:
        return self.mixer_override if self.mixer_override is not None else (0x2A if self.noise_period else 0x38)

    def serialize(self) -> bytes:
        result = bytearray()
        for period in self.periods:
            result += bytes((period & 0xFF, (period >> 8) & 0x0F))
        result += bytes(self.volumes)
        if not 0 <= self.noise_period <= 31:
            raise ValueError("noise period must be 0..31")
        result[1] |= (self.noise_period & 15) << 4
        result[3] |= self.noise_period & 16
        if self.mixer_override is not None:
            if not 0 <= self.mixer_override <= 63:
                raise ValueError('mixer must be a six-bit R7 value')
            # Unused period high bits: B[7:5]=R7[2:0], C[6:4]=R7[5:3].
            # C[7] marks this extension; all twelve tone-period bits survive.
            result[3] |= (self.mixer_override & 7) << 5
            result[5] |= 0x80 | ((self.mixer_override >> 3) << 4)
        if any(not 0 <= v <= (31 if self.state_bytes == 12 else 15) for v in self.volumes):
            raise ValueError('invalid channel level or envelope enable')
        if self.state_bytes == 12:
            if not 0 <= self.envelope_period <= 65535 or self.envelope_shape not in (*range(16),255):
                raise ValueError('invalid hardware envelope controls')
            result += bytes((self.envelope_period & 255,self.envelope_period >> 8,self.envelope_shape))
        elif self.state_bytes != 9 or self.envelope_period or self.envelope_shape != 255:
            raise ValueError('hardware envelope requires a twelve-byte state')
        if len(result) != self.state_bytes:
            raise AssertionError("invalid AY state size")
        return bytes(result)

    @classmethod
    def deserialize(cls, state: bytes) -> "AyFrame":
        if len(state) not in (9,12):
            raise ValueError("invalid AY state size")
        return cls(tuple(state[2*i] + ((state[2*i+1] & 15) << 8) for i in range(3)),
                   tuple(state[6:9]), (state[1] >> 4) | (state[3] & 16),
                   ((state[3] >> 5) | (((state[5] >> 4) & 7) << 3)) if state[5] & 0x80 else None,
                   int.from_bytes(state[9:11],'little') if len(state)==12 else 0,
                   state[11] if len(state)==12 else 255,len(state))


def registers(frame):
    result=[]
    for period in frame.periods:result.extend((period&255,(period>>8)&15))
    result = bytes((*result,frame.noise_period,frame.mixer,*frame.volumes))
    if frame.state_bytes == 12:
        result += bytes((frame.envelope_period & 255,frame.envelope_period >> 8,frame.envelope_shape))
    return result
