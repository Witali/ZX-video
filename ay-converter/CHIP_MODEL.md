# Chip model and envelope playback

The public target is `--chip AY-3-8910` (default) or `--chip YM2149`.
The movie converter uses `--ay-chip`. Analysis, quantization, continuous
simulation, feedback and cache identities all use that choice. The historical
renderer filename `render_ym2149.js` also handles AY explicitly.

The [General Instrument manual](https://pub.intvprime.com/ba4ef/ie/Programming/AY-3-8910-8912-Programmable-Sound-Generator-Data-Manual.pdf)
defines three tone oscillators, one shared noise source, a Boolean mixer and
one shared envelope. Its register labels are octal: R10 is decimal 8, R13 is
decimal 11 and R15 is decimal 13. Enabling tone and noise combines their gates;
it does not add two independent analogue waveforms. Disabling both gates
holds the channel gate open; fixed zero volume is needed to mute it.

Fixed volume uses 16 codes. Bit 4 of decimal R8..R10 selects the shared
envelope instead. R11/R12 hold its 16-bit period; writing R13 starts/restarts
one of 16 shape actions. A period write preserves phase. The AY envelope has
16 effective DAC levels. The [Yamaha YM2149 manual](https://www.ym2149.com/ym2149.pdf)
specifies 16 fixed-volume codes and 32 envelope codes. The renderer uses the
vendored Ayumi DAC tables, continuous oscillators, noise LFSR and DC filter;
the analogue response of a particular Spectrum board is not calibrated.

With the selected direct clock, a complete envelope ramp lasts 256*P master
clocks; an alternating ramp pair lasts 512*P. Internal 32-step timing maps
to paired AY DAC levels. Hardware shapes are logarithmic DAC ramps, not ideal
linear triangles or sinusoids. Envelope-only synthesis is legal with the
tone/noise gates held open. Multiple envelope channels share period and phase.

The fitter evaluates complete waveforms for disjoint slow ramps and periodic
shapes, preserves shape phase across fields, and accepts source-objective and
headroom improvements. Fixed-volume voices remain available alongside ENV
voices. No arbitrary per-channel hardware envelope or extra PCM is emitted.

AY12 stores the AY9 fields plus R11/R12 and a shape action. Software shape
255 means no write; it is never sent to the bus. Fourteen-byte register records
retain the same action. Movie AYH2 uses 14 initial registers and 16 Huffman
contexts; ordinary AYH1 remains compatible. Explicit repeated R13 actions
are preserved even when the new shape equals the previous one. Video scaffold
padding never duplicates a restart.

## Deterministic instruction costs

Counts below use the Z80 instruction timing table and are checked in the
independent native core. They exclude IRQ entry, HALT, ULA contention,
TR-DOS ROM execution and disk latency.

| Resident sound path | Previous 11-register records | 14 registers, hold | 14 registers, restart |
| --- | ---: | ---: | ---: |
| Register routine | 867 | 1059 | 1099 |
| Ordinary field | 974 | 1166 | 1206 |
| Near bank end | 992 | 1184 | 1224 |
| Bank change | 1091 | 1283 | 1323 |
| Exact bank-end EOF | 1007 | 1199 | 1239 |
| Loop restart | 1079 | 1271 | 1311 |

Thirteen writes cost 1023 T; the shape-action tail costs 36 T when skipped
or 76 T on restart. The per-field increase is +192/+232 T. The existing
105-T loop-reset work is unchanged. Each 14-byte bank holds 1170 states,
16380 bytes, leaving four unused bytes; six banks hold 7020 states/140.4 s.
All resident disk reads finish before playback.

The movie IRQ remains 367+83*n T for n register writes (14 writes: 1529 T);
the queue-capacity comparison still costs 7 T. AYH2 adds three skipped
register checks of 20 T each, +60 T/decoded field. A present constant symbol
costs 167 T instead of a skipped 20 T, +147 T. Startup initialization adds
three writes at 78 T, +234 T before playback. AYH2 roots are page-aligned at
0x8300, versus AYH1 0x8200, within the existing memory reservation.

`test_chip_capabilities.js` independently checks all 16 shapes at four periods
against the manual step rules (4096 checks), phase holding/restarts, shared
envelope routing and the software sentinel. Native tests additionally cover
all data banks, EOF, loop restarts and movie AYH2/FIFO/IRQ execution. Full cold
Fuse register traces verify actual publication fields separately; normal-speed
emulator WAVs are listening evidence, not physical-chip measurements.
