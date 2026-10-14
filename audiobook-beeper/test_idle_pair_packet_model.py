"""Source-free pair selection, periodic filter proof and exact table scope."""
import unittest

import numpy as np

from build_pdm import CPU_CLOCK
from ima_waveform_encoder import WaveformModel
from idle_pair_packet_model import (IDLE_PAIR_WORDS, IDLE_PAIR_STATES,
    apply_idle_pair_packet, validate_idle_pair_packet, select_idle_pair)
from neutral_packet_model import ORDINARY_PENTAGON_HOLDS, PHYSICAL_CPU_HZ, on_time_tstates
from probe_feedback_packets import integral_table


def model():
    return dict(holds=list(ORDINARY_PENTAGON_HOLDS), beta=.5, extent=1., pcm_origin=0,
                pcm_quantization_bias=512, idle_pair_words=list(IDLE_PAIR_WORDS))


def table():
    words, nxt, _ = integral_table(64, 2, holds=ORDINARY_PENTAGON_HOLDS,
                                 beta=.5, extent=1., pcm_origin=0)
    return words, nxt


def signed(word):
    return np.asarray([1. if word & (1 << shift) else -1. for shift in range(15, -1, -1)])


def direct_pair_metrics(pair):
    """Compose 32 individual transitions, independent of packet matrices."""
    analog = WaveformModel()
    holds = np.tile(np.asarray(ORDINARY_PENTAGON_HOLDS), 2) * CPU_CLOCK / PHYSICAL_CPU_HZ
    bits = np.r_[signed(pair[0]), signed(pair[1])]
    periodic, drive = np.eye(6), np.zeros(6)
    for hold, bit in zip(holds, bits):
        e, u = analog.transition(hold)
        periodic = e @ periodic
        drive = e @ drive + u * bit
    initial = np.linalg.solve(np.eye(6) - periodic, drive)
    state = initial.copy()
    observed = []
    for hold, bit in zip(holds, bits):
        e, u = analog.transition(hold / 2)
        observed.append(analog.c @ (e @ state + u * bit))
        e, u = analog.transition(hold)
        state = e @ state + u * bit
    output = np.asarray(observed)
    weights = np.tile(np.asarray(ORDINARY_PENTAGON_HOLDS), 2) / 898
    mean = weights @ output
    second_moment = weights @ (output * output)
    variance = weights @ ((output - mean) ** 2)
    return initial, state, output, float(mean), float(second_moment), float(variance)


class IdlePairPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection, cls.arrays = select_idle_pair()

    def test_absent_option_is_identity_without_scope_validation(self):
        words, nxt = table()
        for config in (None, {}, dict(holds=[1]), dict(idle_cycle_word=0x56AD),
                       dict(neutral_packet_word=0x56AD, neutral_packet_successor=16)):
            with self.subTest(config=config):
                result, successor = apply_idle_pair_packet(words, nxt, config)
                self.assertIs(result, words)
                self.assertIs(successor, nxt)
                self.assertIsNone(validate_idle_pair_packet(config))

    def test_immutable_inputs_two_word_scope_and_original_cycle(self):
        words, nxt = table()
        before, next_before = words.copy(), nxt.copy()
        words.flags.writeable = nxt.flags.writeable = False
        result, successor = apply_idle_pair_packet(words, nxt, model())
        self.assertIsNot(result, words)
        self.assertFalse(np.shares_memory(result, words))
        self.assertIs(successor, nxt)
        expected = before.copy()
        expected[32, 16:18] = IDLE_PAIR_WORDS
        np.testing.assert_array_equal(result, expected)
        self.assertEqual(np.argwhere(result != before).tolist(), [[32, 16], [32, 17]])
        self.assertEqual(int(np.count_nonzero(result == before)), 2046)
        np.testing.assert_array_equal(words, before)
        np.testing.assert_array_equal(successor, next_before)
        self.assertEqual(IDLE_PAIR_STATES, (16, 17))
        self.assertEqual(tuple(map(int, successor[32, 16:18])), (17, 16))
        state = 16
        for step in range(256):
            self.assertEqual(int(result[32, state]), IDLE_PAIR_WORDS[step % 2])
            state = int(successor[32, state])

    def test_ordered_duty_exact_half_area_and_frozen_pair(self):
        self.assertEqual(IDLE_PAIR_WORDS, (22170, 22189))
        self.assertEqual(tuple(map(on_time_tstates, IDLE_PAIR_WORDS)), (224, 225))
        self.assertEqual(sum(map(on_time_tstates, IDLE_PAIR_WORDS)), 449)
        self.assertEqual(sum(map(on_time_tstates, IDLE_PAIR_WORDS)) / 898, .5)
        valid = model()
        self.assertEqual(validate_idle_pair_packet(valid), IDLE_PAIR_WORDS)
        valid['idle_pair_words'] = IDLE_PAIR_WORDS
        self.assertEqual(validate_idle_pair_packet(valid), IDLE_PAIR_WORDS)

    def test_invalid_pair_types_old_flags_and_model_scope(self):
        valid = model()
        invalid = [dict(idle_pair_words=value) for value in
            (None, '569A,56AD', [], [22170], [22170, 22189, 0], np.array(IDLE_PAIR_WORDS),
             [True, 22189], [22170., 22189], [np.int64(22170), 22189], [-1, 22189],
             [22170, 65536], [0, 65535], [22189, 22170], [0xA952, 0xA965])]
        invalid += [dict(**{key: value}) for key, value in (
            ('idle_cycle_word', None), ('idle_cycle_word', 0x56AD),
            ('neutral_packet_word', None), ('neutral_packet_successor', 16),
            ('family', None), ('family', 'sigma_delta2'), ('pcm_bins', 128), ('pcm_bins', 64.),
            ('pcm_quantization_bias', 0), ('pcm_quantization_bias', 512.),
            ('pcm_origin', .5), ('pcm_origin', False), ('extent', .5), ('extent', True),
            ('beta', .25), ('q_clip', (0, 14)), ('q_clip', (0., 15.)), ('q_clip', None),
            ('holds', None), ('holds', [1] * 16))]
        for changes in invalid:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                validate_idle_pair_packet(dict(valid, **changes))
        changed = valid.copy()
        changed['holds'] = list(ORDINARY_PENTAGON_HOLDS)
        changed['holds'][0] += 1
        changed['holds'][1] -= 1
        with self.assertRaises(ValueError):
            validate_idle_pair_packet(changed)
        for required in ('pcm_quantization_bias', 'pcm_origin', 'holds'):
            partial = valid.copy()
            partial.pop(required)
            with self.subTest(missing=required), self.assertRaises(ValueError):
                validate_idle_pair_packet(partial)

    def test_malformed_arrays_and_changed_cycle_rejected_without_mutation(self):
        words, nxt = table()
        for first, second in ((words[:63], nxt), (words, nxt[:63]), (words.astype(float), nxt),
                              (words, nxt.astype(float)), (np.full((64, 32), 65536), nxt),
                              (np.full((64, 32), -1), nxt), (words, np.full((64, 32), 32)),
                              (words, np.full((64, 32), -1))):
            with self.subTest(shape=(first.shape, second.shape)), self.assertRaises(ValueError):
                apply_idle_pair_packet(first, second, model())
        for state, target in ((16, 16), (17, 17), (16, 18), (17, 15)):
            changed = nxt.copy()
            changed[32, state] = target
            before = changed.copy()
            with self.subTest(state=state), self.assertRaises(ValueError):
                apply_idle_pair_packet(words, changed, model())
            np.testing.assert_array_equal(changed, before)
        reset = nxt.copy()
        reset[32, :] = 16
        with self.assertRaises(ValueError):
            apply_idle_pair_packet(words, reset, model())

    def test_all_bin_closure_and_dictionary(self):
        words, nxt = table()
        result, successor = apply_idle_pair_packet(words, nxt, model())
        states = {16}
        while True:
            expanded = states | set(map(int, nxt[:, sorted(states)].ravel()))
            if expanded == states:
                break
            states = expanded
        self.assertEqual(len(states), 18)
        self.assertIs(successor, nxt)
        original, candidate = words[:, sorted(states)], result[:, sorted(states)]
        self.assertEqual((len(np.unique(original >> 8)), len(np.unique(original & 255))), (138, 96))
        self.assertEqual((len(np.unique(candidate >> 8)), len(np.unique(candidate & 255))), (138, 98))
        for state in states:
            self.assertTrue(set(map(int, successor[:, state])).issubset(states))

    def test_complete_source_free_selection_and_exact_symmetry(self):
        report, arrays = self.selection, self.arrays
        self.assertFalse(report['source_audio_opened'])
        self.assertEqual(report['all_words_enumerated'], 65536)
        self.assertEqual(report['duty224_words'], 424)
        self.assertEqual(report['duty225_words'], 424)
        self.assertEqual(report['pairs_enumerated'], 179776)
        self.assertEqual(report['complement_swap_fixed_pairs'], 424)
        self.assertEqual(report['complement_swap_orbits'], 90100)
        self.assertEqual(tuple(report['selected_words']), IDLE_PAIR_WORDS)
        self.assertLess(report['solve_condition'], 20)
        self.assertLess(report['solve_residual_max'], 1e-14)
        self.assertLess(report['spectral_radius_two_packets'], 1)
        first, second = arrays['first_words'], arrays['second_words']
        rows = np.searchsorted(first, 65535 - second)
        columns = np.searchsorted(second, 65535 - first)
        for key in ('variance', 'second_moment'):
            values = arrays[key]
            np.testing.assert_array_equal(values, values[rows[None, :], columns[:, None]])
        means = arrays['midpoint_weighted_mean']
        np.testing.assert_array_equal(means, -means[rows[None, :], columns[:, None]])
        self.assertEqual(report['top_candidates'][1]['words'], [0xA952, 0xA965])
        self.assertEqual(report['top_candidates'][0]['variance'], report['top_candidates'][1]['variance'])

    def test_independent_32_transition_periodic_filter_matches_selection(self):
        initial, final, output, mean, second_moment, variance = direct_pair_metrics(IDLE_PAIR_WORDS)
        np.testing.assert_allclose(final, initial, atol=2e-13, rtol=0)
        arrays, report = self.arrays, self.selection
        predicted = (arrays['steady_word16_basis'] @ signed(IDLE_PAIR_WORDS[0]) +
                     arrays['steady_word17_basis'] @ signed(IDLE_PAIR_WORDS[1]))
        np.testing.assert_allclose(initial, predicted, atol=2e-13, rtol=0)
        state1 = arrays['a'] @ predicted + arrays['b'] @ signed(IDLE_PAIR_WORDS[0])
        composed_output = np.r_[arrays['l'] @ predicted + arrays['r'] @ signed(IDLE_PAIR_WORDS[0]),
                                arrays['l'] @ state1 + arrays['r'] @ signed(IDLE_PAIR_WORDS[1])]
        np.testing.assert_allclose(output, composed_output, atol=2e-13, rtol=0)
        self.assertAlmostEqual(mean, report['selected_midpoint_weighted_mean'], places=14)
        self.assertAlmostEqual(second_moment, report['selected_second_moment'], places=14)
        self.assertAlmostEqual(variance, report['selected_estimated_variance'], places=14)

    def test_quadratic_score_matches_direct_outputs_for_other_pairs(self):
        first, second = self.arrays['first_words'], self.arrays['second_words']
        for row, column in ((0, 0), (0, 423), (423, 0), (423, 423), (42, 83), (212, 211)):
            pair = int(first[row]), int(second[column])
            _, _, _, mean, second_moment, variance = direct_pair_metrics(pair)
            with self.subTest(pair=pair):
                self.assertAlmostEqual(mean, self.arrays['midpoint_weighted_mean'][row, column], places=13)
                self.assertAlmostEqual(second_moment, self.arrays['second_moment'][row, column], places=13)
                self.assertAlmostEqual(variance, self.arrays['variance'][row, column], places=13)


if __name__ == '__main__':
    unittest.main()
