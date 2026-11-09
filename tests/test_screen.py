import contextlib
import io
import tempfile
import unittest
from unittest.mock import patch

from apex.config import UI_WIDTH
from apex.ui.menus import help_text, quick_guide
from apex.ui.repl import interactive
from apex.ui.screen import CLEAR, Screen, center_block


class CenterBlockTests(unittest.TestCase):
    def test_every_line_moves_by_the_widest_line(self):
        self.assertEqual(center_block("ab\nabcd\n", 10), "   ab\n   abcd\n")

    def test_color_codes_take_no_space(self):
        self.assertEqual(center_block("\033[91mab\033[0m\n", 6), "  \033[91mab\033[0m\n")

    def test_a_block_wider_than_the_terminal_stays_at_the_left(self):
        self.assertEqual(center_block("abcdef\n", 4), "abcdef\n")

    def test_blank_lines_stay_empty(self):
        self.assertEqual(center_block("ab\n\nab\n", 6), "  ab\n\n  ab\n")


class DividerTests(unittest.TestCase):
    EQUALS, DASHES = "=" * UI_WIDTH, "-" * UI_WIDTH

    def test_page_dividers_fill_a_wider_terminal(self):
        out = center_block(f"{self.EQUALS}\nab\ncd\n{self.DASHES}\n", 100).split("\n")
        self.assertEqual(out[0], "=" * 100)
        self.assertEqual(out[1], " " * 10 + "ab")
        self.assertEqual(out[3], "-" * 100)

    def test_page_dividers_shrink_with_a_narrower_terminal(self):
        self.assertEqual(center_block(f"{self.EQUALS}\n", 40), "=" * 40 + "\n")

    def test_table_rules_keep_the_width_of_their_table(self):
        self.assertEqual(center_block("abcde\n-----\n", 15), "     abcde\n     -----\n")

    def test_a_title_between_dividers_is_centered_on_its_own(self):
        out = center_block(f"{self.EQUALS}\n  TITLE\n{self.EQUALS}\n", 100).split("\n")
        self.assertEqual(out[1], " " * 47 + "TITLE")

    def test_color_codes_do_not_move_a_title(self):
        out = center_block(f"{self.EQUALS}\n  \033[93mTITLE\033[0m\n{self.EQUALS}\n", 100).split("\n")
        self.assertEqual(out[1], " " * 47 + "\033[93mTITLE\033[0m")

    def test_the_titles_are_centered_at_every_width(self):
        for text, title in ((quick_guide(), "APEX CAREER DIARY"), (help_text(), "APEX CAREER DIARY - HELP")):
            for cols in range(30, 200):
                with self.subTest(title=title, cols=cols):
                    line = next(x for x in center_block(text, cols).split("\n") if title in x)
                    left = len(line) - len(title)
                    self.assertIn(cols - len(title) - 2 * left, (0, 1))

    def test_the_titles_are_centered_in_plain_output(self):
        for text, title in ((quick_guide(), "APEX CAREER DIARY"), (help_text(), "APEX CAREER DIARY - HELP")):
            with self.subTest(title=title):
                line = next(x for x in text.split("\n") if title in x)
                self.assertIn(UI_WIDTH - len(title) - 2 * (len(line) - len(title)), (0, 1))

    def test_no_width_leaves_dividers_alone(self):
        self.assertEqual(center_block(quick_guide(), 0), quick_guide())


class ScreenCase(unittest.TestCase):
    def setUp(self):
        self.cols = UI_WIDTH
        self.out = io.StringIO()
        self.typed = "7 1"
        self.screen = Screen(lambda: self.cols, self.out, reader=self.reader)
        self.while_reading = lambda: None

    def reader(self):
        self.while_reading()
        return self.typed

    def resize(self, cols):
        """A new width that holds still: seen by one poll, redrawn by the next."""
        self.cols = cols
        self.screen.poll()
        self.screen.poll()

    def drawn(self):
        """What is on the screen after the last redraw."""
        return self.out.getvalue().rsplit(CLEAR, 1)[-1]


