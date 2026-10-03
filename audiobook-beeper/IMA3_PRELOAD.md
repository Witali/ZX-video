# Three-bit IMA disk with fast expansion

This experiment stores the project's three-bit IMA subset on disk, expands
small blocks directly into resident four-bit IMA, then runs the existing
direct PDM player. It preserves the complete 186880-sample control excerpt
(23.36 s at 8000 Hz), including its silent loop guard. The duration remains
limited by the expanded resident data; disk compression does not add RAM.

Use Spectrum 128 with Beta Disk/TR-DOS (tested in Fuse). Boot the TRD from
reset. The screen shows **LOADING AUDIO DATA**, disk-reading progress and
IMA expansion progress; the loading message disappears before playback.
The excerpt repeats automatically without disk access during playback.

Disk: [ZX-audiobook-IMA3-PDM-test.trd](../ZX-audiobook-IMA3-PDM-test.trd).
Saved [results](experiments/ima-3bit-preload/report.json) and
[Fuse audio](experiments/ima-3bit-preload/result-preview.wav).

The final version includes PC-side timing compensation. Its actual output
measures **18.171 / 18.153 dB** over two full loops, with **-0.04327%** mean
speed error. This is a listening preview; it does **not** reach the 20-dB
goal or replace the higher-fidelity four-bit waveform experiment.

## Storage and memory

`ADPCM3-step6` is the even-nibble subset described in
[the decoder study](DECODER_OPTIMIZATION_ROUNDS.md). The mapping
`IMA_nibble = code << 1` is exact. The disk contains 70080 compressed audio
bytes, versus 93440 expanded bytes: 25% fewer audio bytes and a nominal
5.333:1 ratio relative to PCM16. Sector padding adds 64 bytes. This is
not a claim of 5.333:1 compression for the complete bootable disk.

The independently bootable disk occupies 473 file sectors, versus 517 for
the corresponding ordinary IMA disk: 44 sectors / 11264 bytes saved after
paying for the preloader and its screen/tables. A TRD container itself
remains the standard 655360-byte image, with more free sectors.

Thirteen blocks reuse a 6144-byte input buffer at 6000..77FF in bank 5.
Most expand to 8192 bytes; the two final partial blocks produce 1280 and
2048 bytes. The full output occupies banks 0/4/6/1/3, the upper 9472 bytes
of bank 7, and the upper 2048 bytes of bank 2. Screen 7 and the final
player/table/ROM workspace allocation are the existing 128-KiB layout.

Preloader code starts at 8000, lookup pages occupy 9000..93FF and the
initial screen occupies 9400..AEFF. A temporary trampoline at 6000 reloads
the player only through B7FF, preserving bank 2's final B800..BFFF audio.
The player loads its screen and tables, then uses the already resident IMA.
No preceding disk, retained RAM, PCM buffer or complete PDM buffer is needed.

## CPU and verification scope

The unchanged round-3 expansion core is **285 T/eight samples**. Its full
23360 groups cost 6657600 T. Actual preloader CPU work, including screen
setup, disk-call wrappers, block control and progress, is **6896434 T**
(1.944355 s), excluding the stubbed ROM service and ULA. The earlier
standalone round-3 total was 6657930 T; integration adds **238504 T** to
that CPU benchmark, with no change to the 285-T core.

