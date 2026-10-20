# Audio resampling

- Convert new recorded audio directly from the original source to the firmware's native playback sample rate in one resampling pass.
- Do not resample through intermediate rates or resample an already resampled working copy. Preserve and reuse the original source for each output-rate variant.
- Apply anti-aliasing and interpolation filtering in that single conversion, and record the source, output rate, and resampler settings with the measurements.

# Shared audio balance

- Store the project default musical-role balance in the root `audio-settings.json`.
- Use its named role gains for new music firmware and requested balance updates, applied to the original score gains before envelopes and level quantization.
- Map gains by musical role (lead, piano accompaniment, bass, inner voice), independently of the hardware oscillator assigned to a note.
- Keep published firmware unchanged unless its update is requested. An explicitly requested alternative balance takes precedence over the project default.

# Firmware catalog

- Whenever creating a firmware image or a new version of an existing firmware, update the root `FIRMWARE-CATALOG.md` in the same focused commit.
- Add a catalog entry for each new retained variant. When replacing an existing version, update its entry to describe the resulting firmware accurately.
- Include links to the firmware files and documentation, and keep the relevant characteristics current: melodies, voice count, output mode, sample rate, PDM rate, and distinguishing features.
- Update the total image counts when adding or removing published images. Count a BIN/Intel HEX pair as one image; do not count duplicate copies or temporary build outputs as separate firmware.
- List only available firmware images as released variants; distinguish future plans and unbuilt experimental configurations from published firmware.
- Record measured quality in `FIRMWARE-CATALOG.md`: signal-to-noise or signal-to-error ratio, song-duration and tempo deviation, measurement conditions, and links to reports tied to the exact ROM. Distinguish digital analysis from physical-board measurements. Mark unavailable measurements explicitly instead of inventing values.

# Audio file layout

- Follow `docs/AUDIO-LAYOUT.md` when adding or moving audio files.
- Store experiments under `audio/<music|sound>/<program>/<experiment>/`; keep output mode and rate variants inside the experiment.
- Put source code in `src/`, canonical shared inputs in `audio/assets/`, and reusable audio code in `audio/lib/`.
- Reserve `<mode>/<rate>/release/` for ready, selected firmware. Keep other retained images and their replay data in `artifacts/`, with an explicit `candidate`, `experimental`, `historical`, or `reference` status. Store additional measurements and analysis in `reports/`.
- Use the root ignored `build/audio/<variant-id>/` directory for temporary assembly outputs, logs, and listening WAVs. Do not commit temporary build directories.
- Register every published audio image in `audio/catalog.json` with a stable ID, source entry point, songs, mode, rates, artifact paths, and exact ROM SHA-256. Keep `FIRMWARE-CATALOG.md` consistent with this registry.
- Keep canonical scores, samples, licenses, and provenance together; reuse identical source inputs across PDM/R2R. Generated release snapshots may remain with their ROM when required for independent replay.
- Preserve retained experiments as separate directories. Use Git history for revisions of one variant instead of date-stamped source copies.
- Resolve repository paths independently of the current working directory and avoid imports that accidentally select another experiment's same-named module.
- When migrating paths, keep a reproducible migration script and before/after hash inventory, update scripts/tests/document links, and verify that published BIN/HEX payloads remain byte-identical.
