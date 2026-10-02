"""Ubuntu evdev/uinput backend; explicit keyboard selection and exclusive grab."""
import select
import time

from core import Engine
from keycodes import linux_key

VIRTUAL_PREFIX = "keyboard-surface-pointer"


def run(settings, dry_run=False, check_backend=False, device_path=None, list_devices=False):
    from evdev import InputDevice, UInput, ecodes as ec, list_devices as event_paths

    def is_keyboard(device):
        keys = device.capabilities().get(ec.EV_KEY, [])
        return ec.KEY_J in keys and ec.KEY_K in keys and ec.KEY_ENTER in keys

    if list_devices:
        for path in event_paths():
            try:
                with InputDevice(path) as dev:
                    if is_keyboard(dev) and not dev.name.startswith(VIRTUAL_PREFIX):
                        print(f"{path}: {dev.name}")
            except PermissionError:
                print(f"{path}: permission denied (try sudo)")
        return
    if check_backend:
        print("evdev imported. No input device grabbed or virtual device created.")
        print("Runtime also requires access to the selected /dev/input/eventN and /dev/uinput.")
        return
    if not device_path:
        raise ValueError("Select a keyboard: --list-devices, then --device /dev/input/eventN")
    with InputDevice(device_path) as device:
        if device.name.startswith(VIRTUAL_PREFIX) or not is_keyboard(device):
            raise ValueError("Select a physical keyboard, not a virtual device")
        if device.active_keys():
            raise ValueError("Release all keyboard keys before starting and try again")
        keys = device.capabilities()[ec.EV_KEY]
        capabilities = {ec.EV_KEY: list(set(keys + [ec.BTN_LEFT, ec.BTN_RIGHT])),
                        ec.EV_REL: [ec.REL_X, ec.REL_Y, ec.REL_WHEEL]}
        with UInput(capabilities, name=VIRTUAL_PREFIX + " virtual input") as output:
            engine = Engine(settings)
            forwarded = set()
            pressed_buttons = set()
            buttons = {"left": ec.BTN_LEFT, "right": ec.BTN_RIGHT}

            def emit(actions):
                for action in actions:
                    if dry_run:
                        print(action)
                        continue
                    if action[0] == "move":
                        output.write(ec.EV_REL, ec.REL_X, action[1])
                        output.write(ec.EV_REL, ec.REL_Y, action[2])
                    elif action[0] == "scroll":
                        output.write(ec.EV_REL, ec.REL_WHEEL, action[1] // 120)
                    else:
                        button = buttons[action[1]]
                        output.write(ec.EV_KEY, button, int(action[2]))
                        if action[2]:
                            pressed_buttons.add(button)
                        else:
                            pressed_buttons.discard(button)
                    output.syn()

            print(f"Keyboard: {device.name}. Hold Caps Lock/F8 to point; release to type.")
            print("Ctrl+C: stop. Ctrl+Alt+Esc: emergency stop on the selected keyboard.")
            if dry_run:
                print("DRY RUN: pointing keys suppressed; mouse events printed only.")
            grabbed = False
            try:
                device.grab()
                grabbed = True
                # Recheck the small race between the first held-key check and grab.
                if device.active_keys():
                    raise ValueError("A key was pressed during startup; release keys and retry")
                while True:
                    readable, _, _ = select.select([device], [], [], 0.005)
                    if readable:
                        for event in device.read():
                            if event.type == ec.EV_SYN and event.code == ec.SYN_DROPPED:
                                raise RuntimeError("Input events were dropped; stopping to restore keyboard control")
                            if event.type != ec.EV_KEY:
                                continue
                            scan, extended = linux_key(event.code)
                            result = engine.handle(scan, extended, event.value != 0, time.monotonic())
                            # Always available, even when Ctrl+C cannot reach a terminal.
                            held = engine.held
                            if ((0x01, False) in held
                                    and any((x, False) in held for x in (0x1D,))
                                    and ((0x38, False) in held or (0x38, True) in held)):
                                return
                            emit(result.actions)
                            if not result.suppress:
                                output.write(ec.EV_KEY, event.code, event.value)
                                output.syn()
                                if event.value:
                                    forwarded.add(event.code)
                                else:
                                    forwarded.discard(event.code)
                    emit(engine.tick(time.monotonic()))
            finally:
                # Release virtual keys before restoring the physical keyboard.
                try:
                    for code in forwarded | pressed_buttons:
                        output.write(ec.EV_KEY, code, 0)
                    output.syn()
                    engine.reset()
                finally:
                    if grabbed:
                        device.ungrab()
