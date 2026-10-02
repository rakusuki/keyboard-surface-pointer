"""Exercise grab/forward/cleanup without reading any real input devices."""
from contextlib import redirect_stdout
import io
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import Settings
from ubuntu_backend import run


class FakeKeyboard:
    name = "test physical keyboard"

    def __init__(self, events):
        self.events = events
        self.grabbed = False
        self.released = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def capabilities(self):
        return {1: [36, 37, 28, 58, 56, 15, 29, 1]}

    def active_keys(self):
        return []

    def grab(self):
        self.grabbed = True

    def ungrab(self):
        self.released = True

    def read(self):
        return iter(self.events)


class FakeOutput:
    def __init__(self):
        self.events = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def write(self, kind, code, value):
        self.events.append((kind, code, value))

    def syn(self):
        pass


class UbuntuBackendTests(unittest.TestCase):
    def exercise(self, events):
        keyboard, output = FakeKeyboard(events), FakeOutput()
        constants = SimpleNamespace(EV_KEY=1, EV_REL=2, EV_SYN=0, SYN_DROPPED=3,
                                    KEY_J=36, KEY_K=37, KEY_ENTER=28, BTN_LEFT=272,
                                    BTN_RIGHT=273, REL_X=0, REL_Y=1, REL_WHEEL=8)
        module = SimpleNamespace(InputDevice=lambda path: keyboard,
                                 UInput=lambda *a, **kw: output,
                                 ecodes=constants, list_devices=lambda: [])
        with patch.dict("sys.modules", evdev=module), \
                patch("select.select", return_value=([keyboard], [], [])), \
                patch("time.monotonic", side_effect=[i * 0.02 for i in range(100)]), \
                redirect_stdout(io.StringIO()):
            run(Settings(), device_path="fake-device")
        self.assertTrue(keyboard.grabbed)
        self.assertTrue(keyboard.released)
        return output.events

    def test_consumed_keys_and_normal_alt_tab_forwarding(self):
        sequence = [(58, 1), (36, 1), (36, 0), (37, 1), (37, 0), (58, 0),
                    (56, 1), (15, 1), (15, 0), (56, 0),
                    (29, 1), (56, 1), (1, 1)]  # emergency stop
        events = [SimpleNamespace(type=1, code=code, value=value) for code, value in sequence]
        output = self.exercise(events)
        self.assertIn((2, 0, 32), output)
        self.assertFalse(any(kind == 1 and code in {36, 37, 58} for kind, code, _ in output))
        for code, value in [(56, 1), (15, 1), (15, 0), (56, 0), (29, 0)]:
            self.assertIn((1, code, value), output)

    def test_dropped_input_ungrabs(self):
        keyboard = FakeKeyboard([SimpleNamespace(type=0, code=3, value=0)])
        output = FakeOutput()
        constants = SimpleNamespace(EV_KEY=1, EV_REL=2, EV_SYN=0, SYN_DROPPED=3,
                                    KEY_J=36, KEY_K=37, KEY_ENTER=28, BTN_LEFT=272,
                                    BTN_RIGHT=273, REL_X=0, REL_Y=1, REL_WHEEL=8)
        module = SimpleNamespace(InputDevice=lambda path: keyboard,
                                 UInput=lambda *a, **kw: output,
                                 ecodes=constants, list_devices=lambda: [])
        with patch.dict("sys.modules", evdev=module), \
                patch("select.select", return_value=([keyboard], [], [])), \
                redirect_stdout(io.StringIO()), self.assertRaises(RuntimeError):
            run(Settings(), device_path="fake-device")
        self.assertTrue(keyboard.released)


if __name__ == "__main__":
    unittest.main()
