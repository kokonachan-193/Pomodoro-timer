from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Ellipse, Line, Mesh, Rectangle
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget
from kivy.utils import platform

try:
    import yt_dlp
except Exception:
    yt_dlp = None

if platform == "android":
    from android.permissions import Permission, request_permissions
    from jnius import autoclass


STRINGS = {
    "ja": {
        "tagline": "ひとつの課題。ひとつのセッション。",
        "question": "この時間で何を終わらせますか？",
        "task_hint": "次にやる具体的な1アクション",
        "start": "集中を始める",
        "pause": "一時停止",
        "resume": "再開",
        "reset": "セッションをリセット",
        "sound": "サウンド",
        "visuals": "Focus演出",
        "water": "半透明の水",
        "bubbles": "気泡",
        "glow": "発光粒子",
        "caustics": "水中の光",
        "ready": "準備完了",
        "focused": "集中中",
        "paused": "一時停止中",
        "today": "今日 · {n} セッション完了",
        "play": "再生",
        "stop": "停止",
        "music_hint": "YouTube / 音声URL",
        "music_focus_only": "音楽はFocus中に使えます",
        "music_paste": "YouTubeまたは音声URLを入力してください",
        "stopped": "停止中",
        "break": "休憩 · 次のブロック前に回復",
        "next_focus": "次の集中ブロック",
        "language": "言語",
    },
    "en": {
        "tagline": "one task. one session.",
        "question": "What will you finish?",
        "task_hint": "One concrete next action",
        "start": "Start focus",
        "pause": "Pause",
        "resume": "Resume",
        "reset": "Reset session",
        "sound": "Sound",
        "visuals": "Focus visuals",
        "water": "Translucent water",
        "bubbles": "Bubbles",
        "glow": "Bioluminescence",
        "caustics": "Caustics",
        "ready": "Ready",
        "focused": "In focus",
        "paused": "Paused",
        "today": "Today · {n} completed sessions",
        "play": "Play",
        "stop": "Stop",
        "music_hint": "YouTube / audio URL",
        "music_focus_only": "Music is available during Focus",
        "music_paste": "Paste a YouTube or direct audio URL",
        "stopped": "Stopped",
        "break": "Break · recover before the next block",
        "next_focus": "Next focus block",
        "language": "Language",
    },
}


