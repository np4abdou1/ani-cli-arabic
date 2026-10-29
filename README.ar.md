<div dir="rtl">

<div align="center">

  <p>
    <strong>أداة بث وتحميل الأنمي مباشرة من  (Terminal)</strong><br>
    شاهد وحمّل الأنمي بجودة عالية مع ترجمة عربية وإنجليزية مباشرة من سطر الأوامر.
  </p>

  <p>
    <a href="https://paypal.me/np4abdou"><img src="https://img.shields.io/badge/Sponsor-PayPal-00457C?style=flat-square&logo=paypal&logoColor=white" alt="Donate with PayPal" /></a>
  </p>

  <!-- Primary Release & Package Badges -->
  <p>
    <a href="https://github.com/np4abdou1/ani-cli-arabic/releases"><img src="https://img.shields.io/github/v/release/np4abdou1/ani-cli-arabic?style=flat-square&logo=github&label=Release&color=6366f1" alt="GitHub Release" /></a>
    <a href="https://pypi.org/project/ani-cli-arabic"><img src="https://img.shields.io/pypi/v/ani-cli-arabic?style=flat-square&logo=pypi&logoColor=white&label=PyPI&color=3776AB" alt="PyPI Version" /></a>
    <a href="https://aur.archlinux.org/packages/ani-cli-arabic"><img src="https://img.shields.io/aur/version/ani-cli-arabic?style=flat-square&logo=archlinux&logoColor=white&label=AUR&color=1793D1" alt="AUR Version" /></a>
    <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python 3.9+" />
    <a href="LICENSE"><img src="https://img.shields.io/badge/License-GPL--3.0-22c55e?style=flat-square" alt="License" /></a>
  </p>

  <!-- CI/CD & Repo Activity Badges -->
  <p>
    <a href="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/np4abdou1/ani-cli-arabic/ci.yml?style=flat-square&logo=githubactions&logoColor=white&label=CI%20Tests" alt="CI Status" /></a>
    <a href="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/publish-pypi.yml"><img src="https://img.shields.io/github/actions/workflow/status/np4abdou1/ani-cli-arabic/publish-pypi.yml?style=flat-square&logo=pypi&logoColor=white&label=PyPI%20Build" alt="PyPI Workflow" /></a>
    <a href="https://github.com/np4abdou1/ani-cli-arabic/actions/workflows/publish-aur.yml"><img src="https://img.shields.io/github/actions/workflow/status/np4abdou1/ani-cli-arabic/publish-aur.yml?style=flat-square&logo=archlinux&logoColor=white&label=AUR%20Build" alt="AUR Workflow" /></a>
    <a href="https://github.com/np4abdou1/ani-cli-arabic/stargazers"><img src="https://img.shields.io/github/stars/np4abdou1/ani-cli-arabic?style=flat-square&logo=github&label=Stars&color=eab308" alt="GitHub Stars" /></a>
    <a href="https://github.com/np4abdou1/ani-cli-arabic/network"><img src="https://img.shields.io/github/forks/np4abdou1/ani-cli-arabic?style=flat-square&logo=github&label=Forks&color=8b5cf6" alt="GitHub Forks" /></a>
  </p>

  <p>
    🌍 <strong><a href="README.md">Click here for the English README</a></strong>
  </p>

  <hr />

  <!-- Quick Navigation Bar -->
  <p>
    <a href="#-ما-الجديد-في-الإصدار-v20">🚀 ما الجديد</a> &nbsp;•&nbsp;
    <a href="#-المصادر-والسيرفرات">🌐 المصادر</a> &nbsp;•&nbsp;
    <a href="#-التثبيت">📦 التثبيت</a> &nbsp;•&nbsp;
    <a href="#-طريقة-الاستخدام">🎮 الاستخدام</a> &nbsp;•&nbsp;
    <a href="#️-اختصارات-لوحة-المفاتيح">⌨️ الاختصارات</a> &nbsp;•&nbsp;
    <a href="#️-الإعدادات">⚙️ الإعدادات</a> &nbsp;•&nbsp;
    <a href="#-المساهمون">👥 المساهمون</a>
  </p>

