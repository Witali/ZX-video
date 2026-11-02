/* global ZX_Bus, ZX_Clock, ZX_Z80, ZX_ROM, ZX_RAM, ZX_Display, ZX_Keyboard,
  ZX_Floppy, ZX_BetaDisk, ZX_PortFE, ZX_Port7FFD, ZX_PSG */
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
    this.onDiskActivity = () => {};
    this.diskActive = false;
    this.diskBusyUntil = 0;
    this.held = new Set();
    const rows = ['ShiftLeft,Z,X,C,V', 'A,S,D,F,G', 'Q,W,E,R,T', '1,2,3,4,5',
      '0,9,8,7,6', 'P,O,I,U,Y', 'Enter,L,K,J,H', 'Space,AltLeft,M,N,B'];
    this.keys = new Map(rows.flatMap((row, index) => row.split(',').map((key, bit) =>
      [key.length === 1 ? (/\d/.test(key) ? `Digit${key}` : `Key${key}`) : key, { index, bit }])));
    container.addEventListener('keydown', event => this.keyboard(event, true));
    container.addEventListener('keyup', event => this.keyboard(event, false));
    container.addEventListener('blur', () => this.releaseKeys());
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
    h.bus.opt('RENDERING_PARAMS', { scale: 1, scaleType: 1, rendererType: 1, renderOnAnimationFrame: false });
    const canvases = [document.createElement('canvas'), document.createElement('canvas'), document.createElement('canvas')];
    canvases.forEach((canvas, index) => {
      canvas.width = index ? 256 : 288;
      canvas.height = index ? 192 : 224;
      canvas.className = index ? 'screen-layer' : 'border-layer';
      this.container.append(canvas);
    });
    h.display.bind(canvases);
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
  async enableAudio() {
    if (!this.audio) {
      const Audio = window.AudioContext || window.webkitAudioContext;
      if (!Audio) throw new Error('This browser does not support Web Audio.');
      this.audio = new Audio({ sampleRate: 44100 });
      await this.audio.audioWorklet.addModule(new URL('audio-worklet.js', import.meta.url));
      this.output = new AudioWorkletNode(this.audio, 'spectrum-audio', { outputChannelCount: [2] });
      this.gain = this.audio.createGain();
      this.output.connect(this.gain).connect(this.audio.destination);
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
  keyboard(event, pressed) {
    const code = { ShiftRight: 'ShiftLeft', AltRight: 'AltLeft' }[event.code] || event.code;
    const key = this.keys.get(code);
    if (!key || !this.hw) return;
    event.preventDefault();
    if (pressed) this.held.add(code); else this.held.delete(code);
    this.hw.keyboard.switchKeys([key], pressed);
  }
  releaseKeys() {
    if (this.hw) for (const code of this.held) this.hw.keyboard.switchKeys([this.keys.get(code)], false);
    this.held.clear();
  }
  async tap(key) {
    const mapping = { Enter: { index: 6, bit: 0 }, Space: { index: 7, bit: 0 },
      '1': { index: 3, bit: 0 }, '2': { index: 3, bit: 1 } }[key];
    this.hw.keyboard.switchKeys([mapping], true);
    await new Promise(resolve => setTimeout(resolve, 100));
    this.hw.keyboard.switchKeys([mapping], false);
  }
}
