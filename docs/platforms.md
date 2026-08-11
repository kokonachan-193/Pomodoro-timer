# Aqua Focus — 対応 OS とビルド

公式サポート対象（すべて本体動作対象）:

| # | OS | バージョン目安 |
| :---: | :--- | :--- |
| 1 | **Windows 11** | 現行サポート版 |
| 2 | **Windows 10** | 22H2 などサポート中の版 |
| 3 | **macOS** | Apple Silicon / Intel（現行付近） |
| 4 | **Ubuntu** | 22.04 LTS / 24.04 LTS 想定 |
| 5 | **Linux** | その他ディストロ（glibc 系想定） |

---

## 機能マトリクス

| OS | アプリ本体 | 誘惑排除 | 配布物 | ビルド |
| :--- | :---: | :--- | :--- | :--- |
| **Windows 11** | ○ | ○ フィルム（他アプリ全面） | `AquaFocus.exe` / Setup | `scripts/build_exe.ps1` |
| **Windows 10** | ○ | ○ フィルム（他アプリ全面） | `AquaFocus.exe` / Setup | `scripts/build_exe.ps1` |
| **macOS** | ○ | 簡易（前面維持） | `AquaFocus.app` | `scripts/build_unix.sh` |
| **Ubuntu** | ○ | 簡易（前面維持） | フォルダ + `.desktop` | `scripts/build_unix.sh` |
| **Linux** | ○ | 簡易（前面維持） | フォルダ + `.desktop` | `scripts/build_unix.sh` |

> 他ソフトへ薄いフィルムを貼る機能は Win32 API 依存のため **Windows 10 / Windows 11 専用**。  
> **macOS / Ubuntu / Linux** では Focus 中に Aqua Focus を前面に保つ簡易モードになります。

---

## 必要ランタイム（開発実行）

共通:

```bash
pip install -r requirements.txt
```

| OS | 追加パッケージ例 |
| :--- | :--- |
| **Windows 10 / 11** | Python 3.10+（`py` ランチャ可）。Tk は公式インストーラ同梱が多い |
| **macOS** | `brew install python-tk portaudio` |
| **Ubuntu** | `sudo apt install python3-tk libportaudio2`（CJK: `fonts-noto-cjk` 推奨） |
| **Linux** | ディストロに応じて `python3-tk` / PortAudio / Noto CJK |

```bash
python main.py    # Windows: py main.py
```

> **ffmpeg**: `imageio-ffmpeg` がバイナリを用意。  
> **exe / .app / 配布フォルダ** では PyInstaller 同梱＋起動時 `bin/` 展開。別途 ffmpeg インストールは原則不要。

---

## 言語（全 OS 共通）

サイドバー **LANGUAGE** → **日本語 / English**  
設定: `data/settings.json`（UI・プリセット・フィルム文言などが一括切替）

---

## GitHub Releases（推奨・ビルド不要）

タグ `v*` を push すると Actions が次を自動生成して [Releases](https://github.com/kokonachan-193/Pomodoro-timer/releases) に載せます。

| 成果物 | OS |
| :--- | :--- |
| `AquaFocusSetup-*.exe` / `AquaFocus-Windows-x64.zip` | Windows 10 / 11 |
| `AquaFocus-macOS.zip`（`.app`） | macOS |
| `AquaFocus-Linux-x64.tar.gz` | Ubuntu / Linux |

```bash
git tag v1.1.0
git push origin v1.1.0
```

## ローカルビルド手順

### Windows 11 / Windows 10

```powershell
.\scripts\build_exe.ps1
# インストーラー（任意）
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' .\installer\aqua-focus.iss
```

- 出力: `dist\AquaFocus\AquaFocus.exe`
- Setup: `dist\installer\AquaFocusSetup-1.0.0.exe`
- Win10 / Win11 とも同じ成果物で動作

### macOS

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
```

- 出力: `dist/AquaFocus.app`
- `/Applications` へドラッグ、または DMG 化して配布

### Ubuntu

```bash
chmod +x scripts/build_unix.sh
./scripts/build_unix.sh
# 必要なら:
sudo apt install python3-tk libportaudio2 fonts-noto-cjk
```

- 出力: `dist/AquaFocus/AquaFocus`
- `AquaFocus.desktop` を `~/.local/share/applications/` にコピー可

### Linux（Ubuntu 以外）

```bash
./scripts/build_unix.sh
```

- 出力は Ubuntu と同じ onedir 形式
- 依存パッケージ名はディストロごとに読み替え（PortAudio / Tk / CJK フォント）

---

## 注意（全プラットフォーム）

| 項目 | 内容 |
| :--- | :--- |
| フィルム誘惑排除 | Windows 10 / 11 のみフル実装 |
| フォント | Linux / Ubuntu は **Noto Sans CJK JP** 推奨 |
| 音楽ストリーム | 同梱 ffmpeg 優先（PATH の ffmpeg も可） |
| インストーラ言語 | Inno ウィザードの JA/EN はアプリ内 LANGUAGE とは別 |
| クロスビルド | 各 OS 上でビルド推奨（Win 用 exe は Windows で、.app は macOS で） |
