<div align="center">

<a href="README.ar.md">
  <img src="https://img.shields.io/badge/Language-Arabic-green?style=for-the-badge&logo=google-translate&logoColor=white" alt="Arabic">
</a>

# ⛩️ ani-cli-ar

<p align="center">
  <b>Terminal-based Anime Streaming</b> · Fast · Clean · <b>Arabic Subtitles</b>
</p>

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
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

<p align="center">
  <i>Highly inspired by</i> <a href="https://github.com/pystardust/ani-cli">ani-cli</a>
</p>

<br>

## 🎬 Showcase

https://github.com/user-attachments/assets/22eb92a1-b57e-4126-9869-b0988cab63a6

</div>

---

## 📑 Table of Contents
- [✨ Features](#-features)
- [📦 Installation](#-installation)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
- [🎮 Usage Controls](#-usage-controls)
- [🛠 Configuration](#-configuration)

---

## ✨ Features

* 🎥 **High‑Definition Streaming** — Stream episodes in **1080p (FHD)**, **720p (HD)**, or **480p (SD)** directly from a private API.
* 🧠 **Smart TUI** — Built with `rich` for spinners, tables, smooth navigation, and centered layouts.
* ⏩ **Episode Jump** — Instantly jump to any episode by number without endless scrolling.
* 🎮 **Discord Rich Presence** — Shows anime title, episode number, poster, and watch state on Discord.
* 🚫 **Ad‑Free by Design** — No browser, no popups, no ads. Streams raw video files directly.

---

## 📦 Installation

**Requirements:**
- Python **3.8+**
- **MPV** media player

### 🐍 PyPI (Recommended)

The easiest way to install ani-cli-arabic:

```bash
# Install from PyPI
pip install ani-cli-arabic

# Run the application
ani-cli-arabic
# or
ani-cli-ar
```

**Update to latest version:**
```bash
pip install --upgrade ani-cli-arabic
```

---

### 🪟 Windows

1. **Install MPV**
   - **Scoop:**
     ```powershell
     scoop install mpv
     ```
   - **Manual:** Download from https://mpv.io/installation/ and add `mpv.exe` to your **PATH**

2. **Clone & Run**
   ```powershell
   git clone https://github.com/np4abdou1/ani-cli-arabic.git
   cd ani-cli-arabic
   pip install -r requirements.txt
   python main.py
   ```

---

### 🐧 Linux

1. **Install Dependencies**
   ```bash
   # Debian / Ubuntu
   sudo apt update && sudo apt install mpv git python3-pip

   # Arch Linux
   sudo pacman -S mpv git python-pip

   # Fedora
   sudo dnf install mpv git python3-pip
   ```

2. **Clone & Run**
   ```bash
   git clone https://github.com/np4abdou1/ani-cli-arabic.git
   cd ani-cli-arabic
   pip install -r requirements.txt
   python3 main.py
   ```

---

### 🍎 macOS

1. **Install Dependencies**
   ```bash
   brew install mpv python
   ```

2. **Clone & Run**
   ```bash
   git clone https://github.com/np4abdou1/ani-cli-arabic.git
   cd ani-cli-arabic
   pip install -r requirements.txt
   python3 main.py
   ```

---

## 🎮 Usage Controls

| Key | Context | Action |
|-----|--------|--------|
| ↑ ↓ | Menu | Navigate lists |
| Enter | Menu | Select / Play |
| G | Episodes | Jump to episode |
| B | Menu | Go back |
| Q / Esc | Global | Quit |
| Space | Player | Pause / Resume |
| ← → | Player | Seek ±5s |
| F | Player | Fullscreen |

---

## 🛠 Configuration

Customize visuals via **themes.py**

**File:** `themes.py`

| Variable | Description |
|---------|-------------|
| `CURRENT_THEME` | Global color scheme |
| `CUSTOM_ASCII_ART` | Optional custom header ASCII |

**Themes:**
`green` (default), `purple`, `red`, `blue`, `yellow`, `pink`, `orange`, `cyan`, `custom`

**Example:**
```python
CURRENT_THEME = "blue"
```

