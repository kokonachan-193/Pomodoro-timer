"""Aqua Focus desktop water FX hotfix.

Loaded after pc_runtime_fixes.  It replaces only the water-family animation
extensions with a calmer aqua layer:
- animation-rising-water
- animation-caustics
- animation-bubbles
- animation-bioluminescence
- animation-depth-particles

The old water path used the current theme accent as water.  With pink accents or
image backgrounds it could look like a solid magenta band.  This patch suppresses
that legacy water path while the stock Focus renderer runs, then draws a soft
blue water layer with constrained bubbles/caustics below the waterline.
"""

from __future__ import annotations

import math

_PATCHED = False
WATER_IDS = {
    "animation-rising-water",
    "animation-caustics",
    "animation-bubbles",
    "animation-bioluminescence",
    "animation-depth-particles",
}


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _widget_alive(widget) -> bool:
    if widget is None:
        return False
    try:
        return bool(widget.winfo_exists())
    except Exception:
        return False


def _hex_to_rgb(value: str, fallback=(8, 22, 32)) -> tuple[int, int, int]:
    try:
        v = str(value or "").strip().lstrip("#")
        if len(v) == 3:
            v = "".join(ch * 2 for ch in v)
        return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return fallback


def _blend(a: str, b: str, amount: float) -> str:
    ar, ag, ab = _hex_to_rgb(a)
    br, bg, bb = _hex_to_rgb(b, (80, 225, 255))
    x = max(0.0, min(1.0, float(amount)))
    return "#%02x%02x%02x" % (
        int(ar + (br - ar) * x),
        int(ag + (bg - ag) * x),
        int(ab + (bb - ab) * x),
    )


def _smoothstep(x: float) -> float:
    x = max(0.0, min(1.0, float(x)))
    return x * x * (3.0 - 2.0 * x)


def _enabled_ids(workspace) -> set[str]:
    if workspace is None:
        return set()
    try:
        if hasattr(workspace, "reload_extensions_if_needed"):
            workspace.reload_extensions_if_needed()
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


def _without_legacy_water(workspace, callback):
    """Temporarily hide only old water-family IDs from existing renderers."""
    if workspace is None or not callable(getattr(workspace, "extension_enabled", None)):
        return callback()
    old_extension_enabled = workspace.extension_enabled
    old_enabled_animation_ids = getattr(workspace, "enabled_animation_ids", None)

    def extension_enabled(extension_id: str) -> bool:
        if str(extension_id) in WATER_IDS:
            return False
        return old_extension_enabled(extension_id)

    def enabled_animation_ids() -> set[str]:
        if callable(old_enabled_animation_ids):
            return set(old_enabled_animation_ids()) - WATER_IDS
        return _enabled_ids(workspace) - WATER_IDS

    workspace.extension_enabled = extension_enabled
    if callable(old_enabled_animation_ids):
        workspace.enabled_animation_ids = enabled_animation_ids
    try:
        return callback()
    finally:
        workspace.extension_enabled = old_extension_enabled
        if callable(old_enabled_animation_ids):
            workspace.enabled_animation_ids = old_enabled_animation_ids


def _create(canvas, method: str, *args, **kwargs):
    try:
        kwargs.setdefault("tags", ("pc_water_fx",))
        return getattr(canvas, method)(*args, **kwargs)
    except Exception:
        return None


def _surface_points(width: int, water_y: float, phase: float, amp: float, segments: int, offset: float = 0.0):
    pts = []
    for i in range(segments + 1):
        nx = i / max(1, segments)
        x = width * nx
        y = (
            water_y
            + math.sin(phase * 1.9 + nx * math.tau * 2.15 + offset) * amp
            + math.sin(phase * 1.05 + nx * math.tau * 4.8 + offset * 0.5) * amp * 0.22
        )
        pts.append((x, y))
    return pts


