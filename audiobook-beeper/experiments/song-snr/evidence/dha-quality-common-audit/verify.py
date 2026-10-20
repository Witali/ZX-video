"""Authenticate saved DHA quality outputs and already completed terminal jobs.

No codec, filter, score, encoder or native player is executed. Only the new
audit folder is written. After initial capture, its retained logs support
verification from another checkout without the original temporary folder.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path, PureWindowsPath
import shutil
import struct
import wave
import zlib


NAMES = ["sea_foam", "silence", "quiet440", "loud3000", "steps", "quiet997",
         "multitone", "speech", "entertainer"]
MODEL_SHA = "199a17a9967bfbb941099039f32a47192af8933faf37cf015047abb51bfb9a7b"
PRODUCER_SHA = "823abcd6e79937709192046561e461075949c885bf4644810188bd7ba8929fab"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def read_wave(path: Path, width: int) -> tuple[bytes, int]:
    with wave.open(str(path), "rb") as stream:
        assert (stream.getnchannels(), stream.getsampwidth(), stream.getframerate()) == (1, width, 8000)
        count = stream.getnframes()
        return stream.readframes(count), count


def capture(folder: Path, evidence: Path, temporary: Path):
    """Copy original bytes once; never rewrite the nine existing score folders."""
    files = [(temporary / name, folder / "execution" / name)
             for name in ("before.json", "execution.json")]
    files += [(temporary / name / filename, folder / "execution" / name / filename)
              for name in NAMES[1:]
              for filename in ("score.stdout.log", "score.stderr.log", "terminal-exit.json")]
    files += [(evidence / "dha-quality-common" / name / "manifest.json",
               folder / "quality-manifests" / (name + ".json")) for name in NAMES]
    for old, new in files:
        assert old.is_file() and not new.exists(), (str(old), str(new))
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(old, new)
    producer = gzip.decompress((evidence / "dha-quality-common/sea_foam/producer.py.gz").read_bytes())
    assert digest(producer) == PRODUCER_SHA
    destination = folder / "sources/dha_host_score.py"
    assert not destination.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(producer)


def classify(row: dict) -> str:
    measured = row["filtered"]
    if measured["signal_rms"] == 0:
        assert measured["snr_db"] is None
        return "undefined SNR: zero reference signal; zero error" if measured["error_rms"] == 0 else "undefined SNR: zero reference signal"
    if measured["error_rms"] == 0:
        assert measured["snr_db"] is None
        return "exact after fixed edges: zero error, mathematically infinite SNR"
    assert measured["snr_db"] is not None
    return "finite unfitted SNR"


def verify_container(data: bytes, source: bytes, decoded: bytes) -> dict:
    """Independently check frame CRCs/counts and every raw fallback sample."""
    assert data[:4] == b"DHAF" and struct.unpack_from("<HH", data, 4) == (1, 1572)
    assert zlib.crc32(data[:1568]) == struct.unpack_from("<I", data, 1568)[0]
    rate, channels, frame_size, samples = struct.unpack_from("<IHHQ", data, 8)
    assert (rate, channels, samples) == (8000, 1, len(source))
    position, offset, sequence = 1572, 0, 0
    frames, counts = [0, 0], [0, 0]
    while position < len(data):
        assert data[position:position + 4] == b"DHF1"
        size, seq, count, channel, kind = struct.unpack_from("<IIHBB", data, position + 4)
        bits = struct.unpack_from("<I", data, position + 24)[0]
        assert seq == sequence and channel == 0 and kind in (0, 1)
        assert 0 < count <= frame_size and size >= 32 and position + size <= len(data)
        payload = data[position + 32:position + size]
        assert zlib.crc32(data[position:position + 28] + payload) == struct.unpack_from("<I", data, position + 28)[0]
        if kind == 0:
            assert bits == count * 16 and len(payload) == count * 2
            wanted = b"".join(struct.pack("<h", (value - 128) * 256)
                              for value in source[offset:offset + count])
            assert payload == wanted == decoded[offset * 2:(offset + count) * 2]
        else:
            assert len(payload) == (bits + 7) // 8
        frames[kind] += 1
        counts[kind] += count
        position += size
        offset += count
        sequence += 1
    assert position == len(data) and offset == len(source)
    return dict(predictive_frames=frames[1], PCM16_fallback_frames=frames[0],
                predictive_samples=counts[1], PCM16_fallback_samples=counts[0],
                header_frame_CRCs_counts_and_fallback_samples_rechecked=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--capture-from", type=Path)
    args = parser.parse_args()
    folder = Path(__file__).resolve().parent
    evidence = args.evidence_root.resolve()
    if args.capture_from:
        capture(folder, evidence, args.capture_from.resolve())
    assert digest((folder / "sources/dha_host_score.py").read_bytes()) == PRODUCER_SHA
    authenticated, manifests, rows, source_hashes = [], [], [], []
    total_samples = 0
    for name in NAMES:
        out = evidence / "dha-quality-common" / name
        captured_manifest = folder / "quality-manifests" / (name + ".json")
        assert captured_manifest.read_bytes() == (out / "manifest.json").read_bytes()
        manifest = load(captured_manifest)["artifact_files"]
        actual_names = {p.name for p in out.iterdir() if p.is_file() and p.name != "manifest.json"}
        assert set(manifest) == actual_names
        manifests.append(dict(source=name, sha256=digest(captured_manifest.read_bytes()),
                              artifacts=len(manifest)))
        for relative, item in manifest.items():
            raw = (out / relative).read_bytes()
            assert len(raw) == item["bytes"] and digest(raw) == item["sha256"]
            authenticated.append(dict(path="dha-quality-common/" + name + "/" + relative, **item))
        report = load(out / "report.json")
        assert report["complete"] is True and report["source"] == name and report["sample_rate"] == 8000
        producer = gzip.decompress((out / "producer.py.gz").read_bytes())
        assert digest(producer) == report["producer_sha256"] == PRODUCER_SHA
        source_path = evidence / "general/inputs" / (name + ".wav")
        source, count = read_wave(source_path, 1)
        assert count == report["source_samples"] and digest(source) == report["source_PCM8_sha256"]
        assert digest(source_path.read_bytes()) == report["source_WAV_sha256"]
        packed = gzip.decompress((source_path.with_name(name + ".ima.gz")).read_bytes())
        assert len(packed) == report["frozen_IMA4_bytes"] and digest(packed) == report["frozen_IMA4_sha256"]
        assert len(packed) * 2 == count
        trial = evidence / "dha-common-host" / name
        decoded, decoded_count = read_wave(trial / "decoded.wav", 2)
        assert decoded_count == count and digest((trial / "decoded.wav").read_bytes()) == report["DHA_WAV_sha256"]
        container = (trial / "audio.dhaf").read_bytes()
        assert digest(container) == report["DHA_file_sha256"]
        verified = verify_container(container, source, decoded)
        c = report["container"]
        for key in ("predictive_frames", "PCM16_fallback_frames", "predictive_samples", "PCM16_fallback_samples"):
            assert verified[key] == c[key]
        assert len(container) == c["file_bytes"]
        assert digest(container[32:1056]) == c["model_sha256"] == MODEL_SHA
        assert digest(container[1056:1568]) == c["ans_sha256"]
        total_samples += count
        codecs = {}
        for row in report["rows"]:
            assert row["samples"] == count
            if row["codec"] == "DHA":
                assert digest(decoded) == row["PCM16_sha256"]
            codecs[row["codec"]] = dict(filtered_snr_db=row["filtered"]["snr_db"],
                                         filtered_error_rms=row["filtered"]["error_rms"],
                                         raw_bit_exact_after_edges=row["unfiltered"]["bit_exact_after_edges"],
                                         semantics=classify(row))
        rows.append(dict(source=name, samples=count, DHA_bytes=c["file_bytes"],
                         frozen_IMA4_bytes=len(packed), **verified, codecs=codecs))
        source_hashes.append(dict(source=name, source_PCM8_sha256=digest(source),
                                 source_WAV_sha256=digest(source_path.read_bytes()),
                                 frozen_IMA4_sha256=digest(packed),
                                 DHA_file_sha256=digest(container),
                                 DHA_decoded_PCM16_sha256=digest(decoded),
                                 DHA_decoded_WAV_sha256=digest((trial / "decoded.wav").read_bytes())))
    execution = load(folder / "execution/execution.json")
    assert execution["complete"] and execution["song_unchanged"] and execution["all_manifest_producer_hashes_verified"]
    assert [row["source"] for row in execution["rows"]] == NAMES[1:]
    exits = []
    for row in execution["rows"]:
        saved = load(folder / "execution" / row["source"] / "terminal-exit.json")
        assert saved == row and row["exit_code"] == 0 and row["producer_sha256"] == PRODUCER_SHA
        assert (folder / "execution" / row["source"] / "score.stderr.log").read_bytes() == b""
        lines = (folder / "execution" / row["source"] / "score.stdout.log").read_text().splitlines()
        assert json.loads(lines[-1])["source"] == row["source"]
        exits.append(dict(source=row["source"], exit_code=0, elapsed_seconds=row["elapsed_seconds"]))
    before = load(folder / "execution/before.json")
    assert before["producer_sha256"] == PRODUCER_SHA
    original_song_hashes = {PureWindowsPath(path).name: value for path, value in before["song_files"].items()}
    current_song_hashes = {p.name: digest(p.read_bytes()) for p in (evidence / "dha-quality-common/sea_foam").iterdir() if p.is_file()}
    assert original_song_hashes == current_song_hashes
    assert len(manifests) == 9 and len(authenticated) == 36 and total_samples == 1195520
    result = dict(complete=True, audit_date="2026-10-20", scoring_execution_timestamp_recorded=False,
                  scope="Completion/provenance audit only. No encoder, filter, score or native player rerun; nine immutable result folders untouched.",
                  nine_sources_complete=True, quality_manifests=manifests,
                  authenticated_quality_artifacts=authenticated,
                  source_and_codec_hashes=source_hashes, total_source_samples=total_samples,
                  score_producer_sha256=PRODUCER_SHA, common_model_sha256=MODEL_SHA,
                  completed_remaining_eight_jobs=exits,
                  remaining_eight_elapsed_seconds=sum(row["elapsed_seconds"] for row in exits),
                  all_remaining_eight_terminal_exit_codes_zero=True, song_unchanged=True,
                  existing_song_files_sha256=current_song_hashes, rows=rows,
                  interpretation="Ideal multilevel DAC only. Song score includes predominantly PCM16 fallback and all bytes are charged. Common-model predictive mode regresses on quiet tones, speech and Entertainer; no universal quality or player acceptance.",
                  audit_producer_sha256=digest(Path(__file__).read_bytes()))
    save(folder / "report.json", result)
    files = {p.relative_to(folder).as_posix(): dict(bytes=p.stat().st_size,
                sha256=digest(p.read_bytes())) for p in sorted(folder.rglob("*"))
             if p.is_file() and p.name != "manifest.json"}
    save(folder / "manifest.json", dict(complete=True, artifact_count=len(files), artifact_files=files))
    print(json.dumps(dict(complete=True, source_samples=total_samples,
                          quality_artifacts=len(authenticated), quality_manifests=len(manifests),
                          terminal_exit_codes=[row["exit_code"] for row in exits],
                          elapsed_seconds=result["remaining_eight_elapsed_seconds"],
                          song_unchanged=True, no_measurement_repeated=True), indent=2))


if __name__ == "__main__":
    main()
