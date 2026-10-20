"""Read-only audit of the retained DHA C library's precision and provenance.

This does not import the tester's research modules, fit a model, encode audio,
execute Z80 code, or modify the inspected repository. Its exhaustive numeric
check covers the complete declared q domain, not a selected audio excerpt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


MODEL_SHA = "70582ffa6ec234742248acd008bda13795f5243a884681f496af87bd6609260f"
ANS_SHA = "af7cef130c9edf04d1da1944678314a4cd5e2c7d6957ded64f0cc5f028fa7ce8"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path("C:/Work/z80-tester"))
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    source_root = args.source_root.resolve()
    output = args.output.resolve()
    library = "audio/lib/dha-codec/"
    history = "audio/music/sea-foam/recorded-difference-history/"
    paths = [
        library + "include/dha_codec.h",
        library + "src/dha_decode.c",
        library + "src/dha_encode.c",
        library + "src/dha_common.c",
        library + "src/dha_tables.inc.h",
        library + "README.md",
        library + "FORMAT.md",
        history + "src/probe.py",
        history + "README.md",
    ]
    texts: dict[str, str] = {}
    sources = []
    for relative in paths:
        raw = (source_root / relative).read_bytes()
        canonical = raw.replace(b"\r\n", b"\n")
        texts[relative] = canonical.decode("utf-8")
        sources.append(dict(path=relative, bytes=len(raw), sha256=digest(raw),
                            canonical_lf_sha256=digest(canonical)))

    def cite(relative: str, anchor: str, after: int = 0) -> dict:
        lines = texts[relative].splitlines()
        matches = [i for i, line in enumerate(lines) if anchor in line]
        if len(matches) != 1:
            raise AssertionError((relative, anchor, matches))
        start = matches[0]
        return dict(path=relative, line=start + 1, end_line=start + 1 + after,
                    excerpt="\n".join(lines[start:start + 1 + after]))

    table_source = texts[library + "src/dha_tables.inc.h"]
    tables = {}
    for name, count, expected in [("dha_default_model", 1024, MODEL_SHA),
                                  ("dha_default_ans", 512, ANS_SHA)]:
        match = re.search(name + r"\[\d+\]\s*=\s*\{(.*?)\};", table_source, re.S)
        assert match is not None, name
        values = [int(value) for value in re.findall(r"-?\d+", match[1])]
        raw = bytes(value & 255 for value in values)
        assert len(raw) == count and digest(raw) == expected
        tables[name] = dict(bytes=count, sha256=digest(raw),
                            minimum=min(values), maximum=max(values))

    q = list(range(-256, 255))
    pcm = [(((value + 257) // 2) - 128) * 256 for value in q]
    raw_q_pcm = [value * 128 for value in q]
    assert len(q) == 511 and len(set(pcm)) == 256
    assert all(value % 256 == 0 for value in pcm)
    assert sorted(set(out - raw for out, raw in zip(pcm, raw_q_pcm))) == [0, 128]
    # For every legal predictor output, verify the simpler ceil(q/2) form
    # independently of the positive-offset division used in the C source.
    assert all(out == -((-value) // 2) * 256 for value, out in zip(q, pcm))

    references = dict(
        public_state=cite(library + "include/dha_codec.h", "typedef struct { int16_t q;"),
        public_rounding=cite(library + "include/dha_codec.h", "DHA uses the exact unsigned8 R2R rounding", 2),
        q_range=cite(library + "src/dha_decode.c", "if (prediction < -256", 1),
        returned_pcm=cite(library + "src/dha_decode.c", "value = (((q + 257)", 0),
        raw_fallback=cite(library + "src/dha_decode.c", "if (decoder->frame.kind == DHA_FRAME_PCM16)", 6),
        q_commit=cite(library + "src/dha_decode.c", "decoder->state.q = (int16_t)q;", 4),
        pdm_state=cite(library + "include/dha_codec.h", "typedef struct { uint8_t accumulator; }", 0),
        pdm_algorithm=cite(library + "src/dha_decode.c", "sum = (unsigned)state->accumulator + pcm8;", 2),
        encoder_objective=cite(library + "src/dha_encode.c", "difference=(((q+257)/2)-128)*256-(int)target;", 3),
        encoder_defaults=cite(library + "src/dha_encode.c", "options->beam_width=64;", 4),
        copied_tables=cite(library + "src/dha_common.c", "memcpy(info->model,dha_default_model", 2),
        raw_q_api=cite(library + "include/dha_codec.h", "exact signed predictor outputs, before R2R/PDM rounding.", 7),
        training_input=cite(history + "src/probe.py", "folder=ROOT/'build/audio/capacity-stage25-five-ans-full'", 3),
        training_fit=cite(history + "src/probe.py", "h=np.zeros((len(q),4),float)", 13),
        training_excerpt=cite(history + "README.md", "The selected example plays the complete", 6),
        documented_training_scope=cite(history + "README.md", "An independent least-squares fit uses all", 8),
        source_clock=cite(history + "README.md", "**800 T at20MHz**:399T parser plus401T synthesis.", 4),
        library_quality_scope=cite(library + "README.md", "files and the complete saved Z80 trajectory. No analog or SNR/SER assessment", 1),
        container_scope=cite(library + "FORMAT.md", "DHAF stores the existing DHA1 difference predictor", 5),
    )
    report = dict(
        schema=1, date="2026-10-19", source_root=str(source_root),
        scope="Static C/API/provenance audit plus exhaustive integer enumeration of all 511 declared q values; no native execution, encoding, fitting, resampling, or quality measurement.",
        source_repository_modified=False, sources=sources, tables=tables,
        precision=dict(q_min=-256, q_max=254, internal_distinct_q=511,
                       public_predictive_distinct_pcm16=256,
                       public_predictive_low_zero_bits=8,
                       public_predictive_pcm16_range=[min(pcm), max(pcm)],
                       raw_q128_distinct_pcm16=511,
                       raw_q128_pcm16_range=[min(raw_q_pcm), max(raw_q_pcm)],
                       public_minus_raw_q128_values=[0, 128],
                       all_q_verified=len(q),
                       pcm16_fallback_preserves_input=True),
        pdm=dict(order=1, target_bits=8, accumulator_bits=8,
                 clock_owned_by_caller=True),
        encoder=dict(beam_width=64, gain_candidates=8, lookahead=2,
                     rate_penalty=82.0, allow_pcm_fallback=True,
                     loss_target="Rounded unsigned-PCM8 R2R output represented as PCM16; not unrounded q*128.",
                     source_adaptive="Residuals, reconstructed history and gains are selected by the same bounded search for each source; built-in model coefficients and ANS table are not refitted by this API."),
        model_provenance=dict(
            trained_on_song=True, source_independent_training_corpus=False,
            song="Stay with us, boy / In the Blue Sea, in the White Foam",
            excerpt_seconds=[56, 71], sample_rate=25000, training_samples=375000,
            features=["q1", "q1-q2", "q1-2*q2+q3", "q1-3*q2+3*q3-q4"],
            fit="Ordinary least squares, target=reference/128-q1; no intercept or ridge; separately nearest-even rounded table rows.",
            coefficients=[-0.03965039152806261, 0.8990253695520664,
                          0.463045998278022, 0.26278664629475357],
            training_fan2_sha256="8cbc8c0079752c2c2e86359372ba0b0cd9428df674606c41d76b0d36ab61857a",
            training_q_sha256="42afa1edc87d54737ff3aa1c6e7cf6b1b8b10bdc9b71dd671fb72e5adaf2b6ff",
            training_reference_sha256="cc26f695ab5b0aa954e40886f11d8707434859779eeb77971d7d5f6343065a21",
            actual_training_run_repeated=False),
        timing=dict(source_documentation_only=True, predictor_tstates=401,
                    parser_tstates=399, sample_tstates=800, clock_hz=20000000,
                    sample_rate=25000, native_repeated_by_this_audit=False,
                    zx_448t_port_proved=False,
                    note="Source firmware timing is reported from the retained project; it is not our Spectrum player, a lower bound on a redesigned implementation, or a native proof performed here."),
        decision="Use fixed defaults as a separately labelled codec baseline if benchmarked. Do not call its predictive PCM16 buffer full-16-bit precision, infer source-independent training, or transfer its 25-kHz R2R SER to the current 8-kHz EAR disk. A raw-q9 adapter changes the loss target and needs its own controlled measurement.",
        references=references,
    )
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(source_files=len(sources), model_sha256=MODEL_SHA,
                          all_q_verified=len(q), predictive_pcm_levels=256,
                          native_execution=False), indent=2))


if __name__ == "__main__":
    main()
