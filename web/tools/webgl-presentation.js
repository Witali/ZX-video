// Local presentation override for pinned ZX-Dream. Bank rendering stays native;
// only one complete, device-sized WebGL canvas is exposed to the browser.
Object.assign(WebGLRenderer.prototype, {
    // Atlas coordinates need more precision than the minimum lowp guarantee.
    _renderFragmentShaderSource: WebGLRenderer.prototype._renderFragmentShaderSource
        .replace('precision lowp float;', 'precision highp float;'),
    bind: function (canvases) {
        this._border = canvases[0];
        this._layer0 = canvases[1];
        this._layer1 = canvases[2];
        this._layer0.style.display = 'none';
        this._layer1.style.display = 'none';
        const options = { preserveDrawingBuffer: true, alpha: false, antialias: false };
        this._screenCtx = this._glGetContext(this._border, options);
        this._layer0Ctx = this._glGetContext(this._layer0, options);
        this._layer1Ctx = this._glGetContext(this._layer1, options);
        if (!this._screenCtx || !this._layer0Ctx || !this._layer1Ctx) {
            throw new Error(ZX_Lang.ERR_CANNOT_CREATE_CANVAS);
        }
        this._glInitWebGLContext(this._layer0Ctx);
        this._glInitWebGLContext(this._layer1Ctx);
        const gl = this._screenCtx;
        this._presentationProgram = this._glCreateAndLinkProgram(gl, [
            this._glCreateShader(gl, gl.VERTEX_SHADER, this._copyVertexShaderSource),
            this._glCreateShader(gl, gl.FRAGMENT_SHADER,
                this._copyFragmentShaderSource.replace('precision lowp float;', 'precision highp float;'))
        ]);
        gl.useProgram(this._presentationProgram);
        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        // Copy shader expects top-left-origin unit coordinates, not clip coordinates.
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([0, 0, 0, 1, 1, 0, 1, 1]), gl.STATIC_DRAW);
        const position = gl.getAttribLocation(this._presentationProgram, 'a_position');
        gl.enableVertexAttribArray(position);
        gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
        this._copyTexture = gl.createTexture();
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, this._copyTexture);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.NEAREST);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.NEAREST);
        gl.uniform1i(gl.getUniformLocation(this._presentationProgram, 'u_source'), 0);
        this._displayedLayer = -1;
        this._presentationChanged = true;
        this._lastBorderColor = [0, 0, 0, 255];
    },
    displayLayer: function (layer) {
        if (this._displayedLayer !== layer || this._presentationChanged) {
            const gl = this._screenCtx;
            gl.bindTexture(gl.TEXTURE_2D, this._copyTexture);
            // Canvas-to-texture transfer; no readPixels, PNG or JS RGBA readback.
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE,
                layer ? this._layer1 : this._layer0);
            this._displayedLayer = layer;
            this._presentationChanged = false;
            this._presentFrame();
        }
    },
    drawBorder: function (color) {
        this._lastBorderColor = color.slice(0, 4);
        this._presentFrame();
    },
    _presentFrame: function () {
        const gl = this._screenCtx, color = this._lastBorderColor;
        const scale = this._border.width / (256 + 2 * this._borderWidth);
        const border = this._borderWidth * scale;
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.clearColor(color[0] / 255, color[1] / 255, color[2] / 255, 1);
        gl.clear(gl.COLOR_BUFFER_BIT);
        if (this._displayedLayer >= 0) {
            // Integer viewport and NEAREST filtering give each native texel
            // exactly 2x2 output pixels, on the same grid as the border.
            gl.viewport(border, border, 256 * scale, 192 * scale);
            gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        }
        gl.flush();
    }
});
