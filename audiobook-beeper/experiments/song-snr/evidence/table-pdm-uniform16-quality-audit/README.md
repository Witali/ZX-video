# Matched uniform-table quality audit

Executed2026-10-20 from existing cachedfloat64 arrays. No audio was re-encoded or rendered.

|Source|Canonical frozen IMA / uniform table dB|Matched IMA / uniform table dB|Change dB|
|---|---:|---:|---:|
|sea_foam|21.193927|22.781483|1.587556|
|silence|n/a|n/a|n/a|
|quiet440|4.597903|5.564858|0.966955|
|loud3000|19.231750|19.989988|0.758238|
|steps|-0.216154|2.100536|2.316690|
|quiet997|-0.804007|0.866545|1.670553|
|multitone|20.247278|21.624793|1.377515|
|speech|21.738939|23.817786|2.078847|
|entertainer|20.096678|21.567557|1.470879|

The delivered449T player has its own measured song score20.250315887dB. Its schedule is separate from both flat-uniform host controls above; no full native player claim follows. Silence uses absolute error RMS rather than SNR.

All9 sources retain original hashes, full sample counts and the final128 original silent samples. One frozen C preset uses width32, horizon128, commit64, regularization0.1, beta0.5 and extent0.5. The song remains360192 IMA bytes. All predictors, words and successor states are independently checked.

Waveform, known-tone and whole-error spectral diagnostics cover both same-clock controls at the declared bank/page/search/field frequencies, including0.48828125Hz for residentPCM8 banks. Fits are diagnostic only and never modify SNR. Short controls, rank-deficient fits and unreliable fundamental tracking remain inconclusive. Every numerical increase is retained in the comparison files; this is not unconditional artifact acceptance.

The host wrapper gained an explicit --packed-dir input after the canonical frozen-IMA archives. Both versions are frozen; their Python hashes differ intentionally while the C decoder and table bytes remain identical. The original incorrectly scaled host render is preserved by the prior audit and is not used in this comparison.

There is no integrated native IMA decode/bank/EOF/bootable-disk proof in this host quality result. Release and artifact acceptance remain false.
