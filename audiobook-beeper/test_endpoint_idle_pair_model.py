"""Exact endpoint constraints, unchanged graph and source-free pair ranking."""
from fractions import Fraction as F
import unittest

import numpy as np

from build_pdm import CPU_CLOCK
from endpoint_idle_pair_model import (ENDPOINT_IDLE_PAIR_WORDS, ENDPOINT_IDLE_PAIR_STATES,
    ENDPOINT_EPSILON, derive_idle_endpoint, validate_endpoint_idle_pair,
    apply_endpoint_idle_pair, select_endpoint_idle_pair)
from ima_waveform_encoder import WaveformModel
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, PHYSICAL_CPU_HZ, on_time_tstates
from probe_feedback_packets import integral_table


def model():
    return dict(holds=list(ORDINARY_PENTAGON_HOLDS), beta=.5, extent=1., pcm_origin=0,
                pcm_quantization_bias=512, endpoint_idle_pair_words=list(ENDPOINT_IDLE_PAIR_WORDS))


def table():
    words, nxt, _ = integral_table(64, 2, holds=ORDINARY_PENTAGON_HOLDS,
                                 beta=.5, extent=1., pcm_origin=0)
    return words, nxt


def closed_form_endpoint(word, state):
    """Independent exact sum of the geometric recent recurrence.

    q before each pulse is 16/449 times the preceding signed hold area.
    Dividing q by this pulse's weight reduces to preceding_area/hold.
    This avoids the primary replay's iterative q/recent propagation.
    """
    previous_area = F(0)
    recent = F(-1 if state == 16 else 1, 2 * 65536)
    for slot, (shift, hold) in enumerate(zip(range(15, -1, -1), ORDINARY_PENTAGON_HOLDS)):
        bit = (word >> shift) & 1
        contribution = F(1, 2) + previous_area / hold - bit
        recent += contribution / 2**(15-slot)
        previous_area += hold * (F(1, 2) - bit)
    q = 16 * previous_area / 449
    epsilon = F(1, 10**12)
    qvalue, rvalue = 8*q + F(17, 2) + epsilon, recent + 1 + epsilon
    qcode = min(15, max(0, qvalue.numerator // qvalue.denominator))
    rcode = min(1, max(0, rvalue.numerator // rvalue.denominator))
    return q, recent, 2*qcode + rcode


def signed(word):
    return np.array([1. if word & (1 << shift) else -1. for shift in range(15, -1, -1)])


def direct_pair_metrics(pair):
    """Independent individual-pulse filter propagation, without packet()."""
    analog = WaveformModel()
    holds = np.tile(np.asarray(ORDINARY_PENTAGON_HOLDS), 2) * CPU_CLOCK / PHYSICAL_CPU_HZ
    bits = np.r_[signed(pair[0]), signed(pair[1])]
    periodic, drive = np.eye(6), np.zeros(6)
    for hold, bit in zip(holds, bits):
        e, u = analog.transition(hold)
        periodic, drive = e @ periodic, e @ drive + u * bit
    initial = np.linalg.solve(np.eye(6) - periodic, drive)
    state, output = initial.copy(), []
    for hold, bit in zip(holds, bits):
        e, u = analog.transition(hold / 2)
        output.append(analog.c @ (e @ state + u * bit))
        e, u = analog.transition(hold)
        state = e @ state + u * bit
    output = np.asarray(output)
    weights = np.tile(np.asarray(ORDINARY_PENTAGON_HOLDS), 2) / 898
    mean = weights @ output
    second_moment = weights @ (output * output)
    variance = weights @ ((output - mean) ** 2)
    return initial, state, output, float(mean), float(second_moment), float(variance)


class EndpointIdlePairTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection, cls.arrays = select_endpoint_idle_pair()

    def test_absent_option_is_identity_and_prior_flags_are_independent(self):
        words, nxt = table()
        for config in (None, {}, dict(holds=[1]), dict(idle_pair_words=[0x569A, 0x56AD]),
                       dict(idle_cycle_word=0x56AD), dict(neutral_packet_successor=16)):
            with self.subTest(config=config):
                result, successor = apply_endpoint_idle_pair(words, nxt, config)
                self.assertIs(result, words)
                self.assertIs(successor, nxt)
                self.assertIsNone(validate_endpoint_idle_pair(config))

    def test_immutable_exact_two_cell_scope_and_preserved_original_cycle(self):
        words, nxt = table()
        before, next_before = words.copy(), nxt.copy()
        words.flags.writeable = nxt.flags.writeable = False
        result, successor = apply_endpoint_idle_pair(words, nxt, model())
        self.assertIsNot(result, words)
        self.assertFalse(np.shares_memory(result, words))
        self.assertIs(successor, nxt)
        expected = before.copy()
        expected[32, 16:18] = ENDPOINT_IDLE_PAIR_WORDS
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(np.argwhere(result != before).tolist(), [[32, 16], [32, 17]])
        self.assertEqual(int(np.count_nonzero(result == before)), 2046)
        np.testing.assert_array_equal(words, before)
        np.testing.assert_array_equal(nxt, next_before)
        state = 16
        for step in range(256):
            self.assertEqual(int(result[32, state]), ENDPOINT_IDLE_PAIR_WORDS[step % 2])
            state = int(successor[32, state])

    def test_exact_endpoints_and_non_equivalence_to_individual_bit_rule(self):
        self.assertEqual(ENDPOINT_IDLE_PAIR_WORDS, (0x670D, 0x969C))
        self.assertEqual(ENDPOINT_EPSILON, F(1, 10**12))
        self.assertEqual(ENDPOINT_IDLE_PAIR_STATES, (16, 17))
        for word, state, expected in ((0x6AD5, 16, 17), (0x952A, 17, 16),
                                     (0x56AD, 16, 17), (0x56AD, 17, 17),
                                     (0x569A, 16, 17), (0x670D, 16, 17), (0x969C, 17, 16)):
            result = derive_idle_endpoint(word, state)
            q, recent, successor = closed_form_endpoint(word, state)
            self.assertEqual((result['q'], result['recent'], result['successor']), (q, recent, successor))
            self.assertEqual(successor, expected)
        for word, state in zip(ENDPOINT_IDLE_PAIR_WORDS, ENDPOINT_IDLE_PAIR_STATES):
            # Endpoint consistency does not silently become greedy-rule equivalence.
            self.assertTrue(derive_idle_endpoint(word, state)['greedy_bit_rule_mismatch_slots'])
        self.assertEqual(tuple(map(on_time_tstates, ENDPOINT_IDLE_PAIR_WORDS)), (224, 225))
        self.assertEqual(sum(map(on_time_tstates, ENDPOINT_IDLE_PAIR_WORDS)) / 898, .5)
        for word, state in ((True, 16), (-1, 16), (65536, 16), (0x670D, True), (0x670D, 15)):
            with self.subTest(word=word, state=state), self.assertRaises(ValueError):
                derive_idle_endpoint(word, state)

    def test_independent_exact_filter_for_every_duty_candidate(self):
        arrays = self.arrays
        for name, state, expected in (('duty224', 16, 17), ('duty225', 17, 16)):
            all_words = arrays['all_' + name + '_words']
            independent = [closed_form_endpoint(int(word), state) for word in all_words]
            np.testing.assert_array_equal(arrays[name + '_derived_successors'], [item[2] for item in independent])
            self.assertEqual(arrays[name + '_endpoint_recent_exact'].tolist(), [str(item[1]) for item in independent])
            kept = [int(word) for word, result in zip(all_words, independent) if result[2] == expected]
            self.assertEqual(len(all_words), 424)
            self.assertEqual(len(kept), 238)
            np.testing.assert_array_equal(arrays['first_words' if state == 16 else 'second_words'], kept)
        self.assertGreater(self.selection['endpoint_boundary_minimum_absolute_distance_float'], 1e-6)

    def test_complete_source_free_ranking_and_exact_complement_swap_symmetry(self):
        report, arrays = self.selection, self.arrays
        self.assertFalse(report['source_audio_opened'])
        self.assertEqual(report['pairs_enumerated'], 56644)
        self.assertEqual(report['complement_swap_fixed_pairs'], 238)
        self.assertEqual(report['complement_swap_orbits'], 28441)
        self.assertEqual(tuple(report['selected_words']), ENDPOINT_IDLE_PAIR_WORDS)
        self.assertEqual(report['derived_successors'], [17, 16])
        first, second = arrays['first_words'], arrays['second_words']
        self.assertEqual(set(map(int, second)), {65535-int(word) for word in first})
        rows, columns = np.searchsorted(first, 65535-second), np.searchsorted(second, 65535-first)
        for key in ('variance', 'second_moment'):
            values = arrays[key]
            np.testing.assert_array_equal(values, values[rows[None, :], columns[:, None]])
        means = arrays['midpoint_weighted_mean']
        np.testing.assert_array_equal(means, -means[rows[None, :], columns[:, None]])
        self.assertEqual(report['top_candidates'][1]['words'], [0x6963, 0x98F2])
        self.assertEqual(report['top_candidates'][0]['variance'], report['top_candidates'][1]['variance'])
        self.assertLess(report['solve_condition'], 20)
        self.assertLess(report['solve_residual_max'], 1e-14)

    def test_independent_32_pulse_propagation_matches_analytic_scores(self):
        pairs = (ENDPOINT_IDLE_PAIR_WORDS, (0x6963, 0x98F2),
                 (int(self.arrays['first_words'][0]), int(self.arrays['second_words'][-1])))
        for pair in pairs:
            initial, final, output, mean, second_moment, variance = direct_pair_metrics(pair)
            np.testing.assert_allclose(final, initial, atol=2e-13, rtol=0)
            row = int(np.searchsorted(self.arrays['first_words'], pair[0]))
            column = int(np.searchsorted(self.arrays['second_words'], pair[1]))
            self.assertAlmostEqual(mean, self.arrays['midpoint_weighted_mean'][row, column], places=13)
            self.assertAlmostEqual(second_moment, self.arrays['second_moment'][row, column], places=13)
            self.assertAlmostEqual(variance, self.arrays['variance'][row, column], places=13)
            predicted = (self.arrays['steady_word16_basis'] @ signed(pair[0]) +
                         self.arrays['steady_word17_basis'] @ signed(pair[1]))
            np.testing.assert_allclose(initial, predicted, atol=2e-13, rtol=0)

    def test_strict_pair_model_and_mixed_flag_guards(self):
        valid = model()
        self.assertEqual(validate_endpoint_idle_pair(valid), ENDPOINT_IDLE_PAIR_WORDS)
        valid['endpoint_idle_pair_words'] = ENDPOINT_IDLE_PAIR_WORDS
        self.assertEqual(validate_endpoint_idle_pair(valid), ENDPOINT_IDLE_PAIR_WORDS)
        invalid = [dict(endpoint_idle_pair_words=value) for value in (
            None, '670D,969C', [], [0x670D], [0x670D, 0x969C, 0], np.array(ENDPOINT_IDLE_PAIR_WORDS),
            [True, 0x969C], [float(0x670D), 0x969C], [np.int64(0x670D), 0x969C],
            [-1, 0x969C], [0x670D, 65536], [0, 65535], [0x969C, 0x670D],
            [0x6963, 0x98F2], [0x569A, 0x56AD])]
        invalid += [dict(**{key: value}) for key, value in (
            ('idle_pair_words', None), ('idle_cycle_word', 0x56AD), ('neutral_packet_word', None),
            ('neutral_packet_successor', 16), ('family', None), ('family', 'sigma_delta2'),
            ('pcm_bins', 128), ('pcm_bins', 64.), ('pcm_quantization_bias', 0),
            ('pcm_quantization_bias', 512.), ('pcm_origin', .5), ('pcm_origin', False),
            ('extent', .5), ('extent', True), ('beta', .25), ('q_clip', (0, 14)),
            ('q_clip', (0., 15.)), ('q_clip', None), ('holds', None), ('holds', [1] * 16))]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_endpoint_idle_pair(dict(valid, **changes))
        changed = model()
        changed['holds'][0] += 1
        changed['holds'][1] -= 1
        with self.assertRaises(ValueError):
            validate_endpoint_idle_pair(changed)
        for required in ('pcm_quantization_bias', 'pcm_origin', 'holds'):
            partial = model()
            partial.pop(required)
            with self.assertRaises(ValueError):
                validate_endpoint_idle_pair(partial)

    def test_array_and_original_cycle_guards_preserve_inputs(self):
        words, nxt = table()
        for first, second in ((words[:63], nxt), (words, nxt[:63]), (words.astype(float), nxt),
                              (words, nxt.astype(float)), (np.full((64, 32), 65536), nxt),
                              (np.full((64, 32), -1), nxt), (words, np.full((64, 32), 32)),
                              (words, np.full((64, 32), -1))):
            with self.assertRaises(ValueError):
                apply_endpoint_idle_pair(first, second, model())
        for state, target in ((16, 16), (17, 17), (16, 18), (17, 15)):
            changed = nxt.copy()
            changed[32, state] = target
            before = changed.copy()
            with self.assertRaises(ValueError):
                apply_endpoint_idle_pair(words, changed, model())
            np.testing.assert_array_equal(changed, before)

    def test_all_bin_closed_dictionary_footprint(self):
        words, nxt = table()
        result, successor = apply_endpoint_idle_pair(words, nxt, model())
        states = {16}
        while True:
            expanded = states | set(map(int, nxt[:, sorted(states)].ravel()))
            if expanded == states:
                break
            states = expanded
        self.assertEqual(len(states), 18)
        self.assertIs(successor, nxt)
        old, new = words[:, sorted(states)], result[:, sorted(states)]
        self.assertEqual((len(np.unique(old >> 8)), len(np.unique(old & 255))), (138, 96))
        self.assertEqual((len(np.unique(new >> 8)), len(np.unique(new & 255))), (139, 98))
        self.assertEqual((139-138)*42 + (98-96)*64, 170)


if __name__ == '__main__':
    unittest.main()
