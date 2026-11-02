export const LOWPASS_CUTOFFS = Object.freeze([5000, 10000, 15000, 20000]);

// A passive, single-pole RC-style smoother, with its digital -3 dB point
// calibrated to the requested frequency even near Nyquist. For p=1-alpha,
// H(z)=alpha/(1-p*z^-1); alpha²=2*(1-alpha)*(1-cos(2*pi*fc/fs)).
// Its nonnegative exponential impulse response cannot overshoot a bounded input.
export function rcCoefficients(cutoff, sampleRate) {
  if (!Number.isFinite(cutoff) || !Number.isFinite(sampleRate) || cutoff <= 0 || cutoff >= sampleRate / 2) {
    throw new RangeError('Low-pass cutoff must be below the sample-rate Nyquist frequency');
  }
  const d = 1 - Math.cos(2 * Math.PI * cutoff / sampleRate);
  const alpha = Math.sqrt(d * (d + 2)) - d;
  return { feedforward: [alpha], feedback: [1, alpha - 1] };
}

export class RcLowpassBank {
  constructor(context, input, output, cutoff = 20000) {
    if (!LOWPASS_CUTOFFS.includes(cutoff)) throw new RangeError('Unknown low-pass preset');
    this.context = context;
    this.cutoff = cutoff;
    // Keep the four cheap one-pole filters warm. Changing the selected output
    // then needs only a 20-ms crossfade, without resetting a filter's history.
    this.branches = new Map(LOWPASS_CUTOFFS.map(hz => {
      const { feedforward, feedback } = rcCoefficients(hz, context.sampleRate);
      const filter = context.createIIRFilter(feedforward, feedback);
      const gain = context.createGain();
      gain.gain.value = hz === cutoff ? 1 : 0;
      input.connect(filter).connect(gain).connect(output);
      return [hz, { filter, gain }];
    }));
  }
  setCutoff(cutoff) {
    if (!this.branches.has(cutoff)) throw new RangeError('Unknown low-pass preset');
    if (cutoff === this.cutoff) return;
    const now = this.context.currentTime;
    for (const [hz, { gain }] of this.branches) {
      const value = gain.gain;
      if (value.cancelAndHoldAtTime) value.cancelAndHoldAtTime(now);
      else {
        const current = value.value;
        value.cancelScheduledValues(now);
        value.setValueAtTime(current, now);
      }
      value.linearRampToValueAtTime(hz === cutoff ? 1 : 0, now + 0.02);
    }
    this.cutoff = cutoff;
  }
}
