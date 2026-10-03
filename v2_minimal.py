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
from PIL import Image, ImageDraw, ImageTk


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
        self._water_photo = None
        self.intent_entry = None
        self.music_entry = None
        self.start_button = None
        self.duration_label = None
        self.rhythm_label = None
        self.sound_drawer = None
        self.shell = None
        self.top = None
        self.brand = None
        self.top_actions = None
        self.focus_card = None
        self.focus_title = None
        self._top_buttons = []
        self._home_resize_after = None
        self.home_bg = None
        self._home_bg_photo = None

    # ------------------------------------------------------------------ home
    def install(self):
        a = self.app
        t = a.theme

        # Idempotent install: only destroy the Home surface that *we* own.
        #
        # Important: do NOT walk main_container.winfo_children() and destroy
        # everything except sidebar/setup_frame.  CTkScrollableFrame is backed
        # by internal wrapper widgets, so the object returned by winfo_children()
        # is not guaranteed to be the same Python object as setup_frame/sidebar.
        # Destroying that wrapper leaves references such as entry_work alive in
        # Python while the underlying Tk command is already gone, which later
        # raises: TclError: invalid command name "...!ctkentry.!entry".
        if self.surface is not None:
            try:
                if self.surface.winfo_exists():
                    self.surface.destroy()
            except Exception:
                pass
            self.surface = None

        # The legacy control surface is the compatibility/backend UI for a large
        # amount of timer, audio, focus-lock and update logic.  Keep it alive and
        # merely hide it.  "Full controls" can reveal the exact same widgets.
        for widget in (getattr(a, "sidebar", None), getattr(a, "setup_frame", None)):
            if widget is not None:
                try:
                    widget.pack_forget()
                except Exception:
                    pass

        self.surface = ctk.CTkFrame(a.main_container, fg_color=t.bg, corner_radius=0)
        self.surface.pack(fill="both", expand=True)
        self.home_bg = tk.Label(self.surface, bd=0, highlightthickness=0, bg=t.bg)
        self.home_bg.place(x=0, y=0, relwidth=1, relheight=1)

        # The minimal shell must remain usable as a genuinely small desktop
        # utility.  The legacy app used 940x640 as its minimum which meant the
        # new compact UI could never actually be compact.
        try:
            a.minsize(500, 500)
        except Exception:
            pass

        # generous at normal sizes, automatically tightened by _apply_home_layout
        shell = ctk.CTkFrame(self.home_bg, fg_color="transparent")
        shell.pack(fill="both", expand=True, padx=30, pady=22)
        self.shell = shell

        top = ctk.CTkFrame(shell, fg_color="transparent", height=44)
        self.top = top
        top.pack(fill="x")
        top.pack_propagate(False)

        brand = ctk.CTkFrame(top, fg_color="transparent")
        self.brand = brand
        brand.pack(side="left")
        ctk.CTkLabel(
            brand, text="Aqua Focus",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=20, weight="bold"),
            text_color=t.text,
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand, text=a.t("home_tagline"),
            font=ctk.CTkFont(size=10), text_color=t.muted,
        ).pack(anchor="w", pady=(1, 0))

        top_actions = ctk.CTkFrame(top, fg_color="transparent")
        self.top_actions = top_actions
        top_actions.pack(side="right")
        stats_btn = self._quiet_button(top_actions, a.t("nav_stats"), a.workspace.open_stats)
        tasks_btn = self._quiet_button(top_actions, a.t("nav_tasks"), a.workspace.open_tasks)
        tools_btn = self._quiet_button(top_actions, "•••", self.open_tools, width=44)
        settings_btn = self._quiet_button(top_actions, a.t("nav_settings"), self.open_settings, width=84)
        stats_btn.pack(side="left", padx=3)
        tasks_btn.pack(side="left", padx=3)
        tools_btn.pack(side="left", padx=3)
        settings_btn.pack(side="left", padx=(3, 0))
        self._top_buttons = [stats_btn, tasks_btn, tools_btn, settings_btn]

        # Responsive content: never use absolute placement here.
        # Fixed place() coordinates caused the card to be clipped on smaller
        # windows and Windows DPI scaling.
        center = ctk.CTkFrame(shell, fg_color="transparent")
        center.pack(fill="both", expand=True, pady=(10, 0))

        focus_card = ctk.CTkFrame(
            center,
            width=660,
            fg_color=self._blend(t.sidebar, t.bg, 0.08),
            corner_radius=26,
            border_width=1,
            border_color=self._blend(t.glow, t.accent, 0.18),
        )
        self.focus_card = focus_card
        focus_card.pack(anchor="n", pady=(14, 0))
        focus_card.pack_propagate(True)
        focus_card.grid_columnconfigure(0, weight=1)

        eyebrow = ctk.CTkLabel(
            focus_card, text=a.t("home_focus_session"),
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=9, weight="bold"),
            text_color=t.accent,
        )
        eyebrow.grid(row=0, column=0, padx=34, pady=(26, 5), sticky="w")

        self.focus_title = ctk.CTkLabel(
            focus_card, text=a.t("home_question"),
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=23, weight="bold"),
            text_color=t.text,
        )
        self.focus_title.grid(row=1, column=0, padx=34, sticky="w")

        self.intent_entry = ctk.CTkEntry(
            focus_card,
            height=50,
            corner_radius=14,
            border_width=1,
            border_color=self._blend(t.glow, t.accent, 0.34),
            fg_color=self._blend(t.sidebar, t.bg, 0.34),
            text_color=t.text,
            placeholder_text=a.t("home_task_ph"),
            font=ctk.CTkFont(size=14),
        )
        self.intent_entry.grid(row=2, column=0, padx=34, pady=(14, 18), sticky="ew")
        self.intent_entry.bind("<Return>", lambda _event: self.start_focus())
        try:
            existing = a.entry_intention.get().strip()
            if existing:
                self.intent_entry.insert(0, existing)
        except Exception:
            pass

        duration_area = ctk.CTkFrame(focus_card, fg_color="transparent")
        duration_area.grid(row=3, column=0, padx=34, sticky="ew")
        ctk.CTkLabel(
            duration_area, text=a.t("home_session"),
            font=ctk.CTkFont(size=11), text_color=t.muted,
        ).pack(side="left")

        chips = ctk.CTkFrame(duration_area, fg_color="transparent")
        chips.pack(side="right")
        for key in ("25", "50", "90"):
            b = ctk.CTkButton(
                chips,
                text=a.t("home_min", n=key),
                width=74,
                height=34,
                corner_radius=17,
                border_width=1,
                font=ctk.CTkFont(size=11, weight="bold"),
                command=lambda k=key: self.select_duration(k),
            )
            b.pack(side="left", padx=4)
            self.duration_buttons[key] = b

        self.duration_label = ctk.CTkLabel(
            focus_card,
            text="50:00",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=60, weight="bold"),
            text_color=t.text,
        )
        self.duration_label.grid(row=4, column=0, pady=(16, 0))

        self.rhythm_label = ctk.CTkLabel(
            focus_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=t.muted,
        )
        self.rhythm_label.grid(row=5, column=0, pady=(0, 12))

        # Secondary information stays collapsed.
        sound_row = ctk.CTkFrame(focus_card, fg_color="transparent")
        sound_row.grid(row=6, column=0, padx=34, sticky="ew")
        self.sound_button = ctk.CTkButton(
            sound_row,
            text=a.t("home_sound_optional"),
            height=32,
            corner_radius=16,
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
            text=a.t("home_start"),
            height=54,
            corner_radius=15,
            fg_color=t.accent,
            hover_color=t.accent_hover,
            text_color="#071116",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD, size=16, weight="bold"),
            command=self.start_focus,
        )
        self.start_button.grid(row=8, column=0, padx=34, pady=(14, 24), sticky="ew")

        # Tiny status line below the focus card.
        self.today_label = ctk.CTkLabel(
            center,
            text=self._today_copy(),
            font=ctk.CTkFont(size=10),
            text_color=t.muted,
        )
        self.today_label.pack(pady=(12, 0))

        self.select_duration(self.selected if self.selected in self.PRESETS else "50")
        a._v3_focus = True

        # Reflow rather than clip when the user drags the window smaller.
        # Debouncing avoids doing expensive font/layout work for every pixel.
        self.surface.bind("<Configure>", self._on_home_resize, add="+")
        self.surface.after(40, self._apply_home_layout)

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

    def _on_home_resize(self, _event=None):
        if self.surface is None:
            return
        try:
            if self._home_resize_after is not None:
                self.surface.after_cancel(self._home_resize_after)
        except Exception:
            pass
        try:
            self._home_resize_after = self.surface.after(35, self._apply_home_layout)
        except Exception:
            self._home_resize_after = None

    def _apply_home_layout(self):
        """Continuously adapt Home from full desktop down to a small utility window."""
        if self.surface is None or self.shell is None or self.focus_card is None:
            return
        try:
            w = max(1, int(self.surface.winfo_width()))
            h = max(1, int(self.surface.winfo_height()))
        except Exception:
            return

        compact = w < 700
        very_compact = w < 610
        wide = w >= 1250
        ultra = w >= 1900
        short = h < 620

        outer_x = 12 if very_compact else (18 if compact else (42 if wide else 30))
        outer_y = 10 if short else (32 if wide else 22)
        home_scale = max(0.82, min(1.22, float(self.app.settings.get("home_scale", 1.0) or 1.0)))
        self.refresh_background()
        try:
            self.shell.pack_configure(padx=outer_x, pady=outer_y)
        except Exception:
            pass

        # At compact widths the brand and utility actions become two rows instead
        # of fighting for the same horizontal pixels.
        if self.top is not None and self.brand is not None and self.top_actions is not None:
            try:
                self.brand.pack_forget()
                self.top_actions.pack_forget()
                if very_compact:
                    self.top.configure(height=76)
                    self.brand.pack(side="top", anchor="w")
                    self.top_actions.pack(side="bottom", anchor="e")
                else:
                    self.top.configure(height=44)
                    self.brand.pack(side="left")
                    self.top_actions.pack(side="right")
            except Exception:
                pass

        # Keep the primary card inside the actual viewport.  A CTkFrame width is
        # otherwise allowed to stay at 660px and gets clipped by a smaller window.
        available = max(300, w - (outer_x * 2) - 8)
        if very_compact:
            target = available
        elif compact:
            target = int(available * 0.94)
        elif ultra:
            target = min(900, int(available * 0.48))
        elif wide:
            target = min(820, int(available * 0.52))
        else:
            target = min(700, int(available * 0.68))
        # Never force a 360px card into a viewport that has less room.  The old
        # clamp could still overflow on Windows DPI scaling / tiny windows.
        card_width = max(300, min(int(target * home_scale), available))
        try:
            self.focus_card.configure(width=card_width, corner_radius=22 if compact else 28)
        except Exception:
            pass

        pad = 22 if very_compact else (28 if compact else (44 if wide else 34))
        for widget in (
            getattr(self, "intent_entry", None),
            getattr(self, "start_button", None),
            getattr(self, "sound_button", None),
        ):
            if widget is None:
                continue
            try:
                info = widget.grid_info()
                if info:
                    widget.grid_configure(padx=pad if widget is not self.sound_button else 0)
            except Exception:
                pass

        try:
            self.focus_title.configure(font=ctk.CTkFont(
                family=self.app.FONT_UI_BOLD,
                size=max(16, int((19 if very_compact else (21 if compact else (29 if ultra else (26 if wide else 23)))) * home_scale)),
                weight="bold",
            ))
        except Exception:
            pass
        try:
            self.duration_label.configure(font=ctk.CTkFont(
                family=self.app.FONT_UI_BOLD,
                size=max(40, int((46 if very_compact else (52 if compact else (78 if ultra else (68 if wide else 60)))) * home_scale)),
                weight="bold",
            ))
        except Exception:
            pass

        for button in self._top_buttons:
            try:
                button.configure(
                    height=38 if wide else 34,
                    font=ctk.CTkFont(size=12 if wide else 11),
                )
            except Exception:
                pass

        try:
            if self.start_button is not None:
                self.start_button.configure(height=58 if wide else 52)
            if self.intent_entry is not None:
                self.intent_entry.configure(height=52 if wide else 48)
        except Exception:
            pass

        # Small windows need less vertical air, not smaller hit targets.
        try:
            self.focus_card.pack_configure(pady=(6 if short else 14, 0))
            self.today_label.pack_configure(pady=(7 if short else 12, 0))
        except Exception:
            pass
        self._home_resize_after = None

    def refresh_background(self):
        """Refresh the persisted/theme background behind the clean Home."""
        if self.home_bg is None or self.surface is None:
            return
        try:
            w = max(2, int(self.surface.winfo_width()))
            h = max(2, int(self.surface.winfo_height()))
            photo = self.app._get_bg_photo(w, h)
            self._home_bg_photo = photo
            if photo is not None:
                self.home_bg.configure(image=photo, bg=self.app.theme.bg)
            else:
                self.home_bg.configure(image="", bg=self.app.theme.bg)
        except Exception:
            pass

    def _apply_focus_scale(self):
        """Scale focus typography/controls to the current canvas, with sane touch targets."""
        a = self.app
        try:
            w = max(1, a.canvas.winfo_width())
            h = max(1, a.canvas.winfo_height())
        except Exception:
            return 1.0
        scale = max(0.62, min(1.0, w / 900.0, h / 640.0))
        try:
            a.status_text.configure(font=ctk.CTkFont(
                family=a.FONT_UI_BOLD, size=max(10, int(12 * scale))
            ))
            a.time_text.configure(font=ctk.CTkFont(
                family=a.FONT_UI_BOLD, size=max(56, int(94 * scale)), weight="bold"
            ))
            a.pause_btn.configure(width=max(88, int(112 * scale)))
            a.stop_btn.configure(width=max(78, int(96 * scale)))
        except Exception:
            pass
        return scale

    def _today_copy(self):
        try:
            minutes = self.app.workspace.stats.today_minutes()
        except Exception:
            minutes = 0
        if minutes < 1:
            return self.app.t("today_empty")
        h = int(minutes // 60)
        m = int(minutes % 60)
        if h:
            return self.app.t("today_hm", h=h, m=f"{m:02d}")
        return self.app.t("today_m", m=m)

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
        rhythm_copy = {"25": a.t("rhythm_25"), "50": a.t("rhythm_50"), "90": a.t("rhythm_90")}
        if self.rhythm_label:
            self.rhythm_label.configure(text=rhythm_copy.get(key, a.t("rhythm_custom")))
        work, brk, name, long_break, every, cycles, blurb, preset_key = self.PRESETS[key]
        a.set_preset(work, brk, name, long_break=long_break, long_every=every, cycles=cycles, blurb=blurb, key=preset_key)

    def toggle_sound(self):
        if self._sound_open:
            self.sound_drawer.grid_forget()
            self.sound_button.configure(text=a.t("home_sound_optional"))
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
            placeholder_text=a.t("home_music_ph"),
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
            actions, text=a.t("home_ambient"), width=88, height=32, corner_radius=16,
            fg_color="transparent", hover_color=t.glow,
            border_width=1, border_color=t.glow, text_color=t.muted,
            command=a.workspace.open_soundscape,
        ).pack(side="left")
        ctk.CTkLabel(
            actions, text=a.t("home_music_secondary"),
            font=ctk.CTkFont(size=10), text_color=t.muted,
        ).pack(side="right")

        self.sound_drawer.grid(row=7, column=0, padx=34, sticky="ew")
        self.sound_button.configure(text=a.t("home_sound_hide"))
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


    def refresh_theme(self):
        """Rebuild the visible shell after a theme change without losing user input."""
        a = self.app
        intent = ""
        music = ""
        try:
            intent = self.intent_entry.get().strip() if self.intent_entry else ""
        except Exception:
            pass
        try:
            music = self.music_entry.get().strip() if self.music_entry else ""
        except Exception:
            pass
        if intent:
            try:
                a.entry_intention.delete(0, tk.END)
                a.entry_intention.insert(0, intent)
            except Exception:
                pass
        if music:
            try:
                a.entry_music.delete(0, tk.END)
                a.entry_music.insert(0, music)
            except Exception:
                pass
        if self.surface is not None:
            try:
                self.surface.destroy()
            except Exception:
                pass
        self.surface = None
        self.duration_buttons = {}
        self.intent_entry = None
        self.music_entry = None
        self.start_button = None
        self.duration_label = None
        self.rhythm_label = None
        self.sound_drawer = None
        self.shell = None
        self.top = None
        self.brand = None
        self.top_actions = None
        self.focus_card = None
        self.focus_title = None
        self._top_buttons = []
        self._home_resize_after = None
        self.home_bg = None
        self._home_bg_photo = None
        self._sound_open = False
        self.install()

    # ------------------------------------------------------------ focus screen
    def place_focus_chrome(self):
        a = self.app
        scale = self._apply_focus_scale()
        visible = bool(getattr(a, "_chrome_visible", False)) or a.mode == "Break" or a.is_paused or a._menu_open
        # Keep the two most useful in-session actions one tap away: direct music
        # add/library access and the rest of the focus menu.  They stay small and
        # pinned to the upper-right so the timer remains visually dominant.
        try:
            a.menu_btn.place(relx=0.975, rely=0.04, anchor="ne")
            a.menu_btn.lift()
        except Exception:
            pass
        try:
            a.focus_music_btn.place(relx=0.925, rely=0.04, anchor="ne")
            a.focus_music_btn.lift()
        except Exception:
            pass

        if visible:
            try:
                a.music_live.place(relx=0.5, rely=0.70 if scale < 0.78 else 0.72, anchor="center")
            except Exception:
                pass
            try:
                a.ctrl_bar.place(relx=0.5, rely=0.86 if scale < 0.78 else 0.89, anchor="center")
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
        scale = self._apply_focus_scale()

        t = a.theme
        motion = 0.0 if a.reduce_motion else (0.25 if frozen else 1.0)
        self._focus_phase += 0.012 * motion

        photo = a._get_bg_photo(w, h)
        if photo is not None:
            c.create_image(0, 0, image=photo, anchor="nw")
        else:
            for i in range(12):
                y0 = int(i * h / 12)
                y1 = int((i + 1) * h / 12) + 1
                amount = 0.025 + (i / 11) * 0.18
                c.create_rectangle(0, y0, w, y1, fill=self._blend(t.bg, t.glow, amount), outline="")

        strength = max(0.25, min(1.8, float(a.settings.get("focus_visual_strength", 1.0) or 1.0)))
        if not a.reduce_motion and a.workspace.extension_enabled("animation-light-shafts"):
            for i in range(2):
                x = w * (0.30 + i * 0.38) + math.sin(self._focus_phase + i * 1.9) * 18
                col = self._blend(t.bg, t.accent, min(0.12, 0.055 * strength))
                c.create_polygon(x-45, 0, x+10, 0, x+120, h, x-100, h, fill=col, outline="")

        progress = 0.0
        if a.total_seconds > 0:
            progress = max(0.0, min(1.0, 1.0 - a.remaining_seconds / a.total_seconds))

        # Aqua progress: during Work, a restrained waterline rises with elapsed
        # focus time. It sits behind the timer and is disabled by Reduce Motion.
        # On breaks the surface relaxes back down so the metaphor stays readable.
        # Water is a translucent body, not a rising frame. Multiple blended
        # layers create a glassy depth while the top edge remains a living wave.
        if a.workspace.extension_enabled("animation-rising-water"):
            if a.mode == "Work":
                level_progress = progress
            else:
                level_progress = max(0.0, 0.16 - progress * 0.16)

            water_y = h * (0.95 - 0.58 * level_progress)
            wave_amp = 0.0 if a.reduce_motion else max(3.0, h * 0.008 * strength)
            segments = 42

            # Use one base wave for both layers so the rear crest can never
            # cross the front crest or form broken spikes as phases drift.
            main_surface = []
            back_surface = []
            back_gap = max(6.0, 9.0 * strength)
            for i in range(segments + 1):
                x = w * i / segments
                nx = i / segments
                phase = self._focus_phase * 2.55 + nx * math.tau * 2.65
                primary = math.sin(phase) * wave_amp
                secondary = math.sin(phase * 0.52 + 0.9) * wave_amp * 0.22
                y = water_y + primary + secondary
                main_surface.append((x, y))
                rear_ripple = math.sin(phase + 0.8) * wave_amp * 0.16
                back_surface.append((x, y + back_gap + rear_ripple))

            # True RGBA water overlay: the selected Focus background remains
            # visible through the water instead of being replaced by a solid box.
            try:
                def rgb(value):
                    value = str(value).lstrip("#")
                    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
                wr, wg, wb = rgb(t.accent)
                overlay = Image.new("RGBA", (max(1, int(w)), max(1, int(h))), (0, 0, 0, 0))
                draw = ImageDraw.Draw(overlay, "RGBA")
                back_poly = [(0, int(h))] + [(int(x), int(y)) for x, y in back_surface] + [(int(w), int(h))]
                main_poly = [(0, int(h))] + [(int(x), int(y)) for x, y in main_surface] + [(int(w), int(h))]
                draw.polygon(back_poly, fill=(wr, wg, wb, max(22, min(72, int(42 * strength)))))
                draw.polygon(main_poly, fill=(wr, wg, wb, max(34, min(108, int(68 * strength)))))
                self._water_photo = ImageTk.PhotoImage(overlay)
                c.create_image(0, 0, image=self._water_photo, anchor="nw")
            except Exception:
                main_poly = [(0, h)] + main_surface + [(w, h)]
                c.create_polygon(
                    *[v for p in main_poly for v in p],
                    fill=self._blend(t.bg, t.accent, min(0.32, 0.16 * strength)),
                    outline=""
                )

            depth = max(1, int(h - water_y))
            # Repaint the animated water surface on top of the translucent body.
            crest = []
            for x, y in main_surface:
                crest.extend((x, y))
            c.create_line(
                *crest,
                fill=self._blend(t.bg, t.accent, min(0.82, 0.54 * strength)),
                width=max(2, int(3 * strength)),
                smooth=False
            )
            crest2 = []
            for x, y in back_surface:
                crest2.extend((x, y))
            c.create_line(
                *crest2,
                fill=self._blend(t.bg, t.glow, min(0.62, 0.28 * strength)),
                width=max(1, int(2 * strength)),
                smooth=False
            )

            if not a.reduce_motion and a.workspace.extension_enabled("animation-caustics"):
                for j in range(5):
                    y = water_y + 28 + j * max(18, depth / 7)
                    pts = []
                    for i in range(15):
                        x = w * i / 14
                        yy = y + math.sin(self._focus_phase * 2.0 + i * 0.8 + j) * (4 + j)
                        pts.extend((x, yy))
                    c.create_line(
                        *pts,
                        fill=self._blend(t.bg, t.accent, 0.24),
                        width=1,
                        smooth=True
                    )

            if not a.reduce_motion and a.workspace.extension_enabled("animation-bubbles"):
                for i in range(max(6, int(14 * strength))):
                    x = ((i * 113) % max(1, int(w))) + math.sin(self._focus_phase + i) * 14
                    travel = (self._focus_phase * (42 + i * 2) + i * 71) % max(1, depth + 70)
                    y = h - travel
                    if y < water_y + 8:
                        continue
                    r = 1.5 + (i % 4) * 0.7
                    edge = self._blend(t.bg, t.text, 0.34)
                    c.create_oval(x-r, y-r, x+r, y+r, outline=edge, width=1)

            if not a.reduce_motion and a.workspace.extension_enabled("animation-bioluminescence"):
                for i in range(max(4, int(9 * strength))):
                    x = ((i * 173 + 57) % max(1, int(w))) + math.sin(self._focus_phase * 0.8 + i) * 22
                    y = water_y + 35 + ((i * 89 + self._focus_phase * (16 + i)) % max(1, depth - 30))
                    r = 1 + (i % 3)
                    glow = self._blend(t.bg, t.particle, 0.70)
                    c.create_oval(x-r*2, y-r*2, x+r*2, y+r*2, fill=self._blend(t.bg, glow, 0.30), outline="")
                    c.create_oval(x-r, y-r, x+r, y+r, fill=glow, outline="")

        cx, cy = w / 2, h * 0.40
        radius = min(w, h) * (0.17 if scale < 0.78 else 0.185)
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
        if not a.reduce_motion and a.workspace.extension_enabled("animation-depth-particles"):
            for i in range(max(2, int(8 * strength))):
                x = ((i * 149) % max(1, int(w))) + math.sin(self._focus_phase * 1.2 + i) * 12
                y = h - ((self._focus_phase * (18 + i) + i * 83) % (h + 30))
                r = 1 + (i % 2)
                c.create_oval(x-r, y-r, x+r, y+r, fill=self._blend(t.bg, t.particle, 0.35), outline="")

    # -------------------------------------------------------------- secondary
    def open_tools(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title(f"Aqua Focus · {a.t('more_title')}")
        w.geometry("520x650")
        w.minsize(460, 500)
        w.configure(fg_color=t.bg)

        body = ctk.CTkScrollableFrame(w, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=10)
        self._dialog_heading(body, a.t("more_title"), a.t("more_subtitle"))

        groups = (
            (a.t("group_focus_tools"), (
                (a.t("deep_dive"), a.t("deep_dive_desc"), a.start_deep_dive_mode),
                (a.t("custom_session"), a.t("custom_session_desc"), self.open_custom_session),
                (a.t("countdown"), a.t("countdown_desc"), a.v2_modes.open_countdown),
                (a.t("stopwatch"), a.t("stopwatch_desc"), a.v2_modes.open_stopwatch),
                (a.t("alarm"), a.t("alarm_desc"), a.v2_modes.open_alarm),
            )),
            (a.t("group_workspace"), (
                (a.t("nav_tasks"), a.t("tasks_desc"), a.workspace.open_tasks),
                (a.t("nav_stats"), a.t("stats_desc"), a.workspace.open_stats),
                (a.t("extensions_title"), a.t("extensions_desc"), a.workspace.open_extensions),
            )),
            (a.t("group_music_sound"), (
                (a.t("music_library"), a.t("music_library_desc"), self.open_music_library),
                (a.t("ambient_sound"), a.t("ambient_sound_desc"), a.workspace.open_soundscape),
                (a.t("preload_music"), a.t("prepare_music_desc"), a.preload_music),
            )),
            (a.t("group_advanced"), (
                (a.t("full_controls"), a.t("full_controls_desc"), self.open_advanced_workspace),
                (a.t("nav_settings"), a.t("settings_desc"), self.open_settings),
            )),
        )
        for group, items in groups:
            self._section(body, group)
            for name, sub, command in items:
                card = ctk.CTkButton(
                    body, text=f"{name}\n{sub}", height=56, corner_radius=16,
                    fg_color=t.sidebar, hover_color=t.glow,
                    border_width=1, border_color=t.glow,
                    text_color=t.text, anchor="w",
                    font=ctk.CTkFont(size=11), command=command,
                )
                card.pack(fill="x", padx=12, pady=4)

    def open_music_library(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title(f"Aqua Focus · {a.t('music_library')}")
        w.geometry("620x560")
        w.minsize(520, 440)
        w.configure(fg_color=t.bg)
        self._dialog_heading(w, a.t("music_library"), a.t("music_library_subtitle"))

        composer = ctk.CTkFrame(w, fg_color="transparent")
        composer.pack(fill="x", padx=24, pady=(0, 10))
        url = ctk.CTkEntry(
            composer, height=42, corner_radius=13,
            placeholder_text=a.t("home_music_ph"),
        )
        url.pack(side="left", fill="x", expand=True, padx=(0, 8))

        transport = ctk.CTkFrame(w, fg_color="transparent")
        transport.pack(fill="x", padx=24, pady=(0, 10))
        ctk.CTkButton(
            transport, text=a.t("previous"), width=92, height=34,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.playlist_prev_track,
        ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(
            transport, text=a.t("next"), width=92, height=34,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.playlist_next_track,
        ).pack(side="left", padx=6)
        continuous = ctk.BooleanVar(value=bool(a.playlist.continuous))
        def set_continuous():
            a.playlist.continuous = bool(continuous.get())
            a.playlist.save()
        ctk.CTkSwitch(
            transport, text=a.t("continuous"), variable=continuous,
            command=set_continuous, progress_color=t.accent,
            text_color=t.muted,
        ).pack(side="right")

        body = ctk.CTkScrollableFrame(w, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        def render():
            for child in body.winfo_children():
                child.destroy()
            if not a.playlist.tracks:
                ctk.CTkLabel(
                    body, text=a.t("playlist_empty"), text_color=t.muted
                ).pack(pady=24)
                return
            for i, track in enumerate(list(a.playlist.tracks)):
                row = ctk.CTkFrame(body, fg_color=t.sidebar, corner_radius=14)
                row.pack(fill="x", padx=4, pady=4)
                title = track.title or track.url
                ctk.CTkLabel(
                    row, text=title[:58], anchor="w", text_color=t.text
                ).pack(side="left", fill="x", expand=True, padx=12, pady=10)
                ctk.CTkButton(
                    row, text=a.t("play"), width=58, height=30,
                    fg_color=t.glow, hover_color=t.accent_hover,
                    command=lambda idx=i: a.playlist_play_index(idx),
                ).pack(side="left", padx=4)
                ctk.CTkButton(
                    row, text="×", width=32, height=30,
                    fg_color="transparent", hover_color="#5b2c36",
                    command=lambda idx=i: (a.playlist_remove_index(idx), render()),
                ).pack(side="left", padx=(0, 8))

        def add():
            value = url.get().strip()
            if not value:
                return
            try:
                a.entry_music.delete(0, tk.END)
                a.entry_music.insert(0, value)
                a.add_current_url_to_playlist()
                url.delete(0, tk.END)
                render()
            except Exception:
                pass

        ctk.CTkButton(
            composer, text=a.t("add"), width=72, height=42,
            fg_color=t.accent, hover_color=t.accent_hover,
            text_color="#071116", command=add,
        ).pack(side="right")
        url.bind("<Return>", lambda _event: add())
        render()

    def open_advanced_workspace(self):
        """Reveal the full legacy control surface as a safety-net for every feature."""
        a = self.app
        try:
            if self.surface is not None:
                self.surface.pack_forget()
            a.sidebar.pack(side="left", fill="y", padx=(12, 0), pady=12)
            a.setup_frame.pack(side="right", fill="both", expand=True, padx=(20, 12), pady=12)
        except Exception:
            return

        back = getattr(self, "_advanced_back", None)
        if back is None or not back.winfo_exists():
            back = ctk.CTkButton(
                a.main_container,
                text=a.t("clean_home"),
                width=112,
                height=36,
                corner_radius=18,
                fg_color=a.theme.accent,
                hover_color=a.theme.accent_hover,
                text_color="#071116",
                font=ctk.CTkFont(size=11, weight="bold"),
                command=self.close_advanced_workspace,
            )
            self._advanced_back = back
        back.place(relx=0.985, rely=0.985, anchor="se")
        back.lift()

    def close_advanced_workspace(self):
        a = self.app
        try:
            a.sidebar.pack_forget()
            a.setup_frame.pack_forget()
        except Exception:
            pass
        try:
            if getattr(self, "_advanced_back", None) is not None:
                self._advanced_back.place_forget()
        except Exception:
            pass
        if self.surface is None or not self.surface.winfo_exists():
            self.install()
        else:
            self.surface.pack(fill="both", expand=True)
            self._apply_home_layout()

    def open_custom_session(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title(f"Aqua Focus · {a.t('custom_session')}")
        w.geometry("440x360")
        w.resizable(False, False)
        w.configure(fg_color=t.bg)
        self._dialog_heading(w, a.t("custom_session"), a.t("custom_session_subtitle"))

        grid = ctk.CTkFrame(w, fg_color="transparent")
        grid.pack(fill="x", padx=24, pady=8)
        fields = []
        for label, default in ((a.t("focus_minutes"), "45"), (a.t("break_minutes"), "10"), (a.t("cycles"), "2")):
            row = ctk.CTkFrame(grid, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=label, width=130, anchor="w", text_color=t.muted).pack(side="left")
            entry = ctk.CTkEntry(row, height=38, corner_radius=12)
            entry.insert(0, default)
            entry.pack(side="right", fill="x", expand=True)
            fields.append(entry)

        def apply_and_start():
            try:
                work = max(1, float(fields[0].get()))
                rest = max(1, float(fields[1].get()))
                cycles = max(1, int(float(fields[2].get())))
            except ValueError:
                return
            a.set_preset(work, rest, "Custom", long_break=rest, long_every=cycles, cycles=cycles, blurb="Custom rhythm")
            self.selected = ""
            try:
                w.destroy()
            except Exception:
                pass
            self.start_focus()

        ctk.CTkButton(
            w, text=a.t("start_custom_session"), height=48, corner_radius=18,
            fg_color=t.accent, hover_color=t.accent_hover, text_color="#071116",
            font=ctk.CTkFont(size=14, weight="bold"), command=apply_and_start,
        ).pack(fill="x", padx=24, pady=(14, 24))

    def open_settings(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title(f"Aqua Focus · {a.t('nav_settings')}")
        w.geometry("540x680")
        w.minsize(460, 520)
        w.configure(fg_color=t.bg)

        body = ctk.CTkScrollableFrame(w, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        self._dialog_heading(body, a.t("nav_settings"), a.t("settings_subtitle"))

        self._section(body, a.t("appearance"))
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
            body, text=a.t("reduce_motion"), variable=motion,
            command=set_motion, progress_color=t.accent, text_color=t.text,
        ).pack(anchor="w", padx=12, pady=8)

        self._section(body, a.t("audio"))
        ctk.CTkButton(
            body, text=a.t("choose_audio_output"), height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=self._audio_settings,
        ).pack(fill="x", padx=12, pady=5)

        self._section(body, a.t("background"))
        ctk.CTkButton(
            body, text=a.t("choose_background"), height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.pick_background,
        ).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(
            body, text=a.t("reset_background"), height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.reset_background,
        ).pack(fill="x", padx=12, pady=5)

        self._section(body, a.t("customization"))
        ctk.CTkLabel(body, text=a.t("background_dim"), text_color=t.muted).pack(anchor="w", padx=12, pady=(4, 0))
        bg_dim = ctk.CTkSlider(body, from_=0.0, to=0.75, number_of_steps=75, progress_color=t.accent)
        bg_dim.set(float(a.settings.get("background_dim", 0.30) or 0.30))
        def set_bg_dim(value):
            a.settings.set("background_dim", float(value))
            a._bg_photo = None
            a._bg_cache_size = None
            self.refresh_background()
            if a.wave_frame.winfo_ismapped():
                a.draw_waves(frozen=a.is_paused)
        bg_dim.configure(command=set_bg_dim)
        bg_dim.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(body, text=a.t("home_scale"), text_color=t.muted).pack(anchor="w", padx=12, pady=(4, 0))
        home_scale = ctk.CTkSlider(body, from_=0.82, to=1.22, number_of_steps=40, progress_color=t.accent)
        home_scale.set(float(a.settings.get("home_scale", 1.0) or 1.0))
        home_scale.configure(command=lambda value: (a.settings.set("home_scale", float(value)), self._apply_home_layout()))
        home_scale.pack(fill="x", padx=12, pady=(4, 10))

        ctk.CTkLabel(body, text=a.t("focus_visual_strength"), text_color=t.muted).pack(anchor="w", padx=12, pady=(4, 0))
        visual = ctk.CTkSlider(body, from_=0.25, to=1.8, number_of_steps=31, progress_color=t.accent)
        visual.set(float(a.settings.get("focus_visual_strength", 1.0) or 1.0))
        visual.configure(command=lambda value: a.settings.set("focus_visual_strength", float(value)))
        visual.pack(fill="x", padx=12, pady=(4, 10))
        ctk.CTkLabel(body, text=a.t("animations_in_extensions"), text_color=t.muted, wraplength=450, justify="left").pack(anchor="w", padx=12, pady=(2, 8))
        ctk.CTkButton(
            body, text=a.t("open_animation_extensions"), height=40,
            fg_color=t.sidebar, hover_color=t.glow, border_width=1, border_color=t.glow,
            command=a.workspace.open_extensions,
        ).pack(fill="x", padx=12, pady=(0, 8))

        self._section(body, a.t("language"))
        lang = ctk.CTkOptionMenu(
            body,
            values=[a.t("lang_ja"), a.t("lang_en")],
            command=a._on_language_change,
            height=40, corner_radius=12,
        )
        lang.set(a.t("lang_en") if a.i18n.lang == "en" else a.t("lang_ja"))
        lang.pack(fill="x", padx=12, pady=(0, 8))

        self._section(body, a.t("focus"))
        ctk.CTkButton(
            body,
            text=a.t("disable_focus_lock") if a._temptation_armed else a.t("enable_focus_lock"),
            height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.toggle_temptation_guard,
        ).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(
            body, text=a.t("focus_lock_exclusions"), height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a.open_temptation_exclude_dialog,
        ).pack(fill="x", padx=12, pady=5)

        self._section(body, a.t("app"))
        auto_updates = ctk.BooleanVar(value=bool(a.settings.get("agiu_auto_check", True)))
        def set_auto_updates():
            a.settings.set("agiu_auto_check", bool(auto_updates.get()))
        ctk.CTkSwitch(
            body, text=a.t("auto_updates"),
            variable=auto_updates, command=set_auto_updates,
            progress_color=t.accent, text_color=t.text,
        ).pack(anchor="w", padx=12, pady=8)
        ctk.CTkButton(
            body, text=a.t("check_updates"), height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a._agiu_check_manual,
        ).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(
            body, text=a.t("open_full_controls"), height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=lambda: (w.destroy(), self.open_advanced_workspace()),
        ).pack(fill="x", padx=12, pady=5)

    def _audio_settings(self):
        a = self.app
        a._refresh_audio_device_menu()
        # Legacy selector remains the source of truth. Show it briefly in a tiny modal.
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title(a.t("audio_output"))
        w.geometry("480x190")
        w.configure(fg_color=t.bg)
        self._dialog_heading(w, a.t("audio_output"), a.t("audio_output_subtitle"))
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
