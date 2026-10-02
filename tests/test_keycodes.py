import unittest
from core import Engine, Settings
from keycodes import linux_key, mac_key


class PlatformMappingTests(unittest.TestCase):
    def test_linux_special_keys(self):
        self.assertEqual(linux_key(100), (0x38, True))
        self.assertEqual(linux_key(125), (0x5B, True))
        self.assertEqual(linux_key(103), (0x48, True))
        self.assertEqual(linux_key(89), (0x73, False))
        self.assertEqual(linux_key(124), (0x7D, False))
        self.assertNotEqual(linux_key(96), (0x1C, False))

    def test_mac_controls(self):
        self.assertEqual(mac_key(100), (0x42, False))
        self.assertEqual(mac_key(55), (0x5B, True))
        self.assertEqual(mac_key(56), (0x2A, False))
        self.assertEqual(mac_key(60), (0x36, False))
        self.assertEqual(mac_key(126), (0x48, True))
        self.assertEqual(mac_key(94), (0x73, False))

    def test_unknown_codes_do_not_alias_mapped_keys(self):
        self.assertGreater(linux_key(200)[0], 255)
        self.assertGreater(mac_key(200)[0], 255)

    def test_both_platforms_two_key_and_hold(self):
        for mapper, mode, j, k in ((linux_key, 58, 36, 37), (mac_key, 100, 38, 40)):
            with self.subTest(mapper=mapper):
                e = Engine(Settings(mode_scan=mapper(mode)[0]))
                e.handle(*mapper(mode), True, 0)
                actions = []
                for i, code in enumerate([j, k, j, k]):
                    actions.extend(e.handle(*mapper(code), True, 0.05 * i).actions)
                    if i < 3:
                        e.handle(*mapper(code), False, 0.05 * i + 0.01)
                self.assertEqual(actions, [("move", 32, 0)] * 2)
                self.assertTrue(e.tick(0.46))
                e.handle(*mapper(mode), False, 0.47)
                self.assertEqual(e.tick(1), ())

    def test_mac_command_tab_and_linux_alt_tab_pass(self):
        for mapper, modifier, tab in ((mac_key, 55, 48), (linux_key, 56, 15)):
            e = Engine(Settings())
            for code in (modifier, tab):
                self.assertFalse(e.handle(*mapper(code), True, 0).suppress)
            for code in (tab, modifier):
                self.assertFalse(e.handle(*mapper(code), False, 1).suppress)


if __name__ == "__main__":
    unittest.main()
