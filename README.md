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
  <b>v1.1.0</b>
  ·
  Windows · macOS · Ubuntu · Linux
</p>

---

## Get the app

No build required. Grab a package from [`downloads/`](downloads/) (or a GitHub Release when published).

| Platform | Package | Run |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-1.1.0.exe` | Installer (recommended) |
| **Windows** | `AquaFocus-Windows-Portable-1.1.0.zip` | Unzip → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-1.1.0.zip` | Unzip → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-1.1.0.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |

ffmpeg is **bundled**. Updates can be checked in-app via **AGIU** (GitHub Releases).

> Release notes (EN / JA) for uploaders: [`docs/release/`](docs/release/)

---

## What’s new in 1.1.0

- **AGIU** — check GitHub Releases and update the installed app (all OS packages)
- **Audio output** — pick the playback device yourself (no silent auto-select)
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