class FocusVisual(Widget):
    progress = NumericProperty(0.0)
    running = BooleanProperty(False)
    mode = StringProperty("FOCUS")
    water_enabled = BooleanProperty(True)
    bubbles_enabled = BooleanProperty(True)
    glow_enabled = BooleanProperty(True)
    caustics_enabled = BooleanProperty(True)
    phase = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        for name in (
            "progress", "running", "mode", "water_enabled", "bubbles_enabled",
            "glow_enabled", "caustics_enabled", "phase", "pos", "size"
        ):
            self.bind(**{name: lambda *_: self.redraw()})
        Clock.schedule_interval(self._animate, 1 / 30.0)

    def _animate(self, dt):
        if self.running:
            self.phase += dt
        self.redraw()

    def redraw(self):
        w, h = self.width, self.height
        if w <= 4 or h <= 4:
            return
        x0, y0 = self.x, self.y
        self.canvas.clear()
        with self.canvas:
            # Deep-sea background.
            for i in range(12):
                t = i / 11
                Color(0.018 + t * 0.018, 0.055 + t * 0.045, 0.085 + t * 0.07, 1)
                Rectangle(pos=(x0, y0 + h * i / 12), size=(w, h / 12 + 2))

            # Soft caustic shafts behind the water.
            if self.caustics_enabled:
                for j in range(3):
                    pts = []
                    for i in range(18):
                        x = x0 + w * i / 17
                        y = y0 + h * (0.76 - j * 0.11) + math.sin(self.phase * 0.9 + i * 0.55 + j) * dp(7)
                        pts.extend((x, y))
                    Color(0.38, 0.86, 0.88, 0.11)
                    Line(points=pts, width=1.15)

            p = max(0.0, min(1.0, float(self.progress)))
            if self.water_enabled:
                level = p if self.mode == "FOCUS" else max(0.0, 0.14 - p * 0.14)
                surface_y = y0 + h * (0.06 + 0.58 * level)
                amp = dp(8)
                seg = 40

                def wave(offset=0.0, amp_scale=1.0, shift=0.0):
                    out = []
                    for i in range(seg + 1):
                        x = x0 + w * i / seg
                        y = surface_y + offset + math.sin(self.phase * 2.25 + i * 0.48 + shift) * amp * amp_scale
                        out.append((x, y))
                    return out

                back = wave(dp(8), 0.66, 1.2)
                front = wave(0, 1.0, 0)

                # Triangle strip from wave surface to bottom = true translucent water body.
                vertices = []
                indices = []
                for i, (x, y) in enumerate(back):
                    vertices += [x, y, 0, 0, x, y0, 0, 0]
                    indices += [2*i, 2*i+1]
                Color(0.08, 0.62, 0.78, 0.19)
                Mesh(vertices=vertices, indices=indices, mode="triangle_strip")

                vertices = []
                indices = []
                for i, (x, y) in enumerate(front):
                    vertices += [x, y, 0, 0, x, y0, 0, 0]
                    indices += [2*i, 2*i+1]
                Color(0.08, 0.72, 0.82, 0.28)
                Mesh(vertices=vertices, indices=indices, mode="triangle_strip")

                # Surface crests.
                Color(0.48, 0.95, 0.94, 0.72)
                Line(points=[v for pnt in front for v in pnt], width=1.9)
                Color(0.28, 0.76, 0.88, 0.34)
                Line(points=[v for pnt in back for v in pnt], width=1.1)

                # Underwater caustics.
                if self.caustics_enabled:
                    for j in range(4):
                        pts = []
                        yy = surface_y - dp(36 + j * 34)
                        for i in range(14):
                            xx = x0 + w * i / 13
                            y = yy + math.sin(self.phase * 1.7 + i * 0.72 + j) * dp(4 + j)
                            pts.extend((xx, y))
                        Color(0.55, 0.96, 0.94, 0.13)
                        Line(points=pts, width=1)

                # Bubbles stay under the water surface.
                if self.bubbles_enabled:
                    depth = max(dp(60), surface_y - y0)
                    for i in range(16):
                        bx = x0 + ((i * 97) % max(1, int(w))) + math.sin(self.phase + i) * dp(8)
                        travel = (self.phase * (34 + i * 1.7) + i * 53) % depth
                        by = y0 + travel
                        if by > surface_y - dp(8):
                            continue
                        r = dp(1.5 + (i % 4) * 0.65)
                        Color(0.76, 0.96, 1.0, 0.34)
                        Line(circle=(bx, by, r), width=0.8)

                if self.glow_enabled:
                    depth = max(dp(50), surface_y - y0)
                    for i in range(11):
                        gx = x0 + ((i * 137 + 33) % max(1, int(w))) + math.sin(self.phase * 0.7 + i) * dp(11)
                        gy = y0 + dp(18) + ((i * 71 + self.phase * (12 + i)) % max(dp(20), depth - dp(20)))
                        rr = dp(1.3 + (i % 3) * 0.45)
                        Color(0.43, 0.98, 0.86, 0.17)
                        Ellipse(pos=(gx-rr*3, gy-rr*3), size=(rr*6, rr*6))
                        Color(0.62, 1.0, 0.91, 0.76)
                        Ellipse(pos=(gx-rr, gy-rr), size=(rr*2, rr*2))

            # Circular timer guide.
            cx, cy = x0 + w/2, y0 + h*0.58
            rad = min(w, h) * 0.20
            Color(0.42, 0.68, 0.72, 0.22)
            Line(circle=(cx, cy, rad), width=1.3)
            if p > 0.002:
                Color(0.45, 0.93, 0.88, 0.86)
                Line(circle=(cx, cy, rad, 90, 90 - p * 360), width=2.4)


