"""Aqua Focus v2 workspace features: tasks, stats, soundscapes and extension catalog."""

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

import customtkinter as ctk
import tkinter as tk

try:
    import numpy as np
    import sounddevice as sd
except Exception:
    np = None
    sd = None


@dataclass
class TaskItem:
    id: str
    title: str
    done: bool = False
    focused_minutes: float = 0.0
    created_at: str = ""
    completed_at: str = ""


class TaskStore:
    def __init__(self, path: Path):
        self.path = path
        self.items: list[TaskItem] = []
        self.load()

    def load(self):
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            self.items = [TaskItem(**x) for x in raw if isinstance(x, dict)]
        except Exception:
            self.items = []

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps([asdict(x) for x in self.items], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def add(self, title: str) -> TaskItem | None:
        title = (title or "").strip()
        if not title:
            return None
        now = datetime.now().isoformat(timespec="seconds")
        item = TaskItem(id=f"task-{int(time.time()*1000)}", title=title, created_at=now)
        self.items.append(item)
        self.save()
        return item

    def toggle(self, task_id: str):
        for item in self.items:
            if item.id == task_id:
                item.done = not item.done
                item.completed_at = datetime.now().isoformat(timespec="seconds") if item.done else ""
                break
        self.save()

    def delete(self, task_id: str):
        self.items = [x for x in self.items if x.id != task_id]
        self.save()

    def active(self) -> list[TaskItem]:
        return [x for x in self.items if not x.done]

    def completed(self) -> list[TaskItem]:
        return [x for x in self.items if x.done]

    def add_focus(self, title: str, minutes: float):
        title = (title or "").strip()
        if not title:
            return
        low = title.lower()
        for item in self.items:
            if item.title.strip().lower() == low and not item.done:
                item.focused_minutes += max(0.0, float(minutes))
                self.save()
                return


class SessionStats:
    def __init__(self, path: Path):
        self.path = path
        self.sessions: list[dict] = []
        self.load()

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.sessions = data if isinstance(data, list) else []
        except Exception:
            self.sessions = []

    def save(self):
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.sessions, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def record(self, minutes: float, mode: str, task: str = ""):
        if minutes <= 0:
            return
        self.sessions.append({
            "at": datetime.now().isoformat(timespec="seconds"),
            "minutes": round(float(minutes), 2),
            "mode": mode,
            "task": (task or "").strip(),
        })
        self.sessions = self.sessions[-5000:]
        self.save()

    def _date(self, row: dict):
        try:
            return datetime.fromisoformat(row.get("at", "")).date()
        except Exception:
            return None

    def today_minutes(self) -> float:
        today = datetime.now().date()
        return sum(float(x.get("minutes", 0)) for x in self.sessions if self._date(x) == today)

    def week_minutes(self) -> float:
        today = datetime.now().date()
        start = today - timedelta(days=today.weekday())
        return sum(
            float(x.get("minutes", 0))
            for x in self.sessions
            if self._date(x) is not None and start <= self._date(x) <= today
        )

    def total_minutes(self) -> float:
        return sum(float(x.get("minutes", 0)) for x in self.sessions)

    def last_days(self, days: int = 7) -> list[tuple[str, float]]:
        today = datetime.now().date()
        out = []
        for offset in range(days - 1, -1, -1):
            day = today - timedelta(days=offset)
            total = sum(float(x.get("minutes", 0)) for x in self.sessions if self._date(x) == day)
            out.append((day.strftime("%a"), total))
        return out


class AmbientMixer:
    """Synthetic low-volume ambience; independent from the music player."""

    def __init__(self, status_cb: Callable[[str], None] | None = None):
        self.status_cb = status_cb or (lambda _x: None)
        self.kind = "ocean"
        self.volume = 0.0
        self.running = False
        self._stop = threading.Event()
        self._thread = None

    def start(self, kind: str, volume: float):
        self.stop()
        self.kind = kind
        self.volume = max(0.0, min(0.7, float(volume)))
        if self.volume <= 0:
            return
        if sd is None or np is None:
            self.status_cb("sounddevice / numpy unavailable")
            return
        self._stop.clear()
        self.running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self.status_cb(f"Ambient · {kind.title()}")

    def set_volume(self, value: float):
        self.volume = max(0.0, min(0.7, float(value)))

    def stop(self):
        self._stop.set()
        self.running = False
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=0.5)
        self._thread = None

    def _run(self):
        sr = 44100
        block = 2048
        phase = 0.0
        smooth = 0.0
        try:
            with sd.OutputStream(samplerate=sr, channels=2, dtype="float32", blocksize=block) as stream:
                while not self._stop.is_set():
                    t = np.arange(block, dtype=np.float32) / sr
                    white = np.random.normal(0, 1, block).astype(np.float32)
                    if self.kind == "brown":
                        # Gentle Brown-noise approximation.
                        data = np.cumsum(white)
                        data -= data.mean()
                        denom = max(1e-6, float(np.max(np.abs(data))))
                        mono = data / denom
                    elif self.kind == "rain":
                        mono = white * 0.20
                        # sparse soft droplets
                        for _ in range(4):
                            idx = random.randrange(block)
                            mono[idx:min(block, idx+80)] += np.linspace(0.8, 0, min(80, block-idx), dtype=np.float32)
                    else:
                        # ocean: shaped noise + slow wave.
                        kernel = np.ones(48, dtype=np.float32) / 48.0
                        filtered = np.convolve(white, kernel, mode="same")
                        wave = np.sin(2 * math.pi * (0.12 * t + phase)).astype(np.float32)
                        mono = filtered * (0.45 + 0.25 * wave)
                        phase = (phase + block / sr * 0.12) % 1.0
                    mono = np.clip(mono * self.volume * 0.18, -0.9, 0.9)
                    stereo = np.column_stack((mono, mono)).astype(np.float32)
                    stream.write(stereo)
        except Exception as exc:
            self.status_cb(f"Ambient error: {exc}")
        self.running = False


