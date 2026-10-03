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

APP_VERSION = "2.1.7"
APP_DIR = Path(__file__).resolve().parent

FONT_CANDIDATES = (
    APP_DIR / "assets" / "fonts" / "NotoSansCJK-Regular.ttc",
    APP_DIR / "assets" / "fonts" / "NotoSansJP-Regular.otf",
    APP_DIR / "assets" / "fonts" / "NotoSansJP-Regular.ttf",
    APP_DIR / "assets" / "fonts" / "NotoSans-Regular.ttf",
    Path("/system/fonts/NotoSansCJK-Regular.ttc"),
    Path("/system/fonts/NotoSansCJKjp-Regular.otf"),
    Path("/system/fonts/NotoSansJP-Regular.otf"),
    Path("/system/fonts/NotoSansJP-VF.ttf"),
    Path("/system/fonts/NotoSans-Regular.ttf"),
    Path("/system/fonts/DroidSansFallback.ttf"),
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
        "sakura": "桜の花びら",
        "reduce_motion": "動きを抑える",
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
        "font_status_fallback": "日本語フォント未検出 · 英語表示推奨",
        "signature_unknown": "署名情報を取得できません",
        "signature": "APK署名 SHA-256 · {digest}",
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
        "sakura": "Sakura petals",
        "reduce_motion": "Reduce motion",
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
        "font_status_fallback": "Japanese font unavailable · English UI recommended",
        "signature_unknown": "Signing certificate unavailable",
        "signature": "APK signature SHA-256 · {digest}",
        "resolving": "Resolving audio…",
        "spotify_unavailable": "Spotify full-track playback is not available on Android yet",
        "yt_dlp_missing": "YouTube resolver module is unavailable",
        "no_stream": "No playable audio stream found",
        "playback_error": "Playback error: {msg}",
        "mediaplayer_error": "MediaPlayer error: {msg}",
        "playing": "Playing · {title}",
    },
}


def install_android_font() -> tuple[str, bool, str]:
    """Register a bundled or device Japanese-capable font."""
    for candidate in FONT_CANDIDATES:
        path = Path(candidate)
        if path.exists():
            try:
                LabelBase.register(name="AquaJP", fn_regular=str(path))
                return "AquaJP", True, str(path)
            except Exception:
                continue
    return "Roboto", False, ""


def android_signature_digest() -> str:
    if platform != "android":
        return ""
    try:
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        Build = autoclass("android.os.Build")
        PackageManager = autoclass("android.content.pm.PackageManager")
        MessageDigest = autoclass("java.security.MessageDigest")
        context = PythonActivity.mActivity
        package_name = context.getPackageName()
        manager = context.getPackageManager()
        if Build.VERSION.SDK_INT >= 28:
            info = manager.getPackageInfo(package_name, 0x08000000)  # GET_SIGNING_CERTIFICATES
            signatures = info.signingInfo.getApkContentsSigners()
        else:
            info = manager.getPackageInfo(package_name, PackageManager.GET_SIGNATURES)
            signatures = info.signatures
        if not signatures or len(signatures) == 0:
            return ""
        md = MessageDigest.getInstance("SHA-256")
        digest = md.digest(signatures[0].toByteArray())
        return "".join(f"{int(b) & 0xff:02X}" for b in digest)
    except Exception:
        return ""


