// Preserve the pinned renderer's vertices and pixels while streaming only its
// dirty prefix. All replacements are confined to the upstream WebGL module.
export function patchWebGLStreaming(source) {
  function replace(before, after) {
    if ((source.match(new RegExp(before.source, 'g')) || []).length !== 1) {
      throw new Error(`WebGL streaming anchor changed: ${before}`);
    }
    source = source.replace(before, after);
  }
  replace(/glContext\.bindBuffer\(glContext\.ARRAY_BUFFER, buffer\);/, `$&
        // Allocate each bank's vertex storage once, not on every redraw.
        glContext.bufferData(glContext.ARRAY_BUFFER, this._glBuffer.byteLength, glContext.DYNAMIC_DRAW);`);
  const vertices = [
    ['x', 'y', 'sx', 'sy'], ['p', 'y', 'sp', 'sy'], ['p', 'q', 'sp', 'sq'],
    ['x', 'y', 'sx', 'sy'], ['x', 'q', 'sx', 'sq'], ['p', 'q', 'sp', 'sq']
  ];
  const fill = vertices.map(vertex => '                    ' + vertex
    .map(value => `this._glBuffer[glBufferIndex++] = ${value};`).join(' ')).join('\n');
  replace(/sq = sy\+1,[\s\S]*?glData = \[[\s\S]*?glBufferIndex \+= 24;/, `sq = sy+1;

                    // Write the same six vertices directly, without a temporary
                    // 24-number Array for every dirty group of eight pixels.
${fill}`);
  replace(/ctx\.bufferData\(ctx\.ARRAY_BUFFER, this\._glBuffer, ctx\.STATIC_DRAW\);/, `// Empty frames never upload. Sparse updates transfer only populated vertices.
                ctx.bufferSubData(ctx.ARRAY_BUFFER, 0, this._glBuffer.subarray(0, glBufferIndex));`);
  replace(/\r?\n\s*ctx\.finish\(\);/, `
                // flush submits the bank before canvas-to-texture presentation.
                // The browser synchronizes that copy; do not block the CPU on finish().`);
  return source;
}
