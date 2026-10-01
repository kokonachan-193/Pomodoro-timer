"""Aqua Focus minimal shell.

The core rule is progressive disclosure:
- one task
- one duration
- one primary action
Everything else is reachable, but not competing for attention.
"""

from __future__ import annotations

import math
import tkinter as tk
import customtkinter as ctk


class MinimalShell:
    PRESETS = {
        "25": (25, 5, "Classic", 15, 4, 4, "Short structured focus", "classic"),
        "50": (50, 10, "Flow 50", 20, 2, 3, "Balanced deep work", "balanced"),
        "90": (90, 20, "Deep Dive", 20, 1, 1, "Long uninterrupted focus", "ultradian"),
    }

    def __init__(self, app):
        self.app = app
        self.surface = None
        self.selected = "50"
        self.duration_buttons = {}
        self._sound_open = False
        self._focus_phase = 0.0
        self.intent_entry = None
        self.music_entry = None
        self.start_button = None
        self.duration_label = None
        self.sound_drawer = None

    # ------------------------------------------------------------------ home
    def install(self):
        a = self.app
        t = a.theme

        # Legacy UI remains alive because timer/audio logic still references it,
        # but it no longer competes with the user.
        for widget in (getattr(a, "sidebar", None), getattr(a, "setup_frame", None)):
            if widget is not None:
                try:
                    widget.pack_forget()
                except Exception:
                    pass

        self.surface = ctk.CTkFrame(a.main_container, fg_color=t.bg, corner_radius=0)
        self.surface.pack(fill="both", expand=True)

        # generous outer gutter: avoids the "admin dashboard" look
        shell = ctk.CTkFrame(self.surface, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=42, pady=30)

        top = ctk.CTkFrame(shell, fg_color="transparent", height=48)
        top.pack(fill="x")
        top.pack_propagate(False)

        brand = ctk.CTkFrame(top, fg_color="transparent")
        brand.pack(side="left")
        ctk.CTkLabel(
            brand, text="Aqua Focus",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=20, weight="bold"),
            text_color=t.text,
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand, text="one task. one session.",
            font=ctk.CTkFont(size=10), text_color=t.muted,
        ).pack(anchor="w", pady=(1, 0))

        top_actions = ctk.CTkFrame(top, fg_color="transparent")
        top_actions.pack(side="right")
        self._quiet_button(top_actions, "Stats", a.workspace.open_stats).pack(side="left", padx=3)
        self._quiet_button(top_actions, "Tasks", a.workspace.open_tasks).pack(side="left", padx=3)
        self._quiet_button(top_actions, "•••", self.open_tools, width=44).pack(side="left", padx=3)
        self._quiet_button(top_actions, "Settings", self.open_settings, width=84).pack(side="left", padx=(3, 0))

        # Main content deliberately leaves large empty areas.
        center = ctk.CTkFrame(shell, fg_color="transparent")
        center.pack(fill="both", expand=True, pady=(26, 0))

        focus_card = ctk.CTkFrame(
            center,
            width=700,
            fg_color=t.sidebar,
            corner_radius=32,
            border_width=1,
            border_color=self._blend(t.bg, t.glow, 0.78),
        )
        focus_card.place(relx=0.5, rely=0.44, anchor="center")
        focus_card.grid_columnconfigure(0, weight=1)

        eyebrow = ctk.CTkLabel(
            focus_card, text="READY TO DIVE",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=10, weight="bold"),
            text_color=t.accent,
        )
        eyebrow.grid(row=0, column=0, padx=42, pady=(34, 7), sticky="w")

        ctk.CTkLabel(
            focus_card, text="What deserves your attention?",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=25, weight="bold"),
            text_color=t.text,
        ).grid(row=1, column=0, padx=42, sticky="w")

        self.intent_entry = ctk.CTkEntry(
            focus_card,
            height=54,
            corner_radius=18,
            border_width=1,
            border_color=self._blend(t.glow, t.accent, 0.28),
            fg_color=self._blend(t.sidebar, t.bg, 0.25),
            text_color=t.text,
            placeholder_text="Write one concrete next action",
            font=ctk.CTkFont(size=14),
        )
        self.intent_entry.grid(row=2, column=0, padx=42, pady=(18, 24), sticky="ew")
        try:
            existing = a.entry_intention.get().strip()
            if existing:
                self.intent_entry.insert(0, existing)
        except Exception:
            pass

        duration_area = ctk.CTkFrame(focus_card, fg_color="transparent")
        duration_area.grid(row=3, column=0, padx=42, sticky="ew")
        ctk.CTkLabel(
            duration_area, text="Session",
            font=ctk.CTkFont(size=11), text_color=t.muted,
        ).pack(side="left")

        chips = ctk.CTkFrame(duration_area, fg_color="transparent")
        chips.pack(side="right")
        for key in ("25", "50", "90"):
            b = ctk.CTkButton(
                chips,
                text=f"{key} min",
                width=78,
                height=36,
                corner_radius=18,
                border_width=1,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda k=key: self.select_duration(k),
            )
            b.pack(side="left", padx=4)
            self.duration_buttons[key] = b

        self.duration_label = ctk.CTkLabel(
            focus_card,
            text="50:00",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=68, weight="bold"),
            text_color=t.text,
        )
        self.duration_label.grid(row=4, column=0, pady=(24, 0))

        ctk.CTkLabel(
            focus_card,
            text="A calm 50 / 10 rhythm",
            font=ctk.CTkFont(size=11),
            text_color=t.muted,
        ).grid(row=5, column=0, pady=(0, 20))

        # Secondary information stays collapsed.
        sound_row = ctk.CTkFrame(focus_card, fg_color="transparent")
        sound_row.grid(row=6, column=0, padx=42, sticky="ew")
        self.sound_button = ctk.CTkButton(
            sound_row,
            text="Sound  ·  optional",
            height=36,
            corner_radius=18,
            fg_color="transparent",
            hover_color=t.glow,
            border_width=0,
            text_color=t.muted,
            anchor="w",
            command=self.toggle_sound,
        )
        self.sound_button.pack(fill="x")

        self.sound_drawer = ctk.CTkFrame(focus_card, fg_color="transparent")

        self.start_button = ctk.CTkButton(
            focus_card,
            text="Start focus",
            height=58,
            corner_radius=22,
            fg_color=t.accent,
            hover_color=t.accent_hover,
            text_color="#071116",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=16, weight="bold"),
            command=self.start_focus,
        )
        self.start_button.grid(row=8, column=0, padx=42, pady=(22, 36), sticky="ew")

        # Tiny status line below the focus card.
        self.today_label = ctk.CTkLabel(
            center,
            text=self._today_copy(),
            font=ctk.CTkFont(size=10),
            text_color=t.muted,
        )
        self.today_label.place(relx=0.5, rely=0.89, anchor="center")

        self.select_duration("50")
        a._v3_focus = True

        # Focus-view typography and control shape.
        try:
            a.status_text.configure(font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=12), text_color="#8fa9b5")
            a.time_text.configure(font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=94), text_color="#eef7f8")
            a.ctrl_bar.configure(corner_radius=24, fg_color=self._blend(t.bg, t.sidebar, 0.55), border_width=1)
            a.pause_btn.configure(width=112, corner_radius=16, fg_color=t.accent, text_color="#071116")
            a.stop_btn.configure(width=96, corner_radius=16)
            a.menu_btn.place_forget()
        except Exception:
            pass

    def _today_copy(self):
        try:
            minutes = self.app.workspace.stats.today_minutes()
        except Exception:
            minutes = 0
        if minutes < 1:
            return "Nothing to catch up on. Start with one clear session."
        h = int(minutes // 60)
        m = int(minutes % 60)
        if h:
            return f"Today · {h}h {m:02d}m focused"
        return f"Today · {m}m focused"

    def _quiet_button(self, parent, text, command, width=72):
        t = self.app.theme
        return ctk.CTkButton(
            parent, text=text, width=width, height=34, corner_radius=17,
            fg_color="transparent", hover_color=t.glow,
            border_width=0, text_color=t.muted,
            font=ctk.CTkFont(size=11), command=command,
        )

    def select_duration(self, key):
        self.selected = key
        a = self.app
        t = a.theme
        for k, button in self.duration_buttons.items():
            selected = k == key
            button.configure(
                fg_color=t.accent if selected else "transparent",
                text_color="#071116" if selected else t.muted,
                border_color=t.accent if selected else t.glow,
            )
        if self.duration_label:
            self.duration_label.configure(text=f"{key}:00")
        work, brk, name, long_break, every, cycles, blurb, preset_key = self.PRESETS[key]
        a.set_preset(work, brk, name, long_break=long_break, long_every=every, cycles=cycles, blurb=blurb, key=preset_key)

    def toggle_sound(self):
        if self._sound_open:
            self.sound_drawer.grid_forget()
            self.sound_button.configure(text="Sound  ·  optional")
            self._sound_open = False
            return

        a = self.app
        t = a.theme
        for child in self.sound_drawer.winfo_children():
            child.destroy()
        self.music_entry = ctk.CTkEntry(
            self.sound_drawer,
            height=44,
            corner_radius=15,
            border_width=1,
            border_color=t.glow,
            fg_color=self._blend(t.sidebar, t.bg, 0.25),
            placeholder_text="YouTube / Spotify / direct audio URL",
            font=ctk.CTkFont(size=12),
        )
        self.music_entry.pack(fill="x", pady=(2, 8))
        try:
            current = a.entry_music.get().strip()
            if current:
                self.music_entry.insert(0, current)
        except Exception:
            pass

        actions = ctk.CTkFrame(self.sound_drawer, fg_color="transparent")
        actions.pack(fill="x")
        ctk.CTkButton(
            actions, text="Ambient", width=88, height=32, corner_radius=16,
            fg_color="transparent", hover_color=t.glow,
            border_width=1, border_color=t.glow, text_color=t.muted,
            command=a.workspace.open_soundscape,
        ).pack(side="left")
        ctk.CTkLabel(
            actions, text="Music stays secondary to the task.",
            font=ctk.CTkFont(size=10), text_color=t.muted,
        ).pack(side="right")

        self.sound_drawer.grid(row=7, column=0, padx=42, sticky="ew")
        self.sound_button.configure(text="Sound  ·  hide")
        self._sound_open = True

    def start_focus(self):
        a = self.app
        intention = (self.intent_entry.get() if self.intent_entry else "").strip()
        try:
            a.entry_intention.delete(0, tk.END)
            a.entry_intention.insert(0, intention)
        except Exception:
            pass
        if self.music_entry is not None:
            url = self.music_entry.get().strip()
            try:
                a.entry_music.delete(0, tk.END)
                a.entry_music.insert(0, url)
            except Exception:
                pass
        a._calm_focus = True
        a.start_immersive_timer()

    # ------------------------------------------------------------ focus screen
    def place_focus_chrome(self):
        a = self.app
        visible = a.mode == "Break" or a.is_paused or a._menu_open
        try:
            a.menu_btn.place_forget()
        except Exception:
            pass

        if visible:
            try:
                a.music_live.place(relx=0.5, rely=0.72, anchor="center")
            except Exception:
                pass
            try:
                a.ctrl_bar.place(relx=0.5, rely=0.89, anchor="center")
            except Exception:
                pass
        else:
            for widget in (a.music_live, a.track_badge, a.hint_text, a.ctrl_bar, a.break_tip_live):
                try:
                    widget.place_forget()
                except Exception:
                    pass

    def draw_focus_canvas(self, frozen=False):
        a = self.app
        c = a.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 10 or h < 10:
            return

        t = a.theme
        motion = 0.0 if a.reduce_motion else (0.25 if frozen else 1.0)
        self._focus_phase += 0.012 * motion

        # Deep gradient: fewer bands = calmer visual field.
        for i in range(12):
            y0 = int(i * h / 12)
            y1 = int((i + 1) * h / 12) + 1
            amount = 0.025 + (i / 11) * 0.18
            c.create_rectangle(0, y0, w, y1, fill=self._blend(t.bg, t.glow, amount), outline="")

        # Two very low-contrast light shafts.
        if not a.reduce_motion:
            for i in range(2):
                x = w * (0.30 + i * 0.38) + math.sin(self._focus_phase + i * 1.9) * 18
                col = self._blend(t.bg, t.accent, 0.055)
                c.create_polygon(x-45, 0, x+10, 0, x+120, h, x-100, h, fill=col, outline="")

        progress = 0.0
        if a.total_seconds > 0:
            progress = max(0.0, min(1.0, 1.0 - a.remaining_seconds / a.total_seconds))

        cx, cy = w / 2, h * 0.40
        radius = min(w, h) * 0.185
        base = self._blend(t.bg, t.glow, 0.60)
        active = t.accent if a.mode == "Work" else t.wave_front_break
        c.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, outline=base, width=2)
        if progress > 0.001:
            c.create_arc(
                cx-radius, cy-radius, cx+radius, cy+radius,
                start=90, extent=-(progress * 359.0), style="arc",
                outline=active, width=4,
            )

        # One intention only; no session badges, no cycle dots, no album artwork.
        intention = (getattr(a, "intention", "") or "").strip()
        if intention and a.mode == "Work":
            text = intention if len(intention) <= 54 else intention[:53] + "…"
            c.create_text(
                cx, h * 0.62, text=text,
                fill=self._blend(t.text, t.muted, 0.35),
                font=(getattr(a, "FONT_UI_BOLD", "Segoe UI"), 11, "bold"),
            )

        # sparse depth particles
        if not a.reduce_motion:
            for i in range(8):
                x = ((i * 149) % max(1, int(w))) + math.sin(self._focus_phase * 1.2 + i) * 12
                y = h - ((self._focus_phase * (18 + i) + i * 83) % (h + 30))
                r = 1 + (i % 2)
                c.create_oval(x-r, y-r, x+r, y+r, fill=self._blend(t.bg, t.particle, 0.35), outline="")

    # -------------------------------------------------------------- secondary
    def open_tools(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title("Aqua Focus · More")
        w.geometry("440x500")
        w.resizable(False, False)
        w.configure(fg_color=t.bg)
        self._dialog_heading(w, "More", "Tools stay here until you need them.")

        items = (
            ("Countdown", "A single timer", a.v2_modes.open_countdown),
            ("Stopwatch", "Open-ended flow", a.v2_modes.open_stopwatch),
            ("Alarm", "One-time reminder", a.v2_modes.open_alarm),
            ("Extensions", "Themes and presets", a.workspace.open_extensions),
            ("Prepare music", "Resolve a stream before focus", a.preload_music),
        )
        for name, sub, command in items:
            card = ctk.CTkButton(
                w, text=f"{name}\n{sub}", height=56, corner_radius=16,
                fg_color=t.sidebar, hover_color=t.glow,
                border_width=1, border_color=t.glow,
                text_color=t.text, anchor="w",
                font=ctk.CTkFont(size=11), command=command,
            )
            card.pack(fill="x", padx=24, pady=4)

    def open_settings(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title("Aqua Focus · Settings")
        w.geometry("500x580")
        w.minsize(460, 520)
        w.configure(fg_color=t.bg)

        body = ctk.CTkScrollableFrame(w, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        self._dialog_heading(body, "Settings", "Advanced choices belong here, not on Home.")

        self._section(body, "Appearance")
        theme = ctk.CTkOptionMenu(
            body, values=list(a.THEMES.keys()), command=lambda value: a.apply_theme(value),
            height=40, corner_radius=12,
        )
        theme.set(a.theme.name)
        theme.pack(fill="x", padx=12, pady=(0, 8))

        motion = ctk.BooleanVar(value=bool(a.reduce_motion))
        def set_motion():
            a.reduce_motion = bool(motion.get())
            a.settings.set("reduce_motion", a.reduce_motion)
        ctk.CTkSwitch(
            body, text="Reduce motion", variable=motion,
            command=set_motion, progress_color=t.accent, text_color=t.text,
        ).pack(anchor="w", padx=12, pady=8)

        self._section(body, "Audio")
        ctk.CTkButton(
            body, text="Choose / refresh audio output", height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=self._audio_settings,
        ).pack(fill="x", padx=12, pady=5)

        self._section(body, "Focus")
        ctk.CTkButton(
            body, text="Temptation guard settings", height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.open_temptation_exclude_dialog,
        ).pack(fill="x", padx=12, pady=5)

        self._section(body, "App")
        ctk.CTkButton(
            body, text="Check for updates", height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a._agiu_check_manual,
        ).pack(fill="x", padx=12, pady=5)

    def _audio_settings(self):
        a = self.app
        a._refresh_audio_device_menu()
        # Legacy selector remains the source of truth. Show it briefly in a tiny modal.
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title("Audio output")
        w.geometry("480x190")
        w.configure(fg_color=t.bg)
        self._dialog_heading(w, "Audio output", "Select where focus audio should play.")
        values = [a.t("audio_pick")] + list(a._audio_device_map.keys())
        menu = ctk.CTkOptionMenu(w, values=values, command=a._on_audio_device_change)
        menu.pack(fill="x", padx=24, pady=10)

    def _dialog_heading(self, parent, title, subtitle):
        t = self.app.theme
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(size=24, weight="bold"), text_color=t.text,
        ).pack(anchor="w", padx=24, pady=(24, 3))
        ctk.CTkLabel(
            parent, text=subtitle,
            font=ctk.CTkFont(size=11), text_color=t.muted,
        ).pack(anchor="w", padx=24, pady=(0, 15))

    def _section(self, parent, text):
        ctk.CTkLabel(
            parent, text=text.upper(),
            font=ctk.CTkFont(size=9, weight="bold"),
            text_color=self.app.theme.accent,
        ).pack(anchor="w", padx=12, pady=(18, 7))

    @staticmethod
    def _hex_to_rgb(value):
        value = value.lstrip("#")
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))

    @classmethod
    def _blend(cls, a, b, amount):
        ar, ag, ab = cls._hex_to_rgb(a)
        br, bg, bb = cls._hex_to_rgb(b)
        amount = max(0.0, min(1.0, amount))
        return "#%02x%02x%02x" % (
            int(ar + (br-ar)*amount),
            int(ag + (bg-ag)*amount),
            int(ab + (bb-ab)*amount),
        )
