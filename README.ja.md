# Aqua Focus

<p align="center">
  <img src="assets/icons/aqua-focus-app.png" alt="Aqua Focus" width="96" />
</p>

<p align="center">
  <strong>Find your flow.</strong><br />
  落ち着いたデスクトップ向けポモドーロ — Focus 音楽・誘惑排除・計画休憩。
</p>

<p align="center">
  <a href="README.md">English</a>
  ·
  <b>v1.1.0</b>
  ·
  Windows · macOS · Ubuntu · Linux
</p>

---

## ダウンロードして使う

ビルド不要。[`downloads/`](downloads/)（または公開後の GitHub Release）からパッケージを取得してください。

| プラットフォーム | パッケージ | 使い方 |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-1.1.0.exe` | インストーラ（おすすめ） |
| **Windows** | `AquaFocus-Windows-Portable-1.1.0.zip` | 解凍 → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-1.1.0.zip` | 解凍 → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-1.1.0.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |

ffmpeg **同梱**。アプリ内 **AGIU** から GitHub Releases の更新を確認できます。

> リリース投稿用メモ（EN / JA）: [`docs/release/`](docs/release/)

---

## v1.1.0 の新機能

- **AGIU** — GitHub Releases を見てインストール済みアプリを更新（全 OS パッケージ対応）
- **音声出力** — 再生デバイスを自分で選択（自動選択なし）
- クロスプラットフォーム配布: Windows · macOS · Linux / Ubuntu

---

## 機能

| | |
| :--- | :--- |
| **タイマー** | 学習科学プリセット、短→長休憩、今やる目的は1つ |
| **音楽** | YouTube / Spotify / 直リンク — **作業中のみ**再生 |
| **Focus lock** | 誘惑排除（Windows はフィルム、macOS / Linux は簡易） |
| **言語** | サイドバーで 日本語 / English |
| **更新・音声** | AGIU · 出力デバイス選択 |

詳細: [`docs/platforms.md`](docs/platforms.md) · [`docs/learning-science-jp.md`](docs/learning-science-jp.md)

---

## ソースから起動

```bash
pip install -r requirements.txt
python main.py          # Windows: py main.py
```

### パッケージ作成

```powershell
# Windows
.\scripts\make_release_win.ps1
```

```bash
# macOS / Linux（その OS 上で）
./scripts/make_release_unix.sh
```

---

<p align="center">
  <sub>Aqua Focus · ここな · デスクトップ集中ツール</sub>
</p>
