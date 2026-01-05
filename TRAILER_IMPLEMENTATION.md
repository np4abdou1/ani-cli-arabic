# Trailer Implementation Suggestions for ani-cli-arabic

## Overview
The API provides trailer information in the anime data. Here are several approaches to integrate trailers into the CLI tool.

## API Data Available
According to the API documentation, anime responses include:
- `Trailer`: Direct trailer file URL (stored on animeify servers)
- `YTTrailer`: YouTube video ID for the trailer

**Base URL for trailers**: `https://animeify.net/animeify/files/trailers/`

## Implementation Options

### Option 1: Open Trailer in Web Browser (Easiest)
**Pros**: Simple, no additional dependencies, works everywhere
**Cons**: Opens external browser, breaks CLI flow

```python
import webbrowser

def open_trailer(youtube_id=None, trailer_url=None):
    if youtube_id:
        webbrowser.open(f"https://www.youtube.com/watch?v={youtube_id}")
    elif trailer_url:
        webbrowser.open(trailer_url)
```

**Usage**: Add `T` key in episode selection or anime details to open trailer

---

### Option 2: Play Trailer with MPV (Best for CLI)
**Pros**: Stays within terminal environment, uses existing MPV player
**Cons**: Requires MPV (already a dependency)

```python
def play_trailer_mpv(youtube_id=None, trailer_url=None):
    mpv_path = self.player.get_mpv_path()
    
    if youtube_id:
        url = f"https://www.youtube.com/watch?v={youtube_id}"
    elif trailer_url:
        url = trailer_url
    else:
        return False
    
    mpv_args = [
        mpv_path,
        '--fullscreen',
        '--ytdl',
        '--title=Trailer',
        url
    ]
    
    subprocess.run(mpv_args, check=False)
```

**Usage**: Add `T` key shortcut in anime details or episode selection menu

---

### Option 3: ASCII Preview in Terminal (Most Unique)
**Pros**: Fully terminal-based, unique experience
**Cons**: Complex, requires ffmpeg, limited frame rate, large terminal needed

```python
import cv2
from PIL import Image
import numpy as np

def show_ascii_trailer(trailer_url, duration=10):
    """Show first few seconds of trailer as ASCII art"""
    # Download first 10 seconds
    cmd = ['ffmpeg', '-i', trailer_url, '-t', str(duration), 
           '-vf', 'fps=10,scale=80:-1', 'trailer_temp.mp4']
    subprocess.run(cmd, check=False)
    
    # Play as ASCII
    cap = cv2.VideoCapture('trailer_temp.mp4')
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        ascii_frame = convert_to_ascii(frame)
        print('\033[2J\033[H' + ascii_frame)  # Clear and print
        time.sleep(0.1)
```

**Usage**: Show brief ASCII preview, then offer to open full trailer

---

### Option 4: Hybrid Approach (Recommended)
Combine multiple methods based on availability:

```python
class TrailerManager:
    def show_trailer(self, anime_title, youtube_id=None, trailer_url=None):
        if not youtube_id and not trailer_url:
            self.console.print("[dim]No trailer available[/dim]")
            return
        
        # Show options
        options = []
        if youtube_id or trailer_url:
            options.append("Play with MPV")
            options.append("Open in Browser")
        options.append("Cancel")
        
        choice = self.ui.selection_menu(options, 
                                        title=f"Trailer: {anime_title}")
        
        if choice == "Play with MPV":
            self.play_trailer_mpv(youtube_id, trailer_url)
        elif choice == "Open in Browser":
            self.open_trailer_browser(youtube_id, trailer_url)
```

---

## UI Integration Suggestions

### 1. In Anime Selection Menu (Search Results)
Add `T` key to view trailer for selected anime:
```
↑↓ Navigate | ENTER Select | T Trailer | b Back | q Quit
```

