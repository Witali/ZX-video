# Round 11: periodic waves with noise and transitions

2026-10-04. Implement the user's waveform-table idea as an explicitly new
format on the same 186880-sample PCM8 source. For each 160-sample block,
fit integer periods 24..144 to a 32-entry quantized wave. Use one of sixteen
noise amplitudes for poorly periodic blocks. Store eight transition samples
blended from the previous endpoint to the new waveform, avoiding an abrupt
block start. Record: phase step (2), noise level (1), wave (32), transition (8).

1168 records occupy 50224 bytes, plus a charged 4096-byte noise dictionary:
**54320 bytes / 3.440:1 versus PCM8**. RAM tables 4136 bytes, kernel state 6.
Raw source SNR is **9.897 dB**, without gain fitting or delay. This metric
does not measure perceived intelligibility and is not directly comparable
to an unaligned speech-codec score. Retain the preview for listening.

The actual Z80 assembly kernel reconstructs all 186880 bytes exactly as
the independent host model. Cost is **35620 T/block, 222.625 T/sample**,
41604160 T for all kernels. This is below the 437.5-T budget only as a
component measurement. A complete block (4370 instructions) matches the
independent Zilog table. Writes are restricted to six state bytes and stack.
The initial serialized record-size assertion caught a NumPy integer-array
serialization error; explicit PCM8 packing fixed it before native execution.

Host record loading is excluded: no Z80 stream reader, bank transitions or
uniform output scheduler has been implemented for this rejected candidate.
Consequently **no complete real-time decoder is claimed**. Select neither
this format nor the approximate Speex as default: test the existing VQ
waveform reconstruction next, whose previous quality measurements are much
stronger. The periodic representation saves storage, but loses substantial
waveform detail and is not a direct implementation of Speex.

Reproduce with `wavetable_experiment.py`. Native and host audio agree;
`build/speex-port/wavetable/periodic.wav` is the listening preview. See
[report](report.json), [kernel](decoder.s), and [encoder/verifier](../../wavetable_experiment.py).
