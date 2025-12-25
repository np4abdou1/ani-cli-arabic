<div align="center">

<a href="README.md">
  <img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge&logo=google-translate&logoColor=white" alt="English">
</a>

<br><br>

# ani-cli-ar

<p dir="rtl" align="center">
مشاهدة الأنمي عبر التيرمينال مع ترجمة عربية
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
  <a href="https://pypi.org/project/ani-cli-arabic">
    <img src="https://img.shields.io/pypi/v/ani-cli-arabic?style=for-the-badge" />
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" />
</p>

https://github.com/user-attachments/assets/22eb92a1-b57e-4126-9869-b0988cab63a6

</div>

---

<div dir="rtl" align="right">

## المميزات

- بث بجودة 1080p أو 720p أو 480p
- واجهة طرفية متقدمة وسلسة
- القفز لأي حلقة مباشرة
- دعم Discord Rich Presence
- سجل المشاهدة والمفضلة
- بدون إعلانات
- تشغيل تلقائي للحلقة التالية
- تحميل دفعات من الحلقات
- ألوان متعددة للواجهة

## التثبيت

**المتطلبات:** Python 3.8+ و MPV

### عبر pip (جميع الأنظمة)

```bash
pip install ani-cli-arabic
```

تشغيل البرنامج:
```bash
ani-cli-arabic
# أو
ani-cli-ar
```

التحديث:
```bash
pip install --upgrade ani-cli-arabic
```

### من المصدر

**Windows:**
```powershell
# تثبيت MPV
scoop install mpv

# التحميل والتشغيل
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python main.py
```

**Linux:**
```bash
# تثبيت المتطلبات (Debian/Ubuntu)
sudo apt update && sudo apt install mpv git python3-pip

# التحميل والتشغيل
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python3 main.py
```

**macOS:**
```bash
# تثبيت المتطلبات
brew install mpv python

# التحميل والتشغيل
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python3 main.py
```

## أزرار التحكم

| الزر | الوظيفة |
|-----|--------|
| ↑ ↓ | التنقل |
| Enter | اختيار/تشغيل |
| G | القفز لحلقة |
| B | رجوع |
| Q / Esc | خروج |
| Space | إيقاف/استئناف |
| ← → | تقديم/تأخير 5 ثوان |
| F | ملء الشاشة |

## الإعدادات

الإعدادات محفوظة في `~/.ani-cli-arabic/database/config.json`

يمكنك الوصول لقائمة الإعدادات من الشاشة الرئيسية لتغيير:
- الجودة الافتراضية (1080p/720p/480p)
- المشغل (MPV/VLC)
- التشغيل التلقائي للحلقة التالية
- لون الواجهة (16 لون متاح)
- التحقق من التحديثات

## الرخصة

MIT

</div>
