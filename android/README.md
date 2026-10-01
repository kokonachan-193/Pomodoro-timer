# Aqua Focus Android

Android-native companion build for Aqua Focus.

## Included

- Focus / break timer
- 25/5, 50/10 and 90/20 presets
- Session counter
- Persistent settings
- Android notifications
- Modern touch-first scrolling UI
- Volume control
- Direct HTTP audio playback
- YouTube audio resolution through yt-dlp + Android MediaPlayer
- Music automatically stops when Focus ends

Spotify URLs are recognized but full-track playback is not provided by Spotify to this app, so the Android build currently prioritizes YouTube and direct audio URLs.

## Build

```bash
cd android
buildozer android debug
```

GitHub Actions builds:

`AquaFocus-Android-1.2.0.apk`
