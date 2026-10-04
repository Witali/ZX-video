"""Packed nine-byte AY states and their R0..R10 register representation."""
from dataclasses import dataclass

AY_STATE_BYTES = 9


@dataclass(frozen=True)
class AyFrame:
    periods: tuple[int, int, int]
    volumes: tuple[int, int, int]
    # Zero: three tones. 1..31: channel B becomes noise-only (ZXFC v10).
    noise_period: int = 0

    @property
    def mixer(self) -> int:
        return 0x2A if self.noise_period else 0x38

    def serialize(self) -> bytes:
        result = bytearray()
        for period in self.periods:
            result += bytes((period & 0xFF, (period >> 8) & 0x0F))
        result += bytes(self.volumes)
        if not 0 <= self.noise_period <= 31:
            raise ValueError("noise period must be 0..31")
        result[1] |= (self.noise_period & 15) << 4
        result[3] |= self.noise_period & 16
        if len(result) != AY_STATE_BYTES:
            raise AssertionError("invalid AY state size")
        return bytes(result)

    @classmethod
    def deserialize(cls, state: bytes) -> "AyFrame":
        if len(state) != AY_STATE_BYTES:
            raise ValueError("invalid AY state size")
        return cls(tuple(state[2*i] + ((state[2*i+1] & 15) << 8) for i in range(3)),
                   tuple(state[6:]), (state[1] >> 4) | (state[3] & 16))


def registers(frame):
    result=[]
    for period in frame.periods:result.extend((period&255,(period>>8)&15))
    return bytes((*result,frame.noise_period,frame.mixer,*frame.volumes))
