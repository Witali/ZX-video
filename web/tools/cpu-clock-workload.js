// Shared Node/browser fixture. Actual Z80 + banked RAM + bus + 50-Hz clock;
// no display or synthesis. Each kernel runs the same amount of MACHINE time.
function cpuClockWorkload(kind) {
    var kernels = {
        // Arithmetic/flags, an unconditional JP back to 8000h.
        alu: [0x80,0x89,0x92,0x9b,0xa4,0xad,0xb0,0xb9,0x04,0x0d,0x14,0x1d,0x24,0x2d,0xc3,0x00,0x80],
        // Reinitialize HL/DE/BC and repeatedly copy 4 KiB using real LDIR steps.
        copy: [0x21,0x00,0x90,0x11,0x00,0xa0,0x01,0x00,0x10,0xed,0xb0,0xc3,0x00,0x80],
        // DD loads/ALU/store, indexed CB rotate, INC IX; address resets each loop.
        indexed: [0xdd,0x21,0x00,0xa0,0xdd,0x7e,0x01,0xdd,0x86,0x02,0xdd,0x77,0x03,0xdd,0xcb,0x04,0x06,0xdd,0x23,0xc3,0x00,0x80],
        // DJNZ busy loop, CALL/RET and INC A. Exercises stack and taken branches.
        flow: [0x06,0xff,0x10,0xfe,0xcd,0x0b,0x80,0xc3,0x00,0x80,0x00,0x3c,0xc9]
    };
    var bus = new ZX_Bus(), cpu = new ZX_Z80(), clock = new ZX_Clock(), ram = new ZX_RAM();
    cpu.connect(bus); clock.connect(bus,cpu); ram.connect(bus);
    bus.on_instruction_read(function () { return 255; }, {range:{begin:0,end:0x3fff}});
    bus.on_mem_read(function () { return 255; }, {range:{begin:0,end:0x3fff}});
    bus.opt('TSTATES_PER_INTRQ',70908); bus.opt('INTRQ_PERIOD',20); bus.opt('EXTENDED_MEMORY',0);
    for (var address = 0x4000; address < 65536; address++) bus.mem_write(address,(address*73+(address>>>7))&255);
    kernels[kind].forEach(function (value,index) { bus.mem_write(0x8000+index,value); });
    var state=cpu.get_state();
    Object.assign(state,{pc:0x8000,hl:0xa000,de:0xb000,bc:0x1234,sp:0xff00,iff:0}); cpu.set_state(state);
    var interrupts=[];
    bus.on_var_write(function(name,value){if(value)interrupts.push(clock.get_tstates());},'intrq');
    return {cpu:cpu,clock:clock,bus:bus,interrupts:interrupts};
}
