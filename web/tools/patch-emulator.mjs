import { readFileSync } from 'node:fs';
const webglPresentation = readFileSync(new URL('./webgl-presentation.js', import.meta.url), 'utf8');
// Local fixes to pinned ZX-Dream. Match exact upstream text so upgrades fail safely.
export function patchEmulator(source) {
  function replace(before, after) {
    const found = before instanceof RegExp ? before.test(source) : source.includes(before);
    if (!found) throw new Error(`Missing upstream patch anchor: ${String(before).slice(0, 60)}`);
    source = source.replace(before, after);
  }
  replace('var opcode = read_opcode();', `// DD/FD CB's final opcode is a non-M1 operand fetch: 3 T, no R increment.
        var opcode = (prefix_bit && (prefix_ix || prefix_iy)) ? read_operand_byte() : read_opcode();`);
  const begin = source.indexOf('        if (prefix_bit) {');
  const end = source.indexOf('} // endif (prefix_bit)', begin);
  const bitCode = source.slice(begin, end);
  if ((bitCode.match(/ts_cnt \+= 6;/g) || []).length !== 6) throw new Error('Indexed CB timing patch changed');
  source = source.slice(0, begin) + bitCode.replaceAll('ts_cnt += 6;', 'ts_cnt += 3; // Indexed CB internal cycles; opcode fetch is counted separately.') + source.slice(end);
  const ldBegin = source.indexOf('// LD r, n');
  const ldEnd = source.indexOf('// 00xxx010', ldBegin);
  const ldCode = source.slice(ldBegin, ldEnd);
  if ((ldCode.match(/ts_cnt \+= 5;/g) || []).length !== 2) throw new Error('Indexed immediate timing patch changed');
  source = source.slice(0, ldBegin) + ldCode.replaceAll('ts_cnt += 5;', 'ts_cnt += 2; // LD (IX/IY+d),n totals 19 T, including both operands.') + source.slice(ldEnd);
  replace('prefix_iy = state.prefix_dd;', 'prefix_ix = state.prefix_dd;');
  replace('state.imf = imf;', 'state.memptr = memptr;\n        state.q = q;\n        state.imf = imf;');
  replace('imf = state.imf;', 'memptr = state.memptr ?? 0;\n        q = state.q ?? 0;\n        imf = state.imf;');
  replace(/if \(!\(opcode & 0x08\)\) \{\r?\n                    set_iff1\(get_iff2\(\)\);\r?\n                \}/, 'set_iff1(get_iff2()); // RETN and RETI aliases both restore IFF1 from IFF2.');
  replace('data = read_io_byte(( new_b << 8 ) | regs.c ); // именно new_b', 'data = read_io_byte(( old_b << 8 ) | regs.c ); // INI/IND reads before decrementing B.');
  replace('write_io_byte(( regs.b << 8 ) | regs.c, data);', 'write_io_byte(( new_b << 8 ) | regs.c, data); // OUTI/OUTD decrements B before the port write.');
  replace('var BYTES_PER_TRACK_MFM = 6312;', 'var BYTES_PER_TRACK_MFM = 6250;');
  replace('var BYTES_PER_TRACK_FM = 3156;', 'var BYTES_PER_TRACK_FM = 3125;');
  replace('var _intrqDurationTstates = 32;', 'var _intrqDurationTstates = 36; // Original Spectrum 128 ULA interrupt pulse.');
  replace('var _intervalsDependOnFrequency = true;', 'var _intervalsDependOnFrequency = false; // Drive rotation stays at 300 rpm independently of CPU frequency.');
  const clockBegin = source.indexOf('function ZX_Clock()');
  const clockEnd = source.indexOf('function TaskQueue(', clockBegin);
  let clockCode = source.slice(clockBegin, clockEnd);
  if ((clockCode.match(/Date\.now\(\)/g) || []).length !== 5) throw new Error('Host clock patch changed');
  clockCode = clockCode.replaceAll('Date.now()', 'hostNow()');
  clockCode = clockCode.replace('function ZX_Clock() {', `function ZX_Clock() {
    // All hardware deadlines remain on the shared emulated T-state timeline.
    // The browser's monotonic clock paces that timeline; wall-clock edits cannot jump it.
    var hostNow = typeof performance !== 'undefined' && performance.now
        ? function () { return performance.now(); } : function () { return Date.now(); };`);
  const capPattern = /if \(plannedTstates > _maxBoostTstates\) \{[\s\S]*?_baseTimestamp \+= [^\n]+\r?\n\t\t\tplannedTstates = _maxBoostTstates;\r?\n\t\t\}/g;
  if ((clockCode.match(capPattern) || []).length !== 2) throw new Error('Catch-up patch changed');
  clockCode = clockCode.replace(capPattern, `if (plannedTstates > _maxBoostTstates) {
            // Bound work per callback, retaining the original real-time origin and debt.
            // Later callbacks catch up the whole machine without skipping hardware events.
            plannedTstates = _maxBoostTstates;
        }`);
  const commentBegin = clockCode.indexOf('\t// Принцип выполнения итерации');
  const processBegin = clockCode.indexOf('\tfunction process()', commentBegin);
  if (commentBegin < 0 || processBegin < 0) throw new Error('Clock documentation anchor changed');
  clockCode = clockCode.slice(0, commentBegin) + `    // Advance every module from one CPU T-state counter and ordered event queue.
    // Host callback cadence only controls the amount of pending work, not event phases.
    // Pause/resume explicitly starts a new host-time origin without advancing the machine.
` + clockCode.slice(processBegin);
  source = source.slice(0, clockBegin) + clockCode + source.slice(clockEnd);
  const trdBegin = source.indexOf('    this.insertTRD = function');
  const trdEnd = source.indexOf('    this.insertSCL = function', trdBegin);
  const loopBegin = source.indexOf('            for ( var sec = 0; sec < 16; sec++)', trdBegin);
  const loopEnd = source.indexOf('\n        }', loopBegin);
  if (loopBegin < 0 || loopEnd > trdEnd) throw new Error('TRD layout patch changed');
  source = source.slice(0, loopBegin) + `            // Canonical TR-DOS MFM track, matching Fuse's INTERLEAVE_2 layout:
            // one 10-byte initial gap; physical IDs 1,9,2,10,...,8,16;
            // 378 bytes per sector including ID/data marks, CRCs and gaps;
            // 192 final gap bytes complete 6250 bytes at 250 kbit/s, 300 rpm.
            trackStream.writeMultiple(new Array(10).fill(0x4E));
            for (var physical = 0; physical < 16; physical++) {
                var sec = (physical >> 1) + ((physical & 1) ? 8 : 0);
                var offset = index + sec * sectorSize;
                var payload = offset < bin.length ? bin : new Array(sectorSize).fill(0);
                var payloadOffset = offset < bin.length ? offset : 0;
                trackStream.writeMultiple(createTrDosSector(cylIndex, sec, sectorSize, payload, payloadOffset).slice(10));
            }
            trackStream.writeMultiple(new Array(6250 - trackStream.get_length()).fill(0x4E));
            index += 16 * sectorSize;` + source.slice(loopEnd);
  // Keep the Spectrum framebuffer native. Canvas presents a whole completed
  // frame at an integer size before browser/DPI composition. CSS only maps
  // the device-sized presentation surface to CSS units.
  const canvasBegin = source.indexOf('function PutImageDataRenderer()');
  const canvasEnd = source.indexOf('function DrawImageRenderer()', canvasBegin);
  if (canvasBegin < 0 || canvasEnd < 0) throw new Error('Canvas renderer anchor changed');
  let canvasCode = source.slice(canvasBegin, canvasEnd);
  if (!canvasCode.includes('ctx.putImageData(this._samples[sampleIndex], dx, dy);')) {
    throw new Error('Canvas pixel update anchor changed');
  }
  canvasCode = canvasCode.replace('this._samples = [];', `this._samples = [];
    this._nativeLayers = [];
    this._nativeContexts = [];
    this._frames = [];
    this._displayedLayer = -1;
    this._presentationChanged = true;`);
  canvasCode = canvasCode.replace('scale = ( this._scaleType == VAL_SCALE_METHOD_PRE ) ? this._scale : 1,',
    'scale = 1, // Samples and frame storage always use the native 256 x 192 raster.');
  canvasCode = canvasCode.replace("this._layer1Ctx = this._layer1.getContext('2d', { alpha: false });", `this._layer1Ctx = this._layer1.getContext('2d', { alpha: false });
        for (var layer = 0; layer < 2; layer++) {
            var native = this._createCanvas(256, 192);
            var context = native.getContext('2d', { alpha: false });
            this._nativeLayers[layer] = native;
            this._nativeContexts[layer] = context;
            this._frames[layer] = context.createImageData(256, 192);
        }
        this._layer0Ctx.imageSmoothingEnabled = false;
        this._layer1Ctx.imageSmoothingEnabled = false;
        // Present border and active pixels on one device-sized surface. Separate
        // CSS-scaled canvases can acquire different sampling grids at fractional DPI.
        if (this._layer0.style) this._layer0.style.display = 'none';
        if (this._layer1.style) this._layer1.style.display = 'none';
        this._displayedLayer = -1;
        this._presentationChanged = true;`);
  canvasCode = canvasCode.replace('\tdrawData: function', `    displayLayer: function (layer) {
        if (this._displayedLayer !== layer || this._presentationChanged ||
            this._presentedWidth !== this._border.width || this._presentedHeight !== this._border.height ||
            this._presentedViewport !== this._border.spectrumViewport) {
            this._displayedLayer = layer;
            this._presentationChanged = false;
            this._presentFrame();
        }
    },
    drawBorder: function (color) {
        this._lastBorderColor = color.slice(0, 4);
        if (this._border.spectrumViewport) this._presentFrame();
        else RendererBase.prototype.drawBorder.call(this, color);
    },
    _presentFrame: function () {
        var ctx = this._borderCtx, border = this._borderWidth * this._scale;
        this._presentedWidth = this._border.width;
        this._presentedHeight = this._border.height;
        this._presentedViewport = this._border.spectrumViewport;
        var viewport = this._border.spectrumViewport ||
            { x: border, y: border, width: 256 * this._scale, height: 192 * this._scale };
        ctx.fillStyle = 'rgba(' + this._lastBorderColor.join(',') + ')';
        ctx.fillRect(0, 0, this._border.width, this._border.height);
        ctx.imageSmoothingEnabled = false;
        if (this._displayedLayer >= 0) ctx.drawImage(this._nativeLayers[this._displayedLayer],
            0, 0, 256, 192, viewport.x, viewport.y, viewport.width, viewport.height);
    },
\tdrawData: function`);
  canvasCode = canvasCode.replace('sampleScale = ( this._scaleType == VAL_SCALE_METHOD_PRE ) ? this._scale : 1,',
    'sampleScale = 1,');
  canvasCode = canvasCode.replace('if (ctx) {', `if (ctx) {
            var changed = false;
            var frame = this._frames[layer];`);
  canvasCode = canvasCode.replace('ctx.putImageData(this._samples[sampleIndex], dx, dy);', `// Eight adjacent native pixels; Spectrum memory is not row-major.
                    frame.data.set(this._samples[sampleIndex].data, (dy * 256 + dx) * 4);
                    changed = true;`);
  canvasCode = canvasCode.replace(/\t\t\t}\r?\n\t\t}\r?\n\t}\r?\n}\);/, `            }
            if (changed) {
                this._presentationChanged = true;
                this._nativeContexts[layer].putImageData(frame, 0, 0);
                ctx.drawImage(this._nativeLayers[layer], 0, 0, 256, 192,
                    0, 0, ctx.canvas.width, ctx.canvas.height);
            }
        }
    }
});`);
  if (!canvasCode.includes('ctx.drawImage(this._nativeLayers[layer]')) throw new Error('Canvas presentation anchor changed');
  source = source.slice(0, canvasBegin) + canvasCode + source.slice(canvasEnd);
  const webglBegin = source.indexOf('function WebGLRenderer()');
  const webglEnd = source.indexOf('// Upstream module: hardware/keyboard.js', webglBegin);
  if (webglBegin < 0 || webglEnd < 0) throw new Error('WebGL presentation anchor changed');
  const webglCode = source.slice(webglBegin, webglEnd);
  const drawAnchor = 'if (glBufferIndex) {';
  if (!webglCode.includes(drawAnchor)) throw new Error('WebGL dirty upload anchor changed');
  source = source.slice(0, webglBegin)
    + webglCode.replace(drawAnchor, `${drawAnchor}\n                this._presentationChanged = true;`)
    + webglPresentation + '\n\n' + source.slice(webglEnd);
  return source;
}
