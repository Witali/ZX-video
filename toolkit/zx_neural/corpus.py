"""Fixed source-level training, validation and evaluation split for version 1."""

from pathlib import Path

from PIL import Image

ART = Path(__file__).resolve().parents[2] / "music-menu" / "artwork" / "sources"
TRAIN_PHOTOS = (
    "astronaut.png", "brick.png", "camera.png", "grass.png", "gravel.png",
    "horse.png", "hubble_deep_field.jpg", "moon.png", "coins.png", "retina.jpg",
)
TRAIN_ART = (
    "duel", "esquie", "expedition", "guardian", "gustave",
    "lampmaster", "monoco", "portrait", "renoir", "visages",
)
VALIDATION = (("photo", "clock_motion.png"), ("art", "titan"))
EVALUATION = (
    ("photo", "chelsea.png"), ("photo", "coffee.png"), ("photo", "motorcycle_left.png"),
    ("photo", "rocket.jpg"), ("art", "city"), ("art", "maelle"), ("art", "underwater"),
)


def training_sources():
    return [("photo", name) for name in TRAIN_PHOTOS] + [("art", name) for name in TRAIN_ART]


def read_source(kind, name):
    if kind == "photo":
        import skimage.data

        path = Path(skimage.data.__file__).with_name(name)
    else:
        path = ART / f"{name}.png"
    with Image.open(path) as image:
        return image.convert("RGB")
