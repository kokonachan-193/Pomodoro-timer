from __future__ import annotations

import json
import math
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
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


FONT_CANDIDATES = (
    "/system/fonts/NotoSansCJK-Regular.ttc",
    "/system/fonts/NotoSansCJKjp-Regular.otf",
    "/system/fonts/NotoSansJP-Regular.otf",
    "/system/fonts/NotoSansJP-VF.ttf",
    "/system/fonts/NotoSans-Regular.ttf",
    "/system/fonts/DroidSansFallback.ttf",
    "/system/fonts/Roboto-Regular.ttf",
)

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
        "font_status_ok": "日本語フォント適用済み",
        "font_status_fallback": "端末標準フォントを使用中",
        "resolving": "音声を準備中…",
        "spotify_unavailable": "Android版ではSpotifyフル再生は未対応です",
        "yt_dlp_missing": "YouTube再生モジュールが見つかりません",
        "no_stream": "再生できる音声ストリームが見つかりません",
        "playback_error": "再生エラー: {msg}",
        "mediaplayer_error": "MediaPlayerエラー: {msg}",
        "playing": "再生中 · {title}",
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
        "font_status_ok": "Japanese-capable font active",
        "font_status_fallback": "Using device default font",
        "resolving": "Resolving audio…",
        "spotify_unavailable": "Spotify full-track playback is not available on Android yet",
        "yt_dlp_missing": "YouTube resolver module is unavailable",
        "no_stream": "No playable audio stream found",
        "playback_error": "Playback error: {msg}",
        "mediaplayer_error": "MediaPlayer error: {msg}",
        "playing": "Playing · {title}",
    },
}


