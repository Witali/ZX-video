"""Three-layer CNN on the attribute grid. Inference needs only NumPy."""

from pathlib import Path

import numpy as np

from .screen import PAIR_COUNT

WIDTHS = (32, 64)
DEFAULT_WEIGHTS = Path(__file__).with_name("weights.npz")
WIDE_WEIGHTS = Path(__file__).with_name("weights64.npz")
CLIC_WIDE_WEIGHTS = Path(__file__).with_name("weights64-clic.npz")
PIXEL_ART_WEIGHTS = Path(__file__).with_name("weights64-pixel-art.npz")
OUTLINE_WEIGHTS = Path(__file__).with_name("weights64-outline.npz")


def architecture(channels):
    if channels not in WIDTHS:
        raise ValueError(f"unsupported CNN width: {channels}")
    return ((24 + 2 * PAIR_COUNT, channels, 3), (channels, channels, 3),
            (channels, PAIR_COUNT, 1))


def load_weights(path=DEFAULT_WEIGHTS):
    layers = []
    with np.load(path, allow_pickle=False) as arrays:
        first = arrays["weight0"]
        if first.ndim != 4:
            raise ValueError("invalid first CNN layer")
        for i, (inputs, outputs, kernel) in enumerate(architecture(first.shape[0])):
            weight = arrays[f"weight{i}"]
            bias = arrays[f"bias{i}"]
            if (weight.shape != (outputs, inputs, kernel, kernel)
                    or bias.shape != (outputs,) or weight.dtype != np.float32
                    or bias.dtype != np.float32 or not np.isfinite(weight).all()
                    or not np.isfinite(bias).all()):
                raise ValueError(f"invalid CNN weights for layer {i}")
            layers.append((weight, bias))
    return layers


def predict(features, layers):
    """Evaluate the same cross-correlation and zero padding used in training."""
    height, width = features.shape[:2]
    for i, (weight, bias) in enumerate(layers):
        outputs, _, kernel, _ = weight.shape
        if kernel > 1:
            pad = kernel // 2
            padded = np.pad(features, ((pad, pad), (pad, pad), (0, 0)))
            windows = np.lib.stride_tricks.sliding_window_view(padded, (kernel, kernel), axis=(0, 1))
        else:
            windows = features
        features = (windows.reshape(height * width, -1) @ weight.reshape(outputs, -1).T + bias)
        features = features.reshape(height, width, outputs)
        if i + 1 < len(layers):
            np.maximum(features, 0, out=features)
    return features
