import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawnSync, execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
import { showInLibrary } from './catalog-policy.mjs';
const fixture = resolve('.tmp/web-check-input');
await mkdir(fixture, { recursive: true });
const file = resolve(fixture, 'ZX-Music-Menu.trd');
function rejected(message) {
  const result = spawnSync(process.execPath, ['web/tools/build.mjs', '.tmp/web-check-output', fixture], { encoding: 'utf8' });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, message);
}
await writeFile(file, 'version https://git-lfs.github.com/spec/v1\noid sha256:' + '0'.repeat(64) + '\nsize 655360\n');
rejected(/Unresolved Git LFS image/);
const bytes = Buffer.alloc(655360);
await writeFile(file, bytes);
rejected(/Invalid TRD geometry or system sector/);
bytes[0x8e7] = 0x10;
await writeFile(file, bytes);
rejected(/Image differs from committed content/);
const catalogue = JSON.parse(await readFile('.tmp/web-site/catalog.json', 'utf8'));
const tracked = execFileSync('git', ['ls-files', '-z', '--', ':(icase)*.trd'], {encoding:'utf8'}).split('\0').filter(Boolean);
const source = JSON.parse(await readFile('toolkit/trd_catalog.json', 'utf8'));
const expected = tracked.filter(path => {
  const entry = source.images.find(image => image.path === path);
  return showInLibrary(path, entry, source.groups[entry?.group]);
});
assert.deepEqual(catalogue.images.map(image => image.path).sort(), expected.sort());
assert.equal(catalogue.images.filter(image => image.root).length, expected.filter(path => !path.includes('/')).length);
for (const path of ['ZX-audiobook-IMA-ADPCM-direct-test.trd', 'ZX-audiobook-IMA3-compact-tables.trd',
  'ZX-music-Entertainer-IMA3.trd', 'ZX-music-Sea-Foam-RAM-auto.trd']) {
  assert(!catalogue.images.some(image => image.path === path), `${path} is a legacy PDM audition`);
  assert.equal((await readFile(resolve('.tmp/web-site/disks', path))).length, 655360, 'Historical direct downloads remain intact');
}
for (const path of ['ZX-Music-Menu.trd', 'ZX-music-Entertainer-AY.trd', 'ZX-audiobook-OHenry-AY50-test.trd',
  'ZX-audiobook-YM2149-voice-test.trd', 'ZX-video-refined_part02.trd']) {
  assert(catalogue.images.some(image => image.path === path), `${path} must remain available`);
}
assert(!catalogue.images.some(image => image.path.startsWith('audiobook-beeper/')));
for (const image of catalogue.images) assert.match(image.sha256, /^[a-f0-9]{64}$/);
console.log(`Build guards pass: LFS pointer, invalid TRD, uncommitted content; ${expected.length} visible images, ${tracked.length - expected.length} archived PDM images.`);
