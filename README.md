<div align="center">

<h1>Ani-cli-ar</h1>

![445026601441165313](https://github.com/user-attachments/assets/3c6ad4e9-2df6-4ee6-991f-536150e49da2)



Terminal-based anime streaming with Arabic subtitles

<p align="center">
  <a href="https://github.com/np4abdou1/ani-cli-arabic/stargazers">
    <img src="https://img.shields.io/github/stars/np4abdou1/ani-cli-arabic?style=for-the-badge" />
  </a>
  <a href="https://github.com/np4abdou1/ani-cli-arabic/network">
    <img src="https://img.shields.io/github/forks/np4abdou1/ani-cli-arabic?style=for-the-badge" />
  </a>
  <a href="https://github.com/np4abdou1/ani-cli-arabic/releases">
    <img src="https://img.shields.io/github/v/release/np4abdou1/ani-cli-arabic?style=for-the-badge" />
  </a>
  <a href="https://pypi.org/project/ani-cli-arabic">
    <img src="https://img.shields.io/pypi/v/ani-cli-arabic?style=for-the-badge" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-Custom-orange?style=for-the-badge" />
</p>

<p>لإختيار اللغة العربية اضغط على الزر:</p>
<a href="README.ar.md">
  <img src="https://img.shields.io/badge/Language-Arabic-green?style=for-the-badge&logo=google-translate&logoColor=white" alt="Arabic">
</a>

<p align="center">
  <i>Inspired by</i> <a href="https://github.com/pystardust/ani-cli">ani-cli</a>
</p>







https://github.com/user-attachments/assets/8b57a95a-2949-44d2-b786-bd1c035e0060






</div>

---

## Features

- Stream anime in 1080p, 720p, or 480p
- Rich terminal UI with smooth navigation
- Jump to any episode by number
- Discord Rich Presence integration
- Watch history and favorites
- Ad-free streaming
- Auto-next episode support
- Batch download episodes
- Multiple themes

## Installation

**Requirements:** Python 3.8+ and MPV player

### Via pip (All platforms)

```bash
pip install ani-cli-arabic
```

Run the app:
```bash
ani-cli-arabic
# or
ani-cli-ar
```

Update:
```bash
pip install --upgrade ani-cli-arabic
```

### From source

**Windows:**
```powershell
# Install MPV
scoop install mpv

# Clone and run
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python main.py
```

**Linux:**
```bash
# Install dependencies (Debian/Ubuntu)
sudo apt update && sudo apt install mpv git python3-pip

# Clone and run
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python3 main.py
```

**macOS:**
```bash
# Install dependencies
brew install mpv python

# Clone and run
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python3 main.py
```

## Controls

| Key | Action |
|-----|--------|
| ↑ ↓ | Navigate |
| Enter | Select/Play |
| G | Jump to episode |
| B | Go back |
| Q / Esc | Quit |
| Space | Pause/Resume |
| ← → | Seek ±5s |
| F | Fullscreen |

## Configuration

Settings are saved in `~/.ani-cli-arabic/database/config.json`

Access settings menu from the main screen to configure:
- Default quality (1080p/720p/480p)
- Media player (MPV/VLC)
- Auto-next episode
- Theme color (16 themes available)
- Update checking

## License

Custom Proprietary License - See [LICENSE](LICENSE) for details.

---

<div align="center">

### ⚠️ Important Notice

</div>

> [!IMPORTANT]
> **By using this software you agree to:**
> - Collection of anonymous data for monitoring usage and users
> - Not using this software for commercial uses
> - No API abusing

> **License Terms:**  
> This software is licensed for **personal, non-commercial use only**. You may modify the frontend/UI, but **API abuse or reverse-engineering is strictly prohibited**. Commercial use requires prior written permission.  
> 
> **API Usage:**  
> The backend API is private and closed-source. Any attempt to extract, abuse, or redistribute API credentials will result in immediate access termination. Frontend modifications are welcome; backend modifications are not permitted.

For commercial licensing inquiries, please contact the repository owner.

