# mdrst.py
A comprehensive academy for learning Python from scratch.

# أكاديمية بايثون

منصة عربية صغيرة قابلة للتشغيل محلياً، بواجهة متجاوبة، ووضع داكن، وحسابات مستخدمين، وتتبع تقدم ونشاط وتقييمات محفوظة في SQLite، ولوحة أدمن.

## التشغيل

يتطلب Python 3.10+ ولا يحتاج إلى حزم خارجية:

```sh
python server.py
```

ثم افتح <http://localhost:8000>. عند أول تشغيل ينشئ الخادم حساب أدمن عشوائي كلمة المرور ويحفظ بيانات الدخول في `data/admin-credentials.txt` بصلاحيات ملف خاصة؛ سجّل الدخول من زر «تسجيل الدخول». عيّن `ADMIN_EMAIL` و`ADMIN_PASSWORD` قبل أول تشغيل لاختيار بيانات الأدمن بنفسك؛ عند إنشاء الحساب لأول مرة تُحفظ كلمة المرور المشفرة في قاعدة البيانات ولا تتغير عند إعادة التشغيل.

مثال إعداد الأدمن قبل أول تشغيل:

```sh
ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD='use-a-long-unique-password' python server.py
```

لإتاحة المنصة على عنوان مختلف:

```sh
PORT=8080 python server.py
```

## محتويات المشروع

- `server.py`: خادم HTTP وواجهات JSON، المصادقة وتجزئة كلمات المرور، الجلسات، بوابة التقدم، سجل الأعطال وملخصات النشاط والتقييمات.
- `index.html`: هيكل التطبيق العربي.
- `static/style.css`: التنسيق المتجاوب والوضع الداكن.
- `static/app.js`: تسجيل الدخول، الدروس والاختبارات، عرض التقدم ولوحة الأدمن.
- `data/academy.sqlite3`: قاعدة SQLite التي تُنشأ تلقائياً.

## صلاحيات وبوابة المستويات

التسجيل العام ينشئ حساب مستخدم عادي فقط؛ لا يمكن ترقية الحساب إلى أدمن من الواجهة. يُنشأ حساب الأدمن من متغيرات البيئة عند أول تشغيل. يُحفظ إنجاز كل درس في جدول مستقل، ولا يفتح الاختبار الختامي إلا بعد إتمام الدروس الأربعة. يتكون الاختبار من أربعة أسئلة ويلزم 75% على الأقل للنجاح. يتحقق الخادم من إجابات الدروس والاختبار ومن اجتياز المستوى السابق، حتى لو تم استدعاء الواجهة البرمجية مباشرة. تظهر أعداد الدروس والمستويات المكتملة في لوحة الأدمن.

## ملاحظات النشر

المشروع مجهز كخدمة ويب واحدة على Render مع HTTPS وقرص دائم لقاعدة SQLite. قبل استقبال بيانات حقيقية، أضف سياسة خصوصية وشروط استخدام وخطة نسخ احتياطي، وجرّب التسجيل وتسجيل الدخول واستعادة الخدمة. الخادم يستخدم عامل HTTP متعدد الخيوط بعملية واحدة؛ لا ترفع عدد النسخ أفقياً مع SQLite. لا ترفع `data/` أو أسرار البيئة إلى Git.

## تطوير المحتوى من لوحة الأدمن

يحتوي قسم الأدمن على زر «أضف الدفعة التالية». كل ضغطة تنشر الدفعة التعليمية التالية فقط، ولا تكرر الدفعات السابقة. يضم المحتوى الحالي أربع دفعات، 8 دروس في كل دفعة (32 درساً إثرائياً): شرح موجز، مثال، وسؤال مراجعة موزعة على المستويات. تظهر الدروس للجميع عند فتح المستوى، ولا تغيّر شروط اجتيازه. أضف دفعات جديدة إلى `content_packs.py` لتوسيع المنهج؛ لا يمكن لأي مجموعة ثابتة أن تحوي حرفياً كل تفاصيل لغة Python ومكتباتها، لذلك تتوسع التغطية بمراجعة محتوى جديد. هذه دفعات تعليمية مكتوبة مسبقاً وليست توليداً تلقائياً؛ ربط مزود ذكاء اصطناعي يحتاج إعداداً ومراجعة بشرية للمحتوى.

## وكيل الصيانة والتطوير