Playback is unchanged: **423 T per ordinary sample**, +14 T per page and
+140 T per bank, each delta 0. The final calibrated silent tail uses 1273 balanced
output pairs and a 67-T pad; native cycle cost is 79122530 T (2 T less
than the uncorrected pilot's 69-T pad). Clock/ULA
timing must still be verified for this stream, not inferred from old data.

The native preloader checks every output byte, all seven final banks,
every 285-T group, unchanged code/tables and both 32-step progress bars.
A separate cold Fuse run checks every expanded byte with real TR-DOS,
progress and the handoff. It measures 11.064859 s inside the compressed
data ROM reads and **1.935179 s** in expansion blocks including ULA delays.
Preloader entry to player-ready is **18.720633 s**, including the subsequent
player/table loads; initial BASIC/bootstrap loading precedes this interval.
The conversion is below the **39.903992-s** budget (twice raw 128-KiB reads).

The compressed transport itself is lossless with respect to the selected
three-bit stream. That encoder is lossy relative to the source: the prior
codec-only result was 20.999 dB, below the four-bit waveform encoder's
fidelity. Exact unpacking does not promise equal listening quality.
Use the saved end-to-end quality report, not codec SNR, for the beeper result.

## Voice vibration correction and complete playback

The initial direct use of the earlier three-bit payload passed every byte,
bank and PDM check but scored only -3.004 dB against the fixed 8-kHz source
clock (18.522 dB against the time-warped reference). Its sample-time error
spanned about 20.14 ms over the excerpt, including the silent loop filler.
This number combines drift and local timing variation; it is not a claim
of a 20-ms periodic voice wobble. The user reported added voice vibration
while that uncorrected pilot's normal-speed recording was played.

[prepare_ima3_timing.py](prepare_ima3_timing.py) applies the existing
Lanczos time compensation on the PC, re-encodes the three-bit subset with
beam width 32, freezes the pilot's hot-row layout, and recalibrates the new
disk. It retains all 186880 source samples and the original source hash;
the reference is never shifted or gain-fitted to improve the score. A new
complete trace, rather than the pilot timeline, gives the final scores above.

Both native and cold Fuse runs check **5985253 PDM outputs and 373760
predictors/indices** across two loops. The complete Fuse cycles are
82891450 / 82891452 T: a 2-T cold transient, followed by exact repeat phase
at 1169 fields. There are no disk reads during playback; all paging and
loading-message checks pass. FFmpeg independently verifies every IMA sample.
The final normal-speed recording observes two wraps and matching bank latches.
No physical hardware test or perceptual claim that all vibration is gone is
implied by these numerical checks.

The first full-trace attempt paused before execution because a new Fuse
debugger variable contained an underscore. A minimal parser probe confirmed
the restriction. Only the owned test process was stopped; the variable was
renamed, then both complete playback checks were rerun successfully. This
was a verification harness error, not a freeze in the delivered player.

## Reproduce

Use the Python environment in [CONVERTER.md](CONVERTER.md); also include
`toolkit` on PYTHONPATH. The input files must be materialized, not LFS pointers.

```powershell
python audiobook-beeper/build_ima3_disk.py --input audiobook-beeper/experiments/decoder-rounds/ima3 --source-wav audiobook-beeper/experiments/ima-direct-weighted/source-preview.wav --output build/ima3-disk --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/verify_ima3_preload.py build/ima3-disk
python audiobook-beeper/verify_ima3_preload.py build/ima3-disk --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --raw128-report audiobook-beeper/experiments/ima-lpc-preload/raw128/report.json
python audiobook-beeper/verify_direct.py build/ima3-disk
python audiobook-beeper/verify_direct.py build/ima3-disk --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
python audiobook-beeper/analyze_voice_jitter.py build/ima3-disk --ffmpeg <ffmpeg.exe> --loop 0
python audiobook-beeper/analyze_voice_jitter.py build/ima3-disk --ffmpeg <ffmpeg.exe> --loop 1
python audiobook-beeper/prepare_ima3_timing.py --pilot build/ima3-disk --output build/ima3-compensated --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

Run the same native, cold preload, full playback and both analysis commands
against `build/ima3-compensated`; its new output times must be measured.
Record that verified final variant with:

```powershell
python audiobook-beeper/record_pcm.py build/ima3-compensated --fuse "C:/Program Files (x86)/Fuse/fuse.exe" --output build/ima3-compensated/sound-128 --machine 128
```

The assembler consumes [preloader](ima3-preload.asm) and
[handoff](ima3-handoff.asm) source separately; Python packages their binaries
and data. [The builder](build_ima3_disk.py) rejects arbitrary IMA nibbles
outside the three-bit subset. [The preloader verifier](verify_ima3_preload.py)
uses independent expected IMA bytes; the existing verifier checks playback.
