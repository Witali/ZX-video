# Accuracy-guarded dark fills for source-line drawings

2026-10-14. The user chooses contour drawings with source-close solid colour
fills and asks for higher accuracy without losing compression. The previous
qualified977-frame sea-foam disk at`78b7a7be` is the complete matched baseline.

## Qualified result

- [Root TRD](../../../ZX-video-sea-foam-lineart-dark_part01.trd)
- [Full97.7-second native-reference/AY preview](disk-dark-evidence/native-preview.mp4)
- [Full original / previous drawing / new drawing comparison](disk-dark-evidence/accuracy-comparison.mp4)
- [Six difficult scenes](disk-dark-evidence/host-probe/comparison.png)
- [Qualification and exact costs](disk-dark-evidence/qualification.json)
- [All-frame accuracy and quiet-motion measurements](disk-dark-evidence/accuracy-comparison.json)
- [Native timing and independently dirty cold boot](disk-dark-evidence/timing.json)
- [Failed/superseded checks and regression fixture](disk-dark-evidence/attempts/)

The same977 frames/97.7 seconds retain10 fps,256x192 native resolution and
all4885 original50-Hz AY updates. Every changed pixel strictly reduces its
original RGB error. Existing source-detector lines, black regions and actual
coloured pixels remain exact.342,800 logical samples improve on963 frames.
Mean active native RGB MSE falls6885.659687 ->6025.180072(12.4967%). This
measures colour error for the requested drawing style; it is not a visual,
photographic or semantic recognition percentage.

| Complete matched measure | Previous drawing | Dark fills |
| --- | ---: | ---: |
| CB46/LZSA2 before invisible-attribute selection | 658,097 bytes | 624,535 bytes |
| Final selected compressed stream | 626,964 bytes | 591,481 bytes |
| Actual allocated disk data sectors | 2541 | 2399 |
| Free data sectors | 3 | 145 |
| Deterministic selected LZSA2 core | 62,140,081 T | 58,364,356 T |
| Runtime verified sector reads | 2450 | 2311 |
| Combined ROM/disk/IRQ/ULA read service | 68,229,686 T | 64,420,510 T |
| Combined seek service | 1,655,691 T | 1,567,780 T |
| Missed nominal five-field deadlines | 0 | 0 |
| Maximum in-field publication deviation | 17 T | 23 T |

Final stream saving35,483 bytes(5.6595%);142 fewer allocated sectors(36,352
bytes). Dictionary, startup and sector allocation are included in the actual
disk comparison. The new disk uses2399/2544 sectors(94.3003%); intentionally
keep the same source extent for this accuracy/compression comparison rather
than spending the saved space on a different input. This is not a maximum
duration or minimum disk-count claim. TRD SHA256:
`ec6fe8d13b986400dcf6b722aa5e9575ff3f3c5c0245ea4aeb2dd31a2f672dd0`.

## Algorithm and limits

Use `--video-codec cb41 --fps 10 --colour-policy lineart --lineart-dark-fills`.
The new flag is optional; ordinary`lineart`, existing defaults, source
preparation and audio fitting remain unchanged.

The earlier black classifier required every RGB component<=64, in addition
to the same60-RMS source distance used for colour fills. This makes some
dark brown/blue detail into white holes even when black is the closest legal
endpoint. The flag admits coherent black candidates within RMS60 and maximum
component100, the existing colour-fill limits. It still rejects lone samples
and neutral65/65/65 or100/100/0, which exceed the RMS limit. It does not
broaden any red/yellow/other colour bound or generate dither.

Additional black can force a white/colour cell to sacrifice its old colour.
Compare the proposed **rendered pixels** with the current-frame old drawing.
If any pixel gets worse/equal error while changing, or an old coloured pixel
changes, reject whole source-connected added dark components touching that
cell, then rerender. Rejection is monotonic; the original drawing is the
guaranteed feasible fallback. Reject nine proposed source samples over the
whole977-frame input.441,545 accepted added dark samples include some already
black detector-line pixels;342,800 actually change. A rejected region is not
cut at a cell boundary. Every mask uses current source RGB, with no delayed
colour history. Native lines remain two pixels wide; no one-pixel arbitrary
bitmap or new chip/player function is introduced.

Quiet-source motion is measured on6,454,423 consecutive-frame samples whose
source maximum component change<=4. RGB residual variation falls1614.039170
->1414.350569. Opponent-chroma variation29.012656 ->29.041162 rises slightly
(about0.098%); do not claim every temporal metric improves. Existing coloured
pixels remain exact at every frame. Inspect the full motion comparison plus
boy, king, general character scenes and dark interiors.

## Verification and reproduction

All57 tests pass, including real frame460: the unguarded candidate harms
five existing pixels, while the connected-region rollback preserves colour
and component shape. Complete independently dirty-RAM Fuse1.9.0 playback
compares6,753,024 screen bytes and every4885 AY record, zero dropped/missing/
duplicate fields, underruns, nominal misses or late runs. Zero accumulated
drift; the fallback jitter allowance is not needed.2311 runtime sectors,
zero retries; read-call range22,323..134,473 T. Native packet, clock and cell
instruction listings match the earlier player exactly: new instruction delta
0 T. Their absolute instruction counts remain in both release metadata.
The selected LZSA2 core count is independently measured with256-byte output
quotas and excludes IRQ, ULA, paging and physical disk. Full delivery timing
including those costs is measured separately in Fuse, not inferred from
decoder savings. Physical hardware is untested.

Both media files confirm977 frames at10 fps,97.7 seconds of picture and audio.
They render exact native references with unchanged AY chip-model WAV; they
are not Fuse recordings. Original RGB, all AY controls and entire model WAV
match the previous qualified97.7-second input byte for byte.

The preceding same-hue NORMAL/BRIGHT search changes zero samples on all977
frames; preserve and reject it as an accuracy upgrade in`feasible-evidence`.
The first dark review overconstrains old *classified* colour samples which
were actually white; correct that check to preserve rendered colours. The
unguarded dark review then hits a real pixel regression, independently
reproduced at frame460. Preserve both logs, original unguarded producer and
fixture; neither partial attempt qualifies as a release. Add component
rollback and rerun every image/transport/native gate from scratch.

Run`dark_probe.py --input disk-attempts/capacity-1005/cache-inputs.npz --output
NEW --lzsa EXE`, then`build_dark_disk.py --image-cache NEW --compact-cache
AUTHENTICATED_COARSE --one-disk --verification fuse PREPARED --plan PLAN
--output BUILD --frames 977` with the existing runtime arguments. The build
wrapper checks the source selector hash and every reused RGB/history byte.
Run`compare_dark_disk.py`, the existing`analysis/sea_foam/preview.py`, then
`archive_dark_disk.py`; their full arguments and exact producer snapshots are
preserved in`disk-dark-evidence`. The154 measured files/109,149,355 bytes plus
manifest include complete release, host probe and unsuccessful attempts.
Keep the old qualified disk. This is verified progress toward the active
accuracy goal, not proof of a globally optimal drawing encoder.
