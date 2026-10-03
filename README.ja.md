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
  <b>v2.1.7</b>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## ダウンロードして使う

GitHub Release から使用するOS向けのパッケージを取得できます。

| プラットフォーム | パッケージ | 使い方 |
| :--- | :--- | :--- |
| **Windows 10 / 11** | `AquaFocusSetup-2.1.7.exe` | インストーラ · おすすめ |
| **Windows** | `AquaFocus-Windows-Portable-2.1.7.zip` | 解凍 → `AquaFocus.exe` |
| **macOS** | `AquaFocus-macOS-2.1.7.zip` | 解凍 → `AquaFocus.app` |
| **Ubuntu / Linux** | `AquaFocus-*-Portable-2.1.7.tar.gz` | `tar xzf … && ./AquaFocus/AquaFocus` |
| **Android 8+** | `AquaFocus-Android-2.1.7.apk` | APKをインストール |

デスクトップ版は ffmpeg **同梱**。既存版は **AGIU** からGitHub Releasesの更新を確認できます。

Android署名メモ: [`docs/android-signing.md`](docs/android-signing.md)

---

## v2.1.7 の新機能

- **Android日本語文字化け修正** — Androidビルドで Noto 日本語対応フォントを同梱し、端末フォントより先に登録します。
- **未対応端末の安全フォールバック** — 日本語対応フォントを読み込めない場合、豆腐表示や文字化けを避けるためAndroid版は英語UIで起動します。
- **AndroidレスポンシブUI** — スマホ画面サイズに合わせて余白、時計サイズ、ボタン高、Focus描画領域を可変化しました。
- **入力欄フォーカス崩れ対策** — Androidでは `Window.softinput_mode = "pan"` を使い、キーボード表示時に画面が壊れにくいようにしました。
- **Focus演出の波を安定化** — 水面・波メッシュを画面内に制限し、端や上下で波が破綻しないようにしました。
- **桜の花びら + Reduce Motion** — 軽量な桜演出を追加し、動きが強い場合はReduce Motionで抑えられます。
- **APK署名ワークフロー** — GitHub Secretsが設定されている場合、Actionsでrelease APKを署名し、証明書フィンガープリントを添付します。
- **署名情報表示** — Androidアプリ下部にAPK署名証明書のSHA-256短縮表示を追加しました。

### v2.1.4 / v2.1.6 から継続

- **レスポンシブ化** — 小さい画面では重いサイドバーを「破壊せず隠す」、大画面・ウルトラワイドではカードを横に伸ばしすぎない構成。
- **機能は削除しない** — Quick Dive、時間設定、目的、音楽、プレイリスト、音量、Tasks、Stats、環境音、拡張、Focus Lock、更新、テーマ、背景設定を維持。
- **••• に整理** — 低頻度・高度な設定だけをコンパクトなメニューへ移し、ホームの情報量を減らしつつ到達性は維持。
- **集中中の曲操作を復元** — フォーカス画面から曲追加・前後移動・スキップなどへ入れるメニューを常時アクセス可能にしました。
- **水位上昇アニメーション** — 集中の経過に合わせて水面がゆっくり上がる演出を追加。Reduce Motion時は揺れを止めます。

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
