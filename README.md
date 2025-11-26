<div align="center">

# ⛩️ ani-cli-ar

**Terminal-based Anime Streaming. Fast. Clean. Arabic Subtitles.**

[![GitHub Stars](https://img.shields.io/github/stars/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/network)
[![GitHub Release](https://img.shields.io/github/v/release/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/releases)

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Discord RPC](https://img.shields.io/badge/Discord-RPC_Active-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br>

<img src="/assets/showcase.gif" alt="ani-cli-ar showcase" width="100%">

</div>

---

### 📑 Table of Contents
- [✨ Features](#-features)
- [📦 Installation](#-installation)
  - [Windows Setup](#windows)
  - [Linux Setup](#linux)
- [🎮 Usage Controls](#-usage-controls)
- [🛠 Configuration](#-configuration)
- [🔨 Building](#-building)

---

## ✨ Features

* **FHD Streaming:** Scrapes and streams up to 1080p directly to MPV.
* **Rich UI:** Built with `textual` & `rich` for a responsive TUI.
* **Discord RPC:** Automatically displays your watch status.
* **Skip/Jump:** Fast travel through episodes.
* **Ad-Free:** Bypasses browser clutter completely.

---

## 📦 Installation

**Prerequisites:** [Python 3.8+](https://www.python.org/downloads/) and [MPV Player](https://mpv.io/).

### Windows

1.  **Install MPV**
    * Download from [mpv.io](https://mpv.io/installation/) or run `scoop install mpv`.
    * **Crucial:** Ensure `mpv.exe` is added to your System `PATH`.

2.  **Clone & Run**
    ```powershell
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python main.py
    ```

### Linux

1.  **Install Dependencies**
    ```bash
    # Debian/Ubuntu
    sudo apt install mpv git python3-pip

    # Arch Linux
    sudo pacman -S mpv git python-pip
    ```

2.  **Clone & Run**
    ```bash
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python3 main.py
    ```

---

## 🎮 Usage Controls

Navigation is keyboard-centric.

| Key | Function |
| :--- | :--- |
| <kbd>↑</kbd> <kbd>↓</kbd> | Navigate menus / Search results |
| <kbd>Enter</kbd> | Select / Play |
| <kbd>G</kbd> | **Jump** to specific episode number |
| <kbd>B</kbd> | Back to previous menu |
| <kbd>Q</kbd> / <kbd>Esc</kbd> | Quit application |

> **Note:** During playback, MPV controls apply (e.g., <kbd>Space</kbd> to pause, <kbd>→</kbd> to seek).

---

## 🛠 Configuration

You can customize the accent color by editing `themes.py`.

| Variable | Description | Options |
| :--- | :--- | :--- |
| `CURRENT_THEME` | Sets the primary UI color. | `green` (default), `purple`, `red`, `blue`, `yellow`, `pink`, `orange`, `cyan` |

```python
# themes.py
CURRENT_THEME = "purple"