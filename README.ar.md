<div align="center" dir="rtl">

# 🎉 ani-cli-arabic v2.0 - الإصدار الرئيسي

<h2>💖 ادعم هذا المشروع المفتوح المصدر</h2>
<p>دعمك يساعدنا في صيانة الخوادم واستمرار تطوير التحديثات!</p>
<a href="https://paypal.me/np4abdou">
  <img src="https://img.shields.io/badge/Donate_with_PayPal-00457C?style=for-the-badge&logo=paypal&logoColor=white" alt="Donate with PayPal">
</a>
<br><br><br>

بث وتنزيل الأنمي مباشرة من الطرفية بترجمة عربية وإنجليزية

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

<p>To view English documentation click here: </p>
<a href="README.md">
  <img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge&logo=google-translate&logoColor=white" alt="English">
</a>

<br><br>

https://github.com/user-attachments/assets/a6c6882a-7c50-4a8d-aa9c-e56a6d4ff7eb

</div>

---

<div dir="rtl">

## 📑 التنقل السريع

[ما الجديد في الإصدار 2.0](#-ما-الجديد-في-الإصدار-20) • [التثبيت](#-التثبيت) • [كيفية الاستخدام](#-كيفية-الاستخدام) • [الميزات الرئيسية](#-الميزات-الرئيسية) • [اختصارات لوحة المفاتيح](#️-اختصارات-لوحة-المفاتيح) • [الإعدادات](#️-الإعدادات) • [المساهمون](#-المساهمون) • [الرخصة](#-الرخصة)

---

## 🚀 ما الجديد في الإصدار 2.0؟

الإصدار 2.0 يمثل أضخم تحديث وإعادة هيكلة في تاريخ المشروع:

* 🌐 **دعم خوادم ومصادر متعددة**: إمكانية المشاهدة والبحث عبر 4 مصادر مستقلة: **أنمي بالراحة (Anime3rb)**، **أنمي سلاير (Anime Slayer)**، **أنمي فاي (Animeify)**، و **HiAnime** (للبث المترجم والمدبلج بالإنجليزية).
* 📥 **أداة تنزيل جماعي مدمجة (Native Batch Downloader)**: بُنيت بالكامل من الصفر لتنزيل الحلقات مجزأة وبشكل متوازي مع دعم الاستئناف التلقائي وعرض السرعة والوقت المتبقي، **دون الحاجة لأي أدوات خارجية** (لا حاجة لـ aria2c أو yt-dlp).
* ⚡ **إعادة بناء الوضع التفاعلي السريع (`-i`)**: دعم كامل وسلس لـ `fzf`، التنقل بالماوس، حل مشاكل المحاذاة للنصوص العربية (RTL)، وقائمة إجراءات تفاعلية لكل حلقة (`مشاهدة`، `تنزيل فردي`، `تنزيل جماعي`، `تحديد الجودة`).
* 🎬 **دعم شامل لمشغلات الوسائط واستئناف ذكي**: دعم تشغيل عبر **MPV**، **VLC**، **Celluloid**، **IINA**، و **Syncplay** (للمشاهدة المتزامنة مع أصدقائك). التكامل مع MPV عبر JSON-IPC يضمن استئناف المشاهدة بدقة الثانية ونسبة المشاهدة المئوية.
* 🛡️ **بنية تحتية سحابية بثلاثة مستويات**: سلسلة انتقال تلقائي عند تعطل النطاق عبر النطاق المخصص، Cloudflare Pages، و Cloudflare Workers.
* 🔒 **تعزيز الخصوصية**: حذف تتبع سجلات المشاهدة وعزل النسخ التطويرية تماماً عن القياسات.
* 🔄 **ترقية تلقائية سلسة**: دعم التحديث التلقائي عبر PyPI (`pip`) و Arch Linux (`yay` / `paru`) و Homebrew.

---

## 📦 التثبيت

### المتطلبات الأساسية
- **بايثون 3.9 أو أحدث** (يُنصح ببايثون 3.10 - 3.12)
- **مشغل الوسائط MPV** (المشغل الافتراضي الموصى به)
- **ffmpeg** (لمعالجة وسائط الفيديو)
- **fzf** (للبحث والخيارات التفاعلية)

---

### الطريقة الأولى: التثبيت عبر pip (مُستحسن)

أسرع وأسهل طريقة على لينكس، ماك، وويندوز:

```bash
pip install ani-cli-arabic
```

تشغيل التطبيق:
```bash
ani-cli-arabic
# أو استخدام الاختصار المباشر
ani-cli-ar
```

للترقية في أي وقت:
```bash
pip install --upgrade ani-cli-arabic
```

---

### الطريقة الثانية: مستخدمو آرتش لينكس (AUR)

متاح رسمياً على مستودع مستخدمي آرتش:

```bash
# باستخدام yay
yay -S ani-cli-arabic

# باستخدام paru
paru -S ani-cli-arabic
```

---

### الطريقة الثالثة: التشغيل من المصدر

لتشغيل أحدث كود تطويري مباشرة:

```bash
# استنساخ المستودع
git clone https://github.com/np4abdou1/ani-cli-arabic.git
cd ani-cli-arabic

# تثبيت المتطلبات
pip install -r requirements.txt

# التشغيل
python3 main.py
```

---

## 🎮 كيفية الاستخدام

### 1. وضع الواجهة الطرفية الكامل (TUI)
شغّل التطبيق وتنقل بالقوائم عبر الأسهم:
```bash
ani-cli-arabic
```

### 2. الوضع التفاعلي السريع (`-i`)
للبحث والمشاهدة السريعة مباشرة عبر قوائم `fzf`:
```bash
# باللغة العربية
ani-cli-ar -i "ون بيس"

# باللغة الإنجليزية
ani-cli-ar -i "Naruto"
```

### 3. تحديد الخادم المزود من سطر الأوامر
يمكنك تحديد خادم البث مباشرة عند التشغيل:
```bash
# البث من أنمي بالراحة (عربي)
ani-cli-ar -p anime3rb "هنتر"

# البث من HiAnime (مترجم / مدبلج إنجليزي)
ani-cli-ar -p hianime "Attack on Titan"

# البث من أنمي سلاير
ani-cli-ar -p anime_slayer "Bleach"

# البث من أنمي فاي
ani-cli-ar -p animeify "Jujutsu Kaisen"
```

### 4. البحث المباشر
```bash
ani-cli-ar "Detective Conan"
```

---

## 🎯 الميزات الرئيسية

### 📺 خوادم ومصادر بث متعددة
- **Anime3rb**: سيرفرات مباشرة فائقة السرعة مع ترجمة عربية مدمجة.
- **Anime Slayer**: ربط مباشر مع خوادم وسيرفرات تطبيق أنمي سلاير.
- **Animeify**: خيارات جودة متعددة وسيرفرات احتياطية.
- **HiAnime**: بث إنجليزي سريع (Sub / Dub) مع معالجة ذكية للـ Referer وتخطي الحجب.

### 📥 أداة تنزيل جماعي أصلية
- تنزيل مواسم كاملة أو نطاق حلقات محدد (مثل `1-12` أو `1,3,5` أو `all`).
- تنزيل مجزأ متوازي مع إمكانية الإيقاف والاستئناف.
- شريط تقدم تفاعلي يوضح السرعة والوقت المتبقي والنسبة المئوية.
- بدون أي برامج خارجية إضافية.

### 🎬 مشغلات متعددة واستئناف دقيق
- **المشغلات المدعومة**: MPV، VLC، Celluloid، IINA (على ماك)، و Syncplay (للمشاهدة مع الأصدقاء عبر الإنترنت).
- **استئناف ذكي**: تتبع آني لموضع المشاهدة عبر منفذ IPC Socket لاستكمال الحلقة من الثانية ذاتها.
- **المفضلة وسجل المشاهدة**: تبويبات منظمة لتثبيت أعمالك المفضلة وسجل المشاهدة.

### 🎨 واجهة طرفية حديثة وسمات مخصصة
- **17 سمة لونية**: أزرق، أحمر، أخضر، بنفسجي، سماوي، أصفر، وردي، برتقالي، أزرق مخضر، أرجواني، ليموني، مرجاني، خزامى، ذهبي، نعناعي، زهري، الغروب.
- **حضور Discord غني (RPC)**: يعرض غلاف الأنمي واسم العمل والحلقة للمشاهدين على حسابك في ديسكورد.
- **تسوية وتطبيع البحث العربي**: معالجة ذكية لحروف الهمزة والتاء المربوطة والأخطاء الإملائية.

---

## ⌨️ اختصارات لوحة المفاتيح

### القائمة الرئيسية والتنقل
| المفتاح | الوظيفة |
| :---: | :--- |
| **↑ / ↓** أو **j / k** | التنقل عبر القوائم والعناصر |
| **Enter** | اختيار / تأكيد العنصر |
| **G** | الانتقال مباشرة إلى رقم حلقة محدد |
| **B** | العودة إلى الشاشة السابقة |
| **Q** / **Esc** | الخروج من التطبيق |
| **S** | فتح شريط البحث |
| **T** | عرض الأنميات الرائجة (Trending) |
| **R** | عرض الأنميات الأعلى تقييماً (Top Rated) |
| **F** | فتح قائمة المفضلة |
| **H** | فتح سجل المشاهدة |
| **O** | فتح قائمة الإعدادات |
| **D** | دعم المشروع (تبرع PayPal) |

### داخل المشغل (MPV)
| المفتاح | الوظيفة |
| :---: | :--- |
| **Space** | إيقاف مؤقت / استئناف التشغيل |
| **← / →** | تقديم / ترجيع 5 ثوانٍ |
| **[ / ]** | إبطاء / تسريع الفيديو |
| **F** | تبديل وضع ملء الشاشة |
| **9 / 0** | خفض / رفع الصوت |
| **Q** | إيقاف وحفظ موضع الاستئناف |

---

## ⚙️ الإعدادات

يتم تخزين الإعدادات محلياً في `~/.ani-cli-arabic/database/config.json`.

### خيارات قائمة الإعدادات (`[O]`)
- **الخادم النشط**: التبديل بين `anime3rb` و `anime_slayer` و `animeify` و `hianime`.
- **الجودة الافتراضية**: اختيار الجودة التلقائية (`1080p`، `720p`، `480p`، أو `سؤال دائماً`).
- **مشغل الوسائط**: الاختيار بين `mpv` و `vlc` و `celluloid` و `iina` و `syncplay`.
- **التشغيل التلقائي للحلقة التالية**: متابعة البث التلقائي بعد انتهاء الحلقة.
- **حضور Discord RPC**: تفعيل أو تعطيل ملصقات ديسكورد.
- **السمة اللونية**: التبديل المباشر بين 17 سمة لونية دون الحاجة لإعادة التشغيل.
- **مسار التنزيل**: تخصيص مجلد حفظ حلقات الأنمي.
- **الخصوصية والتحديثات**: تفعيل أو تعطيل القياسات المجهولة وفاحص الإصدارات التلقائي.

---

## 👥 المساهمون

شكر خاص لكل من ساهم في بناء واختبار وصيانة المشروع:

</div>

<div align="center">

[![Contributors](https://contrib.rocks/image?repo=np4abdou1/ani-cli-arabic)](https://github.com/np4abdou1/ani-cli-arabic/graphs/contributors)

</div>

<div dir="rtl">

**المساهمون الرئيسيون:**
- [@np4abdou1](https://github.com/np4abdou1) - المنشئ والمطور الرئيسي
- [@Anas-Tou](https://github.com/Anas-Tou) - مساهم
- [@ilyes-pro](https://github.com/ilyes-Pro) - مساهم

تريد المساهمة؟ يسعدنا استقبال مقترحاتك أو طلبات السحب (Pull Requests)!

---

## 📄 الرخصة

هذا المشروع مرخص بموجب **رخصة جنو العمومية الإصدار 3.0 (GPL-3.0)**. راجع ملف [LICENSE](LICENSE) للتفاصيل الكاملة.

- ✅ مجاني بالكامل للاستخدام الشخصي والتعليمي
- ✅ مفتوح المصدر ومدعوم من المجتمع
- ⚠️ أي تعديلات أو نسخ مشتقة يجب أن تظل مفتوحة المصدر تحت رخصة GPL-3.0

---

</div>

<div align="center">

صُنع بـ ❤️ من مجتمع الأنمي

[⭐ ضع نجمة للمستودع](https://github.com/np4abdou1/ani-cli-arabic) • [🐛 أبلغ عن مشكلة](https://github.com/np4abdou1/ani-cli-arabic/issues) • [💬 النقاشات](https://github.com/np4abdou1/ani-cli-arabic/discussions)

</div>
