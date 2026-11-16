"""Sample local texture corpora before resizing any source image."""

from collections import defaultdict
from hashlib import sha256
from pathlib import PurePosixPath

from PIL import Image


def ordered(names, salt):
    return sorted(names, key=lambda name: sha256(f"zx-texture-v1:{salt}:{name}".encode()).digest())


def dtd_split(root):
    """Sample every DTD class, retaining the official first partition."""
    groups = []
    seen = set()
    for split, count in (("train", 2), ("val", 1), ("test", 1)):
        by_class = defaultdict(list)
        for name in (root / "labels" / f"{split}1.txt").read_text(encoding="utf8").splitlines():
            relative = PurePosixPath(name)
            if (len(relative.parts) != 2 or relative.is_absolute() or relative.parts[0] == ".."
                    or "\\" in name or ":" in name
                    or relative.suffix.lower() != ".jpg" or name in seen):
                raise ValueError("invalid or overlapping DTD split entries")
            seen.add(name)
            by_class[relative.parts[0]].append(name)
        if len(by_class) != 47 or any(len(names) < count for names in by_class.values()):
            raise ValueError("expected all 47 DTD classes in each split")
        groups.append([(f"dtd/{name}", root / "images" / name)
                       for category in sorted(by_class)
                       for name in ordered(by_class[category], split)[:count]])
    return tuple(groups)


def kylberg_split(root):
    """Keep whole Kylberg material classes disjoint in the six-class subset."""
    classes = ordered([path.name for path in root.iterdir() if path.is_dir()], "kylberg-classes")
    if len(classes) != 6:
        raise ValueError("expected the six-class Kylberg subset")
    groups = []
    count = 8
    for partition in (classes[:4], classes[4:5], classes[5:]):
        groups.append([(f"kylberg/{category}/{name}", root / category / name)
                       for category in partition
                       for name in ordered([path.name for path in (root / category).glob("*.png")], category)[:count]])
        if len(groups[-1]) != len(partition) * count:
            raise ValueError("incomplete Kylberg material class")
    return tuple(groups)


def read_textures(group):
    for name, path in group:
        with Image.open(path) as image:
            yield name, image.convert("RGB")


def texture_splits(root):
    yield "dtd", dtd_split(root / "dtd-r1.0.1" / "dtd")
    yield "kylberg", kylberg_split(root / "kylberg-v1-small")
