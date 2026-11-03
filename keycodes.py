"""Normalize platform physical key codes to the existing PC set-1 engine."""

LINUX_SPECIAL = {
    96: (0x1C, True), 97: (0x1D, True), 98: (0x35, True),
    100: (0x38, True), 102: (0x47, True), 103: (0x48, True),
    104: (0x49, True), 105: (0x4B, True), 106: (0x4D, True),
    107: (0x4F, True), 108: (0x50, True), 109: (0x51, True),
    110: (0x52, True), 111: (0x53, True), 125: (0x5B, True),
    126: (0x5C, True), 127: (0x5D, True), 89: (0x73, False),
    124: (0x7D, False),
}

# macOS virtual key codes identify physical keys, independent of typed text.
MAC_CODES = {
    0: 0x1E, 1: 0x1F, 2: 0x20, 3: 0x21, 4: 0x23, 5: 0x22,
    6: 0x2C, 7: 0x2D, 8: 0x2E, 9: 0x2F, 11: 0x30,
    12: 0x10, 13: 0x11, 14: 0x12, 15: 0x13, 16: 0x15, 17: 0x14,
    18: 0x02, 19: 0x03, 20: 0x04, 21: 0x05, 22: 0x07, 23: 0x06,
    24: 0x0D, 25: 0x0A, 26: 0x08, 27: 0x0C, 28: 0x09, 29: 0x0B,
    30: 0x1B, 31: 0x18, 32: 0x16, 33: 0x1A, 34: 0x17, 35: 0x19,
    36: 0x1C, 37: 0x26, 38: 0x24, 39: 0x28, 40: 0x25, 41: 0x27,
    42: 0x2B, 43: 0x33, 44: 0x35, 45: 0x31, 46: 0x32, 47: 0x34,
    48: 0x0F, 49: 0x39, 50: 0x29, 51: 0x0E, 53: 0x01,
    56: 0x2A, 58: 0x38, 59: 0x1D, 60: 0x36,
    93: 0x7D, 94: 0x73, 100: 0x42,  # JIS ¥, ろ, F8
}
MAC_EXTENDED = {
    54: 0x5C, 55: 0x5B, 61: 0x38, 62: 0x1D, 76: 0x1C,
    123: 0x4B, 124: 0x4D, 125: 0x50, 126: 0x48,
}
MAC_MODIFIERS = {54, 55, 56, 58, 59, 60, 61, 62}


def linux_key(code: int) -> tuple[int, bool]:
    if code in LINUX_SPECIAL:
        return LINUX_SPECIAL[code]
    if 1 <= code <= 83:
        return code, False
    return 0x1000 + code, False


def mac_key(code: int) -> tuple[int, bool]:
    if code in MAC_EXTENDED:
        return MAC_EXTENDED[code], True
    return MAC_CODES.get(code, 0x2000 + code), False


def mac_visible_flags(flags: int, modes, visible_keys) -> int:
    """Remove reserved modifier flags, preserving a forwarded opposite side."""
    families = (
        (0x80000, ((0x38, False), (0x38, True)), (0x20, 0x40)),
        (0x100000, ((0x5B, True), (0x5C, True)), (0x08, 0x10)),
    )
    for aggregate, keys, device_flags in families:
        if any(key in modes for key in keys):
            for key, flag in zip(keys, device_flags):
                if key in modes and key not in visible_keys:
                    flags &= ~flag
            if not any(key in visible_keys for key in keys):
                flags &= ~aggregate
    return flags



def mac_modifier_down(code: int, flags: int) -> bool:
    """Read the event's side-specific state, not a later HID snapshot.

    Aggregate Command/Option flags cannot distinguish opposite-side releases.
    Quartz flagsChanged events carry the device-dependent side bits too.
    """
    side_flags = {54: 0x10, 55: 0x08, 56: 0x02, 60: 0x04,
                  58: 0x20, 61: 0x40, 59: 0x01, 62: 0x2000}
    return bool(flags & side_flags[code])
