// Rebuild the pinned upstream modules with local patches; see ../vendor/README.md.
import { readFile, writeFile, mkdir, copyFile } from 'node:fs/promises';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHash } from 'node:crypto';
import { patchEmulator } from './patch-emulator.mjs';
import { patchAyumi } from './patch-ayumi.mjs';
const output = resolve(dirname(fileURLToPath(import.meta.url)), '../vendor');
const upstream = resolve(process.argv[2] || '.tmp/zx-dream');
const roms = resolve(process.argv[3] || 'C:/Program Files (x86)/Fuse/roms');
const modules = ['lang/ru.js', 'spectrum/common.js', 'hardware/hw_state.js',
  'hardware/z80.js', 'hardware/bus.js', 'hardware/port_fe.js', 'hardware/port_7ffd.js',
  'hardware/rom.js', 'hardware/ram.js', 'hardware/display.js', 'hardware/keyboard.js',
  'hardware/betadisk.html', 'hardware/floppy.js', 'hardware/vg93.js',
  'hardware/clock.js', 'hardware/psg.js'];
await mkdir(join(output, 'roms'), { recursive: true });
const sources = [];
const hashes = {};
for (const name of modules) {
  const bytes = await readFile(join(upstream, 'source/modules', name));
  hashes[name] = createHash('sha256').update(bytes).digest('hex');
  const source = bytes.toString('utf8');
  // Only Beta Disk is HTML; its entire body is one script, with no UI template.
  const js = name.endsWith('.html') ? source.match(/<script[^>]*>([\s\S]*?)<\/script>/)[1] : source;
  sources.push(`// Upstream module: ${name}\n${js}`);
}
await writeFile(join(output, 'zx-dream.js'), patchEmulator(sources.join('\n')));
const ayumiSource = await readFile(join(upstream, 'source/js/ayumi.js'), 'utf8');
await writeFile(join(output, 'ayumi.js'), patchAyumi(ayumiSource));
await copyFile(join(upstream, 'LICENSE'), join(output, 'LICENSE.zx-dream'));
for (const [target, source] of Object.entries({ '48.rom': '128-1.rom',
  '48turbo.rom': '128-1.rom', '128tr.rom': '128-0.rom', 'tr5_04t.rom': 'trdos.rom' })) {
  // Retain upstream lookup names; the actual machine uses stock 128K / TR-DOS 5.03.
  await copyFile(join(roms, source), join(output, 'roms', target));
}
for (const name of ['ayumi.js', ...['48.rom', '48turbo.rom', '128tr.rom', 'tr5_04t.rom'].map(n => `roms/${n}`)]) {
  hashes[name] = createHash('sha256').update(await readFile(join(output, name))).digest('hex');
}
await writeFile(join(output, 'provenance.json'), JSON.stringify({
  upstream: 'https://github.com/XMypuK/zx-dream',
  revision: 'ef68e190753d599752d1367050a94b85a06121c8', modules: hashes,
  upstreamAssets: { 'ayumi.js': createHash('sha256').update(ayumiSource).digest('hex') },
  localPatches: ['web/tools/patch-emulator.mjs', 'web/tools/patch-webgl-streaming.mjs', 'web/tools/patch-cpu-slices.mjs',
    'web/tools/webgl-presentation.js', 'web/tools/patch-ayumi.mjs']
}, null, 2) + '\n');
