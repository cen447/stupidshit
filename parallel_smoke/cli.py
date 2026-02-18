#!/usr/bin/env python3
"""Cross-platform command wrappers for the quote smoke bot."""

from __future__ import annotations

import contextlib
import io
import os
import re
import sys
import threading
import time
from collections.abc import Callable
from collections.abc import Sequence


STRICT_DEFAULTS = [
    "--concurrency",
    "1",
    "--progress-every",
    "1",
    "--run-retries",
    "0",
    "--checkpoint-grace-ms",
    "10000",
    "--ready-timeout-ms",
    "30000",
]

ANIMATION_FRAMES: list[tuple[list[str], str]] = [
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                      O     ",
            "8==D                                                 /|\\    ",
            "                                                     / \\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "incoming...",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                      O     ",
            "      8==D                                           /|\\    ",
            "                                                     / \\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "incoming...",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                      O     ",
            "                  8==D                               /|\\    ",
            "                                                     / \\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "incoming...",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                      O     ",
            "                              8==D                   /|\\    ",
            "                                                     / \\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "incoming...",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                      O     ",
            "                                          8==D       /|\\    ",
            "                                                     / \\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "oh no...",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                       *    ",
            "                                                      ***   ",
            "                                                       *    ",
            "                                                    /  \\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "sending hawai lullay",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                            ",
            "                                                    O-/|    ",
            "                                                      |\\    ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "ooooooof...",
    ),
    (
        [
            "                                                     Asad   ",
            "                                                      ^     ",
            "                                                            ",
            "                                                            ",
            "                                                    _O/\\__  ",
            "------------------------------------------------------------",
            "                                                            ",
            "                                                            ",
        ],
        "x_x  ...rebooting dignity...",
    ),
]


def _default_browsers_path() -> str:
    if sys.platform.startswith("win"):
        local_appdata = os.getenv("LOCALAPPDATA")
        if local_appdata:
            return os.path.join(local_appdata, "ms-playwright")
        return os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Caches/ms-playwright")
    return os.path.expanduser("~/.cache/ms-playwright")


def _ensure_playwright_env() -> str:
    path = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "").strip() or _default_browsers_path()
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = path
    os.makedirs(path, exist_ok=True)
    return path


def _normalize_exit_code(code: object) -> int:
    if code is None:
        return 0
    if isinstance(code, int):
        return code
    return 1


def _extract_exit_message(code: object) -> str:
    if code is None or isinstance(code, int):
        return ""
    return str(code).strip()


def _is_missing_browser_error(message: str) -> bool:
    lowered = message.lower()
    return (
        "executable doesn't exist" in lowered
        and "chromium" in lowered
        and "playwright" in lowered
    ) or "download new browsers" in lowered


def _install_chromium() -> int:
    path = _ensure_playwright_env()
    print(f"Chromium not found. Installing Playwright Chromium once to: {path}")
    original_argv = sys.argv[:]
    try:
        from playwright.__main__ import main as playwright_main

        sys.argv = ["playwright", "install", "chromium"]
        playwright_main()
        return 0
    except SystemExit as exc:
        return _normalize_exit_code(exc.code)
    except Exception as exc:  # noqa: BLE001 - surface install issues to caller
        print(f"Unable to install Chromium: {exc}", file=sys.stderr)
        return 1
    finally:
        sys.argv = original_argv


def _enable_windows_vt_mode() -> bool:
    if not sys.platform.startswith("win"):
        return True

    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        stdout_handle = kernel32.GetStdHandle(-11)
        if stdout_handle in (0, -1):
            return False

        mode = ctypes.c_uint()
        if kernel32.GetConsoleMode(stdout_handle, ctypes.byref(mode)) == 0:
            return False

        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        if mode.value & ENABLE_VIRTUAL_TERMINAL_PROCESSING:
            return True

        return bool(
            kernel32.SetConsoleMode(
                stdout_handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            )
        )
    except Exception:
        return False


