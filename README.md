<div align="center">

# ⛩️ ani-cli-ar

**Terminal-based Anime Streaming. Fast. Clean. Arabic Subtitles.**

[![GitHub Stars](https://img.shields.io/github/stars/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/network)
[![GitHub Release](https://img.shields.io/github/v/release/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/releases)

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<!-- Language switch links -->
- **Language:** [English](#english) | [العربية](#العربية)

<br>

<img src="/assets/showcase.gif" alt="ani-cli-ar showcase" width="100%">

</div>

---

### 📑 Table of Contents
## العربية

**القائمة:** [English](#english) | [العربية](#العربية)

### ⛩️ ani-cli-ar

تطبيق عرض أنمي في الطرفية — سريع، نظيف، مع ترجمة عربية.

### ✨ الميزات

- **بث عالي الجودة:** يقوم البرنامج بجلب وحفظ حلقات بجودة **1080p (FHD)**، **720p (HD)**، أو **480p (SD)** من واجهة برمجة تطبيقات خاصة.
- **حالة متقدمة على ديسكورد:** يحدث حالة ديسكورد تلقائياً بعنوان الأنمي، صورة الغلاف، رقم الحلقة، وحالة المشاهدة.
- **واجهة طرفية ذكية:** مصممة باستخدام مكتبة `rich` لعرض واجهة تفاعلية مع مؤشرات تحميل وجداول وتنسيق مركزي.
- **الانتقال للحلقة:** إمكانية القفز السريع إلى رقم حلقة محدد دون التمرير.
- **تجاوز الإعلانات:** يتجنب الإعلانات ونوافذ البوب آب من خلال بث ملفات الفيديو الخام مباشرة.

---

### 📦 التثبيت

**المتطلبات:** يجب أن يكون لديك **Python 3.8+** و`MPV` مثبتين.

#### ويندوز

1. **تثبيت MPV**
    - **الخيار A (Scoop):** `scoop install mpv`
    - **الخيار B (يدوي):** نزّل من [mpv.io](https://mpv.io/installation/) وأضف `mpv.exe` إلى متغيرات البيئة (PATH).
2. **نسخ المشروع وتثبيت الحزم**
    ```powershell
    git clone https://github.com/np4abdou1/ani-cli-arabic.git
    cd ani-cli-arabic
    pip install -r requirements.txt
    python main.py
    ```

- [✨ Features](#-features)

- استخدم الأسهم للتنقل و`Enter` للاختيار.
- مفاتيح مفيدة: `G` للقفز إلى حلقة، `B` للعودة، `Q` أو `Esc` للخروج.
- [📦 Installation](#-installation)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
- [🎮 Usage Controls](#-usage-controls)
- [🛠 Configuration](#-configuration)
- [🔨 Building & Deployment](#-building--deployment)

---

## ✨ Features

* **High-Definition Streaming:** Scrapes and streams episodes in **1080p (FHD)**, **720p (HD)**, or **480p (SD)** directly from a private api .
* **Discord Rich Presence:** Automatically updates your Discord status with the anime title,anime poster, episode number, and watching state.
* **Smart TUI:** Built with `rich` to provide a responsive terminal user interface with loading spinners, tables, and centered layouts.
* **Episode Jump:** Fast-travel system to skip directly to specific episode numbers without scrolling.
* **Ad-Block by Design:** Bypasses browser-based ads and popups completely by streaming raw video files.

---

## 📦 Installation

**Prerequisites:** You must have **Python 3.8+** and **MPV** installed.

### Windows

1.  **Install MPV**
    * **Option A (Scoop):** `scoop install mpv`
    * **Option B (Manual):** Download from [mpv.io](https://mpv.io/installation/) and add `mpv.exe` to your System Environment Variables (PATH).
2.  **Clone & Install**
    ```powershell
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python main.py
    ```

### Linux

1.  **Install Dependencies**
    ```bash
    # Debian / Ubuntu
    sudo apt update && sudo apt install mpv git python3-pip

    # Arch Linux
    sudo pacman -S mpv git python-pip

    # Fedora
    sudo dnf install mpv git python3-pip
    ```
2.  **Clone & Install**
    ```bash
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python3 main.py
    ```

### macOS

1.  **Install Dependencies (via Homebrew)**
    ```bash
    brew install mpv python
    ```
2.  **Clone & Install**
    ```bash
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python3 main.py
    ```

---

## 🎮 Usage Controls

The interface is designed for keyboard-only navigation.

| Key | Context | Function |
| :--- | :--- | :--- |
| <kbd>↑</kbd> <kbd>↓</kbd> | Menu | Navigate through anime results or episode lists |
| <kbd>Enter</kbd> | Menu | Select an item / Start playback |
| <kbd>G</kbd> | Episodes | **Jump**: Open prompt to type specific episode number |
| <kbd>B</kbd> | Menu | Back to previous screen |
| <kbd>Q</kbd> / <kbd>Esc</kbd> | Global | Quit the application |
| <kbd>Space</kbd> | Player | Pause / Resume video (MPV default) |
| <kbd>→</kbd> / <kbd>←</kbd> | Player | Seek 5 seconds forward/backward (MPV default) |
| <kbd>F</kbd> | Player | Toggle Fullscreen (MPV default) |

---

## 🛠 Configuration

You can customize the accent colors and visual style by editing `themes.py`.

**File:** `themes.py`

| Variable | Description |
| :--- | :--- |
| `CURRENT_THEME` | Controls the global color scheme of the TUI. |
| `CUSTOM_ASCII_ART` | (Optional) Override the header text with your own ASCII art string. |

**Available Themes:**
`green` (default), `purple`, `red`, `blue`, `yellow`, `pink`, `orange`, `cyan`, `custom`.

**Example:**
```python
# themes.py
CURRENT_THEME = "purple"