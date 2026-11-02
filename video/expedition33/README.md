# Expedition 33 review film

This production captures the published `Expedition-33-Demo.trd` without input
injection or target changes. It includes the end of native loading, the whole
Lumiere and Alicia AY arrangements, the inter-track pause, all 18 illustrations
and the demo's native transitions. A separate four-second title and ending
identify the project and link to the online player. There is no narration.

The user initially required **local review before YouTube upload/publication**.
After revision 2 played without the reported clicks, they explicitly authorized
YouTube upload on 2026-11-03. The prepared bilingual
description starts with the online emulator link and includes the owner's
first-person tribute to the original game's creators. This approval applies
to revision 2; preserve its exact upload hash and resulting publication URL.

## Inputs and reproducibility

- Published source revision: `ee5609781e56513b7df28f86a24cedff85e5488a`.
- Disk SHA256: `fd8868220ad6e9f429fc367a9887a446adfccc9c230caa94f37b8805a5046db4`.
- Visual capture: Fuse 1.9.0, Spectrum 128 + Beta Disk, all native ULA fields
  recorded to FMF. The first review used its PCM16 44100 Hz ACB stereo output;
  the user reported left-channel clicks on note changes, absent on the website.
- Revision 2 replays the **same authenticated native AY port transactions**
  through the website's pinned Ayumi: AY DAC, ABC panning (0.1/0.5/0.9),
  1,773,400 Hz chip, DC removal, gain 0.7 and the website's 20 kHz RC filter.
  It does not modify any notes, volume envelopes, durations or target bytes.
  The audio renderer/configuration difference is established. The user reports
  that the revision-2 preview plays normally without the reported clicks.
  The user subsequently gave explicit permission for YouTube upload.
- Nominal field clock: `3546900 / 70908` Hz. Actual sample positions define
  trims and track chapters. The first Fuse recording emitted 881.8056806
  samples/field, equivalent to 50.0110183 Hz, with under one sample of residual
  phase error. Revision 2 synthesizes on the nominal native T-state clock,
  equivalent to 50.0211542 Hz, and maps visuals to those same fields.
- Final video: 1920x1080, 50 fps, H.264/AAC stereo. The native raster is enlarged
  by exactly four with nearest-neighbor sampling. Hardware border colors fill
  the remaining 16:9 frame. The native 320x240 capture is retained in full.
  The native video is sampled onto a 50 Hz presentation grid without
  changing audio speed; individual picture times can round by one output frame.
- Cinzel is pinned in `music-menu/artwork/font/` (SIL OFL). The literal URL on
  the title card uses Windows Consolas so its letter case remains legible.

Python needs the project's existing NumPy and Pillow packages. FFmpeg and
ffprobe must be on PATH. Use the existing qualified build directory, which
contains `build.json` and the exact independently bootable TRD. Example:

```powershell
py -3.12 video/expedition33/capture.py --fuse <fuse.exe> --build <qualified-build> --output .tmp/capture
py -3.12 video/expedition33/fmf.py .tmp/capture/capture.fmf --output .tmp/decoded
py -3.12 video/expedition33/render.py --capture .tmp/capture --decoded .tmp/decoded --output "C:/Work/YouTube Videos/Expedition33"
py -3.12 video/expedition33/verify.py "C:/Work/YouTube Videos/Expedition33/Expedition-33-ZX-Spectrum-Demo.mp4" --timeline "C:/Work/YouTube Videos/Expedition33/materials/work/timeline.json" --reference-audio "C:/Work/YouTube Videos/Expedition33/materials/work/soundtrack.wav" --output "C:/Work/YouTube Videos/Expedition33/materials/qa"
node video/expedition33/preview.mjs "C:/Work/YouTube Videos/Expedition33" 4196
```

Revision 2, using the retained qualification trace of the exact same TRD:

```powershell
py -3.12 video/expedition33/extract-ay.py <qualified-build>/fuse-demo/trace.txt.gz --output .tmp/ay-trace.json
node video/expedition33/ay-audio.mjs .tmp/ay-trace.json .tmp/capture/capture.json .tmp/ayumi-audio
py -3.12 video/expedition33/render.py --capture .tmp/capture --decoded .tmp/decoded --audio .tmp/ayumi-audio/ayumi.wav --filename Expedition-33-ZX-Spectrum-Demo-v2.mp4 --output "C:/Work/YouTube Videos/Expedition33"
node video/expedition33/preview.mjs "C:/Work/YouTube Videos/Expedition33" 4199 Expedition-33-ZX-Spectrum-Demo-v2.mp4
```

Use `verify.py` against the **v2 filename**, latest `materials/work/timeline.json`
and latest reference WAV, with reports under `materials/qa-v2`. The baseline is
preserved under `materials/revisions/01-fuse`. No recording-method information
belongs in the public bilingual description, as explicitly requested by the user.

Raw FMF, the lossless intermediate and capture identity belong under the
package's `materials/` tree. They are local supporting material, not uploads.
The canonical production scripts remain here in Git; the package also gets a
snapshot for revision. Do not commit or upload local emulator ROMs or binaries.

## Verification

`fmf.py` decodes actual bitmap/attribute slices and checks exact RGB matches
against all 18 checked-in native renders. `render.py` requires the disk hash,
unmodified cold autoplay and track-start fields `[0, 11254, 19140]`; it keeps
the source speed and every musical sample up to the next loop restart.
The complete stereo soundtrack is normalized once, preserving channel balance.

`verify.py` adapts the narrated-project-video skill's container, packet, full
decode, chapter and scene-audio checks for an instrumental film. The audio
language is `zxx`; fabricated speech captions and English-narration assertions
do not apply. It compares both decoded AAC channels with the normalized WAV
in every scene and extracts final encoded frames for visual review.

This is emulator footage, not physical-hardware footage. Native program bytes,
AY data, disk latency and target hot paths are unchanged: target T-state delta
is **0**. Published native timing qualification remains the separate evidence
in `music-menu/reports/demo/`.

Primary references reviewed for this production:

- [Official FMF format](https://sourceforge.net/p/fuse-emulator/wiki/FMF%20File%20Format/).
- [Fuse manual](https://fuse-emulator.sourceforge.net/man/html/fuse.html).
- [Game soundtrack credits](https://www.expedition33.com/post/composing-the-music).
- [YouTube chapters](https://support.google.com/youtube/answer/9884579).
- [YouTube thumbnails](https://support.google.com/youtube/answer/72431).
- [YouTube upload metadata](https://support.google.com/youtube/answer/57407).

The description uses three chapter starts, starting at 00:00, with at least
ten seconds per chapter. Short card/loading subdivisions are container chapters
only. The separate thumbnail is 1280x720 PNG. Keep the resulting upload and
publication status in the publication record.
