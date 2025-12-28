import os
import sys

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
                                            ▀                                 ███    ███
                         {APP_VERSION} - Made by @np4abdou1/ani-cli-arabic
"""

# Theme definitions
THEMES = {
    "blue": {"border": "#00D9FF", "title": "#00D9FF", "prompt": "#00D9FF", "loading_spinner": "#00D9FF", "highlight_fg": "#000000", "highlight_bg": "#00D9FF", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#00D9FF"},
    "red": {"border": "#FF0F47", "title": "#FF4477", "prompt": "#FF0F47", "loading_spinner": "#FF0F47", "highlight_fg": "#000000", "highlight_bg": "#FF0F47", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FF0F47"},
    "green": {"border": "#8BD218", "title": "#8BD218", "prompt": "#8BD218", "loading_spinner": "#8BD218", "highlight_fg": "#000000", "highlight_bg": "#8BD218", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#8BD218"},
    "purple": {"border": "#B565FF", "title": "#B565FF", "prompt": "#B565FF", "loading_spinner": "#B565FF", "highlight_fg": "#000000", "highlight_bg": "#B565FF", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#B565FF"},
    "cyan": {"border": "#00FFFF", "title": "#00FFFF", "prompt": "#00FFFF", "loading_spinner": "#00FFFF", "highlight_fg": "#000000", "highlight_bg": "#00FFFF", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#00FFFF"},
    "yellow": {"border": "#FFD700", "title": "#FFD700", "prompt": "#FFD700", "loading_spinner": "#FFD700", "highlight_fg": "#000000", "highlight_bg": "#FFD700", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FFD700"},
    "pink": {"border": "#FF69B4", "title": "#FF69B4", "prompt": "#FF69B4", "loading_spinner": "#FF69B4", "highlight_fg": "#000000", "highlight_bg": "#FF69B4", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FF69B4"},
    "orange": {"border": "#FF8C00", "title": "#FF8C00", "prompt": "#FF8C00", "loading_spinner": "#FF8C00", "highlight_fg": "#000000", "highlight_bg": "#FF8C00", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FF8C00"},
    "teal": {"border": "#008080", "title": "#20B2AA", "prompt": "#008080", "loading_spinner": "#008080", "highlight_fg": "#000000", "highlight_bg": "#20B2AA", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#20B2AA"},
    "magenta": {"border": "#FF00FF", "title": "#FF00FF", "prompt": "#FF00FF", "loading_spinner": "#FF00FF", "highlight_fg": "#000000", "highlight_bg": "#FF00FF", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FF00FF"},
    "lime": {"border": "#00FF00", "title": "#32CD32", "prompt": "#00FF00", "loading_spinner": "#00FF00", "highlight_fg": "#000000", "highlight_bg": "#32CD32", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#32CD32"},
    "coral": {"border": "#FF7F50", "title": "#FF6347", "prompt": "#FF7F50", "loading_spinner": "#FF7F50", "highlight_fg": "#000000", "highlight_bg": "#FF6347", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FF6347"},
    "lavender": {"border": "#E6E6FA", "title": "#9370DB", "prompt": "#E6E6FA", "loading_spinner": "#E6E6FA", "highlight_fg": "#000000", "highlight_bg": "#9370DB", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#9370DB"},
    "gold": {"border": "#FFD700", "title": "#FFA500", "prompt": "#FFD700", "loading_spinner": "#FFD700", "highlight_fg": "#000000", "highlight_bg": "#FFA500", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FFA500"},
    "mint": {"border": "#98FF98", "title": "#00FA9A", "prompt": "#98FF98", "loading_spinner": "#98FF98", "highlight_fg": "#000000", "highlight_bg": "#00FA9A", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#00FA9A"},
    "rose": {"border": "#FF007F", "title": "#FF1493", "prompt": "#FF007F", "loading_spinner": "#FF007F", "highlight_fg": "#000000", "highlight_bg": "#FF1493", "primary_text": "#FFFFFF", "secondary_text": "#888888", "error": "#FF0000", "ascii": "#FF1493"},
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
    except Exception:
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
