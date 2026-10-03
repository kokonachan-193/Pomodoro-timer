# Aqua Focus

<p align="center">
  <img src="assets/icons/aqua-focus-app.png" alt="Aqua Focus" width="96" />
</p>

<p align="center">
  <strong>Descend into focus.</strong><br />
  A simple, modern Pomodoro workspace — clean focus, subtle motion, music, tasks, stats and extensions.
</p>

<p align="center">
  <a href="README.ja.md">日本語</a>
  ·
  <a href="https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.10"><strong>Aqua Focus v2.1.10</strong></a>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## Get the app

No build required. Download the package for your platform from [**Aqua Focus v2.1.10**](https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.10).

| **File** | **Platform** | **How** |
| :--- | :--- | :--- |
| **AquaFocusSetup-2.1.10.exe** | Windows 10 / 11 | Run the installer |
| **AquaFocus-Windows-Portable-2.1.10.zip** | Windows 10 / 11 | Unzip → `AquaFocus.exe` |
| **AquaFocus-macOS-2.1.10.zip** | macOS | Unzip → open `AquaFocus.app` |
| **AquaFocus-Linux-Portable-2.1.10.tar.gz** | Linux | Extract → run `./AquaFocus/AquaFocus` |
| **AquaFocus-Ubuntu-Portable-2.1.10.tar.gz** | Ubuntu | Same as Linux build |
| **AquaFocus-Android-2.1.10.apk** | Android 8.0+ / arm64-v8a | Install the APK on your device |

ffmpeg is **bundled** on desktop. Existing desktop installs can check GitHub Releases through **AGIU**.

Android release signing notes: [`docs/android-signing.md`](docs/android-signing.md)

---

## What’s new in 2.1.10

- **Visible Focus animation extensions** — Sakura, rain, snow, fireflies, fish, bubbles and particles now use a brighter, faster overlay so enabled FX are clearly visible on dark custom backgrounds.
- **Stronger live extension refresh** — Focus reloads `extensions.json` while running and performs several redraws after extension changes so toggles no longer feel ignored.
- **Reduce Motion still shows state** — motion is calmer, but enabled animation effects remain visibly present instead of disappearing completely.
- **Top-level FX layer** — extension animations are drawn as a dedicated Focus overlay while the calm Aqua base scene remains intact.
- **Windows installer version fix carried forward** — Inno Setup receives the workflow `VERSION`, so `AquaFocusSetup-2.1.10.exe` is generated correctly.
- **AGIU current-version bump** — the desktop updater now treats v2.1.10 as the current app version.
- **Android 2.1.10 release path** — Android build metadata, workflow artifact names and release attachment target now match v2.1.10.

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
  <sub>Aqua Focus · Kokona · Modern Pomodoro focus workspace</sub>
</p>
