"""Windows desktop backend. Run with Python 3.10+ on Windows 10/11."""
import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import time

from core import Engine, Settings


def load_settings(path: Path) -> Settings:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return Settings(**data)


def run(settings: Settings, dry_run: bool, check_backend: bool = False) -> None:
    # This importable module also supports engine tests on non-Windows systems.
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    ULONG_PTR = ctypes.c_size_t
    LRESULT = ctypes.c_ssize_t
    HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

    class KBDLLHOOKSTRUCT(ctypes.Structure):
        _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                    ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                    ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD),
                    ("dwExtraInfo", ULONG_PTR)]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [("uMsg", wintypes.DWORD), ("wParamL", wintypes.WORD),
                    ("wParamH", wintypes.WORD)]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("payload",)
        _fields_ = [("type", wintypes.DWORD), ("payload", INPUTUNION)]

    # Explicit signatures prevent pointer truncation on 64-bit Windows.
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = wintypes.HANDLE
    user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = LRESULT
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
    user32.SendInput.restype = wintypes.UINT
    user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND,
                                    wintypes.UINT, wintypes.UINT, wintypes.UINT]
    user32.PeekMessageW.restype = wintypes.BOOL
    user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
    user32.DispatchMessageW.restype = LRESULT
    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = ctypes.c_short
    user32.MapVirtualKeyW.argtypes = [wintypes.UINT, wintypes.UINT]
    user32.MapVirtualKeyW.restype = wintypes.UINT
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    if check_backend:
        expected = 40 if ctypes.sizeof(ctypes.c_void_p) == 8 else 28
        if ctypes.sizeof(INPUT) != expected:
            raise ValueError("Unexpected Windows INPUT structure size")
        print(f"Windows API loaded; INPUT size = {expected}; no hook or mouse events sent.")
        return

    engine = Engine(settings)
    # Account for keys held before startup, including left/right modifiers.
    for vk in range(1, 256):
        if vk in {0x10, 0x11, 0x12} or vk < 8:  # skip aggregate modifiers / mouse buttons
            continue
        if user32.GetAsyncKeyState(vk) & 0x8000:
            code = user32.MapVirtualKeyW(vk, 4)  # MAPVK_VK_TO_VSC_EX
            if code:
                engine.held[(code & 0xFF, bool(code & 0xFF00))] = False
    failed = []
    hook = None
    button_flags = {("left", True): 0x0002, ("left", False): 0x0004,
                    ("right", True): 0x0008, ("right", False): 0x0010}

    def emit(actions: tuple[tuple, ...]) -> None:
        for action in actions:
            if dry_run:
                # Avoid console I/O in the hook. Print only generated mouse actions later.
                pending.append(action)
                continue
            event = INPUT(type=0)
            if action[0] == "move":
                event.mi = MOUSEINPUT(action[1], action[2], 0, 0x0001, 0, 0)
            elif action[0] == "button":
                event.mi.dwFlags = button_flags[(action[1], action[2])]
            else:
                event.mi.dwFlags = 0x0800
                event.mi.mouseData = action[1] & 0xFFFFFFFF
            if user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(INPUT)) != 1:
                raise OSError(ctypes.get_last_error(), "SendInput failed; check target privileges")
            if action[0] == "button":
                if action[2]:
                    sent_buttons.add(action[1])
                else:
                    sent_buttons.discard(action[1])

    pending = []
    sent_buttons = set()

    @HOOKPROC
    def callback(ncode: int, wparam: int, lparam: int) -> int:
        if ncode < 0 or wparam not in {0x100, 0x101, 0x104, 0x105}:
            return user32.CallNextHookEx(hook, ncode, wparam, lparam)
        event = ctypes.cast(lparam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        if event.flags & 0x10:  # Do not consume injected input from other tools.
            return user32.CallNextHookEx(hook, ncode, wparam, lparam)
        result = None
        try:
            result = engine.handle(event.scanCode, bool(event.flags & 1),
                                   wparam in {0x100, 0x104}, time.monotonic())
            emit(result.actions)
            if result.suppress:
                return 1
        except Exception as exc:
            failed.append(exc)
            # Suppressed down must not become a typed character on output failure.
            if result is not None and result.suppress:
                return 1
        return user32.CallNextHookEx(hook, ncode, wparam, lparam)

    hook = user32.SetWindowsHookExW(13, callback, kernel32.GetModuleHandleW(None), 0)
    if not hook:
        raise ctypes.WinError(ctypes.get_last_error())
    print("Hold a configured mode key (default Caps Lock / right Alt) to point. Space: left/drag; Enter: right.")
    print("Repeat J-K-L strokes to move right; hold the final key to keep moving.")
    print("Shift: precision; arrows up/down: scroll; Esc: cancel mode; Ctrl+C: quit.")
    if dry_run:
        print("DRY RUN: mouse output disabled; mode keys are still suppressed.")
    message = wintypes.MSG()
    try:
        while not failed:
            while user32.PeekMessageW(ctypes.byref(message), None, 0, 0, 1):
                if message.message == 0x12:
                    return
                user32.TranslateMessage(ctypes.byref(message))
                user32.DispatchMessageW(ctypes.byref(message))
            emit(engine.tick(time.monotonic()))
            if pending:
                actions, pending[:] = tuple(pending), []
                for action in actions:
                    print(action)
            time.sleep(0.005)  # let Python process Ctrl+C without blocking GetMessage
        raise failed[0]
    finally:
        user32.UnhookWindowsHookEx(hook)
        # Try each button independently, even if an earlier release fails.
        releases = {action[1] for action in engine.reset()} | sent_buttons
        for button in sorted(releases):
            action = ("button", button, False)
            try:
                emit((action,))
            except OSError as exc:
                print(f"Mouse release failed: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.json"))
    parser.add_argument("--dry-run", action="store_true", help="print mouse actions without sending them")
    parser.add_argument("--check-backend", action="store_true", help="validate Windows API bindings without capturing input")
    args = parser.parse_args()
    if sys.platform != "win32":
        print("This prototype requires native Windows Python (not WSL).", file=sys.stderr)
        return 1
    try:
        run(load_settings(args.config), args.dry_run, args.check_backend)
    except KeyboardInterrupt:
        print("Stopped.")
    except (OSError, ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
