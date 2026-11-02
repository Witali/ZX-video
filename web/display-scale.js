// Windowed mode uses two device pixels per source pixel, including Windows DPI
// and browser zoom. Fullscreen centers the active 256x192 raster at maximum
// size with at least two character cells of border on every side; the renderer
// fills every remaining pixel with the Spectrum border color.
export function keepPhysicalPixelScale(display) {
  let media, scheduled = 0, layoutKey;
  function update() {
    scheduled = 0;
    const ratio = window.devicePixelRatio || 1;
    display.style.setProperty('--spectrum-pixel-size', `${2 / ratio}px`);
    const fullscreen = document.fullscreenElement?.contains(display);
    const host = fullscreen ? document.fullscreenElement.getBoundingClientRect() : null;
    display.style.width = host ? `${host.width}px` : '';
    display.style.height = host ? `${host.height}px` : '';
    const width = host ? Math.round(host.width * ratio) : 576;
    const height = host ? Math.round(host.height * ratio) : 448;
    const scale = Math.min(width / 288, height / 224);
    const rasterWidth = Math.floor(256 * scale), rasterHeight = Math.floor(192 * scale);
    const viewport = host ? { x: Math.round((width - rasterWidth) / 2), y: Math.round((height - rasterHeight) / 2),
      width: rasterWidth, height: rasterHeight } : null;
    const layout = { width, height, viewport };
    const nextKey = JSON.stringify(layout);
    if (nextKey !== layoutKey) {
      layoutKey = nextKey;
      display.dispatchEvent(new CustomEvent('spectrum-layout', { detail: layout }));
    }
    display.style.transform = '';
    // A fractional device-pixel origin would blur an otherwise integer scale.
    const bounds = display.getBoundingClientRect();
    const dx = (Math.round(bounds.left * ratio) - bounds.left * ratio) / ratio;
    const dy = (Math.round(bounds.top * ratio) - bounds.top * ratio) / ratio;
    display.style.transform = `translate(${dx}px, ${dy}px)`;
    display.dataset.devicePixelRatio = String(ratio);
    media?.removeEventListener('change', schedule);
    media = window.matchMedia(`(resolution: ${ratio}dppx)`);
    media.addEventListener('change', schedule);
  }
  function schedule() {
    if (!scheduled) scheduled = window.requestAnimationFrame(update);
  }
  window.addEventListener('resize', schedule);
  window.addEventListener('scroll', schedule, { passive: true });
  document.addEventListener('fullscreenchange', schedule);
  new ResizeObserver(schedule).observe(display.parentElement);
  update();
}
