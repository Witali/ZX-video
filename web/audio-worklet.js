// Bounded stereo queue: discard old packets after a tab stalls; never build lag.
class SpectrumAudio extends AudioWorkletProcessor {
  constructor() {
    super();
    this.queue = [];
    this.offset = 0;
    this.port.onmessage = ({ data }) => {
      if (data.clear) { this.queue = []; this.offset = 0; return; }
      this.queue.push(data);
      if (this.queue.length > 12) { this.queue = this.queue.slice(-4); this.offset = 0; }
    };
  }
  process(inputs, outputs) {
    const [left, right] = outputs[0];
    for (let n = 0; n < left.length; n++) {
      const packet = this.queue[0];
      if (!packet) break;
      left[n] = packet.left[this.offset];
      right[n] = packet.right[this.offset];
      if (++this.offset === packet.left.length) { this.queue.shift(); this.offset = 0; }
    }
    return true;
  }
}
registerProcessor('spectrum-audio', SpectrumAudio);
