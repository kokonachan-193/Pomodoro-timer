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
  <b>v2.1.7</b>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## Get the app

No build required. Download the package for your platform from the GitHub Release.

| Platform | Package | Run |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-2.1.7.exe` | Installer · recommended |
| **Windows** | `AquaFocus-Windows-Portable-2.1.7.zip` | Unzip → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-2.1.7.zip` | Unzip → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-2.1.7.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |
| **Android 8+** | `AquaFocus-Android-2.1.7.apk` | Install the APK |

ffmpeg is **bundled** on desktop. Existing desktop installs can check GitHub Releases through **AGIU**.

Android release signing notes: [`docs/android-signing.md`](docs/android-signing.md)

---

## What’s new in 2.1.7

- **Android Japanese text fixed** — Android builds now bundle a Noto Japanese-capable font and register it before falling back to device fonts.
- **Safer fallback for unsupported devices** — if no Japanese-capable font can be loaded, Android opens in English instead of showing tofu/garbled text.
- **Responsive Android UI** — phone-size metrics now drive spacing, clock size, button height and Focus canvas size to reduce small-screen breakage.
- **Keyboard focus fix** — Android uses `Window.softinput_mode = "pan"` so the layout is less likely to break when a text field is focused.
- **Focus visuals stabilized** — water and wave geometry are clamped inside the view to prevent broken wave edges.
- **Sakura petals + Reduce Motion** — Sakura petals were added as a lightweight visual, and Reduce Motion can calm the animated effects.
- **APK signing workflow** — GitHub Actions can sign release APKs when Android signing secrets are configured and uploads a certificate fingerprint report.
- **Signing identity display** — the Android app footer shows a shortened APK certificate SHA-256 fingerprint when available.

### Carried forward from 2.1.4 / 2.1.6

- **Responsive dashboard** — compact windows hide the heavy sidebar without destroying it, while large and ultrawide windows keep readable card widths instead of stretching everything.
- **Features preserved** — Quick Dive, custom timing, intention, music, playlist, volume, tasks, stats, soundscapes, extensions, Focus Lock, updater, themes and background controls remain available.
- **Progressive disclosure** — advanced and occasional controls are reachable from a compact `•••` menu instead of crowding the main screen.
- **Focus music controls restored** — the in-session menu stays reachable so tracks can be added, skipped, or navigated without leaving focus.
- **Rising-water progress animation** — the focus view fills upward with a subtle animated waterline tied to elapsed focus time; Reduce Motion still disables the motion.

---

## Features

| Area | Included |
| :--- | :--- |
| **Focus** | Pomodoro, 25/5 · 50/10 · 90/20, long breaks, session intention |
| **Modes** | Focus · Deep Dive · Countdown · Stopwatch · Alarm |
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
