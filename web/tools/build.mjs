import { readFile, writeFile, mkdir, copyFile, readdir, rm, lstat } from 'node:fs/promises';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';

const source = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const root = resolve(source, '..');
const output = resolve(root, process.argv[2] || '.tmp/web-site');
// Optional disk source supports sparse worktrees; each image is still bound to HEAD.
const diskRoot = resolve(process.argv[3] || root);
const scratch = join(root, '.tmp');
if (dirname(output) !== scratch) {
  throw new Error('Output must be one directory directly below this checkout\'s .tmp directory');
}
for (const path of [scratch, output]) {
  const info = await lstat(path).catch(error => { if (error.code !== 'ENOENT') throw error; });
  if (info?.isSymbolicLink()) throw new Error('Output symlinks are not allowed');
}
// This exact task-owned output is regenerated so removed disks cannot leak into a later build.
await rm(output, { recursive: true, force: true });
const catalogue = JSON.parse(await readFile(join(root, 'toolkit/trd_catalog.json'), 'utf8'));
const described = new Map(catalogue.images.map(image => [image.path, image]));
const tracked = execFileSync('git', ['ls-files', '-z', '--', ':(icase)*.trd'], { cwd: root, encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 })
  .split('\0').filter(path => /\.trd$/i.test(path)).sort();
const images = [];
for (const path of tracked) {
  const bytes = await readFile(join(diskRoot, path));
  if (bytes.subarray(0, 42).toString().startsWith('version https://git-lfs.github.com/spec/')) {
    throw new Error(`Unresolved Git LFS image: ${path}. Run git lfs pull first.`);
  }
  if (![163840, 327680, 655360].includes(bytes.length) || bytes[0x8e7] !== 0x10) {
    throw new Error(`Invalid TRD geometry or system sector: ${path}`);
  }
  const sha256 = createHash('sha256').update(bytes).digest('hex');
  const pointer = execFileSync('git', ['show', `HEAD:${path}`], { cwd: root });
  const oid = pointer.toString().match(/^oid sha256:([a-f0-9]{64})$/m)?.[1];
  if (oid ? sha256 !== oid : !bytes.equals(pointer)) throw new Error(`Image differs from committed content: ${path}`);
  const entry = described.get(path);
  if (entry && (entry.sha256 !== sha256 || entry.bytes !== bytes.length)) {
    throw new Error(`Catalogue identity mismatch: ${path}`);
  }
  const diskPath = `disks/${path}`;
  await mkdir(dirname(join(output, diskPath)), { recursive: true });
  await copyFile(join(diskRoot, path), join(output, diskPath));
  const group = catalogue.groups[entry?.group];
  images.push({ path, url: diskPath, name: path.split('/').pop(),
    category: path.startsWith('toolkit/') || /video/i.test(path) ? 'Video' : /music|entertainer|sea.foam/i.test(path) ? 'Music' : 'Audio',
    root: !path.includes('/'), catalogued: !!entry, bytes: bytes.length, sha256,
    description: group?.description || entry?.subject || 'Retained project experiment; no curated catalogue description.',
    guide: group?.guide || 'TRD_CATALOG.md' });
}
// Publish only this explicit static allowlist and tracked TRDs, never the checkout.
async function copyTree(from, to) {
  await mkdir(to, { recursive: true });
  for (const entry of await readdir(from, { withFileTypes: true })) {
    if (entry.isSymbolicLink()) throw new Error('Symlinks are not allowed in the site');
    if (entry.isDirectory()) await copyTree(join(from, entry.name), join(to, entry.name));
    else await copyFile(join(from, entry.name), join(to, entry.name));
  }
}
await mkdir(output, { recursive: true });
for (const name of ['index.html', 'styles.css', 'app.js', 'emulator.js', 'audio-worklet.js', 'display-scale.js']) {
  await copyFile(join(source, name), join(output, name));
}
await copyTree(join(source, 'vendor'), join(output, 'vendor'));
await writeFile(join(output, 'catalog.json'), JSON.stringify({ images }, null, 2) + '\n');
await writeFile(join(output, '.nojekyll'), '');
console.log(`Built ${images.length} TRDs (${images.filter(i => i.root).length} root, ${images.filter(i => !i.catalogued).length} without curated descriptions) in ${output}`);
