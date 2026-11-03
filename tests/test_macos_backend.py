"""Quartz adapter regression tests; no real event tap or desktop input."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from core import Settings
from keycodes import mac_modifier_down, mac_visible_flags
from macos_backend import run


class MacBackendTests(unittest.TestCase):
    def exercise(self, sequence, dry_run=False, preheld=()):
        callback = None
        output = []
        forwarded = []
        clock = [0.0]
        kinds = dict(kCGEventKeyDown=10, kCGEventKeyUp=11,
                     kCGEventFlagsChanged=12, kCGEventTapDisabledByTimeout=99,
                     kCGEventTapDisabledByUserInput=100)
        q = SimpleNamespace(**kinds)
        for name in ('kCGEventSourceStateHIDSystemState', 'kCGKeyboardEventKeycode',
                     'kCGHIDEventTap', 'kCGHeadInsertEventTap', 'kCGEventTapOptionDefault',
                     'kCGEventLeftMouseDragged', 'kCGEventRightMouseDragged',
                     'kCGEventMouseMoved', 'kCGMouseButtonLeft', 'kCGMouseButtonRight',
                     'kCGEventLeftMouseDown', 'kCGEventRightMouseDown',
                     'kCGEventLeftMouseUp', 'kCGEventRightMouseUp', 'kCGScrollEventUnitLine'):
            setattr(q, name, name)
        q.CGPreflightListenEventAccess = lambda: True
        q.CGPreflightPostEventAccess = lambda: True
        # HID snapshot intentionally differs from queued events (quick taps).
        q.CGEventSourceKeyState = lambda state, code: code in preheld
        q.CGEventGetIntegerValueField = lambda event, field: event['code']
        q.CGEventGetFlags = lambda event: event['flags']
        q.CGEventSetFlags = lambda event, flags: event.update(flags=flags)
        q.CGEventCreate = lambda source: None
        q.CGEventGetLocation = lambda event: SimpleNamespace(x=100, y=100)
        q.CGEventCreateMouseEvent = lambda source, kind, point, button: dict(kind=kind, point=point, button=button)
        q.CGEventPost = lambda tap, event: output.append(event.copy())
        q.CGEventTapEnable = lambda *args: None

        def create(*args):
            nonlocal callback
            callback = args[-2]
            return 'tap'

        def pump(*args):
            if not sequence:
                raise KeyboardInterrupt
            kind, code, flags, now = sequence.pop(0)
            clock[0] = now
            if kind is not None:
                event = dict(code=code, flags=flags)
                result = callback(None, kind, event, None)
                if result is not None:
                    forwarded.append(result.copy())

        q.CGEventTapCreate = create
        cf = SimpleNamespace(CFRunLoopGetCurrent=lambda: 'loop',
                             CFRunLoopRunInMode=pump,
                             CFMachPortCreateRunLoopSource=lambda *args: 'source',
                             kCFRunLoopCommonModes=0, kCFRunLoopDefaultMode=0)
        for name in ('CFRunLoopAddSource', 'CFRunLoopRemoveSource', 'CFMachPortInvalidate'):
            setattr(cf, name, lambda *args: None)
        settings = Settings(**json.loads(Path('config.macos.json').read_text()))
        with patch.dict('sys.modules', Quartz=q, CoreFoundation=cf), \
                patch('macos_backend.time.monotonic', side_effect=lambda: clock[0]), \
                redirect_stdout(io.StringIO()) as log, self.assertRaises(KeyboardInterrupt):
            run(settings, dry_run=dry_run)
        return output, forwarded, log.getvalue()

    def test_quick_right_command_drag_release_and_shortcuts(self):
        output, forwarded, _ = self.exercise([
            (12, 54, 0x100010, 0), (10, 49, 0x100010, .01),
            (10, 0, 0x100010, .02), (11, 0, 0x100010, .03),
            (10, 1, 0x100010, .04), (12, 54, 0, .1),
            (11, 49, 0, .11), (11, 1, 0, .12),
            (12, 55, 0x100008, .2), (10, 8, 0x100008, .21),
            (11, 8, 0x100008, .22), (10, 48, 0x100008, .23),
            (11, 48, 0x100008, .24), (12, 55, 0, .25)])
        self.assertEqual([e['kind'] for e in output],
                         ['kCGEventLeftMouseDown', 'kCGEventLeftMouseDragged', 'kCGEventLeftMouseUp'])
        self.assertTrue(all(e['flags'] == 0 for e in output))
        self.assertEqual([e['code'] for e in forwarded], [55, 8, 8, 48, 48, 55])
        self.assertEqual([e['flags'] for e in forwarded], [0x100008] * 5 + [0])

    def test_left_hand_hold_precision_and_key_release(self):
        output, _, _ = self.exercise([
            (12, 54, 0x100010, 0), (10, 0, 0x100010, .01),
            (11, 0, 0x100010, .02), (10, 1, 0x100010, .03),
            (None, 0, 0, .29), (12, 56, 0x120012, .30),
            (None, 0, 0, .35), (11, 1, 0x120012, .36),
            (None, 0, 0, .45), (12, 56, 0x100010, .46), (12, 54, 0, .47)])
        self.assertEqual([e['point'] for e in output], [(132, 100), (103, 100), (102, 100)])

    def test_dry_run_never_posts(self):
        output, _, log = self.exercise([
            (12, 58, 0x80020, 0), (10, 38, 0x80020, .01),
            (11, 38, 0x80020, .02), (10, 40, 0x80020, .03),
            (12, 58, 0, .04)], dry_run=True)
        self.assertEqual(output, [])
        self.assertIn("('move', 32, 0)", log)

    def test_preheld_mode_release_preserves_opposite_command(self):
        _, forwarded, _ = self.exercise([
            (12, 55, 0x100018, 0), (12, 54, 0x100008, .01),
            (10, 8, 0x100008, .02), (11, 8, 0x100008, .03),
            (12, 55, 0, .04)], preheld=(54,))
        self.assertEqual(forwarded[0]['flags'], 0x100018)
        self.assertEqual([e['code'] for e in forwarded], [55, 54, 8, 8, 55])

    def test_modifier_sides_are_independent(self):
        for code, own, opposite, aggregate in [(54, 0x10, 8, 0x100000),
                                               (58, 0x20, 0x40, 0x80000),
                                               (56, 2, 4, 0x20000),
                                               (59, 1, 0x2000, 0x40000)]:
            with self.subTest(code=code):
                self.assertTrue(mac_modifier_down(code, aggregate | own | opposite))
                self.assertFalse(mac_modifier_down(code, aggregate | opposite))
                self.assertFalse(mac_modifier_down(code, 0))

    def test_forwarded_reserved_modifier_keeps_flags(self):
        modes = Settings(mode_scan=56, extra_mode_keys=((92, True),)).mode_keys
        self.assertEqual(mac_visible_flags(0x100010, modes, {(92, True)}), 0x100010)
