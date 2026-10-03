"""Desktop runtime fixes for Aqua Focus.

Loaded early by either:
- sitecustomize.py during source runs, or
- pyinstaller_runtime_hook.py inside packaged desktop builds.

v2.1.9 hotfix goals:
- Focus animation extensions must be visibly reflected while Focus is running.
- Installing/removing extension animations should not require restarting Focus.
- Reduce Motion should calm extension FX, not make every enabled FX look absent.
- GUI resize/theme/focus-stop glitches should fail safe instead of breaking Tk.
"""

from __future__ import annotations

import json
import math
import time
from pathlib import Path

_PATCHED = False


# ---------------------------------------------------------------------------
# Tiny safety helpers


def _widget_alive(widget) -> bool:
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _call_on_ui(root, callback, delay: int = 0) -> None:
    if _widget_alive(root):
        try:
            root.after(max(0, int(delay)), callback)
            return
        except Exception:
            pass
    _safe_call(callback)


def _hex_to_rgb(value: str, fallback=(120, 210, 230)) -> tuple[int, int, int]:
    try:
        v = str(value or "").strip().lstrip("#")
        if len(v) == 3:
            v = "".join(ch * 2 for ch in v)
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


def _blend_hex(a: str, b: str, amount: float) -> str:
    ar, ag, ab = _hex_to_rgb(a, (10, 20, 28))
    br, bg, bb = _hex_to_rgb(b, (120, 220, 235))
    x = max(0.0, min(1.0, float(amount)))
    return "#%02x%02x%02x" % (
        int(ar + (br - ar) * x),
        int(ag + (bg - ag) * x),
        int(ab + (bb - ab) * x),
    )


# ---------------------------------------------------------------------------
# Workspace extension state: normalize, reload, notify visible Focus redraw.


