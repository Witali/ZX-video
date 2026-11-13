"""Read a reproducible photo split from the BIDS mirror of Berkeley BSDS500."""

from hashlib import sha256
from io import BytesIO
from pathlib import PurePosixPath
from zipfile import ZipFile

import numpy as np
from PIL import Image

REVISION = "a04b7c6c3a9f0ace74bf205c72a43d32e1c72722"
ARCHIVE_URL = f"https://codeload.github.com/BIDS/BSDS500/zip/{REVISION}"
ADDITIONAL_TRAIN_PHOTOS = 90
EVALUATION_PHOTOS = 20
VALIDATION_PHOTOS = 10
CLIC_TRAIN_PATCHES = 100


def read_photos(archive, split, count):
    """Sample by a fixed hash of each image name, before viewing any outputs."""
    with ZipFile(archive) as source:
        prefix = f"/BSDS500/data/images/{split}/"
        paths = [path for path in source.namelist() if prefix in path and path.endswith(".jpg")]
        expected = 100 if split == "val" else 200
        if len(paths) != expected:
            raise ValueError(f"expected {expected} BSDS500 {split} photos, got {len(paths)}")
        paths.sort(key=lambda path: sha256(f"zx-neural-v2:{PurePosixPath(path).name}".encode()).digest())
        for path in paths[:count]:
            with Image.open(BytesIO(source.read(path))) as image:
                yield PurePosixPath(path).name, image.convert("RGB")


def read_training_photos(archive):
    return read_photos(archive, "train", ADDITIONAL_TRAIN_PHOTOS)


def read_evaluation_photos(archive):
    return read_photos(archive, "test", EVALUATION_PHOTOS)


def read_validation_photos(archive):
    return read_photos(archive, "val", VALIDATION_PHOTOS)


def clic_split(root):
    """Partition whole photos before sampling or augmentation."""
    paths = sorted(root.rglob("*.png"), key=lambda p: p.relative_to(root).as_posix())
    if len(paths) != 42:
        raise ValueError(f"expected 42 CLIC Professional Validation PNGs, got {len(paths)}")
    by_hash = {}
    for path in paths:
        with Image.open(path) as image:
            digest = sha256(image.convert("RGB").tobytes()).hexdigest()
        if digest in by_hash:
            raise ValueError("duplicate decoded CLIC source photo")
        by_hash[digest] = path
    ranked = sorted(by_hash, key=lambda digest: sha256(f"zx-neural-clic-v1:{digest}".encode()).digest())
    groups = (ranked[:30], ranked[30:36], ranked[36:])
    return tuple([(f"clic-{digest[:12]}", by_hash[digest], digest) for digest in group] for group in groups)


def read_clic(group):
    for name, path, _ in group:
        with Image.open(path) as image:
            yield name, image.convert("RGB")


def clic_patches(group, rng):
    """Take 100 distinct 4:3 crops at several scales from the 30 training photos."""
    base, extra = divmod(CLIC_TRAIN_PATCHES, len(group))
    for index, (name, image) in enumerate(read_clic(group)):
        width, height = image.size
        fit = min(width // 4, height // 3)
        boxes = set()
        while len(boxes) < base + (index < extra):
            scale = int(np.clip(round(fit * rng.uniform(.38, .96)), 1, fit))
            w, h = 4 * scale, 3 * scale
            x = int(rng.integers(width - w + 1))
            y = int(rng.integers(height - h + 1))
            box = (x, y, x + w, y + h)
            if box not in boxes:
                boxes.add(box)
                yield name, box, image.crop(box)
