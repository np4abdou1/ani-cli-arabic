<h1 align="center">                          🎉 ani-cli-arabic v2.0 - Major Release </h1>

<div align="center">

<h2>💖 Support This Open Source Project</h2>
<p>Your support helps maintain the project and keeps the updates coming!</p>
<a href="https://paypal.me/np4abdou">
  <img src="https://img.shields.io/badge/Donate_with_PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate with PayPal">
</a>
<br><br><br>

Terminal-based anime streaming & batch downloading with Arabic and English subtitles

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
  <a href="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/ci.yml">
    <img src="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/ci.yml/badge.svg" alt="CI Status" />
  </a>
  <a href="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/publish-pypi.yml">
    <img src="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/publish-pypi.yml/badge.svg" alt="PyPI Workflow" />
  </a>
  <a href="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/publish-aur.yml">
    <img src="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/publish-aur.yml/badge.svg" alt="AUR Workflow" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge" />
</p>

<br>

## 📑 Navigation

[What's New in v2.0](#-whats-new-in-v20) • [Installation](#-installation) • [How to Use](#-how-to-use) • [Key Features](#-key-features) • [Keyboard Shortcuts](#️-keyboard-shortcuts) • [Configuration](#%EF%B8%8F-configuration) • [Contributors](#-contributors) • [License](#-license)

<br><br>

<p>لإختيار اللغة العربية اضغط على الزر: </p>
<a href="README.ar.md">
  <img src="https://img.shields.io/badge/Language-Arabic-green?style=for-the-badge&logo=google-translate&logoColor=white" alt="Arabic">
</a>

<br><br>

https://github.com/user-attachments/assets/a6c6882a-7c50-4a8d-aa9c-e56a6d4ff7eb

</div>

---

## 🚀 What's New in v2.0?

Version 2.0 is the largest architectural overhaul in the project's history:

* 🌐 **Multi-Provider Ecosystem**: Stream seamlessly from 4 independent sources: **Anime3rb**, **Anime Slayer**, **Animeify**, and **HiAnime** (English Sub & Dub).
* 📥 **Native Chunked Batch Downloader**: Built from scratch with parallel chunked streaming, automatic resume, and real-time speed indicators — with **zero external tools required** (no aria2c or yt-dlp).
* ⚡ **Rebuilt Interactive CLI Mode (`-i`)**: Clean organic `fzf` flow, mouse navigation, no Arabic RTL clipping, and an interactive episode action menu (`Play`, `Download`, `Batch Download`, `Quality`).
* 🎬 **Universal Player Support & Real-Time IPC**: Full playback support for **MPV**, **VLC**, **Celluloid**, **IINA**, and **Syncplay**. MPV integration monitors JSON-IPC sockets in real-time for seamless exact-second timestamp resume.
* 🛡️ **Zero-Downtime Edge Infrastructure**: Automatic 3-tier domain fallback chains across custom domains, Cloudflare Pages, and Cloudflare Workers.
* 🔒 **Hardened Privacy**: Completely removed playback tracking and isolated development branches from telemetry.
* 🔄 **Seamless Platform Auto-Updater**: Instant automated updates across PyPI (`pip`), Arch Linux (`yay` / `paru`), and Homebrew.

---

## 📦 Installation

### Prerequisites
- **Python 3.9 or newer** (Python 3.10 - 3.12 recommended)
- **MPV media player** (recommended default player)
- **ffmpeg** (for multimedia streams)
- **fzf** (for interactive search and selection)

---

### Method 1: Install via pip (Recommended)

The quickest way to get started on Linux, macOS, and Windows:

```bash
pip install ani-cli-arabic
```

Launch the application:
```bash
ani-cli-arabic
# or use the short alias
ani-cli-ar
```

Upgrade anytime:
```bash
pip install --upgrade ani-cli-arabic
```

---

### Method 2: Arch Linux (AUR)

For Arch Linux and derivative distributions (Manjaro, EndeavourOS, etc.):

```bash
# Using yay
yay -S ani-cli-arabic

# Using paru
paru -S ani-cli-arabic
```

---

### Method 3: From Source

Run the latest development code directly:

```bash
# Clone the repository
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic

# Install dependencies
pip install -r requirements.txt

# Run
python3 main.py
```

---

## 🎮 How to Use

### 1. Full TUI Mode (Default)
Launch the application and navigate with your arrow keys:
```bash
ani-cli-arabic
```

### 2. Interactive CLI Mode (`-i`)
Quickly search and play from the terminal using native `fzf` menus:
```bash
# Search and choose interactively
ani-cli-ar -i "One Piece"

# Search in Arabic
ani-cli-ar -i "ون بيس"
```

### 3. Provider Switching via CLI
Specify your streaming provider directly on startup:
```bash
# Stream from Anime3rb (Arabic Sub)
ani-cli-ar -p anime3rb "Naruto"

# Stream from HiAnime (English Sub/Dub)
ani-cli-ar -p hianime "Attack on Titan"

# Stream from Anime Slayer
ani-cli-ar -p anime_slayer "Bleach"

# Stream from Animeify
ani-cli-ar -p animeify "Jujutsu Kaisen"
```

### 4. Direct Query Search
```bash
ani-cli-ar "Hunter x Hunter"
```

---

## 🎯 Key Features

### 📺 Multi-Source Streaming & Providers
- **Anime3rb**: High-speed direct CDN streams with Arabic subtitles.
- **Anime Slayer**: Official API endpoints with episode servers.
- **Animeify**: Mirror servers with multiple resolution choices.
- **HiAnime**: Fast English subbed and dubbed streams with dynamic referer resolution.

### 📥 Built-in Chunked Batch Downloader
- Download full seasons or specific episodes (e.g. `1-12`, `1,3,5`, or `all`).
- Multi-threaded chunked downloads with pause/resume support.
- Real-time download metrics: speed (MB/s), ETA, and visual percentage bar.
- Standalone execution: No external CLI download managers needed.

### 🎬 Universal Players & Smart History
- **Supported Players**: MPV, VLC, Celluloid, IINA (macOS), and Syncplay (watch together with friends).
- **Exact Resume**: Real-time MPV IPC socket stream saves exact watch progress; resumes right where you left off.
- **Favorites & History**: Dedicated tabs to bookmark titles and revisit previous watches.

### 🎨 Modern Terminal UI & Themes
- **17 Custom Themes**: blue, red, green, purple, cyan, yellow, pink, orange, teal, magenta, lime, coral, lavender, gold, mint, rose, sunset.
- **Discord Rich Presence**: Live status showing current anime poster, title, and episode.
- **Arabic Search Normalization**: Typo-tolerant query normalization handling hamza, taa marbuta, and latinized names.

---

## ⌨️ Keyboard Shortcuts

### Main Menu & Navigation
| Key | Action |
| :---: | :--- |
| **↑ / ↓** or **j / k** | Navigate through lists and menus |
| **Enter** | Select / Confirm choice |
| **G** | Jump directly to episode number |
| **B** | Go back to previous screen |
| **Q** / **Esc** | Quit application |
| **S** | Open Search prompt |
| **T** | View Trending anime |
| **R** | View Top Rated anime |
| **F** | Open Favorites |
| **H** | Open Watch History |
| **O** | Open Settings menu |
| **D** | Support project (Donate) |

### In Video Player (MPV)
| Key | Action |
| :---: | :--- |
| **Space** | Pause / Resume playback |
| **← / →** | Seek 5 seconds backward / forward |
| **[ / ]** | Decrease / Increase playback speed |
| **F** | Toggle fullscreen |
| **9 / 0** | Volume down / up |
| **Q** | Stop and save resume timestamp |

---

## ⚙️ Configuration

Settings are saved locally in `~/.ani-cli-arabic/database/config.json`.

### Settings Menu Options
Access the settings menu (`[O]`) from the main screen to configure:

- **Active Provider**: Switch between `anime3rb`, `anime_slayer`, `animeify`, and `hianime`.
- **Default Quality**: Set default resolution (`1080p`, `720p`, `480p`, or `Ask`).
- **Media Player**: Choose between `mpv`, `vlc`, `celluloid`, `iina`, or `syncplay`.
- **Auto-next Episode**: Automatically play the next episode upon completion.
- **Discord Rich Presence**: Toggle Discord profile activity on or off.
- **Theme Color**: Switch instantly across 17 color palettes.
- **Download Directory**: Customize your default anime downloads folder.
- **Analytics & Updates**: Toggle anonymous health telemetry or auto-update notifications.

---

## 👥 Contributors

Special thanks to everyone who helped build, test, and maintain this project:

<div align="center">

[![Contributors](https://contrib.rocks/image?repo=np4abdou1/ani-cli-arabic)](https://github.com/np4abdou1/ani-cli-arabic/graphs/contributors)

</div>

**Key Contributors:**
- [@np4abdou1](https://github.com/np4abdou1) - Creator and main developer
- [@Anas-Tou](https://github.com/Anas-Tou) - Contributor
- [@ilyes-pro](https://github.com/ilyes-Pro) - Contributor

Want to contribute? Feel free to open issues or submit pull requests!

---

## 📄 License

This project is licensed under the **GNU General Public License v3.0**. See the [LICENSE](LICENSE) file for details.

- ✅ Free for personal and educational use
- ✅ Open source and community-driven
- ⚠️ Any modifications or forks must remain open source under GPL-3.0

---

<div align="center">

### ⚠️ Disclaimer

</div>

> [!CAUTION]
> - `ani-cli-arabic` does not host any video streams; it acts strictly as a terminal scraper and client for publicly accessible third-party providers.
> - Anonymous telemetry collects basic operational statistics (can be toggled in settings). No playback history or personal queries are ever stored or transmitted.

---

<div align="center">

Made with ❤️ by the anime community

[⭐ Star this repo](https://github.com/np4abdou1/ani-cli-arabic) • [🐛 Report bugs](https://github.com/np4abdou1/ani-cli-arabic/issues) • [💬 Discussions](https://github.com/np4abdou1/ani-cli-arabic/discussions)

</div>
