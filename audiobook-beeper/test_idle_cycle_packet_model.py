"""Word-only idle replacement, strict opt-in guards and full-bin closure."""
import unittest

import numpy as np

from idle_cycle_packet_model import (IDLE_CYCLE_WORD, IDLE_CYCLE_STATES,
    validate_idle_cycle_packet, apply_idle_cycle_packet)
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, on_time_tstates
from probe_feedback_packets import integral_table


def model():
    return dict(holds=list(ORDINARY_PENTAGON_HOLDS), beta=.5, extent=1.,
                pcm_origin=0, pcm_quantization_bias=512, idle_cycle_word=IDLE_CYCLE_WORD)


def table():
    words, nxt, _ = integral_table(64, 2, holds=ORDINARY_PENTAGON_HOLDS,
                                 beta=.5, extent=1., pcm_origin=0)
    return words, nxt


def closed_states(nxt):
    states = {16}
    while True:
        expanded = states | set(map(int, nxt[:, sorted(states)].ravel()))
        if expanded == states:
            return sorted(states)
        states = expanded


class IdleCyclePacketTests(unittest.TestCase):
    def test_absent_option_preserves_identity_without_validation(self):
        words, nxt = table()
        before, next_before = words.copy(), nxt.copy()
        # Prior experiments remain independent when this flag is absent.
        for config in (None, {}, dict(holds=[1]),
                       dict(neutral_packet_word=IDLE_CYCLE_WORD, neutral_packet_successor=16)):
            with self.subTest(config=config):
                result, next_result = apply_idle_cycle_packet(words, nxt, config)
                self.assertIs(result, words)
                self.assertIs(next_result, nxt)
                self.assertIsNone(validate_idle_cycle_packet(config))
        marker = object()
        self.assertEqual(apply_idle_cycle_packet(marker, marker, None), (marker, marker))
        np.testing.assert_array_equal(words, before)
        np.testing.assert_array_equal(nxt, next_before)

    def test_immutable_inputs_exact_two_cell_scope_and_preserved_cycle(self):
        words, nxt = table()
        before, next_before = words.copy(), nxt.copy()
        words.flags.writeable = False
        nxt.flags.writeable = False
        result, next_result = apply_idle_cycle_packet(words, nxt, model())
        self.assertIsNot(result, words)
        self.assertFalse(np.shares_memory(result, words))
        self.assertIs(next_result, nxt)
        self.assertTrue(result.flags.writeable)
        expected = before.copy()
        expected[32, 16:18] = IDLE_CYCLE_WORD
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(np.argwhere(result != before).tolist(), [[32, 16], [32, 17]])
        self.assertEqual(int(np.count_nonzero(result == before)), 2046)
        np.testing.assert_array_equal(words, before)
        np.testing.assert_array_equal(next_result, next_before)
        self.assertEqual(IDLE_CYCLE_STATES, (16, 17))
        state = 16
        for step in range(128):
            self.assertEqual(state, (16, 17)[step % 2])
            self.assertEqual(int(result[32, state]), IDLE_CYCLE_WORD)
            state = int(next_result[32, state])
        # The identical packet is emitted while the feedback state still cycles.
        self.assertEqual(tuple(map(int, nxt[32, 16:18])), (17, 16))

    def test_fixed_literal_duty_and_strict_model_guards(self):
        valid = model()
        self.assertEqual(validate_idle_cycle_packet(valid), 22189)
        self.assertEqual(on_time_tstates(IDLE_CYCLE_WORD), 225)
        self.assertEqual(sum(ORDINARY_PENTAGON_HOLDS), 449)
        self.assertLessEqual(abs(on_time_tstates(IDLE_CYCLE_WORD) - 449 / 2), .5)
        invalid = [
            dict(idle_cycle_word=value) for value in
            (None, True, False, float(IDLE_CYCLE_WORD), np.int64(IDLE_CYCLE_WORD),
             '0x56AD', -1, 65536, 0, 65535, 0xA952)
        ] + [
            dict(family=value) for value in ('sigma_delta2', None)
        ] + [
            dict(pcm_bins=value) for value in (128, 64., True)
        ] + [
            dict(pcm_quantization_bias=value) for value in (0, 512., True, np.int64(512))
        ] + [
            dict(pcm_origin=value) for value in (.5, False, np.int64(0))
        ] + [
            dict(extent=value) for value in (.5, True)
        ] + [
            dict(beta=value) for value in (.25, False)
        ] + [
            dict(holds=value) for value in (None, [], [1] * 16,
                list(ORDINARY_PENTAGON_HOLDS[:-1]) + [17])
        ] + [
            dict(q_clip=value) for value in (None, (0, 14), (0., 15.), (False, 15))
        ] + [
            dict(neutral_packet_word=value) for value in (None, IDLE_CYCLE_WORD)
        ] + [
            dict(neutral_packet_successor=value) for value in (None, 16)
        ]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_idle_cycle_packet(dict(valid, **changes))
        wrong = valid.copy()
        wrong['holds'] = list(ORDINARY_PENTAGON_HOLDS)
        wrong['holds'][0] += 1
        wrong['holds'][1] -= 1
        with self.assertRaises(ValueError):
            validate_idle_cycle_packet(wrong)
        for required in ('pcm_quantization_bias', 'pcm_origin', 'holds'):
            partial = valid.copy()
            partial.pop(required)
            with self.subTest(missing=required), self.assertRaises(ValueError):
                validate_idle_cycle_packet(partial)

    def test_malformed_tables_rejected_without_mutation(self):
        words, nxt = table()
        before, next_before = words.copy(), nxt.copy()
        variants = ((words[:63], nxt), (words, nxt[:63]),
                    (words.astype(float), nxt), (words, nxt.astype(float)),
                    (np.full((64, 32), -1), nxt), (np.full((64, 32), 65536), nxt),
                    (words, np.full((64, 32), -1)), (words, np.full((64, 32), 32)),
                    (words.astype(bool), nxt))
        for first, second in variants:
            with self.subTest(dtype=(first.dtype, second.dtype)), self.assertRaises(ValueError):
                apply_idle_cycle_packet(first, second, model())
        np.testing.assert_array_equal(words, before)
        np.testing.assert_array_equal(nxt, next_before)

    def test_modified_cycle_and_stripped_prior_reset_are_rejected(self):
        words, nxt = table()
        for state, successor in ((16, 16), (17, 17), (16, 18), (17, 15)):
            changed = nxt.copy()
            changed[32, state] = successor
            before = changed.copy()
            with self.subTest(state=state, successor=successor), self.assertRaises(ValueError):
                apply_idle_cycle_packet(words, changed, model())
            np.testing.assert_array_equal(changed, before)
        reset = nxt.copy()
        reset[32, :] = 16
        with self.assertRaises(ValueError):
            apply_idle_cycle_packet(words, reset, model())

    def test_dictionary_uses_every_bin_of_identical_closed_state_graph(self):
        words, nxt = table()
        changed, changed_next = apply_idle_cycle_packet(words, nxt, model())
        original_states = closed_states(nxt)
        changed_states = closed_states(changed_next)
        self.assertEqual(changed_states, original_states)
        self.assertEqual(len(changed_states), 18)
        original_used = words[:, original_states]
        self.assertEqual(len(np.unique(original_used >> 8)), 138)
        self.assertEqual(len(np.unique(original_used & 255)), 96)
        # Catalogue all bins, including values never present in a song fixture.
        used = changed[:, changed_states]
        self.assertEqual(used.shape, (64, 18))
        self.assertIn(IDLE_CYCLE_WORD >> 8, set(map(int, (used >> 8).ravel())))
        self.assertIn(IDLE_CYCLE_WORD & 255, set(map(int, (used & 255).ravel())))
        self.assertEqual(len(np.unique(used >> 8)), 138)
        self.assertEqual(len(np.unique(used & 255)), 97)
        for state in changed_states:
            self.assertTrue(set(map(int, changed_next[:, state])).issubset(changed_states))


if __name__ == '__main__':
    unittest.main()
