import unittest

from apex.core.parsing import InputError, clean, parse_match, parse_quick, resolve_legend, to_int


class ParseMatchTests(unittest.TestCase):
    def test_a_number_alone_is_kills_with_no_win(self):
        self.assertEqual(parse_match(["7"]), (7, 0, None))

    def test_two_numbers_are_kills_and_wins(self):
        self.assertEqual(parse_match(["7", "0"]), (7, 0, None))
        self.assertEqual(parse_match(["7", "2", "wraith"]), (7, 2, "wraith"))

    def test_one_number_then_a_legend_is_one_win(self):
        self.assertEqual(parse_match(["5", "wraith"]), (5, 1, "wraith"))

    def test_a_legend_can_have_two_words(self):
        self.assertEqual(parse_match(["5", "1", "mad", "maggie"]), (5, 1, "mad maggie"))

    def test_thousands_separators_are_accepted(self):
        self.assertEqual(parse_match(["1,500", "2"]), (1500, 2, None))

    def test_a_number_after_the_legend_is_rejected(self):
        with self.assertRaises(ValueError) as caught:
            parse_match(["5", "1", "wraith", "57"])
        self.assertNotIsInstance(caught.exception, InputError)

    def test_input_that_does_not_start_with_a_number_is_not_a_match(self):
        with self.assertRaises(InputError):
            parse_match(["wraith", "5"])


class ParseQuickTests(unittest.TestCase):
    def test_quick_tokens(self):
        self.assertEqual(parse_quick(["5k"]), ("5k", None))
        self.assertEqual(parse_quick(["1w", "wraith"]), ("1w", "wraith"))
        self.assertEqual(parse_quick(["3l"]), ("3l", None))

    def test_a_level_takes_nothing_after_it(self):
        with self.assertRaises(ValueError) as caught:
            parse_quick(["3l", "wraith"])
        self.assertNotIsInstance(caught.exception, InputError)

    def test_other_tokens_are_not_quick_entries(self):
        self.assertIsNone(parse_quick(["7"]))


class CleanTests(unittest.TestCase):
    def test_capitalizes_and_cuts_to_width(self):
        self.assertEqual(clean("wRAITH", 12), "Wraith")
        self.assertEqual(clean("abcdefghijklmnop", 12), "Abcdefghijkl")

    def test_empty_is_no_legend(self):
        self.assertEqual(clean(None, 12), "-")
        self.assertEqual(clean("   ", 12), "-")

    def test_the_column_separator_cannot_enter_a_data_file(self):
        self.assertNotIn("|", clean("a|b", 12))


class ResolveLegendTests(unittest.TestCase):
    KNOWN = {"Wraith", "Wraith x", "Bangalore", "Bloodhound", "Octane"}

    def test_a_unique_prefix_resolves(self):
        self.assertEqual(resolve_legend("oct", self.KNOWN), "Octane")

    def test_any_case(self):
        self.assertEqual(resolve_legend("OCTANE", self.KNOWN), "Octane")

    def test_exact_match_beats_longer_names(self):
        self.assertEqual(resolve_legend("wraith", self.KNOWN), "Wraith")

    def test_several_prefix_matches_are_rejected(self):
        with self.assertRaises(ValueError) as caught:
            resolve_legend("b", self.KNOWN)
        self.assertIn("Bangalore, Bloodhound", str(caught.exception))

    def test_unknown_is_none(self):
        self.assertIsNone(resolve_legend("zzz", self.KNOWN))
        self.assertIsNone(resolve_legend("octanes", self.KNOWN))


class ToIntTests(unittest.TestCase):
    def test_removes_separators(self):
        self.assertEqual(to_int("15,000"), 15000)