</div>

<br />

<div align="center">

https://github.com/user-attachments/assets/e74d4443-20b0-4683-b346-bf168a720025

</div>

---

## 🚀 ما الجديد في الإصدار v2.0؟

يُعد الإصدار **2.0** أكبر تحديث معماري في تاريخ المشروع، حيث تمت إعادة بنائه بالكامل لضمان أقصى سرعة، استقرار، وعدم الاعتماد على أدوات تحميل خارجية:

| الميزة | التفاصيل |
| :--- | :--- |
| 🌐 **محرك متعدد المصادر** | بث مباشر وسلس من **4 مصادر مستقلة**: `Anime3rb`، `Anime Slayer`، `Animeify`، و `HiAnime` (ترجمة ودبلجة إنجليزية). |
| 📥 **محمّل دفعات مدمج (Chunked)** | مبني من الصفر مع دعم التحميل المتوازي، الإيقاف/الاستئناف، وعرض السرعة والوقت المتبقي لحظياً — **دون الحاجة لأي أدوات خارجية** (لا يتطلب `aria2c` أو `yt-dlp`). |
| ⚡ **الوضع التفاعلي السريع (`-i`)** | واجهة `fzf` متطورة تدعم الماوس، عرض سليم للنصوص العربية دون اقتطاع، وقائمة إجراءات سريعة للحلقة (`Play`, `Download`, `Batch`, `Quality`). |
| 🎬 **دعم شامل للمشغلات و IPC** | دعم كامل لمشغلات **MPV**، **VLC**، **Celluloid**، **IINA**، و **Syncplay**. مراقبة لحظية عبر MPV JSON-IPC لحفظ ثانية التوقف بدقة واستئناف المشاهدة لاحقاً. |
| 🛡️ **بنية سحابية بدون توقف** | نظام توجيه احتياطي تلقائي ثلاثي الطبقات عبر النطاقات المخصصة، Cloudflare Pages، و Cloudflare Workers. |
| 🔒 **خصوصية مشددة** | إزالة تتبع المشاهدة بالكامل وعزل فروع التطوير عن إحصائيات فحص الحالة. |
| 🔄 **محدّث تلقائي متعدد المنصات** | تحديث فوري بخطوة واحدة عبر PyPI (`pip`)، توزيعة Arch Linux (`yay` / `paru`)، و Homebrew. |

---

## 🌐 المصادر والسيرفرات

يمكنك التبديل بين المصادر بسهولة من قائمة الإعدادات (`[O]` أو `[c]`) أو مباشرة عبر خيار `-p` في سطر الأوامر:

| المصدر | مفتاح CLI | اللغة | مميزات البث |
| :--- | :---: | :---: | :--- |
| **Anime3rb** | `anime3rb` | 🇸🇦 ترجمة عربية | بث مباشر فائق السرعة عبر CDN مع خيارات متعددة للجودة |
| **Anime Slayer** | `anime_slayer` | 🇸🇦 ترجمة عربية | نقاط اتصال API رسمية مع سيرفرات احتياطية متعددة لكل حلقة |
| **Animeify** | `animeify` | 🇸🇦 ترجمة عربية | سيرفرات متعددة مع تبديل سريع بين الجودات |
| **HiAnime** | `hianime` | 🇬🇧 ترجمة / دبلجة إنجليزية | بث سريع باللغة الإنجليزية (مترجم ومدبلج) مع معالجة تلقائية للروابط |
| **Stardima** | `stardima` | 🇸🇦 دبلجة عربية | روابط بث متعددة ومباشرة مع تحديد تلقائي للمسار الصوتي العربي |
| **Stardima Kids** | `stardima_kids` | 🇸🇦 دبلجة عربية | كرتون وبرامج أطفال مدبلجة، مفصولة تماماً عن كتالوج الأنمي |

---

## 📦 التثبيت

