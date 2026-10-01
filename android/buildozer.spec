[app]
title = Aqua Focus
package.name = aquafocus
package.domain = com.kokonachan
source.dir = .
source.include_exts = py,png,jpg,kv,json
version = 2.1.4
requirements = python3==3.11.9,hostpython3==3.11.9,kivy==2.3.1,pyjnius,yt-dlp,plyer
orientation = portrait
fullscreen = 0
android.api = 35
android.minapi = 26
android.ndk = 27c
android.archs = arm64-v8a, armeabi-v7a
android.permissions = INTERNET,WAKE_LOCK,POST_NOTIFICATIONS,FOREGROUND_SERVICE
android.accept_sdk_license = True
android.private_storage = True
p4a.bootstrap = sdl2
log_level = 2
warn_on_root = 1

[buildozer]
log_level = 2
warn_on_root = 1
