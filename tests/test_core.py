import unittest
from pathlib import Path
from core import Engine, Settings, key_positions
from pointer import load_settings


class GestureTests(unittest.TestCase):
    def setUp(self):
        self.engine = Engine(Settings())
        self.time = 0

    def key(self, scan, down=True, extended=False, delay=0.05):
        self.time += delay
        return self.engine.handle(scan, extended, down, self.time)

    def mode(self):
        self.assertTrue(self.key(0x3A).suppress)

    def test_typing_passes(self):
        self.assertFalse(self.key(0x21).suppress)
        self.assertFalse(self.key(0x21, False).suppress)

    def test_anchor_move_and_repeat(self):
        self.mode()
        self.assertEqual(self.key(0x21).actions, ())
        self.assertEqual(self.key(0x22).actions, (("move", 32, 0),))
        self.assertEqual(self.key(0x22).actions, ())

    def test_staggered_vertical_motion(self):
        self.mode()
        self.key(0x21)
        self.assertEqual(self.key(0x13).actions, (("move", -8, -32),))

    def test_precision(self):
        self.mode()
        self.key(0x2A)
        self.key(0x21)
        self.assertEqual(self.key(0x22).actions, (("move", 4, 0),))

    def test_timeout(self):
        self.mode()
        self.key(0x21)
        self.assertEqual(self.key(0x22, delay=1).actions, ())
        self.assertEqual(self.key(0x23).actions, (("move", 32, 0),))

    def test_jump_reanchors(self):
        self.mode()
        self.key(0x1E)
        self.assertEqual(self.key(0x26).actions, ())
        self.assertEqual(self.key(0x27).actions, (("move", 32, 0),))

    def test_late_keyup_and_reposition(self):
        self.mode()
        self.key(0x21)
        self.key(0x3A, False)
        self.assertTrue(self.key(0x21, False).suppress)
        self.mode()
        self.assertEqual(self.key(0x22).actions, ())

    def test_preheld_key_preserves_forwarded_keyup(self):
        self.key(0x1D)
        self.mode()
        self.assertFalse(self.engine.active)
        self.assertFalse(self.key(0x1D, False).suppress)
        self.assertFalse(self.key(0x21).suppress)

    def test_click_drag(self):
        self.mode()
        self.assertEqual(self.key(0x39).actions, (("button", "left", True),))
        self.key(0x21)
        self.assertEqual(self.key(0x22).actions, (("move", 32, 0),))
        self.assertEqual(self.key(0x39, False).actions, (("button", "left", False),))

    def test_exit_releases_both_buttons(self):
        self.mode()
        self.key(0x39)
        self.key(0x1C)
        self.assertEqual(self.key(0x3A, False).actions,
                         (("button", "left", False), ("button", "right", False)))
        self.assertTrue(self.key(0x39, False).suppress)
        self.assertEqual(self.engine.reset(), ())

    def test_escape_cancels_until_mode_released(self):
        self.mode()
        self.key(0x39)
        result = self.key(0x01)
        self.assertTrue(result.suppress)
        self.assertEqual(result.actions, (("button", "left", False),))
        self.assertFalse(self.engine.active)
        self.assertTrue(self.key(0x39, False).suppress)
        self.key(0x3A)  # repeat must not reactivate
        self.assertFalse(self.engine.active)

    def test_scroll_and_numpad_distinction(self):
        self.mode()
        self.assertEqual(self.key(0x48, extended=True).actions, (("scroll", 120),))
        self.assertEqual(self.key(0x48).actions, ())

    def test_f8_mode(self):
        engine = Engine(Settings(mode_scan=0x42))
        self.assertTrue(engine.handle(0x42, False, True, 0).suppress)
        self.assertTrue(engine.active)


class ContinuousMotionTests(unittest.TestCase):
    def make(self):
        e = Engine(Settings())
        e.handle(0x3A, False, True, 0)
        return e

    def stroke(self, e, codes, start=0):
        for i, code in enumerate(codes):
            e.handle(code, False, True, start + i * 0.05)
            e.handle(code, False, False, start + i * 0.05 + 0.01)

    def test_repeated_jkl_never_moves_back(self):
        e = self.make()
        moves = []
        for i, code in enumerate([0x24, 0x25, 0x26] * 4):
            moves.extend(e.handle(code, False, True, i * 0.05).actions)
            e.handle(code, False, False, i * 0.05 + 0.01)
        self.assertEqual(moves, [("move", 32, 0)] * 8)

    def test_adjacent_reverse_reanchors_then_moves_left(self):
        e = self.make()
        self.stroke(e, [0x24, 0x25, 0x26])
        self.assertEqual(e.handle(0x25, False, True, 0.15).actions, ())
        self.assertEqual(e.handle(0x24, False, True, 0.20).actions, (("move", -32, 0),))

    def test_hold_and_release(self):
        e = self.make()
        self.stroke(e, [0x24, 0x25])
        e.handle(0x26, False, True, 0.1)
        self.assertEqual(e.tick(0.34), ())
        self.assertEqual(e.tick(0.40), (("move", 16, 0),))
        e.handle(0x26, False, False, 0.41)
        self.assertEqual(e.tick(0.5), ())
        self.assertEqual(e.handle(0x24, False, True, 0.51).actions, ())

    def test_first_key_alone_cannot_continue(self):
        e = self.make()
        e.handle(0x24, False, True, 0)
        self.assertEqual(e.tick(1), ())

    def test_release_mode_and_escape_stop_continuation(self):
        for scan in (0x3A, 0x01):
            e = self.make()
            e.handle(0x24, False, True, 0)
            e.handle(0x25, False, True, 0.05)
            self.assertTrue(e.tick(0.4))
            e.handle(scan, False, scan == 0x01, 0.41)
            self.assertEqual(e.tick(0.5), ())

    def test_precision_speed_and_no_catchup_jump(self):
        e = self.make()
        e.handle(0x24, False, True, 0)
        e.handle(0x25, False, True, 0.05)
        e.handle(0x2A, False, True, 0.1)
        self.assertEqual(e.tick(10), (("move", 2, 0),))

    def test_diagonal_is_normalized(self):
        e = self.make()
        e.handle(0x21, False, True, 0)
        e.handle(0x13, False, True, 0.05)
        actions = e.tick(0.35)
        self.assertLess(actions[0][1], 0)
        self.assertLess(actions[0][2], 0)
        self.assertLessEqual(abs(actions[0][2]), 16)

    def test_autorepeat_does_not_postpone_hold(self):
        e = self.make()
        e.handle(0x24, False, True, 0)
        e.handle(0x25, False, True, 0.05)
        e.handle(0x25, False, True, 0.29)
        self.assertTrue(e.tick(0.35))

    def test_leftward_repeated_strokes(self):
        e = self.make()
        moves = []
        for i, code in enumerate([0x26, 0x25, 0x24] * 3):
            moves.extend(e.handle(code, False, True, i * 0.05).actions)
            e.handle(code, False, False, i * 0.05 + 0.01)
        self.assertEqual(moves, [("move", -32, 0)] * 6)


