[app]
title = Aqua Focus
package.name = aquafocus
package.domain = com.kokonachan
source.dir = .
source.include_exts = py,png,jpg,kv,json,ttf,otf,ttc
source.include_patterns = assets/fonts/*
version = 2.1.7
android.numeric_version = 217
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,pyjnius,yt-dlp,plyer
orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 26
android.ndk = 27c
# Build modern Android only. The previous armeabi-v7a target failed while
# cross-linking OpenSSL, and Android 8+ devices are overwhelmingly arm64.
android.archs = arm64-v8a
android.permissions = INTERNET,WAKE_LOCK,POST_NOTIFICATIONS,FOREGROUND_SERVICE
android.accept_sdk_license = True
android.private_storage = True
android.release_artifact = apk
p4a.bootstrap = sdl2
log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
