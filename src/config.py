import os
import re
import json
import subprocess
from pathlib import Path
from typing import Tuple, Dict, Any, Optional

from .version import APP_VERSION

CURRENT_VERSION = APP_VERSION
DISCORD_CLIENT_ID = "1437470271895376063"
DISCORD_LOGO_URL = "https://i.postimg.cc/DydJfKY3/logo.gif"
DISCORD_LOGO_TEXT = f"ani-cli-arabic {APP_VERSION}"
MYANIMELIST_API_BASE = "https://api.jikan.moe/v4/anime/"

DEFAULT_HEADER_ART = """█▀█ █▄ █ █   █▀▀ █   █   █▀█ █▀▄
█▀█ █ ▀█ █   █▄▄ █▄▄ █   █▀█ █▀▄"""

MINIMAL_ASCII_ART = r"""
_           _         ___             
 ___ ____  (_)_______/ (_)______ _____
/ _ `/ _ \/ /___/ __/ / /___/ _ `/ __/
\_,_/_//_/_/    \__/_/_/    \_,_/_/   
"""

GOODBYE_ART = r"""
 _             _ 
| |__ _  _ ___| |
| '_ \ || / -_)_|
|_.__/\_, \___(_)
      |__/       
"""

# Base Theme definitions
THEMES: Dict[str, Dict[str, str]] = {
    "blue": {"border": "#7eb3d4", "title": "#9ac9e3", "prompt": "#7eb3d4", "loading_spinner": "#9ac9e3", "highlight_fg": "#1a2332", "highlight_bg": "#7eb3d4", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#7eb3d4"},
    "red": {"border": "#d97979", "title": "#e59393", "prompt": "#d97979", "loading_spinner": "#e59393", "highlight_fg": "#2b1a1a", "highlight_bg": "#d97979", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#d97979"},
    "green": {"border": "#8ba87f", "title": "#a3ba98", "prompt": "#8ba87f", "loading_spinner": "#a3ba98", "highlight_fg": "#1a2318", "highlight_bg": "#8ba87f", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#8ba87f"},
    "purple": {"border": "#a88dbd", "title": "#bda3cf", "prompt": "#a88dbd", "loading_spinner": "#bda3cf", "highlight_fg": "#1f1a28", "highlight_bg": "#a88dbd", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#a88dbd"},
    "cyan": {"border": "#7ebfbf", "title": "#9bd3d3", "prompt": "#7ebfbf", "loading_spinner": "#9bd3d3", "highlight_fg": "#1a2828", "highlight_bg": "#7ebfbf", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#7ebfbf"},
    "yellow": {"border": "#d9c379", "title": "#e5d193", "prompt": "#d9c379", "loading_spinner": "#e5d193", "highlight_fg": "#2b2618", "highlight_bg": "#d9c379", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#d9c379"},
    "pink": {"border": "#d9a3ba", "title": "#e5b8cd", "prompt": "#d9a3ba", "loading_spinner": "#e5b8cd", "highlight_fg": "#2b1a24", "highlight_bg": "#d9a3ba", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#d9a3ba"},
    "orange": {"border": "#d9a379", "title": "#e5b693", "prompt": "#d9a379", "loading_spinner": "#e5b693", "highlight_fg": "#2b1f18", "highlight_bg": "#d9a379", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#d9a379"},
    "teal": {"border": "#6b9a9a", "title": "#85b0b0", "prompt": "#6b9a9a", "loading_spinner": "#85b0b0", "highlight_fg": "#182424", "highlight_bg": "#6b9a9a", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#6b9a9a"},
    "magenta": {"border": "#c77eb8", "title": "#d79acd", "prompt": "#c77eb8", "loading_spinner": "#d79acd", "highlight_fg": "#281a26", "highlight_bg": "#c77eb8", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#c77eb8"},
    "lime": {"border": "#a3ba8d", "title": "#b7cba3", "prompt": "#a3ba8d", "loading_spinner": "#b7cba3", "highlight_fg": "#1f261a", "highlight_bg": "#a3ba8d", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#a3ba8d"},
    "coral": {"border": "#d99382", "title": "#e5a899", "prompt": "#d99382", "loading_spinner": "#e5a899", "highlight_fg": "#2b1d1a", "highlight_bg": "#d99382", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#d99382"},
    "lavender": {"border": "#b4a8cf", "title": "#c8bedd", "prompt": "#b4a8cf", "loading_spinner": "#c8bedd", "highlight_fg": "#211e2b", "highlight_bg": "#b4a8cf", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#b4a8cf"},
    "gold": {"border": "#c9b87f", "title": "#d9ca98", "prompt": "#c9b87f", "loading_spinner": "#d9ca98", "highlight_fg": "#292418", "highlight_bg": "#c9b87f", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#c9b87f"},
    "mint": {"border": "#8dbaa3", "title": "#a3cbb7", "prompt": "#8dbaa3", "loading_spinner": "#a3cbb7", "highlight_fg": "#1a2621", "highlight_bg": "#8dbaa3", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#8dbaa3"},
    "rose": {"border": "#d97ea8", "title": "#e599bd", "prompt": "#d97ea8", "loading_spinner": "#e599bd", "highlight_fg": "#2b1a23", "highlight_bg": "#d97ea8", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#d97ea8"},
    "sunset": {"border": "#e48b7a", "title": "#f0a19a", "prompt": "#e48b7a", "loading_spinner": "#f0a19a", "highlight_fg": "#0a1220", "highlight_bg": "#e48b7a", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#d97979", "ascii": "#e48b7a"},
}

def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 8:
        hex_str = hex_str[2:] if hex_str.startswith(('ff', 'FF')) else hex_str[:6]
    elif len(hex_str) == 3:
        hex_str = "".join(c * 2 for c in hex_str)
    return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(r: int, g: int, b: int) -> str:
    return f"#{max(0, min(255, r)):02x}{max(0, min(255, g)):02x}{max(0, min(255, b)):02x}"

def lighten_color(hex_str: str, factor: float = 0.22) -> str:
    try:
        r, g, b = hex_to_rgb(hex_str)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return rgb_to_hex(r, g, b)
    except Exception:
        return hex_str

def get_contrast_text(hex_str: str) -> str:
    try:
        r, g, b = hex_to_rgb(hex_str)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#111827" if luminance > 0.58 else "#ffffff"
    except Exception:
        return "#ffffff"

def create_theme_from_accent(accent: str) -> Dict[str, str]:
    accent = accent.lower()
    title_col = lighten_color(accent, 0.22)
    subtitle_col = lighten_color(accent, 0.35)
    spinner_col = lighten_color(accent, 0.28)
    fg_col = get_contrast_text(accent)
    return {
        "border": accent,
        "title": title_col,
        "subtitle": subtitle_col,
        "prompt": accent,
        "loading_spinner": spinner_col,
        "highlight_fg": fg_col,
        "highlight_bg": accent,
        "primary_text": "#FFFFFF",
        "secondary_text": "#888888",
        "error": "#d97979",
        "ascii": accent,
    }

def detect_system_theme() -> Dict[str, str]:
    """
    Intelligently auto-detect desktop theme & accent color across:
    1. Omarchy Desktop Environment (colors.toml / custom themes / theme.name)
    2. Freedesktop / XDG Desktop Portal (org.freedesktop.appearance accent-color)
    3. Hyprland active border color (general:col.active_border)
    4. GNOME / Ubuntu / GTK system accent color (gsettings)
    5. KDE Plasma accent color (kdeglobals)
    6. Pywal / Wallust dynamic colors (~/.cache/wal/colors.json)
    7. Terminal palette (foot, kitty, alacritty)
    """
    home = Path.home()

    # 1. Omarchy Current Theme colors.toml
    omarchy_colors = home / ".config" / "omarchy" / "current" / "theme" / "colors.toml"
    if omarchy_colors.exists():
        try:
            content = omarchy_colors.read_text(encoding="utf-8")
            m = re.search(r'accent\s*=\s*["\'](#?[0-9a-fA-F]{6,8})["\']', content)
            if m:
                r, g, b = hex_to_rgb(m.group(1))
                return create_theme_from_accent(rgb_to_hex(r, g, b))
        except Exception:
            pass

    # 1b. Omarchy Theme Name matching
    omarchy_name_file = home / ".config" / "omarchy" / "current" / "theme.name"
    if omarchy_name_file.exists():
        try:
            t_name = omarchy_name_file.read_text(encoding="utf-8").strip().lower()
            name_map = {
                "tokyo-night": "#7aa2f7", "catppuccin": "#cba6f7", "catppuccin-latte": "#8839ef",
                "nord": "#88c0d0", "gruvbox": "#d79921", "rose-pine": "#ebbcba",
                "kanagawa": "#7e9cd8", "everforest": "#a7c080", "amberbyte": "#d66b6b",
                "odyssey": "#7eb3d4", "hackerman": "#00ff66", "matte-black": "#d9d9d9",
                "vantablack": "#d97979", "miasma": "#78a978"
            }
            if t_name in name_map:
                return create_theme_from_accent(name_map[t_name])
        except Exception:
            pass

    # 2. XDG Desktop Portal (Freedesktop Standard D-Bus query)
    try:
        proc = subprocess.run(
            ["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
             "--object-path", "/org/freedesktop/portal/desktop",
             "--method", "org.freedesktop.portal.Settings.Read",
             "org.freedesktop.appearance", "accent-color"],
            capture_output=True, text=True, timeout=1
        )
        if proc.returncode == 0 and proc.stdout:
            nums = re.findall(r"([0-9]*\.[0-9]+|[0-9]+)", proc.stdout)
            if len(nums) >= 3:
                r, g, b = [int(float(x) * 255) for x in nums[:3]]
                return create_theme_from_accent(rgb_to_hex(r, g, b))
    except Exception:
        pass

    # 3. Hyprland active border color
    try:
        proc = subprocess.run(["hyprctl", "getoption", "general:col.active_border", "-j"], capture_output=True, text=True, timeout=1)
        if proc.returncode == 0 and proc.stdout:
            data = json.loads(proc.stdout)
            custom_str = data.get("custom", "")
            hex_match = re.search(r"(?:rgba\()?([0-9a-fA-F]{6,8})", custom_str)
            if hex_match:
                r, g, b = hex_to_rgb(hex_match.group(1))
                return create_theme_from_accent(rgb_to_hex(r, g, b))
    except Exception:
        pass

    # 4. GNOME / GTK settings
    try:
        proc = subprocess.run(["gsettings", "get", "org.gnome.desktop.interface", "accent-color"], capture_output=True, text=True, timeout=1)
        if proc.returncode == 0 and proc.stdout:
            accent_name = proc.stdout.strip().strip("'").lower()
            gnome_map = {
                "blue": "#3584e4", "teal": "#2190a4", "green": "#3a944a",
                "yellow": "#c88800", "orange": "#ed5b00", "red": "#e62d42",
                "pink": "#d56199", "purple": "#9141ac", "slate": "#6f8396"
            }
            if accent_name in gnome_map:
                return create_theme_from_accent(gnome_map[accent_name])
    except Exception:
        pass

    # 5. KDE Plasma kdeglobals
    kdeglobals = home / ".config" / "kdeglobals"
    if kdeglobals.exists():
        try:
            content = kdeglobals.read_text(encoding="utf-8")
            m = re.search(r"(?:AccentColor|BackgroundNormal)\s*=\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)", content)
            if m:
                r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
                return create_theme_from_accent(rgb_to_hex(r, g, b))
        except Exception:
            pass

    # 6. Pywal cache
    wal_colors = home / ".cache" / "wal" / "colors.json"
    if wal_colors.exists():
        try:
            data = json.loads(wal_colors.read_text(encoding="utf-8"))
            accent = data.get("colors", {}).get("color4") or data.get("special", {}).get("accent")
            if accent:
                r, g, b = hex_to_rgb(accent)
                return create_theme_from_accent(rgb_to_hex(r, g, b))
        except Exception:
            pass

    return THEMES["blue"]

def load_user_theme():
    """Load theme name from config.json, defaulting to auto."""
    try:
        home_dir = Path.home()
        config_file = home_dir / ".ani-cli-arabic" / "database" / "config.json"
        
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                return config.get("theme", "auto")
    except (IOError, json.JSONDecodeError, KeyError):
        pass
    return "auto"

selected_theme = load_user_theme()

# Inject dynamic auto theme
THEMES["auto"] = detect_system_theme()

theme_colors = THEMES.get(selected_theme, THEMES["auto"])

HEADER_ART = DEFAULT_HEADER_ART
COLOR_ASCII = theme_colors.get("ascii", "#8BD218")
COLOR_BORDER = theme_colors.get("border", "#8BD218")
COLOR_TITLE = theme_colors.get("title", "#8BD218")
COLOR_SUBTITLE = theme_colors.get("subtitle", lighten_color(theme_colors.get("border", "#8BD218"), 0.35))
COLOR_PROMPT = theme_colors.get("prompt", "#8BD218")
COLOR_LOADING_SPINNER = theme_colors.get("loading_spinner", "#8BD218")
COLOR_HIGHLIGHT_FG = theme_colors.get("highlight_fg", "#000000")
COLOR_HIGHLIGHT_BG = theme_colors.get("highlight_bg", "#8BD218")
COLOR_PRIMARY_TEXT = theme_colors.get("primary_text", "#FFFFFF")
COLOR_SECONDARY_TEXT = theme_colors.get("secondary_text", "#888888")
COLOR_ERROR = theme_colors.get("error", "#FF0000")

POPULAR_GENRES = [
    {"name_ar": "أكشن", "name_en": "Action", "slug": "action"},
    {"name_ar": "مغامرة", "name_en": "Adventure", "slug": "adventure"},
    {"name_ar": "كوميدي", "name_en": "Comedy", "slug": "comedy"},
    {"name_ar": "دراما", "name_en": "Drama", "slug": "drama"},
    {"name_ar": "خيال", "name_en": "Fantasy", "slug": "fantasy"},
    {"name_ar": "إيسيكاي", "name_en": "Isekai", "slug": "isekai"},
    {"name_ar": "رومانسي", "name_en": "Romance", "slug": "romance"},
    {"name_ar": "خيال علمي", "name_en": "Sci-Fi", "slug": "sci-fi"},
    {"name_ar": "شونين", "name_en": "Shounen", "slug": "shounen"},
    {"name_ar": "الحياة اليومية", "name_en": "Slice of Life", "slug": "slice-of-life"},
    {"name_ar": "خارق للطبيعة", "name_en": "Supernatural", "slug": "supernatural"},
    {"name_ar": "غموض", "name_en": "Mystery", "slug": "mystery"},
    {"name_ar": "تشويق", "name_en": "Suspense", "slug": "suspense"},
    {"name_ar": "رياضي", "name_en": "Sports", "slug": "sports"},
    {"name_ar": "مدرسي", "name_en": "School", "slug": "school"},
    {"name_ar": "سينين", "name_en": "Seinen", "slug": "seinen"},
    {"name_ar": "شوچو", "name_en": "Shoujo", "slug": "shoujo"},
    {"name_ar": "رعب", "name_en": "Horror", "slug": "horror"},
    {"name_ar": "ميكا", "name_en": "Mecha", "slug": "mecha"},
    {"name_ar": "تاريخي", "name_en": "Historical", "slug": "historical"},
    {"name_ar": "قوى خارقة", "name_en": "Super Power", "slug": "super-power"},
    {"name_ar": "سحر", "name_en": "Magic", "slug": "magic"},
    {"name_ar": "أساطير", "name_en": "Mythology", "slug": "mythology"},
    {"name_ar": "عسكري", "name_en": "Military", "slug": "military"},
    {"name_ar": "إيتشي", "name_en": "Ecchi", "slug": "ecchi"},
    {"name_ar": "حريم", "name_en": "Harem", "slug": "harem"},
    {"name_ar": "بطولة راشدين", "name_en": "Adult Cast", "slug": "adult-cast"},
    {"name_ar": "طعام", "name_en": "Gourmet", "slug": "gourmet"},
    {"name_ar": "موسيقى", "name_en": "Music", "slug": "music"},
    {"name_ar": "فضاء", "name_en": "Space", "slug": "space"},
    {"name_ar": "بوليسي", "name_en": "Detective", "slug": "detective"},
    {"name_ar": "سفر عبر الزمن", "name_en": "Time Travel", "slug": "time-travel"},
    {"name_ar": "مصاصي دماء", "name_en": "Vampire", "slug": "vampire"},
    {"name_ar": "سايبربانك", "name_en": "Cyberpunk", "slug": "cyberpunk"},
]

GENRE_NAME_TO_SLUG = {g["name_en"].lower(): g["slug"] for g in POPULAR_GENRES}
GENRE_NAME_TO_SLUG.update({g["name_ar"]: g["slug"] for g in POPULAR_GENRES})

POPULAR_STUDIOS_MAP = {
    "MAPPA": [
        {"id": "jujutsu-kaisen", "title_en": "Jujutsu Kaisen", "title_ar": "جوجيتسو كايسن", "score": "9.19", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300438/1663096538d388.jpg"},
        {"id": "chainsaw-man", "title_en": "Chainsaw Man", "title_ar": "رجل المنشار", "score": "8.51", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301297/1669d92fe19672.jpg"},
        {"id": "jigokuraku", "title_en": "Jigokuraku (Hell's Paradise)", "title_ar": "جنة الجحيم", "score": "8.88", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301389/166fa216c52a0a.jpg"},
        {"id": "dororo", "title_en": "Dororo", "title_ar": "دورورو", "score": "8.95", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/299092/1656e5ca939999.jpg"},
        {"id": "banana-fish", "title_en": "Banana Fish", "title_ar": "سمكة الموز", "score": "8.62", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300439/1663096541f5e8.jpg"},
        {"id": "kakegurui", "title_en": "Kakegurui", "title_ar": "المقامر المحترف", "score": "7.67", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/299088/1656e5c26915e6.jpg"},
        {"id": "zankyou-no-terror", "title_en": "Zankyou no Terror (Terror in Resonance)", "title_ar": "صدى الإرهاب", "score": "8.78", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300440/166309654366aa.jpg"},
        {"id": "vinland-saga-season-2", "title_en": "Vinland Saga Season 2", "title_ar": "ملحمة فينلاند الموسم الثاني", "score": "9.14", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301385/166fa1d927c3d2.jpg"}
    ],
    "ufotable": [
        {"id": "kimetsu-no-yaiba-hashira-geiko-hen", "title_en": "Kimetsu no Yaiba: Hashira Geiko-hen", "title_ar": "قاتل الشياطين: تدريب الهاشيرا", "score": "9.16", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301552/664161869e5d4.jpg"},
        {"id": "kimetsu-no-yaiba-movie-1-mugenjou-hen-akaza-sairai", "title_en": "Kimetsu no Yaiba Movie 1: Mugenjou-hen", "title_ar": "فيلم قاتل الشياطين: قلعة اللانهاية", "score": "9.36", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/301579/66a9870198aa7.jpg"},
        {"id": "kimetsu-no-yaiba-yuukaku-hen", "title_en": "Kimetsu no Yaiba: Yuukaku-hen", "title_ar": "قاتل الشياطين: حي المتعة", "score": "9.28", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300588/166309734dbfa6.jpg"},
        {"id": "kimetsu-no-yaiba-katanakaji-no-sato-hen", "title_en": "Kimetsu no Yaiba: Katanakaji no Sato-hen", "title_ar": "قاتل الشياطين: قرية صانعي السيوف", "score": "9.12", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301386/166fa1ec12cf6f.jpg"},
        {"id": "fate-zero", "title_en": "Fate/Zero", "title_ar": "فيت/زيرو", "score": "8.98", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295679/164e9fc5eec2e6.jpg"},
        {"id": "fate-stay-night-unlimited-blade-works", "title_en": "Fate/stay night: Unlimited Blade Works", "title_ar": "فيت/ستاي نايت", "score": "8.82", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295680/164e9fc93b6641.jpg"}
    ],
    "Madhouse": [
        {"id": "sousou-no-frieren", "title_en": "Sousou no Frieren (Frieren: Beyond Journey's End)", "title_ar": "فريرن: ما بعد نهاية الرحلة", "score": "9.52", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301438/167096057a66bf.jpg"},
        {"id": "hunter-x-hunter-2011", "title_en": "Hunter x Hunter (2011)", "title_ar": "القناص 2011", "score": "9.53", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295670/164e881b6df3ec.jpg"},
        {"id": "death-note", "title_en": "Death Note", "title_ar": "مذكرة الموت", "score": "9.24", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295671/164e881db24177.jpg"},
        {"id": "monster", "title_en": "Monster", "title_ar": "مونستر", "score": "9.27", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295672/164e881fa6a47a.jpg"},
        {"id": "one-punch-man", "title_en": "One Punch Man", "title_ar": "ون بنش مان", "score": "8.73", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295673/164e882205562e.jpg"},
        {"id": "overlord", "title_en": "Overlord", "title_ar": "أوفرلورد", "score": "8.47", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295674/164e8823bcf079.jpg"},
        {"id": "parasyte-the-maxim", "title_en": "Kiseijuu: Sei no Kakuritsu (Parasyte)", "title_ar": "الطفيليات", "score": "8.90", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295675/164e8825c92c53.jpg"}
    ],
    "Wit Studio": [
        {"id": "vinland-saga", "title_en": "Vinland Saga", "title_ar": "ملحمة فينلاند", "score": "9.35", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300441/16630965471415.jpg"},
        {"id": "spy-x-family", "title_en": "Spy x Family", "title_ar": "عائلة الجاسوس", "score": "8.92", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300442/16630965492ff3.jpg"},
        {"id": "ousama-ranking", "title_en": "Ousama Ranking (Ranking of Kings)", "title_ar": "ترتيب الملوك", "score": "8.47", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300443/166309655079a4.jpg"},
        {"id": "great-pretender", "title_en": "Great Pretender", "title_ar": "المحتال العظيم", "score": "8.07", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300444/1663096552bb7a.jpg"},
        {"id": "vivy-fluorite-eyes-song", "title_en": "Vivy: Fluorite Eye's Song", "title_ar": "فيفي: أغنية عين الفلوريت", "score": "8.75", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300445/1663096554b799.jpg"},
        {"id": "owari-no-seraph", "title_en": "Owari no Seraph (Seraph of the End)", "title_ar": "سيراف النهاية", "score": "8.32", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300446/16630965561a0b.jpg"}
    ],
    "Bones": [
        {"id": "fullmetal-alchemist-brotherhood", "title_en": "Fullmetal Alchemist: Brotherhood", "title_ar": "الخيميائي الفولاذي: فل ميتال", "score": "9.58", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295676/164e88295a09c2.jpg"},
        {"id": "mob-psycho-100", "title_en": "Mob Psycho 100", "title_ar": "موب سايكو 100", "score": "8.75", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295677/164e882b7db5b6.jpg"},
        {"id": "bungou-stray-dogs", "title_en": "Bungou Stray Dogs", "title_ar": "كلاب الأدب الضالة", "score": "8.51", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295678/164e882d8c3682.jpg"},
        {"id": "boku-no-hero-academia-7th-season", "title_en": "Boku no Hero Academia 7th Season", "title_ar": "أكاديمية بطلي الموسم السابع", "score": "8.72", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301550/663c0a5996f01.jpg"},
        {"id": "noragami", "title_en": "Noragami", "title_ar": "نوراغامي", "score": "8.68", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295681/164e9fcb9e38d9.jpg"},
        {"id": "soul-eater", "title_en": "Soul Eater", "title_ar": "آكل الأرواح", "score": "8.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295682/164e9fce03f837.jpg"}
    ],
    "Kyoto Animation": [
        {"id": "violet-evergarden-the-movie", "title_en": "Violet Evergarden: The Movie", "title_ar": "فيلم فايوليت إيفرجاردن", "score": "9.42", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/300447/166309655811ca.jpg"},
        {"id": "koe-no-katachi", "title_en": "Koe no Katachi (A Silent Voice)", "title_ar": "صوت صامت", "score": "9.38", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299094/1656e5cfe5e589.jpg"},
        {"id": "hyouka", "title_en": "Hyouka", "title_ar": "هيوكا", "score": "8.75", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300448/16630965600c3b.jpg"},
        {"id": "clannad-after-story", "title_en": "Clannad: After Story", "title_ar": "كلاناد: أفتر ستوري", "score": "9.35", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300449/1663096562095f.jpg"},
        {"id": "kobayashi-san-chi-no-maid-dragon", "title_en": "Kobayashi-san Chi no Maid Dragon", "title_ar": "خادمة الآنسة كوباياشي تنين", "score": "8.62", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300450/1663096563e46c.jpg"},
        {"id": "hibike-euphonium", "title_en": "Hibike! Euphonium", "title_ar": "اعزفي! يوفونيوم", "score": "8.54", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300451/16630965651cb9.jpg"}
    ],
    "Toei Animation": [
        {"id": "one-piece", "title_en": "One Piece", "title_ar": "ون بيس", "score": "9.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/455312/1669d86b4ca885.jpg"},
        {"id": "dragon-ball-super", "title_en": "Dragon Ball Super", "title_ar": "دراغون بول سوبر", "score": "8.42", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295667/164e8817fb0b70.jpg"},
        {"id": "dragon-ball-daima", "title_en": "Dragon Ball Daima", "title_ar": "دراغون بول دايما", "score": "8.25", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301433/167095af89ee2e.jpg"},
        {"id": "slam-dunk", "title_en": "Slam Dunk", "title_ar": "سلام دانك", "score": "9.18", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295683/164e9fd0316687.jpg"},
        {"id": "world-trigger", "title_en": "World Trigger", "title_ar": "مُحفّز العالم", "score": "8.34", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300452/166309656722d3.jpg"},
        {"id": "one-piece-film-red", "title_en": "One Piece Film: Red", "title_ar": "فيلم ون بيس: ريد", "score": "8.50", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299106/1656e690907ff1.jpg"}
    ],
    "Studio Pierrot": [
        {"id": "bleach-sennen-kessen-hen", "title_en": "Bleach: Sennen Kessen-hen", "title_ar": "بليتش: حرب الألف سنة الدموية", "score": "9.48", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301298/1669d93278dafe.jpg"},
        {"id": "naruto-shippuuden", "title_en": "Naruto: Shippuuden", "title_ar": "ناروتو شيبودن", "score": "9.22", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295662/164e88059b3830.jpg"},
        {"id": "black-clover", "title_en": "Black Clover", "title_ar": "بلاك كلوفر", "score": "8.80", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295684/164e9fd268c783.jpg"},
        {"id": "tokyo-ghoul", "title_en": "Tokyo Ghoul", "title_ar": "طوكيو غول", "score": "8.65", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295685/164e9fd48b8c27.jpg"},
        {"id": "yu-yu-hakusho", "title_en": "Yu Yu Hakusho", "title_ar": "يو يو هاكوشو", "score": "8.92", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295686/164e9fd6a8f115.jpg"}
    ],
    "A-1 Pictures": [
        {"id": "solo-leveling-season-2-arise-from-the-shadow", "title_en": "Solo Leveling Season 2", "title_ar": "سولو ليفلينج الموسم الثاني", "score": "9.25", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301594/680517865c345.jpg"},
        {"id": "kaguya-sama-wa-kokurasetai-ultra-romantic", "title_en": "Kaguya-sama: Love Is War", "title_ar": "كاغويا ساما: الحب حرب", "score": "9.35", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300453/166309656976ca.jpg"},
        {"id": "86-part-2", "title_en": "86: Eighty Six Part 2", "title_ar": "86 الجزء الثاني", "score": "9.18", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300454/16630965719cb4.jpg"},
        {"id": "sword-art-online", "title_en": "Sword Art Online", "title_ar": "فن السيف عبر الإنترنت", "score": "8.40", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295687/164e9fd8d6cb7f.jpg"},
        {"id": "shigatsu-wa-kimi-no-uso", "title_en": "Shigatsu wa Kimi no Uso (Your Lie in April)", "title_ar": "كذبتك في أبريل", "score": "9.20", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295688/164e9fdafac244.jpg"},
        {"id": "mashle-magic-and-muscles-the-divine-visionary-candidate-exam-arc", "title_en": "Mashle: Magic and Muscles", "title_ar": "ماكل السحر والعضلات", "score": "8.55", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301512/659e95fa53696.jpg"}
    ],
    "CloverWorks": [
        {"id": "bocchi-the-rock", "title_en": "Bocchi the Rock!", "title_ar": "بوتشي ذا روك", "score": "9.28", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301300/1669d9370b3438.jpg"},
        {"id": "spy-x-family-season-2", "title_en": "Spy x Family Season 2", "title_ar": "عائلة الجاسوس الموسم الثاني", "score": "8.92", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301439/16709607db7a9d.jpg"},
        {"id": "sono-bisque-doll-wa-koi-wo-suru", "title_en": "Sono Bisque Doll wa Koi wo Suru (My Dress-Up Darling)", "title_ar": "فتاتي المرتدية للدمى", "score": "8.80", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300455/1663096573c6a4.jpg"},
        {"id": "yakusoku-no-neverland", "title_en": "Yakusoku no Neverland (The Promised Neverland)", "title_ar": "نيفرلاند الموعودة", "score": "8.95", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300456/1663096575cb27.jpg"},
        {"id": "horimiya", "title_en": "Horimiya", "title_ar": "هوريميا", "score": "8.74", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300457/1663096577884d.jpg"},
        {"id": "wind-breaker", "title_en": "Wind Breaker", "title_ar": "ويند بريكر", "score": "8.65", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301549/663c09ed8d47b.jpg"}
    ],
    "White Fox": [
        {"id": "steinsgate", "title_en": "Steins;Gate", "title_ar": "شتاينز غيت", "score": "9.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295689/164e9fdd3068e1.jpg"},
        {"id": "rezero-kara-hajimeru-isekai-seikatsu-3rd-season", "title_en": "Re:Zero kara Hajimeru Isekai Seikatsu 3rd Season", "title_ar": "ري زيرو الموسم الثالث", "score": "9.20", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301582/66e01a88bb3d3.jpg"},
        {"id": "akame-ga-kill", "title_en": "Akame ga Kill!", "title_ar": "أكامي غا كيل", "score": "8.72", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295691/164e9fdf55f019.jpg"},
        {"id": "goblin-slayer-ii", "title_en": "Goblin Slayer II", "title_ar": "قاتل الغوبلن الجزء الثاني", "score": "8.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301440/1670960a37e199.jpg"},
        {"id": "shinchou-yuusha-kono-yuusha-ga-ore-tueee-kuse-ni-shinchou-sugiru", "title_en": "Cautious Hero", "title_ar": "البطل الحذر", "score": "8.38", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300458/16630965799781.jpg"}
    ],
    "David Production": [
        {"id": "jojo-no-kimyou-na-bouken-part-6-stone-ocean", "title_en": "JoJo no Kimyou na Bouken: Stone Ocean", "title_ar": "مغامرات جوجو العجيبة: ستون أوشن", "score": "9.15", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300459/16630965819777.jpg"},
        {"id": "fire-force", "title_en": "Enen no Shouboutai (Fire Force)", "title_ar": "قوة النار", "score": "8.48", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300460/16630965839912.jpg"},
        {"id": "hataraku-saibou", "title_en": "Hataraku Saibou (Cells at Work!)", "title_ar": "الخلايا تعمل!", "score": "8.40", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300461/1663096585bb34.jpg"},
        {"id": "undead-unluck", "title_en": "Undead Unluck", "title_ar": "أنديد أنلاك", "score": "8.25", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301441/1670960cb7d105.jpg"}
    ],
    "Shaft": [
        {"id": "bakemonogatari", "title_en": "Bakemonogatari", "title_ar": "باكيمونوغاتاري", "score": "9.12", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295692/164e9fe16a809f.jpg"},
        {"id": "mahou-shoujo-madoka-magica", "title_en": "Mahou Shoujo Madoka★Magica", "title_ar": "الفتاة الساحرة مادوكا ماجيكا", "score": "9.05", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295693/164e9fe3845bb2.jpg"},
        {"id": "sangatsu-no-lion", "title_en": "3-gatsu no Lion (March Comes in Like a Lion)", "title_ar": "أسد مارس", "score": "9.22", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300462/1663096587c671.jpg"},
        {"id": "nisekoi", "title_en": "Nisekoi", "title_ar": "نيسيكوي", "score": "8.35", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295694/164e9fe59de290.jpg"}
    ],
    "Trigger": [
        {"id": "dungeon-meshi", "title_en": "Dungeon Meshi (Delicious in Dungeon)", "title_ar": "طعام الدانجون", "score": "8.95", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301511/659e959779df5.jpg"},
        {"id": "cyberpunk-edgerunners", "title_en": "Cyberpunk: Edgerunners", "title_ar": "سايبربانك: إيدجرانرز", "score": "9.20", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301299/1669d934bb0e51.jpg"},
        {"id": "kill-la-kill", "title_en": "Kill la Kill", "title_ar": "كيل لا كيل", "score": "8.82", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295695/164e9fe7cfbb15.jpg"},
        {"id": "little-witch-academia", "title_en": "Little Witch Academia", "title_ar": "أكاديمية الساحرات الصغيرات", "score": "8.50", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300463/1663096589e472.jpg"},
        {"id": "darling-in-the-franxx", "title_en": "Darling in the FranXX", "title_ar": "حبيبي في الفرانكس", "score": "8.40", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295696/164e9fea1a88b1.jpg"}
    ],
    "Production I.G": [
        {"id": "haikyuu", "title_en": "Haikyuu!!", "title_ar": "هايكيو!!", "score": "9.38", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295697/164e9fec39e7c5.jpg"},
        {"id": "kuroko-no-basket", "title_en": "Kuroko no Basket", "title_ar": "كرة سلة كوروكو", "score": "8.95", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295698/164e9fee563e41.jpg"},
        {"id": "psycho-pass", "title_en": "Psycho-Pass", "title_ar": "سايكو باس", "score": "8.90", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295699/164e9ff07f89d3.jpg"},
        {"id": "kaijuu-8-gou", "title_en": "Kaijuu 8-gou (Kaiju No. 8)", "title_ar": "كايجو رقم 8", "score": "8.82", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301551/663c0a876bf66.jpg"},
        {"id": "ao-ashi", "title_en": "Ao Ashi", "title_ar": "آو أشي", "score": "8.65", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300464/1663096591f82e.jpg"}
    ],
    "J.C.Staff": [
        {"id": "toradora", "title_en": "Toradora!", "title_ar": "تورادورا!", "score": "8.85", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295700/164e9ff296fa2b.jpg"},
        {"id": "dungeon-ni-deai-wo-motomeru-no-wa-machigatteiru-darou-ka-v", "title_en": "DanMachi Season 5", "title_ar": "دانماتشي الموسم الخامس", "score": "8.78", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301583/66e01acc4cf91.jpg"},
        {"id": "shokugeki-no-souma", "title_en": "Shokugeki no Souma (Food Wars!)", "title_ar": "صراع الطبخ", "score": "8.80", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295701/164e9ff4b58e72.jpg"},
        {"id": "saiki-kusuo-no-psi-nan", "title_en": "Saiki Kusuo no Ψ-nan", "title_ar": "سايكي كوسو", "score": "8.92", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295702/164e9ff6c738e4.jpg"},
        {"id": "prison-school", "title_en": "Prison School", "title_ar": "مدرسة السجن", "score": "8.25", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295703/164e9ff8e7bc95.jpg"}
    ],
    "TMS Entertainment": [
        {"id": "meitantei-conan", "title_en": "Detective Conan", "title_ar": "المحقق كونان", "score": "9.30", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295704/164e9ffb12c8b7.jpg"},
        {"id": "dr-stone-new-world", "title_en": "Dr. Stone: New World", "title_ar": "دكتور ستون: العالم الجديد", "score": "8.85", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301390/166fa23412cf88.jpg"},
        {"id": "fruits-basket-the-final", "title_en": "Fruits Basket: The Final", "title_ar": "سلة الفواكه: النهاية", "score": "9.40", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300465/1663096593a290.jpg"},
        {"id": "megalo-box", "title_en": "Megalo Box", "title_ar": "ميجالو بوكس", "score": "8.52", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300466/1663096595bf11.jpg"}
    ],
    "Studio Deen": [
        {"id": "kono-subarashii-sekai-ni-shukufuku-wo-3", "title_en": "KonoSuba: God's Blessing on This Wonderful World! 3", "title_ar": "كونوسوبا الموسم الثالث", "score": "9.10", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301548/663c09b6574f1.jpg"},
        {"id": "nanatsu-no-taizai", "title_en": "Nanatsu no Taizai (The Seven Deadly Sins)", "title_ar": "الخطايا السبع المميتة", "score": "8.60", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295705/164e9ffd39e992.jpg"},
        {"id": "higurashi-no-naku-koro-ni", "title_en": "Higurashi no Naku Koro ni", "title_ar": "عندما تبكي حشرات الليل", "score": "8.48", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295706/164e9fff55ec78.jpg"},
        {"id": "sasaki-to-miyano", "title_en": "Sasaki to Miyano", "title_ar": "ساساكي وميانو", "score": "8.42", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300467/1663096597c41f.jpg"}
    ],
    "Lerche": [
        {"id": "ansatsu-kyoushitsu", "title_en": "Ansatsu Kyoushitsu (Assassination Classroom)", "title_ar": "فصل الاغتيال", "score": "8.90", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295707/164ea0017f8b91.jpg"},
        {"id": "youkoso-jitsuryoku-shijou-shugi-no-kyoushitsu-e-3rd-season", "title_en": "Classroom of the Elite III", "title_ar": "فصل النخبة الموسم الثالث", "score": "8.82", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/301510/659e9533f81aa.jpg"},
        {"id": "danganronpa-the-animation", "title_en": "Danganronpa: The Animation", "title_ar": "دانغانرونبا", "score": "8.15", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295708/164ea00396cbb2.jpg"},
        {"id": "jibaku-shounen-hanako-kun", "title_en": "Jibaku Shounen Hanako-kun", "title_ar": "هاناكو-كن شبح المرحاض", "score": "8.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300468/1663096599b519.jpg"}
    ],
    "P.A. Works": [
        {"id": "angel-beats", "title_en": "Angel Beats!", "title_ar": "نبضات الملاك", "score": "8.80", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295709/164ea005c2a4f7.jpg"},
        {"id": "another", "title_en": "Another", "title_ar": "آخر", "score": "8.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295710/164ea007dc2184.jpg"},
        {"id": "charlotte", "title_en": "Charlotte", "title_ar": "شارلوت", "score": "8.55", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295711/164ea009e51fa2.jpg"},
        {"id": "paripi-koumei", "title_en": "Paripi Koumei (Ya Boy Kongming!)", "title_ar": "يا رجل كونغمينغ!", "score": "8.48", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/300469/1663096601b87a.jpg"}
    ],
    "CoMix Wave Films": [
        {"id": "kimi-no-na-wa", "title_en": "Kimi no Na wa. (Your Name.)", "title_ar": "اسمك", "score": "9.48", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299093/1656e5cd96ba45.jpg"},
        {"id": "tenki-no-ko", "title_en": "Tenki no Ko (Weathering With You)", "title_ar": "أغير معك الطقس", "score": "8.95", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299095/1656e5d263914a.jpg"},
        {"id": "suzume-no-tojimari", "title_en": "Suzume no Tojimari", "title_ar": "سوزومي", "score": "9.10", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/301391/166fa2536fb190.jpg"},
        {"id": "kotonoha-no-niwa", "title_en": "Kotonoha no Niwa (The Garden of Words)", "title_ar": "حديقة الكلمات", "score": "8.80", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299096/1656e5d48bf62e.jpg"}
    ],
    "Gainax": [
        {"id": "neon-genesis-evangelion", "title_en": "Neon Genesis Evangelion", "title_ar": "إيفانجيليون", "score": "9.25", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295712/164ea00bf9028a.jpg"},
        {"id": "tengen-toppa-gurren-lagann", "title_en": "Tengen Toppa Gurren Lagann", "title_ar": "غورين لاغان", "score": "9.18", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295713/164ea00e123398.jpg"},
        {"id": "flcl", "title_en": "FLCL", "title_ar": "فولي كولي", "score": "8.50", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295714/164ea010375cf9.jpg"}
    ],
    "Sunrise": [
        {"id": "code-geass-hangyaku-no-lelouch", "title_en": "Code Geass: Hangyaku no Lelouch", "title_ar": "كود غياس: لولوش الثائر", "score": "9.45", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295715/164ea01256bb8c.jpg"},
        {"id": "cowboy-bebop", "title_en": "Cowboy Bebop", "title_ar": "كاوبوي بيبوب", "score": "9.30", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295716/164ea0148b3aa1.jpg"},
        {"id": "gintama", "title_en": "Gintama", "title_ar": "جينتاما", "score": "9.48", "type": "مسلسل", "thumbnail": "https://images.anime3rb.com/295717/164ea016af0884.jpg"}
    ],
    "Studio Ghibli": [
        {"id": "sen-to-chihiro-no-kamikakushi", "title_en": "Sen to Chihiro no Kamikakushi (Spirited Away)", "title_ar": "المخطوفة", "score": "9.52", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299097/1656e5d6d81e3a.jpg"},
        {"id": "mononoke-hime", "title_en": "Mononoke Hime (Princess Mononoke)", "title_ar": "الأميرة مونونوكي", "score": "9.40", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299098/1656e5d8fb855d.jpg"},
        {"id": "howl-no-ugoku-shiro", "title_en": "Howl no Ugoku Shiro (Howl's Moving Castle)", "title_ar": "قلعة هاول المتحركة", "score": "9.35", "type": "فيلم", "thumbnail": "https://images.anime3rb.com/299099/1656e5db1e7239.jpg"}
    ]
}



