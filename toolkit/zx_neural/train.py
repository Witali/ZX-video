"""Reproduce the small attribute CNN with CPU PyTorch and a fixed source split."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

import numpy as np
from PIL import Image
import torch
from torch import nn

from .corpus import VALIDATION, read_source, training_sources
from .model import DEFAULT_WEIGHTS, LAYERS, load_weights, predict
from .objective import (
    COLOR_BUDGET, SEAM_WEIGHT, TARGET_TEMPERATURE, TEMPERATURE, TRAIN_SWEEPS,
    Candidates, features,
)
from .screen import HEIGHT, WIDTH, prepare

SEED = 433
VIEWS = 8
EPOCHS = 80


def augment(image, rng):
    """Rescale, move and recolor the source before computing its legal labels."""
    w, h = image.size
    width = max(1, int(w * rng.uniform(.56, 1)))
    height = max(1, int(h * rng.uniform(.56, 1)))
    left = int(rng.integers(0, w - width + 1))
    top = int(rng.integers(0, h - height + 1))
    image = image.crop((left, top, left + width, top + height))
    if rng.random() < .5:
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    pixels = prepare(image, crop=bool(rng.integers(2))).astype(np.float32)
    gain = rng.uniform(.74, 1.24, 3).astype(np.float32)
    return np.clip(pixels * gain + rng.uniform(-12, 12), 0, 255).astype(np.uint8)


def synthetic(rng):
    """Generate smooth ramps, narrow lines and overlapping shapes at random cell phases."""
    y, x = np.indices((HEIGHT, WIDTH), dtype=np.float32)
    a, b = rng.integers(0, 256, (2, 3)).astype(np.float32)
    ramp = (x / WIDTH * rng.uniform(.25, .8) + y / HEIGHT * rng.uniform(.2, .7)).clip(0, 1)
    rgb = a + (b - a) * ramp[..., None]
    for _ in range(9):
        left, top = rng.uniform(-24, WIDTH), rng.uniform(-24, HEIGHT)
        w, h = rng.uniform(3, 94), rng.uniform(3, 78)
        if rng.random() < .5:
            shape = ((x - left) / w) ** 2 + ((y - top) / h) ** 2 < 1
        else:
            shape = (x >= left) & (x < left + w) & (y >= top) & (y < top + h)
        rgb[shape] = rng.integers(0, 256, 3)
    return rgb.astype(np.uint8)


def dataset(cache):
    rng = np.random.default_rng(SEED)
    train_images = []
    source_hashes = {}
    for kind, name in training_sources():
        image = read_source(kind, name)
        source_hashes[name] = sha256(image.tobytes()).hexdigest()
        train_images.append(prepare(image))
        train_images.extend(augment(image, rng) for _ in range(VIEWS - 1))
    train_images.extend(synthetic(rng) for _ in range(32))
    validation = [prepare(read_source(kind, name)) for kind, name in VALIDATION]
    images = np.stack(train_images + validation)
    signature = sha256(images.tobytes()).hexdigest()
    cache_key = f"seam-v1:{signature}:{COLOR_BUDGET}:{SEAM_WEIGHT}:{TARGET_TEMPERATURE}:{TEMPERATURE}:{TRAIN_SWEEPS}"
    if cache and cache.exists():
        with np.load(cache, allow_pickle=False) as data:
            if data["signature"].item() == cache_key:
                return data["inputs"], data["base"], data["targets"], data["importance"], source_hashes, signature
    inputs, base, targets, importance = [], [], [], []
    for i, image in enumerate(images):
        candidates = Candidates(image)
        inputs.append(features(image, candidates))
        base.append(np.where(candidates.allowed, -candidates.regret / TEMPERATURE, -100.))
        target, weight = candidates.training_target()
        targets.append(target)
        importance.append(weight)
        if (i + 1) % 32 == 0:
            print(f"Prepared {i + 1}/{len(images)} teacher screens", flush=True)
    inputs, base, targets, importance = map(np.stack, (inputs, base, targets, importance))
    if cache:
        np.savez_compressed(cache, inputs=inputs, base=base, targets=targets, importance=importance, signature=cache_key)
    return inputs, base, targets, importance, source_hashes, signature


def train(output, cache, epochs):
    torch.manual_seed(SEED)
    torch.set_num_threads(4)
    torch.use_deterministic_algorithms(True)
    generator = torch.Generator().manual_seed(SEED)
    inputs, base, targets, importance, source_hashes, signature = dataset(cache)
    x = torch.from_numpy(inputs).permute(0, 3, 1, 2).contiguous()
    y = torch.from_numpy(targets).permute(0, 3, 1, 2).contiguous()
    prior = torch.from_numpy(base).permute(0, 3, 1, 2).contiguous()
    importance = torch.from_numpy(importance)
    count = len(x) - len(VALIDATION)
    layers = [nn.Conv2d(i, o, k, padding=k // 2) for i, o, k in LAYERS]
    model = nn.Sequential(layers[0], nn.ReLU(), layers[1], nn.ReLU(), layers[2])
    optimizer = torch.optim.AdamW(model.parameters(), lr=.003)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=.0002)
    best_loss = float("inf")
    best_epoch = None
    history = []
    for epoch in range(1, epochs + 1):
        train_loss = 0.
        for batch in torch.randperm(count, generator=generator).split(8):
            losses = -((model(x[batch]) + prior[batch]).log_softmax(1) * y[batch]).sum(1)
            loss = (losses * importance[batch]).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            train_loss += loss.item() * len(batch)
        schedule.step()
        with torch.no_grad():
            losses = -((model(x[count:]) + prior[count:]).log_softmax(1) * y[count:]).sum(1)
            validation = (losses * importance[count:]).mean().item()
        if validation < best_loss:
            best_epoch, best_loss = epoch, validation
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        history.append(dict(epoch=epoch, training=train_loss / count, validation=validation))
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"Epoch {epoch}: train {train_loss / count:.4f}, validation {validation:.4f}", flush=True)

    model.load_state_dict(best_state)
    arrays = {f"{name}{i}": getattr(layer, name).detach().numpy()
              for i, layer in enumerate(layers) for name in ("weight", "bias")}
    with output.open("wb") as file:
        np.savez_compressed(file, **arrays)
    numpy_layers = load_weights(output)
    with torch.no_grad():
        expected = model(x[count:]).permute(0, 2, 3, 1).numpy()
    actual = np.stack([predict(frame, numpy_layers) for frame in inputs[count:]])
    np.testing.assert_allclose(actual, expected, atol=2e-5, rtol=2e-5)
    report = dict(seed=SEED, torch=torch.__version__, numpy=np.__version__,
                  training_screens=count, validation_screens=len(VALIDATION),
                  source_pixel_sha256=source_hashes, prepared_corpus_sha256=signature,
                  parameters=sum(p.numel() for p in model.parameters()),
                  weights_bytes=output.stat().st_size, weights_sha256=sha256(output.read_bytes()).hexdigest(),
                  best_epoch=best_epoch, validation_loss=best_loss,
                  max_numpy_logit_error=float(np.max(np.abs(actual - expected))),
                  history=history)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path, default=DEFAULT_WEIGHTS)
    parser.add_argument("--cache", type=Path, help="optional teacher cache (.npz)")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("--epochs must be positive")
    report = train(args.weights, args.cache, args.epochs)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
