// Use the Clang/wasm-ld bundled with z80-tester's Emscripten SDK. The
// standalone module needs no Emscripten loader, C runtime, or host filesystem.
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const sdkArgument = process.argv[2] || process.env.EMSDK;
if (!sdkArgument) throw new Error('Usage: node web/tools/build-spectrum-wasm.mjs <emsdk> [python]');
const sdk = resolve(sdkArgument);
const python = process.argv[3] || 'python3';
const root = fileURLToPath(new URL('../../', import.meta.url));
const build = join(root, '.tmp/spectrum-wasm');
const clang = join(sdk, 'upstream/bin', process.platform === 'win32' ? 'clang.exe' : 'clang');
const sysroot = join(sdk, 'upstream/emscripten/cache/sysroot');
mkdirSync(build, { recursive: true });
execFileSync(python, [join(root, 'emulator/tools/generate_fast_decoder.py'), '--spectrum',
  '--output', join(build, 'spectrum_slices.h')], { stdio: 'inherit' });
execFileSync(clang, ['--target=wasm32-unknown-unknown', '--sysroot=' + sysroot, '-std=c11',
  '-O3', '-DNDEBUG', '-ffreestanding', '-nostdlib', '-Wall', '-Wextra', '-Werror',
  '-I', build, '-Wl,--no-entry,--strip-all,--export-memory',
  join(root, 'emulator/src/spectrum_wasm.c'), '-o', join(root, 'web/vendor/spectrum-z80.wasm')],
{ stdio: 'inherit' });