class TwoKeyAndShortcutTests(unittest.TestCase):
    def test_two_key_strokes_both_directions(self):
        for codes, dx in (([0x24, 0x25], 32), ([0x25, 0x24], -32)):
            with self.subTest(codes=codes):
                e = Engine(Settings())
                e.handle(0x3A, False, True, 0)
                actions = []
                for i, code in enumerate(codes * 5):
                    actions.extend(e.handle(code, False, True, i * 0.05).actions)
                    e.handle(code, False, False, i * 0.05 + 0.01)
                self.assertEqual(actions, [("move", dx, 0)] * 5)

    def test_two_key_hold_continues(self):
        e = Engine(Settings())
        e.handle(0x3A, False, True, 0)
        for i, code in enumerate([0x24, 0x25, 0x24]):
            e.handle(code, False, True, i * 0.05)
            e.handle(code, False, False, i * 0.05 + 0.01)
        e.handle(0x25, False, True, 0.15)
        self.assertEqual(e.tick(0.46), (("move", 16, 0),))
        e.handle(0x25, False, False, 0.47)
        self.assertEqual(e.tick(0.5), ())

    def assert_shortcut_passes(self, e, codes):
        for i, (scan, extended) in enumerate(codes):
            result = e.handle(scan, extended, True, 1 + i * 0.01)
            self.assertFalse(result.suppress)
            self.assertEqual(result.actions, ())
        for i, (scan, extended) in enumerate(reversed(codes)):
            self.assertFalse(e.handle(scan, extended, False, 2 + i * 0.01).suppress)

    def test_shortcuts_before_and_after_pointing(self):
        shortcuts = [
            [(0x38, False), (0x0F, False)],  # Alt+Tab
            [(0x38, True), (0x0F, False)],   # right Alt+Tab
            [(0x1D, False), (0x2E, False)], # Ctrl+C
            [(0x2A, False), (0x23, False)], # Shift+H
            [(0x5B, True), (0x20, False)],  # Win+D
        ]
        for after_mode in (False, True):
            for codes in shortcuts:
                with self.subTest(after_mode=after_mode, codes=codes):
                    e = Engine(Settings())
                    if after_mode:
                        e.handle(0x3A, False, True, 0)
                        e.handle(0x24, False, True, 0.05)
                        e.handle(0x25, False, True, 0.1)
                        e.tick(0.4)
                        e.handle(0x3A, False, False, 0.5)
                        e.handle(0x24, False, False, 0.6)
                        e.handle(0x25, False, False, 0.6)
                    self.assert_shortcut_passes(e, codes)
                    self.assertEqual(e.tick(3), ())

    def test_alt_pressed_after_mode_release_even_with_late_movement_keyup(self):
        e = Engine(Settings())
        e.handle(0x3A, False, True, 0)
        e.handle(0x24, False, True, 0.05)
        e.handle(0x3A, False, False, 0.1)
        self.assert_shortcut_passes(e, [(0x38, False), (0x0F, False)])
        self.assertTrue(e.handle(0x24, False, False, 3).suppress)

    def test_forwarded_alt_release_is_not_swallowed(self):
        e = Engine(Settings())
        self.assertFalse(e.handle(0x38, False, True, 0).suppress)
        e.handle(0x3A, False, True, 0.05)
        e.handle(0x3A, False, False, 0.1)
        self.assertFalse(e.handle(0x38, False, False, 0.15).suppress)


class ConfigurationTests(unittest.TestCase):
    def test_default_config(self):
        self.assertEqual(load_settings(Path(__file__).parents[1] / "config.json"), Settings())

    def test_layouts(self):
        self.assertIn((0x73, False), key_positions("jis"))
        self.assertNotIn((0x73, False), key_positions("us"))
        self.assertNotEqual(key_positions("us")[(0x2B, False)],
                            key_positions("jis")[(0x2B, False)])

    def test_invalid(self):
        for options in ({"gain": 0}, {"gain": float("nan")}, {"gain": True},
                        {"mode_scan": 0x39}, {"layout": "unknown"},
                        {"precision_gain": 100}, {"stroke_timeout": -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                Settings(**options)


if __name__ == "__main__":
    unittest.main()
