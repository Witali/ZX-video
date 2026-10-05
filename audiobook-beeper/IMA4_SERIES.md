# Sequential IMA4 audio disks

Updated 2026-10-05. Use the existing public converter:

```powershell
python audiobook-beeper/convert_audio.py "input.m4a" --codec ima4 --output build/ima4 --ffmpeg "path/to/ffmpeg.exe" --fuse "C:/Program Files (x86)/Fuse/fuse.exe"
```

The default `--disk-mode single` produces `audio.trd`, filled with consecutive
parts of the recording. `--disk-mode all` produces `audio-0001.trd`, etc.,
covering the selected input exactly once. Every disk boots independently.
`--duration N` bounds the source prefix. `--disk-mode preview` retains the
previous RAM-sized looping excerpt and its `audiobook-preview.trd` name.

Spectrum shows `LOADING AUDIO DATA` with 32 progress steps, hides that text,
and plays one part. It then loads the next part automatically. The last part
ends at `END OF AUDIO`; a nonfinal volume asks for the next numbered disk
and Space. The shared controller validates the recording and volume identity.
Disk reads occur only between parts, so loading pauses are audible. There is
no simultaneous floppy streaming or full PCM/PDM expansion in Spectrum RAM.

## Capacity and representation

Audio remains packed four-bit IMA: two codes per byte, decoded directly by
the existing player as it emits PDM. FFmpeg prepares an 8-kHz mono reference
on the PC; sequential mode uses one normalization gain for the selected
track. Each part has 10-ms boundary fades and at least 128 silent samples.
A short final part is padded, never repeated. Source ranges are contiguous.

The decoder's hot IMA rows depend on the recording. Cold rows occupy the
unused portions of bank-5 PDM tables, so each part stores its own complete
table files. Reusing another part's tables would change or corrupt decoding.
The builder preserves each independently qualified stream, row placement,
feedback model and live instruction addresses, changing only disk locations
and the final silent-tail exit.

| Disk allocation | Sectors of 256 bytes |
| --- | ---: |
| TR-DOS system track | 16 |
| BASIC boot | 1 |
| Shared transient controller | 8 |
| Volume header | 2 |
| Player and shadow screen, per part | 91 |
| Lower and upper tables, per part | 28 + 32 |
| Packed audio, per full part | 365 |

Four full parts each contain 93440 packed bytes /186880 prepared samples.
The fifth uses the remaining 318 audio sectors, giving 81408 packed bytes
/162816 prepared samples. Total: **2560 sectors, zero free sectors**,
455168 audio bytes and 910336 prepared samples. Removing five 128-sample
guards leaves **909696 source samples /113.712 seconds**. A shorter input
uses fewer sectors. For longer input, all mode repeats the same allocation
on independently bootable volumes. A full part retains 23.344 seconds of
source; the final full-disk part retains 20.336 seconds.

## Memory and timing

The existing full player uses five 16-KiB banks, 9472 bytes of bank 7 and
2048 bytes of bank 2 for audio. Bank 2 still reserves 14336 bytes for resident
code/tables; bank 5 holds the other tables and TR-DOS workspace, while the
shadow screen occupies the rest of bank 7. No additional RAM reservation
reduces audio capacity. The 57-byte exit stub fits existing resident padding.
The 2048-byte controller loads at 4000..47FF only after sound stops, replacing
tables that the next part reloads. Header workspace is 4800..4BFF; the stack
at 6000 remains clear of TR-DOS workspace.

Live source-bearing paths retain **423 native T/sample, +14 T at page
transitions and +140 T at bank transitions**: delta **0 T** from the looping
player. No per-sample branch or table lookup is added. Loader progress runs
only during disk reads.

Only the final bank tail changes. `JP chain_exit` (10 T), `DI` (4),
`LD SP,nn` (10), `LD IY,nn` (14), `IM 1` (8), `XOR A` (4), and `OUT (n),A`
(11) clear the beeper after **61 native T**. The previous tail reached its
next output after 103 T without filler, a difference of **-42 T** between
these stop/continue endpoints. Its optional filler added 52 T per pair,
7 T for each nonempty block (including the first) and the recorded padding.
The exact old cost is `103 + 52*pairs + 7*ceil(pairs/255) + pad`. This exit omits
33 PDM pulses exclusively in the silent guard. CPU counts exclude ULA waits,
TR-DOS ROM and physical disk latency; emulator loading measurements are
reported separately.

## Conversion and verification

The same bounded quality search calibrates each part independently. Every
retained candidate must pass complete native and cold Fuse playback on two
loops. The final volume is then executed from a cold boot through every part
and the terminal screen: every output bit, predictor/index, bank, loading
indicator and progress event is checked. Its actual pulse timeline is
compared with either fully qualified preview loop and measured again against
the fixed 8-kHz reference, using float64 filtering. The limit remains 8 T for
every pulse after aligning the first output, with no skipped source interval.
If neither loop matches, the verifier qualifies the unchanged preview with
a complete native/cold two-loop run in the volume's naturally occurring
ROM/HALT entry phase. A debugger guard accepts only that phase before audio
starts; it neither edits CPU state nor shifts execution time. At most 32
cold starts are tried. Failure remains fatal. The chosen reference, loop and
all timing differences are recorded, including the first active scanline's
contention transient.

Mean playback speed must remain within 2%; first preparation and each loading
pause must remain below 60 seconds in Fuse. The default quality goal remains
20 dB; below-target but otherwise verified output is explicitly a preview
and returns exit code 2. No physical Spectrum certification is implied.

`report.json` records retained source, gain, quality and final verification;
`volumes.json` maps source parts to their disk structures. `work/` retains
per-part previews, selected binaries and rejected searches. `--resume` reuses
only authenticated complete parts with identical source/tool/settings/producer
hashes. An interrupted part is retained and regenerated. `--no-recording`
skips normal-speed host sound capture but keeps full execution checks and
measured-port listening WAVs. Use a Fuse build that writes debugger output
to the captured standard-output stream: the bundled SDL build's shared
`stdout.txt` is unsuitable for these verification scripts.

The layout/controller implementation is in `ima4_series.py`, using the
existing separately assembled `ima3-chain.asm` controller and shared series
verification. The legacy controller filename/signature remains unchanged;
the volume header uses `IMA4VOL1` to distinguish this disk format. IMA3's
default layout and the ordinary IMA4 preview binaries remain unchanged.
