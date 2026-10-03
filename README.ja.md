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
  <a href="https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.10"><strong>Aqua Focus v2.1.10</strong></a>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## ダウンロードして使う

GitHub Release の [**Aqua Focus v2.1.10**](https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.10) から使用するOS向けのパッケージを取得できます。

| **ファイル / File** | **対象 / Platform** | **使い方 / How** |
| :--- | :--- | :--- |
| **AquaFocusSetup-2.1.10.exe** | Windows 10 / 11 | インストーラを実行 / Run the installer |
| **AquaFocus-Windows-Portable-2.1.10.zip** | Windows 10 / 11 | 解凍 → `AquaFocus.exe` / Unzip → `AquaFocus.exe` |
| **AquaFocus-macOS-2.1.10.zip** | macOS | 解凍 → `AquaFocus.app` / Unzip → open `AquaFocus.app` |
| **AquaFocus-Linux-Portable-2.1.10.tar.gz** | Linux | 解凍 → `./AquaFocus/AquaFocus` / Extract → run `./AquaFocus/AquaFocus` |
| **AquaFocus-Ubuntu-Portable-2.1.10.tar.gz** | Ubuntu | Linux版と同じ / Same as Linux build |
| **AquaFocus-Android-2.1.10.apk** | Android 8.0+ / arm64-v8a | APKを端末へインストール / Install the APK on your device |

デスクトップ版は ffmpeg **同梱**。既存版は **AGIU** からGitHub Releasesの更新を確認できます。

Android署名メモ: [`docs/android-signing.md`](docs/android-signing.md)

---

## v2.1.10 の新機能

- **Focus中のアニメーション拡張を見える強さへ修正** — ONにした桜・雨・雪・蛍・魚・泡・粒子が、濃い背景画像の上でも分かるように数・速度・明るさを上げました。
- **拡張ON/OFFの即時反映を強化** — `extensions.json` をFocus中にも再読込し、保存直後に複数回再描画して、切り替えが無反応に見える状態を減らします。
- **Reduce Motionでも完全には消えない** — 動きは抑えつつ、ON状態が分かる静かなFX表示を残します。
- **Focus描画の上位FXレイヤーを追加** — 既存の落ち着いたAqua描画を残しつつ、拡張アニメーションだけを別レイヤーで重ねて表示します。
- **v2.1.9のインストーラ版数固定も修正済み** — Inno SetupへVERSIONを渡し、`AquaFocusSetup-2.1.10.exe` が正しく生成されるようにしました。
- **AGIUの現在版を更新** — デスクトップ更新機能がv2.1.10を現在版として扱います。
- **Android 2.1.10配布対応** — Buildozer版数、GitHub Actions成果物名、Release添付先をv2.1.10へ統一しました。

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
