# Pinned Z80 CPU and generated instruction slices

`z80.h` is the unmodified floooh/chips Z80 header at revision
`9e88298ce56319953ac7a43213a1120359f7a3a6`, copyright Andre Weissflog,
under the preserved zlib/libpng license. Its normalized SHA256 is
`6ca70ffd91b1bdbaf00f7a41e7092b326145fd1c95dcdd7bb01183370de734f3`.

The files were imported read-only from `C:/Work/z80-tester`, clean revision
`d45d8889f436e99f76855b4f90afacdf8a666143`. No external checkout is needed
to build this project. `provenance.json` records exact local file hashes and
the source generator hashes. The header is the CPU implementation; there is
no separately maintained instruction decoder in this project.

`fast_slices.h` is an **altered generated derivative**, not an unmodified
upstream source. The local `emulator/tools/generate_fast_decoder.py` adapts
that project's generator and reads only the included pinned `z80.h`. It
joins existing microsteps until a fetch boundary and adds its NMOS Q
and repeating-block flag corrections. Our sole subsequent generated-slice
change replaces its direct flat read with `codec_flat_read`, so C-native
memory guards observe every access. `q_flags.h` is the source project's
flag-history classification, reproduced by the local
`emulator/tools/generate_q_table.ps1`. Both retain their original timing
operations. See `LICENSE` for the upstream notice.

`emulator/src/codec_cpu.c` supplies a separate RAM/guard/bus adapter. Its flat
mode uses these slices only when no external bus/phase hooks or asynchronous
lines are active. Its original single-T mode services native bus callbacks.
Pins alone are insufficient to model every Spectrum contention cycle; the
before-T hook exposes pinned decoder phases for separately verified bus
annotations. This import does not establish complete Spectrum, CMOS, disk,
audio or physical-silicon conformance.

Regeneration exposed a stale ignored `build/emulator/fast_decoder.h` in the
source checkout: its eight repeat-stage hooks were absent although its current
generator contained them. The included slices were regenerated locally with
those hooks; the historical ignored-header hash and this discovery are retained
in `provenance.json`. Generator regression checks compare both included headers
byte-for-byte after newline normalization. Fusion is explicitly exercised in
repeat-boundary tests, rather than inferred from a requested mode.