### 2. In Episode Selection Menu
Add trailer option in header or as a menu option:
```
↑↓ Navigate | ENTER Select | T Trailer | g Jump | F Fav | M Batch | b Back
```

### 3. In Anime Details View
Show trailer button/indicator if available:
```
Score: ⭐ 8.44/10    📺 Trailer Available
Rank: #137           (Press T to watch)
```

---

## Code Changes Required

### 1. Update AnimeResult Model
```python
@dataclass
class AnimeResult:
    # ... existing fields ...
    trailer: str = ""
    yt_trailer: str = ""
```

### 2. Update API Parser
```python
def _parse_anime_result(self, item: dict) -> AnimeResult:
    # ... existing code ...
    trailer=item.get('Trailer', ''),
    yt_trailer=item.get('YTTrailer', ''),
```

### 3. Add Trailer Manager
Create new `src/trailer.py`:
```python
class TrailerManager:
    def __init__(self, player_manager, ui_manager):
        self.player = player_manager
        self.ui = ui_manager
    
    def show_trailer(self, anime_title, yt_trailer=None, trailer_url=None):
        # Implementation here
```

### 4. Update Episode Selection Menu
Add trailer handling to key events:
```python
elif key == 't' or key == 'T':
    if anime_details.get('yt_trailer') or anime_details.get('trailer'):
        self.trailer_manager.show_trailer(
            anime_title,
            anime_details.get('yt_trailer'),
            anime_details.get('trailer')
        )
        live.update(generate_renderable(), refresh=True)
```

---

## Recommendation

**Start with Option 2 (MPV Player)** because:
1. MPV is already a dependency
2. Keeps users in the terminal environment
3. Works offline if trailer is cached
4. Supports YouTube URLs via ytdl
5. Consistent with existing video playback

**Implementation Priority**:
1. ✅ Add trailer fields to model and API parser
2. ✅ Add `T` key shortcut in episode selection menu
3. ✅ Play trailer with MPV (with ytdl support)
4. ✅ Fallback to browser if MPV fails
5. ⚠️ Show trailer indicator in UI when available

---

## Example Full Implementation

```python
# In src/app.py
def handle_episode_selection(self, selected_anime, episodes):
    # ... existing code ...
    
    # Add trailer info to anime_details
    anime_details = {
        'score': selected_anime.score,
        'rank': selected_anime.rank,
        'popularity': selected_anime.popularity,
        'rating': selected_anime.rating,
        'type': selected_anime.type,
        'episodes': selected_anime.episodes,
        'status': selected_anime.status,
        'studio': selected_anime.creators,
        'genres': selected_anime.genres,
        'trailer': selected_anime.trailer,
        'yt_trailer': selected_anime.yt_trailer
    }
    
    ep_idx = self.ui.episode_selection_menu(
        selected_anime.title_en, 
        episodes, 
        self.rpc, 
        selected_anime.thumbnail,
        last_watched_ep=last_watched,
        is_favorite=is_fav,
        anime_details=anime_details
    )
    
    # Handle trailer request
    if ep_idx == 'play_trailer':
        self.play_trailer(
            selected_anime.title_en,
            selected_anime.yt_trailer,
            selected_anime.trailer
        )
        continue

def play_trailer(self, anime_title, yt_trailer, trailer_url):
    """Play anime trailer"""
    if not yt_trailer and not trailer_url:
        self.ui.render_message("Info", "No trailer available", "info")
        return
    
    url = f"https://www.youtube.com/watch?v={yt_trailer}" if yt_trailer else trailer_url
    
    try:
        self.player.play(url, f"Trailer: {anime_title}", player_type='mpv')
    except Exception as e:
        # Fallback to browser
        import webbrowser
        webbrowser.open(url)
```

---

## Notes
- YouTube trailers may require `yt-dlp` or `youtube-dl` for MPV
- Some anime may not have trailers available
- Consider adding trailer status indicator (📺) in anime lists
- Trailers should not affect watch history
