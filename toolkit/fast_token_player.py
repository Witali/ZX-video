"""Choose measured Fast ZX0 tokenizations within a disk-sector reserve.

Decoder/player instructions are unchanged. Re-encode selected short matches
as literals, then recheck every decoded byte and actual in-place placement.
"""
import struct

from benchmark_adaptive_zx0 import choose_cpu
from build_fap3_trd import sha
from fast_zx0_player import Builder as PreviousBuilder
from inplace_slot_input_z80 import MAX_OUTPUT
from inplace_zx0 import trace, layout
from probe_adaptive_block_codecs import geometry
import zx0_speed


def select(volume, *, margin_sectors=4):
    if margin_sectors < 0: raise ValueError('negative bootstrap margin')
    price = volume['disk_charge_tstates_per_byte']
    options = [[dict(name=name, bytes=o['bytes'], tstates=o['decoder_tstates']+price*o['bytes'])
        for name,o in row['variants'].items() if o['executed'] and 'reuses' not in o]
        for row in volume['blocks']]
    capacity = volume['capacity_bytes']-256*margin_sectors
    choice = choose_cpu(options, capacity)
    names = choice.pop('selected_codecs'); objective = choice.pop('decoder_tstates')
    ticks = sum(r['variants'][n]['decoder_tstates'] for r,n in zip(volume['blocks'],names,strict=True))
    original = sum(r['variants']['min0']['decoder_tstates'] for r in volume['blocks'])
    return dict(choice, names=names, decoder_tstates=ticks, delta_decoder_tstates=ticks-original,
        estimated_objective_tstates=objective, disk_charge_tstates_per_byte=price,
        bootstrap_margin_sectors=margin_sectors, capacity_bytes=capacity,
        delta_bytes=choice['stream_bytes']-volume['baseline_bytes'],
        geometry=geometry(choice['stream_bytes'],volume['video_start_sector']))


class Builder(PreviousBuilder):
    def __init__(self, *args, token_volume, token_selection, **kwargs):
        super().__init__(*args, **kwargs)
        self.token_volume = token_volume
        self.token_selection = token_selection

    def stream(self, start, end):
        key = start, end
        if key not in self.inplace_streams:
            video, _ = self.separated(start, end)
            rows = self.token_volume['blocks']; names = self.token_selection['names']
            if (len(video)+MAX_OUTPUT-1)//MAX_OUTPUT != len(rows) or len(names) != len(rows):
                raise ValueError('token selection has wrong block count')
            stream = bytearray(); blocks = []
            for index, lo in enumerate(range(0, len(video), MAX_OUTPUT)):
                raw = video[lo:lo+MAX_OUTPUT]; row = rows[index]; name = names[index]
                if sha(raw) != row['raw_sha256']: raise ValueError('token selection has wrong decoded bytes')
                baseline = self.compress(raw)
                if sha(baseline) != row['variants']['min0']['payload_sha256']:
                    raise ValueError('different baseline compressor output')
                payload = zx0_speed.rewrite(baseline, int(name.removeprefix('min')))
                if sha(payload) != row['variants'][name]['payload_sha256']:
                    raise ValueError('retokenized payload differs from measured candidate')
                exact, proof = trace(payload, limit=len(raw))
                plan = layout(len(payload), len(raw), proof['minimum_input_start'], len(stream))
                if exact != raw or not plan['sector_aligned_fits']:
                    raise ValueError('unsafe or inexact selected block')
                blocks.append(dict(raw_start=lo, raw_end=lo+len(raw), decoded_bytes=len(raw),
                    zx0_bytes=len(payload), sha256=sha(raw), inplace_proof=proof, inplace_layout=plan))
                stream += struct.pack('<HH',len(raw),len(payload))+payload
            if len(stream) != self.token_selection['stream_bytes']:
                raise ValueError('selected stream size differs')
            self.inplace_streams[key] = bytes(stream), blocks
        return self.inplace_streams[key]

    def ram(self, start, end, next_sector, remaining):
        sections, m = super().ram(start, end, next_sector, remaining)
        m['fast_token_selection'] = self.token_selection
        return sections, m