def _draw_clean_water(shell, frozen: bool = False) -> None:
    app = getattr(shell, "app", None)
    canvas = getattr(app, "canvas", None)
    workspace = getattr(app, "workspace", None)
    if app is None or canvas is None or workspace is None:
        return
    enabled = _enabled_ids(workspace)
    if not (enabled & WATER_IDS):
        try:
            canvas.delete("pc_water_fx")
        except Exception:
            pass
        return

    try:
        width = max(1, int(canvas.winfo_width()))
        height = max(1, int(canvas.winfo_height()))
        canvas.delete("pc_water_fx")
    except Exception:
        return
    if width < 40 or height < 40:
        return

    theme = getattr(app, "theme", None)
    bg = getattr(theme, "bg", "#071116")
    text = getattr(theme, "text", "#e8f7ff")
    particle = getattr(theme, "particle", "#a9fff1")
    aqua = "#45dcff"
    aqua_light = "#a7f7ff"
    deep = "#0a2a3e"

    try:
        strength = max(0.55, min(1.9, float(app.settings.get("focus_visual_strength", 1.0) or 1.0)))
    except Exception:
        strength = 1.0

    progress = 0.0
    try:
        total = float(getattr(app, "total_seconds", 0) or 0)
        remaining = float(getattr(app, "remaining_seconds", 0) or 0)
        if total > 0:
            progress = max(0.0, min(1.0, 1.0 - remaining / total))
    except Exception:
        progress = 0.0

    rising = "animation-rising-water" in enabled
    mode = str(getattr(app, "mode", "Work"))
    if rising and mode == "Work":
        level = _smoothstep(progress)
    elif rising:
        level = max(0.0, 0.14 * (1.0 - progress))
    else:
        level = 0.16

    # Much calmer than the legacy 0.58 range. It starts almost hidden at the
    # bottom and rises smoothly instead of producing a thick solid bar early on.
    water_y = height * (0.965 - 0.46 * level)
    water_y = max(height * 0.43, min(height * 0.985, water_y))
    depth = max(1.0, height - water_y)

    reduce_motion = bool(getattr(app, "reduce_motion", False)) or bool(frozen)
    phase_step = 0.012 if reduce_motion else 0.050
    phase = float(getattr(shell, "_pc_water_phase", 0.0)) + phase_step
    shell._pc_water_phase = phase
    amp = 0.0 if reduce_motion else max(2.0, min(9.0, height * 0.0065 * strength))

    # Soft blue depth gradient.  No accent color, so a pink theme cannot turn the
    # water into a magenta strip.
    stripes = 9 if depth < 170 else 13
    for j in range(stripes):
        y0 = water_y + depth * j / stripes
        y1 = water_y + depth * (j + 1) / stripes + 1
        amount = 0.075 + 0.17 * (j / max(1, stripes - 1))
        fill = _blend(_blend(bg, deep, 0.34), aqua, amount)
        _create(canvas, "create_rectangle", 0, y0, width, y1, fill=fill, outline="")

    segments = 56 if width >= 900 else 40
    front = _surface_points(width, water_y, phase, amp, segments)
    rear = _surface_points(width, water_y + max(5.0, 8.0 * strength), phase, amp * 0.62, segments, offset=0.85)
    _create(canvas, "create_line", *[v for p in rear for v in p], fill=_blend(bg, aqua, 0.42), width=max(1, int(2 * strength)), smooth=True)
    _create(canvas, "create_line", *[v for p in front for v in p], fill=_blend(bg, aqua_light, 0.78), width=max(2, int(3 * strength)), smooth=True)

    for i in range(4):
        gx0 = (i * 0.23 + phase * 0.028) % 1.0
        x0 = width * gx0
        x1 = min(width, x0 + width * (0.07 + 0.02 * (i % 2)))
        y = water_y + math.sin(phase * 1.6 + i) * max(2.0, amp)
        _create(canvas, "create_line", x0, y, x1, y + math.sin(i) * 2, fill=_blend(bg, text, 0.52), width=1)

    if "animation-caustics" in enabled and depth > 42:
        for j in range(max(3, min(8, int(depth / 72)))):
            y = water_y + 26 + j * max(20, depth / 7)
            if y > height - 14:
                continue
            pts = []
            for i in range(18):
                x = width * i / 17
                yy = y + math.sin(phase * 2.0 + i * 0.72 + j) * (3.0 + j * 0.45)
                pts.extend((x, yy))
            _create(canvas, "create_line", *pts, fill=_blend(bg, aqua_light, 0.34), width=1, smooth=True)

    if "animation-bubbles" in enabled and depth > 24:
        for i in range(max(6, min(18, int(11 * strength)))):
            x = ((i * 137 + 41) % max(1, int(width))) + math.sin(phase * 1.2 + i) * 11
            travel = (phase * (34 + i * 2) + i * 47) % max(1.0, depth + 32)
            y = height - travel
            if y < water_y + 8 or y > height - 4:
                continue
            r = 1.6 + (i % 4) * 0.75
            _create(canvas, "create_oval", x - r, y - r, x + r, y + r, outline=_blend(bg, aqua_light, 0.62), width=1)

    if "animation-bioluminescence" in enabled and depth > 36:
        for i in range(max(4, min(14, int(7 * strength)))):
            x = ((i * 181 + 73) % max(1, int(width))) + math.sin(phase * 0.9 + i) * 18
            y = water_y + 24 + ((i * 67 + phase * (18 + i)) % max(1, depth - 24))
            r = 1.2 + (i % 3) * 0.55
            glow = _blend(bg, particle, 0.78)
            _create(canvas, "create_oval", x - r * 3, y - r * 3, x + r * 3, y + r * 3, fill=_blend(bg, glow, 0.30), outline="")
            _create(canvas, "create_oval", x - r, y - r, x + r, y + r, fill=glow, outline="")

    if "animation-depth-particles" in enabled and depth > 28:
        for i in range(max(5, min(16, int(9 * strength)))):
            x = ((i * 149 + 19) % max(1, int(width))) + math.sin(phase * 1.4 + i) * 10
            y = water_y + ((phase * (20 + i) + i * 53) % max(1, depth))
            r = 1 + (i % 2) * 0.55
            _create(canvas, "create_oval", x - r, y - r, x + r, y + r, fill=_blend(bg, particle, 0.46), outline="")


