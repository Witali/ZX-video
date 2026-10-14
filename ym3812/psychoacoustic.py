"""Source-based critical-band masking approximation for register fitting.

This is a relative audibility model, not PEAQ or a calibrated hearing model.
The source alone supplies maskers. An erroneous candidate cannot hide itself.
"""
import numpy as np

MODEL = dict(model='relative_bark_masking_v1', bands=24,
    spreading_db_per_bark_up=15, spreading_db_per_bark_down=27,
    noise_masker_offset_db=6, tonal_masker_offset_db=16,
    forward_decay_db_per_20ms=8, minimum_error_weight=.1,
    absolute_hearing_threshold=False, calibrated_playback_spl=False,
    source='https://publica-rest.fraunhofer.de/server/api/core/bitstreams/02820baa-82ed-4a16-80c3-c4c974362413/content',
    limitations='Tunable approximation of critical bands, simultaneous and short forward masking; no standard compliance or listening-quality guarantee.')


def bark(hz):
    hz = np.asarray(hz, float)
    return 13*np.arctan(.00076*hz)+3.5*np.arctan((hz/7500)**2)


def thresholds(magnitude, hz):
    """Return source-only power thresholds in the same FFT magnitude units.

    Mean band power avoids a threshold that grows with FFT bin count. Flatness
    interpolates noise/tonal offsets; asymmetric spreading models neighbouring
    critical bands. Carry only decaying past masking, without pre-echo masking.
    """
    power = np.asarray(magnitude, float)**2
    bands = np.minimum(bark(hz).astype(int), 23)
    energy = np.zeros((len(power), 24)); tonal = energy.copy()
    for band in range(24):
        values = power[:, bands == band]
        if not values.shape[1]:
            continue
        energy[:, band] = values.mean(axis=1)
        flatness = np.exp(np.log(np.maximum(values, 1e-30)).mean(axis=1))/np.maximum(energy[:, band], 1e-30)
        tonal[:, band] = np.clip(-10*np.log10(np.maximum(flatness, 1e-12))/20, 0, 1)
    masked = energy*10**(-(6+10*tonal)/10)
    distance = np.arange(24)[:, None]-np.arange(24)[None, :]
    spread = 10**(-np.where(distance >= 0, 15*distance, -27*distance)/10)
    threshold = np.max(masked[:, None, :]*spread[None, :, :], axis=2)
    decay = 10**(-8/10)
    for tick in range(1, len(threshold)):
        threshold[tick] = np.maximum(threshold[tick], threshold[tick-1]*decay)
    return threshold[:, bands].astype(np.float32)


def error_weights(reference, candidate, threshold):
    # Audible newly introduced noise remains penalized, even in source rests.
    power = np.maximum(reference, candidate)**2
    return .1+.9*np.minimum(1, power/np.maximum(threshold, 1e-30))
