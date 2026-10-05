# Round 09: exact port-only Speex

2026-10-04. Remove the 320-byte validation output buffer and its IY stores,
increments and saves. Keep the full-precision feedback sample in existing
asm_y; expose that word as _last_pcm16 so the verifier still compares every
internal PCM16 value as well as the emitted PCM8 byte.

Same complete speech: **2510789186 T**, delta **-16564288 T**;
**13435.302 T/sample**. Code 6624 (-33), state 1039 (-320), tables unchanged.
Exact instruction accounting: -87 T/sample, -64 T/40-sample call and
-6720 T once for the removed initialization: 186880*87+4672*64+6720
=16564288. First-frame audit: 1861567 T, delta -20896 T; every instruction
matches the independent Zilog table. Select for the user's port-only task.

Full speech, seven signal/capacity streams, products, entries, excitation
and cache-page tests pass. Internal PCM16 and every PCM8 output stay exact.
Relative to round 04 the cumulative saving is 248468068 T (9.005%); this
still needs 30.709 times the nominal real-time budget, before ULA/hardware.

Reproduce: `build.py --skip-host --variant pure-r9` and
`check_round.py --variant pure-r9`. See [report](report.json),
[checks](checks.json), [filter](filter.s), [transform](../../followup_opt.py).
