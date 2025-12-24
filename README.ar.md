<div align="center">

<a href="README.md">
  <img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge&logo=google-translate&logoColor=white" alt="English">
</a>

<br><br>

# ⛩️ ani-cli-ar

<p dir="rtl" align="center">
  <b>مشاهدة الأنمي عبر الطرفية</b> · سريع · نظيف · <b>ترجمة عربية</b>
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

<br>

<img src="/assets/showcase.gif" alt="ani-cli-ar showcase" width="100%">

</div>

---

<div dir="rtl" align="right">

## 📑 جدول المحتويات
- [✨ المميزات](#-المميزات)
- [📦 التثبيت](#-التثبيت)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
- [🎮 أزرار التحكم](#-أزرار-التحكم)
- [🛠 الإعدادات](#-الإعدادات)

---

## ✨ المميزات

* 🎥 **بث عالي الجودة** — مشاهدة الحلقات بجودة **1080p (FHD)**، **720p (HD)**، أو **480p (SD)** مباشرة من واجهة برمجة تطبيقات خاصة.
* 🧠 **واجهة طرفية ذكية (TUI)** — مبنية باستخدام `rich` مع مؤشرات تحميل، جداول، وتنقل سلس.
* ⏩ **القفز للحلقات** — الانتقال فوراً إلى أي حلقة عبر إدخال رقمها مباشرة.
* 🎮 **Discord Rich Presence** — عرض اسم الأنمي، رقم الحلقة، صورة الغلاف، وحالة المشاهدة على ديسكورد.
* 🚫 **بدون إعلانات** — لا متصفح، لا نوافذ منبثقة، بث مباشر لملفات الفيديو الخام.

---

## 📦 التثبيت

**المتطلبات:**
- Python **3.8+**
- مشغل **MPV**

---

### 🪟 Windows

1. **تثبيت MPV**
   - **Scoop:**
     ```powershell
     scoop install mpv
     ```
   - **يدوي:** تحميل من https://mpv.io/installation/ وإضافة `mpv.exe` إلى متغيرات النظام (PATH)

2. **التحميل والتشغيل**
   ```powershell
   git clone https://github.com/np4abdou1/ani-cli-arabic.git
   cd ani-cli-arabic
   pip install -r requirements.txt
   python main.py
   ```

---

### 🐧 Linux

1. **تثبيت الحزم المطلوبة**
   ```bash
   # Debian / Ubuntu
   sudo apt update && sudo apt install mpv git python3-pip

   # Arch Linux
   sudo pacman -S mpv git python-pip

   # Fedora
   sudo dnf install mpv git python3-pip
   ```

2. **التحميل والتشغيل**
   ```bash
   git clone https://github.com/np4abdou1/ani-cli-arabic.git
   cd ani-cli-arabic
   pip install -r requirements.txt
   python3 main.py
   ```

---

### 🍎 macOS

1. **تثبيت الحزم**
   ```bash
   brew install mpv python
   ```

2. **التحميل والتشغيل**
   ```bash
   git clone https://github.com/np4abdou1/ani-cli-arabic.git
   cd ani-cli-arabic
   pip install -r requirements.txt
   python3 main.py
   ```

---

## 🎮 أزرار التحكم

| الزر | السياق | الوظيفة |
|-----|--------|--------|
| ↑ ↓ | القوائم | التنقل |
| Enter | القوائم | اختيار / تشغيل |
| G | الحلقات | القفز إلى حلقة |
| B | القوائم | رجوع |
| Q / Esc | عام | خروج |
| Space | المشغل | إيقاف / استئناف |
| ← → | المشغل | تقديم / تأخير 5 ثوانٍ |
| F | المشغل | ملء الشاشة |

---

## 🛠 الإعدادات

تخصيص المظهر يتم عبر ملف **themes.py**

| المتغير | الوصف |
|--------|-------|
| `CURRENT_THEME` | اللون العام للواجهة |
| `CUSTOM_ASCII_ART` | (اختياري) شعار ASCII مخصص |

**السمات المتاحة:**
`green` (افتراضي)، `purple`، `red`، `blue`، `yellow`، `pink`، `orange`، `cyan`، `custom`

**مثال:**
```python
CURRENT_THEME = "purple"
```

</div>

