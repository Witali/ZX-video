# Round 12: complete, paced PVQ PCM8 port playback

2026-10-04. Reuse the existing PVQ3x1024 half-predictor dictionary and indices
on the same 186880-sample speech (source hash in report). The new assembly
player handles the entire memory stream, all bank switches and the partial
last vector. It outputs directly to an 8-bit DAC decoding the low byte FB.
This is **a different stored codec**, not an exact Speex optimization.

## CPU and scheduling

Unpaced full playback costs **16897348 T**, **90.418 T/sample**, including
startup, stream parsing, output, paging and loop control. Steady twelve-sample
cost is `(8*34 + 3*150 + 363)/12 = 90.416667 T/sample`. The former partial
1024-entry probe cost 100.25 T for decoding plus 21 T for OUT/driver,
121.25 total: the comparable steady saving is **30.833 T/sample (25.43%)**.
Its 51/193/216-T decoder paths become 34/150/363 including output; the new
363-T boundary also includes bank handling and group control.

The selected paced version emits **all 186880 samples**, with **every one
of the 186879 intervals exactly 437 or 438 T**, including banks 0,1,3,4,6
and the four-sample tail. With first OUT as origin, event i is exactly
`437*i + floor(i/2)` T: no accumulated drift, zero late nominal deadlines,
maximum phase error 0.5 T early. CPU cost including startup is 81760062 T;
first/last OUT are 499/81760061 T. The startup cost is not hidden.

Input banks hold 16380 bytes, four unused bytes per full bank, so each
five-byte group remains contiguous. The bank-check subroutine costs exactly
143 T including RET on every path; caller CALL adds 17. Spare slot time uses
PUSH/POP AF (21), CP n (7) and NOP (4), preserving decoder registers. Regular
slots 34 T, new-vector slots 150 T and group-start slots 363 T are padded
to the alternating schedule. No PDM or timer interrupt is involved.

## Storage, quality and verification

Stored stream 77870 + dictionary 3072 + header 32 = **80974 bytes**, or
**2.3079:1 versus PCM8**. Bank padding adds 16 resident bytes for this input;
it is not serialized. The record-specific book is charged in full. Tables
occupy **4614 RAM bytes**, paced code **935**, state **1**, reserved stack
**256**. Compressed payload resides in five 16-KiB banks; code/book/stack are
in the fixed 8000..BFFF bank. Code size is 387 bytes without pacing (+548
for timing). The original book/index hashes are recorded for provenance.

Every native PCM8 byte matches the scalar recurrence, without clipping or
wrapping. Raw source SNR is **23.510 dB**, unchanged by pacing; previous
filtered-codec metric was 24.348 dB and uses a different measurement filter.
The periodic-wave experiment's raw SNR was 9.897 dB. Select VQ when PCM8
playback speed and waveform preservation matter more than Speex's 8:1 ratio.

Guards restrict writes to the single state byte and private stack; every
input bank, code and static table remains unchanged. Additional complete
1/2/3/11/12/13-sample runs verify tails and zero complete-group startup.
An instruction-by-instruction audit covers startup and the first bank
transition: 2264 instructions / 20624 T match the independent timing model.
Index-half instructions use the established Z80 prefix-plus-register count
(8 T); these are undocumented mnemonics, emitted explicitly because sdasz80
rejected them. Other instruction counts follow the Zilog timing table.

The first pacing run exposed a bank-switch path ten T too short; an explicit
10-T jump equalized it before final full verification. The rejected trace
was not treated as a timing pass. Saved output timestamps allow independent
checking of every final deadline.

**Scope:** nominal 3.5-MHz native Z80 only. ULA contention, a physical DAC,
TR-DOS/disk delivery and hardware are unverified. In particular the full
payload uses contended banks on a Spectrum 128; constant CPU instruction
counts do not establish physical output timing there. No release TRD or
complete Spectrum hardware claim follows.

Run `pvq_port.py` to rebuild, replay, audit and save the preview under
`build/speex-port/pvq/pvq.wav`. [Report](report.json), [assembly](decoder.s),
[image](player.ihx), [map](player.map), [full timestamps](out-times.u64.gz),
[stored audio](audio.pvq.gz), [generator/verifier](../../pvq_port.py).
