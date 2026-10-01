"""Aqua Focus — 集中用ポモドーロ。"""

from __future__ import annotations

import math
import os
import hashlib
import io
import json
import re
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import unquote, urlparse, quote

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import ctypes
    from ctypes import wintypes
except ImportError:  # pragma: no cover
    ctypes = None
    wintypes = None

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageTk
except ImportError:  # pragma: no cover
    Image = ImageDraw = ImageFilter = ImageTk = None

try:
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

try:
    import yt_dlp
except ImportError:  # pragma: no cover
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover
    imageio_ffmpeg = None

from i18n import I18n, PRESET_KEYS, TIP_KEYS, QUOTE_KEYS
from settings_store import SettingsStore
from v2_experience import OceanHero, AuxiliaryModes
from v2_workspace import WorkspacePanels
from v2_minimal import MinimalShell
from agiu import (
    APP_VERSION,
    AgiuController,
    ReleaseInfo,
    RELEASES_PAGE,
    fetch_latest_release,
    is_newer,
)


def app_root() -> Path:
    """インストール先 / 開発時のプロジェクトルート。"""
    if getattr(sys, "frozen", False):
        # macOS .app: Contents/MacOS/exe → Resources は別。まずは exe 隣を優先
        exe = Path(sys.executable).resolve()
        if sys.platform == "darwin":
            # .../AquaFocus.app/Contents/MacOS/AquaFocus
            contents = exe.parent.parent
            resources = contents / "Resources"
            if resources.is_dir():
                return resources
        return exe.parent
    return Path(__file__).resolve().parent


def resource_path(*parts: str) -> Path:
    """バンドル内リソース（PyInstaller の _MEIPASS）か app_root を返す。"""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base = Path(getattr(sys, "_MEIPASS"))
        candidate = base.joinpath(*parts)
        if candidate.exists():
            return candidate
    return app_root().joinpath(*parts)


IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")

# UI フォント（起動時に OS 向けへ上書き）
FONT_UI = "Segoe UI"
FONT_UI_BOLD = "Segoe UI Semibold"


def init_ui_fonts() -> None:
    """OS ごとに日本語が出せるフォントを選ぶ。"""
    global FONT_UI, FONT_UI_BOLD
    try:
        import tkinter.font as tkfont
        available = {f.lower(): f for f in tkfont.families()}
    except Exception:
        available = {}

    def pick(cands: list[str], fallback: str) -> str:
        for name in cands:
            hit = available.get(name.lower())
            if hit:
                return hit
        return fallback

    if IS_WINDOWS:
        FONT_UI = pick(["Segoe UI", "Yu Gothic UI", "Meiryo"], "Segoe UI")
        FONT_UI_BOLD = pick(["Segoe UI Semibold", "Segoe UI", "Yu Gothic UI"], FONT_UI)
    elif IS_MAC:
        FONT_UI = pick(["Hiragino Sans", "Hiragino Kaku Gothic ProN", "Helvetica Neue", "Arial Unicode MS"], "Helvetica Neue")
        FONT_UI_BOLD = pick(["Hiragino Sans", "Helvetica Neue", "Helvetica"], FONT_UI)
    else:
        FONT_UI = pick(
            ["Noto Sans CJK JP", "Noto Sans CJK", "Noto Sans JP", "Yu Gothic", "DejaVu Sans", "FreeSans"],
            "DejaVu Sans",
        )
        FONT_UI_BOLD = pick(
            ["Noto Sans CJK JP", "Noto Sans CJK", "Noto Sans JP", "DejaVu Sans Bold", "DejaVu Sans"],
            FONT_UI,
        )


def apply_window_icon(window) -> None:
    """Windows は .ico、macOS/Linux は PNG。"""
    ico = resource_path("assets", "icons", "aqua-focus.ico")
    png = resource_path("assets", "icons", "aqua-focus-app.png")
    try:
        if IS_WINDOWS and ico.exists():
            window.iconbitmap(default=str(ico))
            window.iconbitmap(str(ico))
            return
    except Exception:
        pass
    try:
        if png.exists() and Image is not None and ImageTk is not None:
            img = Image.open(png).convert("RGBA")
            photo = ImageTk.PhotoImage(img)
            window.iconphoto(True, photo)
            window._aqua_icon_ref = photo
    except Exception:
        pass


def resolve_ffmpeg_exe() -> str | None:
    """PATH / アプリ同梱 (imageio-ffmpeg・bin/) から ffmpeg を探す。別途インストール不要。"""
    import shutil

    candidates: list[Path] = []
    which = shutil.which("ffmpeg")
    if which:
        candidates.append(Path(which))

    exe_name = "ffmpeg.exe" if IS_WINDOWS else "ffmpeg"
    for base in (app_root() / "bin", resource_path("bin"), resource_path("ffmpeg")):
        candidates.append(base / exe_name)

    if imageio_ffmpeg is not None:
        try:
            candidates.append(Path(imageio_ffmpeg.get_ffmpeg_exe()))
        except Exception:
            pass

    for bin_dir in (
        resource_path("imageio_ffmpeg", "binaries"),
        app_root() / "_internal" / "imageio_ffmpeg" / "binaries",
    ):
        try:
            if bin_dir.is_dir():
                for p in bin_dir.iterdir():
                    name = p.name.lower()
                    if p.is_file() and "ffmpeg" in name and "ffprobe" not in name and not name.endswith(".md"):
                        candidates.append(p)
        except Exception:
            pass

    for c in candidates:
        try:
            if c is not None and c.is_file():
                return str(c.resolve())
        except Exception:
            continue
    return None


def ensure_bundled_ffmpeg() -> str | None:
    """同梱 ffmpeg を app/bin に展開（インストーラ配布でもパスが安定）。"""
    import shutil

    src = resolve_ffmpeg_exe()
    if not src:
        return None
    dest_dir = app_root() / "bin"
    dest = dest_dir / ("ffmpeg.exe" if IS_WINDOWS else "ffmpeg")
    try:
        src_p = Path(src).resolve()
        if dest.resolve() == src_p and dest.is_file():
            return str(dest)
        dest_dir.mkdir(parents=True, exist_ok=True)
        if (not dest.exists()) or dest.stat().st_size != src_p.stat().st_size:
            shutil.copy2(src_p, dest)
        return str(dest.resolve())
    except Exception:
        return src


def enable_windows_dpi_awareness() -> None:
    if sys.platform != "win32" or ctypes is None:
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


# Themes

@dataclass(frozen=True)
class Theme:
    name: str
    bg: str
    sidebar: str
    accent: str
    accent_hover: str
    wave_back_work: str
    wave_front_work: str
    wave_back_break: str
    wave_front_break: str
    particle: str
    glow: str
    text: str
    muted: str


THEMES: dict[str, Theme] = {
    "Abyss Glass": Theme(
        name="Abyss Glass",
        bg="#071319",
        sidebar="#0b1b22",
        accent="#63d8cf",
        accent_hover="#4fc2ba",
        wave_back_work="#12333b",
        wave_front_work="#63d8cf",
        wave_back_break="#15352f",
        wave_front_break="#7ad9b5",
        particle="#b9e9e5",
        glow="#173740",
        text="#eef7f6",
        muted="#829ba1",
    ),
    "Ocean Depth": Theme(
        name="Ocean Depth",
        bg="#061722",
        sidebar="#0d2b3d",
        accent="#38bdf8",
        accent_hover="#169bd5",
        wave_back_work="#0f5877",
        wave_front_work="#38bdf8",
        wave_back_break="#116452",
        wave_front_break="#43dfb6",
        particle="#a9e5ff",
        glow="#2b6f8c",
        text="#f4fbff",
        muted="#b7d3df",
    ),
    "Midnight Aurora": Theme(
        name="Midnight Aurora",
        bg="#0a0e1a",
        sidebar="#12182a",
        accent="#6c8cff",
        accent_hover="#5570e0",
        wave_back_work="#2a3a7a",
        wave_front_work="#6c8cff",
        wave_back_break="#2a5a6a",
        wave_front_break="#5eead4",
        particle="#a5b4fc",
        glow="#3d4f8f",
        text="#eef2ff",
        muted="#94a3b8",
    ),
    "Sunset Glow": Theme(
        name="Sunset Glow",
        bg="#1a0f14",
        sidebar="#26141c",
        accent="#e07a5f",
        accent_hover="#c9654a",
        wave_back_work="#8b3a4a",
        wave_front_work="#e07a5f",
        wave_back_break="#6b4a2a",
        wave_front_break="#f2cc8f",
        particle="#ffb4a2",
        glow="#7a3a45",
        text="#fff5f0",
        muted="#c9a99a",
    ),
    "Forest Mist": Theme(
        name="Forest Mist",
        bg="#0c1612",
        sidebar="#14221c",
        accent="#3d9e6f",
        accent_hover="#2f855a",
        wave_back_work="#1e5c40",
        wave_front_work="#3d9e6f",
        wave_back_break="#3a5a2a",
        wave_front_break="#86efac",
        particle="#a7f3d0",
        glow="#2a5a42",
        text="#ecfdf5",
        muted="#86a899",
    ),
    "Sakura Night": Theme(
        name="Sakura Night",
        bg="#160f18",
        sidebar="#221828",
        accent="#e879a9",
        accent_hover="#d45f93",
        wave_back_work="#7a3a5a",
        wave_front_work="#e879a9",
        wave_back_break="#5a3a6a",
        wave_front_break="#c4b5fd",
        particle="#f9a8d4",
        glow="#6a3a55",
        text="#fdf2f8",
        muted="#b8a0b0",
    ),
    "Slate Modern": Theme(
        name="Slate Modern",
        bg="#111318",
        sidebar="#1a1d24",
        accent="#38bdf8",
        accent_hover="#0ea5e9",
        wave_back_work="#1e3a4a",
        wave_front_work="#38bdf8",
        wave_back_break="#1e3a30",
        wave_front_break="#34d399",
        particle="#bae6fd",
        glow="#2a4555",
        text="#f1f5f9",
        muted="#94a3b8",
    ),
}

THEME_BG_FILES = {
    "Ocean Depth": "ocean_depth.jpg",
    "Midnight Aurora": "midnight_aurora.jpg",
    "Sunset Glow": "sunset_glow.jpg",
    "Forest Mist": "forest_mist.jpg",
    "Sakura Night": "sakura_night.jpg",
    "Slate Modern": "slate_modern.jpg",
}

ASSETS_BG_DIR = resource_path("assets", "backgrounds")
ICON_PATH = resource_path("assets", "icons", "aqua-focus.ico")

# 学習科学プリセット等の文言は i18n.py（JA/EN）
TEMPTATION_FILM_ALPHA = 0.58  # thin translucent film

_TEMPTATION_SKIP_CLASSES = {
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "Progman",
    "WorkerW",
    "DV2ControlHost",
    "ForegroundStaging",
    "NotifyIconOverflowWindow",
    "Windows.UI.Core.CoreWindow",
}

# 音楽再生などで必須のヘルパー（フィルムを貼らない）
_TEMPTATION_ALWAYS_EXCLUDE_EXES = {
    "ffmpeg.exe",
    "ffprobe.exe",
    "conhost.exe",
    "openconsole.exe",
}


def _is_temptation_helper_exe(exe: str, title: str = "") -> bool:
    """ffmpeg / 付属コンソールなど、Focus 中も触れてよい（貼らない）プロセス。"""
    e = (exe or "").strip().lower()
    t = (title or "").strip().lower()
    if not e:
        return False
    if e in _TEMPTATION_ALWAYS_EXCLUDE_EXES:
        return True
    if e.startswith("ffmpeg") or "ffmpeg" in e:
        return True
    if e.startswith("ffprobe") or "ffprobe" in e:
        return True
    if e in ("cmd.exe", "powershell.exe", "pwsh.exe", "windowsterminal.exe"):
        if "ffmpeg" in t or "ffprobe" in t or "imageio" in t:
            return True
    return False


def _subprocess_hidden_kwargs() -> dict:
    """Windows でコンソール窓を出さない Popen/run 用オプション。"""
    if sys.platform != "win32":
        return {}
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0
    return {"creationflags": flags, "startupinfo": si}


def is_windows_admin() -> bool:
    if sys.platform != "win32" or ctypes is None:
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_elevated_with_flag(flag: str = "--temptation-guard") -> bool:
    """UAC で管理者として起動し直す。"""
    if sys.platform != "win32" or ctypes is None:
        return False
    if is_windows_admin():
        return False
    kept = [a for a in sys.argv[1:] if a != flag]
    if getattr(sys, "frozen", False):
        params = subprocess.list2cmdline([flag, *kept])
        cwd = str(app_root())
        target = sys.executable
    else:
        script = str(Path(__file__).resolve())
        params = subprocess.list2cmdline([script, flag, *kept])
        cwd = str(Path(script).parent)
        target = sys.executable
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", target, params, cwd, 1)
    return int(rc) > 32


# Music helpers

try:
    import sounddevice as sd
    import numpy as np
except ImportError:  # pragma: no cover
    sd = None
    np = None


def list_output_audio_devices() -> list[tuple[int, str]]:
    """Return [(device_index, display_name), ...] for playback devices."""
    if sd is None:
        return []
    out: list[tuple[int, str]] = []
    try:
        devices = sd.query_devices()
        hostapis = sd.query_hostapis()
    except Exception:
        return []
    for i, d in enumerate(devices):
        try:
            if int(d.get("max_output_channels") or 0) <= 0:
                continue
            name = str(d.get("name") or f"Device {i}").strip()
            api_i = int(d.get("hostapi", 0))
            api = ""
            try:
                api = str(hostapis[api_i].get("name") or "")
            except Exception:
                pass
            label = f"{name}" + (f"  ·  {api}" if api else "")
            out.append((i, label))
        except Exception:
            continue
    return out


def resolve_output_device_index(
    preferred_index: int | None,
    preferred_name: str,
) -> int | None:
    """Match saved device by index+name; None if user has not chosen / missing."""
    devices = list_output_audio_devices()
    if not devices:
        return None
    name = (preferred_name or "").strip()
    if preferred_index is not None:
        for idx, label in devices:
            if idx == preferred_index:
                if not name or name in label or label.startswith(name):
                    return idx
    if name:
        for idx, label in devices:
            if name == label or name in label or label.startswith(name):
                return idx
        # bare device name without hostapi suffix
        bare = name.split("  ·  ")[0].strip()
        for idx, label in devices:
            if label.startswith(bare):
                return idx
    return None

def default_output_audio_device() -> tuple[int, str] | None:
    """Return the PortAudio default output, falling back to the first usable device."""
    devices = list_output_audio_devices()
    if not devices:
        return None
    if sd is not None:
        try:
            raw = sd.default.device
            idx = int(raw[1] if isinstance(raw, (tuple, list)) else raw)
            for dev_idx, label in devices:
                if dev_idx == idx:
                    return dev_idx, label
        except Exception:
            pass
    return devices[0]



# Cloud stream player (no full download)

