# Aqua Focus

**[English](README.md)**

PC 向けポモドーロ。タイマー・Focus 音楽・誘惑排除。

**対応 OS:** Windows 11 · Windows 10 · macOS · Ubuntu · Linux

---

## ダウンロードして使う（ビルド不要）

完成版は **`downloads/`** フォルダを渡すだけでOKです（GitHub 不要）。

| パッケージ | OS | 使い方 |
| :--- | :--- | :--- |
| `downloads/Windows/AquaFocusSetup-*.exe` | Windows 10 / 11 | インストーラを実行 |
| `downloads/Windows/AquaFocus-Windows-Portable-*.zip` | Windows 10 / 11 | 解凍 → `AquaFocus.exe` |
| `downloads/macOS/AquaFocus-macOS-*.zip` | macOS | 解凍 → `AquaFocus.app` |
| `downloads/Linux/AquaFocus-Linux-Portable-*.tar.gz` | Ubuntu / Linux | `tar xzf … && ./AquaFocus/AquaFocus` |

Windows 用はこの PC で作成済み。  
**macOS / Linux 用は、その OS 上で一度だけ**次を実行して `downloads/` に入れてください。

```bash
./scripts/make_release_unix.sh
# dist/releases/ の成果物を downloads/macOS または downloads/Linux へ
```

パッケージには ffmpeg 同梱です。

---

## ソースから起動

```bash
pip install -r requirements.txt
python main.py          # Windows: py main.py
```

詳細: [`docs/platforms.md`](docs/platforms.md)

## 機能

- 学習科学プリセット・長休憩・目的1つ  
- Focus 音楽（作業中のみ）  
- 誘惑排除 · 日本語 / English  
