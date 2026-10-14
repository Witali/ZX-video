# Continuous RAM playback in the song TRD

Implemented2026-10-14 from main `89cf9f01`. The user explicitly asks to fix
the current TRD so sufficient RAM removes the pauses between parts. The new
root `ZX-music-Sea-Foam-RAM-auto.trd` replaces the earlier raw-sector cache
image, SHA256 `f3c131ba4fae9618e150016fc6d4a08b408203d0728408cc8b8a45d2f8bae771`.
Earlier images/evidence remain in Git. This is one independently bootable disk.
Generic audio converters, movie formats and old reference disks are unchanged.

The entire720,000-sample prepared main song is encoded once. Its WAV hash is
`bf4fb30cf4b0019764f8a9b10f7af44eb19293710947124911624d4da13a00aa`.
Original IMA beam32/block64, PDM beta0.5/extent1 and423-T holds remain.
The source gain/filter/cut is unchanged. There are no inserted fades, guards,
predictor/index resets or duplicate code/table loads between old parts.
Only384 silent alignment/EOF samples follow the complete90-second source.
The continuous360,192-byte stream uses1407 sectors. Six directory entries
accommodate TR-DOS's255-sector file limit; physical audio remains contiguous.

## RAM and loading

Bank2 reserves16 KiB for code, resident tables, descriptors and256-byte bounce.
Bank5 reserves16 KiB for lookup tables, TR-DOS/IRQ workspace and stack.
Bank7 preserves the6912-byte shadow screen and supplies its remaining9472 bytes
to audio. Banks0,4,6,1,3,7 hold the beginning in ordinary RAM; physical8 upward
hold the continuation. No expanded PCM/PDM buffer or transient part controller
is needed. All distinct available pages can be used, bounded by actual EOF.

| Machine | Available audio bytes | Song refills | Actual first audio | Largest live hold |
|---|---:|---:|---:|---:|
| Spectrum128 |91,392 |3 |27.349 s |287 T /80.916 us |
| Scorpion256 |222,464 |1 |45.607 s |308 T /88.000 us |
| Pentagon512 |484,608 |0 |69.180 s |277 T /77.288 us |
| Pentagon1024 |1,008,896 |0 |69.800 s |277 T /77.288 us |

Times include cold boot, real Fuse ROM/floppy execution and ULA waits. Startup
still exceeds60 seconds when preloading the whole song; this is the authorized
RAM-first tradeoff. On both Pentagons, every source-bearing output interval is
checked: no RAM copies, refills, floppy/ROM calls or multi-second part gaps.
The measured song lasts90.256 s including EOF guard, with7981.572 Hz source
rate (-0.230345%). Rate gates remain2%;128 is+0.040739%, Scorpion+0.798152%.
Spectrum128 has explicit refill pauses16.044/15.851/15.188 s; Scorpion has one
23.490-s pause. Those pauses are recorded in the complete trace and excluded
only from the separately labelled continuous sample-rate calculation.

Each three-byte descriptor stores7FFD, source high byte and Scorpion1FFD.
Every source slice ends atFFFF. The live bank tail walks a fixed-RAM descriptor,
pages the source and resumes the pending pulse; it never uses the lookup SP
for calls. AF', main/alternate registers, predictor, decoder row and feedback
survive. An insufficient-RAM batch boundary saves all live registers and SP,
silences output, loads the next contiguous sectors and restores the exact
pending decode/output state. TR-DOS always runs with normal RAM selected.

The actual cartoon title appears before tables/audio. Its top160 lines survive
loading and playback; the lower bar counts exactly the audio sectors in each
RAM batch. A short batch may advance several cells per sector. It reaches32
after the required sectors, and END OF AUDIO appears in the footer.

## Deterministic instruction counts

Counts are from the Z80 instruction timing table, excluding ULA/ROM/floppy.
Ordinary samples stay423 T on128/Scorpion and449 T on either Pentagon,
delta0 from the previous adaptive player. The existing Pentagon pacing is
JP10 +4 NOPs16 +original JP(IY)8: delta26 from the original423-T player.
Page crossing stays extra14 T, delta0.

