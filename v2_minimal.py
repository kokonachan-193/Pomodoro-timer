"""Minimal v2.1 shell for Aqua Focus.

Keeps advanced features available while making the default surface intentionally sparse.
"""

from __future__ import annotations

import customtkinter as ctk


class MinimalShell:
    def __init__(self, app):
        self.app = app
        self.nav_buttons = []
        self.quick_buttons = []

    def install(self):
        a = self.app
        t = a.theme

        # ----- Sidebar: hide the legacy control stack, keep it alive for compatibility.
        for child in list(a.sidebar.winfo_children()):
            try:
                child.pack_forget()
            except Exception:
                try:
                    child.grid_forget()
                except Exception:
                    pass

        try:
            a.sidebar.configure(width=190, corner_radius=0, border_width=0)
        except Exception:
            pass

        brand = ctk.CTkFrame(a.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=(22, 24))
        ctk.CTkLabel(
            brand,
            text="AQUA",
            font=ctk.CTkFont(family=a.FONT_UI_BOLD if hasattr(a, "FONT_UI_BOLD") else "Segoe UI", size=22, weight="bold"),
            text_color=t.text,
        ).pack(anchor="w")
        ctk.CTkLabel(
            brand,
            text="focus, quietly.",
            font=ctk.CTkFont(size=11),
            text_color=t.muted,
        ).pack(anchor="w", pady=(1, 0))

        self._nav(a.sidebar, "Focus", lambda: self._home())
        self._nav(a.sidebar, "Tasks", a.workspace.open_tasks)
        self._nav(a.sidebar, "Stats", a.workspace.open_stats)
        self._nav(a.sidebar, "Sound", a.workspace.open_soundscape)

        ctk.CTkFrame(a.sidebar, height=1, fg_color=t.glow).pack(fill="x", padx=16, pady=14)
        self._nav(a.sidebar, "More", self.open_tools, quiet=True)
        self._nav(a.sidebar, "Settings", self.open_settings, quiet=True)

        # ----- Home: remove dashboard clutter.
        for widget_name in (
            "hero_label", "hero_sub", "mode_launcher", "science_row", "science_note",
            "rhythm_panel", "inputs_row",
        ):
            widget = getattr(a, widget_name, None)
            if widget is not None:
                try:
                    widget.pack_forget()
                except Exception:
                    pass

        # Ocean hero becomes a restrained header instead of a large dashboard block.
        try:
            a.ocean_hero.configure(height=112)
            a.ocean_hero.pack_configure(pady=(18, 16))
        except Exception:
            pass

        # Insert compact session picker before the intention card.
        self.session_bar = ctk.CTkFrame(
            a.setup_frame,
            fg_color="transparent",
        )
        try:
            self.session_bar.pack(fill="x", pady=(0, 10), before=a.intention_panel)
        except Exception:
            self.session_bar.pack(fill="x", pady=(0, 10))

        left = ctk.CTkFrame(self.session_bar, fg_color="transparent")
        left.pack(side="left")
        ctk.CTkLabel(
            left, text="Session",
            font=ctk.CTkFont(size=11),
            text_color=t.muted,
        ).pack(side="left", padx=(0, 10))

        for label, args in (
            ("25", (25, 5, "25 / 5", 15, 4, 4, "Classic focus", "classic")),
            ("50", (50, 10, "50 / 10", 20, 2, 3, "Long focus", "balanced")),
            ("90", (90, 20, "90 / 20", 20, 1, 1, "Deep work", "ultradian")),
        ):
            b = ctk.CTkButton(
                left,
                text=label,
                width=50,
                height=34,
                corner_radius=17,
                fg_color="transparent",
                border_width=1,
                border_color=t.glow,
                hover_color=t.glow,
                text_color=t.text,
                command=lambda x=args: self._preset(x),
            )
            b.pack(side="left", padx=3)
            self.quick_buttons.append(b)

        self.deep_btn = ctk.CTkButton(
            self.session_bar,
            text="Deep Dive",
            width=98,
            height=34,
            corner_radius=17,
            fg_color="transparent",
            border_width=1,
            border_color=t.accent,
            hover_color=t.glow,
            text_color=t.accent,
            command=a.start_deep_dive_mode,
        )
        self.deep_btn.pack(side="right")

        # Simplify task card.
        try:
            a.intention_panel.configure(corner_radius=22, border_width=1, border_color=t.glow)
            a.intention_badge.pack_forget()
            a.intention_title_lbl.configure(text="What are you focusing on?", font=ctk.CTkFont(size=15, weight="bold"))
            a.intention_sub_lbl.pack_forget()
            a.entry_intention.configure(height=48, corner_radius=14)
        except Exception:
            pass

        # Simplify music card to a single URL/search field + volume.
        try:
            a.music_panel.configure(corner_radius=22, border_width=1, border_color=t.glow)
            a.music_title_lbl.configure(text="Soundtrack", font=ctk.CTkFont(size=15, weight="bold"))
            a.music_hint_lbl.configure(text="YouTube, playlist, or direct audio")
            a.add_playlist_btn.pack_forget()
            a.playlist_count_label.pack_forget()
            a.now_preview.pack_forget()
            a.music_status_label.pack_forget()
        except Exception:
            pass

        # One primary action. Preload remains available from More / focus menu.
        try:
            a.preload_btn.pack_forget()
            a.start_btn.configure(
                text="Start focus",
                height=58,
                corner_radius=20,
                font=ctk.CTkFont(size=17, weight="bold"),
            )
        except Exception:
            pass

    def _nav(self, parent, label, command, quiet=False):
        t = self.app.theme
        b = ctk.CTkButton(
            parent,
            text=label,
            height=40,
            corner_radius=12,
            fg_color="transparent",
            hover_color=t.glow,
            text_color=t.muted if quiet else t.text,
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold" if not quiet else "normal"),
            command=command,
        )
        b.pack(fill="x", padx=10, pady=2)
        self.nav_buttons.append(b)
        return b

    def _home(self):
        try:
            self.app.setup_frame._parent_canvas.yview_moveto(0)
        except Exception:
            pass

    def _preset(self, args):
        work, brk, name, long_break, every, cycles, blurb, key = args
        self.app.set_preset(
            work, brk, name,
            long_break=long_break,
            long_every=every,
            cycles=cycles,
            blurb=blurb,
            key=key,
        )

    def open_tools(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title("Aqua Focus · More")
        w.geometry("440x470")
        w.resizable(False, False)
        w.configure(fg_color=t.bg)
        ctk.CTkLabel(
            w, text="More tools",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=t.text,
        ).pack(anchor="w", padx=24, pady=(24, 4))
        ctk.CTkLabel(
            w, text="Only open these when you need them.",
            font=ctk.CTkFont(size=11), text_color=t.muted,
        ).pack(anchor="w", padx=24, pady=(0, 18))

        tools = (
            ("Countdown", a.v2_modes.open_countdown),
            ("Stopwatch", a.v2_modes.open_stopwatch),
            ("Alarm", a.v2_modes.open_alarm),
            ("Extensions", a.workspace.open_extensions),
            ("Prepare music", a.preload_music),
        )
        for label, command in tools:
            ctk.CTkButton(
                w, text=label, height=44, corner_radius=14,
                fg_color=t.sidebar, hover_color=t.glow,
                border_width=1, border_color=t.glow,
                text_color=t.text, anchor="w",
                command=command,
            ).pack(fill="x", padx=24, pady=5)

    def open_settings(self):
        a = self.app
        t = a.theme
        w = ctk.CTkToplevel(a)
        w.title("Aqua Focus · Settings")
        w.geometry("500x570")
        w.minsize(460, 520)
        w.configure(fg_color=t.bg)

        body = ctk.CTkScrollableFrame(w, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        ctk.CTkLabel(
            body, text="Settings",
            font=ctk.CTkFont(size=25, weight="bold"), text_color=t.text,
        ).pack(anchor="w", padx=12, pady=(8, 18))

        self._section(body, "Appearance")
        theme = ctk.CTkOptionMenu(
            body,
            values=list(a.THEMES.keys()) if hasattr(a, "THEMES") else ["Ocean Depth"],
            command=lambda value: a.apply_theme(value),
        )
        try:
            theme.set(a.theme.name)
        except Exception:
            pass
        theme.pack(fill="x", padx=12, pady=(0, 10))

        motion = ctk.BooleanVar(value=bool(a.reduce_motion))
        def set_motion():
            a.reduce_motion = bool(motion.get())
            a.settings.set("reduce_motion", a.reduce_motion)
        ctk.CTkSwitch(
            body, text="Reduce motion", variable=motion,
            command=set_motion, progress_color=t.accent,
            text_color=t.text,
        ).pack(anchor="w", padx=12, pady=8)

        self._section(body, "Focus")
        calm = ctk.BooleanVar(value=bool(getattr(a, "_calm_focus", True)))
        def set_calm():
            a._calm_focus = bool(calm.get())
            try:
                a.calm_var.set(a._calm_focus)
            except Exception:
                pass
        ctk.CTkSwitch(
            body, text="Auto-hide controls while focusing", variable=calm,
            command=set_calm, progress_color=t.accent, text_color=t.text,
        ).pack(anchor="w", padx=12, pady=8)

        self._section(body, "App")
        ctk.CTkButton(
            body, text="Check for updates", height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a._agiu_check_manual,
        ).pack(fill="x", padx=12, pady=5)
        ctk.CTkButton(
            body, text="Refresh audio devices", height=40,
            fg_color=t.sidebar, hover_color=t.glow,
            border_width=1, border_color=t.glow,
            command=a._refresh_audio_device_menu,
        ).pack(fill="x", padx=12, pady=5)

    def _section(self, parent, text):
        ctk.CTkLabel(
            parent, text=text.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=self.app.theme.accent,
        ).pack(anchor="w", padx=12, pady=(16, 8))
