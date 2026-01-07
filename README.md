<div align="center">


![download](https://github.com/user-attachments/assets/39760ac2-9550-407c-893b-51ad5cbe3bfa)



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
  <img src="https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge" />
</p>

<p>لإختيار اللغة العربية اضغط على الزر:</p>
<a href="README.ar.md">
  <img src="https://img.shields.io/badge/Language-Arabic-green?style=for-the-badge&logo=google-translate&logoColor=white" alt="Arabic">
</a>

<br>

<h3>SHOWCASE</h3>







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

**Requirements:** Python 3.8+ and MPV player and ffmpeg

**Note:** Python 3.13+ is not currently recommended, as numpy may need to compile from source which can take considerable time.

**Recommended:** Python 3.12.x

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

MIT License - See [LICENSE](LICENSE) for details.

---

<div align="center">

### ⚠️ Important Notice

</div>

> [!IMPORTANT]
> **By using this software you agree to:**
> - Collection of anonymous data for monitoring users for the github Page stats banner.

> **License Terms:**  
> This software is licensed under the **MIT License**. You are free to use, modify, and distribute it.