The old ordinary-bank tail costs107 T including its final JP(HL); the new
descriptor tail costs210 T, delta+103. Shared handoff overhead53 T replaces
the ordinary20-T tail, so old bank extra140 becomes243 T. The affected hold
is174 T before,277 T after, delta+103. Scorpion replaces JP10 with3 NOPs12
plus LD BC,1FFD10 and OUT12: extra24 T, tail234 T, bank extra267 T, affected
hold301 T and delta+127 against old174 T. These are sparse bank-boundary
holds; ordinary per-sample pacing is unchanged.

The210-T tail is:

```
LD (nn),HL16; LD HL,(nn)16; LD A,(HL)7; OR A4; JP Z10;
LD (nn),A13; INC HL6; LD D,(HL)7; LD E,n7; INC HL6;
LD A,(HL)7; INC HL6; LD (nn),HL16; LD HL,(nn)16;
JP10; LD BC,nn10; LD A,(nn)13; OUT12; EXX4; SCF4;
EX AF,AF'4; OUT12; JP(HL)4.
```

Native checks require every continuous hold to match the independently
constructed page/bank schedule exactly. Physical reload timing is measured
separately by Fuse; stubbed native ROM latency is never presented as hardware.

## Complete verification and reproduction

Four native and four independently cold Fuse song runs verify all11,526,111
source/guard pulses and720,382 predictor/index states per machine, all bank
transitions, complete source order, code/table guards, cover/bar and EOF.
Native cold loading compares every stored audio byte with its exact disk
sector. Ten regression tests include distinct/aliased RAM detection, allocation,
short loading bars, exact live holds and preserved refill state. No prefix run
qualifies. Reports, actual output timestamps, complete debugger traces, all
assembly/data/configuration and source/packed identities are in [evidence](evidence).

The long control extends the non-silent song with silence to512,000 bytes,
crossing physical bank32 on Pentagon1024. Aliasing would overwrite earlier
non-silent song banks. It verifies the complete1,024,000-sample control in
native/Fuse, including7FFD bit5 and the512K refill/capacity boundary. See its
separate report; it does not replace the actual song proof.

With NumPy, Pillow, z80, pyz80, FFmpeg and Fuse available, from the repo root:

```powershell
$env:PYTHONPATH='audiobook-beeper;toolkit'
python -m unittest discover -s audiobook-beeper -p test_stream_trd.py
python -m unittest discover -s audiobook-beeper -p test_ram_cache.py
python audiobook-beeper/build_stream_trd.py `
  --prepared audiobook-beeper/experiments/sea-foam-song/evidence/prepared-song.wav `
  --cover audiobook-beeper/experiments/ram-audio/evidence/verified/cover.scr `
  --output new-continuous-song
python audiobook-beeper/verify_stream_trd.py new-continuous-song `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe' --jobs 4
python audiobook-beeper/experiments/seamless-trd/measure_audio.py new-continuous-song
python audiobook-beeper/experiments/seamless-trd/check_high_bank.py `
  --song new-continuous-song `
  --cover audiobook-beeper/experiments/ram-audio/evidence/verified/cover.scr `
  --output new-high-bank-control --fuse 'C:/Program Files (x86)/Fuse/fuse.exe'
```

Use a fresh output or the exact authenticated input resume. `--captured` is
an explicit recheck of saved complete same-image/same-command Fuse traces,
not a new emulator run. The first harness counted the terminal beeper-mute
OUT as a source pulse and expected too few refill page events. The corrected
postflight verifies that one additional teardown OUT separately, preserves
every source pulse/interval and checks the first descriptor after each refill.
The unchanged complete traces are retained with the failed harness logs.
Earlier assembly padding and short-bar failures are retained as diagnostics;
forcing the final byte and repeated exact progress subtraction fixed them.

The full verified Pentagon512 timeline is rendered as `output-pentagon512.wav`.
Strict unfitted fixed-clock SNR is-3.085 dB, below the unchanged20-dB gate.
The original uncompensated model remains a listening preview; pause removal
does not claim a sound-quality release or subjective cure for earlier flutter.
No physical Spectrum/clone hardware has been tested.
