# Hide screen RAM used by the initial loader

Implemented and measured on 2026-09-28, at the user's request. The shared
`fap3_disk_z80.build_bootstrap` enables this automatically for player layouts
that use the normal screen as staging and restore a complete shadow screen.
Both the generic converter and the current integrated builders use it.

## Why both screen selection and attributes matter

Some current startup sections occupy **27 sectors / 6912 bytes** at 4000h.
This includes the normal screen's attributes at 5800h..5AFFh. Setting those
attributes to black once would not work: subsequent reads overwrite them
with compressed data.

The loader now maps bank 7 without displaying it, clears all **768 shadow
attributes** at D800h..DAFFh to **INK 0 / PAPER 0 / FLASH 0**, and selects
the shadow display during staging reads. Paging other RAM banks preserves
that display selection. Compressed bytes in bank 5 are never displayed.

The shadow-screen section is restored forward: its complete valid bitmap
arrives before its original attributes. Thus it can reveal valid initial
screen content, but never compressed staging bytes. Once all sections are
restored, the loader selects bank 5 for display and maps bank 7, exactly as
the existing runtime expects (7FFD = 17h). First-frame preparation restores
the normal video colours. No extra frame or staging buffer is allocated.

Small synthetic layouts without a complete shadow restore retain their
legacy path; the change must not erase attributes that such a layout expects
to retain. Production layouts tested here restore the full shadow screen.

## Instruction and disk cost

The added startup-only instructions are:

```text
LD A,17h; LD BC,7FFDh; OUT (C),A   7 + 10 + 12 = 29 T
LD HL,D800h; LD DE,D801h
LD BC,767; LD (HL),0; LDIR        40 + 21*767 - 5 = 16142 T
```

Total **16171 T**, approximately **4.56 ms** of uncontended CPU time.
ULA/IRQ and real disk latency are additional. Existing section paging
instructions have the same timing, with only bit 3 of their immediates
changed. Playback instruction delta is **0 T**. Bootstrap code grows by
**20 bytes inside existing padding**; PLAYER stays 1024 bytes. Disk sector
count, stream bytes, video packets, resolution and AY data are unchanged.

| Disk | Native startup before | Native startup after | Reads | Hidden bank-5 screen writes |
| --- | ---: | ---: | ---: | ---: |
| 1 | 3094770 T | 3110941 T | 91 | 29952 |
| 2 | 3214643 T | 3230814 T | 92 | 30208 |
| 3 | 3303161 T | 3319332 T | 94 | 30464 |

## Verification

- Three new unit tests verify all attributes, retained bitmap bytes,
  display selection and the instruction count; nine generic-converter and
  two integrated-bootstrap tests pass.
- Real bootstrap opcodes execute from dirty RAM for all three current Fast
  volumes. Every staging write is guarded against becoming visible. Each
  shadow bitmap is checked complete before attributes reveal it.
- Final section bytes, first complete native frame, second compact frame,
  immutable AY data and the 31-record initial FIFO match the baseline.
  Both disk swaps, wrong-disk rejection and wrong-series rejection pass
  with mocked TR-DOS reads.
- Separate Fuse checks execute real TR-DOS on all three disks. They check
  all 768 cleared attributes and all **91 / 92 / 94** read entry/return page
  pairs. No ROM call exposes the normal staging screen. The expected 17h
  page is restored before the playback driver. The debugger performs no
  memory writes.

The measured Fuse startup times are **19682980 / 19882186 / 20789220 T**,
including ROM, disk, IRQ and contention. These tests stop at the driver;
they do not revalidate complete-movie timing or claim a release. Previous
playback results describe the archived earlier binaries. Existing root
preview images are not replaced by this startup-only check.

## Reproduction

The checker regenerates only the four PLAYER sectors of a prepared set;
all other **2556 sectors per disk** stay byte-identical. The rebuilt images
are for startup verification, with metadata marking full playback unverified.

```powershell
python toolkit/check_hidden_bootstrap.py --directory .tmp/fast-zx0-player `
  --states .worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz `
  --output .tmp/new-hidden-bootstrap
python toolkit/measure_hidden_bootstrap_fuse.py `
  --fuse "C:/Program Files (x86)/Fuse/fuse.exe" `
  --directory .tmp/new-hidden-bootstrap --output .tmp/new-hidden-bootstrap-fuse
python -m unittest discover -s toolkit -p test_hidden_bootstrap.py
python toolkit/audit_hidden_bootstrap.py
```

[Saved summary](hidden_bootstrap_summary.json) ·
[Evidence and source snapshots](hidden_bootstrap_evidence/manifest.json) ·
[Native checker](check_hidden_bootstrap.py) ·
[Fuse checker](measure_hidden_bootstrap_fuse.py)
