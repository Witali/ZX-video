"""Pareto selection of measured tokenizations under a total storage budget."""
from itertools import accumulate
from collections import Counter


def choose_cpu(options, capacity):
    """Minimize additive decoder T-states; Pareto-prune bytes/cycles after each block.

    Each option has name/bytes/tstates, bytes include its four-byte header.
    Future blocks have a precomputed minimum, so impossible states are skipped.
    Equal cycle totals prefer fewer bytes; equal complete choices retain order.
    """
    minimum = [min(row['bytes'] for row in group) for group in options]
    remaining = list(accumulate(reversed(minimum)))
    remaining = list(reversed(remaining))+[0]
    states = {0: (0, ())}
    for index, group in enumerate(options):
        candidates = {}
        for used, (ticks, choices) in states.items():
            for row in group:
                size = used+row['bytes']
                cost = ticks+row['tstates']
                if size+remaining[index+1] > capacity:
                    continue
                if size not in candidates or cost < candidates[size][0]:
                    candidates[size] = (cost, choices+(row['name'],))
        states = {}
        best = float('inf')
        for used, result in sorted(candidates.items()):
            if result[0] < best:
                states[used] = result
                best = result[0]
        if not states:
            raise ValueError('no choices fit capacity')
    used, (ticks, choices) = min(states.items(), key=lambda item: (item[1][0], item[0]))
    return dict(stream_bytes=used, decoder_tstates=ticks, selected_codecs=list(choices),
                selected_counts=dict(Counter(choices)), final_pareto_states=len(states))
