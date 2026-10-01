"""
AGIU — Auto GitHub In Update
Checks GitHub Releases and replaces the installed/portable app on Windows / macOS / Linux.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

APP_NAME = "Aqua Focus"
APP_VERSION = "2.1.2"
GITHUB_OWNER = "kokonachan-193"
GITHUB_REPO = "Pomodoro-timer"
API_LATEST = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"


@dataclass
class ReleaseInfo:
    tag: str
    version: str
    name: str
    body: str
    asset_name: str
    asset_url: str
    html_url: str


def _parse_version(text: str) -> tuple[int, ...]:
    nums = [int(x) for x in re.findall(r"\d+", str(text or ""))]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:4])


def is_newer(remote: str, local: str = APP_VERSION) -> bool:
    return _parse_version(remote) > _parse_version(local)


def _platform_key() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def _pick_asset(assets: list[dict], platform: str) -> dict | None:
    names = [(a.get("name") or "", a) for a in assets if a.get("browser_download_url")]
    lowered = [(n.lower(), a) for n, a in names]

    def find(*needles: str) -> dict | None:
        for n, a in lowered:
            if all(x in n for x in needles):
                return a
        return None

    if platform == "windows":
        return (
            find("setup", ".exe")
            or find("windows", "portable", ".zip")
            or find("windows", ".zip")
            or find("aquafocussetup")
        )
    if platform == "macos":
        return find("macos", ".zip") or find("mac", ".zip") or find(".app")
    return (
        find("linux", ".tar.gz")
        or find("ubuntu", ".tar.gz")
        or find("linux", ".zip")
    )


def fetch_latest_release(timeout: float = 20.0) -> ReleaseInfo | None:
    req = urllib.request.Request(
        API_LATEST,
        headers={
            "User-Agent": f"AquaFocus-AGIU/{APP_VERSION}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    tag = str(data.get("tag_name") or "")
    version = tag.lstrip("vV")
    assets = data.get("assets") or []
    asset = _pick_asset(assets, _platform_key())
    if not asset:
        return None
    return ReleaseInfo(
        tag=tag,
        version=version,
        name=str(data.get("name") or tag),
        body=str(data.get("body") or ""),
        asset_name=str(asset.get("name") or "update.bin"),
        asset_url=str(asset.get("browser_download_url")),
        html_url=str(data.get("html_url") or RELEASES_PAGE),
    )


def download_file(
    url: str,
    dest: Path,
    progress_cb: Callable[[int, int], None] | None = None,
    timeout: float = 60.0,
) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"AquaFocus-AGIU/{APP_VERSION}"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as out:
        total = int(resp.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = resp.read(1024 * 256)
            if not chunk:
                break
            out.write(chunk)
            done += len(chunk)
            if progress_cb:
                progress_cb(done, total)
    return dest


def _app_install_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _write_and_run_updater(commands: list[str], shell: str) -> None:
    tmp = Path(tempfile.gettempdir()) / "aqua_focus_agiu"
    tmp.mkdir(parents=True, exist_ok=True)
    if shell == "bat":
        script = tmp / "apply_update.bat"
        body = "@echo off\r\n" + "\r\n".join(commands) + "\r\n"
        script.write_text(body, encoding="utf-8")
        subprocess.Popen(["cmd", "/c", str(script)], close_fds=True)
    else:
        script = tmp / "apply_update.sh"
        body = "#!/bin/bash\nset -e\n" + "\n".join(commands) + "\n"
        script.write_text(body, encoding="utf-8")
        script.chmod(0o755)
        subprocess.Popen(["/bin/bash", str(script)], start_new_session=True)


def apply_update(package: Path, release: ReleaseInfo) -> None:
    """Spawn a helper that replaces files after this process exits, then exit caller should quit."""
    install_dir = _app_install_dir()
    name = package.name.lower()
    staging = Path(tempfile.gettempdir()) / "aqua_focus_agiu" / "staging"
    if staging.exists():
        shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True, exist_ok=True)

    if name.endswith(".exe") and sys.platform == "win32":
        # Inno Setup — launch installer then quit
        subprocess.Popen([str(package)], close_fds=True)
        return

    extract_dir = staging / "extract"
    extract_dir.mkdir(parents=True, exist_ok=True)
    if name.endswith(".zip"):
        shutil.unpack_archive(str(package), str(extract_dir), "zip")
    elif name.endswith(".tar.gz") or name.endswith(".tgz"):
        shutil.unpack_archive(str(package), str(extract_dir), "gztar")
    else:
        raise RuntimeError(f"Unsupported package: {package.name}")

    # Locate payload root (folder with AquaFocus.exe / AquaFocus / .app)
    payload = extract_dir
    kids = list(extract_dir.iterdir())
    if len(kids) == 1 and kids[0].is_dir():
        payload = kids[0]
    for child in extract_dir.rglob("*"):
        if child.name in ("AquaFocus.exe", "AquaFocus") or child.suffix == ".app" or child.name.endswith(".app"):
            if child.suffix == ".app" or child.name.endswith(".app"):
                payload = child
            else:
                payload = child.parent
            break

    if sys.platform == "win32":
        exe = install_dir / "AquaFocus.exe"
        relaunch = str(exe if exe.exists() else Path(sys.executable))
        src = str(payload)
        dst = str(install_dir)
        _write_and_run_updater(
            [
                "timeout /t 2 /nobreak >nul",
                f'xcopy /E /Y /I /Q "{src}\\*" "{dst}\\"',
                f'start "" "{relaunch}"',
            ],
            "bat",
        )
    elif sys.platform == "darwin":
        # Prefer replacing .app in /Applications or install_dir
        app_src = payload if payload.suffix == ".app" or payload.name.endswith(".app") else None
        if app_src is None:
            found = list(extract_dir.glob("*.app"))
            app_src = found[0] if found else None
        if app_src is None:
            raise RuntimeError("AquaFocus.app not found in package")
        apps = Path("/Applications") / "AquaFocus.app"
        target = apps if apps.exists() or install_dir.name.endswith(".app") else (install_dir.parent / "AquaFocus.app")
        if install_dir.name.endswith(".app"):
            target = install_dir
        _write_and_run_updater(
            [
                "sleep 2",
                f'rm -rf "{target}"',
                f'cp -R "{app_src}" "{target}"',
                f'open "{target}"',
            ],
            "sh",
        )
    else:
        # Linux onedir
        relaunch = str(install_dir / "AquaFocus")
        if not Path(relaunch).exists():
            relaunch = sys.executable
        _write_and_run_updater(
            [
                "sleep 2",
                f'cp -a "{payload}/." "{install_dir}/"',
                f'chmod +x "{install_dir}/AquaFocus" 2>/dev/null || true',
                f'"{relaunch}" &',
            ],
            "sh",
        )


class AgiuController:
    """Background check + download orchestration."""

    def __init__(
        self,
        status_cb: Callable[[str], None] | None = None,
        on_update_available: Callable[[ReleaseInfo], None] | None = None,
    ):
        self.status_cb = status_cb or (lambda _s: None)
        self.on_update_available = on_update_available
        self._busy = False
        self.latest: ReleaseInfo | None = None

    def check_async(self) -> None:
        if self._busy:
            return
        threading.Thread(target=self._check_worker, daemon=True).start()

    def _check_worker(self) -> None:
        self._busy = True
        try:
            self.status_cb("AGIU: checking GitHub Releases…")
            info = fetch_latest_release()
            if info is None:
                self.status_cb("AGIU: could not reach GitHub Releases")
                return
            self.latest = info
            if is_newer(info.version, APP_VERSION):
                self.status_cb(f"AGIU: update available {APP_VERSION} → {info.version}")
                if self.on_update_available:
                    self.on_update_available(info)
            else:
                self.status_cb(f"AGIU: up to date (v{APP_VERSION})")
        finally:
            self._busy = False

    def download_and_apply(
        self,
        info: ReleaseInfo | None = None,
        progress_cb: Callable[[int, int], None] | None = None,
    ) -> Path:
        release = info or self.latest or fetch_latest_release()
        if release is None:
            raise RuntimeError("No release info")
        if not is_newer(release.version, APP_VERSION):
            raise RuntimeError("Already up to date")
        dest = Path(tempfile.gettempdir()) / "aqua_focus_agiu" / release.asset_name
        self.status_cb(f"AGIU: downloading {release.asset_name}…")
        download_file(release.asset_url, dest, progress_cb=progress_cb)
        self.status_cb("AGIU: applying update…")
        apply_update(dest, release)
        return dest
