# Aqua Focus Android

Android companion for Aqua Focus v2.1.9.

## Focus visuals

The Android Focus screen uses the same Aqua visual language as desktop, tuned for small touch screens:

- translucent rising water body, not a rising frame
- clamped dual wave surface to avoid broken edges
- underwater caustics
- bubbles
- bioluminescent particles
- Sakura petals
- circular timer guide
- per-effect toggles
- Reduce Motion toggle
- Japanese / English UI

## Included

- Focus / break timer
- 25/5, 50/10 and 90/20 presets
- persistent timer / visual settings
- Android notifications
- touch-first scrolling UI
- responsive sizing for small phones
- Japanese font bundling through CI
- YouTube / direct HTTP audio through Android MediaPlayer
- volume control
- APK signing certificate SHA-256 display in the app footer

## Japanese text rendering

The CI build bundles a Noto Japanese-capable font from `fonts-noto-cjk` into `android/assets/fonts/` before building the APK. At runtime the app tries bundled fonts first, then device system fonts. If no Japanese-capable font can be registered, the app automatically opens in English to avoid tofu/garbled Japanese text.

## Release signing

The GitHub Actions workflow supports stable release signing through repository secrets:

- `ANDROID_KEYSTORE_BASE64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

When those secrets are configured, the workflow builds a release APK, signs it with `apksigner`, verifies it, and uploads `AquaFocus-Android-2.1.9.certs.txt` with the certificate fingerprints.

If the secrets are not configured, the workflow falls back to a debug APK so development builds still work.

> Note: Android may still show a system warning when installing an APK directly from outside Google Play. Signing proves the APK identity and keeps updates consistent, but it does not remove every sideload/install-source warning. To minimize user-facing warnings, distribute through Google Play or another trusted app store with a stable release key.

## Build

```bash
cd android
buildozer android debug
```

GitHub Actions produces:

`AquaFocus-Android-2.1.9.apk`
