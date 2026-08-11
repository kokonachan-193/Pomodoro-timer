# Aqua Focus

**[日本語](README.ja.md)**

Desktop Pomodoro — timer, focus music, distraction guard.

**OS:** Windows 11 · Windows 10 · macOS · Ubuntu · Linux

---

## Download & run (no build)

Share the **`downloads/`** folder (or the files inside). Users only download / copy and run.

| Package | OS | How |
| :--- | :--- | :--- |
| `downloads/Windows/AquaFocusSetup-*.exe` | Windows 10 / 11 | Double-click installer |
| `downloads/Windows/AquaFocus-Windows-Portable-*.zip` | Windows 10 / 11 | Unzip → `AquaFocus.exe` |
| `downloads/macOS/AquaFocus-macOS-*.zip` | macOS | Unzip → open `AquaFocus.app` |
| `downloads/Linux/AquaFocus-Linux-Portable-*.tar.gz` | Ubuntu / Linux | `tar xzf … && ./AquaFocus/AquaFocus` |

Windows packages are built on Windows. macOS / Linux packages must be produced **once** on that OS:

```bash
./scripts/make_release_unix.sh
# then copy dist/releases/* into downloads/macOS or downloads/Linux
```

ffmpeg is bundled in packaged builds.

---

## Run from source

```bash
pip install -r requirements.txt
python main.py          # Windows: py main.py
```

See [`docs/platforms.md`](docs/platforms.md).

## Features

- Science presets, long breaks, one intention  
- Focus music during work only  
- Temptation guard · English / 日本語 UI  
