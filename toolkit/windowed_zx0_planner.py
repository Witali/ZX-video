"""Bounded-horizon lossless ZX0 selection without alternative TRD builds.

The model carries slot ownership, input/decode progress, packet lookahead,
compact preparation and absolute six-field deadlines between windows.
Native block costs are exact for their measured demands; elapsed scheduling
is an estimate (sector rotations, ULA phase and variable demands are not
emulated). Only final real playback may validate publication deadlines.
"""
from bisect import bisect_right
from collections import Counter
from copy import copy
from itertools import product
import math

from benchmark_adaptive_zx0 import choose_cpu

FIELD = 70908
PERIOD = 6*FIELD


class Model:
    def __init__(self, frames, blocks, *, disk_tstates_per_byte=125, cpu_scale=(51, 50), slots=3):
        if not frames or not blocks or not 1 <= slots <= 3:
            raise ValueError('nonempty frames/blocks and one to three slots required')
        self.frames = frames; self.blocks = blocks; self.slots = slots
        self.ends = [0]
        for b in blocks: self.ends.append(self.ends[-1]+b['decoded_bytes'])
        if frames[-1]['packet_end'] != self.ends[-1]: raise ValueError('packet/block coverage differs')
        if any(f['packet_end'] <= (frames[i-1]['packet_end'] if i else 0)
               or min(f['draw_tstates'], f['prepare_tstates'], f['copy_tstates']) < 0 for i, f in enumerate(frames)):
            raise ValueError('invalid frame costs or packet order')
        num, den = cpu_scale
        if num < den or den <= 0 or disk_tstates_per_byte < 0: raise ValueError('invalid cost assumptions')
        self.jobs = []
        for b in blocks:
            jobs = {}
            for name, v in b['variants'].items():
                if not v.get('executed') or not v.get('all_offsets_fit') or 'reuses' in v: continue
                if sum(v['slice_tstates']) != v['decoder_tstates']: raise ValueError('invalid native decoder costs')
                outputs = list(range(256, b['decoded_bytes'], 256))+[b['decoded_bytes']]
                if len(outputs) != len(v['slice_tstates']): raise ValueError('requires measured 256-byte demands')
                # Average observed disk service plus conservative producer CPU.
                # A sector is atomic in this model; it may cross publication.
                count = (v['bytes']+255)//256
                load = math.ceil(v['bytes']*(disk_tstates_per_byte+7))
                steps = [(load//count+(i < load%count), 0) for i in range(count)]
                steps += [((t*num+den-1)//den, at) for t, at in zip(v['slice_tstates'], outputs, strict=True)]
                jobs[name] = steps
            if 'min0' not in jobs: raise ValueError('safe baseline required')
            self.jobs.append(jobs)
        self.now = 0; self.frame = 1; self.phase = 'draw'; self.pub = 0
        self.publications = [0]; self.reserves = []
        self.next_block = min(slots, len(blocks)); self.produced = self.ends[self.next_block]
        # Prime zero/native, one/compact, and packet two before starting clock.
        self.consumer = frames[min(2, len(frames)-1)]['packet_end']
        if self.consumer > self.produced: raise ValueError('priming packets exceed prefilled slots')
        self.pending = len(frames) > 2; self.read_frame = None; self.read_after = None
        self.active = None; self.step_index = 0; self.active_name = None

    def clone(self):
        other = copy(self)
        other.publications = list(self.publications); other.reserves = list(self.reserves)
        return other

    def produce(self, names, *, stop_new):
        """One atomic input/decode step; return a pending choice before mutation."""
        if self.active is None:
            if self.next_block == len(self.blocks): return 'idle'
            consumer_block = bisect_right(self.ends, self.consumer)-1
            if self.next_block-consumer_block >= self.slots: return 'idle'
            if stop_new: return self.next_block
            self.active = self.next_block; self.active_name = names[self.active]; self.step_index = 0
        steps = self.jobs[self.active][self.active_name]
        ticks, at = steps[self.step_index]; self.now += ticks
        if at: self.produced = self.ends[self.active]+at
        self.step_index += 1
        if self.step_index == len(steps):
            self.next_block += 1; self.active = None; self.active_name = None
        if not 0 <= self.produced-self.consumer <= self.slots*15872:
            raise AssertionError('reservoir ownership exceeded')
        return 'worked'

    def accept(self, index, name):
        if self.active is not None or index != self.next_block: raise ValueError('choice is already committed')
        if name not in self.jobs[index]: raise ValueError('unsafe token variant')
        self.active = index; self.active_name = name; self.step_index = 0

    def run(self, names, *, until_frame=None, stop_new=False):
        end = len(self.frames) if until_frame is None else min(len(self.frames), until_frame)
        while self.frame < end:
            i = self.frame
            if self.phase == 'draw':
                self.now = max(self.now, self.pub)+self.frames[i]['draw_tstates']
                self.pub = max(i*PERIOD, ((self.now+FIELD-1)//FIELD)*FIELD)
                self.publications.append(self.pub)
                self.phase = 'prepare' if i+1 < len(self.frames) else 'idle'
                if self.phase == 'prepare' and not self.pending:
                    self.read_frame = i+1; self.read_after = 'prepare'; self.phase = 'read'
            elif self.phase == 'read':
                target = self.frames[self.read_frame]['packet_end']
                if self.produced < target:
                    result = self.produce(names, stop_new=stop_new)
                    if isinstance(result, int): return result
                    if result == 'idle': raise AssertionError('packet acquisition deadlock')
                    continue
                self.reserves.append(dict(frame=self.read_frame, ready_bytes=self.produced-self.consumer))
                self.now += self.frames[self.read_frame]['copy_tstates']
                self.consumer = target; self.pending = True; self.phase = self.read_after
            elif self.phase == 'prepare':
                self.now += self.frames[i+1]['prepare_tstates']; self.pending = False
                # Match current optional packet acquisition: ready drawing wins
                # once this frame was published while reconstruction ran.
                if i+2 < len(self.frames) and self.now < self.pub:
                    self.read_frame = i+2; self.read_after = 'idle'; self.phase = 'read'
                else: self.phase = 'idle'
            elif self.phase == 'idle':
                if self.now < self.pub:
                    result = self.produce(names, stop_new=stop_new)
                    if isinstance(result, int): return result
                    if result == 'worked': continue
                    self.now = self.pub
                self.frame += 1; self.phase = 'draw'
            else: raise AssertionError('unknown model stage')
        return None

    def score(self, first_frame):
        deviations = [max(0, t-i*PERIOD) for i, t in enumerate(self.publications) if i >= first_frame]
        return (sum(deviations), sum(d > 0 for d in deviations), max(deviations, default=0))


def select(frames, blocks, capacity_bytes, *, window_frames=64, disk_tstates_per_byte=125):
    """Commit one producer block at a time; test at most two local choices.

    An additive CPU/byte allocation seeds future choices, reserving their
    space. Each local trial clones the current carried state and visits at
    most window_frames future frames. It never builds a disk or runs Fuse.
    The following block stays tentative until its actual admission point.
    """
    if window_frames < 2: raise ValueError('window must contain at least two frames')
    model = Model(frames, blocks, disk_tstates_per_byte=disk_tstates_per_byte)
    options = []
    for i, b in enumerate(blocks):
        group = [dict(name=n, bytes=b['variants'][n]['bytes'],
            tstates=b['variants'][n]['decoder_tstates']+disk_tstates_per_byte*b['variants'][n]['bytes'])
            for n in model.jobs[i] if i >= model.next_block or n == 'min0']
        options.append(group)
    seed = choose_cpu(options, capacity_bytes)
    names = seed['selected_codecs']; initial = list(names); used = seed['stream_bytes']
    trials = []; comparisons = 0; maximum_horizon = 0
    while (index := model.run(names, stop_new=True)) is not None:
        first = model.frame; horizon = min(len(frames), first+window_frames)
        indices = list(range(index, min(index+2, len(blocks))))
        previous = [names[j] for j in indices]
        base_bytes = used-sum(blocks[j]['variants'][names[j]]['bytes'] for j in indices)
        best = None; count = 0
        for pair in product(*(model.jobs[j] for j in indices)):
            size = base_bytes+sum(blocks[j]['variants'][n]['bytes'] for j, n in zip(indices, pair, strict=True))
            if size > capacity_bytes: continue
            candidate = list(names)
            for j, n in zip(indices, pair, strict=True): candidate[j] = n
            trial = model.clone(); trial.run(candidate, until_frame=horizon)
            # Prefer less storage when both local schedules are equally good.
            key = (*trial.score(first), size, pair)
            if best is None or key < best[0]: best = (key, candidate, size)
            count += 1
        if best is None: raise AssertionError('seeded feasible choice disappeared')
        key, names, used = best
        trials.append(dict(block=index, first_frame=first, end_frame_exclusive=horizon,
            previous=previous, selected=[names[j] for j in indices], estimated_score=list(key[:3]),
            comparisons=count, stream_bytes=used, remaining_bytes=capacity_bytes-used,
            start_tstates=model.now, consumer_bytes=model.consumer, produced_bytes=model.produced,
            producer_next_block=model.next_block, packet_pending=model.pending, stage=model.phase))
        comparisons += count; maximum_horizon = max(maximum_horizon, horizon-first)
        model.accept(index, names[index])
    if used != sum(b['variants'][n]['bytes'] for b, n in zip(blocks, names, strict=True)):
        raise AssertionError('disk-space accounting differs')
    return dict(names=names, selected_counts=dict(Counter(names)), stream_bytes=used,
        capacity_bytes=capacity_bytes, remaining_bytes=capacity_bytes-used,
        decoder_tstates=sum(b['variants'][n]['decoder_tstates'] for b, n in zip(blocks, names, strict=True)),
        seed_names=initial, window_frames=window_frames, maximum_evaluated_horizon_frames=maximum_horizon,
        local_comparisons=comparisons, decisions=trials, estimated_score=list(model.score(0)),
        estimated_publications=model.publications, estimated_reserves=model.reserves,
        estimated_only=True, actual_publication_verified=False,
        alternative_trds_built=0, alternative_fuse_runs=0,
        assumptions=dict(prefilled_slots=3, decoded_capacity_bytes=47616, packet_lookahead=True,
            disk_tstates_per_byte=disk_tstates_per_byte, producer_tstates_per_byte=7,
            decoder_elapsed_scale=[51, 50], decoder_demand_bytes=256,
            phase_dependent_contention_and_rotation_emulated=False))
