from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


def patch_workspace() -> None:
    path = "v2_workspace.py"
    s = read(path)
    if "animation-sakura-petals" not in s:
        anchor = '        {"id":"animation-bioluminescence","name_key":"ext_anim_bioluminescence","desc_key":"ext_anim_bioluminescence_desc","type":"animation","builtin":True},\n'
        extra = anchor + (
            '        {"id":"animation-sakura-petals","name_key":"ext_anim_sakura","desc_key":"ext_anim_sakura_desc","type":"animation","builtin":True},\n'
            '        {"id":"animation-rain-window","name_key":"ext_anim_rain","desc_key":"ext_anim_rain_desc","type":"animation","builtin":True},\n'
            '        {"id":"animation-snowfall","name_key":"ext_anim_snow","desc_key":"ext_anim_snow_desc","type":"animation","builtin":True},\n'
            '        {"id":"animation-fireflies","name_key":"ext_anim_fireflies","desc_key":"ext_anim_fireflies_desc","type":"animation","builtin":True},\n'
            '        {"id":"animation-aquarium-fish","name_key":"ext_anim_fish","desc_key":"ext_anim_fish_desc","type":"animation","builtin":True},\n'
        )
        s = replace_once(s, anchor, extra, "builtin scene animations")
    write(path, s)


def patch_i18n() -> None:
    path = "i18n.py"
    s = read(path)
    if "ext_anim_sakura" not in s:
        ja_anchor = '        "ext_anim_bioluminescence_desc": "水中に淡い発光粒子を漂わせます。",\n'
        ja_extra = ja_anchor + (
            '        "ext_anim_sakura": "桜の花びら",\n'
            '        "ext_anim_sakura_desc": "3〜6枚の淡い花びらがゆっくり落ちます。",\n'
            '        "ext_anim_rain": "雨の窓",\n'
            '        "ext_anim_rain_desc": "ガラスを流れるような細い雨粒を少量だけ描きます。",\n'
            '        "ext_anim_snow": "静かな雪",\n'
            '        "ext_anim_snow_desc": "小さな雪が奥行きをもってゆっくり降ります。",\n'
            '        "ext_anim_fireflies": "蛍",\n'
            '        "ext_anim_fireflies_desc": "淡い発光点が夜の背景にゆっくり漂います。",\n'
            '        "ext_anim_fish": "小さな魚影",\n'
            '        "ext_anim_fish_desc": "水面の奥を1〜3匹の小さな魚影が横切ります。",\n'
        )
        s = replace_once(s, ja_anchor, ja_extra, "JA scene animation strings")

        en_anchor = '        "ext_anim_bioluminescence_desc": "Adds subtle glowing particles drifting underwater.",\n'
        en_extra = en_anchor + (
            '        "ext_anim_sakura": "Sakura Petals",\n'
            '        "ext_anim_sakura_desc": "Three to six soft petals drift downward without crowding the timer.",\n'
            '        "ext_anim_rain": "Rain Window",\n'
            '        "ext_anim_rain_desc": "A small number of thin raindrops slide like glass-window streaks.",\n'
            '        "ext_anim_snow": "Quiet Snow",\n'
            '        "ext_anim_snow_desc": "Small snowflakes fall slowly with depth and low visual noise.",\n'
            '        "ext_anim_fireflies": "Fireflies",\n'
            '        "ext_anim_fireflies_desc": "Soft glowing points drift through darker backgrounds.",\n'
            '        "ext_anim_fish": "Small Fish Shadows",\n'
            '        "ext_anim_fish_desc": "One to three small fish silhouettes cross behind the timer.",\n'
        )
        s = replace_once(s, en_anchor, en_extra, "EN scene animation strings")
    write(path, s)


