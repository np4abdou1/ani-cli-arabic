from .version import APP_VERSION

CURRENT_VERSION = APP_VERSION
DISCORD_CLIENT_ID = "1437470271895376063"
DISCORD_LOGO_URL = "https://i.postimg.cc/DydJfKY3/logo.gif"
DISCORD_LOGO_TEXT = f"ani-cli-arabic {APP_VERSION}"
MYANIMELIST_API_BASE = "https://api.jikan.moe/v4/anime/"

DEFAULT_HEADER_ART = f"""
   ▄████████ ███▄▄▄▄    ▄█        ▄████████  ▄█        ▄█          ▄████████    ▄████████
  ███    ███ ███▀▀▀██▄ ███       ███    ███ ███       ███         ███    ███   ███    ███
  ███    ███ ███   ███ ███▌      ███    █▀  ███       ███▌        ███    ███   ███    ███
  ███    ███ ███   ███ ███▌      ███        ███       ███▌        ███    ███  ▄███▄▄▄▄██▀
▀███████████ ███   ███ ███▌      ███        ███       ███▌      ▀███████████ ▀▀███▀▀▀▀▀  
  ███    ███ ███   ███ ███       ███    █▄  ███       ███         ███    ███ ▀███████████
  ███    ███ ███   ███ ███       ███    ███ ███▌    ▄ ███         ███    ███   ███    ███
  ███    █▀   ▀█   █▀  █▀        ████████▀  █████▄▄██ █▀          ███    █▀    ███    ███
                                            ▀                                  ███    ███
                         {APP_VERSION} - Made by @np4abdou1/ani-cli-arabic
"""

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

# Theme definitions
THEMES = {
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

def load_user_theme():
    """Load theme from config.json"""
    try:
        from pathlib import Path
        import json
        
        home_dir = Path.home()
        config_file = home_dir / ".ani-cli-arabic" / "database" / "config.json"
        
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('theme', 'blue')
    except (IOError, json.JSONDecodeError, KeyError):
        pass
    return 'blue'

selected_theme = load_user_theme()
theme_colors = THEMES.get(selected_theme, THEMES['blue'])

HEADER_ART = DEFAULT_HEADER_ART
COLOR_ASCII = theme_colors.get("ascii", "#8BD218")
COLOR_BORDER = theme_colors.get("border", "#8BD218")
COLOR_TITLE = theme_colors.get("title", "#8BD218")
COLOR_PROMPT = theme_colors.get("prompt", "#8BD218")
COLOR_LOADING_SPINNER = theme_colors.get("loading_spinner", "#8BD218")
COLOR_HIGHLIGHT_FG = theme_colors.get("highlight_fg", "#000000")
COLOR_HIGHLIGHT_BG = theme_colors.get("highlight_bg", "#8BD218")
COLOR_PRIMARY_TEXT = theme_colors.get("primary_text", "#FFFFFF")
COLOR_SECONDARY_TEXT = theme_colors.get("secondary_text", "#888888")
COLOR_ERROR = theme_colors.get("error", "#FF0000")