def install_android_font() -> str:
    """Register a Japanese-capable system font when available."""
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            try:
                LabelBase.register(name="AquaJP", fn_regular=str(path))
                return "AquaJP"
            except Exception:
                continue
    return "Roboto"


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

    def _wave_surfaces(self, surface_y: float, width: float, amp: float, seg: int):
        front, back = [], []
        gap = dp(8)
        for i in range(seg + 1):
            x = self.x + width * i / seg
            nx = i / seg
            phase = self.phase * 2.4 + nx * math.tau * 2.45
            primary = math.sin(phase) * amp
            secondary = math.sin(phase * 0.55 + 0.8) * amp * 0.22
            y = surface_y + primary + secondary
            front.append((x, y))
            back.append((x, y + gap + math.sin(phase + 0.8) * amp * 0.14))
        return front, back

    def _mesh_to_bottom(self, surface, bottom_y):
        vertices, indices = [], []
        for i, (x, y) in enumerate(surface):
            vertices += [x, y, 0, 0, x, bottom_y, 0, 0]
            indices += [2 * i, 2 * i + 1]
        return vertices, indices

    def redraw(self):
        w, h = self.width, self.height
        if w <= 4 or h <= 4:
            return
        x0, y0 = self.x, self.y
        self.canvas.clear()
        with self.canvas:
            for i in range(14):
                t = i / 13
                Color(0.014 + t * 0.018, 0.050 + t * 0.045, 0.080 + t * 0.075, 1)
                Rectangle(pos=(x0, y0 + h * i / 14), size=(w, h / 14 + 2))

            if self.caustics_enabled:
                for j in range(3):
                    pts = []
                    for i in range(20):
                        x = x0 + w * i / 19
                        y = y0 + h * (0.78 - j * 0.12) + math.sin(self.phase * 0.8 + i * 0.52 + j) * dp(6)
                        pts.extend((x, y))
                    Color(0.38, 0.86, 0.88, 0.10)
                    Line(points=pts, width=1.0, cap="round", joint="round")

            p = max(0.0, min(1.0, float(self.progress)))
            if self.water_enabled:
                level = p if self.mode == "FOCUS" else max(0.0, 0.14 - p * 0.14)
                surface_y = y0 + h * (0.06 + 0.58 * level)
                amp = dp(7.5)
                front, back = self._wave_surfaces(surface_y, w, amp, 44)

                vertices, indices = self._mesh_to_bottom(back, y0)
                Color(0.08, 0.62, 0.78, 0.16)
                Mesh(vertices=vertices, indices=indices, mode="triangle_strip")

                vertices, indices = self._mesh_to_bottom(front, y0)
                Color(0.08, 0.72, 0.82, 0.27)
                Mesh(vertices=vertices, indices=indices, mode="triangle_strip")

                Color(0.47, 0.95, 0.94, 0.74)
                Line(points=[v for pnt in front for v in pnt], width=1.8, cap="round", joint="round")
                Color(0.30, 0.78, 0.88, 0.32)
                Line(points=[v for pnt in back for v in pnt], width=1.0, cap="round", joint="round")

                depth = max(dp(60), surface_y - y0)

                if self.caustics_enabled:
                    for j in range(4):
                        pts = []
                        yy = surface_y - dp(34 + j * 34)
                        for i in range(15):
                            xx = x0 + w * i / 14
                            y = yy + math.sin(self.phase * 1.55 + i * 0.72 + j) * dp(3.5 + j)
                            pts.extend((xx, y))
                        Color(0.55, 0.96, 0.94, 0.12)
                        Line(points=pts, width=1, cap="round", joint="round")

                if self.bubbles_enabled:
                    for i in range(14):
                        bx = x0 + ((i * 97) % max(1, int(w))) + math.sin(self.phase + i) * dp(8)
                        travel = (self.phase * (30 + i * 1.4) + i * 53) % depth
                        by = y0 + travel
                        if by > surface_y - dp(7):
                            continue
                        r = dp(1.4 + (i % 4) * 0.65)
                        Color(0.76, 0.96, 1.0, 0.32)
                        Line(circle=(bx, by, r), width=0.75)

                if self.glow_enabled:
                    for i in range(9):
                        gx = x0 + ((i * 137 + 33) % max(1, int(w))) + math.sin(self.phase * 0.7 + i) * dp(11)
                        gy = y0 + dp(18) + ((i * 71 + self.phase * (10 + i)) % max(dp(20), depth - dp(20)))
                        rr = dp(1.2 + (i % 3) * 0.45)
                        Color(0.43, 0.98, 0.86, 0.15)
                        Ellipse(pos=(gx - rr * 3, gy - rr * 3), size=(rr * 6, rr * 6))
                        Color(0.62, 1.0, 0.91, 0.70)
                        Ellipse(pos=(gx - rr, gy - rr), size=(rr * 2, rr * 2))

            cx, cy = x0 + w / 2, y0 + h * 0.58
            rad = min(w, h) * 0.20
            Color(0.42, 0.68, 0.72, 0.22)
            Line(circle=(cx, cy, rad), width=1.3)
            if p > 0.002:
                Color(0.45, 0.93, 0.88, 0.86)
                Line(circle=(cx, cy, rad, 90, 90 - p * 360), width=2.4)