KV = r"""
#:import dp kivy.metrics.dp

<PrimaryButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.39, .85, .81, 1) if self.state == "normal" else (.31, .72, .69, 1)
    color: .03, .08, .10, 1
    font_size: "15sp"
    bold: True
    size_hint_y: None
    height: dp(54)

<QuietButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.055, .12, .15, .92) if self.state == "normal" else (.08, .17, .20, .95)
    color: .66, .78, .80, 1
    font_size: "12sp"
    size_hint_y: None
    height: dp(40)

<PresetButton@ToggleButton>:
    group: "duration"
    allow_no_selection: False
    background_normal: ""
    background_down: ""
    background_color: (.39, .85, .81, 1) if self.state == "down" else (.055, .12, .15, .92)
    color: (.03, .08, .10, 1) if self.state == "down" else (.67, .78, .80, 1)
    font_size: "12sp"
    bold: True
    size_hint_y: None
    height: dp(38)

<RootView>:
    orientation: "vertical"
    canvas.before:
        Color:
            rgba: .018, .055, .085, 1
        Rectangle:
            pos: self.pos
            size: self.size

    ScrollView:
        do_scroll_x: False
        bar_width: dp(2)
        BoxLayout:
            orientation: "vertical"
            size_hint_y: None
            height: self.minimum_height
            padding: dp(18), dp(18), dp(18), dp(30)
            spacing: dp(14)

            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: dp(48)
                BoxLayout:
                    orientation: "vertical"
                    Label:
                        text: "Aqua Focus"
                        color: .94, .98, .98, 1
                        font_size: "21sp"
                        bold: True
                        text_size: self.size
                        halign: "left"
                        valign: "middle"
                    Label:
                        text: root.t("tagline")
                        color: .49, .61, .64, 1
                        font_size: "10sp"
                        text_size: self.size
                        halign: "left"
                        valign: "top"
                QuietButton:
                    text: "JA / EN"
                    width: dp(76)
                    size_hint_x: None
                    on_release: root.toggle_language()

            Label:
                text: root.t("question")
                color: .94, .98, .98, 1
                font_size: "20sp"
                bold: True
                size_hint_y: None
                height: dp(34)
                text_size: self.size
                halign: "left"

            TextInput:
                id: intention
                hint_text: root.t("task_hint")
                multiline: False
                size_hint_y: None
                height: dp(48)
                foreground_color: .92, .97, .97, 1
                hint_text_color: .43, .56, .59, 1
                background_normal: ""
                background_active: ""
                background_color: .028, .075, .092, .95
                padding: dp(13), dp(13)
                on_text: root.intention = self.text

            BoxLayout:
                size_hint_y: None
                height: dp(40)
                spacing: dp(7)
                PresetButton:
                    text: "25 min"
                    state: "down" if root.work_minutes == 25 else "normal"
                    on_release: root.set_preset(25, 5)
                PresetButton:
                    text: "50 min"
                    state: "down" if root.work_minutes == 50 else "normal"
                    on_release: root.set_preset(50, 10)
                PresetButton:
                    text: "90 min"
                    state: "down" if root.work_minutes == 90 else "normal"
                    on_release: root.set_preset(90, 20)

            FloatLayout:
                size_hint_y: None
                height: dp(470)
                FocusVisual:
                    pos: self.parent.pos
                    size: self.parent.size
                    progress: root.progress
                    running: root.running
                    mode: root.mode
                    water_enabled: root.water_enabled
                    bubbles_enabled: root.bubbles_enabled
                    glow_enabled: root.glow_enabled
                    caustics_enabled: root.caustics_enabled

                Label:
                    text: root.clock_text
                    color: .95, .99, .99, 1
                    font_size: "64sp"
                    bold: True
                    size_hint: .82, None
                    height: dp(92)
                    pos_hint: {"center_x": .5, "center_y": .59}

                Label:
                    text: root.progress_text
                    color: .68, .82, .84, 1
                    font_size: "11sp"
                    size_hint: .82, None
                    height: dp(28)
                    pos_hint: {"center_x": .5, "center_y": .45}

                PrimaryButton:
                    text: root.primary_button_text()
                    size_hint_x: .82
                    pos_hint: {"center_x": .5, "y": .08}
                    on_release: root.toggle_timer()

            QuietButton:
                text: root.t("reset")
                on_release: root.reset_timer()

            QuietButton:
                text: root.t("visuals") + ("   ▴" if root.visuals_open else "   ▾")
                on_release: root.visuals_open = not root.visuals_open

            GridLayout:
                cols: 2
                size_hint_y: None
                height: dp(176) if root.visuals_open else 0
                opacity: 1 if root.visuals_open else 0
                disabled: not root.visuals_open
                row_default_height: dp(42)
                row_force_default: True
                spacing: dp(6)
                Label:
                    text: root.t("water")
                    color: .72, .84, .85, 1
                Switch:
                    active: root.water_enabled
                    on_active: root.water_enabled = self.active
                Label:
                    text: root.t("bubbles")
                    color: .72, .84, .85, 1
                Switch:
                    active: root.bubbles_enabled
                    on_active: root.bubbles_enabled = self.active
                Label:
                    text: root.t("glow")
                    color: .72, .84, .85, 1
                Switch:
                    active: root.glow_enabled
                    on_active: root.glow_enabled = self.active
                Label:
                    text: root.t("caustics")
                    color: .72, .84, .85, 1
                Switch:
                    active: root.caustics_enabled
                    on_active: root.caustics_enabled = self.active

            QuietButton:
                text: root.t("sound") + ("   ▴" if root.sound_open else "   ▾")
                on_release: root.sound_open = not root.sound_open

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(172) if root.sound_open else 0
                opacity: 1 if root.sound_open else 0
                disabled: not root.sound_open
                spacing: dp(8)
                TextInput:
                    id: music_url
                    hint_text: root.t("music_hint")
                    multiline: False
                    size_hint_y: None
                    height: dp(46)
                    foreground_color: .9, .96, .96, 1
                    hint_text_color: .40, .54, .57, 1
                    background_normal: ""
                    background_active: ""
                    background_color: .028, .075, .092, 1
                    padding: dp(12), dp(12)
                Label:
                    text: root.music_status
                    color: .52, .66, .69, 1
                    font_size: "11sp"
                    size_hint_y: None
                    height: dp(24)
                BoxLayout:
                    size_hint_y: None
                    height: dp(40)
                    spacing: dp(8)
                    PrimaryButton:
                        text: root.t("play")
                        height: dp(40)
                        on_release: root.play_music(music_url.text)
                    QuietButton:
                        text: root.t("stop")
                        height: dp(40)
                        on_release: root.stop_music()
                Slider:
                    min: 0
                    max: 1
                    value: root.volume
                    size_hint_y: None
                    height: dp(28)
                    on_value: root.set_volume(self.value)

            Label:
                text: root.t("today").format(n=root.sessions)
                color: .43, .56, .58, 1
                font_size: "11sp"
                size_hint_y: None
                height: dp(30)
"""


