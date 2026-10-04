# Round 17: complete nested throughput profile

2026-10-04. Profile the unchanged round16 binary and all 186880 speech
samples before choosing the next optimization. Native breakpoints observe
function entry/return without adding Z80 instructions. Count inclusive and
exclusive spans separately; nested callees are subtracted from their parent
and shared return addresses close all matching tail-call activations.
Caller CALL/JP overhead belongs to the caller, not the callee span.

| Largest exclusive category | T/sample | Share of total |
| --- | ---: | ---: |
| Coefficient products | 2680.000 | 23.136% |
| Decoder body (including excitation and packet work) | 1763.282 | 15.222% |
| Filter body outside observed callees | 1730.589 | 14.940% |
| Signed 8x16 products | 1606.093 | 13.865% |
| Coefficient preparation | 1427.169 | 12.320% |
| General 16x16 products | 893.856 | 7.716% |

The full JSON contains smaller categories and exact integer counts. All
exclusive categories plus 1548592 unprofiled startup/driver T reconcile
exactly to **2164784952 T**. All **186880 PCM16/PCM8 samples** remain exact,
the binary hash matches round16, and **every saved OUT timestamp is byte
identical** to the unprofiled run. The old filter/LPC inclusive totals also
match. Expected call counts pass: 1168 packets, 4672 filter/LPC/preparation
calls, 186880 sample splits and 1868800 coefficient products. No CPU speed
change is claimed: delta **0 T**.

Signed 8x16 multiplication is called 562373 times and costs 300146569 T.
Its current eight iterations separately shift the 24-bit accumulator and
multiplier. Next test a combined A:HL multiplier/accumulator, then skip
leading zero multiplier bits. It needs no additional table memory and keeps
the exact signed product; use the same complete input to select it. The
existing quarter-square 8x8 helper receives zero calls in this speech run,
so merely accelerating that helper would not help the measured decoder.

Reproduce with `profile_throughput.py --variant pure-r16`, after building
round16 and retaining its complete ordinary `report.json` and timestamps.
[Profile](profile.json), [script](../../profile_throughput.py),
[unchanged binary](../16/player.ihx). ULA, disk and physical hardware are
outside this nominal CPU profile. The average real-time goal is still unmet.
