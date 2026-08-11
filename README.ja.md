# Aqua Focus

**[English](README.md)**

PC 向けポモドーロ。タイマー・Focus 音楽・誘惑排除で作業に戻りやすくします。

**対応 OS:** Windows 11 · Windows 10 · macOS · Ubuntu · Linux

---

## ダウンロード（ビルド不要）

完成版は **[Releases](https://github.com/kokonachan-193/Pomodoro-timer/releases)** から入手できます。落として実行するだけです。

| ファイル | 対象 | 使い方 |
| :--- | :--- | :--- |
| **`AquaFocusSetup-*.exe`** | Windows 10 / 11 | インストーラを実行 |
| **`AquaFocus-Windows-x64.zip`** | Windows 10 / 11 | 解凍 → `AquaFocus.exe` |
| **`AquaFocus-macOS.zip`** | macOS | 解凍 → `AquaFocus.app` を開く |
| **`AquaFocus-Linux-x64.tar.gz`** | Ubuntu / Linux | 展開 → `./AquaFocus` |

全パッケージに ffmpeg 同梱。Linux では必要に応じて `sudo apt install libportaudio2 fonts-noto-cjk`。

バージョンタグ（`v*`）を push すると GitHub Actions が全 OS 向けに自動ビルドして Releases に載せます。

---

## ソースから起動（開発者向け）

```bash
pip install -r requirements.txt
python main.py          # Windows: py main.py
```

詳細: [`docs/platforms.md`](docs/platforms.md)

## 機能

- 学習科学ベースのプリセット・長休憩・目的1つ  
- Focus 音楽（作業中のみ）  
- 誘惑排除（Windows=フィルム / Mac·Linux=前面維持）  
- 言語: 日本語 / English  
