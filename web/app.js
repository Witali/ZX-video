import { SpectrumPlayer } from './emulator.js';
import { keepPhysicalPixelScale } from './display-scale.js';
import { LOWPASS_CUTOFFS } from './audio-filter.js';
const $ = id => document.getElementById(id);
const parameters = new URL(location.href).searchParams;
const cpuBackend = parameters.get('cpu') === 'wasm' ? 'wasm' : 'js';
const ayBackend = parameters.get('ay') === 'js' ? 'js' : 'wasm';
const player = new SpectrumPlayer($('display'), cpuBackend, ayBackend);
keepPhysicalPixelScale($('display'));
let images = [], selected, mounted, localBytes, busy = false, paused = false, readingDisk = false;
let visibilityPaused = false;
try {
  $('play-in-background').checked = localStorage.getItem('zx-video.play-in-background') !== 'false';
} catch { /* Background playback defaults on when storage is unavailable. */ }
player.setPlayInBackground($('play-in-background').checked);
function updateVisibilityPause() {
  const wasPaused = paused || visibilityPaused;
  visibilityPaused = !!mounted && document.hidden && !$('play-in-background').checked;
  const isPaused = paused || visibilityPaused;
  if (mounted && wasPaused !== isPaused) player.pause(isPaused);
  controls();
  if (visibilityPaused) status('Paused while the tab is hidden. Playback resumes when you return.');
  else if (wasPaused && !isPaused) status('Playback resumed.');
}
$('play-in-background').addEventListener('change', () => {
  player.setPlayInBackground($('play-in-background').checked);
  try { localStorage.setItem('zx-video.play-in-background', String($('play-in-background').checked)); }
  catch { /* The current choice still works without browser storage. */ }
  updateVisibilityPause();
});
player.onDiskActivity = active => { readingDisk = active; controls(); };
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
player.onRendererChanged = (actual, fallback) => {
  $('renderer-status').textContent = fallback
    ? 'WebGL unavailable. Canvas is active; playback is preserved.'
    : `${actual === 'webgl' ? 'WebGL' : 'Canvas'} · native 256×192 buffer · exact 2× physical pixels in windowed mode.`;
};
try {
  const saved = new URL(location.href).searchParams.get('renderer') || localStorage.getItem('zx-video.renderer');
  if (['canvas', 'webgl'].includes(saved)) $('renderer').value = saved;
} catch { /* Rendering still works when browser storage is unavailable. */ }
player.setRenderer($('renderer').value);
$('renderer').addEventListener('change', () => {
  const mode = $('renderer').value;
  player.setRenderer(mode);
  try { localStorage.setItem('zx-video.renderer', mode); } catch { /* Optional preference storage. */ }
  const url = new URL(location.href);
  url.searchParams.set('renderer', mode);
  history.replaceState(null, '', url);
});
try {
  const saved = Number(new URL(location.href).searchParams.get('lpf') || localStorage.getItem('zx-video.lowpass'));
  if (LOWPASS_CUTOFFS.includes(saved)) $('lowpass').value = String(saved);
} catch { /* The default filter remains available without browser storage. */ }
player.setLowpassCutoff(Number($('lowpass').value));
$('lowpass').addEventListener('change', () => {
  const cutoff = Number($('lowpass').value);
  player.setLowpassCutoff(cutoff);
  try { localStorage.setItem('zx-video.lowpass', String(cutoff)); } catch { /* Optional preference storage. */ }
  const url = new URL(location.href);
  url.searchParams.set('lpf', String(cutoff));
  history.replaceState(null, '', url);
});
function controls() {
  $('play').disabled = busy || !selected;
  $('swap').disabled = busy || !mounted || !selected;
  for (const id of ['pause', 'restart']) $(id).disabled = busy || !mounted;
  document.querySelectorAll('[data-key]').forEach(button => { button.disabled = busy || !mounted; });
  $('pause').textContent = paused ? 'Resume' : 'Pause';
  const effectivePaused = paused || visibilityPaused;
  const loading = busy || (readingDisk && !effectivePaused);
  $('machine-status').dataset.loading = String(loading);
  $('machine-state').textContent = busy ? 'Loading disk…' : effectivePaused ? 'Paused' : readingDisk ? 'Reading floppy…' : mounted ? 'Running · drive A' : 'Ready when you are';
}
function select(image, bytes) {
  selected = image; localBytes = bytes;
  $('disk-name').textContent = image.name;
  $('description').textContent = image.description;
  $('disk-path').textContent = bytes ? 'Local file · never uploaded' : image.path;
  $('disk-size').textContent = `${Math.round(image.bytes / 1024)} KiB · ${bytes ? 'Local disk' : image.catalogued ? 'Catalogued' : 'Uncatalogued experiment'}`;
  $('download').hidden = !!bytes;
  $('download').href = image.url || '#';
  $('download').download = image.name;
  $('guide').hidden = !!bytes;
  $('guide').href = `https://github.com/Witali/ZX-video/blob/main/${image.guide || 'TRD_CATALOG.md'}`;
  $('share').disabled = !!bytes;
  if (!bytes) {
    const url = new URL(location.href); url.searchParams.set('disk', image.path);
    history.replaceState(null, '', url);
  }
  controls(); render();
}
function render() {
  const query = $('search').value.trim().toLowerCase();
  const filtered = images.filter(image => ($('scope').value === 'all' || image.root)
    && ($('category').value === 'all' || image.category === $('category').value)
    && `${image.name} ${image.path} ${image.description}`.toLowerCase().includes(query));
  $('results').textContent = `${filtered.length} ${filtered.length === 1 ? 'disk' : 'disks'} to explore`;
  const scrollTop = $('disks').scrollTop;
  $('disks').replaceChildren();
  for (const image of filtered) {
    const button = document.createElement('button'); button.className = 'disk-card';
    button.setAttribute('aria-pressed', String(selected?.path === image.path && !localBytes));
    const name = document.createElement('span'); name.className = 'name'; name.textContent = image.name;
    const meta = document.createElement('span'); meta.className = 'meta';
    meta.textContent = `${image.category} · ${image.root ? 'Root disk' : 'Archive'}${image.catalogued ? '' : ' · Uncatalogued'}`;
    button.append(name, meta); button.title = image.path;
    button.addEventListener('click', () => select(image)); $('disks').append(button);
  }
  if (!filtered.length) { const empty = document.createElement('p'); empty.className = 'empty'; empty.textContent = 'No disks found. Try another search or choose all project disks.'; $('disks').append(empty); }
  $('disks').scrollTop = scrollTop;
}
async function load(boot, disk = selected, bytes = localBytes) {
  if (busy) return;
  busy = true; controls(); status(`Loading ${disk.name}…`);
  try {
    // Begin Web Audio during the click, before any network requests.
    await player.enableAudio();
    await player.initialize();
    if (!bytes) {
      const response = await fetch(disk.url);
      if (!response.ok) throw new Error(`Disk request failed (${response.status}).`);
      bytes = new Uint8Array(await response.arrayBuffer());
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes)), byte => byte.toString(16).padStart(2, '0')).join('');
      if (hash !== disk.sha256) throw new Error('Disk integrity check failed. Rebuild the site with materialized Git LFS images.');
    }
    if (![163840, 327680, 655360].includes(bytes.length) || bytes[0x8e7] !== 0x10) throw new Error('This is not a supported TRD disk image.');
    player.mount(bytes, boot);
    mounted = { ...disk, data: bytes }; paused = false; visibilityPaused = false; $('welcome').hidden = true;
    updateVisibilityPause();
    $('mounted').textContent = `Drive A: ${disk.name}`;
    status(boot ? 'Started in TR-DOS. Disk loading can take up to a minute. If a command prompt appears, press Enter to run the boot file.' : 'Disk inserted. RAM is preserved. Press the key requested by the program to continue.');
  } catch (error) { status(`Could not load disk: ${error.message}`, true); }
  finally { busy = false; controls(); }
}
$('play').addEventListener('click', () => load(true));
$('swap').addEventListener('click', () => load(false));
$('restart').addEventListener('click', () => load(true, mounted, mounted.data));
$('pause').addEventListener('click', () => { paused = !paused; player.pause(paused || visibilityPaused); controls(); status(paused ? 'Playback paused.' : 'Playback resumed.'); });
$('mute').addEventListener('click', () => { player.setMuted(!player.muted); $('mute').setAttribute('aria-pressed', String(player.muted)); $('mute').textContent = player.muted ? 'Unmute' : 'Mute'; });
$('fullscreen').addEventListener('click', async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else {
      await $('monitor').requestFullscreen();
      $('display').focus({ preventScroll: true });
    }
  } catch { status('Full screen is unavailable in this browser.'); }
});
for (const id of ['search', 'scope', 'category']) $(id).addEventListener(id === 'search' ? 'input' : 'change', render);
$('local').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  if (!/\.trd$/i.test(file.name) || ![163840,327680,655360].includes(file.size)) { status('Choose a valid 160, 320 or 640 KiB TRD image.', true); return; }
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (bytes[0x8e7] !== 0x10) { status('The file has no valid TR-DOS system sector.', true); return; }
  select({ name: file.name, bytes: file.size, description: 'Your local TRD disk. Press Play disk to boot, or insert it into the running machine.' }, bytes);
  event.target.value = '';
});
document.querySelectorAll('[data-key]').forEach(button => button.addEventListener('click', () => player.tap(button.dataset.key)));
$('share').addEventListener('click', async () => { try { await navigator.clipboard.writeText(location.href); status('Link copied. It opens this disk selected, ready to play.'); } catch { status('Copy the page address to share the selected disk.'); } });
document.addEventListener('visibilitychange', updateVisibilityPause);
try {
  const response = await fetch('catalog.json'); if (!response.ok) throw new Error(`HTTP ${response.status}`);
  ({ images } = await response.json()); $('total').textContent = String(images.length);
  const requested = new URL(location.href).searchParams.get('disk');
  const diskPath = requested === 'ZX-Music-Menu.trd' ? 'Expedition-33-Demo.trd' : requested;
  const first = images.find(image => image.path === diskPath) || images.find(image => image.path === 'Expedition-33-Demo.trd') || images[0];
  if (!first) throw new Error('The disk library is empty.');
  if (!first.root) $('scope').value = 'all';
  select(first);
  status(requested && first.path !== requested ? 'The linked disk was not found. Choose another disk from the library.' : 'Disk selected. Press Play disk to start the Spectrum.');
} catch (error) { $('disk-name').textContent = 'Library unavailable'; $('results').textContent = 'Could not load library'; status(`Cannot load the disk library: ${error.message}. Serve the built site over HTTP.`, true); }
