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
  <a href="https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.9"><strong>Aqua Focus v2.1.9</strong></a>
  ·
  Windows · macOS · Ubuntu · Linux · Android
</p>

---

## ダウンロードして使う

GitHub Release の [**Aqua Focus v2.1.9**](https://github.com/kokonachan-193/Pomodoro-timer/releases/tag/v2.1.9) から使用するOS向けのパッケージを取得できます。

| **ファイル / File** | **対象 / Platform** | **使い方 / How** |
| :--- | :--- | :--- |
| **AquaFocusSetup-2.1.9.exe** | Windows 10 / 11 | インストーラを実行 / Run the installer |
| **AquaFocus-Windows-Portable-2.1.9.zip** | Windows 10 / 11 | 解凍 → `AquaFocus.exe` / Unzip → `AquaFocus.exe` |
| **AquaFocus-macOS-2.1.9.zip** | macOS | 解凍 → `AquaFocus.app` / Unzip → open `AquaFocus.app` |
| **AquaFocus-Linux-Portable-2.1.9.tar.gz** | Linux | 解凍 → `./AquaFocus/AquaFocus` / Extract → run `./AquaFocus/AquaFocus` |
| **AquaFocus-Ubuntu-Portable-2.1.9.tar.gz** | Ubuntu | Linux版と同じ / Same as Linux build |
| **AquaFocus-Android-2.1.9.apk** | Android 8.0+ / arm64-v8a | APKを端末へインストール / Install the APK on your device |

デスクトップ版は ffmpeg **同梱**。既存版は **AGIU** からGitHub Releasesの更新を確認できます。

Android署名メモ: [`docs/android-signing.md`](docs/android-signing.md)

---

## v2.1.9 の新機能

- **v2.1.6と同じRelease形式に整理** — Windowsインストーラ、Windowsポータブル、macOS、Linux、Ubuntu、Android APKの6成果物をRelease本文の表へ明記します。
- **GUI安定化を強化** — リサイズ連打、テーマ再構築、Focus停止、コンパクト画面切替で古いTk/CTk widget参照を触りにくくしました。
- **Focus描画の安全フォールバック** — アニメーション描画で例外が出ても、空白や半端な描画で止まらず、最低限のAqua背景へ復帰します。
- **アニメーション拡張の即時反映を継続補強** — `extensions.json` をFocus中にも再読込し、インストール/削除後に再起動なしで反映します。
- **Focus時計と操作UIの再配置補正** — update tick後にも時計サイズ・Focus操作ボタンを再スケールして、巨大化や位置ズレを抑えます。
- **AGIUの現在版を更新** — デスクトップ更新機能がv2.1.9を現在版として扱います。
- **Android 2.1.9配布対応** — Buildozer版数、GitHub Actions成果物名、Release添付先をv2.1.9へ統一しました。

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
