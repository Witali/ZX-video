"""Lossless note/volume/noise commands for the 50 Hz stream (offline prototype).

Each tick starts with the number of commands, 0..7. Pitch command: channel
in bits 7:6, period table index in 5:0; index 62 escapes a literal 16-bit
period. Cx/Dx/Ex set A/B/C volume. F0..FD set noise 0..13, FE sets 31,
FF escapes a noise period byte. Noise also implies the standard mixer.
This format has no Z80 decoder yet; never substitute it into a v11 disk.
"""
from __future__ import annotations

import build_long_video_trd as video

PERIODS=(1,)+tuple(round(1773400/(16*440*2**((note-69)/12))) for note in range(33,94))
PERIOD_INDEX={value:index for index,value in enumerate(PERIODS)}
NOISE=(tuple(range(14))+(31,))


def encode_ticks(frames):
    previous=None;result=[]
    for frame in frames:
        if (len(frame.periods)!=3 or len(frame.volumes)!=3
                or any(not 0<=p<=4095 for p in frame.periods)
                or any(not 0<=v<=15 for v in frame.volumes)
                or not 0<=frame.noise_period<=31):raise ValueError('invalid AY state')
        commands=[]
        for voice,period in enumerate(frame.periods):
            if previous is None or period!=previous.periods[voice]:
                index=PERIOD_INDEX.get(period,62)
                commands.append(bytes([(voice<<6)|index])+(period.to_bytes(2,'little') if index==62 else b''))
        if previous is None or frame.noise_period!=previous.noise_period:
            noise=frame.noise_period
            commands.append(bytes([0xF0+NOISE.index(noise)]) if noise in NOISE else bytes([0xFF,noise]))
        for voice,volume in enumerate(frame.volumes):
            if previous is None or volume!=previous.volumes[voice]:
                commands.append(bytes([0xC0+(voice<<4)+volume]))
        result.append(bytes([len(commands)])+b''.join(commands));previous=frame
    return result


def decode_ticks(data,count):
    position=0;periods=[None]*3;volumes=[None]*3;noise=None;result=[]
    def byte():
        nonlocal position
        if position==len(data):raise ValueError('truncated AY events')
        value=data[position];position+=1;return value
    for _ in range(count):
        commands=byte()
        if commands>7:raise ValueError('too many AY commands')
        for _ in range(commands):
            token=byte()
            if token<0xC0:
                voice,index=token>>6,token&63
                if index==63:raise ValueError('reserved pitch token')
                period=byte()+256*byte() if index==62 else PERIODS[index]
                if not 0<=period<=4095:raise ValueError('invalid period')
                periods[voice]=period
            elif token<0xF0:volumes[(token>>4)-12]=token&15
            else:
                noise=byte() if token==255 else NOISE[token-0xF0]
                if noise>31:raise ValueError('invalid noise')
        if noise is None or None in periods or None in volumes:raise ValueError('uninitialized AY state')
        result.append(video.AyFrame(tuple(periods),tuple(volumes),noise))
    if position!=len(data):raise ValueError('trailing AY data')
    return result
