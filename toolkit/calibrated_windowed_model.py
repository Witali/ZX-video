"""Correct packet-stage placement and measured foreground costs in the model.

This changes host-side estimates only. Baseline elapsed costs include IRQ
and ULA effects and are frozen across trials; they are not exact predictions.
The first model and its completed experiment remain reproducible unchanged.
"""
from windowed_zx0_planner import FIELD, PERIOD, Model


class CalibratedModel(Model):
    def run(self, names, *, until_frame=None, stop_new=False):
        end = len(self.frames) if until_frame is None else min(len(self.frames), until_frame)
        while self.frame < end:
            i = self.frame
            if self.phase == 'draw':
                frame = self.frames[i]
                self.now = max(self.now, self.pub)+frame['draw_entry_tstates']+frame['draw_tstates']
                self.pub = max(i*PERIOD, ((self.now+FIELD-1)//FIELD)*FIELD)
                self.publications.append(self.pub)
                self.phase = 'prepare' if i+1 < len(self.frames) else 'idle'
                if self.phase == 'prepare' and not self.pending:
                    self.read_frame = i+1
                    self.read_after = 'prepare'
                    self.phase = 'read'
            elif self.phase == 'read':
                frame = self.frames[self.read_frame]
                target = frame['packet_end']
                if self.produced < target:
                    result = self.produce(names, stop_new=stop_new)
                    if isinstance(result, int):
                        return result
                    if result == 'idle':
                        raise AssertionError('packet acquisition deadlock')
                    continue
                self.reserves.append(dict(frame=self.read_frame, ready_bytes=self.produced-self.consumer))
                self.now += frame['copy_tstates']
                self.consumer = target
                # read_packet expands the metadata before returning. Waiting
                # until prepare would grant the producer fictitious idle time.
                self.now += frame['metadata_tstates']
                self.pending = True
                self.phase = self.read_after
            elif self.phase == 'prepare':
                frame = self.frames[i+1]
                self.now += frame['prepare_entry_tstates']+frame['prepare_tstates']
                self.pending = False
                if i+2 < len(self.frames) and self.now < self.pub:
                    self.read_frame = i+2
                    self.read_after = 'idle'
                    self.phase = 'read'
                else:
                    self.phase = 'idle'
            elif self.phase == 'idle':
                if self.now < self.pub:
                    result = self.produce(names, stop_new=stop_new)
                    if isinstance(result, int):
                        return result
                    if result == 'worked':
                        continue
                    self.now = self.pub
                self.frame += 1
                self.phase = 'draw'
            else:
                raise AssertionError('unknown model stage')
        return None


def frame_costs(reference, calibration, *, move_metadata=True, fit_transport=True, include_entries=True):
    """Use only baseline observations, never the held-out candidate's costs."""
    frames = []
    for row in reference:
        stages = row['stages']
        metadata = stages['metadata']['elapsed']-stages['metadata']['disk_service']
        prepare = stages['prepare']['elapsed']-stages['prepare']['disk_service']
        copy = calibration['copy']
        frames.append(dict(packet_end=row['raw_position']+row['packet_bytes'],
            draw_tstates=stages['draw']['elapsed']-stages['draw']['disk_service'],
            prepare_tstates=prepare+(0 if move_metadata else metadata),
            metadata_tstates=metadata if move_metadata else 0,
            copy_tstates=round(copy['tstates_per_byte']*row['packet_bytes']+copy['fixed_tstates'])
                if fit_transport else 16*row['packet_bytes']+800,
            draw_entry_tstates=calibration['draw_entry_tstates'] if include_entries else 0,
            prepare_entry_tstates=calibration['prepare_entry_tstates'] if include_entries else 0))
    return frames
