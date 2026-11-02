import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
import { spawnSync, execFileSync } from 'node:child_process';
import assert from 'node:assert/strict';
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
assert.equal(catalogue.images.length, tracked.length);
assert.equal(catalogue.images.filter(image => image.root).length, tracked.filter(path => !path.includes('/')).length);
for (const image of catalogue.images) assert.match(image.sha256, /^[a-f0-9]{64}$/);
console.log(`Build guards pass: LFS pointer, invalid TRD, uncommitted content; ${tracked.length} authenticated images.`);
