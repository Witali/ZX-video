# Retained native timing and extraction accounting

2026-10-13, baseline `0085a116`. Moving implementations and sharing the
guard patcher preserves all default opcode bytes, addresses and label maps.
The extraction adds **0 deterministic T-states** to any existing decoder or
producer path. Custom absolute addresses preserve instruction opcodes and
counts; contention and paging still depend on the application's placement.

Counts below use Zilog UM0080 (the same table referenced in emitted metadata).
Conditional JP=10 T, JR=7/12 T, register logical=4 T, immediate/memory
logical=7 T, LDI=16 T, LDIR=21 T per repeating byte and 16 T on the last byte.
LDIR cannot be modeled as a constant 21 T for every byte.

| Retained path / consistent endpoints | Before extraction | Library | Delta |
| --- | ---: | ---: | ---: |
| Fast/tuned Turbo copy boundary: output high below target, through AF restore | 29 T | 29 T | 0 T |
| Fast/tuned Turbo boundary: equal high, low below target | 57 T | 57 T | 0 T |
| Fast/tuned Turbo boundary: equal target through CALL yield (excludes yield body) | 74 T | 74 T | 0 T |
| Fast/tuned Turbo boundary: high above target through CALL yield | 58 T | 58 T | 0 T |
| Fast target synchronization including RET | 112 T | 112 T | 0 T |
| Tuned Turbo target synchronization including RET | 86 T | 86 T | 0 T |
| LZSA2 available header, direct entry through token_body | 46 T | 46 T | 0 T |
| LZSA2 available header, older CALL/RET entry through token_body | 96 T | 96 T | 0 T |
| LZSA2 shared guard patcher, ordinary partial / complete, excludes caller RET | 187 / 224 T | 187 / 224 T | 0 T |
| LZSA2 shared guard patcher, direct partial / complete, excludes caller RET | 174 / 211 T | 174 / 211 T | 0 T |

The guard-patcher totals use OR A (4), LD A,n (7), JP Z (10), LD (nn),A
(13), LD HL,nn (10), LD (nn),HL (16). The complete case executes one extra
LD A,n and three extra LD HL,nn. Direct mode omits the header opcode store.
The native library test measures all four paths, including a separate 10-T RET.

Historical improvement scopes remain distinct:

- [Complete Fast ZX0 CPU comparison](../toolkit/FASTER_ZX0.md): retained
  Turbo 189573555 T -> adapted Fast 183122436 T (-6451119), 188 identical
  blocks/2965011 output bytes; producer 11831304 T unchanged. Fast may slow
  individual slices (62 of 11584, at most69 T) despite improving every block.
- [LZSA2 S/P dispatch](../toolkit/LZSA2_DISPATCH.md): 21 unchanged blocks,
  decoder 19844626 ->19412006 T (-432620). None/one-or-two/extended literal
  dispatch:54/38/50 T, versus54/58/58 before that earlier optimization.
- [Direct header improvement](../CHANGELOG.md): available guard96 ->46 T
  (-50), an earlier change already retained before this extraction.

These are CPU-only component counts, not end-to-end playback rates.
The extraction's 24-case direct streaming regression records baseline
component total4101406 T versus guarded4144763 T (+43357); guarded partial
input has extra work. That comparison is to complete-input decoding, not to
the pre-extraction streaming implementation. Do not turn it into a claimed
new regression/improvement or a disk-delivery result. ROM/disk/IRQ/ULA and
actual publication timing remain separately qualified by the application.

[Item01 long-copy counts](LONG_COPY.md) add an opt-in LZSA2 profile, with
complete native/streaming comparisons and exact path/space deltas. They do
not change this default baseline or its compression cost model.