class FocusVisual(Widget):
    progress = NumericProperty(0.0)
    running = BooleanProperty(False)
    mode = StringProperty("FOCUS")
    water_enabled = BooleanProperty(True)
    bubbles_enabled = BooleanProperty(True)
    glow_enabled = BooleanProperty(True)
    caustics_enabled = BooleanProperty(True)
    sakura_enabled = BooleanProperty(True)
    reduce_motion = BooleanProperty(False)
    phase = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._last_static = 0.0
        for name in (
            "progress", "running", "mode", "water_enabled", "bubbles_enabled",
            "glow_enabled", "caustics_enabled", "sakura_enabled", "reduce_motion",
            "phase", "pos", "size"
        ):
            self.bind(**{name: lambda *_: self.redraw()})
        Clock.schedule_interval(self._animate, 1 / 30.0)

    def _animate(self, dt):
        now = time.monotonic()
        if self.running and not self.reduce_motion:
            self.phase += min(dt, 0.05)
            self.redraw()
        elif now - self._last_static > 0.45:
            self._last_static = now
            self.redraw()

    def _clamp(self, value: float, low: float, high: float) -> float:
        return max(low, min(high, value))

    def _wave_surfaces(self, surface_y: float, width: float, amp: float, seg: int):
        front, back = [], []
        gap = dp(7)
        seg = max(12, min(seg, 56))
        for i in range(seg + 1):
            x = self.x + width * i / seg
            nx = i / seg
            speed = 1.8 if self.reduce_motion else 2.35
            phase = self.phase * speed + nx * math.tau * 2.25
            primary = math.sin(phase) * amp
            secondary = math.sin(phase * 0.54 + 0.8) * amp * 0.24
            y = self._clamp(surface_y + primary + secondary, self.y + dp(4), self.top - dp(4))
            front.append((x, y))
            by = self._clamp(y + gap + math.sin(phase + 0.8) * amp * 0.12, self.y + dp(4), self.top - dp(4))
            back.append((x, by))
        return front, back

    def _mesh_to_bottom(self, surface, bottom_y):
        vertices, indices = [], []
        for i, (x, y) in enumerate(surface):
            vertices += [x, y, 0, 0, x, bottom_y, 0, 0]
            indices += [2 * i, 2 * i + 1]
        return vertices, indices

    def redraw(self):
        w, h = self.width, self.height
        if w <= dp(24) or h <= dp(24):
            return
        x0, y0 = self.x, self.y
        top = y0 + h
        p = max(0.0, min(1.0, float(self.progress)))
        phase = 0.0 if self.reduce_motion else self.phase
        self.canvas.clear()
        with self.canvas:
            bands = 16
            for i in range(bands):
                t = i / max(1, bands - 1)
                Color(0.014 + t * 0.020, 0.048 + t * 0.050, 0.080 + t * 0.078, 1)
                Rectangle(pos=(x0, y0 + h * i / bands), size=(w, h / bands + 2))

            if self.caustics_enabled and not self.reduce_motion:
                for j in range(3):
                    pts = []
                    for i in range(22):
                        xx = x0 + w * i / 21
                        yy = y0 + h * (0.80 - j * 0.13) + math.sin(phase * 0.72 + i * 0.46 + j) * dp(5.5)
                        pts.extend((xx, self._clamp(yy, y0 + dp(8), top - dp(8))))
                    Color(0.38, 0.86, 0.88, 0.09)
                    Line(points=pts, width=1.0, cap="round", joint="round")

            if self.water_enabled:
                level = p if self.mode == "FOCUS" else max(0.0, 0.18 - p * 0.18)
                surface_y = self._clamp(y0 + h * (0.08 + 0.62 * level), y0 + dp(18), top - dp(22))
                amp = min(dp(8.0), max(dp(3.5), w * 0.018))
                front, back = self._wave_surfaces(surface_y, w, amp, 48)

                vertices, indices = self._mesh_to_bottom(back, y0)
                Color(0.07, 0.56, 0.74, 0.14)
                Mesh(vertices=vertices, indices=indices, mode="triangle_strip")

                vertices, indices = self._mesh_to_bottom(front, y0)
                Color(0.08, 0.72, 0.82, 0.25)
                Mesh(vertices=vertices, indices=indices, mode="triangle_strip")

                Color(0.48, 0.96, 0.94, 0.72)
                Line(points=[v for point in front for v in point], width=1.8, cap="round", joint="round")
                Color(0.30, 0.78, 0.88, 0.28)
                Line(points=[v for point in back for v in point], width=1.0, cap="round", joint="round")

                depth = max(dp(54), surface_y - y0)
                if self.caustics_enabled and not self.reduce_motion:
                    for j in range(4):
                        pts = []
                        yy = surface_y - dp(28 + j * 34)
                        if yy <= y0 + dp(8):
                            continue
                        for i in range(16):
                            xx = x0 + w * i / 15
                            wave_y = yy + math.sin(phase * 1.35 + i * 0.68 + j) * dp(3 + j * 0.7)
                            pts.extend((xx, self._clamp(wave_y, y0 + dp(8), surface_y - dp(6))))
                        Color(0.55, 0.96, 0.94, 0.11)
                        Line(points=pts, width=1, cap="round", joint="round")

                if self.bubbles_enabled and not self.reduce_motion:
                    bubble_count = 10 if w < dp(360) else 14
                    for i in range(bubble_count):
                        bx = x0 + ((i * 97) % max(1, int(w))) + math.sin(phase + i) * dp(8)
                        travel = (phase * (30 + i * 1.3) + i * 53) % depth
                        by = y0 + travel
                        if by > surface_y - dp(7):
                            continue
                        r = dp(1.4 + (i % 4) * 0.58)
                        Color(0.76, 0.96, 1.0, 0.30)
                        Line(circle=(bx, by, r), width=0.75)

                if self.glow_enabled:
                    glow_count = 6 if w < dp(360) else 9
                    for i in range(glow_count):
                        gx = x0 + ((i * 137 + 33) % max(1, int(w))) + math.sin(phase * 0.65 + i) * dp(9)
                        gy = y0 + dp(18) + ((i * 71 + phase * (10 + i)) % max(dp(20), depth - dp(20)))
                        gy = min(gy, surface_y - dp(10))
                        rr = dp(1.2 + (i % 3) * 0.42)
                        Color(0.43, 0.98, 0.86, 0.13)
                        Ellipse(pos=(gx - rr * 3, gy - rr * 3), size=(rr * 6, rr * 6))
                        Color(0.62, 1.0, 0.91, 0.65)
                        Ellipse(pos=(gx - rr, gy - rr), size=(rr * 2, rr * 2))

            if self.sakura_enabled and not self.reduce_motion:
                petal_count = 4 if w < dp(360) else 6
                for i in range(petal_count):
                    cycle = (phase * (0.10 + i * 0.012) + i * 0.17) % 1.0
                    px = x0 + (w * ((i * 0.23 + cycle * 0.38) % 1.0)) + math.sin(phase * 0.55 + i) * dp(16)
                    py = top - h * cycle
                    rw = dp(5.0 + (i % 3) * 1.2)
                    rh = dp(2.4 + (i % 2) * 0.8)
                    Color(1.0, 0.70, 0.82, 0.46)
                    Ellipse(pos=(px - rw, py - rh), size=(rw * 2, rh * 2))

            cx, cy = x0 + w / 2, y0 + h * 0.58
            rad = min(w, h) * (0.18 if w < dp(360) else 0.20)
            Color(0.42, 0.68, 0.72, 0.20)
            Line(circle=(cx, cy, rad), width=1.3)
            if p > 0.002:
                Color(0.45, 0.93, 0.88, 0.86)
                Line(circle=(cx, cy, rad, 90, 90 - p * 360), width=2.4)


