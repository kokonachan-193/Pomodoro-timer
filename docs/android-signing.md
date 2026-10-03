# Android release signing

This project builds Android APKs through GitHub Actions. Aqua Focus v2.1.7 supports stable release signing without committing secrets to the repository.

## Why signing matters

Android identifies the app publisher and update path by the APK signing certificate. A stable release key means:

- users can update from one release APK to the next without uninstalling
- the app can show its signing certificate SHA-256 fingerprint in the footer
- release artifacts can be verified against the uploaded certificate report

Signing does **not** remove every warning shown when installing an APK from outside Google Play. Android can still warn about unknown install sources or sideloading. To reduce those warnings for general users, publish through Google Play or another trusted store.

## Generate a release keystore locally

Run this on a trusted local machine, not inside the repository:

```bash
keytool -genkeypair \
  -v \
  -keystore aquafocus-release.jks \
  -alias aquafocus \
  -keyalg RSA \
  -keysize 4096 \
  -validity 10000 \
  -dname "CN=Kokona, OU=Aqua Focus, O=Kokonachan, L=Tokyo, ST=Tokyo, C=JP"
```

Keep `aquafocus-release.jks` private. Losing it means future APKs cannot update over existing installs signed with that key.

## Add GitHub Secrets

Base64 encode the keystore:

```bash
base64 -w 0 aquafocus-release.jks > aquafocus-release.jks.base64
```

Then add these repository secrets in GitHub:

- `ANDROID_KEYSTORE_BASE64` — content of `aquafocus-release.jks.base64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS` — for example `aquafocus`
- `ANDROID_KEY_PASSWORD`

## Workflow behavior

`.github/workflows/android-build.yml` checks whether all signing secrets exist.

- If configured, it builds a release APK, zipaligns it, signs it with `apksigner`, verifies it, and uploads both the APK and certificate report.
- If not configured, it builds a debug APK fallback so CI remains usable.

The release assets are:

- `AquaFocus-Android-2.1.7.apk`
- `AquaFocus-Android-2.1.7.certs.txt`

## Verification

After downloading the APK, verify the signing certificate:

```bash
apksigner verify --print-certs AquaFocus-Android-2.1.7.apk
```

Compare the SHA-256 digest with `AquaFocus-Android-2.1.7.certs.txt` and the shortened SHA-256 shown in the app footer.