`maintenance_agent.py` يعمل في خيط خلفي كل 5 دقائق افتراضياً (`AGENT_INTERVAL_SECONDS` لتغيير الفترة). يفحص SQLite، ينظف الجلسات المنتهية، يعيد إنشاء الفهارس المفقودة بطريقة idempotent، يشغّل `PRAGMA optimize`، ويلخص نشاط المستويات والأخطاء. تسجّل نتائج الفحوص في جدول `agent_reports` وتظهر داخل لوحة الأدمن؛ يمكن تشغيل الفحص يدوياً من اللوحة.

الإصلاح الذاتي هنا مقصور عمداً على إجراءات تشغيلية آمنة ومحددة. لا يعدّل الوكيل HTML أو JavaScript أو ملفات Python ولا ينفّذ اقتراحاته ككود. الأعطال التي تحتاج تغييراً برمجياً تظهر للأدمن للتحليل والمراجعة. بذلك لا تتحول رسالة خطأ أو اقتراح نموذج إلى تعديل عشوائي على الموقع.

يمكن اختيارياً توصيل نقطة نهاية متوافقة مع Chat Completions عبر متغيرات البيئة التالية:

```sh
AGENT_AI_ENDPOINT='https://your-provider.example/v1/chat/completions' \
AGENT_AI_KEY='secret-from-your-provider' \
AGENT_AI_MODEL='your-model-name' \
python server.py
```

من دون هذه الإعدادات يستخدم الوكيل قواعد محلية فقط. عند تفعيل المزود، تُرسل المؤشرات المجمعة وفئات الأخطاء وأعدادها فقط، ولا تُرسل أسماء المستخدمين أو بريدهم أو ملفات الارتباط أو نصوص رسائل الأخطاء الخام. راجع سياسة مزودك قبل تفعيل إرسال المؤشرات خارج جهازك.

## النشر العام على Render

ملف `render.yaml` ينشئ خدمة Python عامة في فرانكفورت، ويضبط نقطة فحص الصحة، والتشغيل بعملية واحدة، وقرصاً دائماً لملف SQLite. رابط `onrender.com` يُنشأ تلقائياً بعد أول نشر. الخطة المحددة `starter` والقرص الدائم مدفوعان؛ راجع التكلفة في Render قبل إنشاء الموارد. لا تستخدم تخزين SQLite مؤقتاً لاستضافة بيانات مستخدمين حقيقية.

### خطوات النشر

1. أنشئ مستودعاً خاصاً فارغاً في GitHub. من مجلد المشروع نفّذ الأوامر التالية مع استبدال الرابط برابط مستودعك. لا ترفع مجلد `data/` أو `.env` أو بيانات اعتماد الأدمن؛ `.gitignore` يستثني قاعدة البيانات المحلية.

   ```sh
   git add .
   git commit -m "Prepare Python academy for deployment"
   git branch -M main
   git remote add origin https://github.com/USERNAME/REPOSITORY.git
   git push -u origin main
   ```