def _patch_app_instance(shell) -> None:
    app = getattr(shell, "app", None)
    if app is None or getattr(app, "_pc_water_fixed", False):
        return

    current_update_loop = getattr(app, "update_loop", None)
    if callable(current_update_loop):
        def update_loop_wrapper(*args, **kwargs):
            workspace = getattr(app, "workspace", None)
            try:
                return _without_legacy_water(workspace, lambda: current_update_loop(*args, **kwargs))
            finally:
                try:
                    if getattr(app, "_v3_focus", False) and _widget_alive(getattr(app, "wave_frame", None)):
                        if app.wave_frame.winfo_ismapped():
                            _draw_clean_water(shell, bool(getattr(app, "is_paused", False)))
                except Exception:
                    pass
        app.update_loop = update_loop_wrapper

    app._pc_water_fixed = True


def install() -> None:
    global _PATCHED
    if _PATCHED:
        return
    try:
        from v2_minimal import MinimalShell
    except Exception:
        return

    if getattr(MinimalShell, "_pc_water_fixed", False):
        _PATCHED = True
        return

    original_install = MinimalShell.install
    original_draw = MinimalShell.draw_focus_canvas

    def install_wrapper(self, *args, **kwargs):
        result = original_install(self, *args, **kwargs)
        _patch_app_instance(self)
        return result

    def draw_focus_canvas_wrapper(self, frozen=False):
        app = getattr(self, "app", None)
        workspace = getattr(app, "workspace", None)
        try:
            result = _without_legacy_water(workspace, lambda: original_draw(self, frozen=frozen))
        except Exception:
            result = _safe_call(original_draw, self, frozen=frozen)
        _draw_clean_water(self, frozen)
        return result

    MinimalShell.install = install_wrapper
    MinimalShell.draw_focus_canvas = draw_focus_canvas_wrapper
    MinimalShell._pc_water_fixed = True
    _PATCHED = True


install()
