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
