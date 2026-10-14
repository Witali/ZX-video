# Delivered loading/playback interface

Date:2026-10-14. `ZX-music-Sea-Foam-SNR20-RAM-auto.trd` is now the independently
bootable655360-byte image with SHA
`b96763cad15810d8d1755870f5a02ee2bfa1a708e787921fadf581f654a9e28e`.
`delivery.json` authenticates the worktree and main-folder copies. The
previousccab image remains in `../achieved-disk/`; the unsuccessful
frame-clock control55216119 remains in `../audio-ui-delivery/` and commit8db960a.

The light-gray loading bar uses attributes only. Centered `LOADING` cycles
through one/two/three dots every16 completed reads, including header reads
after the cover appears. This replaces ROM FRAMES, which barely advances
during actual TR-DOS reads. Physical read speed controls the animation's
wall-clock period; no elapsed-seconds or interrupt assumption remains.
Pentagon512/1024's green playback bar advances at bank handoffs, about4.105
seconds per full bank, without additional audio T-states.128/Scorpion retain
their existing live paging and update playback progress at refills/completion.

The complete public C CLI takes60.871331 seconds, including source/model
preparation, both encoders, assembly, unchanged-filter scoring and artifact
writing. Main waveform encoding takes26.677900 seconds; assembly/artifact
I/O2.195068 seconds. The original Python and C encoder sources are unchanged.
Source, cover, packed audio and decoder tables are exact; only the16-KiB
PLAYER disk file changes. The unfitted original-clock score stays
20.25031588676249 dB. Actual emulator verification is a separate cost.

Four whole native runs and two new complete installed-Fuse captures pass.
Each Pentagon verifies all11,526,111 source bits/relative timestamps and
720,382 predictor/index samples, zero refills/live ROM reads,92 strict dot
phases and22 independently checked global-prefix positions. The final bar
is full green. Both source timestamp arrays equal the authenticatedccab
clock byte for byte. Post-source final mute is219 vs201 T (+18 T/5.02us),
measured separately; source-bearing audio stays exact and the established
100-ms quality crop excludes this teardown interval. No physical-hardware
or completed universal noise-research claim follows from this UI release.

Ten standalone loading tests, eight focused player tests and four builder
tests pass. The maximum2392-sector layout retains18 startup/31 worker/
8 helper bytes spare without reducing audio RAM. Default/false disks and
metadata remain exact. Short multi-bank sources requiring more than two
live bar writes are rejected explicitly by this optional UI; compact
loader/UI combinations are also rejected. The default player remains available.

Reproduce with fresh output directories:

```powershell
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-delivery-sectors/generate.py `
  --output .tmp/reproduce-ui-sectors
python audiobook-beeper/experiments/song-snr/evidence/audio-ui-emulator-sectors/verify.py `
  --disk .tmp/reproduce-ui-sectors/audio.trd `
  --metadata .tmp/reproduce-ui-sectors/player.json `
  --packed .tmp/reproduce-ui-sectors/soundtrack.ima.gz `
  --output .tmp/reproduce-ui-sectors-execution `
  --fuse 'C:/Program Files (x86)/Fuse/fuse.exe'
```

`generate.py` reuses the immutable identity-checking generator while selecting
a new directory. `deliver.py` verifies all completed reports, independently
compares the entire source clocks and exact bar geometry, and then writes
the named copies. It refuses unexpected preexisting snapshot bytes.
`manifest.json` authenticates every saved delivery artifact except itself
and Python caches. The execution [README](../audio-ui-emulator-sectors/README.md)
describes observed-screen provenance and actual executable hashes; the
[player](../audio-ui-player-sectors/README.md) and
[loading](../audio-ui-loading-sectors/README.md) proofs separate deterministic
CPU counts from actual ULA/ROM/floppy execution.
