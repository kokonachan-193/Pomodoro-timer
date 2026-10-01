# Aqua Focus

<p align="center">
  <img src="assets/icons/aqua-focus-app.png" alt="Aqua Focus" width="96" />
</p>

<p align="center">
  <strong>Descend into focus.</strong><br />
  A deep-sea focus workspace — immersive timers, music, tasks, soundscapes, stats and extensions.
</p>

<p align="center">
  <a href="README.ja.md">日本語</a>
  ·
  <b>v2.1.2</b>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## Get the app

No build required. Download the package for your platform from the GitHub Release.

| Platform | Package | Run |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-2.1.2.exe` | Installer · recommended |
| **Windows** | `AquaFocus-Windows-Portable-2.1.2.zip` | Unzip → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-2.1.2.zip` | Unzip → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-2.1.2.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |
| **Android 8+** | `AquaFocus-Android-2.1.2.apk` | Install the APK |

ffmpeg is **bundled** on desktop. Existing desktop installs can check GitHub Releases through **AGIU**.

---

## What’s new in 2.1.2

- **Fixed duplicated Home surfaces** — the clean Home is created exactly once; theme changes can no longer stack a second colored Home underneath it
- **Idempotent UI mounting** — stale Home frames are removed before rebuilding, preventing ghost / split-screen layouts
- **Real responsive breakpoints** — Compact, Normal, Wide and Ultra layouts adapt card width, spacing and typography to both small windows and large monitors
- **Feature access restored** — Tasks, Stats, Extensions, Music Library, Soundscape, Countdown, Stopwatch, Alarm and Custom Session are all available from `…`
- **Settings restored** — Theme, Reduce Motion, background image, language, audio output, Focus Lock, exclusions and updater controls are available without crowding Home
- **Full controls escape hatch** — every legacy control remains available from `… → Full controls`
- **Music library UI** — add, play and remove playlist tracks without reopening the old dashboard
- **Cleaner large-screen scaling** — the focus card and timer grow moderately on wide / ultra-wide displays instead of looking tiny in the middle

### Carried forward from 2.0.0

- **Deep Sea UI** — animated caustic light, bubbles, glass-like cards and a calmer visual hierarchy
- **Quick Dive** — Focus, Deep Dive, Countdown, Stopwatch and Alarm from one launcher
- **Deep Dive** — one-click 90-minute low-distraction session
- **Coral Tasks** — persistent tasks that collect focused minutes automatically
- **Abyss Stats** — today / week / all-time focus tracking with a 7-day chart
- **Ocean Soundscape** — independent Ocean / Rain / Brown Noise ambient layer
- **Reef Extensions** — online catalog foundation for themes, sounds and focus presets
- **Reduce Motion** — lower-motion mode for comfort and accessibility
- **Music reliability** — yt-dlp/ffmpeg streaming headers and fallback logic retained from v1.2
- **Cross-platform** — Windows, macOS, Linux / Ubuntu and Android packages

---

## Features

| Area | Included |
| :--- | :--- |
| **Focus** | Pomodoro, 25/5 · 50/10 · 90/20, long breaks, session intention |
| **Modes** | Focus · Deep Dive · Countdown · Stopwatch · Blue Alarm |
| **Music** | YouTube / Spotify-matched / direct streams, playlists, audio output selection |
| **Soundscape** | Ocean · Rain · Brown Noise as a separate ambient layer |
| **Tasks** | Persistent tasks, completion state, focus-minute attribution |
| **Stats** | Daily / weekly / total focus time, recent sessions, 7-day chart |
| **Extensions** | Online catalog + local installed-extension registry |
| **Focus lock** | Temptation guard on desktop |
| **Accessibility** | Reduce Motion and calm-focus behavior |
| **Updates** | AGIU desktop update checker |

Product / UI plan: [`docs/aqua-focus-v2-concept.md`](docs/aqua-focus-v2-concept.md)

---

## Run from source

```bash
pip install -r requirements.txt
python main.py
```

### Build packages

```powershell
# Windows
.\scripts\make_release_win.ps1
```

```bash
# macOS / Linux
./scripts/make_release_unix.sh
```

Android:

```bash
cd android
buildozer android debug
```

---

<p align="center">
  <sub>Aqua Focus · Kokona · Deep Sea focus workspace</sub>
</p>
