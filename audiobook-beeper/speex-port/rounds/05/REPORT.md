# Item 05: final verification

2026-10-04. Verify the selected `pure-r4` binary without changing decoder
instructions. Its image hash is
`bee20e8c7e86172d06af716d26f53fa353b569ee08b2c2b4785106fa1af0cc7e`.

All **1074400 PCM16 samples and PCM8 outputs** match the independent upstream
fixed-point Speex reference: 186880 speech samples, six 3200-sample signal
fixtures, 786400 samples at six-bank capacity, and 81920 samples from 512
deterministic random packets with valid mode-3 framing. Random packets test
decoder arithmetic, not speech quality. Their input/reference are archived.
The specialized host oracle also agrees with upstream for every random frame.

Directly compare compact LPC with the verified round03 recurrence on 1104
angle vectors: ordered random vectors, unordered vectors and extreme or
degenerate values. All ten coefficients agree in every case. Round04's
general and specialized primitive checks also pass: 65536 unsigned8 products,
10400 signed16 products, 25737 cosine angles, 3000 Q14 cases, 12 saturation
edges, 12048 signed8x16 cases, 5056 energy/shape pairs, 8448 innovation table
entries, 40960 coefficient entries and 12800 coefficient products.

Every CPU write in the full streams is inside declared state, stack or
dynamic-table regions. Compressed input, code and static tables stay intact.
State begins poisoned, exposing missing initialization. Zero frames,
unsupported prefixes and excessive frame counts all return the expected
status without unintended PCM output.

The first speech frame's instruction-table audit is 2016616 T. An additional
two-frame silence audit covers cache reuse: **3320178 T, 443264 instructions**,
each matching the independent instruction timing table. The complete speech
trace has 186880 OUT timestamps; count, endpoints, maximum interval and every
missed nominal deadline reconcile with the report. The table arena is exactly
16384 bytes. No arithmetic or decoder mismatch occurred.

Accept correctness for the tested mode and coverage; this is not a proof for
every possible stream. CPU-only real time still fails. No ULA/disk/hardware
playback claim is made. See [checks](checks.json),
[full speech timing](speech-report.json), [OUT trace](speech-out-times.u64.gz)
and [round04 checks](../04/checks.json).

```powershell
python audiobook-beeper/speex-port/check_round.py --variant pure-r4
python audiobook-beeper/speex-port/final_checks.py
```
