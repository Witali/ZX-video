// Two device pixels per source pixel, including Windows DPI and browser zoom.
export function keepPhysicalPixelScale(display) {
  let media, scheduled = 0;
  function update() {
    scheduled = 0;
    const ratio = window.devicePixelRatio || 1;
    display.style.setProperty('--spectrum-pixel-size', `${2 / ratio}px`);
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
