import unittest
from core import Engine, Settings
from keycodes import mac_visible_flags


class DualModeTests(unittest.TestCase):
    def engine(self):
        return Engine(Settings(mode_scan=56, extra_mode_keys=((92, True),)))

    def test_left_hand_repeat_and_hold(self):
        e = self.engine()
        e.handle(92, True, True, 0)
        actions = []
        for i, scan in enumerate([30, 31, 30, 31]):
            actions.extend(e.handle(scan, False, True, .05 * (i + 1)).actions)
            if i != 3:
                e.handle(scan, False, False, .05 * (i + 1) + .01)
        self.assertEqual(actions, [('move', 32, 0)] * 2)
        self.assertTrue(e.tick(.5))
        e.handle(92, True, False, .6)
        self.assertEqual(e.tick(.7), ())

    def test_both_release_orders_and_drag(self):
        for first, second in [((56, False), (92, True)), ((92, True), (56, False))]:
            e = self.engine()
            e.handle(*first, True, 0)
            e.handle(57, False, True, .1)
            e.handle(*second, True, .2)
            self.assertEqual(e.handle(*first, False, .3).actions, ())
            self.assertTrue(e.active)
            self.assertEqual(e.handle(*second, False, .4).actions, (('button', 'left', False),))
            self.assertFalse(e.active)
            self.assertTrue(e.handle(57, False, False, .5).suppress)

    def test_escape_latched_across_second_mode(self):
        e = self.engine()
        e.handle(56, False, True, 0)
        e.handle(1, False, True, .1)
        e.handle(92, True, True, .2)
        self.assertFalse(e.active)

    def test_preheld_key_blocks_both_modes(self):
        e = self.engine()
        e.handle(30, False, True, 0)
        e.handle(56, False, True, .1)
        e.handle(92, True, True, .2)
        self.assertFalse(e.active)
        self.assertFalse(e.handle(30, False, False, .3).suppress)

    def test_left_command_tab_after_release(self):
        e = self.engine()
        e.handle(92, True, True, 0)
        e.handle(92, True, False, .1)
        for key, down in [((91, True), True), ((15, False), True),
                          ((15, False), False), ((91, True), False)]:
            self.assertFalse(e.handle(*key, down, .2).suppress)

    def test_right_alt_distinguished_from_left(self):
        e = Engine(Settings(extra_mode_keys=((56, True),)))
        self.assertFalse(e.handle(56, False, True, 0).suppress)
        e.handle(56, False, False, .1)
        e.handle(56, True, True, .2)
        self.assertTrue(e.active)

    def test_flags_preserve_opposite_modifier_and_shift(self):
        modes = self.engine().settings.mode_keys
        self.assertEqual(mac_visible_flags(0x180030, modes, set()), 0)
        self.assertEqual(mac_visible_flags(0x100018, modes, {(91, True)}), 0x100008)
        self.assertEqual(mac_visible_flags(0x80060, modes, {(56, True)}), 0x80040)
        self.assertEqual(mac_visible_flags(0x20000, modes, set()), 0x20000)

    def test_validation(self):
        for kwargs in [dict(mode_extended=1), dict(extra_mode_keys=[[56, 1]]),
                       dict(extra_mode_keys=[[True, False]]),
                       dict(extra_mode_keys=[[58, False]]), dict(extra_mode_keys='bad')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                Settings(**kwargs)