class CloudAudioStreamer:
    """Stream remote audio via ffmpeg → PCM → sounddevice (no local file cache)."""

    SAMPLE_RATE = 44100
    CHANNELS = 2
    CHUNK_BYTES = SAMPLE_RATE * CHANNELS * 2 // 10  # ~100ms

    def __init__(self, status_cb: Callable[[str], None] | None = None):
        self.status_cb = status_cb or (lambda _s: None)
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._volume = 0.55
        self._device: int | None = None
        self._resolve_url: Callable[[], str | tuple[str, dict[str, str]]] | None = None
        self._loop = True
        self.playing = False
        self._on_natural_end: Callable[[], None] | None = None
        self._on_error: Callable[[str], None] | None = None

    def set_volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, float(value)))

    def set_device(self, device: int | None) -> None:
        self._device = device

    def start(
        self,
        resolve_url: Callable[[], str | tuple[str, dict[str, str]]],
        loop: bool = True,
        on_natural_end: Callable[[], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.stop()
        ffmpeg = resolve_ffmpeg_exe()
        if not ffmpeg:
            raise RuntimeError("ffmpeg が必要です（imageio-ffmpeg）")
        if sd is None or np is None:
            raise RuntimeError("sounddevice / numpy が必要です")
        if self._device is None:
            raise RuntimeError("音声出力デバイスを選択してください")

        self._resolve_url = resolve_url
        self._loop = loop
        self._on_natural_end = on_natural_end
        self._on_error = on_error
        self._stop.clear()
        self._pause.clear()
        self._thread = threading.Thread(target=self._run, args=(ffmpeg,), daemon=True)
        self._thread.start()

    def pause(self) -> None:
        self._pause.set()
        self.playing = False

    def resume(self) -> None:
        self._pause.clear()
        self.playing = True

    def stop(self) -> None:
        self._stop.set()
        self._pause.clear()
        self.playing = False
        self._kill_proc()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=1.5)
        self._thread = None

    def _kill_proc(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass
        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass

    def _run(self, ffmpeg: str) -> None:
        assert self._resolve_url is not None
        while not self._stop.is_set():
            try:
                source = self._resolve_url()
                if isinstance(source, tuple):
                    url, headers = source
                else:
                    url, headers = source, {}
            except Exception as exc:
                msg = f"ストリーム URL 取得失敗: {exc}"
                self.status_cb(msg)
                if self._on_error:
                    self._on_error(msg)
                break
            if not url:
                msg = "ストリーム URL が空です"
                self.status_cb(msg)
                if self._on_error:
                    self._on_error(msg)
                break

            cmd = [
                ffmpeg,
                "-hide_banner",
                "-loglevel", "error",
                "-nostdin",
                "-reconnect", "1",
                "-reconnect_streamed", "1",
                "-reconnect_delay_max", "5",
                "-rw_timeout", "15000000",
            ]
            if headers:
                header_blob = "".join(
                    f"{key}: {value}\r\n"
                    for key, value in headers.items()
                    if key and value
                )
                if header_blob:
                    cmd.extend(["-headers", header_blob])
            cmd.extend([
                "-i", url,
                "-vn",
                "-f", "s16le",
                "-acodec", "pcm_s16le",
                "-ar", str(self.SAMPLE_RATE),
                "-ac", str(self.CHANNELS),
                "pipe:1",
            ])
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    bufsize=self.CHUNK_BYTES * 4,
                    **_subprocess_hidden_kwargs(),
                )
            except Exception as exc:
                self.status_cb(f"ffmpeg 起動失敗: {exc}")
                break

            self.playing = True
            self.status_cb("♪ ストリーム再生中")
            try:
                with sd.RawOutputStream(
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype="int16",
                    blocksize=0,
                    device=self._device,
                ) as stream:
                    while not self._stop.is_set():
                        if self._pause.is_set():
                            self.playing = False
                            time.sleep(0.04)
                            continue
                        self.playing = True
                        proc = self._proc
                        if proc is None or proc.stdout is None:
                            break
                        data = proc.stdout.read(self.CHUNK_BYTES)
                        if not data:
                            break
                        if len(data) < 4:
                            continue
                        frame = self.CHANNELS * 2
                        if len(data) % frame:
                            data = data[: len(data) - (len(data) % frame)]
                        if self._volume < 0.995:
                            arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                            arr *= self._volume
                            data = np.clip(arr, -32768, 32767).astype(np.int16).tobytes()
                        stream.write(data)
            except Exception as exc:
                if not self._stop.is_set():
                    self.status_cb(f"ストリームエラー: {exc}")
            finally:
                self._kill_proc()
                self.playing = False

            if self._stop.is_set():
                break
            if self._on_natural_end is not None:
                try:
                    self._on_natural_end()
                except Exception:
                    pass
            if not self._loop:
                break
            time.sleep(0.15)

        self.playing = False


# Playlist

@dataclass
class PlaylistTrack:
    url: str
    title: str = ""


class TemptationExcludeStore:
    """Persist process names (e.g. Cursor.exe) excluded from temptation films."""

    def __init__(self, path: Path):
        self.path = path
        self.exclusions: set[str] = set()  # lowercase exe names
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                items = data.get("exclusions", [])
                self.exclusions = {str(x).strip().lower() for x in items if str(x).strip()}
        except Exception:
            self.exclusions = set()

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            payload = {"exclusions": sorted(self.exclusions)}
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_excluded(self, exe_name: str) -> bool:
        return (exe_name or "").strip().lower() in self.exclusions

    def set_excluded(self, exe_name: str, excluded: bool) -> None:
        key = (exe_name or "").strip().lower()
        if not key:
            return
        if excluded:
            self.exclusions.add(key)
        else:
            self.exclusions.discard(key)
        self.save()


class PlaylistStore:
    """Simple JSON-backed playlist for focus sessions."""

    def __init__(self, path: Path):
        self.path = path
        self.tracks: list[PlaylistTrack] = []
        self.index = 0
        self.continuous = True
        self.load()

    def load(self) -> None:
        try:
            if self.path.exists():
                data = json.loads(self.path.read_text(encoding="utf-8"))
                self.tracks = [
                    PlaylistTrack(url=t.get("url", ""), title=t.get("title", ""))
                    for t in data.get("tracks", [])
                    if t.get("url")
                ]
                self.index = max(0, min(int(data.get("index", 0)), max(0, len(self.tracks) - 1)))
                self.continuous = bool(data.get("continuous", True))
        except Exception:
            self.tracks = []
            self.index = 0

    def save(self) -> None:
        try:
            payload = {
                "index": self.index,
                "continuous": self.continuous,
                "tracks": [{"url": t.url, "title": t.title} for t in self.tracks],
            }
            self.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def add(self, url: str, title: str = "") -> bool:
        url = (url or "").strip()
        if not url:
            return False
        if any(t.url == url for t in self.tracks):
            return False
        if not title:
            kind = MusicController.detect_kind(url)
            if kind == "direct":
                title = unquote(Path(urlparse(url).path).stem).replace("_", " ").replace("-", " ")
            elif kind == "youtube":
                title = "YouTube track"
            elif kind == "spotify":
                title = "Spotify track"
            else:
                title = url[:40]
        self.tracks.append(PlaylistTrack(url=url, title=title.strip() or "Track"))
        self.save()
        return True

    def remove_at(self, idx: int) -> None:
        if 0 <= idx < len(self.tracks):
            del self.tracks[idx]
            if self.index >= len(self.tracks):
                self.index = max(0, len(self.tracks) - 1)
            self.save()

    def current(self) -> PlaylistTrack | None:
        if not self.tracks:
            return None
        self.index = max(0, min(self.index, len(self.tracks) - 1))
        return self.tracks[self.index]

    def next(self) -> PlaylistTrack | None:
        if not self.tracks:
            return None
        self.index = (self.index + 1) % len(self.tracks)
        self.save()
        return self.current()

    def prev(self) -> PlaylistTrack | None:
        if not self.tracks:
            return None
        self.index = (self.index - 1) % len(self.tracks)
        self.save()
        return self.current()

    def select(self, idx: int) -> PlaylistTrack | None:
        if 0 <= idx < len(self.tracks):
            self.index = idx
            self.save()
            return self.current()
        return None

    def labels(self) -> list[str]:
        out = []
        for i, t in enumerate(self.tracks):
            mark = "▶ " if i == self.index else "   "
            name = t.title or t.url
            if len(name) > 36:
                name = name[:35] + "…"
            out.append(f"{mark}{i + 1}. {name}")
        return out


AUDIO_EXTS = (".mp3", ".ogg", ".wav", ".m4a", ".flac", ".aac")


class MusicController:
    """Cloud-first player: stream YouTube / direct / Spotify-matched audio in-app (no browser)."""

    def __init__(self, status_cb: Callable[[str], None] | None = None):
        self.status_cb = status_cb or (lambda _s: None)
        self.url = ""
        self.kind: str | None = None  # "youtube" | "spotify" | "direct" | None
        self.stream_url: str | None = None  # resolved HTTP media URL
        self.stream_headers: dict[str, str] = {}
        self.local_path: str | None = None  # fallback only
        self.meta_title: str = ""
        self.meta_artist: str = ""
        self.thumbnail_url: str | None = None
        self.cover_image = None  # PIL.Image RGB square
        self._yt_match_url: str | None = None  # YouTube page used for Spotify playback
        self._ready = False
        self._loading = False
        self._is_playing = False
        self._paused = False
        self._play_when_ready = False
        self._volume = 0.55
        self._use_stream = True
        self._mixer_ok = False
        self._cache_dir = Path(tempfile.gettempdir()) / "aqua_focus_music"
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self.streamer = CloudAudioStreamer(status_cb=self._notify)
        self.on_track_ended: Callable[[], None] | None = None
        self._output_device_index: int | None = None
        self._output_device_name: str = ""

        if pygame is not None:
            try:
                pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=2048)
                self._mixer_ok = True
            except Exception:
                self._mixer_ok = False

    def set_output_device(self, index: int | None, name: str = "") -> None:
        """User-selected playback device (required for stream; pygame re-inits when possible)."""
        self._output_device_index = index
        self._output_device_name = (name or "").strip()
        self.streamer.set_device(index)
        if index is None or pygame is None:
            return
        bare = self._output_device_name.split("  ·  ")[0].strip() or self._output_device_name
        was_playing = self._is_playing and not self._paused
        try:
            if self._mixer_ok:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                pygame.mixer.quit()
            kwargs = dict(frequency=44100, size=-16, channels=2, buffer=2048)
            try:
                pygame.mixer.init(**kwargs, devicename=bare)
            except TypeError:
                pygame.mixer.init(**kwargs)
            except Exception:
                pygame.mixer.init(**kwargs)
            self._mixer_ok = True
            pygame.mixer.music.set_volume(self._volume)
        except Exception:
            self._mixer_ok = False
        if was_playing and self._ready:
            try:
                self.play()
            except Exception:
                pass

    def _notify(self, msg: str) -> None:
        self.status_cb(msg)

    def _on_stream_natural_end(self) -> None:
        """Called when one stream finishes (before loop/next resolve)."""
        if self.on_track_ended:
            try:
                self.on_track_ended()
            except Exception:
                pass

    @staticmethod
    def detect_kind(url: str) -> str | None:
        u = (url or "").strip()
        low = u.lower()
        if not low:
            return None
        if "spotify.com" in low or low.startswith("spotify:"):
            return "spotify"
        if any(x in low for x in ("youtube.com", "youtu.be", "music.youtube.com")):
            return "youtube"
        if low.startswith("http://") or low.startswith("https://"):
            return "direct"
        return None

    def display_title(self) -> str:
        if self.meta_title:
            t = self.meta_title.strip()
            return (t[:48] + "…") if len(t) > 48 else t
        if not self.url:
            return "No track selected"
        if self.kind == "spotify":
            return "Spotify · Now Playing"
        if self.kind == "youtube":
            return "YouTube · Focus Mix"
        name = unquote(Path(urlparse(self.url).path).stem)
        name = name.replace("_", " ").replace("-", " ").strip()
        return (name[:42] + "…") if len(name) > 42 else (name or "Cloud Track")

    def display_artist(self) -> str:
        if self.meta_artist:
            a = self.meta_artist.strip()
            return (a[:40] + "…") if len(a) > 40 else a
        return {
            "youtube": "YouTube",
            "spotify": "Spotify",
            "direct": "Cloud Stream",
        }.get(self.kind or "", "")

    def source_badge(self) -> str:
        return {
            "youtube": "YT",
            "spotify": "SP",
            "direct": "CLOUD",
        }.get(self.kind or "", "—")

    def set_url(self, url: str) -> None:
        url = (url or "").strip()
        if url == self.url and self._ready:
            return
        self.stop()
        self.url = url
        self.kind = self.detect_kind(url)
        self.stream_url = None
        self.stream_headers = {}
        self.local_path = None
        self.meta_title = ""
        self.meta_artist = ""
        self.thumbnail_url = None
        self.cover_image = None
        self._yt_match_url = None
        self._ready = False
        self._use_stream = True
        self._is_playing = False
        self._paused = False

    def set_volume(self, value: float) -> None:
        self._volume = max(0.0, min(1.0, value))
        self.streamer.set_volume(self._volume)
        if self._mixer_ok and pygame is not None:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except Exception:
                pass

    def _youtube_ydl_options(self, *, search: bool = False, download: bool = False) -> dict:
        """Harden yt-dlp for packaged playback with retries and client fallback."""
        opts: dict = {
            "format": "bestaudio[protocol^=http][acodec!=none]/bestaudio[acodec!=none]/bestaudio/best",
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "noprogress": True,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 20,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
            },
        }
        if search:
            opts["default_search"] = "ytsearch1"
        if download:
            opts["overwrites"] = True
        ffmpeg = resolve_ffmpeg_exe()
        if ffmpeg:
            opts["ffmpeg_location"] = ffmpeg
        return opts

    def _extract_youtube_info(self, target: str, *, search: bool = False, download: bool = False) -> dict:
        if yt_dlp is None:
            raise RuntimeError("yt-dlp が必要です")
        last_exc: Exception | None = None
        for clients in (["android", "ios", "tv", "web"], ["web", "mweb", "android"], ["android_vr", "tv", "web"]):
            opts = self._youtube_ydl_options(search=search, download=download)
            opts["extractor_args"] = {"youtube": {"player_client": clients}}
            try:
                with yt_dlp.YoutubeDL(opts) as ydl:
                    return ydl.extract_info(target, download=download)
            except Exception as exc:
                last_exc = exc
        raise RuntimeError(f"yt-dlp で音源を取得できませんでした: {last_exc}")

    def _resolve_youtube_stream_url(self) -> str:
        info = self._extract_youtube_info(self.url, download=False)
        if info.get("entries"):
            info = info["entries"][0] or info
        media = info.get("url")
        if not media:
            raise RuntimeError("YouTube ストリーム URL を取得できませんでした")
        self.stream_url = media
        headers = dict(info.get("http_headers") or {})
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        referer = info.get("webpage_url") or info.get("original_url") or self.url
        if referer:
            headers.setdefault("Referer", str(referer))
        self.stream_headers = {
            str(key): str(value) for key, value in headers.items()
            if key and value is not None
        }
        self.meta_title = (info.get("title") or self.meta_title or "YouTube Track").strip()
        self.meta_artist = (info.get("artist") or info.get("uploader") or info.get("channel") or self.meta_artist or "YouTube").strip()
        thumb = info.get("thumbnail") or (info.get("thumbnails") or [{}])[-1].get("url")
        if thumb:
            self.thumbnail_url = thumb
        return media

    def _fetch_spotify_metadata(self) -> None:
        """Use Spotify oEmbed (+ light OG fallback) for title + cover art."""
        oembed = f"https://open.spotify.com/oembed?url={quote(self.url, safe='')}"
        req = urllib.request.Request(
            oembed,
            headers={"User-Agent": "AquaFocus/1.0", "Accept": "application/json"},
        )
        with self._urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        title = (data.get("title") or "").strip()
        if " · " in title:
            song, artist = title.split(" · ", 1)
            self.meta_title = song.strip() or title
            self.meta_artist = artist.strip() or "Spotify"
        elif " - " in title and " by " not in title.lower():
            song, artist = title.split(" - ", 1)
            self.meta_title = song.strip() or title
            self.meta_artist = artist.strip() or "Spotify"
        else:
            self.meta_title = title or "Spotify Track"
            self.meta_artist = "Spotify"

        thumb = data.get("thumbnail_url")
        if thumb:
            self.thumbnail_url = thumb

        if self.meta_artist in ("", "Spotify"):
            try:
                page_req = urllib.request.Request(
                    self.url,
                    headers={"User-Agent": "AquaFocus/1.0", "Accept": "text/html"},
                )
                with self._urlopen(page_req, timeout=15) as resp:
                    html = resp.read().decode("utf-8", errors="replace")
                m = re.search(
                    r'property="og:title"\s+content="([^"]+)"',
                    html,
                    flags=re.IGNORECASE,
                )
                if not m:
                    m = re.search(
                        r'content="([^"]+)"\s+property="og:title"',
                        html,
                        flags=re.IGNORECASE,
                    )
                if m:
                    og = m.group(1)
                    if " by " in og:
                        left, right = og.split(" by ", 1)
                        self.meta_title = left.replace(" - song", "").replace(" – song", "").strip() or self.meta_title
                        self.meta_artist = right.split("|")[0].strip() or self.meta_artist
                    elif " - " in og:
                        parts = og.split(" - ")
                        if len(parts) >= 2:
                            self.meta_title = parts[0].strip() or self.meta_title
                            self.meta_artist = parts[1].split("|")[0].strip() or self.meta_artist
                img = re.search(
                    r'property="og:image"\s+content="([^"]+)"',
                    html,
                    flags=re.IGNORECASE,
                )
                if img and not self.thumbnail_url:
                    self.thumbnail_url = img.group(1)
            except Exception:
                pass

    def _fetch_direct_metadata(self) -> None:
        name = unquote(Path(urlparse(self.url).path).stem)
        name = name.replace("_", " ").replace("-", " ").strip()
        self.meta_title = name or "Cloud Track"
        self.meta_artist = "Cloud Stream"

    def _download_cover_image(self) -> None:
        if not self.thumbnail_url or Image is None:
            return
        try:
            req = urllib.request.Request(
                self.thumbnail_url,
                headers={"User-Agent": "AquaFocus/1.0", "Accept": "image/*,*/*"},
            )
            with self._urlopen(req, timeout=25) as resp:
                raw = resp.read()
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            w, h = img.size
            side = min(w, h)
            left = (w - side) // 2
            top = (h - side) // 2
            img = img.crop((left, top, left + side, top + side))
            img = img.resize((512, 512), Image.Resampling.LANCZOS)
            self.cover_image = img
        except Exception as exc:
            self._notify(f"ジャケット取得スキップ: {exc}")

    def make_circular_cover(self, size: int, ring_color: str | None = None):
        """Return PIL RGBA circular album art (or None)."""
        if self.cover_image is None or Image is None or ImageDraw is None:
            return None
        base = self.cover_image.resize((size, size), Image.Resampling.LANCZOS).convert("RGBA")
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((1, 1, size - 2, size - 2), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(base, (0, 0))
        out.putalpha(mask)
        if ring_color and len(ring_color) >= 7:
            draw = ImageDraw.Draw(out)
            rgb = tuple(int(ring_color.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
            draw.ellipse((2, 2, size - 3, size - 3), outline=rgb + (220,), width=max(2, size // 48))
        return out

    def _resolve_spotify_via_youtube(self) -> str:
        """
        Spotify does not expose full-track stream URLs to third-party apps.
        Resolve an in-app stream the same way as YouTube: search a matching track and stream it.
        Keep Spotify title/cover for the UI.
        """
        if yt_dlp is None:
            raise RuntimeError("yt-dlp が必要です")
        title = (self.meta_title or "").strip()
        artist = (self.meta_artist or "").strip()
        if artist in ("Spotify", "spotify"):
            artist = ""
        if not title:
            raise RuntimeError("Spotify の曲名を取得できませんでした")

        query = f"{artist} {title} audio".strip() if artist else f"{title} audio"
        search = f"ytsearch1:{query}"
        self._notify(f"対応音源を検索中… {query[:40]}")

        info = self._extract_youtube_info(search, search=True, download=False)
        if info.get("entries"):
            info = info["entries"][0] or {}
        media = info.get("url")
        if not media:
            raise RuntimeError("Spotify 曲の再生用ストリームが見つかりませんでした")
        page = info.get("webpage_url") or info.get("original_url")
        if page:
            self._yt_match_url = page
        self.stream_url = media
        headers = dict(info.get("http_headers") or {})
        headers.setdefault(
            "User-Agent",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        if page:
            headers.setdefault("Referer", str(page))
        self.stream_headers = {
            str(key): str(value) for key, value in headers.items()
            if key and value is not None
        }
        return media

    def _resolve_stream_url(self) -> str:
        if self.kind == "direct":
            self.stream_headers = {
                "User-Agent": "AquaFocus/1.2 (+https://github.com/kokonachan-193/Pomodoro-timer)"
            }
            return self.url
        if self.kind == "youtube":
            return self._resolve_youtube_stream_url()
        if self.kind == "spotify":
            if self._yt_match_url:
                saved_title, saved_artist, saved_thumb, saved_cover = (
                    self.meta_title, self.meta_artist, self.thumbnail_url, self.cover_image,
                )
                original_url = self.url
                try:
                    self.url = self._yt_match_url
                    media = self._resolve_youtube_stream_url()
                finally:
                    self.url = original_url
                    self.meta_title = saved_title
                    self.meta_artist = saved_artist
                    self.thumbnail_url = saved_thumb
                    self.cover_image = saved_cover
                return media
            return self._resolve_spotify_via_youtube()
        raise RuntimeError("ストリーム非対応の種別です")

    def _resolve_stream_source(self) -> tuple[str, dict[str, str]]:
        return self._resolve_stream_url(), dict(self.stream_headers)

    def _on_stream_error(self, message: str) -> None:
        if not self._use_stream:
            return
        self._use_stream = False
        self._is_playing = False
        self._paused = False
        self._notify(f"{message} · ローカル再生へ切替中…")

        def fallback() -> None:
            time.sleep(0.15)
            if self.url and self._ready:
                self.play()

        threading.Thread(target=fallback, daemon=True).start()

    def prepare_async(self, done_cb: Callable[[bool, str], None] | None = None) -> None:
        if not self.url or self.kind is None:
            if done_cb:
                done_cb(True, "no music")
            return
        if self._ready and (self.stream_url or self.local_path or self._yt_match_url):
            if done_cb:
                done_cb(True, "cached")
            return
        if self._loading:
            return

        can_stream = resolve_ffmpeg_exe() is not None and sd is not None and np is not None
        if self.kind in ("youtube", "spotify") and yt_dlp is None:
            if done_cb:
                done_cb(False, "yt-dlp が必要です")
            return

        self._loading = True
        self._notify("タイトル / ジャケット取得中…")

        def worker() -> None:
            ok, msg = False, ""
            try:
                if self.kind == "spotify":
                    if not can_stream:
                        raise RuntimeError("ストリーム再生には ffmpeg と sounddevice が必要です")
                    self._fetch_spotify_metadata()
                    self._download_cover_image()
                    self._resolve_spotify_via_youtube()
                    self._use_stream = True
                    self._ready = True
                    ok, msg = True, "spotify-stream-ready"
                elif self.kind == "direct":
                    self._fetch_direct_metadata()
                    if can_stream:
                        self.stream_url = self.url
                        self._use_stream = True
                    else:
                        if not self._mixer_ok:
                            raise RuntimeError("再生エンジンがありません")
                        self.local_path = self._fetch_direct_url(self.url)
                        self._use_stream = False
                    self._ready = True
                    ok, msg = True, "stream-ready"
                else:  # youtube
                    if can_stream:
                        self._resolve_youtube_stream_url()
                        self._use_stream = True
                    else:
                        if not self._mixer_ok:
                            raise RuntimeError("再生エンジンがありません")
                        self.local_path = self._fetch_youtube_file(self.url)
                        self._use_stream = False
                        if not self.meta_title:
                            self.meta_title = "YouTube Track"
                    self._download_cover_image()
                    self._ready = True
                    ok, msg = True, "stream-ready"
                if self.meta_title:
                    self._notify(f"♪ {self.display_title()}")
            except Exception as exc:
                ok, msg = False, str(exc)
            finally:
                self._loading = False
                should_play = ok and self._play_when_ready
                if should_play:
                    self._play_when_ready = False
                if done_cb:
                    done_cb(ok, msg)
                if should_play:
                    threading.Thread(target=self.play, daemon=True).start()

        threading.Thread(target=worker, daemon=True).start()

    def _ssl_context(self):
        import ssl
        try:
            import certifi
            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()

    def _urlopen(self, req, timeout: int = 90):
        import ssl
        try:
            return urllib.request.urlopen(req, timeout=timeout, context=self._ssl_context())
        except urllib.error.URLError as exc:
            reason = str(getattr(exc, "reason", exc))
            if "CERTIFICATE" in reason.upper() or "SSL" in reason.upper():
                self._notify("SSL 検証を緩和して再試行中…")
                ctx = ssl._create_unverified_context()
                return urllib.request.urlopen(req, timeout=timeout, context=ctx)
            raise

    def _direct_cache_path(self, url: str, content_type: str = "") -> Path:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        path_ext = Path(urlparse(url).path).suffix.lower()
        ctype = (content_type or "").lower()
        if path_ext in AUDIO_EXTS:
            ext = path_ext
        elif "ogg" in ctype:
            ext = ".ogg"
        elif "wav" in ctype:
            ext = ".wav"
        elif "mp4" in ctype or "m4a" in ctype or "aac" in ctype:
            ext = ".m4a"
        else:
            ext = ".mp3"
        return self._cache_dir / f"direct_{digest}{ext}"

    def _fetch_direct_url(self, url: str) -> str:
        """Fallback: full download when streaming stack unavailable."""
        guessed = self._direct_cache_path(url)
        if guessed.exists() and guessed.stat().st_size > 1024:
            return str(guessed)

        self._notify("フォールバック: ダウンロード中…")
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "AquaFocus/1.0", "Accept": "audio/*,*/*"},
            method="GET",
        )
        with self._urlopen(req, timeout=90) as resp:
            ctype = resp.headers.get("Content-Type", "")
            dest = self._direct_cache_path(url, ctype)
            partial = dest.with_suffix(dest.suffix + ".part")
            total = 0
            with open(partial, "wb") as out:
                while True:
                    chunk = resp.read(64 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    total += len(chunk)
            if total < 256:
                partial.unlink(missing_ok=True)
                raise RuntimeError("音声データが空です")
            partial.replace(dest)
            return str(dest)

    def _fetch_youtube_file(self, url: str) -> str:
        """Fallback: download YouTube audio to disk."""
        outtmpl = str(self._cache_dir / "%(id)s.%(ext)s")
        ffmpeg_exe = resolve_ffmpeg_exe()
        ydl_opts: dict = {
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "overwrites": True,
        }
        if ffmpeg_exe:
            ydl_opts["ffmpeg_location"] = ffmpeg_exe
        path = None
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            vid = info.get("id", "track")
            for ext in ("mp3", "m4a", "ogg", "webm", "opus", "wav", "mp4"):
                candidate = self._cache_dir / f"{vid}.{ext}"
                if candidate.exists():
                    path = str(candidate)
                    break
        if not path:
            raise RuntimeError("音声ファイルを取得できませんでした")
        if path.lower().endswith((".mp3", ".ogg", ".wav")):
            return path
        if not ffmpeg_exe:
            raise RuntimeError("ffmpeg が必要です")
        mp3_path = str(self._cache_dir / f"{Path(path).stem}.mp3")
        proc = subprocess.run(
            [ffmpeg_exe, "-y", "-i", path, "-vn", "-ar", "44100", "-ac", "2", "-b:a", "192k", mp3_path],
            capture_output=True,
            text=True,
            **_subprocess_hidden_kwargs(),
        )
        if proc.returncode != 0 or not Path(mp3_path).exists():
            raise RuntimeError("mp3 変換に失敗")
        return mp3_path

    def play(self) -> None:
        if not self.url or not self.kind:
            return
        if self._is_playing and not self._paused:
            return
        if self._output_device_index is None:
            default_dev = default_output_audio_device()
            if default_dev is None:
                self._notify("利用できる音声出力デバイスが見つかりません")
                return
            self.set_output_device(default_dev[0], default_dev[1])
            self._notify(f"♪ 既定の音声出力を使用: {default_dev[1].split('  ·  ')[0][:40]}")

        if not self._ready:
            self._play_when_ready = True
            self._notify("音楽を準備中…")
            if not self._loading:
                self.prepare_async()
            return

        if self._use_stream:
            try:
                if self._paused and self.streamer._thread and self.streamer._thread.is_alive():
                    self.streamer.resume()
                    self._is_playing = True
                    self._paused = False
                    self._notify("♪ ストリーム再開")
                    return
                self.streamer.set_volume(self._volume)
                self.streamer.start(
                    self._resolve_stream_source,
                    loop=True,
                    on_natural_end=self._on_stream_natural_end,
                    on_error=self._on_stream_error,
                )
                self._is_playing = True
                self._paused = False
                return
            except Exception as exc:
                self._notify(f"ストリーム失敗、切替中… ({exc})")
                self._use_stream = False

        if not self.local_path or not Path(self.local_path).exists():
            try:
                if self.kind == "direct":
                    self.local_path = self._fetch_direct_url(self.url)
                elif self.kind == "spotify":
                    page = self._yt_match_url or self.url
                    self.local_path = self._fetch_youtube_file(page)
                else:
                    self.local_path = self._fetch_youtube_file(self.url)
            except Exception as exc:
                self._notify(f"再生エラー: {exc}")
                return
        if not self._mixer_ok:
            self._notify("pygame が使えず再生できません")
            return
        try:
            if self._paused:
                pygame.mixer.music.unpause()
            else:
                pygame.mixer.music.load(self.local_path)
                pygame.mixer.music.set_volume(self._volume)
                pygame.mixer.music.play(-1)
            self._is_playing = True
            self._paused = False
            self._notify("♪ 再生中（ローカルキャッシュ）")
        except Exception as exc:
            self._notify(f"再生エラー: {exc}")

    def pause(self) -> None:
        if not self._is_playing or self._paused:
            return
        if self._use_stream:
            self.streamer.pause()
            self._paused = True
            self._is_playing = False
            self._notify("ストリーム一時停止")
            return
        if self._mixer_ok and pygame is not None:
            try:
                pygame.mixer.music.pause()
                self._paused = True
                self._is_playing = False
            except Exception:
                pass

    def resume(self) -> None:
        self.play()

    def stop(self) -> None:
        self._play_when_ready = False
        self.streamer.stop()
        if self._mixer_ok and pygame is not None:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
        self._is_playing = False
        self._paused = False

# Particles

class Particle:
    __slots__ = ("x", "y", "vx", "vy", "r", "a", "life")

    def __init__(self, w: int, h: int, water_y: float):
        import random
        self.x = random.uniform(0, w)
        self.y = random.uniform(water_y, h)
        self.vx = random.uniform(-0.35, 0.35)
        self.vy = random.uniform(-1.2, -0.25)
        self.r = random.uniform(1.5, 4.0)
        self.a = random.uniform(0.25, 0.85)
        self.life = random.uniform(40, 120)

    def step(self) -> bool:
        self.x += self.vx
        self.y += self.vy
        self.life -= 1
        self.a *= 0.992
        return self.life > 0 and self.a > 0.05


# Main App

class WaterTimer(ctk.CTk):
    def __init__(self):
        enable_windows_dpi_awareness()
        super().__init__()
        init_ui_fonts()
        self.title("Aqua Focus")
        self.geometry("980x680")
        self.minsize(560, 520)
        apply_window_icon(self)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.theme = THEMES["Abyss Glass"]
        self.is_running = False
        self.is_paused = False
        self.phase1 = 0.0
        self.phase2 = 0.0
        self.phase_glow = 0.0
        self.remaining_seconds = 0.0
        self.total_seconds = 0.0
        self.current_cycle = 1
        self.max_cycles = 1
        self.mode = "Work"
        self.work_time = 25 * 60
        self.break_time = 5 * 60
        self.long_break_time = 15 * 60
        self.long_break_every = 4
        self.is_long_break = False
        self.intention = ""
        self._break_tip_idx = 0

        self.particles: list[Particle] = []
        self._ui_pulse = 0.0
        self._fade_alpha = 0
        self._setup_visible = True
        self._music_status = ""
        self._btn_scale_hint = {}
        self._custom_bg_path: str | None = None
        self._bg_src: object | None = None  # PIL Image
        self._bg_photo = None
        self._bg_cache_size: tuple[int, int] | None = None
        self._disc_angle = 0.0
        self._title_scroll = 0.0
        self._eq_seed = 0.0
        self._cover_tk_cache: dict[tuple[int, str], object] = {}
        self._cover_token = 0  # bump when cover changes
        self._chrome_visible = True
        self._chrome_hide_job = None
        self._calm_focus = True  # psychology-informed low-distraction mode
        self._menu_open = False
        self._temptation_armed = "--temptation-guard" in sys.argv
        self._temptation_job = None
        self._temptation_films: dict[int, dict] = {}  # target_hwnd -> film widgets
        self._temptation_quote_idx = 0
        self._temptation_quote_job = None
        self._dashboard_resize_job = None
        self._dashboard_compact = None

        self.playlist = PlaylistStore(app_root() / "playlist.json")
        self.temptation_exclude = TemptationExcludeStore(
            app_root() / "data" / "temptation_exclude.json"
        )
        settings_path = app_root() / "data" / "settings.json"
        self.settings = SettingsStore(settings_path)
        self.i18n = I18n(settings_path)
        self.reduce_motion = bool(self.settings.get("reduce_motion", False))
        self._ffmpeg_path = ensure_bundled_ffmpeg()
        self._exclude_dialog: ctk.CTkToplevel | None = None
        self._audio_device_map: dict[str, int] = {}
        self.music = MusicController(status_cb=self._on_music_status)
        self.music.on_track_ended = self._on_music_track_ended
        self._apply_saved_audio_device()
        self.agiu = AgiuController(
            status_cb=self._on_agiu_status,
            on_update_available=self._on_agiu_update_available,
        )
        self.v2_modes = AuxiliaryModes(
            self,
            theme_getter=lambda: self.theme,
            font_family=FONT_UI,
        )
        self.workspace = WorkspacePanels(
            self,
            data_dir=app_root() / "data",
            theme_getter=lambda: self.theme,
            font_family=FONT_UI,
            font_bold=FONT_UI_BOLD,
        )
        self.THEMES = THEMES
        self.FONT_UI_BOLD = FONT_UI_BOLD
        self.minimal_shell = MinimalShell(self)

        self.configure(fg_color=self.theme.bg)
        self.setup_ui()
        self.apply_theme(self.theme.name, animate=False)
        self.load_theme_background(self.theme.name)
        self._refresh_playlist_ui()
        self._refresh_temptation_btn()
        self.apply_language()
        self._refresh_audio_device_menu()
        # v2.1.2-style progressive-disclosure Home is the primary experience:
        # one task, one duration, one primary action. Full functionality remains
        # available through Tasks / Stats / Settings / ••• without competing
        # with focus setup. Current crash hardening and focus features stay live.
        self.minimal_shell.install()

        self.bind("<space>", self._hotkey_space)
        self.bind("<Escape>", self._hotkey_esc)
        self.bind("<KeyPress-p>", self._hotkey_space)
        self.focus_set()

        self.after(40, self._ambient_loop)
        if self._temptation_armed:
            self.after(300, self._start_temptation_watch)
            self.after(500, lambda: self.hero_sub.configure(
                text=self.t("temptation_armed_admin")
            ))
        self.after(200, self._report_ffmpeg_status)
        if self.settings.get("agiu_auto_check", True):
            self.after(1800, self._agiu_check_silent)

    def t(self, key: str, **kwargs) -> str:
        return self.i18n.t(key, **kwargs)

    def _report_ffmpeg_status(self) -> None:
        path = self._ffmpeg_path or resolve_ffmpeg_exe()
        if path:
            self._on_music_status(self.t("ffmpeg_ok"))
        else:
            self._on_music_status(self.t("ffmpeg_missing"))

    def _on_language_change(self, choice: str) -> None:
        self.i18n.set_lang("en" if str(choice).lower().startswith("en") else "ja")
        self.apply_language()

    def _apply_saved_audio_device(self) -> None:
        name = str(self.settings.get("audio_output_name") or "")
        raw_idx = self.settings.get("audio_output_index")
        idx = None
        try:
            if raw_idx is not None and str(raw_idx).strip() != "":
                idx = int(raw_idx)
        except (TypeError, ValueError):
            idx = None
        resolved = resolve_output_device_index(idx, name)
        if resolved is not None:
            devices = list_output_audio_devices()
            label = next((lab for i, lab in devices if i == resolved), name)
            self.music.set_output_device(resolved, label or name)

    def _refresh_audio_device_menu(self, preserve: bool = False) -> None:
        if not hasattr(self, "audio_device_menu"):
            return
        pick = self.t("audio_pick")
        devices = list_output_audio_devices()
        self._audio_device_map = {lab: i for i, lab in devices}
        values = [pick] + [lab for _i, lab in devices]
        if not devices:
            values = [pick, self.t("audio_none")]
        current = ""
        if preserve:
            try:
                current = self.audio_device_menu.get()
            except Exception:
                current = ""
        self.audio_device_menu.configure(values=values)
        saved_name = str(self.settings.get("audio_output_name") or "")
        saved_idx = self.settings.get("audio_output_index")
        try:
            saved_i = int(saved_idx) if saved_idx is not None and str(saved_idx).strip() != "" else None
        except (TypeError, ValueError):
            saved_i = None
        resolved = resolve_output_device_index(saved_i, saved_name)
        chosen = pick
        if resolved is not None:
            for lab, i in self._audio_device_map.items():
                if i == resolved:
                    chosen = lab
                    break
        elif current and current in values and current != pick:
            chosen = current
        self.audio_device_menu.set(chosen)
        if chosen != pick and chosen in self._audio_device_map:
            self.music.set_output_device(self._audio_device_map[chosen], chosen)

    def _on_audio_device_change(self, choice: str) -> None:
        pick = self.t("audio_pick")
        none_lbl = self.t("audio_none")
        if choice in (pick, none_lbl) or choice not in self._audio_device_map:
            self.settings.set("audio_output_name", "")
            self.settings.set("audio_output_index", None)
            self.music.set_output_device(None, "")
            self._on_music_status(self.t("audio_need_pick"))
            return
        idx = self._audio_device_map[choice]
        self.settings.set("audio_output_name", choice)
        self.settings.set("audio_output_index", idx)
        self.music.set_output_device(idx, choice)
        self._on_music_status(self.t("audio_selected", name=choice.split("  ·  ")[0][:40]))

    def _on_agiu_auto_toggle(self) -> None:
        on = bool(self.agiu_auto_sw.get())
        self.settings.set("agiu_auto_check", on)

    def _on_agiu_status(self, msg: str) -> None:
        def ui():
            if hasattr(self, "agiu_status_lbl"):
                self.agiu_status_lbl.configure(text=msg)
        self.after(0, ui)

    def _agiu_check_silent(self) -> None:
        self.agiu.check_async()

    def _agiu_check_manual(self) -> None:
        self._on_agiu_status(self.t("agiu_checking"))
        self.agiu.on_update_available = self._on_agiu_update_available
        # wrap check to show up-to-date dialog

        def worker():
            self._on_agiu_status(self.t("agiu_checking"))
            info = fetch_latest_release()
            if info is None:
                self._on_agiu_status(self.t("agiu_fail"))
                self.after(0, lambda: messagebox.showwarning(self.t("agiu_title"), self.t("agiu_fail")))
                return
            self.agiu.latest = info
            if is_newer(info.version, APP_VERSION):
                self._on_agiu_status(self.t("agiu_available", cur=APP_VERSION, new=info.version))
                self.after(0, lambda: self._on_agiu_update_available(info))
            else:
                self._on_agiu_status(self.t("agiu_uptodate", ver=APP_VERSION))
                self.after(
                    0,
                    lambda: messagebox.showinfo(
                        self.t("agiu_title"),
                        self.t("agiu_uptodate", ver=APP_VERSION),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _on_agiu_update_available(self, info: ReleaseInfo) -> None:
        def ui():
            msg = self.t("agiu_prompt", cur=APP_VERSION, new=info.version, name=info.asset_name)
            if messagebox.askyesno(self.t("agiu_title"), msg):
                self._agiu_download_apply(info)
            else:
                self._on_agiu_status(self.t("agiu_later", ver=info.version))

        self.after(0, ui)

    def _agiu_download_apply(self, info: ReleaseInfo) -> None:
        self._on_agiu_status(self.t("agiu_downloading", name=info.asset_name))

        def progress(done: int, total: int) -> None:
            if total > 0:
                pct = int(done * 100 / total)
                self._on_agiu_status(self.t("agiu_progress", pct=pct))

        def worker():
            try:
                if not getattr(sys, "frozen", False):
                    import webbrowser

                    self._on_agiu_status(self.t("agiu_dev_open"))
                    webbrowser.open(info.html_url or RELEASES_PAGE)
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            self.t("agiu_title"),
                            self.t("agiu_dev_open"),
                        ),
                    )
                    return
                self.agiu.download_and_apply(info, progress_cb=progress)
                self._on_agiu_status(self.t("agiu_restarting"))
                self.after(400, self.destroy)
            except Exception as exc:
                self._on_agiu_status(self.t("agiu_apply_fail", msg=str(exc)[:80]))
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        self.t("agiu_title"),
                        self.t("agiu_apply_fail", msg=str(exc)),
                    ),
                )

        threading.Thread(target=worker, daemon=True).start()

    def _break_tips(self) -> list[str]:
        return [self.t(k) for k in TIP_KEYS]

    def _focus_quotes(self) -> list[str]:
        return [self.t(k) for k in QUOTE_KEYS]

    def _science_presets(self) -> list[tuple]:
        """(display_name, w, b, lb, every, cycles, blurb, key)"""
        out = []
        for name_k, blurb_k, w, b, lb, every, cycles in PRESET_KEYS:
            out.append((self.t(name_k), w, b, lb, every, cycles, self.t(blurb_k), name_k))
        return out

    def apply_language(self) -> None:
        """Refresh visible UI strings after JA/EN switch."""
        t = self.t
        if hasattr(self, "lang_menu"):
            self.lang_menu.configure(values=[t("lang_ja"), t("lang_en")])
            self.lang_menu.set(t("lang_en") if self.i18n.lang == "en" else t("lang_ja"))
        if hasattr(self, "audio_device_menu"):
            self._refresh_audio_device_menu(preserve=True)
        for attr, key in (
            ("sidebar_sub", "app_subtitle"),
            ("sidebar_science", "science_badge"),
            ("sidebar_focus_lock", "focus_lock"),
            ("temptation_exclude_btn", "temptation_exclude_btn"),
            ("sidebar_presets", "presets"),
            ("sidebar_theme", "theme"),
            ("sidebar_bg", "background"),
            ("bg_pick_btn", "pick_image"),
            ("bg_theme_btn", "reset_theme_bg"),
            ("bg_label", "theme_art"),
            ("hero_label", "timer_settings"),
            ("science_note", "science_doc_hint"),
            ("intention_title_lbl", "intention_title"),
            ("intention_sub_lbl", "intention_sub"),
            ("rhythm_title_lbl", "rhythm_title"),
            ("long_note_lbl", "long_note"),
            ("music_title_lbl", "focus_music"),
            ("music_hint_lbl", "music_hint_long"),
            ("add_playlist_btn", "add_playlist"),
            ("vol_lbl", "volume"),
            ("preload_btn", "stream_prep"),
            ("start_btn", "start_focus"),
            ("hint_text", "hint_keys"),
            ("pause_btn", "resume" if self.is_paused else "pause"),
            ("stop_btn", "exit"),
            ("continuous_sw", "continuous"),
            ("calm_sw", "calm_focus"),
            ("menu_prev_btn", "prev_track"),
            ("menu_next_btn", "next_track"),
            ("menu_skip_btn", "skip_track"),
            ("menu_exclude_btn", "temptation_exclude_btn"),
            ("menu_exit_btn", "exit_focus"),
            ("menu_learning_lbl", "learning_science"),
            ("menu_learning_blurb", "learning_blurb"),
            ("menu_session_lbl", "session"),
            ("menu_title_lbl", "menu"),
            ("lang_section_lbl", "lang"),
            ("audio_section_lbl", "audio_out"),
            ("audio_refresh_btn", "audio_refresh"),
            ("agiu_section_lbl", "agiu_title"),
            ("agiu_auto_sw", "agiu_auto"),
            ("agiu_check_btn", "agiu_check"),
        ):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.configure(text=t(key))
                except Exception:
                    pass
        if hasattr(self, "agiu_version_lbl"):
            try:
                self.agiu_version_lbl.configure(text=t("agiu_version", ver=APP_VERSION))
            except Exception:
                pass
        if hasattr(self, "entry_intention"):
            try:
                self.entry_intention.configure(placeholder_text=t("intention_ph"))
            except Exception:
                pass
        if hasattr(self, "entry_music"):
            try:
                self.entry_music.configure(placeholder_text=t("music_url_ph"))
            except Exception:
                pass
        if hasattr(self, "menu_url_entry"):
            try:
                self.menu_url_entry.configure(placeholder_text=t("url_add_ph"))
            except Exception:
                pass
        for lbl, key in getattr(self, "_pillar_labels", []):
            try:
                lbl.configure(text=t(key))
            except Exception:
                pass
        for lbl, key in getattr(self, "_input_label_refs", []):
            try:
                lbl.configure(text=t(key))
            except Exception:
                pass
        for lbl, key in getattr(self, "_legend_labels", []):
            try:
                lbl.configure(text=t(key))
            except Exception:
                pass
        if not (self.is_running or (hasattr(self, "wave_frame") and self.wave_frame.winfo_ismapped())):
            try:
                self.hero_sub.configure(text=t("hero_sub_default"))
            except Exception:
                pass
        self._rebuild_preset_buttons()
        self._refresh_temptation_btn()
        self._refresh_playlist_ui()
        self._update_live_films_language()
        self._report_ffmpeg_status()

    def _update_live_films_language(self) -> None:
        quotes = self._focus_quotes()
        quote = quotes[self._temptation_quote_idx % len(quotes)] if quotes else ""
        for film in list(self._temptation_films.values()):
            try:
                film["title"].configure(text=self.t("film_title"))
                film["body"].configure(text=self.t("film_body"))
                film["foot"].configure(text=self.t("film_footer"))
                film["quote"].configure(text=quote)
            except Exception:
                pass

    def _rebuild_preset_buttons(self) -> None:
        host = getattr(self, "_preset_host", None)
        if host is None:
            return
        for child in list(host.winfo_children()):
            try:
                child.destroy()
            except Exception:
                pass
        self.preset_btns = []
        self._preset_canvases = []
        presets = self._science_presets()
        if not getattr(self, "_selected_preset_key", None) and presets:
            self._selected_preset_key = presets[0][7]
        for name, w, b, lb, every, cycles, blurb, key in presets:
            card = ctk.CTkFrame(
                host, fg_color=self.theme.bg, corner_radius=12,
                border_width=1, border_color=self.theme.glow,
            )
            card.pack(pady=4, padx=10, fill="x")
            mini = tk.Canvas(card, height=28, bg=self.theme.bg, highlightthickness=0)
            mini.pack(fill="x", padx=8, pady=(8, 2))
            self._draw_rhythm_strip(mini, w, b, lb, every, width_hint=170)
            self._preset_canvases.append((mini, w, b, lb, every))
            btn = ctk.CTkButton(
                card, text=name, height=28,
                font=ctk.CTkFont(family=FONT_UI, size=11),
                fg_color="transparent", hover_color=self.theme.glow,
                text_color=self.theme.text, anchor="w",
                command=lambda w=w, b=b, lb=lb, e=every, c=cycles, n=name, bl=blurb, k=key: self.set_preset(
                    w, b, n, long_break=lb, long_every=e, cycles=c, blurb=bl, key=k,
                ),
            )
            btn.pack(fill="x", padx=6, pady=(0, 6))
            self.preset_btns.append((btn, card, key))
        self.after(40, lambda: self._highlight_preset(getattr(self, "_selected_preset_key", "")))

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.grid(row=0, column=0, sticky="nsew")

        self.sidebar = ctk.CTkScrollableFrame(
            self.main_container,
            width=262,
            corner_radius=18,
            fg_color=self.theme.sidebar,
            border_width=1,
            border_color=self.theme.glow,
            scrollbar_button_color=self.theme.glow,
            scrollbar_button_hover_color=self.theme.accent,
        )
        self.sidebar.pack(side="left", fill="y", padx=(12, 0), pady=12)

        ctk.CTkLabel(
            self.sidebar, text="Aqua Focus",
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=24),
            text_color=self.theme.text,
        ).pack(pady=(28, 4), padx=16, anchor="w")
        self.sidebar_sub = ctk.CTkLabel(
            self.sidebar, text=self.t("app_subtitle"),
            font=ctk.CTkFont(family=FONT_UI, size=12),
            text_color=self.theme.muted,
        )
        self.sidebar_sub.pack(padx=16, anchor="w")
        self.sidebar_science = ctk.CTkLabel(
            self.sidebar, text=self.t("science_badge"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.accent,
        )
        self.sidebar_science.pack(padx=16, pady=(4, 0), anchor="w")

        self.workspace_section_lbl = ctk.CTkLabel(
            self.sidebar, text="WORKSPACE",
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=10),
            text_color=self.theme.accent,
        )
        self.workspace_section_lbl.pack(pady=(14, 5), padx=16, anchor="w")
        self.workspace_buttons = []
        for label, command in (
            ("Coral Tasks", self.workspace.open_tasks),
            ("Abyss Stats", self.workspace.open_stats),
            ("Ocean Soundscape", self.workspace.open_soundscape),
            ("Reef Extensions", self.workspace.open_extensions),
        ):
            btn = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=38,
                corner_radius=12,
                fg_color="transparent",
                hover_color=self.theme.glow,
                border_width=1,
                border_color=self.theme.glow,
                text_color=self.theme.text,
                font=ctk.CTkFont(family=FONT_UI_BOLD, size=12),
                anchor="w",
                command=command,
            )
            btn.pack(padx=14, pady=2, fill="x")
            self.workspace_buttons.append(btn)

        self.lang_section_lbl = ctk.CTkLabel(
            self.sidebar, text=self.t("lang"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.lang_section_lbl.pack(pady=(14, 6), padx=16, anchor="w")
        self.lang_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=[self.t("lang_ja"), self.t("lang_en")],
            command=self._on_language_change,
            fg_color=self.theme.glow,
            button_color=self.theme.accent,
            button_hover_color=self.theme.accent_hover,
            dropdown_fg_color=self.theme.sidebar,
            font=ctk.CTkFont(family=FONT_UI, size=12),
        )
        self.lang_menu.set(self.t("lang_en") if self.i18n.lang == "en" else self.t("lang_ja"))
        self.lang_menu.pack(padx=14, fill="x")

        self.audio_section_lbl = ctk.CTkLabel(
            self.sidebar, text=self.t("audio_out"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.audio_section_lbl.pack(pady=(14, 6), padx=16, anchor="w")
        self.audio_device_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=[self.t("audio_pick")],
            command=self._on_audio_device_change,
            fg_color=self.theme.glow,
            button_color=self.theme.accent,
            button_hover_color=self.theme.accent_hover,
            dropdown_fg_color=self.theme.sidebar,
            font=ctk.CTkFont(family=FONT_UI, size=11),
            dynamic_resizing=False,
        )
        self.audio_device_menu.set(self.t("audio_pick"))
        self.audio_device_menu.pack(padx=14, fill="x")
        self.audio_refresh_btn = ctk.CTkButton(
            self.sidebar, text=self.t("audio_refresh"), height=28,
            font=ctk.CTkFont(family=FONT_UI, size=11),
            fg_color="transparent", border_width=1,
            border_color=self.theme.glow, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self._refresh_audio_device_menu,
        )
        self.audio_refresh_btn.pack(padx=14, fill="x", pady=(6, 0))

        self.agiu_section_lbl = ctk.CTkLabel(
            self.sidebar, text=self.t("agiu_title"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.agiu_section_lbl.pack(pady=(14, 6), padx=16, anchor="w")
        self.agiu_version_lbl = ctk.CTkLabel(
            self.sidebar, text=self.t("agiu_version", ver=APP_VERSION),
            font=ctk.CTkFont(family=FONT_UI, size=10),
            text_color=self.theme.muted,
        )
        self.agiu_version_lbl.pack(padx=16, anchor="w")
        self.agiu_auto_sw = ctk.CTkSwitch(
            self.sidebar, text=self.t("agiu_auto"),
            font=ctk.CTkFont(family=FONT_UI, size=12),
            text_color=self.theme.text,
            progress_color=self.theme.accent,
            command=self._on_agiu_auto_toggle,
        )
        if self.settings.get("agiu_auto_check", True):
            self.agiu_auto_sw.select()
        else:
            self.agiu_auto_sw.deselect()
        self.agiu_auto_sw.pack(padx=14, pady=(8, 0), anchor="w")
        self.agiu_check_btn = ctk.CTkButton(
            self.sidebar, text=self.t("agiu_check"), height=32,
            font=ctk.CTkFont(family=FONT_UI, size=12),
            fg_color="transparent", border_width=1,
            border_color=self.theme.glow, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self._agiu_check_manual,
        )
        self.agiu_check_btn.pack(padx=14, fill="x", pady=(8, 0))
        self.agiu_status_lbl = ctk.CTkLabel(
            self.sidebar, text="",
            font=ctk.CTkFont(size=10),
            text_color=self.theme.muted,
            wraplength=170, justify="left",
        )
        self.agiu_status_lbl.pack(padx=16, pady=(4, 0), anchor="w")

        self.sidebar_focus_lock = ctk.CTkLabel(
            self.sidebar, text=self.t("focus_lock"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.sidebar_focus_lock.pack(pady=(18, 6), padx=16, anchor="w")
        self.temptation_btn = ctk.CTkButton(
            self.sidebar, text=self.t("temptation_off"), height=40,
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=13),
            fg_color="#8b3a3a", hover_color="#a84848",
            text_color="#fff5f5",
            command=self.toggle_temptation_guard,
        )
        self.temptation_btn.pack(padx=14, fill="x")
        self.temptation_hint = ctk.CTkLabel(
            self.sidebar,
            text=self.t("temptation_hint_win" if IS_WINDOWS else "temptation_hint_unix"),
            font=ctk.CTkFont(size=10),
            text_color=self.theme.muted,
            wraplength=170, justify="left",
        )
        self.temptation_hint.pack(padx=16, pady=(6, 0), anchor="w")
        self.temptation_exclude_btn = ctk.CTkButton(
            self.sidebar, text=self.t("temptation_exclude_btn"), height=32,
            font=ctk.CTkFont(family=FONT_UI, size=12),
            fg_color="transparent", border_width=1,
            border_color=self.theme.glow, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self.open_temptation_exclude_dialog,
        )
        self.temptation_exclude_btn.pack(padx=14, fill="x", pady=(8, 0))
        self.temptation_exclude_label = ctk.CTkLabel(
            self.sidebar, text="",
            font=ctk.CTkFont(size=10),
            text_color=self.theme.muted,
            wraplength=170, justify="left",
        )
        self.temptation_exclude_label.pack(padx=16, pady=(4, 0), anchor="w")

        self.sidebar_presets = ctk.CTkLabel(
            self.sidebar, text=self.t("presets"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.sidebar_presets.pack(pady=(16, 6), padx=16, anchor="w")

        self._preset_host = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self._preset_host.pack(fill="x")
        self.preset_btns = []
        self._preset_canvases = []
        self._selected_preset_key = PRESET_KEYS[0][0]
        self._rebuild_preset_buttons()

        self.sidebar_theme = ctk.CTkLabel(
            self.sidebar, text=self.t("theme"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.sidebar_theme.pack(pady=(24, 8), padx=16, anchor="w")

        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=list(THEMES.keys()),
            command=self.apply_theme,
            fg_color=self.theme.glow,
            button_color=self.theme.accent,
            button_hover_color=self.theme.accent_hover,
            dropdown_fg_color=self.theme.sidebar,
            font=ctk.CTkFont(family=FONT_UI, size=12),
        )
        self.theme_menu.set(self.theme.name)
        self.theme_menu.pack(padx=14, fill="x")

        self.reduce_motion_sw = ctk.CTkSwitch(
            self.sidebar,
            text="Reduce Motion",
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.text,
            progress_color=self.theme.accent,
            command=self._toggle_reduce_motion,
        )
        if self.reduce_motion:
            self.reduce_motion_sw.select()
        self.reduce_motion_sw.pack(padx=14, pady=(9, 0), anchor="w")

        self.sidebar_bg = ctk.CTkLabel(
            self.sidebar, text=self.t("background"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.sidebar_bg.pack(pady=(22, 8), padx=16, anchor="w")

        self.bg_pick_btn = ctk.CTkButton(
            self.sidebar, text=self.t("pick_image"), height=34,
            font=ctk.CTkFont(family=FONT_UI, size=12),
            fg_color="transparent", border_width=1,
            border_color=self.theme.glow, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self.pick_background,
        )
        self.bg_pick_btn.pack(padx=14, fill="x", pady=(0, 6))
        self.bg_theme_btn = ctk.CTkButton(
            self.sidebar, text=self.t("reset_theme_bg"), height=34,
            font=ctk.CTkFont(family=FONT_UI, size=12),
            fg_color="transparent", border_width=1,
            border_color=self.theme.glow, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self.reset_background,
        )
        self.bg_theme_btn.pack(padx=14, fill="x")
        self.bg_label = ctk.CTkLabel(
            self.sidebar, text=self.t("theme_art"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        )
        self.bg_label.pack(padx=16, pady=(8, 0), anchor="w")

        self.setup_frame = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color="transparent",
            corner_radius=18,
            scrollbar_button_color=self.theme.glow,
            scrollbar_button_hover_color=self.theme.accent,
        )
        self.setup_frame.pack(side="right", fill="both", expand=True, padx=(20, 12), pady=12)

        # Keep advanced/occasional controls one click away instead of letting the
        # dashboard grow into a wall of controls. This does not remove features:
        # it reuses MinimalShell's complete More/Settings surface.
        # Keep frequent workspace actions discoverable; move the long tail into
        # ••• instead of deleting it. This restores capability without returning
        # to a wall of controls.
        self.dashboard_actions = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        self.dashboard_actions.pack(fill="x", pady=(4, 0))
        self.dashboard_tasks_btn = ctk.CTkButton(
            self.dashboard_actions, text="Tasks", width=78, height=34, corner_radius=17,
            fg_color="transparent", hover_color=self.theme.glow,
            border_width=1, border_color=self.theme.glow, text_color=self.theme.text,
            command=self.workspace.open_tasks,
        )
        self.dashboard_tasks_btn.pack(side="right", padx=(6, 0))
        self.dashboard_stats_btn = ctk.CTkButton(
            self.dashboard_actions, text="Stats", width=78, height=34, corner_radius=17,
            fg_color="transparent", hover_color=self.theme.glow,
            border_width=1, border_color=self.theme.glow, text_color=self.theme.text,
            command=self.workspace.open_stats,
        )
        self.dashboard_stats_btn.pack(side="right", padx=(6, 0))
        self.dashboard_more_btn = ctk.CTkButton(
            self.dashboard_actions,
            text="•••",
            width=44,
            height=34,
            corner_radius=17,
            fg_color="transparent",
            hover_color=self.theme.glow,
            border_width=1,
            border_color=self.theme.glow,
            text_color=self.theme.muted,
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=15),
            command=self.minimal_shell.open_tools,
        )
        self.dashboard_more_btn.pack(side="right")

        self.hero_label = ctk.CTkLabel(
            self.setup_frame, text=self.t("timer_settings"),
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=38),
            text_color=self.theme.text,
        )
        self.hero_label.pack(pady=(24, 6), anchor="w")
        self.hero_sub = ctk.CTkLabel(
            self.setup_frame,
            text=self.t("hero_sub_default"),
            font=ctk.CTkFont(family=FONT_UI, size=14),
            text_color=self.theme.muted,
            wraplength=720, justify="left",
        )
        self.hero_sub.pack(anchor="w", pady=(0, 12))

        # Aqua Focus v2: animated deep-sea home hero.
        self.ocean_hero = OceanHero(
            self.setup_frame,
            theme_getter=lambda: self.theme,
            reduce_motion_getter=lambda: self.reduce_motion,
            font_family=FONT_UI,
            height=145,
        )
        self.ocean_hero.pack(fill="x", pady=(0, 12))

        self.mode_launcher = ctk.CTkFrame(
            self.setup_frame,
            fg_color=self.theme.sidebar,
            corner_radius=20,
            border_width=1,
            border_color=self.theme.glow,
        )
        self.mode_launcher.pack(fill="x", pady=(0, 14))
        mode_head = ctk.CTkFrame(self.mode_launcher, fg_color="transparent")
        mode_head.pack(fill="x", padx=16, pady=(13, 8))
        ctk.CTkLabel(
            mode_head,
            text="QUICK DIVE",
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=12),
            text_color=self.theme.accent,
        ).pack(side="left")
        ctk.CTkLabel(
            mode_head,
            text="Choose how you want to focus",
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
        ).pack(side="right")

        mode_row = ctk.CTkFrame(self.mode_launcher, fg_color="transparent")
        mode_row.pack(fill="x", padx=12, pady=(0, 14))
        mode_row.grid_columnconfigure(0, weight=1)
        mode_row.grid_columnconfigure(1, weight=1)
        self.v2_mode_buttons = []
        mode_specs = [
            ("FOCUS\nPomodoro & presets", self.start_immersive_timer, self.theme.accent),
            ("DEEP DIVE\n90 min · minimal", self.start_deep_dive_mode, self.theme.wave_front_break),
            ("COUNTDOWN\nSingle timer", self.v2_modes.open_countdown, self.theme.glow),
            ("STOPWATCH\nOpen-ended flow", self.v2_modes.open_stopwatch, self.theme.glow),
            ("BLUE ALARM\nOne-time reminder", self.v2_modes.open_alarm, "#8a6a20"),
        ]
        for i, (label, command, color) in enumerate(mode_specs):
            btn = ctk.CTkButton(
                mode_row,
                text=label,
                height=58,
                corner_radius=14,
                fg_color=color,
                hover_color=self.theme.accent_hover,
                text_color="#f8fcff",
                font=ctk.CTkFont(family=FONT_UI_BOLD, size=12),
                command=command,
            )
            btn.grid(row=i // 2, column=i % 2, sticky="ew", padx=5, pady=5)
            self.v2_mode_buttons.append(btn)

        self.science_row = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        self.science_row.pack(fill="x", pady=(0, 12))
        self._science_pillar_cards = []
        self._pillar_labels = []
        pillars = [
            ("pillar_plan", "pillar_plan_sub", self.theme.accent),
            ("pillar_long", "pillar_long_sub", "#e8b86d"),
            ("pillar_one", "pillar_one_sub", self.theme.wave_front_break),
            ("pillar_recover", "pillar_recover_sub", self.theme.glow),
        ]
        for i, (title_k, sub_k, col) in enumerate(pillars):
            card = ctk.CTkFrame(
                self.science_row, fg_color=self.theme.sidebar, corner_radius=12,
                border_width=1, border_color=self.theme.glow,
            )
            card.grid(
                row=i // 2,
                column=i % 2,
                padx=(0 if i % 2 == 0 else 6),
                pady=(0 if i < 2 else 6, 0),
                sticky="nsew",
            )
            sw = ctk.CTkLabel(card, text="", width=8, height=36, fg_color=col, corner_radius=4)
            sw.pack(side="left", padx=(10, 8), pady=10)
            txt = ctk.CTkFrame(card, fg_color="transparent")
            txt.pack(side="left", fill="both", expand=True, pady=8, padx=(0, 10))
            title_lbl = ctk.CTkLabel(
                txt, text=self.t(title_k), font=ctk.CTkFont(family=FONT_UI_BOLD, size=13),
                text_color=self.theme.text,
            )
            title_lbl.pack(anchor="w")
            sub_lbl = ctk.CTkLabel(
                txt, text=self.t(sub_k), font=ctk.CTkFont(family=FONT_UI, size=11), text_color=self.theme.muted,
            )
            sub_lbl.pack(anchor="w")
            self._pillar_labels.extend([(title_lbl, title_k), (sub_lbl, sub_k)])
            self._science_pillar_cards.append((card, sw))
            self.science_row.grid_columnconfigure(i % 2, weight=1)
        self.science_note = ctk.CTkLabel(
            self.setup_frame,
            text=self.t("science_doc_hint"),
            font=ctk.CTkFont(family=FONT_UI, size=10),
            text_color=self.theme.muted,
        )
        self.science_note.pack(anchor="w", pady=(0, 10))

        self.intention_panel = ctk.CTkFrame(self.setup_frame, fg_color=self.theme.sidebar, corner_radius=16)
        self.intention_panel.pack(fill="x", pady=(0, 10))
        int_inner = ctk.CTkFrame(self.intention_panel, fg_color="transparent")
        int_inner.pack(fill="x", padx=18, pady=14)
        int_head = ctk.CTkFrame(int_inner, fg_color="transparent")
        int_head.pack(fill="x")
        self.intention_badge = ctk.CTkLabel(
            int_head, text="1", width=36, height=36,
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=18),
            fg_color=self.theme.accent, text_color="#0a1218", corner_radius=18,
        )
        self.intention_badge.pack(side="left", padx=(0, 10))
        head_txt = ctk.CTkFrame(int_head, fg_color="transparent")
        head_txt.pack(side="left", fill="x", expand=True)
        self.intention_title_lbl = ctk.CTkLabel(
            head_txt, text=self.t("intention_title"),
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=14),
            text_color=self.theme.text,
        )
        self.intention_title_lbl.pack(anchor="w")
        self.intention_sub_lbl = ctk.CTkLabel(
            head_txt,
            text=self.t("intention_sub"),
            font=ctk.CTkFont(size=11), text_color=self.theme.muted,
        )
        self.intention_sub_lbl.pack(anchor="w")
        self.entry_intention = ctk.CTkEntry(
            int_inner, height=38, placeholder_text=self.t("intention_ph"),
            font=ctk.CTkFont(size=13), border_width=1, border_color=self.theme.glow,
        )
        self.entry_intention.pack(fill="x", pady=(10, 0))

        self.rhythm_panel = ctk.CTkFrame(self.setup_frame, fg_color=self.theme.sidebar, corner_radius=16)
        self.rhythm_panel.pack(fill="x", pady=(0, 10))
        rh = ctk.CTkFrame(self.rhythm_panel, fg_color="transparent")
        rh.pack(fill="x", padx=18, pady=14)
        self.rhythm_title_lbl = ctk.CTkLabel(
            rh, text=self.t("rhythm_title"),
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=14),
            text_color=self.theme.text,
        )
        self.rhythm_title_lbl.pack(anchor="w")
        self.rhythm_legend_row = ctk.CTkFrame(rh, fg_color="transparent")
        self.rhythm_legend_row.pack(anchor="w", pady=(2, 8))
        self._rhythm_legend_swatches = []
        self._legend_labels = []
        for label_k, key in (("legend_work", "work"), ("legend_short", "short"), ("legend_long", "long")):
            sw = ctk.CTkLabel(
                self.rhythm_legend_row, text="", width=12, height=12,
                fg_color=self._rhythm_color(key), corner_radius=3,
            )
            sw.pack(side="left", padx=(0, 4))
            leg = ctk.CTkLabel(
                self.rhythm_legend_row, text=self.t(label_k),
                font=ctk.CTkFont(size=11), text_color=self.theme.muted,
            )
            leg.pack(side="left", padx=(0, 12))
            self._rhythm_legend_swatches.append((sw, key))
            self._legend_labels.append((leg, label_k))
        self.rhythm_canvas = tk.Canvas(rh, height=44, bg=self.theme.sidebar, highlightthickness=0)
        self.rhythm_canvas.pack(fill="x")
        self.after(100, self._refresh_rhythm_preview)

        self.inputs_row = ctk.CTkFrame(self.setup_frame, fg_color=self.theme.sidebar, corner_radius=16)
        self.inputs_row.pack(fill="x", pady=8)
        inner = ctk.CTkFrame(self.inputs_row, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=16)

        self._input_label_refs = []
        self.entry_work = self._compact_input(inner, "work_min", "25", 0)
        self.entry_break = self._compact_input(inner, "break_min", "5", 1)
        self.entry_cycles = self._compact_input(inner, "cycles", "4", 2)
        for i in range(3):
            inner.grid_columnconfigure(i, weight=1)

        inner2 = ctk.CTkFrame(self.inputs_row, fg_color="transparent")
        inner2.pack(fill="x", padx=18, pady=(0, 16))
        self.entry_long_break = self._compact_input(inner2, "long_break_min", "15", 0)
        self.entry_long_every = self._compact_input(inner2, "long_every", "4", 1)
        self.long_note_lbl = ctk.CTkLabel(
            inner2,
            text=self.t("long_note"),
            font=ctk.CTkFont(size=10), text_color=self.theme.muted,
        )
        self.long_note_lbl.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        for i in range(2):
            inner2.grid_columnconfigure(i, weight=1)

        for ent in (self.entry_work, self.entry_break, self.entry_long_break, self.entry_long_every):
            ent.bind("<KeyRelease>", lambda _e: self._refresh_rhythm_preview())

        self.music_panel = ctk.CTkFrame(self.setup_frame, fg_color=self.theme.sidebar, corner_radius=16)
        self.music_panel.pack(fill="x", pady=14)

        music_inner = ctk.CTkFrame(self.music_panel, fg_color="transparent")
        music_inner.pack(fill="x", padx=18, pady=16)

        self.music_title_lbl = ctk.CTkLabel(
            music_inner, text=self.t("focus_music"),
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=15),
            text_color=self.theme.text,
        )
        self.music_title_lbl.pack(anchor="w")
        self.music_hint_lbl = ctk.CTkLabel(
            music_inner,
            text=self.t("music_hint_long"),
            font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color=self.theme.muted,
            wraplength=520, justify="left",
        )
        self.music_hint_lbl.pack(anchor="w", pady=(2, 10))

        self.entry_music = ctk.CTkEntry(
            music_inner, height=40,
            placeholder_text=self.t("music_url_ph"),
            font=ctk.CTkFont(family=FONT_UI, size=13),
            border_width=1, border_color=self.theme.glow,
        )
        self.entry_music.pack(fill="x")

        add_row = ctk.CTkFrame(music_inner, fg_color="transparent")
        add_row.pack(fill="x", pady=(8, 0))
        self.add_playlist_btn = ctk.CTkButton(
            add_row, text=self.t("add_playlist"), height=34,
            font=ctk.CTkFont(family=FONT_UI, size=12),
            fg_color="transparent", border_width=1,
            border_color=self.theme.glow, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self.add_current_url_to_playlist,
        )
        self.add_playlist_btn.pack(side="left")
        self.playlist_count_label = ctk.CTkLabel(
            add_row, text="", font=ctk.CTkFont(size=11), text_color=self.theme.muted,
        )
        self.playlist_count_label.pack(side="left", padx=12)

        vol_row = ctk.CTkFrame(music_inner, fg_color="transparent")
        vol_row.pack(fill="x", pady=(12, 0))
        self.vol_lbl = ctk.CTkLabel(vol_row, text=self.t("volume"), font=ctk.CTkFont(size=12), text_color=self.theme.muted)
        self.vol_lbl.pack(side="left")
        self.volume_slider = ctk.CTkSlider(
            vol_row, from_=0, to=1, number_of_steps=20,
            command=self._on_volume,
            progress_color=self.theme.accent,
            button_color=self.theme.accent,
            button_hover_color=self.theme.accent_hover,
        )
        self.volume_slider.set(0.55)
        self.volume_slider.pack(side="left", fill="x", expand=True, padx=12)
        self.music_status_label = ctk.CTkLabel(
            music_inner, text="", font=ctk.CTkFont(size=11), text_color=self.theme.muted,
        )
        self.music_status_label.pack(anchor="w", pady=(8, 0))

        self.now_preview = tk.Canvas(
            music_inner, width=320, height=96,
            bg=self.theme.sidebar, highlightthickness=0,
        )
        self.now_preview.pack(anchor="w", pady=(12, 0))

        action_row = ctk.CTkFrame(self.setup_frame, fg_color="transparent")
        action_row.pack(fill="x", pady=(18, 8))

        self.preload_btn = ctk.CTkButton(
            action_row, text=self.t("stream_prep"), height=46, width=140,
            font=ctk.CTkFont(family=FONT_UI, size=14),
            fg_color="transparent", border_width=1,
            border_color=self.theme.accent, text_color=self.theme.text,
            hover_color=self.theme.glow,
            command=self.preload_music,
        )
        self.preload_btn.pack(side="left", padx=(0, 10))

        self.start_btn = ctk.CTkButton(
            action_row, text=self.t("start_focus"), height=46,
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=16),
            fg_color=self.theme.accent, hover_color=self.theme.accent_hover,
            command=self.start_immersive_timer,
        )
        self.start_btn.pack(side="left", fill="x", expand=True)

        self.wave_frame = ctk.CTkFrame(self, fg_color=self.theme.bg)
        self.canvas = tk.Canvas(self.wave_frame, bg=self.theme.bg, highlightthickness=0)

        self.status_text = ctk.CTkLabel(
            self.wave_frame, text="", font=ctk.CTkFont(family=FONT_UI_BOLD, size=22),
            text_color="#d7e4ec", fg_color="transparent",
        )
        self.time_text = ctk.CTkLabel(
            self.wave_frame, text="", font=ctk.CTkFont(family=FONT_UI_BOLD, size=88),
            text_color="#eef5f8", fg_color="transparent",
        )
        self.hint_text = ctk.CTkLabel(
            self.wave_frame, text=self.t("hint_keys"),
            font=ctk.CTkFont(family=FONT_UI, size=12),
            text_color="#9eb0bc", fg_color="transparent",
        )
        self.music_live = ctk.CTkLabel(
            self.wave_frame, text="", font=ctk.CTkFont(family=FONT_UI, size=13),
            text_color="#c5d4de", fg_color="transparent",
        )
        self.track_badge = ctk.CTkLabel(
            self.wave_frame, text="", font=ctk.CTkFont(family=FONT_UI, size=11),
            text_color="#8fa3b0", fg_color="transparent",
        )
        self.intention_live = ctk.CTkLabel(
            self.wave_frame, text="", font=ctk.CTkFont(family=FONT_UI, size=12),
            text_color="#a8c0ce", fg_color="transparent",
        )
        self.break_tip_live = ctk.CTkLabel(
            self.wave_frame, text="", font=ctk.CTkFont(family=FONT_UI, size=12),
            text_color="#9eb8a8", fg_color="transparent", wraplength=480, justify="center",
        )

        self.ctrl_bar = ctk.CTkFrame(
            self.wave_frame, fg_color=self.theme.sidebar, corner_radius=22, height=56,
            border_width=1, border_color=self.theme.glow,
        )
        self.pause_btn = ctk.CTkButton(
            self.ctrl_bar, text=self.t("pause"), width=100, height=36,
            font=ctk.CTkFont(size=13),
            fg_color=self.theme.glow, hover_color=self.theme.accent,
            text_color=self.theme.text,
            command=self.toggle_pause,
        )
        self.pause_btn.pack(side="left", padx=(16, 8), pady=10)
        self.stop_btn = ctk.CTkButton(
            self.ctrl_bar, text=self.t("exit"), width=100, height=36,
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color=self.theme.glow,
            border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text,
            command=self.stop_timer,
        )
        self.stop_btn.pack(side="left", padx=8, pady=10)

        self.immersive_vol = ctk.CTkSlider(
            self.ctrl_bar, from_=0, to=1, width=120, number_of_steps=20,
            command=self._on_volume,
            progress_color=self.theme.accent, button_color=self.theme.text,
            fg_color=self.theme.glow,
        )
        self.immersive_vol.set(0.55)
        self.immersive_vol.pack(side="left", padx=12, pady=10)

        self.menu_btn = ctk.CTkButton(
            self.wave_frame, text="☰", width=44, height=44,
            font=ctk.CTkFont(size=20),
            fg_color=self.theme.sidebar, hover_color=self.theme.glow,
            border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, corner_radius=12,
            command=self.toggle_focus_menu,
        )

        self.menu_panel = ctk.CTkFrame(
            self.wave_frame, width=320, fg_color=self.theme.sidebar,
            corner_radius=16, border_width=1, border_color=self.theme.glow,
        )
        self.menu_panel.pack_propagate(False)
        self._build_focus_menu(self.menu_panel)

        self.canvas.bind("<Motion>", self._reveal_chrome)
        self.wave_frame.bind("<Motion>", self._reveal_chrome)


    def _polish_full_dashboard(self):
        """Light visual cleanup for the feature-complete dashboard.

        This deliberately avoids a 'minimal redesign': controls stay visible,
        while spacing, borders, hierarchy and proportions become calmer.
        """
        try:
            self.sidebar.configure(
                width=244,
                corner_radius=16,
                border_width=1,
                border_color=self.theme.glow,
            )
        except Exception:
            pass
        try:
            self.setup_frame.pack_configure(padx=(14, 12), pady=12)
        except Exception:
            pass
        try:
            self.hero_label.configure(
                font=ctk.CTkFont(family=FONT_UI_BOLD, size=32)
            )
            self.hero_label.pack_configure(pady=(18, 4))
            self.hero_sub.configure(
                font=ctk.CTkFont(family=FONT_UI, size=13),
                wraplength=820,
            )
            self.hero_sub.pack_configure(pady=(0, 10))
        except Exception:
            pass
        try:
            self.ocean_hero.configure(height=122)
            self.ocean_hero.pack_configure(pady=(0, 10))
        except Exception:
            pass

        # One shared visual language for the main cards.  Keep all information
        # and actions; only reduce the older 'stack of unrelated boxes' feel.
        for panel in (
            getattr(self, "mode_launcher", None),
            getattr(self, "intention_panel", None),
            getattr(self, "rhythm_panel", None),
            getattr(self, "inputs_row", None),
            getattr(self, "music_panel", None),
        ):
            if panel is None:
                continue
            try:
                panel.configure(
                    corner_radius=14,
                    border_width=1,
                    border_color=self.theme.glow,
                )
            except Exception:
                pass

        # Quick modes remain prominent, but no longer dominate the whole page.
        for btn in getattr(self, "v2_mode_buttons", []):
            try:
                btn.configure(
                    height=50,
                    corner_radius=12,
                    font=ctk.CTkFont(family=FONT_UI_BOLD, size=11),
                )
            except Exception:
                pass

        # Inputs and primary actions should feel modern without oversized chrome.
        for entry in (
            getattr(self, "entry_intention", None),
            getattr(self, "entry_music", None),
            getattr(self, "entry_work", None),
            getattr(self, "entry_break", None),
            getattr(self, "entry_cycles", None),
            getattr(self, "entry_long_break", None),
            getattr(self, "entry_long_every", None),
        ):
            if entry is None:
                continue
            try:
                entry.configure(corner_radius=10, border_width=1)
            except Exception:
                pass
        try:
            self.preload_btn.configure(height=42, corner_radius=12)
            self.start_btn.configure(height=46, corner_radius=12)
        except Exception:
            pass

    def _curate_dashboard(self):
        """Keep the high-value parts visible and remove low-value visual noise.

        Aqua Focus should be simple, not empty.  The default surface keeps the
        animated atmosphere, focus choices, intention, timing, music selection
        and the primary action.  Explanatory / duplicate material is hidden.
        """
        # Keep OceanHero: motion/atmosphere is part of the product identity.
        try:
            self.ocean_hero.configure(height=132)
            self.ocean_hero.pack_configure(pady=(0, 12))
        except Exception:
            pass

        # These science cards explain decisions but do not help start a session.
        # They remain constructed for compatibility/localization, just not shown
        # on the default dashboard.
        for widget in (
            getattr(self, "science_row", None),
            getattr(self, "science_note", None),
        ):
            if widget is not None:
                try:
                    widget.pack_forget()
                except Exception:
                    pass

        # Keep Quick Dive visible: mode choice is a frequent, meaningful action.
        try:
            self.mode_launcher.pack_configure(pady=(0, 12))
        except Exception:
            pass

        # Keep intention + rhythm + raw timing values.  Custom timing is useful
        # enough that it should not require opening a secondary window.
        for widget in (
            getattr(self, "intention_panel", None),
            getattr(self, "rhythm_panel", None),
            getattr(self, "inputs_row", None),
        ):
            if widget is not None:
                try:
                    widget.pack_configure(pady=(0, 10))
                except Exception:
                    pass

        # Music is a first-class feature, not an advanced setting.  Preserve URL
        # entry, playlist add, volume, now-playing preview and status.
        try:
            self.music_panel.pack_configure(pady=(2, 12))
            self.music_title_lbl.configure(text=self.t("focus_music"))
            self.music_hint_lbl.configure(wraplength=720)
            self.add_playlist_btn.pack_configure()
            self.playlist_count_label.pack_configure()
            self.music_status_label.pack_configure()
            self.now_preview.pack_configure()
        except Exception:
            pass

        # The main action remains obvious, but preload is secondary and can be
        # visually quieter without being removed.
        try:
            self.preload_btn.configure(
                height=42,
                width=122,
                fg_color="transparent",
                border_width=1,
                border_color=self.theme.glow,
            )
            self.start_btn.configure(
                height=48,
                corner_radius=13,
                font=ctk.CTkFont(family=FONT_UI_BOLD, size=16),
            )
        except Exception:
            pass

        # Reduce sidebar noise without deleting functionality.  Detailed updater
        # status/hints are hidden; the actual controls stay available.
        for widget in (
            getattr(self, "sidebar_science", None),
            getattr(self, "temptation_hint", None),
            getattr(self, "agiu_status_lbl", None),
            getattr(self, "bg_label", None),
        ):
            if widget is not None:
                try:
                    widget.pack_forget()
                except Exception:
                    pass

    def _install_dashboard_responsive(self):
        """Keep the feature-complete dashboard usable from compact to ultrawide."""
        try:
            self.minsize(500, 500)
        except Exception:
            pass
        try:
            self.bind("<Configure>", self._on_dashboard_resize, add="+")
            self.after(60, self._apply_dashboard_layout)
        except Exception:
            pass

    def _on_dashboard_resize(self, event=None):
        # Ignore child configure storms; only the root window controls the mode.
        if event is not None and getattr(event, "widget", None) is not self:
            return
        try:
            if self._dashboard_resize_job is not None:
                self.after_cancel(self._dashboard_resize_job)
        except Exception:
            pass
        try:
            self._dashboard_resize_job = self.after(70, self._apply_dashboard_layout)
        except Exception:
            self._dashboard_resize_job = None

    def _apply_dashboard_layout(self):
        """Responsive disclosure without deleting or recreating functional widgets."""
        try:
            width = max(1, int(self.winfo_width()))
            height = max(1, int(self.winfo_height()))
        except Exception:
            return

        compact = width < 860
        very_compact = width < 680
        wide = width >= 1320
        ultrawide = width >= 1780
        short = height < 650

        # Sidebar is preserved in memory and simply disclosed through ••• on
        # compact windows. Never destroy it: several legacy feature surfaces are
        # intentionally backed by these widgets.
        try:
            if compact:
                if self.sidebar.winfo_ismapped():
                    self.sidebar.pack_forget()
            else:
                # Reassert visibility on every non-compact layout. This also
                # repairs states left behind by the old minimal/advanced shell.
                if not self.sidebar.winfo_ismapped():
                    self.sidebar.pack(side="left", fill="y", padx=(12, 0), pady=12)
        except Exception:
            pass
        self._dashboard_compact = compact

        try:
            side_gap = 8 if very_compact else (12 if compact else 16)
            outer_right = 8 if very_compact else 12
            self.setup_frame.pack_configure(padx=(side_gap, outer_right), pady=8 if short else 12)
            # Give large displays a real workspace instead of a phone-width
            # column floating in the middle of an ultrawide monitor.
            target_width = width - (300 if not compact else 24)
            self.setup_frame.configure(width=max(460, min(1180, target_width)))
        except Exception:
            pass

        try:
            self.hero_label.configure(
                font=ctk.CTkFont(
                    family=FONT_UI_BOLD,
                    size=25 if very_compact else (29 if compact else (34 if wide else 32)),
                )
            )
            self.hero_label.pack_configure(pady=(10 if short else 18, 4))
            self.hero_sub.configure(
                font=ctk.CTkFont(family=FONT_UI, size=11 if very_compact else 12),
                wraplength=max(300, min(900, width - (80 if compact else 340))),
            )
        except Exception:
            pass

        # Do not let ultrawide monitors turn every card into a giant strip.
        # Larger screens receive breathing room instead of larger cognitive load.
        card_pad = 2 if very_compact else (6 if compact else (12 if ultrawide else (8 if wide else 0)))
        for panel in (
            getattr(self, "ocean_hero", None),
            getattr(self, "mode_launcher", None),
            getattr(self, "intention_panel", None),
            getattr(self, "rhythm_panel", None),
            getattr(self, "inputs_row", None),
            getattr(self, "music_panel", None),
        ):
            if panel is None:
                continue
            try:
                panel.pack_configure(padx=card_pad)
            except Exception:
                pass

        try:
            self.ocean_hero.configure(height=104 if short else (116 if compact else 132))
        except Exception:
            pass

        mode_buttons = list(getattr(self, "v2_mode_buttons", []))
        for i, btn in enumerate(mode_buttons):
            try:
                # Narrow windows reflow Quick Dive into one column instead of
                # squeezing labels/buttons until they clip.
                if very_compact:
                    btn.grid_configure(row=i, column=0, columnspan=2, sticky="ew", padx=5, pady=4)
                else:
                    btn.grid_configure(row=i // 2, column=i % 2, columnspan=1, sticky="ew", padx=5, pady=5)
                btn.configure(height=44 if very_compact else (48 if compact else 50))
            except Exception:
                pass

        try:
            self.now_preview.configure(width=max(240, min(360, width - (110 if compact else 390))))
        except Exception:
            pass

        # Timing controls are feature-complete, but should not become a cramped
        # five-field spreadsheet on small windows. Reflow the existing widgets;
        # never recreate them, so callbacks/state remain stable.
        try:
            primary_boxes = [
                self.entry_work.master,
                self.entry_break.master,
                self.entry_cycles.master,
            ]
            primary_grid = primary_boxes[0].master
            for col in range(3):
                primary_grid.grid_columnconfigure(col, weight=0 if very_compact else 1)
            primary_grid.grid_columnconfigure(0, weight=1)
            for i, box in enumerate(primary_boxes):
                if very_compact:
                    box.grid_configure(row=i, column=0, padx=0, pady=(0, 8), sticky="ew")
                else:
                    box.grid_configure(row=0, column=i, padx=8, pady=0, sticky="ew")

            secondary_boxes = [
                self.entry_long_break.master,
                self.entry_long_every.master,
            ]
            secondary_grid = secondary_boxes[0].master
            for col in range(2):
                secondary_grid.grid_columnconfigure(col, weight=0 if very_compact else 1)
            secondary_grid.grid_columnconfigure(0, weight=1)
            for i, box in enumerate(secondary_boxes):
                if very_compact:
                    box.grid_configure(row=i, column=0, padx=0, pady=(0, 8), sticky="ew")
                else:
                    box.grid_configure(row=0, column=i, padx=8, pady=0, sticky="ew")
            if very_compact:
                self.long_note_lbl.grid_configure(row=2, column=0, columnspan=1, sticky="w", pady=(2, 0))
            else:
                self.long_note_lbl.grid_configure(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        except Exception:
            pass

        try:
            self.dashboard_more_btn.configure(width=42 if compact else 44, height=34)
            for quick in (getattr(self, "dashboard_tasks_btn", None), getattr(self, "dashboard_stats_btn", None)):
                if quick is not None:
                    quick.configure(width=70 if very_compact else 78, height=34)
        except Exception:
            pass

        self._dashboard_resize_job = None

    def _compact_input(self, parent, label_key: str, default: str, col: int) -> ctk.CTkEntry:
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.grid(row=0, column=col, padx=8, sticky="ew")
        lab = ctk.CTkLabel(box, text=self.t(label_key), font=ctk.CTkFont(size=12), text_color=self.theme.muted)
        lab.pack(anchor="w")
        if not hasattr(self, "_input_label_refs"):
            self._input_label_refs = []
        self._input_label_refs.append((lab, label_key))
        entry = ctk.CTkEntry(box, height=40, justify="center", font=ctk.CTkFont(size=16))
        entry.insert(0, default)
        entry.pack(fill="x", pady=(4, 0))
        return entry

    def _rhythm_color(self, kind: str) -> str:
        if kind == "work":
            return self.theme.accent
        if kind == "short":
            return self.theme.wave_front_break
        return "#e8b86d"  # long break — restorative gold

    def _draw_rhythm_strip(
        self,
        canvas: tk.Canvas,
        work: float,
        short_b: float,
        long_b: float,
        every: int,
        width_hint: int | None = None,
        bg: str | None = None,
    ):
        every = max(1, int(every))
        work, short_b, long_b = max(0.1, float(work)), max(0.1, float(short_b)), max(0.1, float(long_b))
        try:
            canvas.update_idletasks()
        except Exception:
            pass
        w = max(int(width_hint or canvas.winfo_width() or 160), 80)
        h = int(canvas.cget("height") or 28)
        fill_bg = bg or canvas.cget("bg")
        canvas.delete("all")
        canvas.create_rectangle(0, 0, w, h, fill=fill_bg, outline="")

        segs: list[tuple[str, float]] = []
        for i in range(every):
            segs.append(("work", work))
            segs.append(("long" if i == every - 1 else "short", long_b if i == every - 1 else short_b))
        total = sum(m for _, m in segs) or 1.0
        gap = 2
        usable = w - 10 - gap * (len(segs) - 1)
        x = 5
        y0, y1 = 7, h - 7
        for kind, mins in segs:
            bw = max(4.0, usable * (mins / total))
            canvas.create_rectangle(x, y0, x + bw, y1, fill=self._rhythm_color(kind), outline="")
            x += bw + gap

    def _refresh_rhythm_preview(self):
        if not hasattr(self, "rhythm_canvas"):
            return
        try:
            w = float(self._read_entry_view("entry_work", max(1.0, getattr(self, "work_time", 1500) / 60.0)) or 25)
            b = float(self._read_entry_view("entry_break", max(0.0, getattr(self, "break_time", 300) / 60.0)) or 5)
            lb = float(self._read_entry_view("entry_long_break", max(0.0, getattr(self, "long_break_time", 900) / 60.0)) or 15)
            every = max(1, int(float(self._read_entry_view("entry_long_every", getattr(self, "long_break_every", 4)) or 4)))
        except (TypeError, ValueError):
            return
        try:
            self.rhythm_canvas.update_idletasks()
            width = max(self.rhythm_canvas.winfo_width(), 200)
        except Exception:
            width = 200
        self._draw_rhythm_strip(
            self.rhythm_canvas, w, b, lb, every,
            width_hint=width, bg=self.theme.sidebar,
        )
        for mini, pw, pb, plb, pe in getattr(self, "_preset_canvases", []):
            self._draw_rhythm_strip(mini, pw, pb, plb, pe, width_hint=170, bg=self.theme.bg)

    def _highlight_preset(self, key: str):
        self._selected_preset_key = key
        for item in self.preset_btns:
            if not isinstance(item, tuple) or len(item) < 3:
                continue
            btn, card, pkey = item
            selected = pkey == key
            if card is not None:
                card.configure(
                    border_color=self.theme.accent if selected else self.theme.glow,
                    border_width=2 if selected else 1,
                )
            btn.configure(text_color=self.theme.accent if selected else self.theme.text)

    def _build_focus_menu(self, panel: ctk.CTkFrame):
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 6))
        self.menu_title_lbl = ctk.CTkLabel(
            head, text=self.t("menu"), font=ctk.CTkFont(family=FONT_UI_BOLD, size=16),
            text_color=self.theme.text,
        )
        self.menu_title_lbl.pack(side="left")
        ctk.CTkButton(
            head, text="✕", width=32, height=28,
            fg_color="transparent", hover_color=self.theme.glow,
            text_color=self.theme.muted, command=self.close_focus_menu,
        ).pack(side="right")

        ctk.CTkLabel(
            panel, text="PLAYLIST", font=ctk.CTkFont(size=11),
            text_color=self.theme.muted,
        ).pack(anchor="w", padx=16, pady=(8, 4))

        self.playlist_box = ctk.CTkScrollableFrame(
            panel, height=180, fg_color=self.theme.bg, corner_radius=10,
        )
        self.playlist_box.pack(fill="x", padx=12, pady=(0, 8))

        add_frame = ctk.CTkFrame(panel, fg_color="transparent")
        add_frame.pack(fill="x", padx=12, pady=4)
        self.menu_url_entry = ctk.CTkEntry(
            add_frame, height=34, placeholder_text=self.t("url_add_ph"),
            font=ctk.CTkFont(size=12),
        )
        self.menu_url_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(
            add_frame, text="+", width=36, height=34,
            fg_color=self.theme.accent, hover_color=self.theme.accent_hover,
            command=self.menu_add_track,
        ).pack(side="right")

        nav = ctk.CTkFrame(panel, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=8)
        self.menu_prev_btn = ctk.CTkButton(
            nav, text=self.t("prev_track"), width=90, height=34,
            fg_color="transparent", border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, hover_color=self.theme.glow,
            command=self.playlist_prev_track,
        )
        self.menu_prev_btn.pack(side="left", padx=(0, 6))
        self.menu_next_btn = ctk.CTkButton(
            nav, text=self.t("next_track"), width=90, height=34,
            fg_color="transparent", border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, hover_color=self.theme.glow,
            command=self.playlist_next_track,
        )
        self.menu_next_btn.pack(side="left")

        self.continuous_var = ctk.BooleanVar(value=self.playlist.continuous)
        self.continuous_sw = ctk.CTkSwitch(
            panel, text=self.t("continuous"), variable=self.continuous_var,
            command=self._toggle_continuous,
            progress_color=self.theme.accent,
            text_color=self.theme.text,
        )
        self.continuous_sw.pack(anchor="w", padx=16, pady=(4, 2))

        self.calm_var = ctk.BooleanVar(value=self._calm_focus)
        self.calm_sw = ctk.CTkSwitch(
            panel, text=self.t("calm_focus"), variable=self.calm_var,
            command=self._toggle_calm,
            progress_color=self.theme.accent,
            text_color=self.theme.text,
        )
        self.calm_sw.pack(anchor="w", padx=16, pady=(2, 8))

        self.menu_learning_lbl = ctk.CTkLabel(
            panel, text=self.t("learning_science"), font=ctk.CTkFont(size=11),
            text_color=self.theme.muted,
        )
        self.menu_learning_lbl.pack(anchor="w", padx=16, pady=(8, 4))
        self.menu_learning_blurb = ctk.CTkLabel(
            panel,
            text=self.t("learning_blurb"),
            font=ctk.CTkFont(size=10), text_color=self.theme.muted,
            wraplength=280, justify="left",
        )
        self.menu_learning_blurb.pack(anchor="w", padx=16, pady=(0, 6))

        self.menu_session_lbl = ctk.CTkLabel(
            panel, text=self.t("session"), font=ctk.CTkFont(size=11),
            text_color=self.theme.muted,
        )
        self.menu_session_lbl.pack(anchor="w", padx=16, pady=(4, 4))

        sess = ctk.CTkFrame(panel, fg_color="transparent")
        sess.pack(fill="x", padx=12, pady=4)
        ctk.CTkButton(
            sess, text=self.t("pause_resume"), height=34,
            fg_color=self.theme.glow, hover_color=self.theme.accent,
            text_color=self.theme.text, command=self.toggle_pause,
        ).pack(fill="x", pady=3)
        self.menu_skip_btn = ctk.CTkButton(
            sess, text=self.t("skip_track"), height=34,
            fg_color="transparent", border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, hover_color=self.theme.glow,
            command=self.playlist_next_track,
        )
        self.menu_skip_btn.pack(fill="x", pady=3)
        self.menu_exclude_btn = ctk.CTkButton(
            sess, text=self.t("temptation_exclude_btn"), height=34,
            fg_color="transparent", border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, hover_color=self.theme.glow,
            command=self.open_temptation_exclude_dialog,
        )
        self.menu_exclude_btn.pack(fill="x", pady=3)
        self.menu_exit_btn = ctk.CTkButton(
            sess, text=self.t("exit_focus"), height=34,
            fg_color="transparent", border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, hover_color=self.theme.glow,
            command=self.stop_timer,
        )
        self.menu_exit_btn.pack(fill="x", pady=3)

        self.menu_status = ctk.CTkLabel(
            panel, text="", font=ctk.CTkFont(size=11),
            text_color=self.theme.muted, wraplength=280, justify="left",
        )
        self.menu_status.pack(anchor="w", padx=16, pady=(10, 14))

    def apply_theme(self, name: str, animate: bool = True):
        theme = THEMES.get(name, THEMES["Ocean Depth"])
        self.theme = theme
        self.configure(fg_color=theme.bg)
        self.sidebar.configure(fg_color=theme.sidebar)
        self.inputs_row.configure(fg_color=theme.sidebar)
        self.music_panel.configure(fg_color=theme.sidebar)
        self.intention_panel.configure(fg_color=theme.sidebar)
        self.rhythm_panel.configure(fg_color=theme.sidebar)
        self.rhythm_canvas.configure(bg=theme.sidebar)
        self.intention_badge.configure(fg_color=theme.accent)
        self.hero_label.configure(text_color=theme.text)
        self.hero_sub.configure(text_color=theme.muted)
        self.science_note.configure(text_color=theme.muted)
        for card, sw in getattr(self, "_science_pillar_cards", []):
            card.configure(fg_color=theme.sidebar, border_color=theme.glow)
        if getattr(self, "_science_pillar_cards", None) and len(self._science_pillar_cards) >= 4:
            self._science_pillar_cards[0][1].configure(fg_color=theme.accent)
            self._science_pillar_cards[1][1].configure(fg_color="#e8b86d")
            self._science_pillar_cards[2][1].configure(fg_color=theme.wave_front_break)
            self._science_pillar_cards[3][1].configure(fg_color=theme.glow)
        for sw, key in getattr(self, "_rhythm_legend_swatches", []):
            sw.configure(fg_color=self._rhythm_color(key))
        self.entry_intention.configure(border_color=theme.glow)
        self.start_btn.configure(fg_color=theme.accent, hover_color=theme.accent_hover)
        self.preload_btn.configure(border_color=theme.accent, hover_color=theme.glow, text_color=theme.text)
        self.theme_menu.configure(
            fg_color=theme.glow, button_color=theme.accent,
            button_hover_color=theme.accent_hover, dropdown_fg_color=theme.sidebar,
        )
        if hasattr(self, "lang_menu"):
            self.lang_menu.configure(
                fg_color=theme.glow, button_color=theme.accent,
                button_hover_color=theme.accent_hover, dropdown_fg_color=theme.sidebar,
            )
        if hasattr(self, "audio_device_menu"):
            self.audio_device_menu.configure(
                fg_color=theme.glow, button_color=theme.accent,
                button_hover_color=theme.accent_hover, dropdown_fg_color=theme.sidebar,
            )
        if hasattr(self, "audio_refresh_btn"):
            self.audio_refresh_btn.configure(border_color=theme.glow, hover_color=theme.glow, text_color=theme.text)
        if hasattr(self, "agiu_check_btn"):
            self.agiu_check_btn.configure(border_color=theme.glow, hover_color=theme.glow, text_color=theme.text)
        if hasattr(self, "agiu_auto_sw"):
            self.agiu_auto_sw.configure(progress_color=theme.accent, text_color=theme.text)
        self.volume_slider.configure(
            progress_color=theme.accent, button_color=theme.accent,
            button_hover_color=theme.accent_hover,
        )
        self.entry_music.configure(border_color=theme.glow)
        for item in self.preset_btns:
            if isinstance(item, tuple):
                btn, card, pname = item[0], item[1], item[2] if len(item) > 2 else ""
                btn.configure(hover_color=theme.glow, text_color=theme.text)
                if card is not None:
                    card.configure(fg_color=theme.bg, border_color=theme.glow)
                if pname == getattr(self, "_selected_preset_key", ""):
                    self._highlight_preset(pname)
            else:
                item.configure(border_color=theme.glow, hover_color=theme.glow, text_color=theme.text)
        for mini, *_rest in getattr(self, "_preset_canvases", []):
            mini.configure(bg=theme.bg)
        self._refresh_rhythm_preview()
        self.bg_pick_btn.configure(border_color=theme.glow, hover_color=theme.glow, text_color=theme.text)
        self.bg_theme_btn.configure(border_color=theme.glow, hover_color=theme.glow, text_color=theme.text)
        self.bg_label.configure(text_color=theme.muted)
        if hasattr(self, "temptation_hint"):
            self.temptation_hint.configure(text_color=theme.muted)
        if hasattr(self, "temptation_exclude_btn"):
            self.temptation_exclude_btn.configure(
                border_color=theme.glow, hover_color=theme.glow, text_color=theme.text,
            )
        if hasattr(self, "temptation_exclude_label"):
            self.temptation_exclude_label.configure(text_color=theme.muted)
        self._refresh_temptation_btn()
        self.now_preview.configure(bg=theme.sidebar)
        self.wave_frame.configure(fg_color=theme.bg)
        self.canvas.configure(bg=theme.bg)
        self.ctrl_bar.configure(fg_color=theme.sidebar, border_color=theme.glow)
        self.pause_btn.configure(fg_color=theme.glow, hover_color=theme.accent, text_color=theme.text)
        self.stop_btn.configure(
            hover_color=theme.glow, border_color=theme.glow, text_color=theme.text,
        )
        self.immersive_vol.configure(
            progress_color=theme.accent, button_color=theme.text, fg_color=theme.glow,
        )
        self.menu_btn.configure(
            fg_color=theme.sidebar, hover_color=theme.glow,
            border_color=theme.glow, text_color=theme.text,
        )
        self.menu_panel.configure(fg_color=theme.sidebar, border_color=theme.glow)
        try:
            self.add_playlist_btn.configure(
                border_color=theme.glow, hover_color=theme.glow, text_color=theme.text,
            )
            self.playlist_count_label.configure(text_color=theme.muted)
        except Exception:
            pass
        if self._custom_bg_path is None:
            self.load_theme_background(name)
        if animate:
            self._pulse_widget(self.start_btn)
        if getattr(self, "minimal_shell", None) is not None and getattr(self.minimal_shell, "surface", None) is not None:
            self.minimal_shell.refresh_theme()

    def load_theme_background(self, theme_name: str):
        fname = THEME_BG_FILES.get(theme_name, "ocean_depth.jpg")
        path = ASSETS_BG_DIR / fname
        self._set_background_image(str(path) if path.exists() else None, label=f"Theme · {theme_name}")

    def pick_background(self):
        path = filedialog.askopenfilename(
            title=self.t("pick_bg"),
            filetypes=[
                ("Images", "*.jpg;*.jpeg;*.png;*.webp;*.bmp"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return
        self._custom_bg_path = path
        self._set_background_image(path, label=Path(path).name)

    def reset_background(self):
        self._custom_bg_path = None
        self.load_theme_background(self.theme.name)

    def _set_background_image(self, path: str | None, label: str = ""):
        self._bg_photo = None
        self._bg_cache_size = None
        self._bg_src = None
        if path and Image is not None and Path(path).exists():
            try:
                self._bg_src = Image.open(path).convert("RGB")
                self.bg_label.configure(text=label or Path(path).name)
            except Exception as exc:
                self.bg_label.configure(text=f"読込失敗: {exc}")
                self._bg_src = None
        else:
            self.bg_label.configure(text=label or "No image")

    def _get_bg_photo(self, w: int, h: int):
        if self._bg_src is None or ImageTk is None:
            return None
        if self._bg_photo is not None and self._bg_cache_size == (w, h):
            return self._bg_photo
        img = self._bg_src
        scale = max(w / img.width, h / img.height)
        nw, nh = max(1, int(img.width * scale)), max(1, int(img.height * scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        left, top = (nw - w) // 2, (nh - h) // 2
        cropped = resized.crop((left, top, left + w, top + h))
        dark = Image.new("RGB", (w, h), (10, 16, 22))
        blended = Image.blend(cropped, dark, 0.30)
        self._bg_photo = ImageTk.PhotoImage(blended)
        self._bg_cache_size = (w, h)
        return self._bg_photo

    def _pulse_widget(self, widget, steps: int = 8):
        original = widget.cget("fg_color")
        accent = self.theme.accent

        def step(i=0):
            if i >= steps:
                widget.configure(fg_color=original)
                return
            widget.configure(fg_color=accent if i % 2 == 0 else original)
            self.after(60, lambda: step(i + 1))

        step()

    def _on_music_status(self, msg: str):
        self._music_status = msg
        try:
            self.music_status_label.configure(text=msg)
            title = self.music.display_title()
            artist = self.music.display_artist()
            badge = self.music.source_badge()
            playing = self.music._is_playing and not self.music._paused
            live = f"{'♪ ' if playing else ''}{title}"
            self.music_live.configure(text=live)
            sub = f"{badge}  ·  {artist}" if artist else badge
            if msg and msg not in (title, live):
                sub = f"{sub}  ·  {msg}" if len(msg) < 40 else sub
            self.track_badge.configure(text=sub)
        except Exception:
            pass

    def _get_cover_tk(self, size: int, accent: str):
        if self.music.cover_image is None or ImageTk is None:
            return None
        key = (size, accent, self._cover_token)
        cache_key = (size, self._cover_token)
        hit = self._cover_tk_cache.get(cache_key)
        if hit is not None:
            return hit
        circled = self.music.make_circular_cover(size, ring_color=accent)
        if circled is None:
            return None
        photo = ImageTk.PhotoImage(circled)
        self._cover_tk_cache[cache_key] = photo
        return photo

    def _on_volume(self, value):
        v = float(value)
        self.music.set_volume(v)
        try:
            self.volume_slider.set(v)
            self.immersive_vol.set(v)
        except Exception:
            pass

    def _refresh_playlist_ui(self):
        n = len(self.playlist.tracks)
        try:
            self.playlist_count_label.configure(text=self.t("tracks_n", n=n))
        except Exception:
            pass
        box = getattr(self, "playlist_box", None)
        if box is None:
            return
        for child in box.winfo_children():
            child.destroy()
        if not self.playlist.tracks:
            ctk.CTkLabel(
                box, text=self.t("playlist_empty"),
                font=ctk.CTkFont(size=12), text_color=self.theme.muted,
            ).pack(anchor="w", padx=6, pady=8)
            return
        for i, track in enumerate(self.playlist.tracks):
            row = ctk.CTkFrame(box, fg_color="transparent")
            row.pack(fill="x", pady=2)
            active = i == self.playlist.index
            label = track.title or track.url
            if len(label) > 28:
                label = label[:27] + "…"
            prefix = "▶ " if active else f"{i + 1}. "
            ctk.CTkButton(
                row, text=prefix + label, height=30, anchor="w",
                fg_color=self.theme.glow if active else "transparent",
                hover_color=self.theme.glow,
                text_color=self.theme.text,
                font=ctk.CTkFont(size=12),
                command=lambda idx=i: self.playlist_play_index(idx),
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="×", width=28, height=30,
                fg_color="transparent", hover_color="#5a3038",
                text_color=self.theme.muted,
                command=lambda idx=i: self.playlist_remove_index(idx),
            ).pack(side="right")

    def add_current_url_to_playlist(self):
        url = self.entry_music.get().strip()
        if not url:
            self._on_music_status(self.t("url_empty"))
            return
        title = ""
        if self.music.url == url and self.music.meta_title:
            title = self.music.meta_title
        if self.playlist.add(url, title):
            self._on_music_status(self.t("added_playlist_status", title=title or url[:40]))
            self._refresh_playlist_ui()
            try:
                self.menu_status.configure(text=self.t("added"))
            except Exception:
                pass
        else:
            self._on_music_status(self.t("already_in_playlist"))

    def menu_add_track(self):
        url = self.menu_url_entry.get().strip()
        if not url:
            self.menu_status.configure(text=self.t("enter_url"))
            return
        if self.playlist.add(url):
            self.menu_url_entry.delete(0, tk.END)
            self.menu_status.configure(text=self.t("added_playlist"))
            self._refresh_playlist_ui()
            if not self.entry_music.get().strip():
                self.entry_music.insert(0, url)
        else:
            self.menu_status.configure(text=self.t("already_or_invalid"))

    def playlist_remove_index(self, idx: int):
        self.playlist.remove_at(idx)
        self._refresh_playlist_ui()
        self.menu_status.configure(text=self.t("deleted"))

    def playlist_play_index(self, idx: int):
        track = self.playlist.select(idx)
        if not track:
            return
        self._refresh_playlist_ui()
        self._switch_to_track(track, announce=True)

    def playlist_next_track(self):
        track = self.playlist.next()
        if not track:
            self.menu_status.configure(text=self.t("playlist_is_empty"))
            return
        self._refresh_playlist_ui()
        self._switch_to_track(track, announce=True)

    def playlist_prev_track(self):
        track = self.playlist.prev()
        if not track:
            self.menu_status.configure(text=self.t("playlist_is_empty"))
            return
        self._refresh_playlist_ui()
        self._switch_to_track(track, announce=True)

    def _switch_to_track(self, track: PlaylistTrack, announce: bool = False):
        was_playing = self.is_running and not self.is_paused and self.mode == "Work"
        self.entry_music.delete(0, tk.END)
        self.entry_music.insert(0, track.url)
        self.music.set_url(track.url)
        if announce:
            self.menu_status.configure(text=f"切替: {track.title or track.url[:32]}")
            self._on_music_status(f"♪ {track.title or 'Loading…'}")

        def done(ok: bool, msg: str):
            def ui():
                self._cover_tk_cache.clear()
                self._cover_token += 1
                if ok:
                    if track.title in ("", "YouTube track", "Spotify track") and self.music.meta_title:
                        track.title = self.music.meta_title
                        self.playlist.save()
                        self._refresh_playlist_ui()
                    self._on_music_status(f"♪ {self.music.display_title()}")
                    if was_playing or (self.wave_frame.winfo_ismapped() and self.mode == "Work"):
                        self.music.play()
                else:
                    self._on_music_status(f"失敗: {msg}")
                    self.menu_status.configure(text=f"失敗: {msg}")
            self.after(0, ui)

        self.music.prepare_async(done)

    def _on_music_track_ended(self):
        """Advance playlist when a stream finishes (runs on audio thread)."""
        if not self.playlist.continuous or len(self.playlist.tracks) <= 1:
            return
        self.music.streamer._loop = False
        self.playlist.next()
        self.after(0, self._advance_playlist_after_end)

    def _advance_playlist_after_end(self):
        track = self.playlist.current()
        if not track:
            return
        self._refresh_playlist_ui()
        if self.wave_frame.winfo_ismapped() and self.mode == "Work" and self.is_running:
            self._switch_to_track(track, announce=True)

    def _toggle_continuous(self):
        self.playlist.continuous = bool(self.continuous_var.get())
        self.playlist.save()
        self.menu_status.configure(
            text=self.t("continuous_on") if self.playlist.continuous else self.t("continuous_off")
        )

    def _toggle_calm(self):
        self._calm_focus = bool(self.calm_var.get())
        self.menu_status.configure(text="Calm Focus ON" if self._calm_focus else "Calm Focus OFF")
        if not self._calm_focus:
            self._reveal_chrome()

    def toggle_focus_menu(self):
        if self._menu_open:
            self.close_focus_menu()
        else:
            self.open_focus_menu()

    def open_focus_menu(self):
        self._menu_open = True
        self._refresh_playlist_ui()
        self.menu_panel.place(relx=0.985, rely=0.08, anchor="ne", relheight=0.84)
        self.menu_panel.lift()
        self.menu_btn.lift()
        self._reveal_chrome()

    def close_focus_menu(self):
        self._menu_open = False
        try:
            self.menu_panel.place_forget()
        except Exception:
            pass

    def preload_music(self):
        url = self.entry_music.get().strip()
        self.music.set_url(url)
        if not url:
            self._on_music_status("URL が空です")
            return
        kind = MusicController.detect_kind(url)
        if kind == "spotify":
            self._on_music_status("Spotify → アプリ内ストリーム準備中…")
        elif kind == "direct":
            self._on_music_status("ストリーム準備（ダウンロードなし）…")
        else:
            self._on_music_status("YouTube のタイトル / ジャケット取得中…")

        def done(ok: bool, msg: str):
            def ui():
                self._cover_tk_cache.clear()
                self._cover_token += 1
                if ok:
                    self._on_music_status(f"♪ {self.music.display_title()}")
                else:
                    self._on_music_status(f"失敗: {msg}")
            self.after(0, ui)

        self.music.prepare_async(done)

    def _sync_music_for_state(self):
        """Play only during active (non-paused) Work; stop otherwise."""
        should_play = self.is_running and not self.is_paused and self.mode == "Work"
        if should_play:
            if self.music.kind in ("youtube", "direct") and not self.music._ready:
                return
            self.music.play()
        else:
            if self.is_paused and self.mode == "Work":
                self.music.pause()
            else:
                self.music.stop()

    def _refresh_temptation_btn(self):
        if not hasattr(self, "temptation_btn"):
            return
        admin = is_windows_admin()
        enforcing = self._temptation_should_enforce()
        n_films = len(self._temptation_films)
        n_ex = len(self.temptation_exclude.exclusions)
        if self._temptation_armed:
            suffix = self.t("films_n", n=n_films) if enforcing else ""
            self.temptation_btn.configure(
                text=self.t("temptation_on") + suffix,
                fg_color="#1e6b4a", hover_color="#258a5e",
                state="disabled" if enforcing else "normal",
            )
            role = self.t("role_admin") if admin else self.t("role_user")
            if enforcing:
                if IS_WINDOWS:
                    self.temptation_hint.configure(
                        text=self.t("temptation_enforcing_win", role=role, n=n_films)
                    )
                else:
                    self.temptation_hint.configure(text=self.t("temptation_enforcing_unix"))
            else:
                if IS_WINDOWS:
                    self.temptation_hint.configure(text=self.t("temptation_on_win", role=role))
                else:
                    self.temptation_hint.configure(text=self.t("temptation_on_unix"))
        else:
            self.temptation_btn.configure(
                text=self.t("temptation_off"),
                fg_color="#8b3a3a", hover_color="#a84848",
                state="normal",
            )
            if IS_WINDOWS:
                self.temptation_hint.configure(text=self.t("temptation_off_hint_win"))
            else:
                self.temptation_hint.configure(text=self.t("temptation_hint_unix"))
        if hasattr(self, "temptation_exclude_label"):
            if n_ex:
                names = ", ".join(sorted(self.temptation_exclude.exclusions)[:3])
                more = self.t("exclude_more", n=n_ex - 3) if n_ex > 3 else ""
                self.temptation_exclude_label.configure(
                    text=self.t("temptation_exclude_n", n=n_ex, names=names, more=more)
                )
            else:
                self.temptation_exclude_label.configure(text=self.t("temptation_exclude_none"))

    def toggle_temptation_guard(self):
        if self._temptation_armed:
            if self._temptation_should_enforce():
                self.temptation_hint.configure(text=self.t("temptation_work_locked"))
                return
            self._disarm_temptation_guard()
            return
        if IS_WINDOWS and not is_windows_admin():
            ok = relaunch_elevated_with_flag("--temptation-guard")
            if ok:
                try:
                    self.music.stop()
                except Exception:
                    pass
                self.after(200, self.destroy)
                return
            self.temptation_hint.configure(text=self.t("temptation_elev_cancel"))
        self._temptation_armed = True
        self._refresh_temptation_btn()
        self._start_temptation_watch()
        if IS_WINDOWS:
            self.hero_sub.configure(text=self.t("temptation_on_msg_win"))
        else:
            self.hero_sub.configure(text=self.t("temptation_on_msg_unix"))

    def _disarm_temptation_guard(self):
        if self._temptation_should_enforce():
            return
        self._temptation_armed = False
        self._stop_temptation_watch()
        self._clear_all_temptation_films()
        try:
            self.attributes("-topmost", False)
        except Exception:
            pass
        self._refresh_temptation_btn()
        self.hero_sub.configure(text=self.t("temptation_off_msg"))

    def _temptation_should_enforce(self) -> bool:
        try:
            mapped = self.wave_frame.winfo_ismapped()
        except Exception:
            mapped = False
        return (
            self._temptation_armed
            and self.is_running
            and not self.is_paused
            and self.mode == "Work"
            and mapped
        )

    def _start_temptation_watch(self):
        self._stop_temptation_watch()
        self._temptation_tick()

    def _stop_temptation_watch(self):
        if self._temptation_job is not None:
            try:
                self.after_cancel(self._temptation_job)
            except Exception:
                pass
            self._temptation_job = None

    def _temptation_tick(self):
        self._temptation_job = None
        try:
            if self._temptation_should_enforce():
                self._sync_all_temptation_films()
            else:
                self._clear_all_temptation_films()
            self._refresh_temptation_btn()
        except Exception:
            pass
        if self._temptation_armed:
            self._temptation_job = self.after(150, self._temptation_tick)

    def _collect_our_hwnds(self) -> set[int]:
        hwnds: set[int] = set()
        try:
            hwnds.add(self._tk_toplevel_hwnd(self))
        except Exception:
            pass
        for film in self._temptation_films.values():
            win = film.get("win")
            if win is None:
                continue
            try:
                hwnds.add(self._tk_toplevel_hwnd(win))
                if film.get("hwnd"):
                    hwnds.add(int(film["hwnd"]))
            except Exception:
                pass
        return hwnds

    def _tk_toplevel_hwnd(self, widget) -> int:
        """Resolve the real Win32 HWND for a Tk window (not an inner child id)."""
        widget.update_idletasks()
        hwnd = int(widget.winfo_id())
        if not IS_WINDOWS or ctypes is None:
            return hwnd
        user32 = ctypes.windll.user32
        GA_ROOT = 2
        try:
            root = int(user32.GetAncestor(hwnd, GA_ROOT) or 0)
            if root:
                return root
        except Exception:
            pass
        try:
            parent = int(user32.GetParent(hwnd) or 0)
            if parent:
                return parent
        except Exception:
            pass
        return hwnd

    def _hwnd_belongs_to_us(self, hwnd: int) -> bool:
        if not hwnd or ctypes is None:
            return False
        user32 = ctypes.windll.user32
        try:
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
            if int(pid.value) == os.getpid():
                return True
        except Exception:
            pass
        ours = self._collect_our_hwnds()
        cur = int(hwnd)
        for _ in range(16):
            if cur in ours:
                return True
            parent = int(user32.GetParent(cur) or 0)
            if not parent or parent == cur:
                break
            cur = parent
        return False

    def _window_class_name(self, hwnd: int) -> str:
        if ctypes is None:
            return ""
        buf = ctypes.create_unicode_buffer(256)
        ctypes.windll.user32.GetClassNameW(int(hwnd), buf, 256)
        return buf.value or ""

    def _window_title(self, hwnd: int) -> str:
        if ctypes is None:
            return ""
        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.user32.GetWindowTextW(int(hwnd), buf, 512)
        return (buf.value or "").strip()

    def _is_window_cloaked(self, hwnd: int) -> bool:
        if ctypes is None:
            return False
        try:
            cloaked = wintypes.DWORD(0)
            DWMWA_CLOAKED = 14
            if ctypes.windll.dwmapi.DwmGetWindowAttribute(
                int(hwnd), DWMWA_CLOAKED, ctypes.byref(cloaked), ctypes.sizeof(cloaked)
            ) == 0:
                return bool(cloaked.value)
        except Exception:
            pass
        return False

    def _rect_on_virtual_screen(self, x: int, y: int, w: int, h: int) -> bool:
        if ctypes is None:
            return w >= 200 and h >= 150
        user32 = ctypes.windll.user32
        vx = int(user32.GetSystemMetrics(76))
        vy = int(user32.GetSystemMetrics(77))
        vw = int(user32.GetSystemMetrics(78))
        vh = int(user32.GetSystemMetrics(79))
        if vw <= 0 or vh <= 0:
            return w >= 200 and h >= 150
        if x + w <= vx or y + h <= vy or x >= vx + vw or y >= vy + vh:
            return False
        return w >= 200 and h >= 150

    def _is_skippable_system_window(self, hwnd: int) -> bool:
        if ctypes is None:
            return True
        user32 = ctypes.windll.user32
        cls = self._window_class_name(hwnd)
        if cls in _TEMPTATION_SKIP_CLASSES:
            return True
        title = self._window_title(hwnd)
        if not title:
            return True
        low = title.lower()
        if "komorebi" in low:
            return True
        exe = self._process_exe_name(hwnd) if hasattr(self, "_process_exe_name") else ""
        if _is_temptation_helper_exe(exe, title):
            return True
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.IsIconic(hwnd):
            return True
        if self._is_window_cloaked(hwnd):
            return True
        try:
            GWL_EXSTYLE = -20
            WS_EX_TOOLWINDOW = 0x00000080
            style = int(user32.GetWindowLongW(int(hwnd), GWL_EXSTYLE))
            if style & WS_EX_TOOLWINDOW:
                return True
        except Exception:
            pass
        rect = self._get_window_rect(hwnd)
        if rect is None:
            return True
        x, y, w, h = rect
        if not self._rect_on_virtual_screen(x, y, w, h):
            return True
        return False

    def _get_root_hwnd(self, hwnd: int) -> int:
        user32 = ctypes.windll.user32
        GA_ROOT = 2
        try:
            root = int(user32.GetAncestor(int(hwnd), GA_ROOT) or hwnd)
            return root or int(hwnd)
        except Exception:
            return int(hwnd)

    def _get_window_rect(self, hwnd: int) -> tuple[int, int, int, int] | None:
        if ctypes is None:
            return None

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        user32 = ctypes.windll.user32
        rect = RECT()
        try:
            dwmapi = ctypes.windll.dwmapi
            DWMWA_EXTENDED_FRAME_BOUNDS = 9
            if dwmapi.DwmGetWindowAttribute(
                int(hwnd), DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect)
            ) == 0:
                w = int(rect.right - rect.left)
                h = int(rect.bottom - rect.top)
                if w > 0 and h > 0:
                    return int(rect.left), int(rect.top), w, h
        except Exception:
            pass
        if not user32.GetWindowRect(int(hwnd), ctypes.byref(rect)):
            return None
        w = int(rect.right - rect.left)
        h = int(rect.bottom - rect.top)
        if w <= 0 or h <= 0:
            return None
        return int(rect.left), int(rect.top), w, h

    def _enumerate_top_level_hwnds(self) -> list[int]:
        if sys.platform != "win32" or ctypes is None:
            return []
        user32 = ctypes.windll.user32
        found: list[int] = []
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

        @EnumWindowsProc
        def _cb(hwnd, _lparam):
            try:
                hwnd_i = int(hwnd)
                if not hwnd_i or not user32.IsWindow(hwnd_i):
                    return True
                if user32.GetWindow(hwnd_i, 4):  # GW_OWNER
                    return True
                if user32.GetParent(hwnd_i):
                    return True
                found.append(hwnd_i)
            except Exception:
                pass
            return True

        self._enum_windows_cb_ref = _cb  # prevent GC during EnumWindows
        try:
            user32.EnumWindows(_cb, 0)
        except Exception:
            pass
        return found

    def _process_exe_name(self, hwnd: int) -> str:
        """Return lowercase executable file name for the window's process."""
        if ctypes is None or not hwnd:
            return ""
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(int(hwnd), ctypes.byref(pid))
        if not pid.value:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid.value))
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return Path(buf.value).name.lower()
        except Exception:
            pass
        finally:
            try:
                kernel32.CloseHandle(handle)
            except Exception:
                pass
        return ""

    def _list_running_apps_psutil(self) -> list[dict]:
        """macOS / Linux 用の起動プロセス一覧（除外リスト保存用）。"""
        try:
            import psutil
        except ImportError:
            return []
        skip = {
            "ffmpeg", "ffprobe", "python", "python3", "aquafocus",
            "systemd", "init", "kernel", "dockerd",
        }
        by_name: dict[str, dict] = {}
        for proc in psutil.process_iter(["name", "pid"]):
            try:
                name = (proc.info.get("name") or "").strip()
                if not name:
                    continue
                key = name.lower()
                stem = Path(key).stem
                if stem in skip or key in skip:
                    continue
                if key.endswith((".dll", ".so")):
                    continue
                display = name if name.lower().endswith((".exe", ".app")) else name
                exe_key = key if key.endswith(".exe") else f"{stem}"
                if exe_key not in by_name:
                    by_name[exe_key] = {
                        "exe": exe_key,
                        "title": display[:48],
                        "area": 1,
                        "excluded": self.temptation_exclude.is_excluded(exe_key),
                    }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return sorted(by_name.values(), key=lambda a: (not a["excluded"], a["exe"]))

    def _list_running_apps_for_exclude(self) -> list[dict]:
        """Unique running apps (exe + sample title) suitable for exclude picker."""
        if not IS_WINDOWS:
            return self._list_running_apps_psutil()
        by_exe: dict[str, dict] = {}
        for hwnd in self._enumerate_top_level_hwnds():
            root = self._get_root_hwnd(hwnd)
            if self._hwnd_belongs_to_us(root):
                continue
            if ctypes is None:
                continue
            user32 = ctypes.windll.user32
            if not user32.IsWindowVisible(root) or user32.IsIconic(root):
                continue
            if self._is_window_cloaked(root):
                continue
            title = self._window_title(root)
            if not title:
                continue
            exe = self._process_exe_name(root)
            if not exe or exe in ("explorer.exe", "shellexperiencehost.exe", "searchhost.exe"):
                continue
            if _is_temptation_helper_exe(exe, title):
                continue
            rect = self._get_window_rect(root)
            area = (rect[2] * rect[3]) if rect else 0
            prev = by_exe.get(exe)
            if prev is None or area > prev.get("area", 0):
                by_exe[exe] = {
                    "exe": exe,
                    "title": title[:48],
                    "area": area,
                    "excluded": self.temptation_exclude.is_excluded(exe),
                }
        return sorted(by_exe.values(), key=lambda a: (not a["excluded"], a["exe"]))

    def _list_cover_targets(self) -> list[int]:
        """All visible app windows except Aqua Focus and user exclusions."""
        targets: list[int] = []
        seen: set[int] = set()
        for hwnd in self._enumerate_top_level_hwnds():
            root = self._get_root_hwnd(hwnd)
            if root in seen:
                continue
            seen.add(root)
            if self._hwnd_belongs_to_us(root):
                continue
            if self._is_skippable_system_window(root):
                continue
            exe = self._process_exe_name(root)
            if exe and self.temptation_exclude.is_excluded(exe):
                continue
            if _is_temptation_helper_exe(exe, self._window_title(root)):
                continue
            targets.append(root)
        return targets

    def open_temptation_exclude_dialog(self):
        """Pick which running apps should NOT get the temptation film."""
        if self._exclude_dialog is not None:
            try:
                if self._exclude_dialog.winfo_exists():
                    self._exclude_dialog.lift()
                    self._exclude_dialog.focus_force()
                    self._populate_exclude_dialog()
                    return
            except Exception:
                pass

        dlg = ctk.CTkToplevel(self)
        dlg.title(self.t("exclude_dialog_title"))
        dlg.geometry("420x520")
        dlg.minsize(360, 400)
        dlg.configure(fg_color=self.theme.bg)
        dlg.transient(self)
        try:
            dlg.attributes("-topmost", True)
        except Exception:
            pass
        self._exclude_dialog = dlg

        head = ctk.CTkFrame(dlg, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(16, 8))
        ctk.CTkLabel(
            head, text=self.t("exclude_heading"),
            font=ctk.CTkFont(family=FONT_UI_BOLD, size=18),
            text_color=self.theme.text,
        ).pack(anchor="w")
        ctk.CTkLabel(
            head,
            text=self.t("exclude_blurb"),
            font=ctk.CTkFont(size=12), text_color=self.theme.muted,
            wraplength=380, justify="left",
        ).pack(anchor="w", pady=(4, 0))

        tools = ctk.CTkFrame(dlg, fg_color="transparent")
        tools.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkButton(
            tools, text=self.t("rescan"), width=100, height=30,
            fg_color=self.theme.glow, hover_color=self.theme.accent,
            command=self._populate_exclude_dialog,
        ).pack(side="left")
        ctk.CTkButton(
            tools, text=self.t("clear_exclusions"), width=130, height=30,
            fg_color="transparent", border_width=1, border_color=self.theme.glow,
            text_color=self.theme.text, hover_color=self.theme.glow,
            command=self._clear_all_exclusions,
        ).pack(side="left", padx=(8, 0))

        self._exclude_scroll = ctk.CTkScrollableFrame(
            dlg, fg_color=self.theme.sidebar, corner_radius=12,
        )
        self._exclude_scroll.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._exclude_status = ctk.CTkLabel(
            dlg, text="", font=ctk.CTkFont(size=11), text_color=self.theme.muted,
        )
        self._exclude_status.pack(anchor="w", padx=18, pady=(0, 14))

        def _on_close():
            self._exclude_dialog = None
            try:
                dlg.destroy()
            except Exception:
                pass

        dlg.protocol("WM_DELETE_WINDOW", _on_close)
        self._populate_exclude_dialog()
        dlg.after(50, dlg.lift)

    def _clear_all_exclusions(self):
        self.temptation_exclude.exclusions.clear()
        self.temptation_exclude.save()
        self._populate_exclude_dialog()
        self._refresh_temptation_btn()
        if self._temptation_should_enforce():
            self._sync_all_temptation_films()

    def _populate_exclude_dialog(self):
        if not hasattr(self, "_exclude_scroll") or self._exclude_dialog is None:
            return
        try:
            if not self._exclude_dialog.winfo_exists():
                return
        except Exception:
            return
        for child in self._exclude_scroll.winfo_children():
            try:
                child.destroy()
            except Exception:
                pass

        apps = self._list_running_apps_for_exclude()
        running = {a["exe"] for a in apps}
        for exe in sorted(self.temptation_exclude.exclusions):
            if exe not in running:
                apps.append({
                    "exe": exe,
                    "title": "（現在は未起動）",
                    "area": 0,
                    "excluded": True,
                })

        if not apps:
            ctk.CTkLabel(
                self._exclude_scroll,
                text=self.t("no_apps"),
                text_color=self.theme.muted,
            ).pack(pady=20)
            self._exclude_status.configure(text="")
            return

        for app in apps:
            exe = app["exe"]
            row = ctk.CTkFrame(self._exclude_scroll, fg_color=self.theme.bg, corner_radius=10)
            row.pack(fill="x", padx=6, pady=4)
            var = ctk.BooleanVar(value=bool(app["excluded"]))

            def _toggle(ex=exe, v=var):
                self.temptation_exclude.set_excluded(ex, bool(v.get()))
                self._refresh_temptation_btn()
                n = len(self.temptation_exclude.exclusions)
                self._exclude_status.configure(text=self.t("exclude_saved", n=n))
                if self._temptation_should_enforce():
                    self._sync_all_temptation_films()

            sw = ctk.CTkCheckBox(
                row, text="", variable=var, width=28,
                command=_toggle,
                fg_color=self.theme.accent, hover_color=self.theme.accent_hover,
            )
            sw.pack(side="left", padx=(10, 4), pady=10)
            texts = ctk.CTkFrame(row, fg_color="transparent")
            texts.pack(side="left", fill="x", expand=True, padx=(0, 10), pady=8)
            ctk.CTkLabel(
                texts, text=exe,
                font=ctk.CTkFont(family=FONT_UI_BOLD, size=13),
                text_color=self.theme.text, anchor="w",
            ).pack(anchor="w")
            ctk.CTkLabel(
                texts, text=app["title"],
                font=ctk.CTkFont(size=11), text_color=self.theme.muted, anchor="w",
            ).pack(anchor="w")

        n = len(self.temptation_exclude.exclusions)
        self._exclude_status.configure(
            text=self.t("exclude_status", running=len(running), n=n)
        )
        self._refresh_temptation_btn()

    def _sync_all_temptation_films(self):
        if not IS_WINDOWS:
            self._clear_all_temptation_films()
            try:
                if self._temptation_should_enforce():
                    self.lift()
                    self.attributes("-topmost", True)
                else:
                    self.attributes("-topmost", False)
            except Exception:
                pass
            return

        targets = self._list_cover_targets()
        target_set = set(targets)
        for hwnd in list(self._temptation_films.keys()):
            if hwnd not in target_set:
                self._destroy_film(hwnd)

        fg = 0
        if ctypes is not None:
            try:
                fg = int(ctypes.windll.user32.GetForegroundWindow() or 0)
            except Exception:
                fg = 0
        fg_root = self._get_root_hwnd(fg) if fg else 0
        aqua_focused = bool(fg) and self._hwnd_belongs_to_us(fg)

        quotes = self._focus_quotes()
        quote = quotes[self._temptation_quote_idx % len(quotes)]
        for hwnd in targets:
            rect = self._get_window_rect(hwnd)
            if rect is None or not self._rect_on_virtual_screen(*rect):
                self._destroy_film(hwnd)
                continue
            film = self._ensure_film(hwnd, quote, rect)
            if film is None:
                continue
            activate = (not aqua_focused) and (fg_root == hwnd or fg == hwnd)
            ok = self._pin_film(film, hwnd, rect, activate=activate)
            if not ok:
                self._destroy_film(hwnd)

        if self._temptation_quote_job is None and self._temptation_films:
            self._schedule_quote_rotate()

    def _ensure_film(self, target_hwnd: int, quote: str, rect: tuple[int, int, int, int]) -> dict | None:
        existing = self._temptation_films.get(target_hwnd)
        if existing is not None:
            try:
                if existing["win"].winfo_exists():
                    return existing
            except Exception:
                pass
            self._destroy_film(target_hwnd)

        x, y, w, h = rect
        ov = tk.Toplevel(self)
        ov.withdraw()
        ov.overrideredirect(True)
        ov.configure(bg="#0a1520")
        try:
            ov.attributes("-alpha", TEMPTATION_FILM_ALPHA)
        except Exception:
            pass
        try:
            ov.attributes("-topmost", True)
            ov.attributes("-toolwindow", True)  # avoid tiling WMs (e.g. Komorebi)
        except Exception:
            pass
        ov.protocol("WM_DELETE_WINDOW", lambda: None)
        ov.geometry(self._geometry_string(x, y, w, h))

        title = tk.Label(
            ov, text=self.t("film_title"), bg="#0a1520", fg="#8eb8c8",
            font=(FONT_UI_BOLD, 12),
        )
        title.place(relx=0.5, rely=0.38, anchor="center")
        body = tk.Label(
            ov, text=self.t("film_body"), bg="#0a1520", fg="#f0f7fc",
            font=(FONT_UI_BOLD, 18), wraplength=max(200, w - 40), justify="center",
        )
        body.place(relx=0.5, rely=0.50, anchor="center")
        qlab = tk.Label(
            ov, text=quote, bg="#0a1520", fg="#d4b56a",
            font=(FONT_UI, 11), wraplength=max(180, w - 60), justify="center",
        )
        qlab.place(relx=0.5, rely=0.62, anchor="center")
        foot = tk.Label(
            ov, text=self.t("film_footer"), bg="#0a1520", fg="#6a8494",
            font=(FONT_UI, 9),
        )
        foot.place(relx=0.5, rely=0.74, anchor="center")

        for seq in ("<Button>", "<ButtonRelease>", "<Motion>", "<Key>", "<MouseWheel>"):
            ov.bind(seq, lambda _e: "break")

        ov.update_idletasks()
        hwnd_film = self._tk_toplevel_hwnd(ov)
        self._style_film_hwnd(hwnd_film)
        film = {
            "win": ov, "title": title, "body": body, "quote": qlab, "foot": foot,
            "target": target_hwnd, "hwnd": hwnd_film, "placed": False,
        }
        self._temptation_films[target_hwnd] = film
        return film

    @staticmethod
    def _geometry_string(x: int, y: int, w: int, h: int) -> str:
        return f"{max(1, int(w))}x{max(1, int(h))}+{int(x)}+{int(y)}"

    def _style_film_hwnd(self, hwnd: int) -> None:
        """Mark film as tool/layered/topmost so tiling WMs don't park it at (0,0)."""
        if not hwnd or ctypes is None:
            return
        user32 = ctypes.windll.user32
        GWL_EXSTYLE = -20
        WS_EX_TOPMOST = 0x00000008
        WS_EX_TOOLWINDOW = 0x00000080
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_LAYERED = 0x00080000
        try:
            style = int(user32.GetWindowLongW(int(hwnd), GWL_EXSTYLE))
            style |= WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED
            user32.SetWindowLongW(int(hwnd), GWL_EXSTYLE, style)
        except Exception:
            pass

    def _pin_film(
        self,
        film: dict,
        target_hwnd: int,
        rect: tuple[int, int, int, int] | None = None,
        activate: bool = False,
    ) -> bool:
        """Stick translucent film exactly over the target window (any monitor)."""
        ov = film.get("win")
        if ov is None:
            return False
        if rect is None:
            rect = self._get_window_rect(target_hwnd)
        if rect is None or not self._rect_on_virtual_screen(*rect):
            return False
        x, y, w, h = rect
        try:
            wrap = max(160, w - 40)
            film["body"].configure(wraplength=min(560, wrap))
            film["quote"].configure(wraplength=min(520, wrap))
        except Exception:
            pass

        geom = self._geometry_string(x, y, w, h)
        try:
            ov.geometry(geom)
        except Exception:
            pass

        ok = False
        if sys.platform == "win32" and ctypes is not None:
            try:
                user32 = ctypes.windll.user32
                ov.update_idletasks()
                ohwnd = int(film.get("hwnd") or self._tk_toplevel_hwnd(ov))
                film["hwnd"] = ohwnd
                self._style_film_hwnd(ohwnd)
                HWND_TOPMOST = -1
                SWP_SHOWWINDOW = 0x0040
                SWP_NOACTIVATE = 0x0010
                flags = SWP_SHOWWINDOW | (0 if activate else SWP_NOACTIVATE)
                # SWP_ASYNCWINDOWPOS helps against tiling WM races
                flags |= 0x4000
                result = user32.SetWindowPos(
                    ohwnd, HWND_TOPMOST, int(x), int(y), int(w), int(h), flags,
                )
                ok = bool(result)
                if activate:
                    kernel32 = ctypes.windll.kernel32
                    fg = user32.GetForegroundWindow()
                    fg_tid = user32.GetWindowThreadProcessId(fg, None)
                    our_tid = kernel32.GetCurrentThreadId()
                    if fg_tid and our_tid and fg_tid != our_tid:
                        user32.AttachThreadInput(fg_tid, our_tid, True)
                    user32.BringWindowToTop(ohwnd)
                    user32.SetForegroundWindow(ohwnd)
                    if fg_tid and our_tid and fg_tid != our_tid:
                        user32.AttachThreadInput(fg_tid, our_tid, False)
            except Exception:
                ok = False

        try:
            ov.update_idletasks()
            fx, fy = int(ov.winfo_x()), int(ov.winfo_y())
            fw, fh = int(ov.winfo_width()), int(ov.winfo_height())
            if fw >= 180 and fh >= 120:
                ok = True
            elif abs(fx) <= 2 and abs(fy) <= 2 and fw <= 360 and fh <= 240:
                ok = False
        except Exception:
            pass

        if ok:
            try:
                if not film.get("placed"):
                    ov.deiconify()
                    film["placed"] = True
                ov.attributes("-topmost", True)
            except Exception:
                pass
            return True
        return False

    def _destroy_film(self, target_hwnd: int):
        film = self._temptation_films.pop(target_hwnd, None)
        if not film:
            return
        win = film.get("win")
        if win is not None:
            try:
                win.destroy()
            except Exception:
                pass

    def _clear_all_temptation_films(self):
        for hwnd in list(self._temptation_films.keys()):
            self._destroy_film(hwnd)
        if self._temptation_quote_job is not None:
            try:
                self.after_cancel(self._temptation_quote_job)
            except Exception:
                pass
            self._temptation_quote_job = None

    def _schedule_quote_rotate(self):
        if self._temptation_quote_job is not None:
            try:
                self.after_cancel(self._temptation_quote_job)
            except Exception:
                pass
            self._temptation_quote_job = None
        if not self._temptation_films:
            return
        quotes = self._focus_quotes()
        if not quotes:
            return
        self._temptation_quote_idx = (self._temptation_quote_idx + 1) % len(quotes)
        quote = quotes[self._temptation_quote_idx]
        for film in self._temptation_films.values():
            try:
                film["quote"].configure(text=quote)
            except Exception:
                pass
        self._temptation_quote_job = self.after(9000, self._schedule_quote_rotate)

    def _hide_temptation_overlay(self):
        """Back-compat alias used by break / stop paths."""
        self._clear_all_temptation_films()

    def _entry_alive(self, attr: str) -> bool:
        """Return True only while a CTk/Tk entry still owns a live Tcl command."""
        widget = getattr(self, attr, None)
        if widget is None:
            return False
        try:
            return bool(widget.winfo_exists())
        except (tk.TclError, AttributeError, RuntimeError):
            return False

    def _write_entry_view(self, attr: str, value) -> bool:
        """Best-effort UI sync; authoritative timer state must never depend on it."""
        if not self._entry_alive(attr):
            return False
        widget = getattr(self, attr)
        try:
            widget.delete(0, tk.END)
            widget.insert(0, str(value))
            return True
        except (tk.TclError, AttributeError, RuntimeError):
            return False

    def _read_entry_view(self, attr: str, fallback=""):
        """Read a live entry, otherwise return internal-state fallback."""
        if not self._entry_alive(attr):
            return fallback
        try:
            return getattr(self, attr).get()
        except (tk.TclError, AttributeError, RuntimeError):
            return fallback

    def set_preset(self, w, b, name: str = "", long_break: float = 15, long_every: int = 4, cycles: int = 4, blurb: str = "", key: str = ""):
        # Presets update timer state first. Entry widgets are only views and may
        # be temporarily hidden/rebuilt by responsive/theme changes.
        self._write_entry_view("entry_work", w)
        self._write_entry_view("entry_break", b)
        self._write_entry_view("entry_long_break", long_break)
        self._write_entry_view("entry_long_every", long_every)
        self._write_entry_view("entry_cycles", cycles)

        # Keep timer state authoritative even when the legacy entry surface is
        # temporarily unavailable.
        try:
            self.work_time = max(1, float(w)) * 60
            self.break_time = max(0, float(b)) * 60
            self.long_break_time = max(0, float(long_break)) * 60
            self.long_break_every = max(1, int(float(long_every)))
            self.max_cycles = max(1, int(float(cycles)))
        except (TypeError, ValueError):
            pass
        msg = self.t("preset_msg", name=name, blurb=blurb) if blurb else f"Preset: {name}"
        self.hero_sub.configure(text=msg)
        if key:
            self._highlight_preset(key)
        elif name:
            for n, *_rest, k in self._science_presets():
                if n == name:
                    self._highlight_preset(k)
                    break
        self._refresh_rhythm_preview()
        self._pulse_widget(self.start_btn)

    def _toggle_reduce_motion(self):
        self.reduce_motion = bool(self.reduce_motion_sw.get())
        self.settings.set("reduce_motion", self.reduce_motion)
        try:
            self.hero_sub.configure(
                text="Reduced motion enabled" if self.reduce_motion else self.t("hero_sub_default")
            )
        except Exception:
            pass

    def start_deep_dive_mode(self):
        """90-minute low-distraction focus session using the existing immersive player."""
        self._calm_focus = True
        try:
            self.calm_var.set(True)
        except Exception:
            pass
        self.set_preset(
            90,
            20,
            "Deep Dive",
            long_break=20,
            long_every=1,
            cycles=1,
            blurb="One long, quiet block with minimal chrome.",
            key="deep-dive",
        )
        self.hero_sub.configure(text="Deep Dive · 90 minutes · distractions fade away")
        self.after(90, self.start_immersive_timer)

    def start_immersive_timer(self):
        # Never make focus startup depend on a stale Tk command. Responsive/theme
        # rebuilds can outlive CTk Python objects, so read live views only when
        # available and fall back to the already-authoritative timer state.
        try:
            work_default = max(1.0, float(getattr(self, "work_time", 25 * 60)) / 60.0)
            break_default = max(0.0, float(getattr(self, "break_time", 5 * 60)) / 60.0)
            long_default = max(0.0, float(getattr(self, "long_break_time", 15 * 60)) / 60.0)
            every_default = max(1, int(getattr(self, "long_break_every", 4) or 4))
            cycles_default = max(1, int(getattr(self, "max_cycles", 4) or 4))

            self.work_time = max(1.0, float(self._read_entry_view("entry_work", work_default))) * 60
            self.break_time = max(0.0, float(self._read_entry_view("entry_break", break_default))) * 60
            self.long_break_time = max(0.0, float(self._read_entry_view("entry_long_break", long_default))) * 60
            self.long_break_every = max(1, int(float(self._read_entry_view("entry_long_every", every_default))))
            self.max_cycles = max(1, int(float(self._read_entry_view("entry_cycles", cycles_default))))
        except (TypeError, ValueError):
            try:
                self.hero_sub.configure(text=self.t("invalid_number"))
            except Exception:
                pass
            return

        self.intention = str(self._read_entry_view("entry_intention", getattr(self, "intention", ""))).strip()
        if self.intention:
            self.workspace.current_task = self.intention
        self.is_long_break = False

        url = self.entry_music.get().strip()
        # Prefer playlist current if entry empty
        if not url and self.playlist.current():
            cur = self.playlist.current()
            url = cur.url
            self.entry_music.insert(0, url)
        elif url:
            # ensure current URL is in playlist
            title = self.music.meta_title if self.music.url == url else ""
            self.playlist.add(url, title)
            # select matching index
            for i, t in enumerate(self.playlist.tracks):
                if t.url == url:
                    self.playlist.select(i)
                    break
            self._refresh_playlist_ui()

        self.music.set_url(url)
        self.music.set_volume(float(self.volume_slider.get()))
        if url and self.music._output_device_index is None:
            self._on_music_status(self.t("audio_need_pick"))

        self.main_container.grid_forget()
        self._setup_visible = False
        self._menu_open = False
        self.wave_frame.grid(row=0, column=0, sticky="nsew")
        self.canvas.pack(fill="both", expand=True)
        self.status_text.place(relx=0.5, rely=0.08, anchor="center")
        self.time_text.place(relx=0.5, rely=0.38, anchor="center")
        self.intention_live.place_forget()  # drawn on canvas as visual chip
        self.menu_btn.place(relx=0.97, rely=0.035, anchor="ne")
        self.menu_btn.lift()
        self._chrome_visible = True
        self._place_secondary_chrome()
        self._schedule_chrome_hide()

        self.current_cycle = 1
        self.is_paused = False
        self.pause_btn.configure(text=self.t("pause"))
        self.particles.clear()
        self.focus_set()

        if url:
            self._on_music_status(self.t("music_preparing"))

            def done(ok: bool, msg: str):
                def ui():
                    self._cover_tk_cache.clear()
                    self._cover_token += 1
                    if ok:
                        self._on_music_status(f"♪ {self.music.display_title()}")
                        if self.is_running and not self.is_paused and self.mode == "Work":
                            self.music.play()
                    else:
                        self._on_music_status(self.t("music_skip", msg=msg))

                self.after(0, ui)

            self.music.prepare_async(done)

        self.start_work_period()
        self._animate_enter()

    def _place_secondary_chrome(self):
        if getattr(self, "_v3_focus", False):
            self.minimal_shell.place_focus_chrome()
            return
        try:
            self.menu_btn.place(relx=0.97, rely=0.035, anchor="ne")
            self.menu_btn.lift()
        except Exception:
            pass
        if self._chrome_visible or self.mode == "Break" or self.is_paused or self._menu_open:
            # Keep focus chrome intentionally sparse: one music line + controls.
            self.music_live.place(relx=0.5, rely=0.67, anchor="center")
            self.track_badge.place_forget()
            self.hint_text.place_forget()
            self.ctrl_bar.place(relx=0.5, rely=0.90, anchor="center")
        else:
            for w in (self.music_live, self.track_badge, self.hint_text, self.ctrl_bar):
                try:
                    w.place_forget()
                except Exception:
                    pass

    def _reveal_chrome(self, _event=None):
        if not self.wave_frame.winfo_ismapped():
            return
        self._chrome_visible = True
        self._place_secondary_chrome()
        self._schedule_chrome_hide()

    def _schedule_chrome_hide(self):
        if self._chrome_hide_job is not None:
            try:
                self.after_cancel(self._chrome_hide_job)
            except Exception:
                pass
        self._chrome_hide_job = self.after(4200, self._auto_hide_chrome)

    def _auto_hide_chrome(self):
        self._chrome_hide_job = None
        if not self.wave_frame.winfo_ismapped():
            return
        if self.mode == "Work" and self.is_running and not self.is_paused and not self._menu_open:
            self._chrome_visible = False
            self._place_secondary_chrome()

    def _animate_enter(self):
        """Calm fade-in — soft cool white, never harsh pure white flash."""
        soft = "#dce8ef"
        self.status_text.configure(text_color=self.theme.bg, fg_color="transparent")
        self.time_text.configure(text_color=self.theme.bg, fg_color="transparent")

        def fade(i=0):
            if i > 14 or not self.wave_frame.winfo_ismapped():
                self.status_text.configure(text_color="#c5d6e0")
                self.time_text.configure(text_color=soft)
                return
            t = i / 14
            c = self._blend(self.theme.bg, soft, t)
            self.status_text.configure(text_color=self._blend(self.theme.bg, "#b7c9d4", t))
            self.time_text.configure(text_color=c)
            self.after(40, lambda: fade(i + 1))

        fade()

    def start_work_period(self):
        self.mode = "Work"
        self.is_long_break = False
        self.total_seconds = self.work_time
        self.remaining_seconds = self.work_time
        self.is_running = True
        self.is_paused = False
        self.pause_btn.configure(text=self.t("pause"))
        self.status_text.configure(text=self.t("status_focus", cur=self.current_cycle, max=self.max_cycles))
        self.break_tip_live.place_forget()
        self.intention_live.place_forget()  # canvas chip during Work
        self._sync_music_for_state()
        self._schedule_chrome_hide()
        if self._temptation_armed:
            self._start_temptation_watch()
        self.update_loop()

    def start_break_period(self, long_break: bool = False):
        self.mode = "Break"
        self.is_long_break = long_break
        self.total_seconds = self.long_break_time if long_break else self.break_time
        self.remaining_seconds = self.total_seconds
        self.is_paused = False
        self.pause_btn.configure(text=self.t("pause"))
        if long_break:
            self.status_text.configure(
                text=self.t("status_long_break", min=int(self.long_break_time // 60))
            )
        else:
            self.status_text.configure(text=self.t("status_short_break"))
        tips = self._break_tips()
        tip = tips[self._break_tip_idx % len(tips)]
        self._break_tip_idx += 1
        self.break_tip_live.configure(text=tip)
        self.break_tip_live.place(relx=0.5, rely=0.58, anchor="center")
        self.intention_live.place_forget()
        self._sync_music_for_state()  # music off during break (cognitive recovery)
        self._hide_temptation_overlay()  # allow other apps during restorative break
        self._chrome_visible = True
        self._place_secondary_chrome()
        self.update_loop()

    def toggle_pause(self):
        if not self.wave_frame.winfo_ismapped() or not self.is_running:
            return
        self.is_paused = not self.is_paused
        self.pause_btn.configure(text=self.t("resume") if self.is_paused else self.t("pause"))
        if self.is_paused:
            label = self.t("status_paused")
            self._hide_temptation_overlay()  # pause 中は他ソフト操作可
        elif self.mode == "Work":
            label = self.t("status_focus", cur=self.current_cycle, max=self.max_cycles)
        elif self.is_long_break:
            label = self.t("long_break_recover")
        else:
            label = self.t("short_break_recover")
        self.status_text.configure(text=label)
        self._sync_music_for_state()
        self._chrome_visible = True
        self._place_secondary_chrome()
        if not self.is_paused:
            self._schedule_chrome_hide()
            self.update_loop()

    def stop_timer(self):
        self.is_running = False
        self.is_paused = False
        self.music.stop()
        self._hide_temptation_overlay()
        if self._chrome_hide_job is not None:
            try:
                self.after_cancel(self._chrome_hide_job)
            except Exception:
                pass
            self._chrome_hide_job = None
        self._chrome_visible = True
        self.close_focus_menu()
        self.wave_frame.grid_forget()
        for child in (
            self.canvas, self.status_text, self.time_text, self.hint_text,
            self.music_live, self.track_badge, self.ctrl_bar, self.menu_btn, self.menu_panel,
            self.intention_live, self.break_tip_live,
        ):
            try:
                child.place_forget()
            except Exception:
                pass
            try:
                child.pack_forget()
            except Exception:
                pass
        self.main_container.grid(row=0, column=0, sticky="nsew")
        self._setup_visible = True
        self._on_music_status(self.t("stopped"))
        self.focus_set()

    def _hotkey_space(self, _event=None):
        if self.wave_frame.winfo_ismapped():
            self.toggle_pause()
        return "break"

    def _hotkey_esc(self, _event=None):
        if self.wave_frame.winfo_ismapped():
            if self._menu_open:
                self.close_focus_menu()
            else:
                self.stop_timer()
        return "break"

    def format_time(self, seconds: float) -> str:
        s = max(0, int(seconds))
        return f"{s // 60:02d}:{s % 60:02d}"

    def _flash_canvas(self, color: str):
        self.canvas.configure(bg=color)

        def restore(i=0):
            if i >= 10:
                self.canvas.configure(bg=self.theme.bg)
                return
            # blend toward bg by just resetting later
            self.after(40, lambda: restore(i + 1))

        self.after(120, lambda: restore())

    def update_loop(self):
        if not self.is_running or self.is_paused:
            if self.is_paused:
                self.draw_waves(frozen=True)
            return

        if self.remaining_seconds > 0:
            self.draw_waves()
            self.time_text.configure(text=self.format_time(self.remaining_seconds))
            # Keep the v3 focus view visually stable; no countdown urgency pulse.
            if getattr(self, "_v3_focus", False):
                self.time_text.configure(font=ctk.CTkFont(family=FONT_UI_BOLD, size=94))
            elif self.remaining_seconds <= 10:
                scale = 88 + int(2 * abs(math.sin(self._ui_pulse * 0.6)))
                self.time_text.configure(font=ctk.CTkFont(family=FONT_UI_BOLD, size=scale))
            else:
                self.time_text.configure(font=ctk.CTkFont(family=FONT_UI_BOLD, size=88))
            self.remaining_seconds -= 0.05
            self.after(50, self.update_loop)
        else:
            if self.mode == "Work":
                # Record completed focus blocks for Tasks / Abyss Stats.
                self.workspace.record_focus_session(
                    self.work_time / 60.0,
                    "Deep Dive" if self.work_time >= 85 * 60 and self.max_cycles == 1 else "Focus",
                    self.intention or self.workspace.current_task,
                )
                # 計画的休憩: Nサイクルごとに長休憩（クラシックPT + ウルトラディアン配慮）
                use_long = (self.current_cycle % self.long_break_every == 0)
                self.start_break_period(long_break=use_long)
            elif self.current_cycle < self.max_cycles:
                self.current_cycle += 1
                self.start_work_period()
            else:
                self.status_text.configure(text=self.t("status_done"))
                self.time_text.configure(text="00:00")
                self.break_tip_live.configure(text=self.t("status_done_tip"))
                self.break_tip_live.place(relx=0.5, rely=0.58, anchor="center")
                self.is_running = False
                self.music.stop()
                self._on_music_status(self.t("session_done_short"))
                self.draw_waves(frozen=True)

    def _ambient_loop(self):
        """Keep subtle motion on setup / paused screens."""
        motion = 0.0 if self.reduce_motion else 1.0
        self._ui_pulse += 0.08 * motion
        self.phase_glow += 0.04 * motion
        self._eq_seed += 0.12 * motion
        if self.wave_frame.winfo_ismapped() and (self.is_paused or not self.is_running):
            self.draw_waves(frozen=True)
        if self._setup_visible:
            self._draw_now_preview()
        self.after(50, self._ambient_loop)

    def _draw_now_preview(self):
        c = self.now_preview
        c.delete("all")
        tw = int(c.cget("width"))
        th = int(c.cget("height"))
        accent = self.theme.accent
        cx, cy, r = 44, th // 2, 30
        playing = bool(self.music.url) and (
            self.music._is_playing or self.music._ready or self.music.kind == "spotify"
        )
        if playing and not self.music._paused and self.music._is_playing:
            self._disc_angle += 0.06

        art = self._get_cover_tk(r * 2, accent)
        if art is not None:
            c.create_image(cx, cy, image=art)
            c.create_oval(cx - r, cy - r, cx + r, cy + r, outline=accent, width=2)
            # tiny hub
            c.create_oval(cx - 4, cy - 4, cx + 4, cy + 4, fill="#0b0f14", outline=accent)
        else:
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=self.theme.glow, outline=accent, width=2)
            for i in range(0, 360, 30):
                a = math.radians(i + self._disc_angle * 40)
                c.create_line(
                    cx + math.cos(a) * 10, cy + math.sin(a) * 10,
                    cx + math.cos(a) * (r - 6), cy + math.sin(a) * (r - 6),
                    fill=self._blend(self.theme.sidebar, accent, 0.45),
                )
            c.create_oval(cx - 5, cy - 5, cx + 5, cy + 5, fill=accent, outline="")

        # eq bars
        bx0 = 90
        for i in range(12):
            hgt = 8 + (14 * abs(math.sin(self._eq_seed + i * 0.55)) if (playing and self.music._is_playing) else 4)
            x = bx0 + i * 10
            c.create_rectangle(x, cy + 18 - hgt, x + 6, cy + 18, fill=accent, outline="")
        title = self.music.display_title() if self.music.url else "Add a track to preview"
        artist = self.music.display_artist() if self.music.url else ""
        c.create_text(90, cy - 16, anchor="w", text=title, fill=self.theme.text, font=(FONT_UI, 10, "bold"))
        c.create_text(
            90, cy + 2, anchor="w",
            text=f"{self.music.source_badge()}  ·  {artist or ('Playing' if self.music._is_playing else 'Ready' if self.music.url else 'Idle')}",
            fill=self.theme.muted, font=(FONT_UI, 9),
        )

    def _draw_minimal_focus_ring(self, cx, cy, radius, progress, color):
        """Quiet progress ring behind the timer. No album-art disc during focus."""
        r = max(76, radius * 0.78)
        x0, y0, x1, y1 = cx-r, cy-r, cx+r, cy+r
        base = self._blend(self.theme.bg, self.theme.glow, 0.55)
        self.canvas.create_oval(x0, y0, x1, y1, outline=base, width=2)
        extent = max(0.5, min(359.5, progress * 359.5))
        self.canvas.create_arc(
            x0, y0, x1, y1,
            start=90, extent=-extent,
            style="arc", outline=color, width=4,
        )
        # tiny breathing marker, deliberately quieter than the old now-playing disc.
        angle = math.radians(90 - progress * 360)
        mx = cx + math.cos(angle) * r
        my = cy - math.sin(angle) * r
        self.canvas.create_oval(mx-3, my-3, mx+3, my+3, fill=color, outline="")

    def draw_waves(self, frozen: bool = False):
        if getattr(self, "_v3_focus", False):
            self.minimal_shell.draw_focus_canvas(frozen=frozen)
            return
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 10:
            return
        
        progress = 0.0
        if self.total_seconds > 0:
            progress = 1.0 - (self.remaining_seconds / self.total_seconds)
        water_level = h - (progress * h * 0.55) - h * 0.08
        
        long_break = self.mode == "Break" and self.is_long_break
        if self.mode == "Work":
            c_back = self.theme.wave_back_work
            c_front = self.theme.wave_front_work
        elif long_break:
            c_back = self._blend(self.theme.wave_back_break, "#8a6a20", 0.45)
            c_front = self._rhythm_color("long")
        else:
            c_back = self.theme.wave_back_break
            c_front = self.theme.wave_front_break

        photo = self._get_bg_photo(w, h)
        if photo is not None:
            self.canvas.create_image(0, 0, image=photo, anchor="nw")
        else:
            bands = 8
            for i in range(bands):
                y0 = int(h * i / bands)
                y1 = int(h * (i + 1) / bands) + 1
                factor = i / max(1, bands - 1)
                col = self._blend(self.theme.bg, self.theme.glow, factor * 0.45)
                self.canvas.create_rectangle(0, y0, w, y1, fill=col, outline="")

        if self.mode == "Break":
            tint = self._rhythm_color("long") if long_break else self.theme.wave_front_break
            for i in range(5):
                a = 0.10 * (1.0 - i / 5)
                col = self._blend(self.theme.bg, tint, a)
                y0 = int(h * i / 12)
                y1 = int(h * (i + 1) / 12) + 1
                self.canvas.create_rectangle(0, y0, w, y1, fill=col, outline="", stipple="gray50")
            for i in range(4):
                a = 0.08 * (1.0 - i / 4)
                col = self._blend(self.theme.bg, tint, a)
                y1 = h - int(h * i / 14)
                y0 = h - int(h * (i + 1) / 14)
                self.canvas.create_rectangle(0, y0, w, y1, fill=col, outline="", stipple="gray50")

        calm = self._calm_focus and self.mode == "Work" and not self.is_paused
        if not frozen:
            if self.mode == "Break":
                self.phase2 += 0.035
                self.phase1 += 0.028
                self._eq_seed += 0.05
            else:
                self.phase2 += 0.06 if calm else 0.11
                self.phase1 += 0.04 if calm else 0.075
                self._eq_seed += 0.08 if calm else 0.18
            if self.music._is_playing and not self.is_paused and self.mode == "Work":
                self._disc_angle += 0.02 if calm else 0.045
            self._title_scroll += 0.4
        else:
            self.phase2 += 0.015
            self.phase1 += 0.01
            self._eq_seed += 0.03

        self._draw_cycle_dots(w, h)

        cx, cy = w * 0.5, h * 0.40
        rad = min(w, h) * (0.18 if calm else 0.20)
        if self.mode == "Break":
            self._draw_breath_orb(cx, cy, rad, progress, c_front, long_break, frozen)
        else:
            self._draw_minimal_focus_ring(cx, cy, rad, progress, c_front)

        if self.mode == "Work" and self.intention and not self.is_paused:
            self._draw_intention_chip(w, h)

        margin = 160
        depth = 220
        amp2 = 6 if self.mode == "Break" else 10
        amp1 = 8 if self.mode == "Break" else 14
        p2 = [-margin, h + depth]
        for x in range(-margin, w + margin + 30, 30):
            y = water_level + amp2 * math.sin(x * 0.012 + self.phase2) + 4 * math.sin(x * 0.03 + self.phase2 * 0.7)
            p2.extend([x, y])
        p2.extend([w + margin, h + depth])
        wave_back = self._blend(c_back, self.theme.bg, 0.25 if calm else 0.05)
        self.canvas.create_polygon(p2, fill=wave_back, smooth=True)

        p1 = [-margin, h + depth]
        for x in range(-margin, w + margin + 30, 28):
            y = water_level + amp1 * math.cos(x * 0.011 + self.phase1) + 5 * math.sin(x * 0.025 + self.phase1)
            p1.extend([x, y])
        p1.extend([w + margin, h + depth])
        wave_front = self._blend(c_front, self.theme.bg, 0.20 if calm else 0.0)
        self.canvas.create_polygon(p1, fill=wave_front, smooth=True)

        foam = []
        for x in range(0, w + 20, 18):
            y = water_level + amp1 * math.cos(x * 0.011 + self.phase1) - 3
            foam.extend([x, y])
        if len(foam) >= 4:
            foam_col = "#d4c4a0" if long_break else "#b7c8d4"
            self.canvas.create_line(*foam, fill=foam_col, width=1, smooth=True)

        max_p = 6 if self.mode == "Break" else (10 if calm else 20)
        if not frozen and len(self.particles) < max_p:
            if int(self.phase1 * 10) % (5 if calm else 3) == 0:
                self.particles.append(Particle(w, h, water_level))

        alive = []
        for p in self.particles:
            if frozen:
                p.x += p.vx * 0.15
                p.y += p.vy * 0.15
                keep = p.life > 0
            else:
                keep = p.step()
            if keep and p.y > -10:
                base_col = self._rhythm_color("long") if long_break else (
                    self.theme.wave_front_break if self.mode == "Break" else self.theme.particle
                )
                color = self._hex_alpha(base_col, p.a * (0.35 if self.mode == "Break" else (0.45 if calm else 0.85)))
                self.canvas.create_oval(
                    p.x - p.r, p.y - p.r, p.x + p.r, p.y + p.r,
                    fill=color, outline="",
                )
                alive.append(p)
        self.particles = alive

        try:
            title = self.music.display_title() if self.music.url else ""
            if title:
                if self.music._is_playing:
                    title = f"♪  {title}"
                self.music_live.configure(text=title, fg_color="transparent")
            artist = self.music.display_artist() if self.music.url else ""
            self.track_badge.configure(
                text=f"{self.music.source_badge()}  ·  {artist}" if artist else self.music.source_badge(),
                fg_color="transparent",
            )
            self.status_text.configure(fg_color="transparent")
            self.time_text.configure(fg_color="transparent")
            self.hint_text.configure(fg_color="transparent")
            # Soften text color by phase
            if self.mode == "Break":
                tip_col = "#d4c890" if long_break else "#9eb8a8"
                self.break_tip_live.configure(text_color=tip_col, fg_color="transparent")
        except Exception:
            pass

    def _draw_cycle_dots(self, w: int, h: int):
        """Pomodoro tomatoes toward next long break — planned-break progress as GUI."""
        every = max(1, int(getattr(self, "long_break_every", 4) or 4))
        if self.mode == "Work":
            filled = (self.current_cycle - 1) % every
            active = filled
        elif self.is_long_break:
            filled = every
            active = -1
        else:
            filled = self.current_cycle % every
            if filled == 0:
                filled = every
            active = -1

        r = 6
        gap = 16
        total_w = every * gap
        x0 = w * 0.5 - total_w * 0.5 + gap * 0.5
        y = h * 0.14
        for i in range(every):
            cx = x0 + i * gap
            if i < filled:
                col = self._rhythm_color("long") if self.is_long_break and filled == every else self.theme.accent
                self.canvas.create_oval(cx - r, y - r, cx + r, y + r, fill=col, outline="")
            elif i == active and self.mode == "Work":
                pulse = 0.55 + 0.45 * abs(math.sin(self.phase1 * 1.2))
                col = self._blend(self.theme.bg, self.theme.accent, 0.35 + 0.45 * pulse)
                self.canvas.create_oval(cx - r - 1, y - r - 1, cx + r + 1, y + r + 1, outline=col, width=2)
                self.canvas.create_oval(cx - r + 2, y - r + 2, cx + r - 2, y + r - 2, fill=col, outline="")
            else:
                ring = self._blend(self.theme.bg, self.theme.muted, 0.45)
                self.canvas.create_oval(cx - r, y - r, cx + r, y + r, outline=ring, width=1)

    def _draw_intention_chip(self, w: int, h: int):
        text = self.intention[:42] + ("…" if len(self.intention) > 42 else "")
        try:
            import tkinter.font as tkfont
            f = tkfont.Font(family=FONT_UI, size=11)
            text_w = f.measure(text)
        except Exception:
            text_w = len(text) * 8
        pad_l, pad_r, th = 40, 16, 30
        tw = min(w * 0.78, pad_l + text_w + pad_r)
        cx, cy = w * 0.5, h * 0.535
        x0, y0 = cx - tw / 2, cy - th / 2
        fill = self._blend(self.theme.sidebar, self.theme.bg, 0.35)
        outline = self._blend(self.theme.bg, self.theme.accent, 0.55)
        self.canvas.create_rectangle(x0, y0, x0 + tw, y0 + th, fill=fill, outline=outline, width=1)
        br = 10
        bx = x0 + 16
        self.canvas.create_oval(bx - br, cy - br, bx + br, cy + br, fill=self.theme.accent, outline="")
        self.canvas.create_text(bx, cy, text="1", fill="#0a1218", font=(FONT_UI_BOLD, 10))
        self.canvas.create_text(
            bx + 16, cy, anchor="w", text=text,
            fill=self.theme.text, font=(FONT_UI, 11),
        )

    def _draw_breath_orb(self, cx, cy, rad, progress, accent, long_break: bool, frozen: bool):
        """Restorative break visual — slow breath ring, no spinning media disc."""
        breath = 0.5 + 0.5 * math.sin(self.phase1 * (0.55 if not frozen else 0.2))
        r = rad * (0.82 + 0.14 * breath)
        tint = self._rhythm_color("long") if long_break else accent
        for i, a in enumerate((0.08, 0.14, 0.22)):
            rr = r + 28 - i * 10
            col = self._blend(self.theme.bg, tint, a)
            self.canvas.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, outline=col, width=2)
        body = self._blend(self.theme.bg, tint, 0.22 + 0.08 * breath)
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, fill=body, outline=tint, width=2)
        # progress as soft arc
        self.canvas.create_arc(
            cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10,
            start=90, extent=-max(1.0, 360.0 * progress), style="arc",
            outline=self._blend(self.theme.bg, tint, 0.65), width=3,
        )
        hint = self.t("long_break_recover") if long_break else self.t("short_break_recover")
        self.canvas.create_text(
            cx, cy, text=hint, fill=self.theme.text,
            font=(FONT_UI_BOLD, 13),
        )

    def _draw_now_playing_disc(self, cx, cy, rad, progress, accent, frozen: bool, calm: bool = True):
        # Soft outer rings (low contrast)
        ring = self._blend(self.theme.bg, accent, 0.35 if calm else 0.55)
        for i, a in enumerate((0.10, 0.16)):
            r = rad + 22 - i * 8
            col = self._blend(self.theme.bg, accent, a)
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=col, width=1)

        # progress ring — thin, calm
        self.canvas.create_oval(
            cx - rad - 8, cy - rad - 8, cx + rad + 8, cy + rad + 8,
            outline=self._blend(self.theme.bg, accent, 0.25), width=3,
        )
        extent = -max(1.0, 360.0 * progress)
        self.canvas.create_arc(
            cx - rad - 8, cy - rad - 8, cx + rad + 8, cy + rad + 8,
            start=90, extent=extent, style="arc",
            outline=ring, width=3,
        )

        art_size = int(rad * 2)
        art = self._get_cover_tk(art_size, accent)
        if art is not None:
            self.canvas.create_image(cx, cy, image=art)
            self.canvas.create_oval(
                cx - rad, cy - rad, cx + rad, cy + rad,
                outline=ring, width=2,
            )
            hub = max(7, rad * 0.10)
            self.canvas.create_oval(
                cx - hub, cy - hub, cx + hub, cy + hub,
                fill=self._blend(self.theme.bg, accent, 0.35), outline=ring, width=1,
            )
        else:
            body = self._blend(self.theme.bg, accent, 0.18)
            self.canvas.create_oval(cx - rad, cy - rad, cx + rad, cy + rad, fill=body, outline=ring, width=2)
            for ring_f in (0.72, 0.48):
                rr = rad * ring_f
                self.canvas.create_oval(
                    cx - rr, cy - rr, cx + rr, cy + rr,
                    outline=self._blend(body, "#ffffff", 0.08), width=1,
                )
            hub = rad * 0.14
            self.canvas.create_oval(cx - hub, cy - hub, cx + hub, cy + hub, fill=ring, outline="")

        if not calm or self.mode == "Break":
            bars = 14 if calm else 22
            playing = self.music._is_playing and not self.is_paused and not frozen
            soft_eq = self._blend(self.theme.bg, accent, 0.45)
            for i in range(bars):
                t = i / max(1, bars - 1)
                ang = math.radians(210 + t * 120)
                base_r = rad + 18
                amp = (6 + 8 * abs(math.sin(self._eq_seed + i * 0.4))) if playing else 3
                x0 = cx + math.cos(ang) * base_r
                y0 = cy + math.sin(ang) * base_r
                x1 = cx + math.cos(ang) * (base_r + amp)
                y1 = cy + math.sin(ang) * (base_r + amp)
                self.canvas.create_line(x0, y0, x1, y1, fill=soft_eq, width=2)

        if self._chrome_visible or self.mode != "Work" or self.is_paused:
            title = self.music.display_title() if self.music.url else ""
            artist = self.music.display_artist() if self.music.url else ""
            if title:
                ty = cy + rad + 36
                self._canvas_soft_text(cx, ty, f"{self.music.source_badge()}  ·  {title[:36]}", "#e4eef4", 10, bold=True)
                if artist:
                    self._canvas_soft_text(cx, ty + 18, artist[:40], "#a7b8c4", 9, bold=False)

    def _canvas_soft_text(self, x, y, text: str, fill: str, size: int, bold: bool = False):
        """Readable text without opaque black chips (reduces visual clutter)."""
        font = (FONT_UI_BOLD, size) if bold else (FONT_UI, size)
        # soft shadow toward theme bg, not pure black
        shadow = self._blend(self.theme.bg, fill, 0.15)
        for dx, dy in ((1, 1), (-1, 0), (0, 1)):
            self.canvas.create_text(x + dx, y + dy, text=text, fill=shadow, font=font)
        self.canvas.create_text(x, y, text=text, fill=fill, font=font)

    @staticmethod
    def _blend(c1: str, c2: str, t: float) -> str:
        t = max(0.0, min(1.0, t))

        def parse(c):
            c = c.lstrip("#")
            return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))

        a, b = parse(c1), parse(c2)
        r = int(a[0] + (b[0] - a[0]) * t)
        g = int(a[1] + (b[1] - a[1]) * t)
        bl = int(a[2] + (b[2] - a[2]) * t)
        return f"#{r:02x}{g:02x}{bl:02x}"

    @staticmethod
    def _hex_alpha(hex_color: str, alpha: float) -> str:
        """Approximate alpha by blending toward dark bg (canvas can't do real alpha fills easily)."""
        c = hex_color.lstrip("#")
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        bg = 12
        t = max(0.0, min(1.0, alpha))
        r = int(bg + (r - bg) * t)
        g = int(bg + (g - bg) * t)
        b = int(bg + (b - bg) * t)
        return f"#{r:02x}{g:02x}{b:02x}"


if __name__ == "__main__":
    enable_windows_dpi_awareness()
    app = WaterTimer()

    # Preview-only sizing hook used by CI screenshot capture. Normal launches are
    # unchanged; this merely lets us verify responsive layouts before release.
    try:
        import sys
        if "--preview-size" in sys.argv:
            idx = sys.argv.index("--preview-size")
            size = sys.argv[idx + 1]
            if "x" in size.lower():
                sw, sh = size.lower().split("x", 1)
                sw_i, sh_i = max(500, int(sw)), max(500, int(sh))
                app.geometry(f"{sw_i}x{sh_i}+0+0")
                app.update_idletasks()
                app.after(80, app._apply_dashboard_layout)

        # CI-only focus preview. It exercises the real focus surface (including
        # rising water, chrome and responsive placement) without changing normal
        # launches or requiring a fake screenshot renderer.
        if "--preview-focus" in sys.argv:
            def _preview_focus():
                try:
                    app.start_immersive_timer()
                    # Show a meaningful in-progress water level instead of the
                    # initial frame, while keeping the timer safely paused.
                    app.remaining_seconds = max(1.0, app.total_seconds * 0.58)
                    app.is_paused = True
                    app.pause_btn.configure(text=app.t("resume"))
                    app.draw_waves(frozen=True)
                    app._reveal_chrome()
                except Exception as exc:
                    print(f"[preview-focus] {exc}", file=sys.stderr)
            app.after(450, _preview_focus)
    except Exception:
        pass

    app.mainloop()
