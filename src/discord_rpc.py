import time
import threading
try:
    from pypresence import Presence, PipeClosed
    from pypresence.types import ActivityType
    DISCORD_RPC_AVAILABLE = True
except ImportError:
    DISCORD_RPC_AVAILABLE = False

from .config import DISCORD_CLIENT_ID, DISCORD_LOGO_URL, DISCORD_LOGO_TEXT

class DiscordRPCManager:
    def __init__(self):
        self.rpc = None
        self.connected = False
        self.current_state = "Browsing"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self.update_thread = None
        self.running = False
        self._anime_poster_url = None
        
    def connect(self):
        if not DISCORD_RPC_AVAILABLE:
            return False
            
        try:
            self.rpc = Presence(DISCORD_CLIENT_ID)
            self.rpc.connect()
            self.connected = True
            self.running = True
            
            self.update_browsing()
            
            self.update_thread = threading.Thread(target=self._auto_update, daemon=True)
            self.update_thread.start()
            
            return True
        except Exception:
            self.connected = False
            return False
    
    def _auto_update(self):
        while self.running:
            time.sleep(15)
            if self.connected:
                try:
                    self._update_presence()
                except PipeClosed:
                    try:
                        self.rpc.connect()
                        self._update_presence()
                    except Exception:
                        self.connected = False
                except Exception:
                    pass
                
# for some reason buttons didnt work i will fix it later ..

    def _update_presence(self):
        if not self.connected or not self.rpc:
            return
        
        try:
            if self.current_state == "Watching":
                self.rpc.update(
                    details=f"Episode {self.current_episode}",
                    state=self.current_anime,
                    start=self.start_time,
                    large_image=self._get_anime_poster(),
                    large_text=self.current_anime,
                    small_image=DISCORD_LOGO_URL,
                    small_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Choosing Quality":
                self.rpc.update(
                    details=self.current_anime,
                    state=f"⚙️ Choosing quality for Episode {self.current_episode}",
                    start=self.start_time,
                    large_image=self._get_anime_poster(),
                    large_text=self.current_anime,
                    small_image=DISCORD_LOGO_URL,
                    small_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Loading":
                self.rpc.update(
                    details=self.current_anime,
                    state=f"⏳ Loading Episode {self.current_episode}",
                    start=self.start_time,
                    large_image=self._get_anime_poster(),
                    large_text=self.current_anime,
                    small_image=DISCORD_LOGO_URL,
                    small_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Viewing":
                self.rpc.update(
                    details=self.current_anime,
                    state="📖 Viewing details",
                    start=self.start_time,
                    large_image=self._get_anime_poster(),
                    large_text=self.current_anime,
                    small_image=DISCORD_LOGO_URL,
                    small_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Selecting Episode":
                self.rpc.update(
                    details=self.current_anime,
                    state="📺 Browsing episodes",
                    start=self.start_time,
                    large_image=self._get_anime_poster(),
                    large_text=self.current_anime,
                    small_image=DISCORD_LOGO_URL,
                    small_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Searching":
                self.rpc.update(
                    details="ani-cli-ar",
                    state="🔍 Searching for anime",
                    start=self.start_time,
                    large_image=DISCORD_LOGO_URL,
                    large_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Featured":
                self.rpc.update(
                    details="ani-cli-ar",
                    state="⭐ Browsing featured anime",
                    start=self.start_time,
                    large_image=DISCORD_LOGO_URL,
                    large_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "History":
                self.rpc.update(
                    details="ani-cli-ar",
                    state="📜 Viewing watch history",
                    start=self.start_time,
                    large_image=DISCORD_LOGO_URL,
                    large_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Favorites":
                self.rpc.update(
                    details="ani-cli-ar",
                    state="❤️ Browsing favorites",
                    start=self.start_time,
                    large_image=DISCORD_LOGO_URL,
                    large_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            elif self.current_state == "Settings":
                self.rpc.update(
                    details="ani-cli-ar",
                    state="⚙️ Configuring settings",
                    start=self.start_time,
                    large_image=DISCORD_LOGO_URL,
                    large_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
            else:
                self.rpc.update(
                    details="ani-cli-ar",
                    state="🏠 Browsing",
                    start=self.start_time,
                    large_image=DISCORD_LOGO_URL,
                    large_text=DISCORD_LOGO_TEXT,
                    buttons=[{"label": "Website", "url": "https://np4abdou1.github.io/ani-cli-arabic"}]
                )
        except Exception:
            pass
    
    def _get_anime_poster(self) -> str:
        if hasattr(self, '_anime_poster_url') and self._anime_poster_url:
            return self._anime_poster_url
        return DISCORD_LOGO_URL
    
    def update_browsing(self):
        self.current_state = "Browsing"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = None
        self._update_presence()
    
    def update_searching(self):
        self.current_state = "Searching"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = None
        self._update_presence()
    
    def update_viewing_anime(self, anime_title: str, poster_url: str = None):
        self.current_state = "Viewing"
        self.current_anime = anime_title
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = poster_url
        self._update_presence()
    
    def update_selecting_episode(self, anime_title: str, poster_url: str = None):
        self.current_state = "Selecting Episode"
        self.current_anime = anime_title
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = poster_url
        self._update_presence()
    
    def update_watching(self, anime_title: str, episode_num: str, poster_url: str = None):
        self.current_state = "Watching"
        self.current_anime = anime_title
        self.current_episode = episode_num
        self.start_time = int(time.time())
        self._anime_poster_url = poster_url
        self._update_presence()
    
    def update_choosing_quality(self, anime_title: str, episode_num: str, poster_url: str = None):
        self.current_state = "Choosing Quality"
        self.current_anime = anime_title
        self.current_episode = episode_num
        self.start_time = int(time.time())
        self._anime_poster_url = poster_url
        self._update_presence()
    
    def update_loading(self, anime_title: str, episode_num: str, poster_url: str = None):
        self.current_state = "Loading"
        self.current_anime = anime_title
        self.current_episode = episode_num
        self.start_time = int(time.time())
        self._anime_poster_url = poster_url
        self._update_presence()
    
    def update_featured(self):
        self.current_state = "Featured"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = None
        self._update_presence()
    
    def update_history(self):
        self.current_state = "History"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = None
        self._update_presence()
    
    def update_favorites(self):
        self.current_state = "Favorites"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = None
        self._update_presence()
    
    def update_settings(self):
        self.current_state = "Settings"
        self.current_anime = None
        self.current_episode = None
        self.start_time = int(time.time())
        self._anime_poster_url = None
        self._update_presence()
    
    def disconnect(self):
        self.running = False
        if self.connected and self.rpc:
            try:
                self.rpc.close()
            except Exception:
                pass
            self.connected = False
