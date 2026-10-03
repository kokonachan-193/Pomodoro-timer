# Aqua Focus

<p align="center">
  <img src="assets/icons/aqua-focus-app.png" alt="Aqua Focus" width="96" />
</p>

<p align="center">
  <strong>Descend into focus.</strong><br />
  シンプルでモダンなポモドーロ集中ワークスペース — 集中・さりげない演出・音楽・タスク・統計・拡張機能。
</p>

<p align="center">
  <a href="README.md">English</a>
  ·
  <a href="https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.8"><strong>Aqua Focus v2.1.8</strong></a>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## ダウンロードして使う

GitHub Release の [**Aqua Focus v2.1.8**](https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.8) から使用するOS向けのパッケージを取得できます。

| プラットフォーム | パッケージ | 使い方 |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-2.1.8.exe` | インストーラ · おすすめ |
| **Windows** | `AquaFocus-Windows-Portable-2.1.8.zip` | 解凍 → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-2.1.8.zip` | 解凍 → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-2.1.8.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |
| **Android 8+** | `AquaFocus-Android-2.1.7.apk` | APKをインストール |

デスクトップ版は ffmpeg **同梱**。既存版は **AGIU** からGitHub Releasesの更新を確認できます。

Android署名メモ: [`docs/android-signing.md`](docs/android-signing.md)

---

## v2.1.8 の新機能

- **PC版のアニメーション拡張をFocus中に即時反映** — Extensionsでアニメーションをインストール/削除した時、Focus画面を再起動しなくても描画へ反映します。
- **拡張状態をFocus中にも再読込** — `extensions.json` の更新を描画中に検知し、インストール/削除状態が無視される問題を軽減しました。
- **削除したアニメーションを勝手に復活させない** — 組み込みアニメーションは初回起動時だけ登録し、その後のユーザー操作を尊重します。
- **GUI表示バグ対策** — リサイズ・テーマ再構築・Focus停止時に古いTk/CTk widget参照を触って表示が崩れるケースをガードしました。
- **Focus時計の固定サイズ戻り対策** — v3 Focus画面で毎tick巨大フォントへ戻る挙動を抑え、画面サイズに応じた表示を維持します。
- **通常起動/配布版の両対応** — `sitecustomize.py` は `python main.py` 用、`pyinstaller_runtime_hook.py` は配布ビルド用に同じ修正を読み込みます。
- **ビルド/Releaseをv2.1.8へ更新** — デスクトップGitHub Actionsの配布物名とRelease先をv2.1.8へ揃えました。

### v2.1.7 Androidから継続

- Android日本語フォント同梱と文字化け回避。
- AndroidレスポンシブFocus UIと入力欄フォーカス崩れ対策。
- Android波演出の安定化、桜演出、APK署名ワークフロー。

---

## 主な機能

| 分類 | 内容 |
| :--- | :--- |
| **集中** | ポモドーロ、25/5・50/10・90/20、長休憩、セッション目的 |
| **モード** | Focus · Deep Dive · Countdown · Stopwatch · Blue Alarm |
| **音楽** | YouTube / Spotifyマッチ / 直リンク、プレイリスト、音声出力選択 |
| **環境音** | Ocean · Rain · Brown Noise |
| **タスク** | 保存、完了、集中分数の自動記録 |
| **統計** | 日・週・累計、最近のセッション、7日チャート |
| **拡張** | オンラインカタログ + インストール管理基盤 |
| **誘惑排除** | デスクトップ Focus lock |
| **快適性** | Reduce Motion / Calm Focus |
| **更新** | AGIU |

詳細仕様: [`docs/aqua-focus-v2-concept.md`](docs/aqua-focus-v2-concept.md)

---

## ソースから起動

```bash
pip install -r requirements.txt
python main.py
```

### パッケージ作成

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
  <sub>Aqua Focus · ここな · Modern Pomodoro focus workspace</sub>
</p>
