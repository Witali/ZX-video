// Snapshot native banks at the emulated field boundary; present the newest
// complete snapshot on browser vsync without accumulating animation callbacks.
export function patchFrameClock(source) {
  const begin=source.indexOf('function ZX_Display ()');
  const end=source.indexOf('Object.assign(ZX_Display,',begin);
  if(begin<0||end<begin)throw new Error('Display frame-clock module changed');
  let display=source.slice(begin,end);
  function once(before,after){
    if(display.split(before).length!==2)throw new Error(`Frame-clock anchor changed: ${before.slice(0,70)}`);
    display=display.replace(before,after);
  }
  once('var _renderOnAnimationFrame = false;', `var _renderOnAnimationFrame = false;
    var _animationFrameId = null, _presentationGeneration = 0;
    var _pendingLayer = 0, _pendingBorderColor = null;

    function invalidatePresentation() {
        _presentationGeneration++;
        if (_animationFrameId !== null && typeof cancelAnimationFrame === 'function')
            cancelAnimationFrame(_animationFrameId);
        _animationFrameId = null;
        _pendingBorderColor = null;
        _borderChanged = true;
    }
    function queuePresentation(layer) {
        _pendingLayer = layer;
        if (_borderChanged) {
            var attrs = _port_fe_value & 7;
            _pendingBorderColor = ZX_Display.getColor(!_semicolors, attrs & 2, attrs & 4, attrs & 1);
            _borderChanged = false;
        }
        if (_animationFrameId !== null) return;
        var generation = _presentationGeneration;
        _animationFrameId = requestAnimationFrame(function () {
            if (generation !== _presentationGeneration) return;
            _animationFrameId = null;
            if (_threading === VAL_THREADING_SINGLE) _renderer.displayLayer(_pendingLayer);
            else _renderer.copyLayerToScreen(_pendingLayer);
            if (_pendingBorderColor) {
                var color = _pendingBorderColor;
                _pendingBorderColor = null;
                _renderer.drawBorder(color);
            }
        });
    }`);
  once('\tvar _deferredData = new Uint8Array(0x1B00);', '');
  once('\tvar _deferredDirty = new Uint8Array(0x1800);', '');
  once('function initRenderer() {', 'function initRenderer() {\n        invalidatePresentation();');
  once('function bind(canvases) {', 'function bind(canvases) {\n        invalidatePresentation();');
  const schedule=display.indexOf('\tfunction scheduleRedraw(');
  const redraw=display.indexOf('\tfunction beginRedraw()',schedule);
  const completed=display.indexOf('\tfunction endRedrawInMainThread(',redraw);
  if(schedule<0||redraw<schedule||completed<redraw)throw new Error('Frame snapshot routines changed');
  display=display.slice(0,schedule)+`    function scheduleRedraw(intrqVar, intrqActive) {
        // Exactly one completed-frame snapshot per emulated 50-Hz interrupt.
        // There is no independent wall timer or arbitrary 6.6-ms phase delay.
        if (intrqActive) beginRedraw(false);
    }
    function beginRedraw(forceImmediate) {
        var layer = +!!(_port_7ffd_value & 8);
        var data = layer ? _screen7Data : _screen5Data;
        var dirty = layer ? _screen7Dirty : _screen5Dirty;
        if (_renderOnAnimationFrame && !forceImmediate) {
            // Consume dirty data NOW, while the field is complete. CPU writes
            // after this boundary belong to the next field, not to this vsync.
            _renderer.drawData(layer, data, dirty, _flashInversion, _semicolors);
            queuePresentation(layer);
        } else if (_threading === VAL_THREADING_SINGLE) {
            endRedrawInMainThread(layer, data, dirty, _flashInversion, _semicolors);
        } else {
            _renderer.drawData(layer, data, dirty, _flashInversion, _semicolors);
            endRedrawInDedicatedThread(layer);
        }
    }

`+display.slice(completed);
  once('this.force_redraw = beginRedraw;', `this.force_redraw = function () {
        // Paused layout/renderer changes need an immediate redraw, independent
        // of field/vsync delivery. Invalidate any older queued presentation.
        invalidatePresentation();
        _borderChanged = true;
        beginRedraw(true);
    };`);
  once('_renderOnAnimationFrame = value.renderOnAnimationFrame;', `if (_renderOnAnimationFrame !== value.renderOnAnimationFrame) invalidatePresentation();
        _renderOnAnimationFrame = value.renderOnAnimationFrame;`);
  once('this.set_threading = function (value) {', 'this.set_threading = function (value) {\n        invalidatePresentation();');
  return source.slice(0,begin)+display+source.slice(end);
}