### 🔧 المتطلبات الأساسية

تأكد من تثبيت البرامج الأساسية التالية على نظامك قبل التشغيل:

* **Python 3.9+** (يُنصح بإصدار `3.10` إلى `3.12`)
* **MPV** (المشغل الافتراضي الموصى به لدعم الحفظ التلقائي لوقت التوقف)
* **FFmpeg** (مطلوب لمعالجة وتجميع تدفقات الفيديو)
* **fzf** (مطلوب لتشغيل الوضع التفاعلي السريع `-i`)

---

### ⚡ الطريقة 1: عبر PyPI باستخدام `pip` (موصى به — Linux, macOS, Windows)

<div dir="ltr">

```bash
# Install the latest stable release
pip install ani-cli-arabic

# Launch the full TUI or use the short alias
ani-cli-arabic
ani-cli-ar
```

</div>

<details>
<summary><b>🔄 كيفية التحديث عبر pip</b></summary>

<div dir="ltr">

```bash
pip install --upgrade ani-cli-arabic
```

</div>
</details>

---

### 🏹 الطريقة 2: لمستخدمي Arch Linux (AUR)

متوفر مباشرة في مستودع AUR لتوزيعات Arch، Manjaro، EndeavourOS، و Garuda:

<div dir="ltr">

```bash
# Using yay
yay -S ani-cli-arabic

# Using paru
paru -S ani-cli-arabic
```

</div>

---

### 🛠️ الطريقة 3: التشغيل من المصدر (Source)

لتشغيل أحدث نسخة تطويرية مباشرة من المستودع:

<div dir="ltr">

```bash
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic
pip install -r requirements.txt
python3 main.py
```

</div>

---

## 🎮 طريقة الاستخدام

### 1️⃣ الواجهة الرسومية الكاملة للطرفية (الوضع الافتراضي)
شغّل لوحة التحكم التفاعلية الكاملة مع التنقل بالأسهم، الثيمات، سجل المشاهدة، والمفضلة:
<div dir="ltr">

```bash
ani-cli-ar
```

</div>

### 2️⃣ الوضع التفاعلي السريع عبر `fzf` (`-i`)
تجاوز الواجهة الكاملة وابحث أو شغّل الحلقات فوراً عبر قائمة `fzf` خفيفة باللغة العربية أو الإنجليزية:
<div dir="ltr">

```bash
# Search in English
ani-cli-ar -i "One Piece"

# Search in Arabic
ani-cli-ar -i "ون بيس"
```

</div>

### 3️⃣ اختيار المصدر عبر سطر الأوامر (`-p`)
حدد مصدر البث المطلوب مباشرة عند تشغيل الأمر:
<div dir="ltr">

```bash
# Stream from Anime3rb (Arabic Sub)
ani-cli-ar -p anime3rb "Naruto"

# Stream from HiAnime (English Sub/Dub)
ani-cli-ar -p hianime "Attack on Titan"

# Stream from Anime Slayer
ani-cli-ar -p anime_slayer "Bleach"

# Stream from Animeify
ani-cli-ar -p animeify "Jujutsu Kaisen"

# البث من ستارديما أنمي (دبلجة عربية)
ani-cli-ar -p stardima "ناروتو"

# البث من ستارديما كيدز (كرتون مدبلج)
ani-cli-ar -p stardima_kids "سبونج بوب"
```

</div>

### 4️⃣ البحث المباشر
انتقل مباشرة إلى نتائج البحث داخل الواجهة:
<div dir="ltr">

```bash
ani-cli-ar "Hunter x Hunter"
```

</div>

---

