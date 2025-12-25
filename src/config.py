import os
import sys

from .version import APP_VERSION

CURRENT_VERSION = APP_VERSION
DISCORD_CLIENT_ID = "1437470271895376063"
DISCORD_LOGO_URL = "https://i.postimg.cc/DydJfKY3/logo.gif"
DISCORD_LOGO_TEXT = f"ani-cli-arabic {APP_VERSION}"
MYANIMELIST_API_BASE = "https://api.jikan.moe/v4/anime/"

DEFAULT_HEADER_ART = f"""
   ▄████████ ███▄▄▄▄    ▄█    ▄▄▄▄███▄▄▄▄      ▄████████
  ███    ███ ███▀▀▀██▄ ███  ▄██▀▀▀███▀▀▀██▄   ███    ███
  ███    ███ ███   ███ ███▌ ███   ███   ███   ███    █▀ 
  ███    ███ ███   ███ ███▌ ███   ███   ███  ▄███▄▄▄    
▀███████████ ███   ███ ███▌ ███   ███   ███ ▀▀███▀▀▀    
  ███    ███ ███   ███ ███  ███   ███   ███   ███    █▄ 
  ███    ███ ███   ███ ███  ███   ███   ███   ███    ███
   ███    █▀   ▀█   █▀  █▀    ▀█   ███   █▀    ██████████
      {APP_VERSION} - Made by @np4abdou1/ani-cli-arabic
"""

def load_user_config():
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, base_dir)
        
        try:
            import themes
            return themes
        except ImportError:
            pass
    except Exception:
        pass
    return None

_user_config = load_user_config()

if _user_config:
    selected_theme = getattr(_user_config, 'CURRENT_THEME', 'green')
    themes = getattr(_user_config, 'THEMES', {})
    theme_colors = themes.get(selected_theme, themes.get('green', {}))
    
    custom_art = getattr(_user_config, 'CUSTOM_ASCII_ART', None)
    HEADER_ART = custom_art if custom_art and custom_art.strip() else DEFAULT_HEADER_ART
    
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
else:
    HEADER_ART = DEFAULT_HEADER_ART
    
    COLOR_ASCII = "#8BD218"
    COLOR_BORDER = "#8BD218"
    COLOR_TITLE = "#8BD218"
    COLOR_PROMPT = "#8BD218"
    COLOR_LOADING_SPINNER = "#8BD218"
    COLOR_HIGHLIGHT_FG = "#000000"
    COLOR_HIGHLIGHT_BG = "#8BD218"
    COLOR_PRIMARY_TEXT = "#FFFFFF"
    COLOR_SECONDARY_TEXT = "#888888"
    COLOR_ERROR = "#FF0000"
