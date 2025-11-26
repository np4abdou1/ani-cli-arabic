<div align="center">

<a href="README.md">
  <img src="https://img.shields.io/badge/%F0%9F%87%BA%F0%9F%87%B8%20English-English-blue?style=for-the-badge" alt="English">
</a>

<br><br>

# ⛩️ ani-cli-ar

**مشاهدة الأنمي عبر الطرفية (Terminal). سريع. نظيف. ترجمة عربية.**

[![GitHub Stars](https://img.shields.io/github/stars/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/network)
[![GitHub Release](https://img.shields.io/github/v/release/np4abdou1/ani-cli-arabic?style=for-the-badge)](https://github.com/np4abdou1/ani-cli-arabic/releases)

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<br>

<img src="/assets/showcase.gif" alt="ani-cli-ar showcase" width="100%">

</div>

---

<div dir="rtl" align="right">

### 📑 جدول المحتويات
- [✨ المميزات](#-المميزات)
- [📦 التثبيت](#-التثبيت)
  - [Windows](#windows)
  - [Linux](#linux)
  - [macOS](#macos)
- [🎮 أزرار التحكم](#-أزرار-التحكم)
- [🛠 الإعدادات](#-الإعدادات)

---

## ✨ المميزات

* **بث عالي الجودة:** البحث ومشاهدة الحلقات بجودة **1080p (FHD)**، **720p (HD)**، أو **480p (SD)** مباشرة من واجهة برمجة تطبيقات خاصة.
* **حالة Discord التفاعلية (Rich Presence):** تحديث حالة الديسكورد تلقائياً بعنوان الأنمي، صورة الغلاف، رقم الحلقة، وحالة المشاهدة.
* **واجهة طرفية ذكية (TUI):** مبنية باستخدام مكتبة `rich` لتوفير واجهة مستخدم تفاعلية مع أيقونات تحميل، جداول، وتنسيق منسق.
* **نظام القفز للحلقات:** إمكانية الانتقال مباشرة إلى رقم حلقة معين دون الحاجة للتمرير الطويل.
* **حجب الإعلانات:** تجاوز الإعلانات والنوافذ المنبثقة المزعجة تماماً عبر بث ملفات الفيديو الخام مباشرة.

---

## 📦 التثبيت

**المتطلبات:** يجب أن يكون لديك **Python 3.8+** ومشغل **MPV** مثبتاً على جهازك.

### Windows

1.  **تثبيت MPV**
    * **الخيار أ (عبر Scoop):** `scoop install mpv`
    * **الخيار ب (يدوي):** حمل البرنامج من [mpv.io](https://mpv.io/installation/) وقم بإضافة مسار `mpv.exe` إلى متغيرات النظام (Environment Variables).
2.  **التحميل والتثبيت**
    ```powershell
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python main.py
    ```

### Linux

1.  **تثبيت الحزم المطلوبة**
    ```bash
    # Debian / Ubuntu
    sudo apt update && sudo apt install mpv git python3-pip

    # Arch Linux
    sudo pacman -S mpv git python-pip

    # Fedora
    sudo dnf install mpv git python3-pip
    ```
2.  **التحميل والتثبيت**
    ```bash
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python3 main.py
    ```

### macOS

1.  **تثبيت الحزم (عبر Homebrew)**
    ```bash
    brew install mpv python
    ```
2.  **التحميل والتثبيت**
    ```bash
    git clone [https://github.com/np4abdou1/ani-cli-arabic.git](https://github.com/np4abdou1/ani-cli-arabic.git)
    cd ani-cli-arabic
    pip install -r requirements.txt
    python3 main.py
    ```

---

## 🎮 أزرار التحكم

تم تصميم الواجهة للعمل كلياً عن طريق لوحة المفاتيح.

| الزر | السياق | الوظيفة |
| :--- | :--- | :--- |
| <kbd>↑</kbd> <kbd>↓</kbd> | القوائم | التنقل بين نتائج البحث أو قائمة الحلقات |
| <kbd>Enter</kbd> | القوائم | اختيار العنصر / بدء التشغيل |
| <kbd>G</kbd> | الحلقات | **القفز**: فتح نافذة لكتابة رقم الحلقة مباشرة |
| <kbd>B</kbd> | القوائم | الرجوع للقائمة السابقة |
| <kbd>Q</kbd> / <kbd>Esc</kbd> | عام | الخروج من البرنامج |
| <kbd>Space</kbd> | المشغل | إيقاف مؤقت / استئناف (إعدادات MPV) |
| <kbd>→</kbd> / <kbd>←</kbd> | المشغل | تقديم / تأخير 5 ثواني (إعدادات MPV) |
| <kbd>F</kbd> | المشغل | تكبير الشاشة (إعدادات MPV) |

---

## 🛠 الإعدادات

يمكنك تخصيص الألوان والمظهر العام عبر تعديل ملف `themes.py`.

**الملف:** `themes.py`

| المتغير | الوصف |
| :--- | :--- |
| `CURRENT_THEME` | يتحكم في اللون العام للواجهة. |
| `CUSTOM_ASCII_ART` | (اختياري) استبدال شعار النص في الأعلى بشعارك الخاص. |

**السمات (Themes) المتاحة:**
`green` (الافتراضي), `purple`, `red`, `blue`, `yellow`, `pink`, `orange`, `cyan`, `custom`.

**مثال:**
```python
# themes.py
CURRENT_THEME = "purple"

</div>