class ScreenTests(ScreenCase):
    def test_a_block_is_centered_on_the_current_width(self):
        self.cols = 20
        screen = Screen(lambda: self.cols, self.out)
        screen.show("abcd\n")
        self.assertEqual(self.out.getvalue(), " " * 8 + "abcd\n")

    def test_the_prompt_starts_at_the_left_edge_of_the_ui_column(self):
        self.cols = UI_WIDTH + 20
        screen = Screen(lambda: self.cols, self.out, reader=self.reader)
        self.assertEqual(screen.read("> "), "7 1")
        self.assertEqual(self.out.getvalue(), " " * 10 + "> ")

    def test_the_same_width_never_redraws(self):
        self.screen.show("abcd\n")
        self.screen.poll()
        self.screen.poll()
        self.assertNotIn(CLEAR, self.out.getvalue())

    def test_a_new_width_redraws_everything_recentered(self):
        self.screen.show("abcd\n")
        self.screen.read("> ")
        self.screen.show("efgh\n")
        self.resize(UI_WIDTH + 20)
        pad = " " * ((UI_WIDTH + 20 - 4) // 2)
        self.assertEqual(self.drawn(), f"{pad}abcd\n{' ' * 10}> 7 1\n{pad}efgh\n")

    def test_a_new_width_rescales_the_dividers(self):
        self.screen.show("=" * UI_WIDTH + "\n")
        self.resize(120)
        self.assertEqual(self.drawn(), "=" * 120 + "\n")

    def test_a_width_still_changing_waits_until_it_settles(self):
        self.screen.show("abcd\n")
        for cols in (100, 110, 120):
            self.cols = cols
            self.screen.poll()
        self.assertNotIn(CLEAR, self.out.getvalue())
        self.screen.poll()
        self.assertEqual(self.out.getvalue().count(CLEAR), 1)

    def test_a_resize_while_waiting_for_input_shows_the_prompt_again(self):
        self.while_reading = lambda: self.resize(UI_WIDTH + 20)
        self.screen.show("abcd\n")
        self.assertEqual(self.screen.read("> "), "7 1")
        self.assertTrue(self.drawn().endswith(" " * 10 + "> "))

    def test_a_resize_while_waiting_for_input_discards_the_half_typed_line(self):
        discarded = []
        screen = Screen(lambda: self.cols, self.out, reader=self.reader, discard_typing=lambda: discarded.append(1))
        self.screen = screen
        self.while_reading = lambda: self.resize(UI_WIDTH + 20)
        screen.read("> ")
        self.assertEqual(discarded, [1])

    def test_a_resize_between_prompts_discards_nothing(self):
        discarded = []
        screen = Screen(lambda: self.cols, self.out, reader=self.reader, discard_typing=lambda: discarded.append(1))
        self.screen = screen
        screen.read("> ")
        self.resize(UI_WIDTH + 20)
        self.assertEqual(discarded, [])

    def test_a_finished_prompt_is_not_shown_twice(self):
        self.screen.read("> ")
        self.resize(UI_WIDTH + 20)
        self.assertEqual(self.drawn().count("> "), 1)

    def test_a_refused_read_leaves_no_prompt_behind(self):
        def refuse():
            raise EOFError
        screen = Screen(lambda: self.cols, self.out, reader=refuse)
        with self.assertRaises(EOFError):
            screen.read("> ")
        self.cols = UI_WIDTH + 20
        screen.poll()
        screen.poll()
        self.assertEqual(self.drawn(), "")

    def test_no_width_means_plain_output(self):
        screen = Screen(lambda: 0, self.out, reader=self.reader)
        screen.show("abcd\n")
        screen.read("> ")
        self.assertEqual(self.out.getvalue(), "abcd\n> ")


class InteractiveTests(unittest.TestCase):
    def test_output_that_is_not_a_terminal_stays_plain(self):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as d, contextlib.redirect_stdout(out), \
                patch("builtins.input", side_effect=["nonsense", ""]):
            interactive(d)
        self.assertEqual(out.getvalue(), quick_guide() + "> " + quick_guide() + "> ")


if __name__ == "__main__":
    unittest.main()
