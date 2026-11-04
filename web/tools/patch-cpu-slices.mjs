// Keep the unchanged instruction interpreter in one loop until the host budget
// ends. Dispatch shared-device events at exactly the old CPU-step boundaries.
export function patchCpuSlices(source) {
  function once(text, before, after) {
    if (text.split(before).length !== 2) throw new Error(`CPU event-loop anchor changed: ${before.slice(0, 70)}`);
    return text.replace(before, after);
  }
  source = once(source, '    this.process = process;', `    this.process = process;

    var eventDeadline = 0, instructionStart = 0;
    this.run_until = function (limit, dispatch) {
        eventDeadline = 0;
        while (ts_cnt < limit) {
            instructionStart = ts_cnt;
            if (ts_cnt >= eventDeadline) eventDeadline = dispatch(ts_cnt);
            process();
        }
    };
    // An I/O command may schedule a device BEFORE the previous event deadline.
    // Finish this CPU step, then dispatch at the same boundary as step mode.
    this.reschedule_event = function (deadline) {
        if (deadline < eventDeadline) eventDeadline = deadline;
    };
    this.get_instruction_start = function () { return instructionStart; };`);
  const begin = source.indexOf('function ZX_Clock()');
  const end = source.indexOf('function TaskQueue(', begin);
  if (begin < 0 || end < begin) throw new Error('CPU event-loop clock module changed');
  let clock = source.slice(begin, end);
  clock = once(clock, 'var _cpu;', `var _cpu;
    var _slicing = false, _sliceMachineOrigin = 0;

    // Ports observe the START of the current CPU step, preserving the previous
    // core's bus contract even after operand cycles have accrued inside it.
    function currentTstates() {
        return _slicing ? _sliceMachineOrigin + _cpu.get_instruction_start() : _tstates;
    }
    function dispatchHardware(cpuTstates) {
        _tstates = _sliceMachineOrigin + cpuTstates;
        _taskQueue.process(_tstates);
        var next = _taskQueue.nextTask;
        // Subtract absolute timestamps before adding a relative CPU counter;
        // this retains fractional deadlines just above an integer T-state.
        return next ? next.tsEvent - _sliceMachineOrigin : Infinity;
    }
    function rescheduleEvent(task) {
        if (_slicing) _cpu.reschedule_event(task.tsEvent - _sliceMachineOrigin);
        return task;
    }`);
  const loopBegin = clock.indexOf('\t\twhile ((curTstates = _cpu.get_tstates()) < plannedTstates) {');
  const loopEnd = clock.indexOf('\n\t\t// корректировка счетчиков', loopBegin);
  if (loopBegin < 0 || loopEnd < loopBegin) throw new Error('CPU execution loop changed');
  const steppedLoop = clock.slice(loopBegin, loopEnd);
  clock = clock.slice(0, loopBegin) + `        if (_cpu.run_until && plannedTstates > 0) {
            _sliceMachineOrigin = _tstates;
            _slicing = true;
            try { _cpu.run_until(plannedTstates, dispatchHardware); }
            finally {
                // Also leave the old instruction-start timestamp on exceptions.
                lastTstates = _cpu.get_instruction_start();
                _tstates = _sliceMachineOrigin + lastTstates;
                _slicing = false;
            }
            curTstates = _cpu.get_tstates();
        } else {
${steppedLoop}
        }` + clock.slice(loopEnd);
  clock = once(clock, 'this.get_tstates = function () { return _tstates; }', 'this.get_tstates = currentTstates;');
  clock = once(clock, 'return _tstates / _tstatesPerMs;', 'return currentTstates() / _tstatesPerMs;');
  clock = once(clock, 'return _taskQueue.enqueue(_tstates, ms, func);',
    'return rescheduleEvent(_taskQueue.enqueue(currentTstates(), ms, func));');
  clock = once(clock, 'return _taskQueue.enqueue(_tstates, firstInterval, func, count, interval);',
    'return rescheduleEvent(_taskQueue.enqueue(currentTstates(), firstInterval, func, count, interval));');
  clock = once(clock, 'function updateTstatesPerMs() {', `function updateTstatesPerMs() {
        if (_slicing) _cpu.reschedule_event(_cpu.get_instruction_start());`);
  const frequency = clock.indexOf('function updateTstatesPerMs()');
  clock = clock.slice(0, frequency) + once(clock.slice(frequency), '_baseTstates = _tstates;', '_baseTstates = currentTstates();');
  source = source.slice(0, begin) + clock + source.slice(end);
  const queueBegin = source.indexOf('function TaskQueue(');
  const queueEnd = source.indexOf('// Upstream module: hardware/psg.js', queueBegin);
  if (queueBegin < 0 || queueEnd < queueBegin) throw new Error('CPU event queue module changed');
  let queue = source.slice(queueBegin, queueEnd);
  if (queue.split('end = (end + 1) % capacity;').length !== 3) throw new Error('CPU event queue insertion changed');
  queue = once(queue, 'var _tstatesPerMs = tstatesPerMs;', 'var _tstatesPerMs = tstatesPerMs;\n    this.nextTask = undefined;');
  queue = queue.replaceAll('end = (end + 1) % capacity;', 'end = (end + 1) % capacity;\n        this.nextTask = begin !== end ? queue[begin] : undefined;');
  queue = once(queue, 'begin %= capacity;', 'begin %= capacity;\n                this.nextTask = begin !== end ? queue[begin] : undefined;');
  return source.slice(0, queueBegin) + queue + source.slice(queueEnd);
}
