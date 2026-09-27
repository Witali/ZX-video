# Direct motion target loads into alternate HL

Date: 2026-09-27. Repository baseline: `5856133`; frame CPU baseline:
[the complete two-byte Huffman-cache measurement](cached_huffman_lookahead_cpu.json).
**CPU prototype; no changed TRD or full disk-playback claim.**

## Instruction-level hypothesis

The nonzero unrolled motion phases previously received their output pointer
through the stack. The common target load preceded phase dispatch:

```asm
LD HL,(target)   ; 16 T, common to all non-clear phases
; unchanged phase dispatch
PUSH HL         ; 11 T
EXX             ;  4 T
POP HL          ; 10 T
EXX             ;  4 T
; total pointer setup: 45 T
```

The [prototype](direct_motion_target.py) moves the common load to phase 0
and gives phases 2/4/6 this setup:

```asm
EXX             ;  4 T
LD HL,(target)   ; 16 T
EXX             ;  4 T
; total pointer setup: 24 T
```

The exact saving is **21 T per nonzero-phase motion entry**. Phase 0 still
executes its single 16-T load; the clear-tile path is unchanged. No extra
CALL, jump, NOP, register save, data copy or interrupt-disabled interval is
introduced. Counts were checked against [Zilog UM008011-0816](https://www.zilog.com/docs/z80/um0080.pdf):
printed pages 102 (`LD HL,(nn)`, 16 T), 115 (`PUSH HL`, 11 T),
119 (`POP HL`, 10 T) and 126 (`EXX`, 4 T), and against every executed
instruction in the CPU fixture. All four instructions leave flags unchanged.
Temporary pointer-transfer stack use falls from two bytes to zero;
the ordinary CALL/RET and interrupt stack remain available.

## Register contract and placement

The two-byte Huffman cache already uses HL' for motion output. B'/C'/E'
retain their existing cache/bit-position roles. AF and AF' are unaffected
by the new setup, including its flags.

**Primary HL is no longer returned with the old target in phases 2/6.**
Its value is dead: every existing motion caller immediately calls
`patches`, whose first instruction reloads HL from `bitmap_masks`.
The installer checks those caller and entry bytes and rejects an unknown
contract. Tests compare all other registers and flags; complete-frame
checks verify the callers as well. Phase 4 overwrites primary HL while
looking up shifted pixels, so its final value already matches.

The four replacement entries add **3 bytes of fixed bank-2 code** overall.
The prototype relocates the affected tail, state labels and all listed
absolute/relative references. In the actual movie configuration, the
exclusive reconstruction end moves **8FB8h -> 8FBBh**, leaving five bytes
before the unchanged lookahead helper at 8FC0h. No buffer, dictionary or
additional state is allocated. The inline Huffman body remains 875 bytes.

Integration must respect the changed code addresses: the retired fixed
patch body, currently reused by bank-2 ZX0, moves **8DF2h..8F09h ->
8DF5h..8F0Ch** (exclusive ends). The existing bank-2 installer deliberately
requires its old placement; this prototype must not be applied blindly to
an already installed player. Rebuild those references, bootstrap metadata
and boot verifier before any TRD experiment.

## Verification

Five [specialized tests](test_direct_motion_target.py) pass:

- **1,312 paired motion cases:** all 81 vectors plus the clear marker,
  four stripe positions and four columns, including frame edges and cache
  wrap. Exact output, live registers, flags, stack balance and instruction
  timing; all four phases are exercised.
- Four complete mixed frames compare the compact result, both native
  screens and the per-frame `-21 * nonzero_entries` cycle formula.
- Real AY interrupts after every instruction of a two-frame mixed run
  check both register sets and stream/output state (over 20,000 IRQs).
- Both real video-publication/AY IRQ handlers interrupt every new setup
  boundary: ten boundaries and ten publications per handler, including
  interrupts while the alternate register set is selected.
- Unexpected old setup bytes or insufficient free code space are rejected.

During test development, the first vector comparison incorrectly required
the dead primary HL to match. It exposed the caller contract above; the
test now excludes only H/L in phases 2/6 and the installer explicitly
validates their overwrite. An initial test import also referenced OFFSETS
from the wrong module; it was corrected before the successful suite.

The [full-movie benchmark](benchmark_direct_motion_target.py) records exact
compact data, both complete 6912-byte screens, input and paging contracts,
and each frame's CPU total against the saved baseline. The independent
[evidence auditor](audit_direct_motion_target.py) also checks phase-entry
counts against the earlier executed motion histogram.

## Complete CPU result

All **4,221 frames** pass. The measured 28,773 nonzero-phase entries match
the earlier independent motion histogram exactly. Each frame's measured
delta equals `-21 * nonzero_entries`; all compact pixels, both complete
screens, input cursors and paging checks pass.

| Volume | Frames | Entries | Baseline frame T | New frame T | Delta T |
|---|---:|---:|---:|---:|---:|
| 1 | 1624 | 13502 | 385003910 | 384720368 | -283542 |
| 2 | 1297 | 8272 | 326528010 | 326354298 | -173712 |
| 3 | 1300 | 6999 | 306517321 | 306370342 | -146979 |
| **Total** | **4221** | **28773** | **1018049241** | **1017445008** | **-604233** |

Pointer setup alone falls **1,294,785 -> 690,552 T**. The complete measured
frame stages improve by **0.059352%**. There are **3,352 faster frames**, a
maximum saving of **819 T/frame**, and **zero slower frames**. This is a
small verified CPU improvement, not a measured improvement in frame rate.
The [full report](direct_motion_target_cpu.json) retains per-frame counts,
generated code, relocated references and source/input hashes; the
[audited summary](direct_motion_target_summary.json) checks their totals.

**Decision:** the 45-to-24-T hypothesis is confirmed. Retain the prototype
for later integration; the current disk baseline and release remain as
recorded in the main plan. No additional movie bytes or pixel changes are
needed, but compressed bootstrap size still requires measurement.

## Reproduction and scope

```powershell
$env:PYTHONPATH = 'toolkit;.worktree/audio-fidelity/.tmp/python_packages'
python -m unittest test_direct_motion_target -v
python toolkit/benchmark_direct_motion_target.py --output .tmp/direct-motion-repeat.json
python toolkit/audit_direct_motion_target.py
```

The benchmark defaults to the retained raw volumes under
`.worktree/volume-huffman/.tmp/probe` and authorized saved states under
`.worktree/three-disk-quality/.tmp/no_credits/source/conversion.npz`.
Both paths can be overridden. Sources and inputs are hash-pinned; a smoke
run with `--limit` cannot pass the complete-evidence auditor.

The compressed movie stream is unchanged. **Compressed bootstrap size,
disk-sector count and actual publication timing are unmeasured for this
prototype.** CPU totals exclude ZX0, packet queues/copies, IRQ cadence, ULA
contention, TR-DOS ROM and physical disk latency. The tests check IRQ
correctness, not sustained 50-Hz soundtrack delivery or deadline compliance.
Keep this optimization optional until code placement, independent boot and
all three full disk runs are verified. It cannot by itself establish
smooth 25/3-fps playback.
