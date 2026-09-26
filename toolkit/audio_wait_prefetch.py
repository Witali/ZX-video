"""Use AY backpressure waits for one bounded queue step, preserving input HL.

Only the integrated bank-2 ZX0 layout has the required retired fixed RAM.
Audio data, queue capacity, sample rate and publication deadlines are unchanged.
"""
from build_zxv_trd import MiniAssembler
from build_fap3_trd import sha

ORIGIN=0x7c23


def build(queue_step,enqueue_one):
    a=MiniAssembler(ORIGIN)
    a.emit(0xe5)                       # PUSH HL: 11
    a.label('step_call');a.emit(0xcd);a.word(queue_step)  # CALL: 17
    a.emit(0xe1,0xb7)                 # POP HL: 10; OR A: 4
    a.emit(0xc2);a.word(enqueue_one)   # JP NZ: 10
    a.emit(0xfb,0x76)                 # EI: 4; HALT: initial 4
    a.emit(0xc3);a.word(enqueue_one)   # JP: 10
    a.label('end');blob=a.resolve()
    return blob,dict(a.labels,origin=ORIGIN,code_bytes=len(blob),code_hex=blob.hex(),code_sha256=sha(blob),
        previous_overhead_tstates=18,busy_overhead_tstates=62,idle_overhead_tstates=80,
        busy_delta_tstates=44,idle_delta_tstates=62,
        timing_excludes=['queue step CPU','HALT waiting beyond initial 4 T','IRQ','ULA','ROM','disk latency'])


def install(read8,put,m,h):
    if not m.get('bank2_zx0',{}).get('enabled'):raise ValueError('audio prefetch requires relocated ZX0')
    start=h.audio['audio_enqueue_space']-5;retry=h.audio['audio_enqueue_one']
    original=bytes([0xfb,0x76,0xc3])+retry.to_bytes(2,'little')
    if bytes(read8(start+i) for i in range(5))!=original:raise ValueError('AY wait path differs')
    code,report=build(m['queue_labels']['step'],retry)
    if ORIGIN!=m['bank2_zx0']['old_origin'] or any(read8(ORIGIN+i) for i in range(len(code))):
        raise ValueError('AY helper RAM is occupied')
    hook=bytes([0xc3,ORIGIN&255,ORIGIN>>8,0,0])
    put(ORIGIN,code);put(start,hook)
    return dict(report,enabled=True,hook_address=start,hook_hex=hook.hex(),previous_hook_hex=original.hex(),
        extra_ram_bytes=0,extra_stream_bytes=0,extra_stack_bytes=2,bank7_required=True,
        timing_source='https://www.zilog.com/docs/z80/um0080.pdf')
