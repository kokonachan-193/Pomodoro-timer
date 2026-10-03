"""Aqua Focus v2 experience layer: deep-sea hero + auxiliary timer modes."""

from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import messagebox
from typing import Callable

import customtkinter as ctk


class OceanHero(tk.Canvas):
    """Low-distraction animated deep-sea banner used on the v2 home screen."""

    def __init__(
        self,
        master,
        *,
        theme_getter: Callable[[], object],
        reduce_motion_getter: Callable[[], bool],
        text_getter: Callable[[str], str] | None = None,
        font_family: str = "Segoe UI",
        **kwargs,
    ):
        super().__init__(master, highlightthickness=0, bd=0, **kwargs)
        self.theme_getter = theme_getter
        self.reduce_motion_getter = reduce_motion_getter
        self.text_getter = text_getter or (lambda key: key)
        self.font_family = font_family
        self.phase = 0.0
        self._alive = True
        self.bind("<Destroy>", self._on_destroy)
        self.after(60, self._animate)

    def _on_destroy(self, _event=None):
        self._alive = False

    @staticmethod
    def _hex_to_rgb(value: str) -> tuple[int, int, int]:
        value = (value or "#000000").lstrip("#")
        if len(value) != 6:
            return 0, 0, 0
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))

    @classmethod
    def _blend(cls, a: str, b: str, amount: float) -> str:
        ar, ag, ab = cls._hex_to_rgb(a)
        br, bg, bb = cls._hex_to_rgb(b)
        t = max(0.0, min(1.0, amount))
        return "#%02x%02x%02x" % (
            int(ar + (br - ar) * t),
            int(ag + (bg - ag) * t),
            int(ab + (bb - ab) * t),
        )

    def _animate(self):
        if not self._alive:
            return
        if not self.reduce_motion_getter():
            self.phase += 0.035
        self.draw()
        self.after(60 if not self.reduce_motion_getter() else 500, self._animate)

    def draw(self):
        self.delete("all")
        theme = self.theme_getter()
        w = max(10, self.winfo_width())
        h = max(10, self.winfo_height())
        self.configure(bg=theme.bg)

        # Layered depth bands.
        bands = 18
        for i in range(bands):
            y0 = int(h * i / bands)
            y1 = int(h * (i + 1) / bands) + 1
            col = self._blend(theme.bg, theme.glow, 0.04 + (i / bands) * 0.20)
            self.create_rectangle(0, y0, w, y1, fill=col, outline="")

        # Very soft caustic rays.
        for i in range(5):
            x = (w * (0.10 + i * 0.23)) + math.sin(self.phase + i * 1.7) * 24
            self.create_polygon(
                x - 34, 0,
                x + 18, 0,
                x + 95, h,
                x - 55, h,
                fill=self._blend(theme.bg, theme.accent, 0.075),
                outline="",
            )

        # Slow depth bubbles. Positions are deterministic to avoid visual noise.
        if not self.reduce_motion_getter():
            for i in range(16):
                speed = 0.35 + (i % 5) * 0.08
                base = (i * 97) % max(1, w)
                x = base + math.sin(self.phase * (0.6 + i * 0.02) + i) * 18
                y = h - ((self.phase * 55 * speed + i * 61) % (h + 40))
                r = 2 + (i % 4)
                col = self._blend(theme.bg, theme.particle, 0.48)
                self.create_oval(x-r, y-r, x+r, y+r, outline=col, width=1)

        # Horizon glow and copy.
        glow_y = int(h * 0.72)
        self.create_oval(
            w * 0.12, glow_y - 40, w * 0.88, glow_y + 95,
            fill=self._blend(theme.bg, theme.accent, 0.08),
            outline="",
        )
        self.create_text(
            24, 24,
            anchor="nw",
            text=self.text_getter("deep_sea_workspace"),
            fill=theme.accent,
            font=(self.font_family, 10, "bold"),
        )
        self.create_text(
            24, 53,
            anchor="nw",
            text=self.text_getter("descend_focus"),
            fill=theme.text,
            font=(self.font_family, 24, "bold"),
        )
        self.create_text(
            25, 91,
            anchor="nw",
            text=self.text_getter("quiet_motion"),
            fill=theme.muted,
            font=(self.font_family, 10),
        )


