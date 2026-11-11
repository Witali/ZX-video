// Bounded stereo queue: discard old packets after a tab stalls; never build lag.
class SpectrumAudio extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    this.offset = 0;
    this.background = false;
    this.wakeSamples = 0;
    this.rendered = 0;
    this.missing = 0;
    this.dropped = 0;
    this.port.onmessage = ({ data }) => {
      if (data.background !== undefined) { this.background = data.background; this.wakeSamples = 0; return; }
      if (data.clear) {
        this.queue = [];
        this.offset = this.rendered = this.missing = this.dropped = 0;
        return;
      }
      if (data.stats) {
        this.port.postMessage({ stats: { rendered: this.rendered, missing: this.missing, dropped: this.dropped } });
        return;
      }
      this.queue.push(data);
      if (this.queue.length > 12) {
        const discarded = this.queue.splice(0, this.queue.length - 4);
        this.dropped += discarded.reduce((total, packet) => total + packet.left.length, -this.offset);
        this.offset = 0;
      }
    };
  }
  process(inputs, outputs) {
    const [left, right] = outputs[0];
    if (this.background) {
      this.wakeSamples += left.length;
      if (this.wakeSamples >= sampleRate / 100) {
        this.wakeSamples %= sampleRate / 100;
        this.port.postMessage({ wake: true });
      }
    }
    let n = 0;
    for (; n < left.length; n++) {
      const packet = this.queue[0];
      if (!packet) break;
      left[n] = packet.left[this.offset];
      right[n] = packet.right[this.offset];
      if (++this.offset === packet.left.length) { this.queue.shift(); this.offset = 0; }
    }
    this.rendered += n;
    // Silence sent by the AY chip is PCM too. Count only unavailable samples
    // after the first packet has started, including partial render quanta.
    if (this.rendered) this.missing += left.length - n;
    return true;
  }
}
registerProcessor('spectrum-audio', SpectrumAudio);
