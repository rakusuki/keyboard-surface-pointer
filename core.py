"""OS-independent physical-key gesture engine (no text or event logging)."""
from dataclasses import dataclass
import math

# PC set-1 scan codes, keyed by (scan code, extended flag).
# Unit = one standard key pitch. Rows include their physical horizontal offsets.
def key_positions(layout: str) -> dict[tuple[int, bool], tuple[float, float]]:
    if layout not in {"jis", "us"}:
        raise ValueError("layout must be jis or us")
    rows = [
        (0.0, 0.0, list(range(0x02, 0x0E))),
        (0.5, 1.0, list(range(0x10, 0x1C))),
        (0.75, 2.0, list(range(0x1E, 0x29))),
        (1.25, 3.0, list(range(0x2C, 0x36))),
    ]
    result = {}
    for offset, y, codes in rows:
        for column, code in enumerate(codes):
            result[(code, False)] = (offset + column, y)
    result[(0x29, False)] = (-1.0, 0.0)  # US ` / JIS 半角全角
    result[(0x2B, False)] = (12.5, 1.0) if layout == "us" else (11.75, 2.0)
    if layout == "jis":
        result[(0x7D, False)] = (12.0, 0.0)  # ¥
        result[(0x73, False)] = (11.25, 3.0)  # ろ
    return result


@dataclass(frozen=True)
class Settings:
    layout: str = "jis"
    mode_scan: int = 0x3A  # Caps Lock
    gain: float = 32.0
    precision_gain: float = 4.0
    stroke_timeout: float = 0.45
    max_step: float = 3.0
    restart_distance: float = 2.0
    hold_delay: float = 0.25
    hold_speed: float = 320.0
    precision_hold_speed: float = 40.0

    def __post_init__(self) -> None:
        key_positions(self.layout)
        if isinstance(self.mode_scan, bool) or not isinstance(self.mode_scan, int):
            raise ValueError("mode_scan must be an integer")
        # Keep controls and movement keys distinct; F8 is an alternative.
        if self.mode_scan not in {0x3A, 0x42}:
            raise ValueError("mode_scan must be 58 (Caps Lock) or 66 (F8)")
        for name in ("gain", "precision_gain", "stroke_timeout", "max_step",
                     "restart_distance", "hold_delay", "hold_speed", "precision_hold_speed"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a number")
            if not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.precision_hold_speed > self.hold_speed:
            raise ValueError("precision_hold_speed must not exceed hold_speed")
        if self.precision_gain > self.gain:
            raise ValueError("precision_gain must not exceed gain")


@dataclass(frozen=True)
class Result:
    suppress: bool
    actions: tuple[tuple, ...] = ()


class Engine:
    """Track key-down ownership so forwarded downs always receive their ups."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.positions = key_positions(settings.layout)
        self.held: dict[tuple[int, bool], bool] = {}  # value = suppressed down
        self.active = False
        self.anchor: tuple[float, float] | None = None
        self.last_time = 0.0
        self.buttons: set[str] = set()
        self.direction: tuple[float, float] | None = None
        self.motion_key: tuple[int, bool] | None = None
        self.tick_time = 0.0
        self.continuing = False
        self.remainder = (0.0, 0.0)

    def clear_motion(self) -> None:
        self.anchor = None
        self.direction = None
        self.motion_key = None
        self.continuing = False
        self.remainder = (0.0, 0.0)

    def tick(self, now: float) -> tuple[tuple, ...]:
        """Continue the last direction only while its final key remains held."""
        if not self.active or self.direction is None or self.motion_key not in self.held:
            return ()
        start = self.last_time + self.settings.hold_delay
        if now <= start:
            return ()
        dt = max(0.0, min(0.05, now - max(start, self.tick_time)))
        self.tick_time = now
        self.continuing = True
        precision = any(self.held.get((s, False), False) for s in (0x2A, 0x36))
        speed = self.settings.precision_hold_speed if precision else self.settings.hold_speed
        x = self.direction[0] * speed * dt + self.remainder[0]
        y = self.direction[1] * speed * dt + self.remainder[1]
        dx, dy = math.trunc(x), math.trunc(y)
        self.remainder = (x - dx, y - dy)
        return (("move", dx, dy),) if dx or dy else ()

    def reset(self) -> tuple[tuple, ...]:
        actions = tuple(("button", button, False) for button in sorted(self.buttons))
        self.buttons.clear()
        self.active = False
        self.clear_motion()
        return actions

    def handle(self, scan: int, extended: bool, down: bool, now: float) -> Result:
        key = (scan, extended)
        mode = (self.settings.mode_scan, False)
        if not down:
            suppressed = self.held.pop(key, False)
            if key == self.motion_key:
                if self.continuing:
                    self.clear_motion()
                else:
                    self.motion_key = None
            if key == mode:
                return Result(suppressed, self.reset())
            if suppressed and key in {(0x39, False), (0x1C, False)}:
                button = "left" if scan == 0x39 else "right"
                if button in self.buttons:
                    self.buttons.remove(button)
                    return Result(True, (("button", button, False),))
            return Result(suppressed)
        if key in self.held:  # OS auto-repeat is not finger motion
            return Result(self.held[key])
        if key == mode:
            # Avoid Ctrl/Alt/Win or previously typed keys affecting mouse actions.
            self.active = not self.held
            self.clear_motion()
            self.held[key] = True
            return Result(True)
        self.held[key] = self.active
        if not self.active:
            return Result(False)
        if key == (0x01, False):  # Escape cancels until mode is released
            return Result(True, self.reset())
        if key in {(0x39, False), (0x1C, False)}:
            button = "left" if scan == 0x39 else "right"
            self.buttons.add(button)
            self.clear_motion()
            return Result(True, (("button", button, True),))
        if key in {(0x48, True), (0x50, True)}:
            self.clear_motion()
            return Result(True, (("scroll", 120 if scan == 0x48 else -120),))
        position = self.positions.get(key)
        if position is None:
            if key not in {(0x2A, False), (0x36, False)}:
                self.clear_motion()
            return Result(True)
        previous = self.anchor
        elapsed = now - self.last_time
        self.anchor = position
        self.last_time = now
        self.motion_key = key
        self.tick_time = now
        self.continuing = False
        self.remainder = (0.0, 0.0)
        if previous is None or elapsed < 0 or elapsed > self.settings.stroke_timeout:
            self.direction = None
            return Result(True)
        dx, dy = position[0] - previous[0], position[1] - previous[1]
        # Distant keys are ambiguous (another finger / repositioning): re-anchor.
        distance = math.hypot(dx, dy)
        if distance > self.settings.max_step:
            self.direction = None
            return Result(True)
        # A long return against the preceding direction begins a new stroke.
        # For J-K-L-J, L-J resets the anchor instead of undoing rightward motion.
        if (self.direction is not None and distance >= self.settings.restart_distance
                and dx * self.direction[0] + dy * self.direction[1] < 0):
            self.direction = None
            return Result(True)
        if distance == 0:
            self.direction = None
            return Result(True)
        self.direction = (dx / distance, dy / distance)
        precision = any(self.held.get((s, False), False) for s in (0x2A, 0x36))
        gain = self.settings.precision_gain if precision else self.settings.gain
        return Result(True, (("move", round(dx * gain), round(dy * gain)),))
