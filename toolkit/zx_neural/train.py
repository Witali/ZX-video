"""Train the small attribute CNN in FP32 with a fixed source split."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image
import torch
from torch import nn

from .corpus import TRAIN_PHOTOS, VALIDATION, read_source, training_sources
from .model import (
    CLIC_WIDE_WEIGHTS, DEFAULT_WEIGHTS, WIDTHS, WIDE_WEIGHTS, architecture, load_weights, predict,
)
from .objective import (
    COLOR_BUDGET, SEAM_WEIGHT, TARGET_TEMPERATURE, TEMPERATURE, TRAIN_SWEEPS,
    Candidates, features,
)
from .screen import HEIGHT, WIDTH, prepare

SEED = 433
VIEWS = 8
EPOCHS = 80
DISTILL_TEMPERATURE = 2.
DISTILL_WEIGHT = .5


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


def teacher_screen(image, pixel_art=False, outline=False):
    candidates = Candidates(image)
    prior = np.where(candidates.allowed, -candidates.regret / TEMPERATURE, -100.)
    if pixel_art:
        from .pixel_art import PixelArtCandidates

        target, weight = PixelArtCandidates(candidates).training_target(candidates)
    else:
        target, weight = candidates.training_target()
    if outline:
        from .__main__ import convert
        from .line_art import outline_subjects
        from .screen import ATTRIBUTES, COLS, ROWS

        # Use the same black outline, filled shadows and shaded interiors
        # on independent training images as on the visual reference.
        before = convert(image, "spatial", None, floyd=True, repair=True, automatic_outline=False)
        after, _ = outline_subjects(image, before, unmasked_chroma=.29)
        attrs = np.frombuffer(after[6144:], dtype=np.uint8).reshape(ROWS, COLS)
        original = np.frombuffer(before[0][6144:], dtype=np.uint8).reshape(ROWS, COLS)
        cy, cx = np.nonzero(attrs != original)
        labels = np.searchsorted(ATTRIBUTES, attrs[cy, cx])
        if len(labels):
            # A style pair can be outside the photo-only prior. Let the
            # teacher nominate that pair without a -100 logit penalty.
            prior[cy, cx, labels] = np.maximum(prior[cy, cx, labels], -2.)
            target[cy, cx] *= .25
            target[cy, cx, labels] += .75
            weight[cy, cx] = np.maximum(weight[cy, cx], 4.)
    return features(image, candidates), prior, target, weight


def dataset(cache, bsds_archive=None, clic_root=None, workers=1, pixel_art=False, outline=False):
    rng = np.random.default_rng(SEED)
    train_images = []
    source_hashes = {}
    extra = {}
    if clic_root is not None:
        from .photo_corpus import clic_patches, clic_split, read_clic

        training, validation_group, evaluation_group = clic_split(clic_root)
        source_hashes = {name: digest for name, _, digest in training}
        validation = list(read_clic(validation_group))
        patches = list(clic_patches(training, rng))
        train_images.extend(prepare(image) for _, _, image in patches)
        extra = dict(corpus="CLIC 2020 Professional Validation",
                     evaluation_pixel_sha256={name: digest for name, _, digest in evaluation_group},
                     training_crop_boxes=[dict(source=name, box=box) for name, box, _ in patches])
        if bsds_archive is not None:
            from .photo_corpus import read_training_photos, read_validation_photos

            extra["corpus"] = "CLIC 2020 Professional Validation and BSDS500"
            for name, image in read_training_photos(bsds_archive):
                source_hashes[name] = sha256(image.tobytes()).hexdigest()
                train_images.extend((prepare(image), augment(image, rng)))
            validation.extend(read_validation_photos(bsds_archive))
    elif bsds_archive is None:
        sources = [(name, read_source(kind, name), VIEWS) for kind, name in training_sources()]
        validation = [(name, read_source(kind, name)) for kind, name in VALIDATION]
    else:
        from .photo_corpus import read_training_photos, read_validation_photos

        sources = [(name, read_source("photo", name), 2) for name in TRAIN_PHOTOS]
        sources.extend((name, image, 2) for name, image in read_training_photos(bsds_archive))
        validation = list(read_validation_photos(bsds_archive))
    if clic_root is None:
        for name, image, views in sources:
            source_hashes[name] = sha256(image.tobytes()).hexdigest()
            train_images.append(prepare(image))
            train_images.extend(augment(image, rng) for _ in range(views - 1))
    train_images.extend(synthetic(rng) for _ in range(32))
    validation_hashes = {name: sha256(image.tobytes()).hexdigest() for name, image in validation}
    if set(source_hashes.values()) & set(validation_hashes.values()):
        raise ValueError("training and validation photos overlap")
    images = np.stack(train_images + [prepare(image) for _, image in validation])
    signature = sha256(images.tobytes()).hexdigest()
    metadata = dict(source_pixel_sha256=source_hashes, validation_pixel_sha256=validation_hashes,
                    prepared_corpus_sha256=signature, training_screens=len(train_images),
                    validation_screens=len(validation), **extra)
    cache_key = f"seam-v1:{signature}:{COLOR_BUDGET}:{SEAM_WEIGHT}:{TARGET_TEMPERATURE}:{TEMPERATURE}:{TRAIN_SWEEPS}"
    if pixel_art:
        cache_key = f"pixel-art-v1:{cache_key}"
        metadata["teacher_objective"] = "pixel art"
    if outline:
        cache_key = f"outline-v2:{cache_key}"
        metadata["teacher_objective"] = "pixel art with black outlines and shaded fill"
    if cache and cache.exists():
        with np.load(cache, allow_pickle=False) as data:
            if data["signature"].item() == cache_key:
                return data["inputs"], data["base"], data["targets"], data["importance"], metadata
    pool = ThreadPoolExecutor(max_workers=workers) if workers > 1 else nullcontext()
    screens = []
    with pool as executor:
        # map preserves corpus order even when the workers finish out of order.
        process = executor.map if executor else map
        make_teacher = partial(teacher_screen, pixel_art=pixel_art, outline=outline)
        for i, screen in enumerate(process(make_teacher, images), 1):
            screens.append(screen)
            if i % 32 == 0:
                print(f"Prepared {i}/{len(images)} teacher screens", flush=True)
    inputs, base, targets, importance = map(np.stack, zip(*screens, strict=True))
    if cache:
        np.savez_compressed(cache, inputs=inputs, base=base, targets=targets, importance=importance, signature=cache_key)
    return inputs, base, targets, importance, metadata


def teacher_distribution(path, inputs, prior):
    """Produce soft rankings over the same source-bounded pairs as the student."""
    teacher = load_weights(path)
    with torch.no_grad():
        logits = []
        for batch in inputs.split(8):
            for i, (weight, bias) in enumerate(teacher):
                batch = nn.functional.conv2d(batch, torch.from_numpy(weight), torch.from_numpy(bias),
                                             padding=weight.shape[-1] // 2)
                if i + 1 < len(teacher):
                    batch.relu_()
            logits.append(batch)
        return ((torch.cat(logits) + prior) / DISTILL_TEMPERATURE).softmax(1)


def train(output, cache, epochs, channels=32, bsds_archive=None, teacher=None, clic_root=None,
          device="cpu", workers=1, threads=4, pixel_art=False, outline=False, initialize=None):
    device = torch.device(device)
    if device.type == "cuda":
        # cuBLAS requires a workspace configuration for deterministic FP32.
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    if device.type == "cuda" and not torch.cuda.is_available():
        raise ValueError("CUDA unavailable; use a CUDA-enabled PyTorch build or --device cpu")
    torch.manual_seed(SEED)
    torch.set_num_threads(threads)
    torch.use_deterministic_algorithms(True)
    if device.type == "cuda":
        torch.backends.cuda.matmul.fp32_precision = "ieee"
        torch.backends.cudnn.conv.fp32_precision = "ieee"
    generator = torch.Generator().manual_seed(SEED)
    prepared = perf_counter()
    inputs, base, targets, importance, metadata = dataset(cache, bsds_archive, clic_root, workers, pixel_art, outline)
    preparation_seconds = perf_counter() - prepared
    x = torch.from_numpy(inputs).permute(0, 3, 1, 2).contiguous()
    y = torch.from_numpy(targets).permute(0, 3, 1, 2).contiguous()
    prior = torch.from_numpy(base).permute(0, 3, 1, 2).contiguous()
    importance = torch.from_numpy(importance)
    count = metadata["training_screens"]
    soft_targets = teacher_distribution(teacher, x[:count], prior[:count]) if teacher else None
    x, y, prior, importance = (tensor.to(device) for tensor in (x, y, prior, importance))
    if soft_targets is not None:
        soft_targets = soft_targets.to(device)
    layers = [nn.Conv2d(i, o, k, padding=k // 2, dtype=torch.float32)
              for i, o, k in architecture(channels)]
    if initialize:
        with torch.no_grad():
            for layer, (weight, bias) in zip(layers, load_weights(initialize), strict=True):
                layer.weight.copy_(torch.from_numpy(weight))
                layer.bias.copy_(torch.from_numpy(bias))
        metadata["initial_weights_sha256"] = sha256(initialize.read_bytes()).hexdigest()
    model = nn.Sequential(layers[0], nn.ReLU(), layers[1], nn.ReLU(), layers[2]).to(device)
    if initialize:
        with torch.no_grad():
            initial = -((model(x[count:]) + prior[count:]).log_softmax(1) * y[count:]).sum(1)
            metadata["initial_validation_loss"] = (initial * importance[count:]).mean().item()
    optimizer = torch.optim.AdamW(model.parameters(), lr=.00045 if initialize else .003)
    schedule = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs, eta_min=.0002)
    best_loss = float("inf")
    best_epoch = None
    history = []
    started = perf_counter()
    for epoch in range(1, epochs + 1):
        train_loss = torch.zeros((), device=device)
        for batch in torch.randperm(count, generator=generator).split(8):
            batch = batch.to(device)
            logits = model(x[batch]) + prior[batch]
            losses = -(logits.log_softmax(1) * y[batch]).sum(1)
            if soft_targets is not None:
                soft_losses = -((logits / DISTILL_TEMPERATURE).log_softmax(1) * soft_targets[batch]).sum(1)
                losses = (1 - DISTILL_WEIGHT) * losses + DISTILL_WEIGHT * DISTILL_TEMPERATURE ** 2 * soft_losses
            loss = (losses * importance[batch]).mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            train_loss += loss.detach() * len(batch)
        schedule.step()
        with torch.no_grad():
            losses = -((model(x[count:]) + prior[count:]).log_softmax(1) * y[count:]).sum(1)
            validation = (losses * importance[count:]).mean().item()
        if validation < best_loss:
            best_epoch, best_loss = epoch, validation
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
        train_mean = train_loss.item() / count
        history.append(dict(epoch=epoch, training=train_mean, validation=validation))
        if epoch == 1 or epoch % 10 == 0 or epoch == epochs:
            print(f"Epoch {epoch}: train {train_mean:.4f}, validation {validation:.4f}", flush=True)

    optimization_seconds = perf_counter() - started
    model.load_state_dict(best_state)
    arrays = {f"{name}{i}": getattr(layer, name).detach().cpu().numpy()
              for i, layer in enumerate(layers) for name in ("weight", "bias")}
    numpy_layers = [(arrays[f"weight{i}"], arrays[f"bias{i}"]) for i in range(len(layers))]
    with torch.no_grad():
        device_logits = model(x[count:]).permute(0, 2, 3, 1).cpu().numpy()
        expected = model.cpu()(x[count:].cpu()).permute(0, 2, 3, 1).numpy()
    actual = np.stack([predict(frame, numpy_layers) for frame in inputs[count:]])
    # Convolution and matrix multiplication accumulate FP32 products in
    # different orders. Validate within the same absolute budget as CUDA.
    np.testing.assert_allclose(actual, expected, atol=1e-4, rtol=2e-5)
    # Different FP32 accumulation orders can diverge slightly on the GPU.
    np.testing.assert_allclose(device_logits, expected, atol=1e-4, rtol=2e-5)
    with output.open("wb") as file:
        np.savez_compressed(file, **arrays)
    report = dict(seed=SEED, torch=torch.__version__, numpy=np.__version__,
                  channels=channels, dtype="float32", epochs=epochs,
                  device=str(device), gpu=torch.cuda.get_device_name(device) if device.type == "cuda" else None,
                  optimization_seconds=optimization_seconds,
                  preparation_seconds=preparation_seconds, workers=workers, threads=threads,
                  **metadata,
                  parameters=sum(p.numel() for p in model.parameters()),
                  weights_bytes=output.stat().st_size, weights_sha256=sha256(output.read_bytes()).hexdigest(),
                  best_epoch=best_epoch, validation_loss=best_loss,
                  max_numpy_logit_error=float(np.max(np.abs(actual - expected))),
                  max_device_logit_error=float(np.max(np.abs(device_logits - expected))),
                  history=history)
    if teacher:
        report["distillation"] = dict(teacher_sha256=sha256(teacher.read_bytes()).hexdigest(),
                                      temperature=DISTILL_TEMPERATURE, weight=DISTILL_WEIGHT)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--channels", type=int, choices=WIDTHS, default=32)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument("--workers", type=int, default=1, help="parallel workers for palette target generation")
    parser.add_argument("--threads", type=int, default=4, help="PyTorch CPU thread count")
    parser.add_argument("--bsds-archive", type=Path, help="BSDS500 archive to extend training to 100 photos")
    parser.add_argument("--clic-root", type=Path, help="use 100 crops from the block-palette CLIC corpus")
    parser.add_argument("--pixel-art", action="store_true", help="train on the pixel-art palette objective")
    parser.add_argument("--outline", action="store_true", help="include outlined subjects in pixel-art teacher targets")
    parser.add_argument("--initialize", type=Path, help="fine-tune an existing model of the same width")
    parser.add_argument("--teacher", type=Path, help="distill the pair scores of a trained .npz model")
    parser.add_argument("--cache", type=Path, help="optional teacher cache (.npz)")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=EPOCHS)
    args = parser.parse_args()
    if args.outline and not args.pixel_art:
        parser.error("--outline requires --pixel-art")
    if args.pixel_art and not args.weights:
        parser.error("--pixel-art requires an explicit --weights output")
    if min(args.epochs, args.workers, args.threads) < 1:
        parser.error("--epochs, --workers and --threads must be positive")
    default = CLIC_WIDE_WEIGHTS if args.clic_root else WIDE_WEIGHTS
    if (args.clic_root or args.bsds_archive) and args.channels == 32 and not args.weights:
        parser.error("expanded-corpus training with 32 channels requires an explicit --weights output")
    output = args.weights or (default if args.channels == 64 else DEFAULT_WEIGHTS)
    if args.initialize and (not args.weights or output.resolve() == args.initialize.resolve()):
        parser.error("--initialize requires a distinct, explicit --weights output")
    if args.teacher and (not args.weights or output.resolve() == args.teacher.resolve()):
        parser.error("--teacher requires a distinct, explicit --weights output")
    report = train(output, args.cache, args.epochs, args.channels, args.bsds_archive,
                   args.teacher, args.clic_root, args.device, args.workers, args.threads,
                   args.pixel_art, args.outline, args.initialize)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__":
    main()
