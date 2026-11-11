// The WASM core owns memory and consumes the same clock deadlines as ZX-Dream.
// Device callbacks see the exact port strobe, rather than the start of an opcode.
async function loadBinary() {
  const response = await fetch(new URL('vendor/spectrum-z80.wasm', import.meta.url));
  if (!response.ok) throw new Error(`WASM CPU request failed (${response.status})`);
  return response.arrayBuffer();
}

export async function createWasmCpu(loadRom, { fast = true, audio = false, binary = loadBinary() } = {}) {
  const romNames = ['48.rom', '48turbo.rom', '128tr.rom', 'tr5_04t.rom'];
  const [bytes, roms] = await Promise.all([binary, Promise.all(romNames.map(loadRom))]);
  let bus, advanceDevices, runLimit, currentTstates = 0;
  const listeners = new Set();
  const { instance } = await WebAssembly.instantiate(bytes, {
    spectrum: {
      in_port(port, time) {
        currentTstates = time;
        return bus.io_read(port);
      },
      out_port(port, value, time) {
        currentTstates = time;
        bus.io_write(port, value);
      },
      trdos(enabled) { bus.var_write('rom_trdos', !!enabled); },
      dispatch(time) {
        currentTstates = time;
        return Math.min(runLimit, Math.ceil(advanceDevices(time)));
      },
      audio_block(left, right, sampleCount, tstates) {
        const packet = {
          left: pcm.slice(left / 4, left / 4 + sampleCount),
          right: pcm.slice(right / 4, right / 4 + sampleCount),
          sampleCount, tstates
        };
        for (const listener of listeners) listener(packet);
      }
    }
  });
  const core = instance.exports;
  const memory = new Uint8Array(core.memory.buffer);
  const pcm = new Float32Array(core.memory.buffer);
  roms.forEach((rom, index) => {
    if (rom.length !== 0x4000) throw new Error(`Invalid ROM length for ${romNames[index]}`);
    memory.set(rom, core.rom_ptr() + index * 0x4000);
  });
  return {
    audio: audio ? { get_onDataReady: () => ({ subscribe: listener => listeners.add(listener) }) } : null,
    connect(hardwareBus) {
      bus = hardwareBus;
      bus.on_mem_read(core.read);
      bus.on_mem_write(core.write);
      bus.on_var_write((name, value) => core.page(value), 'port_7ffd_value');
      bus.on_var_write((name, value) => core.int_line(value), 'intrq');
      bus.on_var_write(core.nmi, 'nmirq');
      bus.on_reset(core.reset);
      core.native_audio(audio);
      core.reset(0);
    },
    get_tstates: core.ticks,
    set_tstates(time) {
      currentTstates = time;
      core.set_ticks(time);
    },
    get_instruction_start() { return currentTstates; },
    reschedule_event(deadline) {
      if (deadline < runLimit) core.tighten_deadline(Math.max(currentTstates, Math.ceil(deadline)));
    },
    run_until(limit, dispatch) {
      runLimit = Math.ceil(limit);
      advanceDevices = dispatch;
      try { currentTstates = core.run(runLimit, fast); }
      finally { advanceDevices = null; runLimit = 0; }
    },
    process: core.step,
    get_state() { return { pc: core.pc() }; },
    screen(bank) {
      const address = core.screen(bank);
      return address ? memory.subarray(address, address + 0x1b00) : null;
    }
  };
}