KV = r"""
#:import dp kivy.metrics.dp
#:import sp kivy.metrics.sp

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
    multiline: False

<PrimaryButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.39, .85, .81, 1) if self.state == "normal" else (.31, .72, .69, 1)
    color: .03, .08, .10, 1
    font_size: sp(15)
    bold: True
    size_hint_y: None
    height: app.root_view.primary_h if hasattr(app, "root_view") else dp(52)

<QuietButton@Button>:
    background_normal: ""
    background_down: ""
    background_color: (.055, .12, .15, .92) if self.state == "normal" else (.08, .17, .20, .95)
    color: .66, .78, .80, 1
    font_size: sp(12)
    size_hint_y: None
    height: app.root_view.quiet_h if hasattr(app, "root_view") else dp(40)

<PresetButton@ToggleButton>:
    group: "duration"
    allow_no_selection: False
    background_normal: ""
    background_down: ""
    background_color: (.39, .85, .81, 1) if self.state == "down" else (.055, .12, .15, .92)
    color: (.03, .08, .10, 1) if self.state == "down" else (.67, .78, .80, 1)
    font_size: sp(12)
    bold: True
    size_hint_y: None
    height: app.root_view.chip_h if hasattr(app, "root_view") else dp(38)

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
            padding: root.page_padding, root.page_padding, root.page_padding, dp(28)
            spacing: root.gap

            BoxLayout:
                orientation: "horizontal"
                size_hint_y: None
                height: root.header_h
                BoxLayout:
                    orientation: "vertical"
                    Label:
                        text: "Aqua Focus"
                        color: .94, .98, .98, 1
                        font_size: sp(root.title_sp)
                        bold: True
                        text_size: self.size
                        halign: "left"
                        valign: "middle"
                    Label:
                        text: root.t("tagline")
                        color: .49, .61, .64, 1
                        font_size: sp(root.caption_sp)
                        text_size: self.size
                        halign: "left"
                        valign: "top"
                QuietButton:
                    text: "JA / EN"
                    width: dp(82)
                    size_hint_x: None
                    on_release: root.toggle_language()

            Label:
                text: root.t("question")
                color: .94, .98, .98, 1
                font_size: sp(root.headline_sp)
                bold: True
                size_hint_y: None
                height: root.question_h
                text_size: self.width, None
                halign: "left"
                valign: "middle"

            TextInput:
                id: intention
                hint_text: root.t("task_hint")
                size_hint_y: None
                height: root.input_h
                foreground_color: .92, .97, .97, 1
                hint_text_color: .43, .56, .59, 1
                background_normal: ""
                background_active: ""
                background_color: .028, .075, .092, .95
                padding: dp(13), dp(13)
                on_text: root.intention = self.text

            BoxLayout:
                size_hint_y: None
                height: root.chip_h
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
                height: root.hero_h
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
                    sakura_enabled: root.sakura_enabled
                    reduce_motion: root.reduce_motion

                Label:
                    text: root.clock_text
                    color: .95, .99, .99, 1
                    font_size: sp(root.clock_sp)
                    bold: True
                    size_hint: .90, None
                    height: dp(92)
                    pos_hint: {"center_x": .5, "center_y": .60}

                Label:
                    text: root.progress_text
                    color: .68, .82, .84, 1
                    font_size: sp(root.caption_sp + 1)
                    size_hint: .88, None
                    height: dp(34)
                    text_size: self.size
                    halign: "center"
                    valign: "middle"
                    pos_hint: {"center_x": .5, "center_y": .45}

                PrimaryButton:
                    text: root.primary_button_text()
                    size_hint_x: .86
                    pos_hint: {"center_x": .5, "y": .07}
                    on_release: root.toggle_timer()

            QuietButton:
                text: root.t("reset")
                on_release: root.reset_timer()

            QuietButton:
                text: root.t("visuals") + ("  -" if root.visuals_open else "  +")
                on_release: root.visuals_open = not root.visuals_open

            GridLayout:
                cols: 2
                size_hint_y: None
                height: root.visuals_panel_h if root.visuals_open else 0
                opacity: 1 if root.visuals_open else 0
                disabled: not root.visuals_open
                row_default_height: root.switch_row_h
                row_force_default: True
                spacing: dp(6)
                Label:
                    text: root.t("water")
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.water_enabled
                    on_active: root.water_enabled = self.active; root.save_state_later()
                Label:
                    text: root.t("bubbles")
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.bubbles_enabled
                    on_active: root.bubbles_enabled = self.active; root.save_state_later()
                Label:
                    text: root.t("glow")
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.glow_enabled
                    on_active: root.glow_enabled = self.active; root.save_state_later()
                Label:
                    text: root.t("caustics")
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.caustics_enabled
                    on_active: root.caustics_enabled = self.active; root.save_state_later()
                Label:
                    text: root.t("sakura")
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.sakura_enabled
                    on_active: root.sakura_enabled = self.active; root.save_state_later()
                Label:
                    text: root.t("reduce_motion")
                    color: .72, .84, .85, 1
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Switch:
                    active: root.reduce_motion
                    on_active: root.reduce_motion = self.active; root.save_state_later()

            QuietButton:
                text: root.t("sound") + ("  -" if root.sound_open else "  +")
                on_release: root.sound_open = not root.sound_open

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: root.sound_panel_h if root.sound_open else 0
                opacity: 1 if root.sound_open else 0
                disabled: not root.sound_open
                spacing: dp(8)
                TextInput:
                    id: music_url
                    hint_text: root.t("music_hint")
                    size_hint_y: None
                    height: root.input_h
                    foreground_color: .9, .96, .96, 1
                    hint_text_color: .40, .54, .57, 1
                    background_normal: ""
                    background_active: ""
                    background_color: .028, .075, .092, 1
                    padding: dp(12), dp(12)
                Label:
                    text: root.music_status
                    color: .52, .66, .69, 1
                    font_size: sp(root.caption_sp)
                    size_hint_y: None
                    height: dp(28)
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                BoxLayout:
                    size_hint_y: None
                    height: root.quiet_h
                    spacing: dp(8)
                    PrimaryButton:
                        text: root.t("play")
                        height: root.quiet_h
                        on_release: root.play_music(music_url.text)
                    QuietButton:
                        text: root.t("stop")
                        height: root.quiet_h
                        on_release: root.stop_music()
                Slider:
                    min: 0
                    max: 1
                    value: root.volume
                    size_hint_y: None
                    height: dp(30)
                    on_value: root.set_volume(self.value)

            Label:
                text: root.t("today", n=root.sessions)
                color: .43, .56, .58, 1
                font_size: sp(root.caption_sp)
                size_hint_y: None
                height: dp(28)
                text_size: self.size
                halign: "left"
                valign: "middle"

            Label:
                text: root.font_status
                color: .33, .50, .52, 1
                font_size: sp(10)
                size_hint_y: None
                height: dp(22)
                text_size: self.size
                halign: "left"
                valign: "middle"

            Label:
                text: root.signature_status
                color: .30, .45, .48, 1
                font_size: sp(10)
                size_hint_y: None
                height: dp(24)
                text_size: self.size
                halign: "left"
                valign: "middle"
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
        return url, {"User-Agent": f"AquaFocus-Android/{APP_VERSION}"}, Path(urlparse(url).path).stem or "Cloud audio"

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
    sakura_enabled = BooleanProperty(True)
    reduce_motion = BooleanProperty(False)
    language = StringProperty("ja")
    font_status = StringProperty("")
    signature_status = StringProperty("")

    page_padding = NumericProperty(dp(16))
    gap = NumericProperty(dp(12))
    header_h = NumericProperty(dp(54))
    title_sp = NumericProperty(21)
    headline_sp = NumericProperty(20)
    caption_sp = NumericProperty(11)
    question_h = NumericProperty(dp(42))
    input_h = NumericProperty(dp(50))
    chip_h = NumericProperty(dp(38))
    primary_h = NumericProperty(dp(54))
    quiet_h = NumericProperty(dp(40))
    hero_h = NumericProperty(dp(380))
    clock_sp = NumericProperty(60)
    switch_row_h = NumericProperty(dp(40))
    visuals_panel_h = NumericProperty(dp(252))
    sound_panel_h = NumericProperty(dp(176))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.remaining = self.work_minutes * 60
        self.total = self.remaining
        self._last_tick = time.monotonic()
        self.audio = AndroidAudio(self)
        self.progress_text = self.t("ready")
        self.music_status = self.t("stopped")
        self.font_status = self.t("font_status_fallback")
        self.signature_status = self.t("signature_unknown")
        self.bind(size=lambda *_: self.update_metrics())
        Clock.schedule_once(lambda _dt: self.update_metrics(), 0)
        Clock.schedule_interval(self._tick, 0.20)

    def update_metrics(self):
        w = max(self.width, dp(320))
        h = max(self.height, dp(520))
        small = w < dp(380) or h < dp(680)
        tall = h > dp(760)
        self.page_padding = dp(12 if small else 18)
        self.gap = dp(10 if small else 14)
        self.header_h = dp(48 if small else 54)
        self.title_sp = 18 if small else 21
        self.headline_sp = 17 if small else 20
        self.caption_sp = 10 if small else 11
        self.question_h = dp(38 if small else 42)
        self.input_h = dp(46 if small else 50)
        self.chip_h = dp(36 if small else 38)
        self.primary_h = dp(50 if small else 54)
        self.quiet_h = dp(38 if small else 40)
        hero_ratio = 0.46 if small else 0.52
        self.hero_h = max(dp(286 if small else 340), min(dp(520), h * hero_ratio))
        self.clock_sp = 46 if small else (62 if tall else 56)
        self.switch_row_h = dp(38 if small else 42)
        self.visuals_panel_h = self.switch_row_h * 6 + dp(10)
        self.sound_panel_h = dp(166 if small else 176)

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
        app = App.get_running_app()
        self.font_status = self.t("font_status_ok" if getattr(app, "font_ok", False) else "font_status_fallback")
        digest = android_signature_digest()
        self.signature_status = self.t("signature", digest=digest[:16] + "…") if digest else self.t("signature_unknown")

    def save_state_later(self):
        Clock.unschedule(self._save_state_callback)
        Clock.schedule_once(self._save_state_callback, 0.25)

    def _save_state_callback(self, _dt):
        App.get_running_app().save_state()

    def toggle_language(self):
        self.language = "en" if self.language == "ja" else "ja"
        self.refresh_language_text()
        self.save_state_later()

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
        self.save_state_later()

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
        self.save_state_later()
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
        self.save_state_later()

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
        Window.softinput_mode = "pan"
        self.font_name, self.font_ok, self.font_source = install_android_font()
        Builder.load_string(KV)
        root = RootView()
        self.root_view = root
        self._load_state()
        if not self.font_ok and root.language == "ja":
            root.language = "en"
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
            self.root_view.sakura_enabled = bool(data.get("sakura", True))
            self.root_view.reduce_motion = bool(data.get("reduce_motion", False))
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
                "sakura": bool(self.root_view.sakura_enabled),
                "reduce_motion": bool(self.root_view.reduce_motion),
            }, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def on_stop(self):
        self.save_state()
        if hasattr(self, "root_view"):
            self.root_view.stop_music()


if __name__ == "__main__":
    AquaFocusAndroidApp().run()