def _install_workspace_patch() -> None:
    from v2_workspace import AmbientMixer, SessionStats, TaskStore, WorkspacePanels

    if getattr(WorkspacePanels, "_pc_runtime_fixed", False):
        return

    builtin_by_id = {str(item.get("id")): dict(item) for item in WorkspacePanels.BUILTIN_ANIMATIONS}

    def _normalize_extension(self, item):
        if isinstance(item, str):
            ext = dict(builtin_by_id.get(item, {"id": item, "name": item}))
            ext.setdefault("type", "animation" if item.startswith("animation-") else "extension")
            ext.setdefault("enabled", True)
            return ext
        if not isinstance(item, dict):
            return None
        eid = str(item.get("id", "")).strip()
        if not eid:
            return None
        ext = dict(builtin_by_id.get(eid, {}))
        ext.update(item)
        ext["id"] = eid
        ext.setdefault("type", "animation" if eid.startswith("animation-") else "extension")
        ext["enabled"] = bool(ext.get("enabled", True))
        return ext

    def _load_installed(self):
        try:
            raw = json.loads(self.installed_extensions_path.read_text(encoding="utf-8"))
        except Exception:
            return []
        if isinstance(raw, dict):
            if isinstance(raw.get("installed"), list):
                raw = raw.get("installed")
            elif isinstance(raw.get("extensions"), list):
                raw = raw.get("extensions")
            else:
                raw = list(raw.values())
        if not isinstance(raw, list):
            return []
        out = []
        seen = set()
        for row in raw:
            ext = _normalize_extension(self, row)
            if not ext:
                continue
            eid = ext["id"]
            if eid in seen:
                continue
            seen.add(eid)
            out.append(ext)
        return out

    def _save_installed(self):
        try:
            normalized = []
            seen = set()
            for row in self.installed_extensions:
                ext = _normalize_extension(self, row)
                if not ext or ext["id"] in seen:
                    continue
                seen.add(ext["id"])
                normalized.append(ext)
            self.installed_extensions = normalized
            self.installed_extensions_path.parent.mkdir(parents=True, exist_ok=True)
            self.installed_extensions_path.write_text(
                json.dumps(self.installed_extensions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            try:
                self._extensions_mtime = self.installed_extensions_path.stat().st_mtime
            except Exception:
                self._extensions_mtime = time.time()
        except Exception:
            pass
        _notify_extension_change(self)

    def _reload_extensions_if_needed(self, force: bool = False):
        try:
            mtime = self.installed_extensions_path.stat().st_mtime
        except Exception:
            mtime = 0.0
        if force or mtime != getattr(self, "_extensions_mtime", None):
            self.installed_extensions = _load_installed(self)
            self._extensions_mtime = mtime
        return self.installed_extensions

    def extension_enabled(self, extension_id: str) -> bool:
        eid = str(extension_id)
        for ext in _reload_extensions_if_needed(self):
            if str(ext.get("id")) == eid:
                return bool(ext.get("enabled", True))
        return False

    def enabled_animation_ids(self) -> set[str]:
        return {
            str(ext.get("id"))
            for ext in _reload_extensions_if_needed(self)
            if str(ext.get("type")) == "animation" and bool(ext.get("enabled", True))
        }

    def _notify_extension_change(self) -> None:
        root = getattr(self, "root", None)
        if root is None:
            return

        def redraw():
            _safe_call(_reload_extensions_if_needed, self, True)
            try:
                if callable(getattr(root, "draw_waves", None)):
                    root.draw_waves(frozen=bool(getattr(root, "is_paused", False)))
                shell = getattr(root, "minimal_shell", None)
                if shell is not None and callable(getattr(shell, "refresh_background", None)):
                    shell.refresh_background()
                if callable(getattr(root, "_place_secondary_chrome", None)):
                    root._place_secondary_chrome()
                root._focus_fx_revision = time.time()
            except Exception:
                pass

        _call_on_ui(root, redraw)

    def __init__(self, root, *, data_dir: Path, theme_getter, font_family: str, font_bold: str):
        self.root = root
        self.theme_getter = theme_getter
        self.font_family = font_family
        self.font_bold = font_bold
        self.tasks = TaskStore(data_dir / "tasks.json")
        self.stats = SessionStats(data_dir / "sessions.json")
        self.ambient = AmbientMixer()
        self.current_task = ""
        self.installed_extensions_path = data_dir / "extensions.json"
        existed = self.installed_extensions_path.exists()
        self.installed_extensions = _load_installed(self)
        try:
            self._extensions_mtime = self.installed_extensions_path.stat().st_mtime if existed else 0.0
        except Exception:
            self._extensions_mtime = 0.0
        # First run gets visible animation defaults. After that, respect removals.
        if not existed and not any(str(x.get("type")) == "animation" for x in self.installed_extensions):
            self.installed_extensions.extend(dict(x, enabled=True) for x in self.BUILTIN_ANIMATIONS)
            _save_installed(self)

    WorkspacePanels.__init__ = __init__
    WorkspacePanels._load_installed = _load_installed
    WorkspacePanels._save_installed = _save_installed
    WorkspacePanels.reload_extensions_if_needed = _reload_extensions_if_needed
    WorkspacePanels.extension_enabled = extension_enabled
    WorkspacePanels.enabled_animation_ids = enabled_animation_ids
    WorkspacePanels._notify_extension_change = _notify_extension_change
    WorkspacePanels._pc_runtime_fixed = True


# ---------------------------------------------------------------------------
# Focus drawing patch: keep original scene, then add a visible extension layer.


def _workspace_enabled(workspace, extension_id: str) -> bool:
    try:
        if hasattr(workspace, "reload_extensions_if_needed"):
            workspace.reload_extensions_if_needed()
        return bool(workspace.extension_enabled(extension_id))
    except Exception:
        return False


def _enabled_animation_ids(workspace) -> set[str]:
    try:
        if hasattr(workspace, "enabled_animation_ids"):
            return set(workspace.enabled_animation_ids())
    except Exception:
        pass
    out = set()
    for ext in getattr(workspace, "installed_extensions", []) or []:
        try:
            if str(ext.get("type")) == "animation" and bool(ext.get("enabled", True)):
                out.add(str(ext.get("id")))
        except Exception:
            continue
    return out


def _draw_extension_overlay(shell, frozen: bool = False) -> None:
    """Draw a top-level FX layer that is unmistakably visible when enabled.

    The original v2_minimal drawing kept scene FX very sparse and disabled the
    whole scene branch when Reduce Motion was on. Users could turn everything on
    and still feel like nothing happened. This overlay intentionally keeps low
    object counts, but makes every enabled animation visible.
    """
    app = getattr(shell, "app", None)
    canvas = getattr(app, "canvas", None)
    workspace = getattr(app, "workspace", None)
    if app is None or canvas is None or workspace is None:
        return
    try:
        w = max(1, int(canvas.winfo_width()))
        h = max(1, int(canvas.winfo_height()))
    except Exception:
        return
    if w < 40 or h < 40:
        return

    enabled = _enabled_animation_ids(workspace)
    if not enabled:
        return

    theme = getattr(app, "theme", None)
    bg = getattr(theme, "bg", "#071116")
    text = getattr(theme, "text", "#e8f7ff")
    accent = getattr(theme, "accent", "#74e5f0")
    glow = getattr(theme, "glow", "#315f75")
    particle = getattr(theme, "particle", "#a9fff1")

    try:
        strength = max(0.45, min(2.2, float(app.settings.get("focus_visual_strength", 1.0) or 1.0)))
    except Exception:
        strength = 1.0

    reduce_motion = bool(getattr(app, "reduce_motion", False))
    step = 0.006 if (reduce_motion or frozen) else 0.032
    phase = float(getattr(shell, "_pc_fx_phase", 0.0)) + step
    shell._pc_fx_phase = phase

    # Keep this layer out of the exact timer center as much as possible.
    center_x = w * 0.50
    center_y = h * 0.40
    safe_radius = min(w, h) * 0.17

    def far_from_timer(x, y) -> bool:
        return (x - center_x) ** 2 + (y - center_y) ** 2 > (safe_radius * 0.95) ** 2

    # Gentle global shimmer when any visual FX is active. This gives instant
    # feedback even if only water/caustics/light extensions are enabled.
    if {
        "animation-light-shafts", "animation-caustics", "animation-depth-particles",
        "animation-bioluminescence", "animation-bubbles", "animation-rising-water",
    } & enabled:
        for i in range(10 if w < 1000 else 16):
            x = (i * 197 + int(phase * 880)) % max(1, w)
            y = (i * 83 + int(math.sin(phase * 1.7 + i) * 18) + int(h * 0.17)) % max(1, int(h * 0.78))
            if not far_from_timer(x, y):
                continue
            r = 1.4 + (i % 3) * 0.55
            col = _blend_hex(bg, particle, 0.76)
            canvas.create_oval(x - r * 2.2, y - r * 2.2, x + r * 2.2, y + r * 2.2, fill=_blend_hex(bg, col, 0.44), outline="")
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=col, outline="")

    if "animation-sakura-petals" in enabled:
        count = int(10 * strength) if w >= 900 else int(7 * strength)
        count = max(6, min(18, count))
        petal = _blend_hex("#ffd1df", text, 0.10)
        for i in range(count):
            drift = (phase * (0.11 + i * 0.006) + i * 0.137) % 1.18
            x = w * (0.06 + ((i * 0.227) % 0.88)) + math.sin(phase * 2.0 + i) * (24 + i % 5)
            y = drift * h - h * 0.12
            if not far_from_timer(x, y):
                y += safe_radius * 1.4
            size = max(5.0, min(13.0, h * 0.007 + (i % 4)))
            canvas.create_oval(x - size, y - size * 0.55, x + size, y + size * 0.55, fill=petal, outline="")
            canvas.create_line(x - size * 0.35, y, x + size * 0.45, y, fill="#ff8fbd", width=1)

    if "animation-rain-window" in enabled:
        count = int(22 * strength) if w >= 900 else int(14 * strength)
        count = max(12, min(36, count))
        rain = _blend_hex(bg, "#8cecff", 0.72)
        for i in range(count):
            base = (i * 0.071 + phase * (0.45 + i * 0.006)) % 1.0
            x = w * ((i * 0.173 + 0.03) % 1.0)
            y = h * base
            length = 32 + (i % 5) * 8
            slant = 6 + (i % 4) * 2
            if not far_from_timer(x, y):
                x += safe_radius * 1.1
            canvas.create_line(x, y, x + slant, y + length, fill=rain, width=1)
            if i % 5 == 0:
                canvas.create_oval(x - 1.6, y + length - 1.6, x + 1.6, y + length + 1.6, fill=_blend_hex(bg, rain, 0.78), outline="")

    if "animation-snowfall" in enabled:
        count = int(18 * strength) if w >= 900 else int(11 * strength)
        count = max(8, min(28, count))
        snow = _blend_hex(bg, "#f5fdff", 0.88)
        for i in range(count):
            fall = (phase * (0.075 + i * 0.003) + i * 0.109) % 1.15
            x = w * ((i * 0.193 + 0.08) % 1.0) + math.sin(phase * 1.1 + i) * 18
            y = fall * h - h * 0.10
            if not far_from_timer(x, y):
                x -= safe_radius * 1.25
            r = 1.8 + (i % 4) * 0.65
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=snow, outline="")

    if "animation-fireflies" in enabled:
        count = int(10 * strength) if w >= 900 else int(6 * strength)
        count = max(5, min(16, count))
        for i in range(count):
            x = w * (0.08 + ((i * 0.211) % 0.84)) + math.sin(phase * 1.35 + i * 1.7) * 34
            y = h * (0.16 + ((i * 0.149) % 0.64)) + math.sin(phase * 1.05 + i) * 22
            if not far_from_timer(x, y):
                y += safe_radius * 1.25
            pulse = 0.58 + 0.30 * (0.5 + 0.5 * math.sin(phase * 4.0 + i))
            glow_col = _blend_hex(bg, "#c7ffd6", pulse)
            r = 1.8 + (i % 3) * 0.55
            canvas.create_oval(x - r * 4, y - r * 4, x + r * 4, y + r * 4, fill=_blend_hex(bg, glow_col, 0.36), outline="")
            canvas.create_oval(x - r, y - r, x + r, y + r, fill=glow_col, outline="")

    if "animation-aquarium-fish" in enabled:
        count = 2 if w < 1000 else 3
        fish_col = _blend_hex(bg, accent, 0.76)
        for i in range(count):
            swim = (phase * (0.11 + i * 0.025) + i * 0.31) % 1.30
            direction = -1 if i % 2 else 1
            x = (swim * (w + 220) - 110) if direction > 0 else (w + 110 - swim * (w + 220))
            y = h * (0.66 + i * 0.08) + math.sin(phase * 1.5 + i) * 16
            body = 13 + i * 3
            canvas.create_oval(x - body, y - body * 0.48, x + body, y + body * 0.48, fill=fish_col, outline="")
            tail = body * 0.78
            if direction > 0:
                canvas.create_polygon(x - body, y, x - body - tail, y - tail * 0.55, x - body - tail, y + tail * 0.55, fill=fish_col, outline="")
            else:
                canvas.create_polygon(x + body, y, x + body + tail, y - tail * 0.55, x + body + tail, y + tail * 0.55, fill=fish_col, outline="")


