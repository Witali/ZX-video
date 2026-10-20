# Integrated encoding acceleration: complete corpus

On 2026-10-20 the user requested faster encoding and decoding while preserving the data format. This run uses the integrated native preparation and faster standalone C waveform selection through the original nine-source matched encoding driver. It authenticates the entire previous matched experiment before and after running.

Every complete IMA stream, complete NWFB001 workset, encoding-prior WAV, decoded PCM16 hash, final predictor/index, search iteration count and clipping guard remains identical for all nine original sources. The total is1,195,520 samples. The model, source clock, search parameters, source bytes and original silent guards are unchanged. No quality filter rendering or emulator playback is repeated because the audio bytes are identical; this is no new TRD or release acceptance.

See report.json for all source times. The old elapsed times are historical observations from the previous matched experiment; they are not simultaneous paired timing measurements. This driver has the same workload in both runs. Separate native preparation and C search benchmarks document controlled phase comparisons.

Reproduce with `python audiobook-beeper/experiments/song-snr/codec_speed_integration.py --output NEW_EMPTY_DIRECTORY`. All source producers and their SHA256 values are frozen in producer-source/ and configuration.json; optimized/ contains the original driver snapshots, per-source reports and compressed IMA outputs.