## 🎯 نظرة معمقة على المميزات الأساسية

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>📥 محمّل الدفعات الذكي (Batch Downloader)</h3>
      <ul>
        <li><b>نطاقات مرنة:</b> حمّل مواسم كاملة أو حلقات محددة (مثل <code>1-12</code>، <code>1,3,5</code>، أو <code>all</code>).</li>
        <li><b>متعدد المسارات (Multi-Threaded):</b> تحميل مقسم متوازي مع دعم الإيقاف المؤقت والاستئناف التلقائي.</li>
        <li><b>مؤشرات حية:</b> عرض سرعة التحميل (MB/s)، الوقت المتبقي (ETA)، وشريط التقدم المئوي.</li>
        <li><b>مستقل ذاتياً:</b> لا يحتاج إلى أي برامج تحميل خارجية.</li>
      </ul>
    </td>
    <td width="50%" valign="top">
      <h3>🎨 واجهة عصرية ومميزات ذكية</h3>
      <ul>
        <li><b>17 ثيم مدمج:</b> <code>blue</code>، <code>red</code>، <code>green</code>، <code>purple</code>، <code>cyan</code>، <code>gold</code>، <code>rose</code>، <code>sunset</code>، والمزيد.</li>
        <li><b>ربط Discord Rich Presence:</b> يعرض بوستر الأنمي، الاسم، ورقم الحلقة الحالية مباشرة في ملفك الشخصي على ديسكورد.</li>
        <li><b>بحث عربي ذكي:</b> معالجة تلقائية للأخطاء الإملائية (الهمزات، التاء المربوطة، والأسماء المعرّبة).</li>
        <li><b>مشاهدة جماعية:</b> دعم مدمج لـ <b>Syncplay</b> للمشاهدة مع الأصدقاء في نفس اللحظة.</li>
      </ul>
    </td>
  </tr>
</table>

> ℹ️ *بيانات تصنيف الأعمال مبنية على TMDB؛ هذا المنتج يستخدم واجهة TMDB API لكنه غير معتمد أو موثق من قِبل TMDB.*

---

## ⌨️ اختصارات لوحة المفاتيح

<table>
  <tr>
    <th width="50%">🖥️ التنقل في الواجهة الرئيسية (TUI)</th>
    <th width="50%">🎬 مشغل الفيديو (MPV)</th>
  </tr>
  <tr>
    <td valign="top">

| الزر | الوظيفة |
| :---: | :--- |
| <kbd>↑</kbd> <kbd>↓</kbd> / <kbd>j</kbd> <kbd>k</kbd> | التنقل بين القوائم والعناصر |
| <kbd>Enter</kbd> | بحث / تأكيد الاختيار |
| <kbd>e</kbd> / <kbd>m</kbd> | أحدث الحلقات / الأفلام |
| <kbd>t</kbd> / <kbd>p</kbd> / <kbd>r</kbd> | الرائج / الأكثر شعبية / الأعلى تقييماً |
| <kbd>g</kbd> / <kbd>s</kbd> | تصفح التصنيفات / الاستوديوهات |
| <kbd>l</kbd> / <kbd>f</kbd> | سجل المشاهدة / المفضلة |
| <kbd>c</kbd> / <kbd>O</kbd> | فتح قائمة الإعدادات |
| <kbd>d</kbd> | دعم المشروع (تبرع) |
| <kbd>B</kbd> | الرجوع إلى الشاشة السابقة |
| <kbd>Ctrl+C</kbd> / <kbd>Q</kbd> | إغلاق البرنامج |

</td>
    <td valign="top">

| الزر | الوظيفة |
| :---: | :--- |
| <kbd>Space</kbd> | إيقاف مؤقت / استئناف التشغيل |
| <kbd>←</kbd> / <kbd>→</kbd> | تقديم / ترجيع 5 ثوانٍ |
| <kbd>[</kbd> / <kbd>]</kbd> | إبطاء / تسريع سرعة التشغيل |
| <kbd>F</kbd> | تفعيل / إلغاء ملء الشاشة |
| <kbd>9</kbd> / <kbd>0</kbd> | خفض / رفع مستوى الصوت |
| <kbd>Q</kbd> | إيقاف المشاهدة وحفظ ثانية التوقف بدقة |

</td>
  </tr>
</table>

---

## ⚙️ الإعدادات

يتم حفظ جميع تفضيلات المستخدم محلياً في المسار:
<div dir="ltr">