def _draw_safe_fallback(shell) -> None:
    app = getattr(shell, "app", None)
    canvas = getattr(app, "canvas", None)
    if canvas is None:
        return
    try:
        w = max(1, int(canvas.winfo_width()))
        h = max(1, int(canvas.winfo_height()))
        theme = getattr(app, "theme", None)
        bg = getattr(theme, "bg", "#071116")
        accent = getattr(theme, "accent", "#74e5f0")
        canvas.delete("all")
        canvas.create_rectangle(0, 0, w, h, fill=bg, outline="")
        r = min(w, h) * 0.18
        canvas.create_oval(w / 2 - r, h * 0.40 - r, w / 2 + r, h * 0.40 + r, outline=accent, width=3)
    except Exception:
        pass


def _install_minimal_patch() -> None:
    from v2_minimal import MinimalShell

    if getattr(MinimalShell, "_pc_runtime_fixed", False):
        return

    original_install = MinimalShell.install
    original_draw = MinimalShell.draw_focus_canvas

    def _patch_app_instance(shell) -> None:
        app = getattr(shell, "app", None)
        if app is None or getattr(app, "_pc_runtime_fixed", False):
            return

        original_draw_waves = getattr(app, "draw_waves", None)
        if callable(original_draw_waves):
            def draw_waves_wrapper(*args, **kwargs):
                _safe_call(getattr(getattr(app, "workspace", None), "reload_extensions_if_needed", lambda: None))
                try:
                    result = original_draw_waves(*args, **kwargs)
                except Exception:
                    _draw_safe_fallback(shell)
                    result = None
                _safe_call(_draw_extension_overlay, shell, bool(kwargs.get("frozen", False)))
                return result
            app.draw_waves = draw_waves_wrapper

        original_update_loop = getattr(app, "update_loop", None)
        if callable(original_update_loop):
            def update_loop_wrapper(*args, **kwargs):
                try:
                    return original_update_loop(*args, **kwargs)
                finally:
                    try:
                        if getattr(app, "_v3_focus", False) and _widget_alive(getattr(app, "wave_frame", None)):
                            if app.wave_frame.winfo_ismapped():
                                shell._apply_focus_scale()
                                if callable(getattr(app, "_place_secondary_chrome", None)):
                                    app._place_secondary_chrome()
                    except Exception:
                        pass
            app.update_loop = update_loop_wrapper

        original_stop_timer = getattr(app, "stop_timer", None)
        if callable(original_stop_timer):
            def stop_timer_wrapper(*args, **kwargs):
                try:
                    return original_stop_timer(*args, **kwargs)
                finally:
                    _safe_call(shell._apply_home_layout)
            app.stop_timer = stop_timer_wrapper

        original_pulse = getattr(app, "_pulse_widget", None)
        if callable(original_pulse):
            def pulse_wrapper(widget, steps: int = 8):
                if not _widget_alive(widget):
                    return None
                return _safe_call(original_pulse, widget, steps=steps)
            app._pulse_widget = pulse_wrapper

        app._pc_runtime_fixed = True

    def install_wrapper(self, *args, **kwargs):
        result = original_install(self, *args, **kwargs)
        _patch_app_instance(self)
        return result

    def draw_focus_canvas_wrapper(self, frozen=False):
        workspace = getattr(getattr(self, "app", None), "workspace", None)
        if workspace is not None and hasattr(workspace, "reload_extensions_if_needed"):
            _safe_call(workspace.reload_extensions_if_needed)
        try:
            result = original_draw(self, frozen=frozen)
        except Exception:
            _draw_safe_fallback(self)
            result = None
        _safe_call(_draw_extension_overlay, self, frozen)
        return result

    def _fx_on(self, extension_id: str) -> bool:
        return _workspace_enabled(getattr(self.app, "workspace", None), extension_id)

    MinimalShell.install = install_wrapper
    MinimalShell.draw_focus_canvas = draw_focus_canvas_wrapper
    MinimalShell._fx_on = _fx_on
    MinimalShell._pc_runtime_fixed = True


# ---------------------------------------------------------------------------


def install() -> None:
    global _PATCHED
    if _PATCHED:
        return
    try:
        _install_workspace_patch()
        _install_minimal_patch()
        _PATCHED = True
    except Exception:
        # Startup must not fail because of a runtime safety patch.
        pass


install()
