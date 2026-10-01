from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.utils import platform

try:
    import yt_dlp
except Exception:
    yt_dlp = None

if platform == "android":
    from android.permissions import Permission, request_permissions
    from jnius import autoclass


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
    background_color: (.055, .12, .15, 1) if self.state == "normal" else (.08, .17, .20, 1)
    color: .60, .72, .75, 1
    font_size: "12sp"
    size_hint_y: None
    height: dp(40)

<PresetButton@ToggleButton>:
    group: "duration"
    allow_no_selection: False
    background_normal: ""
    background_down: ""
    background_color: (.39, .85, .81, 1) if self.state == "down" else (.055, .12, .15, 1)
    color: (.03, .08, .10, 1) if self.state == "down" else (.62, .73, .76, 1)
    font_size: "12sp"
    bold: True
    size_hint_y: None
    height: dp(38)

<RootView>:
    orientation: "vertical"
    canvas.before:
        Color:
            rgba: .026, .073, .094, 1
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
            padding: dp(22), dp(22), dp(22), dp(32)
            spacing: dp(18)

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(56)
                Label:
                    text: "Aqua Focus"
                    color: .93, .97, .97, 1
                    font_size: "22sp"
                    bold: True
                    text_size: self.size
                    halign: "left"
                    valign: "middle"
                Label:
                    text: "one task. one session."
                    color: .49, .61, .64, 1
                    font_size: "11sp"
                    text_size: self.size
                    halign: "left"
                    valign: "top"

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(490)
                padding: dp(24)
                spacing: dp(14)
                canvas.before:
                    Color:
                        rgba: .043, .105, .13, .97
                    RoundedRectangle:
                        pos: self.pos
                        size: self.size
                        radius: [dp(30)]

                Label:
                    text: "READY TO DIVE"
                    color: .39, .85, .81, 1
                    font_size: "10sp"
                    bold: True
                    size_hint_y: None
                    height: dp(22)
                    text_size: self.size
                    halign: "left"

                Label:
                    text: "What deserves your attention?"
                    color: .93, .97, .97, 1
                    font_size: "20sp"
                    bold: True
                    size_hint_y: None
                    height: dp(42)
                    text_size: self.size
                    halign: "left"

                TextInput:
                    id: intention
                    hint_text: "One concrete next action"
                    multiline: False
                    size_hint_y: None
                    height: dp(50)
                    foreground_color: .92, .97, .97, 1
                    hint_text_color: .43, .56, .59, 1
                    background_normal: ""
                    background_active: ""
                    background_color: .028, .075, .092, 1
                    padding: dp(14), dp(14)
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

                Label:
                    text: root.clock_text
                    color: .94, .98, .98, 1
                    font_size: "66sp"
                    bold: True
                    size_hint_y: None
                    height: dp(102)

                Label:
                    text: root.mode.title() + ("  ·  " + root.progress_text if root.progress_text else "")
                    color: .48, .62, .65, 1
                    font_size: "11sp"
                    size_hint_y: None
                    height: dp(24)

                ProgressBar:
                    max: 1
                    value: root.progress
                    size_hint_y: None
                    height: dp(5)

                PrimaryButton:
                    text: "Pause" if root.running else "Start focus"
                    on_release: root.toggle_timer()

                QuietButton:
                    text: "Reset session"
                    on_release: root.reset_timer()

            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: dp(48) if not root.sound_open else dp(235)
                padding: dp(2)
                spacing: dp(8)

                QuietButton:
                    text: ("Sound  ·  optional   ▾" if not root.sound_open else "Sound   ▴")
                    on_release: root.sound_open = not root.sound_open

                BoxLayout:
                    orientation: "vertical"
                    size_hint_y: None
                    height: dp(175) if root.sound_open else 0
                    opacity: 1 if root.sound_open else 0
                    disabled: not root.sound_open
                    spacing: dp(8)
                    TextInput:
                        id: music_url
                        hint_text: "YouTube or direct audio URL"
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
                        color: .48, .62, .65, 1
                        font_size: "11sp"
                        size_hint_y: None
                        height: dp(24)
                    BoxLayout:
                        size_hint_y: None
                        height: dp(40)
                        spacing: dp(8)
                        PrimaryButton:
                            text: "Play"
                            height: dp(40)
                            on_release: root.play_music(music_url.text)
                        QuietButton:
                            text: "Stop"
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
                text: ("Today · " + str(root.sessions) + " completed session" + ("" if root.sessions == 1 else "s"))
                color: .40, .52, .55, 1
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
                raise RuntimeError("No playable YouTube audio stream")
            headers = dict(info.get("http_headers") or {})
            return media, headers, info.get("title") or "YouTube"
        return url, {"User-Agent": "AquaFocus-Android/1.2"}, Path(urlparse(url).path).stem or "Cloud audio"

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

            class PreparedListener:
                def onPrepared(_self, mp):
                    mp.start()
                    Clock.schedule_once(lambda _dt: self.status_cb("Playing · " + title[:48]), 0)

            # pyjnius proxy listeners can vary by Android API; polling keeps this build portable.
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

    def set_volume(self, value: float):
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
    progress_text = StringProperty("Ready to focus")
    progress = NumericProperty(0)
    work_minutes = NumericProperty(25)
    break_minutes = NumericProperty(5)
    sessions = NumericProperty(0)
    volume = NumericProperty(0.55)
    music_status = StringProperty("Ready")
    intention = StringProperty("")
    sound_open = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.remaining = self.work_minutes * 60
        self.total = self.remaining
        self._last_tick = time.monotonic()
        self.audio = AndroidAudio(self._set_music_status)
        Clock.schedule_interval(self._tick, 0.25)

    def set_preset(self, work: int, rest: int):
        self.work_minutes = work
        self.break_minutes = rest
        self.reset_timer()
        App.get_running_app().save_state()

    def toggle_timer(self):
        self.running = not self.running
        self._last_tick = time.monotonic()
        self.progress_text = "In focus" if self.running else "Paused"

    def reset_timer(self):
        self.running = False
        self.mode = "FOCUS"
        self.remaining = self.work_minutes * 60
        self.total = self.remaining
        self.progress = 0
        self.progress_text = "Ready"
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
            self.progress_text = "Break · recover before the next block"
        else:
            self.mode = "FOCUS"
            self.remaining = self.work_minutes * 60
            self.progress_text = "Next focus block"
        self.total = self.remaining
        self.progress = 0
        self._sync_clock()
        App.get_running_app().save_state()
        self._notify()

    def _sync_clock(self):
        sec = max(0, int(self.remaining + 0.999))
        self.clock_text = f"{sec // 60:02d}:{sec % 60:02d}"

    def play_music(self, url: str):
        url = (url or "").strip()
        if not url:
            self.music_status = "Paste a YouTube or direct audio URL"
            return
        if self.mode != "FOCUS":
            self.music_status = "Music is available during Focus mode"
            return
        self.audio.play(url)

    def stop_music(self):
        self.audio.stop()
        self.music_status = "Stopped"

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
        Window.clearcolor = (0.025, 0.07, 0.105, 1)
        Builder.load_string(KV)
        root = RootView()
        self.root_view = root
        self._load_state()
        if platform == "android":
            request_permissions([
                Permission.INTERNET,
                Permission.POST_NOTIFICATIONS,
                Permission.WAKE_LOCK,
            ])
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
            }), encoding="utf-8")
        except Exception:
            pass

    def on_stop(self):
        self.save_state()
        if hasattr(self, "root_view"):
            self.root_view.stop_music()


if __name__ == "__main__":
    AquaFocusAndroidApp().run()
