/* global ZX_Bus, ZX_Clock, ZX_Z80, ZX_ROM, ZX_RAM, ZX_Display, ZX_Keyboard,
  ZX_Floppy, ZX_BetaDisk, ZX_PortFE, ZX_Port7FFD, ZX_PSG */
import { LOWPASS_CUTOFFS, RcLowpassBank } from './audio-filter.js';
// Small adapter around pinned ZX-Dream. No upstream UI, PHP server or CDN.
window.ZXContext = { debugMode: false };
window.loadServerFile = async name => {
  const response = await fetch(new URL(`vendor/roms/${name}`, document.baseURI));
  if (!response.ok) throw new Error(`Cannot load emulator ROM (${response.status})`);
  return new Uint8Array(await response.arrayBuffer());
};

export class SpectrumPlayer {
  constructor(container) {
    this.container = container;
    this.hw = null;
    this.audio = null;
    this.muted = false;
    this.lowpassCutoff = 20000;
    this.rendererPreference = 'webgl';
    this.activeRenderer = 'webgl';
    this.onRendererChanged = () => {};
    this.onDiskActivity = () => {};
    this.diskActive = false;
    this.diskBusyUntil = 0;
    this.held = new Map();
    this.keyCounts = new Map();
    const rows = ['ShiftLeft,Z,X,C,V', 'A,S,D,F,G', 'Q,W,E,R,T', '1,2,3,4,5',
      '0,9,8,7,6', 'P,O,I,U,Y', 'Enter,L,K,J,H', 'Space,AltLeft,M,N,B'];
    this.keys = new Map(rows.flatMap((row, index) => row.split(',').map((key, bit) =>
      [key.length === 1 ? (/\d/.test(key) ? `Digit${key}` : `Key${key}`) : key, [{ index, bit }]])));
    this.keys.set('ShiftRight', this.keys.get('ShiftLeft'));
    this.keys.set('AltRight', this.keys.get('AltLeft'));
    // Spectrum cursor keys are Caps Shift with 5/6/7/8, not joystick ports.
    for (const [code, digit] of Object.entries({ ArrowLeft: 5, ArrowDown: 6, ArrowUp: 7, ArrowRight: 8 })) {
      this.keys.set(code, [...this.keys.get('ShiftLeft'), ...this.keys.get(`Digit${digit}`)]);
    }
    container.addEventListener('pointerdown', () => container.focus({ preventScroll: true }));
    container.addEventListener('keydown', event => this.keyboard(event, true));
    container.addEventListener('keyup', event => this.keyboard(event, false));
    container.addEventListener('blur', () => this.releaseKeys());
    window.addEventListener('blur', () => this.releaseKeys());
  }
  async initialize() {
    if (this.hw) return;
    const h = this.hw = { bus: new ZX_Bus(), clock: new ZX_Clock(), cpu: new ZX_Z80(),
      rom: new ZX_ROM(), ram: new ZX_RAM(), display: new ZX_Display(),
      keyboard: new ZX_Keyboard(), drives: Array.from({ length: 4 }, () => new ZX_Floppy()),
      disk: new ZX_BetaDisk(), fe: new ZX_PortFE(), paging: new ZX_Port7FFD(), psg: new ZX_PSG() };
    h.cpu.connect(h.bus);
    h.clock.connect(h.bus, h.cpu);
    for (const device of [h.rom, h.ram, h.keyboard, h.fe, h.paging]) device.connect(h.bus);
    h.display.connect(h.bus, h.clock);
    h.disk.connect(h.bus, h.clock, h.drives);
    h.psg.connect(h.bus, h.clock);
    h.bus.opt('TSTATES_PER_INTRQ', 70908);
    h.bus.opt('INTRQ_PERIOD', 20);
    h.bus.opt('EXTENDED_MEMORY', 0);
    h.bus.opt('SEMICOLORS', true);
    this.bindDisplay();
    h.psg.applySettings(true, 0.35, 1, 0, 0, 1773400, 512, 0.7);
    h.psg.get_onDataReady().subscribe(packet => {
      if (this.output && this.audio?.state === 'running') this.output.port.postMessage({ left: packet.left, right: packet.right });
    });
    try { await h.rom.get_ready$(); }
    catch (error) { this.hw = null; this.container.querySelectorAll('canvas').forEach(c => c.remove()); throw error; }
    // Poll the controller's side-effect-free state, not its I/O status port.
    // Hold brief gaps between sector commands so one read shows a steady spinner.
    this.activityTimer = window.setInterval(() => {
      const running = h.clock.get_running();
      if (running && (h.disk.get_state().vg93.status & 1)) this.diskBusyUntil = performance.now() + 350;
      const active = running && performance.now() < this.diskBusyUntil;
      if (active !== this.diskActive) {
        this.diskActive = active;
        this.onDiskActivity(active);
      }
    }, 80);
  }
  setRenderer(mode) {
    if (!['canvas', 'webgl'].includes(mode)) throw new Error('Unknown renderer');
    this.rendererPreference = mode;
    if (this.hw) this.bindDisplay();
  }
  bindDisplay() {
    const bind = mode => {
      this.container.querySelectorAll('canvas').forEach(canvas => canvas.remove());
      // Canvas has a device-sized presentation surface and a separate native
      // framebuffer. Its final nearest-neighbor blit creates exact 2x2 blocks.
      const presentationScale = mode === 'canvas' ? 2 : 1;
      this.hw.bus.opt('RENDERING_PARAMS', { scale: presentationScale, scaleType: 1,
        rendererType: mode === 'webgl' ? 3 : 1, renderOnAnimationFrame: false });
      const canvases = [0, 1, 2].map(index => {
        const canvas = document.createElement('canvas');
        canvas.width = (index ? 256 : 288) * presentationScale;
        canvas.height = (index ? 192 : 224) * presentationScale;
        canvas.className = index ? 'screen-layer' : 'border-layer';
        if (index) canvas.addEventListener('webglcontextlost', event => {
          event.preventDefault();
          if (this.container.contains(canvas) && this.activeRenderer === 'webgl') {
            bind('canvas');
            this.onRendererChanged('canvas', true);
          }
        });
        this.container.append(canvas);
        return canvas;
      });
      this.hw.display.bind(canvases);
      this.hw.display.force_redraw();
      this.activeRenderer = mode;
      this.container.dataset.renderer = mode;
    };
    try {
      bind(this.rendererPreference);
      this.onRendererChanged(this.activeRenderer, false);
    } catch (error) {
      if (this.rendererPreference !== 'webgl') throw error;
      bind('canvas');
      this.onRendererChanged('canvas', true);
    }
  }
  async enableAudio() {
    if (!this.audio) {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) throw new Error('This browser does not support Web Audio.');
      const audio = new Audio({ sampleRate: 44100 });
      try {
        await audio.audioWorklet.addModule(new URL('audio-worklet.js', import.meta.url));
        const output = new AudioWorkletNode(audio, 'spectrum-audio', { outputChannelCount: [2] });
        const gain = audio.createGain();
        const lowpass = new RcLowpassBank(audio, output, gain, this.lowpassCutoff);
        gain.connect(audio.destination);
        Object.assign(this, { audio, output, gain, lowpass });
      } catch (error) { await audio.close(); throw error; }
    }
    await this.audio.resume();
    this.setMuted(this.muted);
  }
  mount(bytes, boot) {
    this.hw.clock.stop();
    this.releaseKeys();
    this.hw.drives[0].insertTRD(bytes);
    this.output?.port.postMessage({ clear: true });
    if (boot) this.hw.bus.reset(2);
    this.hw.clock.run();
    this.container.focus({ preventScroll: true });
  }
  pause(paused) {
    if (paused) { this.hw.clock.stop(); this.releaseKeys(); this.audio?.suspend(); }
    else { this.audio?.resume(); this.hw.clock.run(); }
    this.output?.port.postMessage({ clear: true });
  }
  setMuted(muted) { this.muted = muted; if (this.gain) this.gain.gain.value = muted ? 0 : 1; }
  setLowpassCutoff(cutoff) {
    if (!LOWPASS_CUTOFFS.includes(cutoff)) throw new RangeError('Unknown low-pass preset');
    this.lowpassCutoff = cutoff;
    this.lowpass?.setCutoff(cutoff);
  }
  keyboard(event, pressed) {
    const keys = this.keys.get(event.code);
    if (!keys || !this.hw) return;
    event.preventDefault();
    this.holdKeys(event.code, keys, pressed);
  }
  holdKeys(source, keys, pressed) {
    if (this.held.has(source) === pressed) return;
    if (pressed) this.held.set(source, keys);
    else { keys = this.held.get(source); this.held.delete(source); }
    // Several arrows and physical Shift can share one matrix key. Release it
    // only after the last source lets go; browser key-repeat adds no extra hold.
    for (const key of keys) {
      const id = key.index * 5 + key.bit;
      const before = this.keyCounts.get(id) || 0;
      const after = before + (pressed ? 1 : -1);
      if (after) this.keyCounts.set(id, after); else this.keyCounts.delete(id);
      if (!before || !after) this.hw.keyboard.switchKeys([key], pressed);
    }
  }
  releaseKeys() {
    for (const [source, keys] of this.held) this.holdKeys(source, keys, false);
  }
  async tap(key) {
    const keys = this.keys.get(/^\d$/.test(key) ? `Digit${key}` : key);
    if (!keys || !this.hw) return;
    this.container.focus({ preventScroll: true });
    const source = Symbol('touch key');
    this.holdKeys(source, keys, true);
    await new Promise(resolve => setTimeout(resolve, 100));
    this.holdKeys(source, keys, false);
  }
}
