# Word-only idle-cycle control: complete and rejected

2026-10-14. The frozen source-independent0x56AD word replaces only bin32
states16/17; all2048 successors and2046 other words stay exact. The original
16→17→16 feedback cycle remains. Both selected packets have225 high T out
of449, so the two-packet mean retains a half-T-per-packet duty offset.
No source participates in word selection. Prior reset-neutral controls,
original Python/C and default player behavior are preserved.

Six helper tests and six independent player tests pass. Exact absent-option
disk/metadata match0a212417. Eight complete4096-sample native before/after
runs check every pulse/state/guard and interval on all four RAM profiles.
All64-bin closure stays18 states; FIRST138/SECOND97 costs64 more dictionary
bytes than the original centered table. Actual maximum2392-sector cold load
passes on1024K; workerBC40..BFBC leaves67 bytes. Native counts remain423/449
T ordinary,14 page and243/267 bank extras, delta0; ULA waits, actual Fuse and
physical hardware are separate. Helper/player evidence is in the sibling
`idle-cycle-helper` and `idle-cycle-packet-player` folders.

All nine complete matched C searches and host scores finish in100.797013 s,
including preparation, worksets, rendering and diagnostics. Original input
bytes, gain, length,8-kHz reference, f64 filter and100-ms edges stay fixed.
SNR has no fitted gain, delay or clock. Silence RMS0.002300011 remains exactly
sample-identical to reset-neutral,16.579842 dB below matched-centered.

Preserving feedback recovers most of the large reset-neutral losses, but
five sources still regress against matched: speech−0.190457 dB,
Entertainer−0.360775, steps−0.394416, quiet440−0.000415 and song−0.009961.
Song20.100940113 dB is0.149375774 below half-joint and1.275869589 above
compensation. Numeric indicators versus matched include33 AM,29 delay and
19 coherent-line increases;33 fits are inconclusive. They are disclosures,
not an audibility threshold or proof of artifact absence.

Reject unconditional promotion. Lower idle noise and restored feedback are
useful mechanisms, but general quality remains incomplete. No new Fuse run
is warranted for this rejected candidate; no main/release/hardware claim.

```powershell
python audiobook-beeper/test_idle_cycle_packet_model.py -v
python audiobook-beeper/test_idle_cycle_packet_player.py --evidence NEW_EMPTY_FOLDER -v
python audiobook-beeper/experiments/song-snr/idle_cycle_control.py `
  audiobook-beeper/experiments/song-snr/evidence --output NEW_EMPTY_FOLDER `
  --scratch .tmp/idle-reproduction --cache .tmp --phase host
```

The manifest checks125 measured/archive files,22 pre-input producers, nine
source/unscaled-array identities and36 baseline inputs. Independent rational
regeneration confirms the exact two-cell override, unchanged successor graph
and closure. Cosmetic helper finalization is disclosed; exact tested/pre-input
bytes remain archived. No measured output, reference, gain or timing changed.
