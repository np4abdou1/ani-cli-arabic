<div align="center">

## 📑 Navigation

[Installation](#-installation) • [Features](#-what-can-you-do) • [How to Use](#-how-to-use) • [Keyboard Shortcuts](#️-keyboard-shortcuts) • [Configuration](#%EF%B8%8F-configuration) • [Contributors](#-contributors) • [License](#-license)

---

Terminal-based anime streaming with Arabic subtitles

<p align="center">
  <a href="https://github.com/np4abdou1/ani-cli-arabic/stargazers">
    <img src="https://img.shields.io/github/stars/np4abdou1/ani-cli-arabic?style=for-the-badge" />
  </a>
  <a href="https://github.com/np4abdou1/ani-cli-arabic/network">
    <img src="https://img.shields.io/github/forks/np4abdou1/ani-cli-arabic?style=for-the-badge" />
  </a>
  <br>
  <a href="https://github.com/np4abdou1/ani-cli-arabic/releases">
    <img src="https://img.shields.io/github/v/release/np4abdou1/ani-cli-arabic?style=for-the-badge" />
  </a>
  <a href="https://pypi.org/project/ani-cli-arabic">
    <img src="https://img.shields.io/pypi/v/ani-cli-arabic?style=for-the-badge" />
  </a>
  <a href="https://aur.archlinux.org/packages/ani-cli-arabic">
  <img src="https://img.shields.io/aur/version/ani-cli-arabic?style=for-the-badge" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge" />
</p>

<p>لإختيار اللغة العربية اضغط على الزر: </p>
<a href="README.ar.md">
  <img src="https://img.shields.io/badge/Language-Arabic-green?style=for-the-badge&logo=google-translate&logoColor=white" alt="Arabic">
</a>

<br>
<br>


https://github.com/user-attachments/assets/a6c6882a-7c50-4a8d-aa9c-e56a6d4ff7eb

</div>

---

## 📦 Installation

### Requirements
Before installing, make sure you have: 
- **Python 3.8 or newer** (Python 3.12 recommended, avoid 3.13+ due to numpy compilation issues)
- **MPV media player** (for streaming)
- **ffmpeg** (for video processing)
- **fzf** (for fuzzing results)

> **⚠️ Important Note:** if you are using mac os, build from source.

### Method 1: Install via pip (Recommended)

The easiest way to get started: 

```bash
pip install ani-cli-arabic
```

Launch the app:
```bash
ani-cli-arabic
# or use the shorter command
ani-cli-ar
```

To update to the latest version:
```bash
pip install --upgrade ani-cli-arabic
```

### Method 2: Arch Linux (AUR)

For Arch Linux users, install from the AUR: 

```bash
# Using yay
yay -S ani-cli-arabic

# Using paru
paru -S ani-cli-arabic
```

### Method 3: From Source

Want to run the development version?

**On Windows:**
```powershell
# Install MPV first
scoop install mpv

# Clone the repo and install dependencies
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python main.py
```

**On Linux (Debian/Ubuntu):**
```bash
# Get the dependencies
sudo apt update && sudo apt install mpv git python3-pip ffmpeg

# Clone and run
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python3 main.py
```

---

## 🎯 What Can You Do?

Here's everything this tool offers:

### Streaming & Playback
- **Multiple Quality Options**: Watch in 1080p, 720p, or 480p depending on your internet speed
- **Batch Download**: Download multiple episodes at once to watch offline
- **Trailer Support**: Watch YouTube trailers before committing to an anime
- **Resume from History**: Pick up exactly where you left off ( buggy )

### Discovery & Browsing
- **Search Anime**: Find any anime and anime movie by name (supports both English and Japanese titles and arabic titles)
- **Trending Now**: See what's currently popular
- **Top Rated**: Browse the highest-rated anime of all time
- **Browse by Genre**: Filter by Action, Romance, Isekai, and 12 other genres
- **Browse by Studio**: Find anime from Toei Animation, MAPPA, Ufotable, and 20+ more studios
- **Latest Releases**: Stay updated with the newest anime

### Personal Library
- **Watch History**: Keep track of everything you've watched with timestamps
- **Favorites System**: Bookmark your favorite anime for quick access
- **Episode Tracking**: The app remembers which episode you're on

### Interface & Experience
- **Rich TUI (Terminal User Interface)**: Beautiful terminal interface built with Rich library
- **17 Color Themes**: Choose from blue, red, purple, sunset, mint, lavender, and more 
- **Discord Rich Presence**: Show off what you're watching on Discord with anime posters 
<img width="864" height="372" alt="image" src="https://github.com/user-attachments/assets/eb8c5bc1-84dc-46a0-9b06-7efc5a5fee6d" />

- **Smooth Navigation**: Intuitive keyboard controls

### Technical Features
- **Zero Ads**: Clean streaming experience
- **Automatic Updates**: Built-in version checker notifies you of new releases, and yes this can be turned off.
- **MPV/VLC Support**: Choose your preferred media player
- **Dependency Auto-installer**: Automatically checks and installs missing dependencies, too lazy...
- **CLI Mode**: Simple command-line mode for quick searches (`ani-cli-ar -i "Naruto"`) _interactive mode also runs if the terminal is too narrow_
- **Cross-platform**: Works on Windows and Linux

---

## 🎮 How to Use

1. **Launch the app**:  Run `ani-cli-arabic` or `ani-cli-ar`
2. **Browse or Search**: Use the main menu to search, view trending, or browse genres
3. **Select an Anime**: Navigate with arrow keys and press Enter
4. **Pick an Episode**: Choose which episode to watch
5. **Select Quality**: Pick your preferred video quality
6. **Enjoy**: MPV will launch and start streaming

You can also use interactive mode for quick searches:
```bash
ani-cli-ar -i "One Piece"
```

---

## ⌨️ Keyboard Shortcuts

| Key | What it Does |
|-----|--------------|
| **↑ / ↓** | Navigate through lists |
| **Enter** | Select/Confirm choice |
| **G** | Jump directly to an episode number |
| **B** | Go back to previous screen |
| **Q / Esc** | Quit the application |
| **Space** | Pause/Resume video (in player) |
| **← / →** | Rewind/Forward 5 seconds |
| **F** | Toggle fullscreen |

---

## ⚙️ Configuration

Settings are stored locally in `~/.ani-cli-arabic/database/config.json`

### Available Settings

Access the settings menu from the main screen to customize:

- **Default Quality**: Set your preferred quality (1080p, 720p, or 480p)
- **Media Player**: Choose between MPV or VLC
- **Auto-next Episode**: Toggle automatic episode continuation
- **Discord Rich Presence**:  Show or hide Discord activity
- **Theme Color**: Pick from 17 beautiful color schemes: 
  - blue, red, green, purple, cyan, yellow, pink, orange, teal, magenta
  - lime, coral, lavender, gold, mint, rose, sunset
- **Analytics**:  Opt-in/out of anonymous usage stats - this is auto enabled by default.
- **Update Checking**: Toggle automatic update notifications

You can also manually edit the config file if you prefer. 

---

## Star History

## Star History

<a href="https://www.star-history.com/#np4abdou1/ani-cli-arabic&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=np4abdou1/ani-cli-arabic&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=np4abdou1/ani-cli-arabic&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=np4abdou1/ani-cli-arabic&type=date&legend=top-left" />
 </picture>
</a>

---

## 👥 Contributors

Special thanks to everyone who helped make this project happen: 

<div align="center">

[![Contributors](https://contrib.rocks/image?repo=np4abdou1/ani-cli-arabic)](https://github.com/np4abdou1/ani-cli-arabic/graphs/contributors)

</div>

**Key Contributors:**
- [@np4abdou1](https://github.com/np4abdou1) - Creator and main developer
- [@Anas-Tou](https://github.com/Anas-Tou) - Contributor

Want to contribute? Feel free to open issues or submit pull requests!

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**. 

You're free to use, modify, and distribute this software under the terms of the GPL-3.0 license.  See the [LICENSE](LICENSE) file for the full legal text.

**In simple terms:**
- ✅ Use it for personal or commercial purposes
- ✅ Modify the source code
- ✅ Distribute it to others
- ⚠️ Any modifications must also be open source under GPL-3.0
- ⚠️ Include the original copyright notice

---

<div align="center">

### ⚠️ Important Notice

</div>

> [! CAUTION]
> **By using this software you understand:**
> 
> - Anonymous usage statistics are collected for the GitHub page stats banner (can be disabled in settings)
> - The project is licensed under GPL-3.0 - see [LICENSE](LICENSE) for details
> - We do not host any content; all streams are from third-party sources
> - This tool is for personal use and educational purposes only

---

<br>

Made with ❤️ by the anime community

[⭐ Star this repo](https://github.com/np4abdou1/ani-cli-arabic) | [🐛 Report bugs](https://github.com/np4abdou1/ani-cli-arabic/issues) | [💬 Discussions](https://github.com/np4abdou1/ani-cli-arabic/discussions)

</div>
