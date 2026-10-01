# Aqua Focus

<p align="center">
  <img src="assets/icons/aqua-focus-app.png" alt="Aqua Focus" width="96" />
</p>

<p align="center">
  <strong>Find your flow.</strong><br />
  A calm desktop Pomodoro — focus music, distraction guard, planned breaks.
</p>

<p align="center">
  <a href="README.ja.md">日本語</a>
  ·
  <b>v1.2.0</b>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## Get the app

No build required. Grab a package from [`downloads/`](downloads/) (or a GitHub Release when published).

| Platform | Package | Run |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-1.2.0.exe` | Installer (recommended) |
| **Windows** | `AquaFocus-Windows-Portable-1.2.0.zip` | Unzip → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-1.2.0.zip` | Unzip → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-1.2.0.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |
| **Android 8+** | `AquaFocus-Android-1.2.0.apk` | Install APK on your Android device |

ffmpeg is **bundled**. Updates can be checked in-app via **AGIU** (GitHub Releases).

> Release notes (EN / JA) for uploaders: [`docs/release/`](docs/release/)

---

## What’s new in 1.2.0

- **AGIU** — check GitHub Releases and update the installed app (all OS packages)
- **Music reliability** — YouTube/Spotify playback preserves required HTTP headers and falls back cleanly when streaming fails
- **Modernized UI** — scrollable settings/sidebar, roomier layout, better small-screen usability
- **Audio output** — uses the OS default automatically when no device is selected
- Cross-platform packages: Windows · macOS · Linux / Ubuntu

---

## Features

| | |
| :--- | :--- |
| **Timer** | Science-based presets, short → long breaks, one session intention |
| **Music** | YouTube / Spotify / direct stream — **work sessions only** |
| **Focus lock** | Temptation guard (full film on Windows; soft mode on macOS / Linux) |
| **Language** | 日本語 / English in the sidebar |
| **Updates** | AGIU · audio device picker |

More detail: [`docs/platforms.md`](docs/platforms.md) · [`docs/learning-science-jp.md`](docs/learning-science-jp.md)

---

## Run from source

```bash
pip install -r requirements.txt
python main.py          # Windows: py main.py
```

### Build packages

```powershell
# Windows
.\scripts\make_release_win.ps1
```

```bash
# macOS or Linux (on that OS)
./scripts/make_release_unix.sh
```

---

<p align="center">
  <sub>Aqua Focus · Kokona · MIT-friendly desktop focus tool</sub>
</p>