SCENE_CODE = r'''        # Scene-style animation extensions. These are intentionally sparse and
        # deterministic: no per-frame random generation, low object counts, and
        # simple Canvas primitives so the Focus screen stays smooth.
        if not a.reduce_motion:
            fx = self._focus_phase
            soft_pink = "#f8c8d8"
            rain_blue = "#7fd2e8"
            snow_white = "#f1fbff"
            firefly = "#b8ffcf"
            fish_col = self._blend(t.bg, t.accent, 0.45)

            if a.workspace.extension_enabled("animation-sakura-petals"):
                count = 3 if w < 760 else 5
                for i in range(count):
                    drift = (fx * (0.030 + i * 0.004) + i * 0.187) % 1.18
                    px = w * (0.14 + ((i * 0.219) % 0.72)) + math.sin(fx * 1.15 + i) * (22 + i * 3)
                    py = drift * h - h * 0.12
                    size = max(4.0, min(10.0, h * 0.006 + (i % 3)))
                    angle = math.sin(fx * 1.8 + i) * size * 0.42
                    fill = self._blend(soft_pink, t.bg, 0.12)
                    c.create_oval(px-size, py-size*0.55, px+size, py+size*0.55, fill=fill, outline="")
                    c.create_line(px-angle, py, px+angle, py, fill=self._blend(soft_pink, t.text, 0.12), width=1)

            if a.workspace.extension_enabled("animation-rain-window"):
                count = 8 if w < 900 else 12
                for i in range(count):
                    base = (i * 0.097 + fx * (0.11 + i * 0.004)) % 1.0
                    px = w * ((i * 0.137) % 1.0)
                    py = h * base
                    length = 22 + (i % 4) * 9
                    slant = 5 + (i % 3) * 2
                    c.create_line(px, py, px+slant, py+length, fill=self._blend(t.bg, rain_blue, 0.36), width=1)
                    if i % 4 == 0:
                        c.create_oval(px-1.2, py+length-1.2, px+1.2, py+length+1.2, fill=self._blend(t.bg, rain_blue, 0.46), outline="")

            if a.workspace.extension_enabled("animation-snowfall"):
                count = 6 if w < 900 else 10
                for i in range(count):
                    fall = (fx * (0.018 + i * 0.002) + i * 0.113) % 1.15
                    px = w * ((i * 0.173 + 0.08) % 1.0) + math.sin(fx * 0.75 + i) * 13
                    py = fall * h - h * 0.10
                    r = 1.5 + (i % 4) * 0.45
                    c.create_oval(px-r, py-r, px+r, py+r, fill=self._blend(t.bg, snow_white, 0.70), outline="")

            if a.workspace.extension_enabled("animation-fireflies"):
                count = 4 if w < 900 else 7
                for i in range(count):
                    px = w * (0.16 + ((i * 0.191) % 0.68)) + math.sin(fx * 0.88 + i * 1.7) * 24
                    py = h * (0.24 + ((i * 0.147) % 0.54)) + math.sin(fx * 0.62 + i) * 16
                    pulse = 0.45 + 0.35 * (0.5 + 0.5 * math.sin(fx * 2.1 + i))
                    r = 1.4 + (i % 3) * 0.45
                    glow = self._blend(t.bg, firefly, pulse)
                    c.create_oval(px-r*3, py-r*3, px+r*3, py+r*3, fill=self._blend(t.bg, glow, 0.30), outline="")
                    c.create_oval(px-r, py-r, px+r, py+r, fill=glow, outline="")

            if a.workspace.extension_enabled("animation-aquarium-fish"):
                count = 1 if w < 800 else 2
                for i in range(count):
                    swim = (fx * (0.020 + i * 0.006) + i * 0.41) % 1.25
                    direction = -1 if i % 2 else 1
                    px = (swim * (w + 180) - 90) if direction > 0 else (w + 90 - swim * (w + 180))
                    py = h * (0.58 + i * 0.13) + math.sin(fx * 0.85 + i) * 11
                    body = 10 + i * 2
                    c.create_oval(px-body, py-body*0.48, px+body, py+body*0.48, fill=fish_col, outline="")
                    tail = body * 0.72
                    if direction > 0:
                        c.create_polygon(px-body, py, px-body-tail, py-tail*0.55, px-body-tail, py+tail*0.55, fill=fish_col, outline="")
                    else:
                        c.create_polygon(px+body, py, px+body+tail, py-tail*0.55, px+body+tail, py+tail*0.55, fill=fish_col, outline="")

'''


def patch_minimal() -> None:
    path = "v2_minimal.py"
    s = read(path)
    if "animation-sakura-petals" not in s:
        anchor = "        cx, cy = w / 2, h * 0.40\n"
        s = replace_once(s, anchor, SCENE_CODE + anchor, "scene animation draw block")
    write(path, s)


def patch_docs() -> None:
    path = "docs/release/v2.1.6.md"
    p = ROOT / path
    if not p.exists():
        return
    s = p.read_text(encoding="utf-8")
    if "Sakura Petals" in s and "Rain Window" in s:
        return
    anchor = "- 深海の光線 / deep light shafts\n"
    extra = anchor + (
        "- 桜の花びら / Sakura Petals\n"
        "- 雨の窓 / Rain Window\n"
        "- 静かな雪 / Quiet Snow\n"
        "- 蛍 / Fireflies\n"
        "- 小さな魚影 / Small Fish Shadows\n"
    )
    s = replace_once(s, anchor, extra, "release scene animation notes")
    p.write_text(s, encoding="utf-8")


def main() -> int:
    patch_workspace()
    patch_i18n()
    patch_minimal()
    patch_docs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
