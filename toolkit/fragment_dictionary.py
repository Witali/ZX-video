"""Exact row-word dictionary training and fixed-width payload encoding.

Eight low index bytes precede packed upper index bits (MSB first); literal
two-byte words for reserved-index escapes follow in row order. A tile costs
`bits + 2*escapes` bytes. Dictionary words retain source little-endian order.
"""
import numpy as np

from probe_motion_residual_order import field_order


def train(states, selected, bits):
    if bits not in range(8, 13) or selected.shape != (len(states), 192):
        raise ValueError('invalid width/selection')
    order = field_order(8).reshape(192, 20)[:, :16]
    data = states[:, order][selected].astype(np.uint16)
    words = data[:, ::2]+256*data[:, 1::2]
    # Only tiles not already represented by fill/one-row/two-row modes.
    distinct = 1+np.count_nonzero(np.diff(np.sort(words, axis=1), axis=1), axis=1)
    histogram = np.bincount(words[distinct > 2].ravel(), minlength=65536)
    escape = (1 << bits)-1
    ranking = np.argsort(-histogram, kind='stable')[:escape]
    blob = b''.join(int(word).to_bytes(2, 'little') for word in ranking)
    lookup = np.full(65536, escape, dtype=np.uint16)
    lookup[ranking] = np.arange(escape, dtype=np.uint16)
    return bits, blob, lookup


def pack(fragment, dictionary):
    bits, _, lookup = dictionary
    if len(fragment) != 16 or bits not in range(8, 13):
        raise ValueError('invalid fragment/width')
    words = [int.from_bytes(fragment[i:i+2], 'little') for i in range(0, 16, 2)]
    indices = [int(lookup[w]) for w in words]
    upper = 0
    for index in indices:
        upper = (upper << (bits-8)) | (index >> 8)
    literals = b''.join(word.to_bytes(2, 'little') for word, index in zip(words, indices)
                        if index == (1 << bits)-1)
    return bytes(index & 255 for index in indices)+upper.to_bytes(bits-8, 'big')+literals
