# Compact IMA3 table placement

The automatic PDM/IMA3 converter now reuses unused code-alignment space for
decoder rows and sizes its fixed-bank reservation to the actual resident
end. It retains all 89 IMA indices, all eight codes per index, every PDM
feedback state and the original 128-level modulation model. No audio is
re-encoded or discarded by this change.

| Allocation | Previous | Compact |
|---|---:|---:|
| Fixed bank 2 code/tables reservation | 14336 bytes | 13312 bytes |
| Complete IMA decoder table | 2848 bytes | 2848 bytes |
| Decoder bytes inside existing code gaps | 0 | 352 |
| Decoder bytes after the PCM pointer table | 2848 | 2496 |
| Padding after the last resident byte | 736 | 64 |
| Maximum packed IMA3 payload | 93432 bytes | 94458 bytes |
| Maximum samples / nominal 8-kHz duration | 249152 /31.144 s | 251888 /31.486 s |

This frees 1024 physical RAM bytes. Packed capacity grows by 1026 bytes:
the extra 1024-byte region also makes the old two-byte bank-2 remainder
usable in complete three-byte groups. This is a modest 1.10% audio-capacity
increase, not a change to the codec's compression ratio.

Four aligned rows use `8380..83FF`; seven use `A020..A0FF`. The remaining
78 rows use `AA00..B3BF`, and bank 2's audio can start at `B400` (visible at
`F400` when paged). The 256-byte PCM pointer table and all pulse/extraction
code stay at their old addresses. Bank 5's contended modulation table,
TR-DOS workspace, loading stack and bank 7's shadow display are unchanged.
Startup-only use of the audio area during loading is unchanged.

Assembler assertions prevent rows from overlapping instructions or audio.
Seven audio loads, all six idle blocks and the calibration maximum of 260 T
padding end startup at `8365`, before `8380`. For an externally requested
larger filler, the builder avoids the startup gap; a 300-T fixture reserves
13568 bytes. The ordinary converter's bounded calibration always uses the
13312-byte layout. The old placement remains available internally through
`build_disk(..., compact_tables=False)` for baseline reproduction.

## Timing and verification

The saved [comparison](experiments/ima-3bit-memory/comparison.json) records
the complete checks. Reproduce with:

```powershell
python audiobook-beeper/verify_ima3_memory.py --input audiobook-beeper/experiments/ima-3bit-direct --output build/ima3-memory --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

The verifier checks all 712 IMA transitions, reconstructs the original
player byte for byte, compares every pulse/extraction instruction byte and
counts every native output interval against the independent instruction
schedule. The ordinary phase totals remain
`417,413,458,413,417,446,409,446` T: **427.375 T/sample before and after,
delta 0 T**. Byte-page transitions still add 14 T and bank transitions
140 T, both delta 0 T. No new lookup instruction is executed. Native
counts exclude contention, TR-DOS ROM work and physical disk latency.

The actual cold-Fuse comparison requires every output bit and every relative
output timestamp across both complete reference loops to equal the old
trace. Only that exact equivalence permits reusing the saved source-clock
SNR and normal listening WAV. A separate full-capacity fixture appends
synthetic silence to the original recording and checks all seven banks,
including the newly available bank-2 area. It does not claim a longer real
recording, calibrated audio quality for the capacity fixture or physical
hardware verification.

Both complete cold-Fuse checks pass: 5981841 outputs /373760 predictor-index
samples for the original excerpt, and 8060417 outputs /503776 samples at full
capacity. The latter loads 429 sectors before playback and performs no disk
reads during playback. Both retain all 32 progress steps and hide the loading
message. Exact reference timing preserves 20.159645/20.159651 dB, mean PDM
127652.961 Hz and speed error -0.299133%. The old 64-level model independently
passes 262145 native outputs on an 8192-sample silent fixture.

Use [the compact-table reference disk](../ZX-audiobook-IMA3-compact-tables.trd).
The old reference disk remains available. New conversions select the compact
placement and the larger capacity automatically; no extra command-line flag
or Spectrum-side unpacking pass is required.