class AuxiliaryModes:
    """Countdown, stopwatch and alarm tools that do not disturb Pomodoro state."""

    def __init__(self, root, theme_getter: Callable[[], object], font_family: str = "Segoe UI"):
        self.root = root
        self.theme_getter = theme_getter
        self.font_family = font_family
        self.alarms: list[dict] = []
        self._countdown_job = None
        self._stopwatch_job = None
        self.root.after(1000, self._alarm_tick)

    def _theme(self):
        return self.theme_getter()

    def _t(self, key: str, **kwargs):
        try:
            return self.root.t(key, **kwargs)
        except Exception:
            return key

    def _window(self, title: str, geometry: str = "520x430"):
        t = self._theme()
        win = ctk.CTkToplevel(self.root)
        win.title(title)
        win.geometry(geometry)
        win.minsize(430, 320)
        win.configure(fg_color=t.bg)
        try:
            win.transient(self.root)
        except Exception:
            pass
        return win

    def _title(self, parent, text: str, sub: str):
        t = self._theme()
        ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(family=self.font_family, size=27, weight="bold"),
            text_color=t.text,
        ).pack(anchor="w", padx=24, pady=(24, 2))
        ctk.CTkLabel(
            parent,
            text=sub,
            font=ctk.CTkFont(family=self.font_family, size=12),
            text_color=t.muted,
        ).pack(anchor="w", padx=24, pady=(0, 18))

    def open_countdown(self):
        t = self._theme()
        win = self._window(f"Aqua Focus · {self._t('countdown')}")
        self._title(win, self._t("countdown"), self._t("countdown_subtitle"))

        card = ctk.CTkFrame(win, fg_color=t.sidebar, corner_radius=20, border_width=1, border_color=t.glow)
        card.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(card, text=self._t("minutes"), text_color=t.muted).pack(anchor="w", padx=18, pady=(16, 4))
        entry = ctk.CTkEntry(card, height=44, placeholder_text="30")
        entry.pack(fill="x", padx=18)
        entry.insert(0, "30")
        label = ctk.CTkLabel(
            card, text="30:00",
            font=ctk.CTkFont(family=self.font_family, size=48, weight="bold"),
            text_color=t.text,
        )
        label.pack(pady=18)
        state = {"running": False, "remaining": 1800.0, "last": time.monotonic()}

        def sync():
            sec = max(0, int(state["remaining"] + 0.999))
            label.configure(text=f"{sec // 60:02d}:{sec % 60:02d}")

        def tick():
            if not win.winfo_exists():
                return
            now = time.monotonic()
            if state["running"]:
                state["remaining"] = max(0.0, state["remaining"] - (now - state["last"]))
                sync()
                if state["remaining"] <= 0:
                    state["running"] = False
                    try:
                        self.root.bell()
                    except Exception:
                        pass
                    messagebox.showinfo("Aqua Focus", self._t("countdown_complete"))
            state["last"] = now
            self._countdown_job = win.after(100, tick)

        def start_pause():
            if state["remaining"] <= 0:
                try:
                    state["remaining"] = max(1.0, float(entry.get()) * 60)
                except ValueError:
                    return
            elif not state["running"]:
                try:
                    requested = float(entry.get()) * 60
                    if abs(state["remaining"] - 1800.0) < 0.5:
                        state["remaining"] = max(1.0, requested)
                except ValueError:
                    return
            state["running"] = not state["running"]
            state["last"] = time.monotonic()
            btn.configure(text=self._t("pause_caps") if state["running"] else self._t("start_caps"))
            sync()

        def reset():
            state["running"] = False
            try:
                state["remaining"] = max(1.0, float(entry.get()) * 60)
            except ValueError:
                state["remaining"] = 1800.0
            btn.configure(text=self._t("start_caps"))
            sync()

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(0, 18))
        btn = ctk.CTkButton(row, text=self._t("start_caps"), height=44, fg_color=t.accent, hover_color=t.accent_hover, command=start_pause)
        btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(row, text=self._t("reset_caps"), height=44, fg_color=t.glow, hover_color=t.accent_hover, command=reset).pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )
        tick()

    def open_stopwatch(self):
        t = self._theme()
        win = self._window(f"Aqua Focus · {self._t('stopwatch')}")
        self._title(win, self._t("stopwatch"), self._t("stopwatch_subtitle"))

        card = ctk.CTkFrame(win, fg_color=t.sidebar, corner_radius=20, border_width=1, border_color=t.glow)
        card.pack(fill="both", expand=True, padx=24, pady=(4, 24))
        label = ctk.CTkLabel(
            card, text="00:00.0",
            font=ctk.CTkFont(family=self.font_family, size=52, weight="bold"),
            text_color=t.text,
        )
        label.pack(pady=(55, 28))
        state = {"running": False, "elapsed": 0.0, "last": time.monotonic()}

        def sync():
            total = max(0.0, state["elapsed"])
            minutes = int(total // 60)
            seconds = int(total % 60)
            tenths = int((total - int(total)) * 10)
            label.configure(text=f"{minutes:02d}:{seconds:02d}.{tenths}")

        def tick():
            if not win.winfo_exists():
                return
            now = time.monotonic()
            if state["running"]:
                state["elapsed"] += now - state["last"]
                sync()
            state["last"] = now
            self._stopwatch_job = win.after(100, tick)

        def toggle():
            state["running"] = not state["running"]
            state["last"] = time.monotonic()
            btn.configure(text=self._t("pause_caps") if state["running"] else self._t("start_caps"))

        def reset():
            state["running"] = False
            state["elapsed"] = 0.0
            btn.configure(text=self._t("start_caps"))
            sync()

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=18)
        btn = ctk.CTkButton(row, text=self._t("start_caps"), height=46, fg_color=t.accent, hover_color=t.accent_hover, command=toggle)
        btn.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(row, text=self._t("reset_caps"), height=46, fg_color=t.glow, hover_color=t.accent_hover, command=reset).pack(
            side="left", fill="x", expand=True, padx=(6, 0)
        )
        tick()

    def open_alarm(self):
        t = self._theme()
        win = self._window(f"Aqua Focus · {self._t('alarm')}", "540x500")
        self._title(win, self._t("alarm"), self._t("alarm_subtitle"))

        card = ctk.CTkFrame(win, fg_color=t.sidebar, corner_radius=20, border_width=1, border_color=t.glow)
        card.pack(fill="x", padx=24, pady=(4, 12))
        default_time = (datetime.now() + timedelta(minutes=10)).strftime("%H:%M")
        time_entry = ctk.CTkEntry(card, height=44, placeholder_text=self._t("time_ph"))
        time_entry.insert(0, default_time)
        time_entry.pack(fill="x", padx=18, pady=(18, 8))
        name_entry = ctk.CTkEntry(card, height=44, placeholder_text=self._t("alarm_label"))
        name_entry.insert(0, self._t("return_to_focus"))
        name_entry.pack(fill="x", padx=18, pady=(0, 12))
        status = ctk.CTkLabel(card, text="", text_color=t.muted)
        status.pack(anchor="w", padx=18, pady=(0, 8))

        alarms_label = ctk.CTkLabel(
            win, text="", justify="left", anchor="w", text_color=t.muted,
            font=ctk.CTkFont(family=self.font_family, size=12),
        )
        alarms_label.pack(fill="x", padx=28, pady=8)

        def refresh():
            if not self.alarms:
                alarms_label.configure(text=self._t("no_active_alarms"))
                return
            lines = [self._t("active_alarms")]
            for a in sorted(self.alarms, key=lambda x: x["when"]):
                lines.append(f"  {a['when'].strftime('%m/%d %H:%M')}  ·  {a['label']}")
            alarms_label.configure(text="\n".join(lines))

        def add():
            try:
                hh, mm = [int(v) for v in time_entry.get().strip().split(":", 1)]
                if hh not in range(24) or mm not in range(60):
                    raise ValueError
            except Exception:
                status.configure(text=self._t("time_help"))
                return
            now = datetime.now()
            when = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
            if when <= now:
                when += timedelta(days=1)
            label = name_entry.get().strip() or self._t("default_alarm_label")
            self.alarms.append({"when": when, "label": label})
            status.configure(text=self._t("alarm_set", when=when.strftime("%m/%d %H:%M")))
            refresh()

        ctk.CTkButton(
            card, text=self._t("set_alarm"), height=44,
            fg_color=t.accent, hover_color=t.accent_hover, command=add,
        ).pack(fill="x", padx=18, pady=(0, 18))
        refresh()

    def _alarm_tick(self):
        now = datetime.now()
        due = [a for a in self.alarms if a["when"] <= now]
        if due:
            for alarm in due:
                try:
                    self.root.bell()
                except Exception:
                    pass
                try:
                    messagebox.showinfo("Aqua Focus · Alarm", alarm["label"])
                except Exception:
                    pass
                try:
                    self.alarms.remove(alarm)
                except ValueError:
                    pass
        self.root.after(1000, self._alarm_tick)
