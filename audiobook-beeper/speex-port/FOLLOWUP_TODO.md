# Further audio optimization worklist

Authorized 2026-10-04. Continue in `codex/speex-port`, based on `9ef19e9`.
The baseline is exact mode-3 Speex `pure-r4`: 2759257254 T for 186880
samples, 14764.861 T/sample, 16010 table bytes in a 16-KiB arena.
Target: mono 8-kHz PCM8 to an 8-bit port on a nominal 3.5-MHz Z80.

- [x] **7. Specialized table multiplication.** Patch four immediate offsets
  once per sample. Check exact products, full speech and allowed code writes.
  Selected: [round 07](rounds/07/REPORT.md), -400 T/sample, exact output.
- [x] **8. Coefficient table preparation.** Avoid rebuilding unchanged pages;
  reduce loop overhead. Include construction in complete decoder timing.
  Selected: [round 08](rounds/08/REPORT.md), -157151780 T on full speech.
- [x] **9. Port-only output.** Remove validation-only PCM16 stores and unused
  pointer work. Preserve internal precision and every PCM8 output.
  Selected: [round 09](rounds/09/REPORT.md), -16564288 T and -320 state bytes.
- [x] **10. Approximate synthesis.** Try reduced sample precision with compact
  products; measure speed and distortion against exact Speex and the source.
  Reject if quality or sustained throughput is unsuitable.
  Rejected: [round 10](rounds/10/REPORT.md), faster but 26.93x over budget.
- [ ] **11. Periodic wavetable synthesis.** Try a bounded offline-prepared
  waveform representation and a Z80 playback kernel. Charge tables, parameters,
  transitions and scheduling. This changes the stored format, not Speex.
- [ ] **12. Predictive VQ playback and selection.** Reuse the existing waveform
  codebook experiment. Implement and verify complete PCM8 port playback with
  uniform pacing, including all input-bank and stream boundaries. Compare
  CPU, stored size, RAM and audio quality with the other candidates.

For each item save a report under `rounds/07` through `rounds/12`, update
this checklist and root CHANGELOG, and make a focused commit. Test a bounded
candidate first, then the complete control speech for each selected version.
Record failed/rejected candidates as well. Select exact and approximate
results separately; never claim a faster different codec is exact Speex.
All proposed cycle savings remain estimates until executed and audited.
No PDM, disk release or physical-hardware qualification is requested.
