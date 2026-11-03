"""macOS Quartz event-tap backend. Configurable left/right hold-mode keys."""
import time

from core import Engine
from keycodes import MAC_CODES, MAC_EXTENDED, MAC_MODIFIERS, mac_key, mac_modifier_down


def run(settings, dry_run=False, check_backend=False):
    import Quartz as q
    from CoreFoundation import (
        CFRunLoopGetCurrent, CFRunLoopAddSource, CFRunLoopRemoveSource,
        CFRunLoopRunInMode, CFMachPortCreateRunLoopSource, CFMachPortInvalidate,
        kCFRunLoopCommonModes, kCFRunLoopDefaultMode,
    )

    if (0x3A, False) in settings.mode_keys:
        raise ValueError("macOS Caps Lock is a toggle; use Option, right Command or F8")
    if check_backend:
        print("Quartz/CoreFoundation imported. No event tap created or mouse events sent.")
        print(f"Input Monitoring granted: {bool(q.CGPreflightListenEventAccess())}")
        print(f"Accessibility/post-event access granted: {bool(q.CGPreflightPostEventAccess())}")
        return
    if not q.CGPreflightListenEventAccess() or not q.CGPreflightPostEventAccess():
        q.CGRequestListenEventAccess()
        q.CGRequestPostEventAccess()
        raise RuntimeError("Grant Input Monitoring and Accessibility to your terminal/Python in System Settings, then restart it")
    engine = Engine(settings)
    # Seed physical state to preserve releases for keys held before tap creation.
    for code in set(MAC_CODES) | set(MAC_EXTENDED):
        if q.CGEventSourceKeyState(q.kCGEventSourceStateHIDSystemState, code):
            engine.held[mac_key(code)] = False
    buttons = set()
    failed = []
    pending = []

    def emit(actions):
        for action in actions:
            if dry_run:
                pending.append(action)
                continue
            location = q.CGEventGetLocation(q.CGEventCreate(None))
            point = (location.x, location.y)
            if action[0] == "move":
                point = (point[0] + action[1], point[1] + action[2])
                if "left" in buttons:
                    kind, button = q.kCGEventLeftMouseDragged, q.kCGMouseButtonLeft
                elif "right" in buttons:
                    kind, button = q.kCGEventRightMouseDragged, q.kCGMouseButtonRight
                else:
                    kind, button = q.kCGEventMouseMoved, q.kCGMouseButtonLeft
                event = q.CGEventCreateMouseEvent(None, kind, point, button)
            elif action[0] == "button":
                left = action[1] == "left"
                button = q.kCGMouseButtonLeft if left else q.kCGMouseButtonRight
                kind = ((q.kCGEventLeftMouseDown if left else q.kCGEventRightMouseDown)
                        if action[2] else
                        (q.kCGEventLeftMouseUp if left else q.kCGEventRightMouseUp))
                event = q.CGEventCreateMouseEvent(None, kind, point, button)
                if action[2]:
                    buttons.add(action[1])
                else:
                    buttons.discard(action[1])
            else:
                event = q.CGEventCreateScrollWheelEvent(None, q.kCGScrollEventUnitLine,
                                                       1, action[1] // 120)
            q.CGEventSetFlags(event, 0)  # mode modifiers must not become Cmd/Option-clicks
            q.CGEventPost(q.kCGHIDEventTap, event)

    def callback(proxy, kind, event, context):
        if kind in (q.kCGEventTapDisabledByTimeout, q.kCGEventTapDisabledByUserInput):
            # Stop rather than continue with stale modifier/button state.
            failed.append(RuntimeError("macOS disabled the input tap; restart the application"))
            return event
        result = None
        try:
            code = q.CGEventGetIntegerValueField(event, q.kCGKeyboardEventKeycode)
            if kind == q.kCGEventFlagsChanged:
                # Caps Lock is toggle state, not reliable physical down/up. Pass it
                # and Fn through; use configured physical modifier keys instead.
                if code not in MAC_MODIFIERS:
                    return event
                down = mac_modifier_down(code, q.CGEventGetFlags(event))
            else:
                down = kind == q.kCGEventKeyDown
            scan, extended = mac_key(code)
            result = engine.handle(scan, extended, down, time.monotonic())
            emit(result.actions)
            if result.suppress:
                return None
            # Physical mode modifiers may still appear in later event flags even
            # though their down event was consumed. Preserve the opposite side.
            from keycodes import mac_visible_flags
            visible = {k for k, consumed in engine.held.items() if not consumed}
            flags = mac_visible_flags(q.CGEventGetFlags(event), settings.mode_keys, visible)
            q.CGEventSetFlags(event, flags)
            return event
        except Exception as exc:
            failed.append(exc)
            return None if result is not None and result.suppress else event

    mask = sum(1 << kind for kind in
               (q.kCGEventKeyDown, q.kCGEventKeyUp, q.kCGEventFlagsChanged))
    tap = q.CGEventTapCreate(q.kCGHIDEventTap, q.kCGHeadInsertEventTap,
                            q.kCGEventTapOptionDefault, mask, callback, None)
    if tap is None:
        raise RuntimeError("Cannot create event tap; check Accessibility and Input Monitoring permissions")
    source = CFMachPortCreateRunLoopSource(None, tap, 0)
    loop = CFRunLoopGetCurrent()
    CFRunLoopAddSource(loop, source, kCFRunLoopCommonModes)
    q.CGEventTapEnable(tap, True)
    print(f"Hold a configured mode key {sorted(settings.mode_keys)} to point.")
    print("Default: left Option / right Command. Release all mode keys to type. Ctrl+C: stop.")
    if dry_run:
        print("DRY RUN: pointing keys suppressed; mouse output printed only.")
    try:
        while not failed:
            CFRunLoopRunInMode(kCFRunLoopDefaultMode, 0.005, False)
            emit(engine.tick(time.monotonic()))
            if pending:
                actions, pending[:] = tuple(pending), []
                for action in actions:
                    print(action)
        raise failed[0]
    finally:
        q.CGEventTapEnable(tap, False)
        CFRunLoopRemoveSource(loop, source, kCFRunLoopCommonModes)
        CFMachPortInvalidate(tap)
        releases = {a[1] for a in engine.reset()} | buttons
        for button in sorted(releases):
            emit((("button", button, False),))