```text
~/.ani-cli-arabic/database/config.json
```

</div>

افتح قائمة الإعدادات (<kbd>c</kbd> أو <kbd>O</kbd>) من القائمة الرئيسية في أي وقت لتخصيص:
* **المصدر النشط (Active Provider)**: التبديل بين `anime3rb`، `anime_slayer`، `animeify`، `hianime`، `stardima`، و `stardima_kids`.
* **لغة صوت ستارديما (Stardima Audio Language)**: اختيار `dub` (افتراضي للدبلجة)، `sub`، أو `both`.
* **الجودة الافتراضية (Default Quality)**: تثبيت الجودة على `1080p`، `720p`، `480p`، أو `Ask` (السؤال في كل مرة).
* **مشغل الوسائط (Media Player)**: الاختيار بين `mpv`، `vlc`، `celluloid`، `iina`، أو `syncplay`.
* **التشغيل التلقائي (Auto-Next Episode)**: تشغيل الحلقة التالية تلقائياً فور انتهاء الحلقة الحالية.
* **حالة ديسكورد (Discord Rich Presence)**: تفعيل أو إيقاف عرض النشاط الحي على ديسكورد.
* **لون الثيم (Theme Color)**: معاينة والتبديل الفوري بين 17 لوحة ألوان مختلفة.
* **مجلد التحميل (Download Directory)**: تحديد مسار المجلد المحلي لحفظ الحلقات المحملة.
* **الخصوصية والتحديثات**: تفعيل أو تعطيل القياسات وفاحص الإصدارات التلقائي.

---

## 👥 المساهمون

شكر خاص لكل من ساهم في بناء، اختبار، وتطوير مشروع **ani-cli-arabic**:

<div align="center">
  <a href="https://github.com/np4abdou1/ani-cli-arabic/graphs/contributors"><img src="https://contrib.rocks/image?repo=np4abdou1/ani-cli-arabic" alt="Contributors" /></a>
</div>

<br />

* **[@np4abdou1](https://github.com/np4abdou1)** — مؤسس المشروع والمطور الرئيسي
* **[@Anas-Tou](https://github.com/Anas-Tou)** — مساهم أساسي
* **[@ilyes-pro](https://github.com/ilyes-Pro)** — مساهم أساسي

> 💡 **هل ترغب في المساهمة؟** اطّلع على [دليل المساهمة](.github/CONTRIBUTING.md) — نرحب دائماً بفتح التذاكر (Issues) وطلبات السحب (Pull Requests)!

---

## 📄 الترخيص

هذا المشروع مرخص بموجب رخصة **GNU General Public License v3.0**. راجع ملف [LICENSE](LICENSE) لمزيد من التفاصيل.

* ✅ مجاني للاستخدام الشخصي، التعليمي، والمجتمعي
* ✅ مفتوح المصدر وشفاف بنسبة 100%
* ⚠️ أي تعديلات أو نسخ مشتقة (Forks) يجب أن تبقى مفتوحة المصدر تحت رخصة **GPL-3.0**

---

<div align="center">

  <h3>💖 ادعم هذا المشروع مفتوح المصدر</h3>
  <p>دعمك يساعد في تغطية تكاليف البنية التحتية واستمرار التحديثات!</p>
  <a href="https://paypal.me/np4abdou"><img src="https://img.shields.io/badge/Donate_with_PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate with PayPal" /></a>

  <br /><br />

  صُنع بـ ❤️ بواسطة مجتمع الأنمي مفتوح المصدر

  <p>
    <a href="https://github.com/np4abdou1/ani-cli-arabic">⭐ ضع نجمة للمستودع</a> &nbsp;•&nbsp;
    <a href="https://github.com/np4abdou1/ani-cli-arabic/issues">🐛 الإبلاغ عن خطأ</a> &nbsp;•&nbsp;
    <a href="https://github.com/np4abdou1/ani-cli-arabic/discussions">💬 النقاشات</a>
  </p>

</div>

</div>
