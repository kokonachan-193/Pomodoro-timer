# Aqua Focus

<p align="center">
  <img src="assets/icons/aqua-focus-app.png" alt="Aqua Focus" width="96" />
</p>

<p align="center">
  <strong>Descend into focus.</strong><br />
  海底へ潜るように集中するワークスペース — タイマー・音楽・タスク・環境音・統計・拡張機能。
</p>

<p align="center">
  <a href="README.md">English</a>
  ·
  <b>v2.1.2</b>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## ダウンロードして使う

GitHub Release から使用するOS向けのパッケージを取得できます。

| プラットフォーム | パッケージ | 使い方 |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-2.1.2.exe` | インストーラ · おすすめ |
| **Windows** | `AquaFocus-Windows-Portable-2.1.2.zip` | 解凍 → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-2.1.2.zip` | 解凍 → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-2.1.2.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |
| **Android 8+** | `AquaFocus-Android-2.1.2.apk` | APKをインストール |

デスクトップ版は ffmpeg **同梱**。既存版は **AGIU** からGitHub Releasesの更新を確認できます。

---

## v2.1.2 の新機能

- **Home二重描画を修正** — 起動時にHomeが2回生成されていた原因を修正し、テーマ変更でも色違いの画面が縦に積み上がらなくなりました
- **UIマウントを安全化** — 再構築前に古いsurfaceを必ず破棄し、ゴースト表示を防止
- **本格レスポンシブ化** — Compact / Normal / Wide / Ultra の段階で、小画面でも大画面でもカード幅・余白・文字サイズを自動調整
- **機能導線を復元** — Tasks / Stats / Extensions / Music Library / Soundscape / Countdown / Stopwatch / Alarm / Custom Session を `…` に整理
- **Settingsを復元** — Theme / Reduce Motion / 背景画像 / 言語 / 音声出力 / Focus Lock / 除外設定 / 更新設定を整理して戻しました
- **Full controls** — 旧画面にあった全機能を `… → Full controls` からそのまま利用可能
- **Music Library追加** — プレイリストの追加・再生・削除をモダン画面から操作可能
- **大画面の見え方も改善** — 4K/大型画面で中央カードだけ極端に小さくならないよう調整

### v2.0.0 から継続

- **Deep Sea UI** — 海中の光、泡、ガラス風カード、深海カラーの新GUI
- **Quick Dive** — Focus / Deep Dive / Countdown / Stopwatch / Alarm をまとめて起動
- **Deep Dive** — 90分の低刺激・没入集中モード
- **Coral Tasks** — タスク保存、完了管理、集中時間の自動紐付け
- **Abyss Stats** — 今日・週間・累計、7日チャート、最近の集中履歴
- **Ocean Soundscape** — 音楽とは独立した Ocean / Rain / Brown Noise 環境音
- **Reef Extensions** — オンライン拡張カタログの基盤
- **Reduce Motion** — アニメーションを抑える設定
- **音楽再生安定化** — v1.2の yt-dlp / ffmpeg 改善を継承
- **クロスプラットフォーム** — Windows / macOS / Linux / Ubuntu / Android

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
  <sub>Aqua Focus · ここな · Deep Sea focus workspace</sub>
</p>