KV = r"""
#:import dp kivy.metrics.dp

<Label>:
    font_name: app.font_name
    markup: False
<Button>:
    font_name: app.font_name
<ToggleButton>:
    font_name: app.font_name
<TextInput>:
    font_name: app.font_name
    write_tab: False

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
                height: dp(54)
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
                        text: root.t("tagline", root.language)
                        color: .49, .61, .64, 1
                        font_size: "10sp"
                        text_size: self.size
                        halign: "left"
                        valign: "top"
                QuietButton:
                    text: "JA / EN"
                    width: dp(82)
                    size_hint_x: None
                    on_release: root.toggle_language()

            Label:
                text: root.t("question", root.language)
                color: .94, .98, .98, 1
                font_size: "20sp"
                bold: True
                size_hint_y: None
                height: dp(42)
                text_size: self.size
                halign: "left"
                valign: "middle"

            TextInput:
                id: intention
                hint_text: root.t("task_hint", root.language)
                multiline: False
                size_hint_y: None
                height: dp(50)
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
                height: max(dp(380), min(dp(520), root.height * .52))
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
                    font_size: "60sp"
                    bold: True
                    size_hint: .86, None
                    height: dp(88)
                    pos_hint: {"center_x": .5, "center_y": .60}

                Label:
                    text: root.progress_text
                    color: .68, .82, .84, 1
                    font_size: "12sp"
                    size_hint: .86, None
                    height: dp(34)
                    text_size: self.size
                    halign: "center"
                    valign: "middle"
                    pos_hint: {"center_x": .5, "center_y": .45}

                PrimaryButton:
                    text: root.primary_button_text()
                    size_hint_x: .84
                    pos_hint: {"center_x": .5, "y": .07}
                    on_release: root.toggle_timer()

            QuietButton:
                text: root.t("reset", root.language)
                on_release: root.reset_timer()

            QuietButton:
                text: root.t("visuals", root.language) + ("  -" if root.visuals_open else "  +")
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
                    text: root.t("water", root.language)
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.water_enabled
                    on_active: root.water_enabled = self.active
                Label:
                    text: root.t("bubbles", root.language)
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.bubbles_enabled
                    on_active: root.bubbles_enabled = self.active
                Label:
                    text: root.t("glow", root.language)
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.glow_enabled
                    on_active: root.glow_enabled = self.active
                Label:
                    text: root.t("caustics", root.language)
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.caustics_enabled
                    on_active: root.caustics_enabled = self.active

            QuietButton:
                text: root.t("sound", root.language) + ("  -" if root.sound_open else "  +")
                on_release: root.sound_open = not root.sound_open

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(176) if root.sound_open else 0
                opacity: 1 if root.sound_open else 0
                disabled: not root.sound_open
                spacing: dp(8)
                TextInput:
                    id: music_url
                    hint_text: root.t("music_hint", root.language)
                    multiline: False
                    size_hint_y: None
                    height: dp(48)
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
                    height: dp(28)
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                BoxLayout:
                    size_hint_y: None
                    height: dp(42)
                    spacing: dp(8)
                    PrimaryButton:
                        text: root.t("play", root.language)
                        height: dp(42)
                        on_release: root.play_music(music_url.text)
                    QuietButton:
                        text: root.t("stop", root.language)
                        height: dp(42)
                        on_release: root.stop_music()
                Slider:
                    min: 0
                    max: 1
                    value: root.volume
                    size_hint_y: None
                    height: dp(28)
                    on_value: root.set_volume(self.value)

            Label:
                text: root.t("today", root.language).format(n=root.sessions)
                color: .43, .56, .58, 1
                font_size: "11sp"
                size_hint_y: None
                height: dp(30)

            Label:
                text: root.font_status
                color: .33, .46, .48, 1
                font_size: "10sp"
                size_hint_y: None
                height: dp(24)
"""