2. سجّل الدخول إلى [Render](https://render.com) واختر **New + → Blueprint** ثم اربط مستودع GitHub الذي يحتوي `render.yaml`.
3. أدخل `ADMIN_EMAIL` كبريد الأدمن و`ADMIN_PASSWORD` كسرّ طويل وفريد عند طلب متغيرات البيئة. لا تستخدم كلمة مرور حساب آخر.
4. راجع الخطة والقرص الدائم والتكلفة، ثم أنشئ الـ Blueprint. Render يبني التطبيق ويشغله تلقائياً.
5. افتح رابط `onrender.com` الذي يظهر في صفحة الخدمة. تحقق من أن `/api/health` يعرض `status: ok`، ثم سجّل الدخول بحساب الأدمن وأنشئ حساب مستخدم تجريبياً.
6. النشر التلقائي مفعّل: كل commit إلى الفرع المتصل يبدأ نشر نسخة جديدة.

### Vercel with Supabase PostgreSQL

The Python API is exposed through `api/[...path].py`; the static homepage remains served from the project root. When `DATABASE_URL` is set, the application uses Supabase PostgreSQL instead of local SQLite. The function initializes the schema on cold start. For Vercel serverless functions, use the Supabase **Transaction pooler** connection string (port 6543) and keep prepared statements disabled in the driver.

1. Create a Supabase project and copy its Transaction pooler URI from **Connect**. Do not put it in browser JavaScript or commit it.
2. In Vercel → Project → Settings → Environment Variables, add `DATABASE_URL`, `ADMIN_EMAIL`, `ADMIN_PASSWORD`, and `COOKIE_SECURE=1`; use a new, unique admin password. Set `PUBLIC_PROXY=1` to respect Vercel's forwarded client IP for rate limiting.
3. Redeploy the Vercel project. On first API invocation, an empty Supabase database gets the tables and admin account. `ADMIN_EMAIL` and `ADMIN_PASSWORD` seed the admin only when no admin exists.
4. Check `/api/health` and `/api/content/extras`, then create a regular test account from the site.

Supabase stores production accounts separately from the local SQLite file; the application does not automatically import the ignored local `data/` database.

## الظهور في بحث Google

أضفت `robots.txt` و`sitemap.xml` ووصف الصفحة والروابط الاجتماعية وcanonical للنطاق `https://mdrst.py/`. بعد ربط النطاق ونشر الموقع:

1. أضف النطاق كخاصية في [Google Search Console](https://search.google.com/search-console) وأكّد ملكيته عبر DNS.
2. أرسل `https://mdrst.py/sitemap.xml` في تقرير **Sitemaps**.
3. استخدم **URL Inspection** لطلب فهرسة الصفحة الرئيسية.

هذه الخطوات تساعد Google على اكتشاف الصفحة، لكنها لا تضمن ترتيباً أو ظهوراً فورياً؛ يجب أن يكون الموقع عاماً ويمكن لـ Google الوصول إليه. راجع [إرشادات Google لإعادة الزحف والفهرسة](https://developers.google.com/search/docs/crawling-indexing/ask-google-to-recrawl).

### استخدام النطاق `mdrst.py`

`.py` نطاق دولة باراغواي، و`mdrst.py` يتطلب تسجيل النطاق أو امتلاك حق استخدامه لدى مسجل النطاقات. ملف Blueprint لا يربطه تلقائياً كي لا يفشل النشر إذا لم يكن النطاق مملوكاً. بعد امتلاك نطاق صالح: من إعدادات خدمة Render أضفه تحت **Custom Domains**، ثم أضف سجلات DNS التي يعرضها Render لدى المسجل، وانتظر التحقق وإصدار شهادة TLS. يمكن استخدام رابط `onrender.com` إلى أن يكتمل ذلك. [قاعدة IANA للنطاقات العليا](https://www.iana.org/domains/root/db/py) · [تعليمات Render للنطاقات المخصصة](https://render.com/docs/custom-domains).

### الأسرار والتخزين

- `ADMIN_EMAIL` و`ADMIN_PASSWORD` يُستخدمان لإنشاء حساب الأدمن عند أول تشغيل فقط. تغييرهُما لاحقاً لا يغيّر كلمة مرور حساب موجود.
- `ACADEMY_DATA_DIR=/var/data` والقرص الدائم يحفظان قاعدة البيانات عند إعادة النشر.
- `COOKIE_SECURE=1` يفعّل كوكيز الجلسة الآمنة وHSTS خلف HTTPS.
- خذ نسخاً احتياطية منتظمة من بيانات الإنتاج، واختبر الاستعادة قبل الاعتماد عليها. لا تعتبر قرص الخدمة وحده نسخة احتياطية.

## طبقات الحماية

- كلمات المرور لا تُخزّن كنص؛ تُخزّن بتجزئة PBKDF2-HMAC-SHA256 وملح مستقل (600,000 دورة). عند أول دخول صحيح تُرقّى التجزئات القديمة تلقائياً.
- الجلسات رموز عشوائية، والخادم يحفظ بصمتها فقط. على Render تستخدم الكوكيز `Secure`, `HttpOnly`, `SameSite=Strict` وبادئة `__Host-`، مع HSTS ورؤوس حماية المتصفح.
- توجد حدود لمحاولات تسجيل الدخول وإنشاء الحسابات، وفحص `Origin` للطلبات التي ترسل ذلك الرأس، واستعلامات SQLite معلّمة بالمعاملات.
- استخدم HTTPS عند النشر العام. إخفاء/تشويش JavaScript لا يحمي الأسرار؛ لا تضع مفاتيح أو كلمات مرور في ملفات المتصفح.

قاعدة SQLite المحلية ليست مشفّرة على مستوى التطبيق. إعداد Render يستخدم قرصاً دائماً، ويذكر Render أن الأقراص مشفّرة عند التخزين؛ إذا انتقلت إلى استضافة أخرى فتحقق من تشفير القرص والنسخ الاحتياطية لديها أو استخدم قاعدة بيانات مُدارة تدعم ذلك. احتفظ بكلمة مرور `ADMIN_PASSWORD` ومفاتيح مزود الذكاء الاصطناعي في أسرار الاستضافة فقط.
