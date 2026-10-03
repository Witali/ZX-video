"""Headless libretro frontend; stores per-window instruction counters and screens."""
from __future__ import annotations
import argparse
import ctypes as C
import hashlib
import json
from pathlib import Path
import struct
import time


class Variable(C.Structure):
    _fields_ = [('key', C.c_char_p), ('value', C.c_char_p)]


class Game(C.Structure):
    _fields_ = [('path', C.c_char_p), ('data', C.c_void_p),
                ('size', C.c_size_t), ('meta', C.c_char_p)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--core', type=Path, required=True)
    ap.add_argument('--system', type=Path, required=True)
    ap.add_argument('--disk', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--model', default='Pentagon 128K')
    ap.add_argument('--frames', type=int, default=6000)
    ap.add_argument('--window', type=int, default=500)
    ap.add_argument('--keys', type=Path, help='JSON list of [start,end,key(s)] frame intervals')
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    lib = C.CDLL(str(args.core.resolve()))
    system = str(args.system.resolve()).encode()
    values = {'fuse_machine': args.model.encode(), 'fuse_fast_load': b'disabled'}
    schedule = json.loads(args.keys.read_text()) if args.keys else []
    held = set()
    framebuffer = None
    callbacks = []

    def callback(restype, types, function):
        cb = C.CFUNCTYPE(restype, *types)(function)
        callbacks.append(cb)
        return cb

    def env(cmd, data):
        if cmd in (9, 31, 30):
            C.cast(data, C.POINTER(C.c_char_p))[0] = system
            return True
        if cmd == 15:
            var = C.cast(data, C.POINTER(Variable)).contents
            value = values.get(var.key.decode())
            if value is None:
                return False
            var.value = value
            return True
        if cmd == 17:
            C.cast(data, C.POINTER(C.c_bool))[0] = False
            return True
        if cmd == 10:  # RGB565 is the only requested format in this core.
            return C.cast(data, C.POINTER(C.c_int))[0] == 2
        if cmd == 3:
            C.cast(data, C.POINTER(C.c_bool))[0] = False
            return True
        return cmd in (11, 16, 18, 35, 37)

    def video(data, width, height, pitch):
        nonlocal framebuffer
        if data:
            framebuffer = (width, height, pitch, C.string_at(data, height * pitch))

    lib.retro_set_environment(callback(C.c_bool, [C.c_uint, C.c_void_p], env))
    lib.retro_set_video_refresh(callback(None, [C.c_void_p, C.c_uint, C.c_uint, C.c_size_t], video))
    lib.retro_set_audio_sample(callback(None, [C.c_int16, C.c_int16], lambda l, r: None))
    lib.retro_set_audio_sample_batch(callback(C.c_size_t, [C.c_void_p, C.c_size_t], lambda p, n: n))
    lib.retro_set_input_poll(callback(None, [], lambda: None))
    lib.retro_set_input_state(callback(C.c_int16, [C.c_uint]*4,
                                       lambda port, device, index, key: int(device == 3 and key in held)))
    lib.retro_init()
    lib.retro_set_controller_port_device(0, 0)
    lib.retro_set_controller_port_device(1, 0)
    lib.retro_set_controller_port_device(2, 259)
    data = args.disk.read_bytes()
    buf = C.create_string_buffer(data)
    info = Game(str(args.disk.resolve()).encode(), C.cast(buf, C.c_void_p), len(data), None)
    lib.retro_load_game.argtypes = [C.POINTER(Game)]
    lib.retro_load_game.restype = C.c_bool
    if not lib.retro_load_game(C.byref(info)):
        raise RuntimeError('Load failed')
    lib.retro_survey_clock.restype = C.c_uint64
    lib.retro_survey_machine.restype = C.c_char_p
    stats = (C.c_uint64 * (18+768))()
    blocks = (C.c_uint64 * 3)()
    report = {'disk': args.disk.name, 'sha256': hashlib.sha256(data).hexdigest(),
              'model_requested': args.model, 'machine': lib.retro_survey_machine().decode(),
              'frame_tstates': lib.retro_survey_frame_length(), 'keys': schedule,
              'core_sha256': hashlib.sha256(args.core.read_bytes()).hexdigest(), 'windows': []}
    lib.retro_survey_reset()
    start = lib.retro_survey_clock()
    host_start = time.monotonic()
    for frame in range(args.frames):
        held = {ord(k) if isinstance(k, str) else k for lo, hi, keys in schedule
                if lo <= frame < hi for k in (keys if isinstance(keys, list) else [keys])}
        lib.retro_run()
        if (frame+1) % args.window == 0 or frame+1 == args.frames:
            stop = lib.retro_survey_clock()
            lib.retro_survey_read(stats)
            lib.retro_survey_blocks(blocks)
            row = {'frontend_frame_end': frame+1, 'start_t': start, 'end_t': stop,
                   'groups': {}}
            for g, name in enumerate(['ram', 'rom', 'trdos']):
                n, base, elapsed, idle_n, idle_t, halt_n = stats[g*6:g*6+6]
                row['groups'][name] = dict(instructions=n, base_t=base, elapsed_t=elapsed,
                    idle_m1=idle_n, idle_t=idle_t, halts=halt_n,
                    repeated_block_continuations=blocks[g],
                    histogram={str(i): stats[18+g*256+i] for i in range(256) if stats[18+g*256+i]})
            row['unattributed_t'] = stop-start-sum(x['elapsed_t']+x['idle_t'] for x in row['groups'].values())
            if framebuffer:
                width, height, pitch, pixels = framebuffer
                rgb = bytearray()
                for y in range(height):
                    for x in range(width):
                        c = struct.unpack_from('<H', pixels, y*pitch+x*2)[0]
                        rgb.extend((((c>>11)&31)*255//31, ((c>>5)&63)*255//63, (c&31)*255//31))
                (args.out/f'{frame+1:06}.ppm').write_bytes(f'P6\n{width} {height}\n255\n'.encode()+rgb)
                row['screen_sha256'] = hashlib.sha256(pixels).hexdigest()
            report['windows'].append(row)
            (args.out/'raw.json').write_text(json.dumps(report, indent=2)+'\n')
            n = sum(x['instructions'] for x in row['groups'].values())
            t = sum(x['base_t'] for x in row['groups'].values())
            print(args.disk.name, frame+1, n, round(t/n, 5) if n else None,
                  'residual', row['unattributed_t'], flush=True)
            lib.retro_survey_reset()
            start = stop
    report['host_seconds'] = time.monotonic()-host_start
    (args.out/'raw.json').write_text(json.dumps(report, indent=2)+'\n')
    lib.retro_unload_game()
    lib.retro_deinit()


if __name__ == '__main__':
    main()