class AndroidAudio:
    def __init__(self, root):
        self.root = root
        self.player = None
        self.volume = 0.55

    def _resolve(self, url: str):
        low = url.lower()
        if "spotify.com" in low:
            raise RuntimeError(self.root.t("spotify_unavailable"))
        if "youtube.com" in low or "youtu.be" in low or "music.youtube.com" in low:
            if yt_dlp is None:
                raise RuntimeError(self.root.t("yt_dlp_missing"))
            opts = {
                "format": "bestaudio[protocol^=http][acodec!=none]/bestaudio[acodec!=none]/bestaudio/best",
                "quiet": True,
                "no_warnings": True,
                "noplaylist": True,
                "retries": 4,
                "socket_timeout": 20,
                "extractor_args": {"youtube": {"player_client": ["android", "ios", "web"]}},
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info.get("entries"):
                info = info["entries"][0] or info
            media = info.get("url")
            if not media:
                raise RuntimeError(self.root.t("no_stream"))
            return media, dict(info.get("http_headers") or {}), info.get("title") or "YouTube"
        return url, {"User-Agent": "AquaFocus-Android/2.1.6"}, Path(urlparse(url).path).stem or "Cloud audio"

    def play(self, url: str):
        if platform != "android":
            self.root.music_status = "Android MediaPlayer only"
            return
        self.stop()
        self.root.music_status = self.root.t("resolving")

        def worker():
            try:
                media, headers, title = self._resolve(url)
                self._start_player(media, headers, title)
            except Exception as exc:
                Clock.schedule_once(
                    lambda _dt, msg=str(exc): setattr(self.root, "music_status", self.root.t("playback_error", msg=msg)),
                    0,
                )

        threading.Thread(target=worker, daemon=True).start()

    def _start_player(self, media: str, headers: dict, title: str):
        try:
            MediaPlayer = autoclass("android.media.MediaPlayer")
            Uri = autoclass("android.net.Uri")
            HashMap = autoclass("java.util.HashMap")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            context = PythonActivity.mActivity
            header_map = HashMap()
            for key, value in headers.items():
                if key and value is not None:
                    header_map.put(str(key), str(value))
            player = MediaPlayer()
            player.setAudioStreamType(3)
            player.setDataSource(context, Uri.parse(media), header_map)
            player.setLooping(True)
            player.setVolume(self.volume, self.volume)
            player.prepare()
            player.start()
            self.player = player
            Clock.schedule_once(
                lambda _dt: setattr(self.root, "music_status", self.root.t("playing", title=title[:48])),
                0,
            )
        except Exception as exc:
            Clock.schedule_once(
                lambda _dt, msg=str(exc): setattr(self.root, "music_status", self.root.t("mediaplayer_error", msg=msg)),
                0,
            )

    def set_volume(self, value):
        self.volume = max(0.0, min(1.0, float(value)))
        if self.player:
            try:
                self.player.setVolume(self.volume, self.volume)
            except Exception:
                pass

    def stop(self):
        if self.player:
            try:
                self.player.stop()
            except Exception:
                pass
            try:
                self.player.release()
            except Exception:
                pass
        self.player = None


class RootView(BoxLayout):
    running = BooleanProperty(False)
    mode = StringProperty("FOCUS")
    clock_text = StringProperty("25:00")
    progress_text = StringProperty("")
    progress = NumericProperty(0)
    work_minutes = NumericProperty(25)
    break_minutes = NumericProperty(5)
    sessions = NumericProperty(0)
    volume = NumericProperty(0.55)
    music_status = StringProperty("")
    intention = StringProperty("")
    sound_open = BooleanProperty(False)
    visuals_open = BooleanProperty(False)
    water_enabled = BooleanProperty(True)
    bubbles_enabled = BooleanProperty(True)
    glow_enabled = BooleanProperty(True)
    caustics_enabled = BooleanProperty(True)
    language = StringProperty("ja")
    font_status = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.remaining = self.work_minutes * 60
        self.total = self.remaining
        self._last_tick = time.monotonic()
        self.audio = AndroidAudio(self)
        self.progress_text = self.t("ready")
        self.music_status = self.t("stopped")
        self.font_status = self.t("font_status_fallback")
        Clock.schedule_interval(self._tick, 0.20)

    def t(self, key, *_args, **kwargs):
        template = STRINGS.get(self.language, STRINGS["en"]).get(key, key)
        try:
            return template.format(**kwargs)
        except Exception:
            return template

    def refresh_language_text(self):
        if self.running:
            self.progress_text = self.t("focused")
        elif self.progress > 0:
            self.progress_text = self.t("paused")
        else:
            self.progress_text = self.t("ready")
        if self.music_status in (STRINGS["ja"]["stopped"], STRINGS["en"]["stopped"], ""):
            self.music_status = self.t("stopped")
        ok = App.get_running_app().font_name != "Roboto"
        self.font_status = self.t("font_status_ok" if ok else "font_status_fallback")

    def toggle_language(self):
        self.language = "en" if self.language == "ja" else "ja"
        self.refresh_language_text()
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
        self.font_name = install_android_font()
        Builder.load_string(KV)
        root = RootView()
        self.root_view = root
        self._load_state()
        root.refresh_language_text()
        if platform == "android":
            perms = []
            for name in ("INTERNET", "WAKE_LOCK", "POST_NOTIFICATIONS"):
                value = getattr(Permission, name, None)
                if value is not None:
                    perms.append(value)
            if perms:
                request_permissions(perms)
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
            }, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def on_stop(self):
        self.save_state()
        if hasattr(self, "root_view"):
            self.root_view.stop_music()


if __name__ == "__main__":
    AquaFocusAndroidApp().run()
