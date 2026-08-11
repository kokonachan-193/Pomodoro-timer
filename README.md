# Aqua Focus

**[日本語](README.ja.md)**

Desktop Pomodoro for focus work — timer, focus music, distraction guard.

**OS:** Windows 11 · Windows 10 · macOS · Ubuntu · Linux

---

## Download (no build)

Get ready-made apps from **[Releases](https://github.com/kokonachan-193/Pomodoro-timer/releases)** — download, then run.

| File | Platform | How to use |
| :--- | :--- | :--- |
| **`AquaFocusSetup-*.exe`** | Windows 10 / 11 | Run the installer |
| **`AquaFocus-Windows-x64.zip`** | Windows 10 / 11 | Unzip → `AquaFocus.exe` |
| **`AquaFocus-macOS.zip`** | macOS | Unzip → open `AquaFocus.app` |
| **`AquaFocus-Linux-x64.tar.gz`** | Ubuntu / Linux | Extract → `./AquaFocus` |

ffmpeg is bundled in all packages. On Linux you may also want: `sudo apt install libportaudio2 fonts-noto-cjk`.

Packages are built automatically by GitHub Actions for every version tag (`v*`).

---

## Run from source (developers)

```bash
pip install -r requirements.txt
python main.py          # Windows: py main.py
```

Details: [`docs/platforms.md`](docs/platforms.md)

## Features

- Science-based presets, long breaks, one intention  
- Focus music (YouTube / Spotify / stream) during work only  
- Temptation guard (Windows film / Mac·Linux stay-on-top)  
- UI language: English / 日本語  
