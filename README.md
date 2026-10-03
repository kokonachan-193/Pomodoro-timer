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
  <a href="https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.9"><strong>Aqua Focus v2.1.9</strong></a>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## Get the app

No build required. Download the package for your platform from [**Aqua Focus v2.1.9**](https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.9).

| **File** | **Platform** | **How** |
| :--- | :--- | :--- |
| **AquaFocusSetup-2.1.9.exe** | Windows 10 / 11 | Run the installer |
| **AquaFocus-Windows-Portable-2.1.9.zip** | Windows 10 / 11 | Unzip → `AquaFocus.exe` |
| **AquaFocus-macOS-2.1.9.zip** | macOS | Unzip → open `AquaFocus.app` |
| **AquaFocus-Linux-Portable-2.1.9.tar.gz** | Linux | Extract → run `./AquaFocus/AquaFocus` |
| **AquaFocus-Ubuntu-Portable-2.1.9.tar.gz** | Ubuntu | Same as Linux build |
| **AquaFocus-Android-2.1.9.apk** | Android 8.0+ / arm64-v8a | Install the APK on your device |

ffmpeg is **bundled** on desktop. Existing desktop installs can check GitHub Releases through **AGIU**.

Android release signing notes: [`docs/android-signing.md`](docs/android-signing.md)

---

## What’s new in 2.1.9

- **Release style aligned with v2.1.6** — all six assets are listed in the release body: Windows installer, Windows portable, macOS, Linux, Ubuntu and Android APK.
- **More resilient modern GUI** — resize storms are debounced, stale Tk/CTk widget calls are guarded, and Focus/Home relayout is safer after stop, theme rebuilds or compact-window changes.
- **Safer Focus drawing fallback** — animation errors now recover to a minimal Aqua frame instead of leaving the canvas blank or half-drawn.
- **Live animation extension refresh** — extension install/remove still reloads from `extensions.json` during Focus and redraws without restarting the session.
- **Responsive Focus chrome** — timer text, control placement and secondary Focus controls are re-applied after each update tick to avoid oversized or misplaced UI.
- **AGIU current-version bump** — the desktop updater now treats v2.1.9 as the current app version.
- **Android 2.1.9 release path** — Android build metadata, workflow artifact names and release attachment target now match v2.1.9.

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
