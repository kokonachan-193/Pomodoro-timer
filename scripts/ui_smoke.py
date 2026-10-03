"""Headless GUI smoke test for Aqua Focus release gating.

Covers the v2.1.2-style Home, responsive presets, secondary windows,
legacy full controls, animation extensions, and the immersive Focus lifecycle
without network/audio.
"""

from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
import tempfile

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from main import WaterTimer  # noqa: E402


def close_new_toplevels(app: WaterTimer, before: set[str]) -> None:
    app.update_idletasks()
    for child in list(app.winfo_children()):
        try:
            if isinstance(child, tk.Toplevel) and str(child) not in before:
                child.destroy()
        except Exception:
            pass
    app.update_idletasks()


def open_and_close(app: WaterTimer, callback, name: str) -> None:
    before = {str(x) for x in app.winfo_children()}
    callback()
    app.update()
    close_new_toplevels(app, before)
    print(f"[smoke] OK: {name}")


def main() -> int:
    app = WaterTimer()
    app.geometry("1120x820+0+0")
    app.update()

    shell = app.minimal_shell
    assert shell.surface is not None and shell.surface.winfo_exists(), "minimal Home missing"
    assert shell.start_button is not None and shell.start_button.winfo_exists(), "Start button missing"
    assert shell.intent_entry is not None and shell.intent_entry.winfo_exists(), "intention input missing"

    # Presets previously triggered stale CTkEntry crashes; exercise every chip.
    for preset in ("25", "50", "90", "50"):
        shell.select_duration(preset)
        app.update()
    print("[smoke] OK: duration presets")

    # Animation pack must be registered as Extensions, not hard-coded hidden UI.
    expected_fx = {
        "animation-rising-water",
        "animation-sakura-petals",
        "animation-rain-window",
        "animation-snowfall",
        "animation-fireflies",
        "animation-aquarium-fish",
    }
    installed_fx = {str(x.get("id")) for x in app.workspace.installed_extensions}
    missing_fx = expected_fx - installed_fx
    assert not missing_fx, f"missing animation extensions: {sorted(missing_fx)}"
    print("[smoke] OK: animation extensions registered")

    # Core secondary surfaces.
    checks = [
        (app.workspace.open_tasks, "Tasks"),
        (app.workspace.open_stats, "Stats"),
        (app.workspace.open_soundscape, "Ambient sound"),
        (app.workspace.open_extensions, "Extensions"),
        (app.v2_modes.open_countdown, "Countdown"),
        (app.v2_modes.open_stopwatch, "Stopwatch"),
        (app.v2_modes.open_alarm, "Alarm"),
        (shell.open_custom_session, "Custom session"),
        (shell.open_music_library, "Music library"),
        (shell.open_settings, "Settings"),
        (shell.open_tools, "More menu"),
    ]
    for callback, name in checks:
        open_and_close(app, callback, name)

    # Full legacy controls must remain reachable and reversible.
    shell.open_advanced_workspace()
    app.update()
    assert app.setup_frame.winfo_ismapped(), "full controls did not open"
    shell.close_advanced_workspace()
    app.update()
    assert shell.surface.winfo_ismapped(), "clean Home did not restore"
    print("[smoke] OK: Full controls round-trip")

    # Focus-time background must render from the selected/custom image.
    with tempfile.TemporaryDirectory() as tmp:
        bg_path = Path(tmp) / "focus-bg.png"
        Image.new("RGB", (320, 200), (24, 52, 78)).save(bg_path)
        app._custom_bg_path = str(bg_path)
        app._set_background_image(str(bg_path), label="focus-bg.png")
        assert app._bg_src is not None, "custom focus background failed to load"

        # Focus start / pause / resume / stop, including background + water renderer.
        shell.intent_entry.delete(0, tk.END)
        shell.intent_entry.insert(0, "Release smoke test")
        shell.start_focus()
        app.update()
        assert app.wave_frame.winfo_ismapped(), "Focus screen did not open"
        assert app.is_running, "timer did not start"
        app.remaining_seconds = max(1.0, app.total_seconds * 0.58)
        app.draw_waves(frozen=True)
        assert app._bg_photo is not None, "Focus background was not rendered"
        app.toggle_pause()
        app.update()
        assert app.is_paused, "pause failed"
        app.toggle_pause()
        app.update()
        assert not app.is_paused, "resume failed"
        app.stop_timer()
        app.update()
        assert app.main_container.winfo_ismapped(), "Home did not return after stop"
        print("[smoke] OK: Focus lifecycle + background + water progress")

    app.destroy()
    print("[smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
