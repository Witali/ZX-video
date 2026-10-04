"""Unpooled, time-aligned multiresolution STFT comparison (not note accuracy)."""
import numpy as np
import ay_fidelity as ay


def features(samples, rate=22050):
    """One global RMS normalization; no local gain, pitch or timing alignment."""
    samples = np.asarray(samples, dtype=float)
    samples = samples/max(float(np.sqrt(np.mean(samples*samples))), 1e-12)*.1
    count = (len(samples)+round(rate/50)-1)//round(rate/50)
    result = {}
    for size in (512, 2048, 8192):
        mag, rms = ay.spectra(samples, rate, 50, count, window_size=size)
        hz = np.fft.rfftfreq(size*2, 1/rate)
        result[size] = (mag[:, (hz >= 50) & (hz <= 8000)], rms)
    return result


def compare(reference, candidate):
    result = {}
    for size, (a, rms) in reference.items():
        b = candidate[size][0]
        if a.shape != b.shape:
            raise ValueError('compare equal source intervals, without time warping')
        active = rms > 1e-4
        peak = max(float(a.max()), 1e-12)
        floor = peak*.001  # Common source-relative -60 dB floor.
        ad = 20*np.log10(np.maximum(a, floor)/peak)
        bd = 20*np.log10(np.maximum(b, floor)/peak)
        support = ((a > floor) | (b > floor)) & active[:, None]
        cos = np.sum(a*b, axis=1)/np.maximum(np.linalg.norm(a, axis=1)*np.linalg.norm(b, axis=1), 1e-20)
        # Square-root compression reduces domination by a few strong partials.
        rootcos = np.sum(np.sqrt(a*b), axis=1)/np.maximum(np.sqrt(a.sum(axis=1)*b.sum(axis=1)), 1e-20)
        result[str(size)] = dict(window_ms=size/22050*1000, hop_ms=20,
            magnitude_cosine=float(cos[active].mean()) if active.any() else 0.,
            sqrt_magnitude_cosine=float(rootcos[active].mean()) if active.any() else 0.,
            log_magnitude_mae_db=float(np.abs(ad-bd)[support].mean()) if support.any() else 0.,
            spectral_convergence=float(np.linalg.norm((a-b)[active])/max(np.linalg.norm(a[active]), 1e-20)),
            active_frames=int(active.sum()))
    return result
