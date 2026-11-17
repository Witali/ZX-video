"""Train the FP32 clash model on legal corrections to decoded screens."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from io import BytesIO
import json
import os
from pathlib import Path
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

import numpy as np
from PIL import Image
import torch
from torch import nn

from .__main__ import convert
from .clash import ClashCells, clash_layout
from .evaluate import independent_decode
from .model import CLIC_WIDE_WEIGHTS, OUTLINE_WEIGHTS, PIXEL_ART_WEIGHTS, load_weights, predict
from .photo_corpus import read_div2k
from .screen import COLS, PAIR_COUNT, ROWS, prepare
from .subject import SubjectDetector

SEED = 773


def create_baselines(path, archives, detector_path, workers):
    """Write the source and existing SCR before teaching any correction."""
    detector = SubjectDetector(detector_path)
    photo, art, outline = map(load_weights, (CLIC_WIDE_WEIGHTS, PIXEL_ART_WEIGHTS, OUTLINE_WEIGHTS))

    def make(item):
        index, (split, name, image) = item
        pixel_art = index % 2 == 0
        source = prepare(image)
        screen, _ = convert(
            source, "hybrid" if pixel_art else "spatial", art if pixel_art else None,
            probability=detector.predict(image), pixel_art=pixel_art,
            photo_layers=photo if pixel_art else None, outline_layers=outline if pixel_art else None,
            floyd=True, repair=True,
        )
        png = BytesIO()
        Image.fromarray(source).save(png, "PNG")
        info = dict(id=name, split=split, pixel_art=pixel_art, source_sha256=sha256(image.tobytes()).hexdigest())
        return info, png.getvalue(), screen

    samples = ((split, name, image) for split, archive in zip(("train", "validation"), archives, strict=True)
               for name, image in read_div2k(archive, split))
    with ZipFile(path, "w", ZIP_DEFLATED) as archive, ThreadPoolExecutor(workers) as pool:
        manifest = []
        for i, (info, png, screen) in enumerate(pool.map(make, enumerate(samples))):
            manifest.append(info)
            archive.writestr(f"{i}/source.png", png)
            archive.writestr(f"{i}/baseline.scr", screen)
        archive.writestr("manifest.json", json.dumps(manifest))


def targets(source, screen):
    preview = independent_decode(screen)
    geometry = ClashCells(source)
    attrs = np.frombuffer(screen[6144:], np.uint8).reshape(ROWS, COLS)
    y, x = np.nonzero(geometry.active(preview))
    labels = np.zeros((ROWS, COLS, PAIR_COUNT), dtype=np.float32)
    if len(y):
        pairs = np.broadcast_to(np.arange(PAIR_COUNT), (len(y), PAIR_COUNT))
        scores, _ = geometry.candidates(preview, geometry.locks(preview, None), y, x, pairs)
        legal = np.isfinite(scores).any(axis=-1)
        costs = scores[legal]
        probability = np.exp(-(costs - costs.min(axis=-1, keepdims=True)) / .10)
        labels[y[legal], x[legal]] = probability / probability.sum(axis=-1, keepdims=True)
    return geometry.features(attrs, preview), labels


def training_data(path, workers):
    with ZipFile(path) as archive, ThreadPoolExecutor(workers) as pool:
        manifest = json.loads(archive.read("manifest.json"))
        if (len({item["source_sha256"] for item in manifest}) != len(manifest)
                or len({item["id"] for item in manifest}) != len(manifest)):
            raise ValueError("training and checkpoint selection must contain distinct photos")
        parts = [item["split"] == "train" for item in manifest]
        if not any(parts) or all(parts) or any(item["split"] not in ("train", "validation") for item in manifest):
            raise ValueError("expected a training and a validation split")

        def read(i):
            with Image.open(BytesIO(archive.read(f"{i}/source.png"))) as image:
                source = np.asarray(image.convert("RGB"))
            return targets(source, archive.read(f"{i}/baseline.scr"))

        x, y = map(np.stack, zip(*pool.map(read, range(len(manifest))), strict=True))
    return x, y, np.asarray(parts), manifest


def train(path, output, device, epochs, workers):
    if device == "cuda":
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        torch.backends.cudnn.conv.fp32_precision = "ieee"
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(workers)
    torch.manual_seed(SEED)
    generator = torch.Generator().manual_seed(SEED)
    started = perf_counter()
    inputs, targets_, training, manifest = training_data(path, workers)
    x = torch.from_numpy(inputs).permute(0, 3, 1, 2).contiguous().to(device)
    y = torch.from_numpy(targets_).permute(0, 3, 1, 2).contiguous().to(device)
    layers = [nn.Conv2d(i, o, k, padding=k // 2, dtype=torch.float32)
              for i, o, k in clash_layout(64)]
    model = nn.Sequential(layers[0], nn.ReLU(), layers[1], nn.ReLU(), layers[2]).to(device)
    select = np.flatnonzero(~training).tolist()
    learned = np.flatnonzero(training).tolist()
    counts = (targets_.sum(axis=-1) > 0).sum(axis=(1, 2))
    if counts[training].sum() == 0 or counts[~training].sum() == 0:
        raise ValueError("expected successful repairs in both splits")
    print(f"Teacher repair cells: {counts[training].sum()} train, {counts[~training].sum()} validation", flush=True)
    learned = [i for i in learned if counts[i]]
    preparation_seconds = perf_counter() - started
    optimizer = torch.optim.AdamW(model.parameters(), lr=.0015)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=.00015)

    def loss(indices):
        expected = y[indices]
        return -(model(x[indices]).log_softmax(1) * expected).sum() / expected.sum()

    with torch.no_grad():
        initial_loss = loss(select).item()
    best_loss = float("inf")
    history = []
    started = perf_counter()
    for epoch in range(1, epochs + 1):
        for order in torch.randperm(len(learned), generator=generator).split(8):
            optimizer.zero_grad(set_to_none=True)
            loss([learned[i] for i in order]).backward()
            optimizer.step()
        schedule.step()
        with torch.no_grad():
            validation = loss(select).item()
        history.append(validation)
        if validation < best_loss:
            best_loss, best_epoch = validation, epoch
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"Epoch {epoch}: validation {validation:.4f}", flush=True)
    optimization_seconds = perf_counter() - started
    model.load_state_dict(best_state)
    with torch.no_grad():
        device_logits = model(x[select]).permute(0, 2, 3, 1).cpu().numpy()
        cpu_logits = model.cpu()(x[select].cpu()).permute(0, 2, 3, 1).numpy()
    arrays = {f"{kind}{i}": getattr(layer, kind).detach().numpy()
              for i, layer in enumerate(layers) for kind in ("weight", "bias")}
    numpy_layers = [(arrays[f"weight{i}"], arrays[f"bias{i}"]) for i in range(len(layers))]
    actual = np.stack([predict(frame, numpy_layers) for frame in inputs[~training]])
    np.testing.assert_allclose(actual, cpu_logits, atol=1e-4, rtol=2e-5)
    np.testing.assert_allclose(device_logits, cpu_logits, atol=1e-4, rtol=2e-5)
    with output.open("wb") as file:
        np.savez_compressed(file, **arrays)
    return dict(device=device, gpu=torch.cuda.get_device_name() if device == "cuda" else None,
                torch=torch.__version__, seed=SEED, epochs=epochs, channels=64, dtype="float32",
                workers=workers, train_images=int(training.sum()), validation_images=int((~training).sum()),
                train_cells=int(counts[training].sum()), validation_cells=int(counts[~training].sum()),
                best_epoch=best_epoch, initial_loss=initial_loss, best_loss=best_loss, validation_history=history,
                preparation_seconds=preparation_seconds, optimization_seconds=optimization_seconds,
                parameters=sum(p.numel() for p in model.parameters()), bytes=output.stat().st_size,
                sha256=sha256(output.read_bytes()).hexdigest(), sources=manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baselines", type=Path, required=True)
    parser.add_argument("--div2k-archives", type=Path, nargs=2, metavar=("TRAIN", "VALID"))
    parser.add_argument("--subject-model", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--weights", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    if min(args.epochs, args.workers) < 1:
        parser.error("--epochs and --workers must be positive")
    inputs = {p.resolve() for p in (args.baselines, *(args.div2k_archives or ()), args.subject_model) if p}
    outputs = {args.weights.resolve(), args.report.resolve()}
    if len(outputs) != 2 or inputs & outputs:
        parser.error("use separate paths for sources, weights and report")
    if not args.baselines.exists():
        if not args.div2k_archives or not args.subject_model:
            parser.error("provide DIV2K archives and a subject model to create the baseline archive")
        create_baselines(args.baselines, args.div2k_archives, args.subject_model, args.workers)
    report = train(args.baselines, args.weights, args.device, args.epochs, args.workers)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