class AndroidAudio:
    def __init__(self, status_cb):
        self.status_cb = status_cb
        self.player = None
        self.volume = 0.55

    def _resolve(self, url: str):
        low = url.lower()
        if "spotify.com" in low:
            raise RuntimeError("Spotify full-track playback is not available on Android yet")
        if "youtube.com" in low or "youtu.be" in low or "music.youtube.com" in low:
            if yt_dlp is None:
                raise RuntimeError("yt-dlp is unavailable")
            opts = {
                "format": "bestaudio[protocol^=http][acodec!=none]/bestaudio[acodec!=none]/bestaudio/best",
                "quiet": True, "no_warnings": True, "noplaylist": True,
                "retries": 4, "socket_timeout": 20,
                "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info.get("entries"):
                info = info["entries"][0] or info
            media = info.get("url")
            if not media:
                raise RuntimeError("No playable YouTube audio stream")
            return media, dict(info.get("http_headers") or {}), info.get("title") or "YouTube"
        return url, {"User-Agent": "AquaFocus-Android/2.1.6"}, Path(urlparse(url).path).stem or "Cloud audio"

    def play(self, url: str):
        if platform != "android":
            self.status_cb("Android MediaPlayer is only available on device")
            return
        self.stop()
        self.status_cb("Resolving audio...")

        def worker():
            try:
                media, headers, title = self._resolve(url)
                Clock.schedule_once(lambda _dt: self._start_player(media, headers, title), 0)
            except Exception as exc:
                Clock.schedule_once(lambda _dt, msg=str(exc): self.status_cb("Playback error: " + msg), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _start_player(self, media: str, headers: dict, title: str):
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            MediaPlayer = autoclass("android.media.MediaPlayer")
            Uri = autoclass("android.net.Uri")
            HashMap = autoclass("java.util.HashMap")
            context = PythonActivity.mActivity
            header_map = HashMap()
            for key, value in headers.items():
                if key and value is not None:
                    header_map.put(str(key), str(value))
            self.player = MediaPlayer()
            self.player.setAudioStreamType(3)
            self.player.setDataSource(context, Uri.parse(media), header_map)
            self.player.setLooping(True)
            self.player.setVolume(self.volume, self.volume)
            self.player.prepareAsync()

            def poll_ready(_dt):
                if not self.player:
                    return False
                try:
                    self.player.start()
                    self.status_cb("Playing · " + title[:48])
                    return False
                except Exception:
                    return True
            Clock.schedule_interval(poll_ready, 0.5)
        except Exception as exc:
            self.status_cb("MediaPlayer error: " + str(exc))

    def set_volume(self, value):
        self.volume = max(0.0, min(1.0, float(value)))
        if self.player:
            try:
                self.player.setVolume(self.volume, self.volume)
            except Exception:
                pass

    def stop(self):
        if self.player:
            try: self.player.stop()
            except Exception: pass
            try: self.player.release()
            except Exception: pass
        self.player = None


class RootView(BoxLayout):
    running = BooleanProperty(False)
    mode = StringProperty("FOCUS")
    clock_text = StringProperty("25:00")
    progress_text = StringProperty("準備完了")
    progress = NumericProperty(0)
    work_minutes = NumericProperty(25)
    break_minutes = NumericProperty(5)
    sessions = NumericProperty(0)
    volume = NumericProperty(0.55)
    music_status = StringProperty("停止中")
    intention = StringProperty("")
    sound_open = BooleanProperty(False)
    visuals_open = BooleanProperty(False)
    water_enabled = BooleanProperty(True)
    bubbles_enabled = BooleanProperty(True)
    glow_enabled = BooleanProperty(True)
    caustics_enabled = BooleanProperty(True)
    language = StringProperty("ja")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.remaining = self.work_minutes * 60
        self.total = self.remaining
        self._last_tick = time.monotonic()
        self.audio = AndroidAudio(self._set_music_status)
        Clock.schedule_interval(self._tick, 0.20)

    def t(self, key):
        return STRINGS.get(self.language, STRINGS["en"]).get(key, key)

    def toggle_language(self):
        self.language = "en" if self.language == "ja" else "ja"
        self.progress_text = self.t("focused") if self.running else self.t("ready")
        App.get_running_app().save_state()

    def primary_button_text(self):
        if self.running:
            return self.t("pause")
        if self.progress > 0:
            return self.t("resume")
        return self.t("start")

    def set_preset(self, work, rest):
        self.work_minutes = work
        self.break_minutes = rest
        self.reset_timer()
        App.get_running_app().save_state()

    def toggle_timer(self):
        self.running = not self.running
        self._last_tick = time.monotonic()
        self.progress_text = self.t("focused") if self.running else self.t("paused")

    def reset_timer(self):
        self.running = False
        self.mode = "FOCUS"
        self.remaining = self.work_minutes * 60
        self.total = self.remaining
        self.progress = 0
        self.progress_text = self.t("ready")
        self._sync_clock()
        self.stop_music()

    def _tick(self, _dt):
        now = time.monotonic()
        elapsed = now - self._last_tick
        self._last_tick = now
        if not self.running:
            return
        self.remaining = max(0, self.remaining - elapsed)
        self.progress = 1 - (self.remaining / max(1, self.total))
        self._sync_clock()
        if self.remaining <= 0:
            self._advance()

    def _advance(self):
        if self.mode == "FOCUS":
            self.sessions += 1
            self.mode = "BREAK"
            self.remaining = self.break_minutes * 60
            self.stop_music()
            self.progress_text = self.t("break")
        else:
            self.mode = "FOCUS"
            self.remaining = self.work_minutes * 60
            self.progress_text = self.t("next_focus")
        self.total = self.remaining
        self.progress = 0
        self._sync_clock()
        App.get_running_app().save_state()
        self._notify()

    def _sync_clock(self):
        sec = max(0, int(self.remaining + 0.999))
        self.clock_text = f"{sec // 60:02d}:{sec % 60:02d}"

    def play_music(self, url):
        url = (url or "").strip()
        if not url:
            self.music_status = self.t("music_paste")
            return
        if self.mode != "FOCUS":
            self.music_status = self.t("music_focus_only")
            return
        self.audio.play(url)

    def stop_music(self):
        self.audio.stop()
        self.music_status = self.t("stopped")

    def set_volume(self, value):
        self.volume = float(value)
        self.audio.set_volume(self.volume)

    def _set_music_status(self, text):
        self.music_status = text

    def _notify(self):
        if platform != "android":
            return
        try:
            from plyer import notification
            notification.notify(
                title="Aqua Focus",
                message="Break time" if self.mode == "BREAK" else "Focus time",
                app_name="Aqua Focus",
            )
        except Exception:
            pass


class AquaFocusAndroidApp(App):
    title = "Aqua Focus"

    def build(self):
        Window.clearcolor = (0.018, 0.055, 0.085, 1)
        Builder.load_string(KV)
        root = RootView()
        self.root_view = root
        self._load_state()
        if platform == "android":
            request_permissions([Permission.INTERNET, Permission.POST_NOTIFICATIONS, Permission.WAKE_LOCK])
        return root

    @property
    def state_path(self):
        return Path(self.user_data_dir) / "state.json"

    def _load_state(self):
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
            self.root_view.work_minutes = int(data.get("work", 25))
            self.root_view.break_minutes = int(data.get("break", 5))
            self.root_view.sessions = int(data.get("sessions", 0))
            self.root_view.volume = float(data.get("volume", 0.55))
            self.root_view.language = str(data.get("language", "ja"))
            self.root_view.water_enabled = bool(data.get("water", True))
            self.root_view.bubbles_enabled = bool(data.get("bubbles", True))
            self.root_view.glow_enabled = bool(data.get("glow", True))
            self.root_view.caustics_enabled = bool(data.get("caustics", True))
            self.root_view.audio.set_volume(self.root_view.volume)
            self.root_view.reset_timer()
        except Exception:
            pass

    def save_state(self):
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(json.dumps({
                "work": int(self.root_view.work_minutes),
                "break": int(self.root_view.break_minutes),
                "sessions": int(self.root_view.sessions),
                "volume": float(self.root_view.volume),
                "language": self.root_view.language,
                "water": bool(self.root_view.water_enabled),
                "bubbles": bool(self.root_view.bubbles_enabled),
                "glow": bool(self.root_view.glow_enabled),
                "caustics": bool(self.root_view.caustics_enabled),
            }), encoding="utf-8")
        except Exception:
            pass

    def on_stop(self):
        self.save_state()
        if hasattr(self, "root_view"):
            self.root_view.stop_music()


if __name__ == "__main__":
    AquaFocusAndroidApp().run()
