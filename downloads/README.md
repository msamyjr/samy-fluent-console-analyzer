# Samy TV — الإصدار الثالث

[تحميل المشروع ZIP](./Samy_Vizio_Modern_Home.zip?raw=true) · [معاينة الواجهة](./preview.png)

واجهة عربية مستوحاة من تنظيم Google TV، مع صفوف تطبيقات أفقية، ومكتبة وبحث، وزر WatchFree القديم مع فحص التطبيق الحالي، ورابط Spotify الرسمي وRTM Klik وAstro AWANI. المعاينة من متصفح محلي، وليست صورة TV.

55 اختبار Python للتطبيق + 4 اختبارات مستقلة للتحديث، واختبارا متصفح ناجحان. WatchFree+ في ماليزيا وSpotify Connect والبث على TV غير متحقق منها. Spotify والمواقع الماليزية روابط ويب وليست تثبيت APK. لا يوجد Google Play أو استبدال Firmware في هذه الحزمة.

## تحديث مجلدك الحالي

أوقف الخادم بـControl+C. من مجلد المشروع الذي يحتوي main.py وsite:

```bash
curl -fL "https://github.com/msamyjr/samy-fluent-console-analyzer/raw/refs/heads/download/samy-vizio-modern-home/downloads/update.py" -o .samy_update.py &&
python3 .samy_update.py &&
python3 main.py launch
```

المحدّث يتحقق من SHA-256، ويحفظ نسخة من ملفات التطبيق القديمة في backups/، ولا يقرأ ولا يغيّر ملف AUTH الخاص بك. لا حاجة لإعادة setup.

لفحص WatchFree منفصلًا: `python3 main.py watchfree` أو القراءة فقط `python3 main.py watchfree --check`. تطابق المعرّف لا يثبت تشغيل الفيديو أو إتاحة الخدمة في البلد.

SHA-256 للحزمة:
`eee7c791e82ca7eb9fb46bccc9d9a9b338c2e26cb953b1600033d3dcc42a1109`