def _run_captured(func: Callable[[], int]) -> tuple[int, str]:
    output_buffer = io.StringIO()
    with contextlib.redirect_stdout(output_buffer), contextlib.redirect_stderr(
        output_buffer
    ):
        code = func()
    return code, output_buffer.getvalue()


def _run_quote_smoke_with_animation(bot_args: Sequence[str]) -> int:
    console = getattr(sys, "__stdout__", sys.stdout)
    if console is None or not console.isatty():
        return _run_quote_smoke(bot_args)
    if not _enable_windows_vt_mode():
        return _run_quote_smoke(bot_args)

    result: dict[str, object] = {"code": 1, "log": ""}

    def _worker() -> None:
        code, log = _run_captured(lambda: _run_quote_smoke(bot_args))
        result["code"] = code
        result["log"] = log

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()

    frame_index = 0
    lines_per_frame = len(ANIMATION_FRAMES[0][0]) + 1
    drew_frame = False

    console.write("\x1b[?25l")
    try:
        while worker.is_alive():
            lines, status = ANIMATION_FRAMES[frame_index % len(ANIMATION_FRAMES)]
            if drew_frame:
                console.write(f"\x1b[{lines_per_frame}A")

            for line in lines:
                console.write(f"\x1b[2K{line}\n")
            console.write(f"\x1b[2K{status}\n")
            console.flush()

            drew_frame = True
            frame_index += 1
            time.sleep(0.11)

        worker.join()
    finally:
        console.write("\x1b[?25h")
        if drew_frame:
            console.write(f"\x1b[{lines_per_frame}A")
            for _ in range(lines_per_frame):
                console.write("\x1b[2K\n")
            console.write(f"\x1b[{lines_per_frame}A")
        console.flush()

    log_text = str(result.get("log", ""))
    if log_text:
        console.write(log_text)
        if not log_text.endswith("\n"):
            console.write("\n")
        console.flush()

    return int(result.get("code", 1))


def _run_quote_smoke(bot_args: Sequence[str]) -> int:
    _ensure_playwright_env()
    from quote_smoke_bot import main as quote_main

    original_argv = sys.argv[:]
    sys.argv = ["quote_smoke_bot.py", *bot_args]
    try:
        quote_main()
        return 0
    except SystemExit as exc:
        message = _extract_exit_message(exc.code)
        if message and _is_missing_browser_error(message):
            if _install_chromium() != 0:
                print("Unable to install Chromium automatically.", file=sys.stderr)
                return 1
            try:
                quote_main()
                return 0
            except SystemExit as retry_exc:
                retry_message = _extract_exit_message(retry_exc.code)
                if retry_message:
                    print(retry_message, file=sys.stderr)
                return _normalize_exit_code(retry_exc.code)

        if message:
            print(message, file=sys.stderr)
        return _normalize_exit_code(exc.code)
    finally:
        sys.argv = original_argv


def parallel_smoke_main() -> None:
    raise SystemExit(_run_quote_smoke(sys.argv[1:]))


def fuck_main() -> None:
    args = sys.argv[1:]
    if not args or args[0] != "asad":
        print("Usage: fuck asad <runs> [additional flags]")
        raise SystemExit(1)

    runs = 1
    passthrough = args[1:]
    if passthrough and not passthrough[0].startswith("-"):
        run_text = passthrough[0]
        if not re.fullmatch(r"[0-9]+", run_text) or int(run_text) < 1:
            print("runs must be a positive integer", file=sys.stderr)
            raise SystemExit(1)
        runs = int(run_text)
        passthrough = passthrough[1:]

    print(f"Launching smoke run (runs={runs}, concurrency=1, strict mode).")
    bot_args = ["--runs", str(runs), *STRICT_DEFAULTS, *passthrough]
    raise SystemExit(_run_quote_smoke_with_animation(bot_args))
