"""Desktop runtime fixes for Aqua Focus.

Loaded early by either:
- sitecustomize.py during source runs, or
- pyinstaller_runtime_hook.py inside packaged desktop builds.

v2.1.9 goals:
- keep Focus animation extensions live without restarting Focus
- avoid random Tk/CTk display crashes after resize/theme rebuilds
- debounce expensive redraw/layout work during resize storms
- keep Focus typography responsive instead of snapping back to a fixed huge size
- make drawing failures recover to a safe modern fallback frame
"""

from __future__ import annotations

import json
import time
from pathlib import Path

_PATCHED = False


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
    """Run a small UI callback without assuming the Tk object is still alive."""
    if _widget_alive(root):
        try:
            root.after(delay, callback)
            return
        except Exception:
            pass
    _safe_call(callback)


def _debounce(widget, attr: str, delay: int, callback) -> None:
    """Collapse resize/redraw storms into one UI callback."""
    if not _widget_alive(widget):
        _safe_call(callback)
        return
    old = getattr(widget, attr, None)
    if old is not None:
        try:
            widget.after_cancel(old)
        except Exception:
            pass
    try:
        setattr(widget, attr, widget.after(delay, callback))
    except Exception:
        setattr(widget, attr, None)
        _safe_call(callback)


def _safe_canvas_clear(app) -> None:
    try:
        c = getattr(app, "canvas", None)
        if c is not None:
            c.delete("all")
    except Exception:
        pass


def _draw_safe_focus_fallback(app, ring: bool = True) -> None:
    """Draw a minimal modern fallback so a canvas error never blanks Focus."""
    try:
        c = getattr(app, "canvas", None)
        if c is None:
            return
        c.delete("all")
        w, h = max(1, c.winfo_width()), max(1, c.winfo_height())
        t = app.theme
        for i in range(10):
            y0 = int(i * h / 10)
            y1 = int((i + 1) * h / 10) + 1
            fill = getattr(app.minimal_shell, "_blend", lambda a, b, m: a)(t.bg, t.glow, 0.03 + i * 0.012)
            c.create_rectangle(0, y0, w, y1, fill=fill, outline="")
        if ring:
            cx, cy = w / 2, h * 0.40
            r = min(w, h) * 0.18
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=t.accent, width=3)
    except Exception:
        pass


def _install_workspace_patch() -> None:
    from v2_workspace import AmbientMixer, SessionStats, TaskStore, WorkspacePanels

    if getattr(WorkspacePanels, "_pc_runtime_fixed", False):
        return

    builtin_by_id = {str(item.get("id")): dict(item) for item in WorkspacePanels.BUILTIN_ANIMATIONS}

    def _normalize_extension(self, item):
        if isinstance(item, str):
            ext = dict(builtin_by_id.get(item, {"id": item, "name": item, "type": "animation" if item.startswith("animation-") else "extension"}))
            ext.setdefault("enabled", True)
            return ext
        if not isinstance(item, dict):
            return None
        eid = str(item.get("id", "")).strip()
        if not eid:
            return None
        base = dict(builtin_by_id.get(eid, {}))
        base.update(item)
        base["id"] = eid
        base.setdefault("type", "animation" if eid.startswith("animation-") else "extension")
        base["enabled"] = bool(base.get("enabled", True))
        return base

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
            self.installed_extensions_path.parent.mkdir(parents=True, exist_ok=True)
            normalized = []
            seen = set()
            for row in self.installed_extensions:
                ext = _normalize_extension(self, row)
                if not ext or ext["id"] in seen:
                    continue
                seen.add(ext["id"])
                normalized.append(ext)
            self.installed_extensions = normalized
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
                wave_frame = getattr(root, "wave_frame", None)
                if _widget_alive(wave_frame) and wave_frame.winfo_ismapped():
                    root.draw_waves(frozen=bool(getattr(root, "is_paused", False)))
                    _safe_call(root._place_secondary_chrome)
                else:
                    shell = getattr(root, "minimal_shell", None)
                    if shell is not None and callable(getattr(shell, "draw_focus_canvas", None)):
                        shell.draw_focus_canvas(frozen=bool(getattr(root, "is_paused", False)))
                shell = getattr(root, "minimal_shell", None)
                if shell is not None:
                    _safe_call(shell.refresh_background)
                root._focus_fx_revision = time.time()
            except Exception:
                _draw_safe_focus_fallback(root)

        _debounce(root, "_extension_redraw_after", 30, redraw)

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
        self._extensions_mtime = self.installed_extensions_path.stat().st_mtime if existed else 0.0
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
                try:
                    workspace = getattr(app, "workspace", None)
                    if workspace is not None and hasattr(workspace, "reload_extensions_if_needed"):
                        workspace.reload_extensions_if_needed()
                except Exception:
                    pass
                try:
                    return original_draw_waves(*args, **kwargs)
                except Exception:
                    _draw_safe_focus_fallback(app, ring=False)
                    return None
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
                                _safe_call(app._place_secondary_chrome)
                    except Exception:
                        pass
            app.update_loop = update_loop_wrapper

        original_stop_timer = getattr(app, "stop_timer", None)
        if callable(original_stop_timer):
            def stop_timer_wrapper(*args, **kwargs):
                try:
                    return original_stop_timer(*args, **kwargs)
                finally:
                    _debounce(app, "_post_stop_layout_after", 45, lambda: _safe_call(shell._apply_home_layout))
            app.stop_timer = stop_timer_wrapper

        original_pulse = getattr(app, "_pulse_widget", None)
        if callable(original_pulse):
            def pulse_wrapper(widget, steps: int = 8):
                if not _widget_alive(widget):
                    return None
                try:
                    return original_pulse(widget, steps=steps)
                except Exception:
                    return None
            app._pulse_widget = pulse_wrapper

        original_place = getattr(shell, "place_focus_chrome", None)
        if callable(original_place):
            def place_focus_chrome_wrapper(*args, **kwargs):
                try:
                    return original_place(*args, **kwargs)
                except Exception:
                    return None
            shell.place_focus_chrome = place_focus_chrome_wrapper

        app._pc_runtime_fixed = True

    def install_wrapper(self, *args, **kwargs):
        result = original_install(self, *args, **kwargs)
        _patch_app_instance(self)
        _debounce(getattr(self, "surface", None), "_v219_initial_layout_after", 50, lambda: _safe_call(self._apply_home_layout))
        return result

    def draw_focus_canvas_wrapper(self, frozen=False):
        app = getattr(self, "app", None)
        try:
            workspace = getattr(app, "workspace", None)
            if workspace is not None and hasattr(workspace, "reload_extensions_if_needed"):
                workspace.reload_extensions_if_needed()
        except Exception:
            pass
        try:
            return original_draw(self, frozen=frozen)
        except Exception:
            _draw_safe_focus_fallback(app)
            return None

    def _fx_on(self, extension_id: str) -> bool:
        try:
            return bool(self.app.workspace.extension_enabled(extension_id))
        except Exception:
            return False

    MinimalShell.install = install_wrapper
    MinimalShell.draw_focus_canvas = draw_focus_canvas_wrapper
    MinimalShell._fx_on = _fx_on
    MinimalShell._pc_runtime_fixed = True


def install() -> None:
    global _PATCHED
    if _PATCHED:
        return
    try:
        _install_workspace_patch()
        _install_minimal_patch()
        _PATCHED = True
    except Exception:
        pass


install()
