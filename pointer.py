"""Keyboard surface pointer: Windows, Ubuntu and macOS entry point."""
import argparse
import json
from pathlib import Path
import sys
import signal

from core import Settings


def load_settings(path: Path) -> Settings:
    with path.open(encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return Settings(**data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check-backend", action="store_true")
    parser.add_argument("--list-devices", action="store_true", help="Ubuntu: list keyboard event devices")
    parser.add_argument("--device", help="Ubuntu: explicit /dev/input/eventN keyboard")
    args = parser.parse_args()
    def stop_on_term(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop_on_term)
    config = args.config or Path(__file__).with_name(
        "config.macos.json" if sys.platform == "darwin" else "config.json")
    try:
        if sys.platform == "win32":
            from windows_backend import run
            if args.list_devices or args.device:
                parser.error("--device and --list-devices are Ubuntu-only")
            run(load_settings(config), args.dry_run, args.check_backend)
        elif sys.platform.startswith("linux"):
            from ubuntu_backend import run
            run(load_settings(config), args.dry_run, args.check_backend,
                args.device, args.list_devices)
        elif sys.platform == "darwin":
            from macos_backend import run
            if args.list_devices or args.device:
                parser.error("--device and --list-devices are Ubuntu-only")
            run(load_settings(config), args.dry_run, args.check_backend)
        else:
            raise ValueError("Supported systems: Windows, Ubuntu Linux and macOS")
    except KeyboardInterrupt:
        print("Stopped.")
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Install requirements for your OS; see README.", file=sys.stderr)
        return 1
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