class WorkspacePanels:
    CATALOG_URL = "https://raw.githubusercontent.com/kokonachan-193/Pomodoro-timer/main/extensions/catalog.json"

    def __init__(
        self,
        root,
        *,
        data_dir: Path,
        theme_getter: Callable[[], object],
        font_family: str,
        font_bold: str,
    ):
        self.root = root
        self.theme_getter = theme_getter
        self.font_family = font_family
        self.font_bold = font_bold
        self.tasks = TaskStore(data_dir / "tasks.json")
        self.stats = SessionStats(data_dir / "sessions.json")
        self.ambient = AmbientMixer()
        self.current_task = ""
        self.installed_extensions_path = data_dir / "extensions.json"
        self.installed_extensions: list[dict] = self._load_installed()

    def _theme(self):
        return self.theme_getter()

    def _load_installed(self):
        try:
            raw = json.loads(self.installed_extensions_path.read_text(encoding="utf-8"))
            return raw if isinstance(raw, list) else []
        except Exception:
            return []

    def _save_installed(self):
        try:
            self.installed_extensions_path.parent.mkdir(parents=True, exist_ok=True)
            self.installed_extensions_path.write_text(
                json.dumps(self.installed_extensions, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception:
            pass

    def record_focus_session(self, minutes: float, mode: str, task: str = ""):
        self.stats.record(minutes, mode, task)
        self.tasks.add_focus(task, minutes)

    def _window(self, title: str, geometry="760x610"):
        t = self._theme()
        win = ctk.CTkToplevel(self.root)
        win.title(title)
        win.geometry(geometry)
        win.minsize(620, 480)
        win.configure(fg_color=t.bg)
        return win

    def _heading(self, parent, title: str, subtitle: str):
        t = self._theme()
        ctk.CTkLabel(
            parent, text=title,
            font=ctk.CTkFont(family=self.font_bold, size=28),
            text_color=t.text,
        ).pack(anchor="w", padx=24, pady=(22, 2))
        ctk.CTkLabel(
            parent, text=subtitle,
            font=ctk.CTkFont(family=self.font_family, size=12),
            text_color=t.muted,
        ).pack(anchor="w", padx=24, pady=(0, 16))

    def open_tasks(self):
        t = self._theme()
        win = self._window("Aqua Focus · Coral Tasks")
        self._heading(win, "Coral Tasks", "Keep today's work small, visible and connected to focus time.")

        composer = ctk.CTkFrame(win, fg_color=t.sidebar, corner_radius=18, border_width=1, border_color=t.glow)
        composer.pack(fill="x", padx=24, pady=(0, 10))
        entry = ctk.CTkEntry(composer, height=42, placeholder_text="What is the next concrete task?")
        entry.pack(side="left", fill="x", expand=True, padx=(14, 8), pady=14)

        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(0, 18))

        def render():
            for child in body.winfo_children():
                child.destroy()
            items = self.tasks.active() + self.tasks.completed()
            if not items:
                ctk.CTkLabel(body, text="No tasks yet. Add one small next action.", text_color=t.muted).pack(pady=30)
                return
            for item in items:
                row = ctk.CTkFrame(body, fg_color=t.sidebar, corner_radius=15)
                row.pack(fill="x", padx=6, pady=5)
                check = ctk.CTkCheckBox(
                    row,
                    text=item.title,
                    text_color=t.muted if item.done else t.text,
                    progress_color=t.accent,
                    command=lambda task_id=item.id: (self.tasks.toggle(task_id), render()),
                )
                if item.done:
                    check.select()
                check.pack(side="left", fill="x", expand=True, padx=12, pady=12)
                ctk.CTkLabel(
                    row,
                    text=f"{item.focused_minutes:.0f}m",
                    width=54,
                    text_color=t.accent if item.focused_minutes > 0 else t.muted,
                ).pack(side="left")
                if not item.done:
                    ctk.CTkButton(
                        row,
                        text="Focus",
                        width=66,
                        height=30,
                        fg_color=t.glow,
                        hover_color=t.accent_hover,
                        command=lambda title=item.title: self._select_task(title, win),
                    ).pack(side="left", padx=5)
                ctk.CTkButton(
                    row,
                    text="×",
                    width=34,
                    height=30,
                    fg_color="transparent",
                    hover_color="#6b3030",
                    command=lambda task_id=item.id: (self.tasks.delete(task_id), render()),
                ).pack(side="left", padx=(0, 10))

        def add():
            if self.tasks.add(entry.get()):
                entry.delete(0, tk.END)
                render()

        ctk.CTkButton(
            composer, text="ADD", width=76, height=42,
            fg_color=t.accent, hover_color=t.accent_hover, command=add,
        ).pack(side="right", padx=(0, 14), pady=14)
        entry.bind("<Return>", lambda _e: add())
        render()

    def _select_task(self, title: str, win=None):
        self.current_task = title
        try:
            self.root.entry_intention.delete(0, tk.END)
            self.root.entry_intention.insert(0, title)
            self.root.hero_sub.configure(text=f"Current task · {title}")
        except Exception:
            pass
        if win:
            try:
                win.destroy()
            except Exception:
                pass

    def open_stats(self):
        t = self._theme()
        win = self._window("Aqua Focus · Abyss Stats", "780x620")
        self._heading(win, "Abyss Stats", "A calm view of your focus history — no pressure, just context.")

        cards = ctk.CTkFrame(win, fg_color="transparent")
        cards.pack(fill="x", padx=18, pady=(0, 14))
        values = [
            ("TODAY", self.stats.today_minutes()),
            ("THIS WEEK", self.stats.week_minutes()),
            ("ALL TIME", self.stats.total_minutes()),
        ]
        for title, minutes in values:
            card = ctk.CTkFrame(cards, fg_color=t.sidebar, corner_radius=18, border_width=1, border_color=t.glow)
            card.pack(side="left", fill="x", expand=True, padx=6)
            ctk.CTkLabel(card, text=title, text_color=t.muted, font=ctk.CTkFont(size=10)).pack(pady=(14, 2))
            ctk.CTkLabel(
                card, text=f"{minutes/60:.1f}h",
                text_color=t.text, font=ctk.CTkFont(family=self.font_bold, size=25),
            ).pack(pady=(0, 14))

        canvas = tk.Canvas(win, height=230, bg=t.sidebar, highlightthickness=0)
        canvas.pack(fill="x", padx=24, pady=6)

        def draw(_event=None):
            canvas.delete("all")
            w = max(300, canvas.winfo_width())
            h = max(180, canvas.winfo_height())
            data = self.stats.last_days(7)
            maxv = max([v for _, v in data] + [60.0])
            gap = 16
            bw = (w - gap * 8) / 7
            for i, (day, value) in enumerate(data):
                x0 = gap + i * (bw + gap)
                x1 = x0 + bw
                bar_h = (h - 60) * (value / maxv)
                y0 = h - 34 - bar_h
                y1 = h - 34
                canvas.create_rectangle(x0, y0, x1, y1, fill=t.accent, outline="")
                canvas.create_text((x0+x1)/2, h-18, text=day, fill=t.muted, font=(self.font_family, 9))
                if value > 0:
                    canvas.create_text((x0+x1)/2, y0-10, text=f"{value:.0f}m", fill=t.text, font=(self.font_family, 8))
        canvas.bind("<Configure>", draw)
        win.after(50, draw)

        recent = self.stats.sessions[-8:][::-1]
        box = ctk.CTkScrollableFrame(win, fg_color="transparent", height=180)
        box.pack(fill="both", expand=True, padx=18, pady=(4, 18))
        if not recent:
            ctk.CTkLabel(box, text="Complete a focus session to start building your history.", text_color=t.muted).pack(pady=20)
        for row in recent:
            label = row.get("task") or row.get("mode") or "Focus"
            when = row.get("at", "").replace("T", " ")[:16]
            ctk.CTkLabel(
                box,
                text=f"{when}   {float(row.get('minutes',0)):.0f} min   ·   {label}",
                text_color=t.text,
                anchor="w",
            ).pack(fill="x", padx=8, pady=4)

    def open_soundscape(self):
        t = self._theme()
        win = self._window("Aqua Focus · Ocean Soundscape", "640x480")
        self._heading(win, "Ocean Soundscape", "A second ambient layer that can sit quietly beneath your music.")

        selected = tk.StringVar(value=self.ambient.kind)
        status = ctk.CTkLabel(win, text="Stopped", text_color=t.muted)
        status.pack(anchor="w", padx=26, pady=(0, 8))

        modes = ctk.CTkFrame(win, fg_color="transparent")
        modes.pack(fill="x", padx=20, pady=8)
        for label, value in [("Ocean", "ocean"), ("Rain", "rain"), ("Brown Noise", "brown")]:
            ctk.CTkRadioButton(
                modes, text=label, variable=selected, value=value,
                fg_color=t.accent, hover_color=t.accent_hover, text_color=t.text,
            ).pack(side="left", expand=True, padx=8)

        ctk.CTkLabel(win, text="Ambient volume", text_color=t.muted).pack(anchor="w", padx=26, pady=(18, 4))
        slider = ctk.CTkSlider(win, from_=0, to=0.7, progress_color=t.accent)
        slider.set(0.20)
        slider.pack(fill="x", padx=26)

        def play():
            self.ambient.status_cb = lambda msg: status.configure(text=msg)
            self.ambient.start(selected.get(), float(slider.get()))
        def stop():
            self.ambient.stop()
            status.configure(text="Stopped")
        slider.configure(command=lambda v: self.ambient.set_volume(float(v)))

        row = ctk.CTkFrame(win, fg_color="transparent")
        row.pack(fill="x", padx=24, pady=28)
        ctk.CTkButton(row, text="PLAY AMBIENT", command=play, fg_color=t.accent, hover_color=t.accent_hover).pack(
            side="left", fill="x", expand=True, padx=(0,6)
        )
        ctk.CTkButton(row, text="STOP", command=stop, fg_color=t.glow, hover_color=t.accent_hover).pack(
            side="left", fill="x", expand=True, padx=(6,0)
        )

    def open_extensions(self):
        t = self._theme()
        win = self._window("Aqua Focus · Reef Extensions", "800x640")
        self._heading(win, "Reef Extensions", "Install curated themes, sound profiles and focus presets from the Aqua catalog.")

        status = ctk.CTkLabel(win, text="Loading catalog…", text_color=t.muted)
        status.pack(anchor="w", padx=26, pady=(0, 8))
        body = ctk.CTkScrollableFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(0,18))

        def render(catalog: list[dict]):
            for child in body.winfo_children():
                child.destroy()
            installed_ids = {x.get("id") for x in self.installed_extensions}
            for item in catalog:
                card = ctk.CTkFrame(body, fg_color=t.sidebar, corner_radius=17, border_width=1, border_color=t.glow)
                card.pack(fill="x", padx=5, pady=6)
                left = ctk.CTkFrame(card, fg_color="transparent")
                left.pack(side="left", fill="both", expand=True, padx=14, pady=12)
                ctk.CTkLabel(
                    left, text=item.get("name","Extension"),
                    text_color=t.text, font=ctk.CTkFont(family=self.font_bold, size=15), anchor="w",
                ).pack(fill="x")
                ctk.CTkLabel(
                    left, text=item.get("description",""),
                    text_color=t.muted, wraplength=500, justify="left", anchor="w",
                ).pack(fill="x", pady=(2,0))
                ext_id = item.get("id")
                installed = ext_id in installed_ids
                def toggle(ext=item):
                    eid = ext.get("id")
                    hit = next((x for x in self.installed_extensions if x.get("id")==eid), None)
                    if hit:
                        self.installed_extensions.remove(hit)
                    else:
                        self.installed_extensions.append(ext)
                    self._save_installed()
                    render(catalog)
                ctk.CTkButton(
                    card,
                    text="REMOVE" if installed else "INSTALL",
                    width=92,
                    height=34,
                    fg_color=t.glow if installed else t.accent,
                    hover_color=t.accent_hover,
                    command=toggle,
                ).pack(side="right", padx=14)

        def worker():
            try:
                req = urllib.request.Request(self.CATALOG_URL, headers={"User-Agent":"AquaFocus/2.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    catalog = json.loads(resp.read().decode("utf-8"))
                if not isinstance(catalog, list):
                    raise ValueError("invalid catalog")
                self.root.after(0, lambda: (status.configure(text=f"{len(catalog)} extensions available"), render(catalog)))
            except Exception as exc:
                fallback = [
                    {"id":"theme-jellyfish","name":"Jellyfish Night","type":"theme","description":"A violet deep-sea visual preset."},
                    {"id":"preset-coding90","name":"Coding 90","type":"preset","description":"A 90/20 deep-work preset."},
                    {"id":"sound-rain","name":"Study Rain","type":"sound","description":"Rain-forward ambient profile."},
                ]
                self.root.after(0, lambda: (status.configure(text=f"Offline catalog · {exc}"), render(fallback)))
        threading.Thread(target=worker, daemon=True).start()
