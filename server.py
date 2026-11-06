"""Python Academy: SQLite locally or Supabase PostgreSQL in serverless production."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, urlsplit
from pathlib import Path
import sqlite3, json, secrets, hashlib, hmac, os, time, datetime, threading, re
from maintenance_agent import MaintenanceAgent
from content_packs import EXTRA_LESSON_BATCHES
from database import USE_POSTGRES, connect as db_connect, is_unique_error

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get('ACADEMY_DATA_DIR') or os.environ.get('DATA_DIR') or str(ROOT / 'data')).resolve()
DB = DATA_DIR / 'academy.sqlite3'
ADMIN_FILE = DATA_DIR / 'admin-credentials.txt'
COURSES = [
 {'id':'beginner','title':'المبتدئ','en':'Beginner','icon':'🌱','description':'أساسيات بايثون، المتغيرات، أنواع البيانات، الشروط والحلقات','lessons':4},
 {'id':'intermediate','title':'المتوسط','en':'Intermediate','icon':'🧩','description':'الدوال، القوائم والقواميس والصفوف والتعامل مع الملفات','lessons':4},
 {'id':'advanced','title':'المتقدم','en':'Advanced','icon':'🚀','description':'البرمجة كائنية التوجه، الاستثناءات والوحدات','lessons':4},
 {'id':'expert','title':'المحترف','en':'Expert','icon':'💎','description':'مشاريع عملية، الاختبارات، الكود النظيف والمهارات الاحترافية','lessons':4},
]
# Server-side answer keys enforce lesson completion and final level exams.
LESSON_ANSWER_KEYS = {'beginner':[1,1,1,1], 'intermediate':[1,0,1,1], 'advanced':[1,1,1,1], 'expert':[0,1,0,1]}
COURSE_EXAM_ANSWERS = LESSON_ANSWER_KEYS
# Curated enrichment pack. Admin activation publishes these additions to every learner.
EXTRA_LESSON_PACK = [
 {'id':'beginner-fstrings','course':'beginner','title':'تنسيق النصوص باستخدام f-strings','summary':'تُدخل f-string قيمة المتغير داخل النص مباشرة. ضع الحرف f قبل علامة الاقتباس، واكتب اسم المتغير بين أقواس معقوفة.','code':'name = "مازن"\nlessons = 3\nprint(f"أهلاً {name}، لديك {lessons} دروس")','question':'كيف نُدرج قيمة متغير داخل f-string؟','options':['نكتب اسمه بين { }','نضيفه بعد النص بفاصلة منقوطة','نضعه بين [ ]'],'answer':0},
 {'id':'beginner-debugging','course':'beginner','title':'اكتشاف الأخطاء وقراءة الرسائل','summary':'اقرأ آخر سطر في رسالة الخطأ أولاً لمعرفة نوع المشكلة، ثم راجع اسم الملف ورقم السطر. جرّب تغييراً صغيراً وأعد التشغيل.','code':'age_text = "20"\nage = int(age_text)  # تحويل النص إلى عدد\nprint(age + 1)','question':'ما نوع الخطأ المتوقع عند int("عشرون")؟','options':['ValueError','حساب خاطئ بصمت','لا يحدث خطأ'],'answer':0},
 {'id':'intermediate-comprehensions','course':'intermediate','title':'إنشاء القوائم بتعبير مختصر','summary':'تعبير إنشاء القائمة يبني قائمة جديدة من عناصر متتابعة. ابدأ بالتعبير، ثم for، ويمكن إضافة if للتصفية.','code':'numbers = [1, 2, 3, 4]\nsquares = [n * n for n in numbers if n % 2 == 0]\nprint(squares)  # [4, 16]','question':'ما ناتج squares؟','options':['[1, 4, 9, 16]','[4, 16]','[2, 4]'],'answer':1},
 {'id':'intermediate-dict-get','course':'intermediate','title':'الوصول الآمن إلى القواميس','summary':'تُرجع get القيمة عند وجود المفتاح، ويمكن تحديد قيمة افتراضية عند غيابه؛ وهذا يمنع KeyError في البيانات الاختيارية.','code':'settings = {"theme": "dark"}\nlanguage = settings.get("language", "ar")\nprint(language)','question':'ما القيمة المطبوعة؟','options':['None','ar','KeyError'],'answer':1},
 {'id':'advanced-dataclass','course':'advanced','title':'تنظيم بيانات الكائن باستخدام dataclass','summary':'تختصر dataclass الشيفرة المتكررة للأصناف التي تخزن بيانات، مثل دوال التهيئة والمقارنة.','code':'from dataclasses import dataclass\n\n@dataclass\nclass Book:\n    title: str\n    pages: int\n\nbook = Book("بايثون", 240)\nprint(book.title)','question':'ما الذي تولّده dataclass تلقائياً عادةً؟','options':['دالة تهيئة للحقول','اتصالاً بقاعدة البيانات','واجهة رسومية'],'answer':0},
 {'id':'advanced-custom-errors','course':'advanced','title':'إنشاء استثناءات واضحة للمشروع','summary':'أنشئ نوع استثناء خاصاً عندما يحتاج المستهلك إلى التمييز بين خطأ متوقع في المجال وأخطاء بايثون العامة.','code':'class InsufficientFundsError(Exception):\n    pass\n\ndef withdraw(balance, amount):\n    if amount > balance:\n        raise InsufficientFundsError("الرصيد غير كافٍ")\n    return balance - amount','question':'من أي صنف ترث عادةً الاستثناءات المخصصة؟','options':['Exception','str','list'],'answer':0},
 {'id':'expert-type-hints','course':'expert','title':'تلميحات الأنواع لتوضيح واجهات الدوال','summary':'توضح تلميحات الأنواع شكل المدخلات والمخرجات للمطور وأدوات الفحص. لا تستبدل اختبارات التشغيل ولا تتحقق من الأنواع تلقائياً وقت التنفيذ.','code':'def calculate_total(prices: list[float]) -> float:\n    # احسب الإجمالي\n    return sum(prices)','question':'هل تتحقق Python تلقائياً من type hints أثناء التشغيل؟','options':['نعم دائماً','لا؛ هي توثيق وأساس لأدوات الفحص','فقط داخل الحلقات'],'answer':1},
 {'id':'expert-logging','course':'expert','title':'تسجيل الأحداث بدلاً من الطباعة العشوائية','summary':'يسمح logging بتحديد مستوى الرسالة وصيغتها ومكان إخراجها. استخدم info للأحداث المعتادة وexception داخل except لتضمين تفاصيل الخطأ.','code':'import logging\n\nlogging.basicConfig(level=logging.INFO)\ntry:\n    result = 10 / 0\nexcept ZeroDivisionError:\n    logging.exception("تعذر حساب النتيجة")','question':'ما الذي يضيفه logging.exception داخل except؟','options':['تفاصيل الاستثناء إلى سجل الخطأ','إصلاح الخطأ تلقائياً','إعادة تشغيل البرنامج'],'answer':0},
]
LOCK = threading.Lock()
AGENT = MaintenanceAgent(DB)
COOKIE_NAME = '__Host-academy_session' if os.environ.get('COOKIE_SECURE')=='1' else 'academy_session'
AUTH_FAILURES = {}  # In-memory brute-force throttle, keyed by operation and client.
AUTH_WINDOW = 15 * 60
AUTH_LIMIT = 8

def connect():
 return db_connect(DB, timeout=15)
def init_db():
 if os.environ.get('VERCEL') and not USE_POSTGRES:
  raise RuntimeError('Set DATABASE_URL to a Supabase PostgreSQL connection string in Vercel')
 if not USE_POSTGRES: DATA_DIR.mkdir(parents=True, exist_ok=True)
 with connect() as c:
  if USE_POSTGRES:
   c.execute("""CREATE TABLE IF NOT EXISTS users(id BIGSERIAL PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',created_at TEXT NOT NULL,last_active TEXT NOT NULL)""")
   c.execute("""CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires BIGINT NOT NULL)""")
   c.execute("""CREATE TABLE IF NOT EXISTS progress(user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,course TEXT NOT NULL,completed INTEGER NOT NULL DEFAULT 0,quiz_score INTEGER NOT NULL DEFAULT 0,activity_count INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,course))""")
   c.execute("""CREATE TABLE IF NOT EXISTS lesson_progress(user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,course TEXT NOT NULL,lesson_index INTEGER NOT NULL,completed INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,course,lesson_index))""")
   c.execute("""CREATE TABLE IF NOT EXISTS extra_lessons(id TEXT PRIMARY KEY,course TEXT NOT NULL,title TEXT NOT NULL,summary TEXT NOT NULL,code TEXT NOT NULL,question TEXT NOT NULL,options TEXT NOT NULL,answer INTEGER NOT NULL,created_at TEXT NOT NULL,batch INTEGER NOT NULL DEFAULT 1)""")
   c.execute("""CREATE TABLE IF NOT EXISTS ratings(user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,course TEXT NOT NULL,score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),updated_at TEXT NOT NULL,PRIMARY KEY(user_id,course))""")
   c.execute("""CREATE TABLE IF NOT EXISTS events(id BIGSERIAL PRIMARY KEY,kind TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL,resolved INTEGER NOT NULL DEFAULT 0)""")
   c.execute("""CREATE TABLE IF NOT EXISTS insights(id BIGSERIAL PRIMARY KEY,message TEXT NOT NULL,created_at TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'suggestion')""")
   c.execute("""CREATE TABLE IF NOT EXISTS agent_reports(id BIGSERIAL PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,summary TEXT NOT NULL,signals TEXT NOT NULL,actions TEXT NOT NULL)""")
  else:
   c.raw.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',created_at TEXT NOT NULL,last_active TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires INTEGER NOT NULL);
   CREATE TABLE IF NOT EXISTS progress(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course TEXT NOT NULL,completed INTEGER NOT NULL DEFAULT 0,quiz_score INTEGER NOT NULL DEFAULT 0,activity_count INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,course));
   CREATE TABLE IF NOT EXISTS lesson_progress(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course TEXT NOT NULL,lesson_index INTEGER NOT NULL,completed INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL,PRIMARY KEY(user_id,course,lesson_index));
   CREATE TABLE IF NOT EXISTS extra_lessons(id TEXT PRIMARY KEY,course TEXT NOT NULL,title TEXT NOT NULL,summary TEXT NOT NULL,code TEXT NOT NULL,question TEXT NOT NULL,options TEXT NOT NULL,answer INTEGER NOT NULL,created_at TEXT NOT NULL,batch INTEGER NOT NULL DEFAULT 1);
   CREATE TABLE IF NOT EXISTS ratings(user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,course TEXT NOT NULL,score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),updated_at TEXT NOT NULL,PRIMARY KEY(user_id,course));
   CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY,kind TEXT NOT NULL,message TEXT NOT NULL,created_at TEXT NOT NULL,resolved INTEGER NOT NULL DEFAULT 0);
   CREATE TABLE IF NOT EXISTS insights(id INTEGER PRIMARY KEY,message TEXT NOT NULL,created_at TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'suggestion');''')
  if USE_POSTGRES:
   extra_columns={r['column_name'] for r in c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=current_schema() AND table_name='extra_lessons'").fetchall()}
  else:
   extra_columns={r['name'] for r in c.execute('PRAGMA table_info(extra_lessons)').fetchall()}
  if 'batch' not in extra_columns:c.execute('ALTER TABLE extra_lessons ADD COLUMN batch INTEGER NOT NULL DEFAULT 1')
  # Preserve lesson visibility for accounts that completed levels before lesson tracking existed.
  legacy=c.execute('SELECT user_id,course FROM progress WHERE completed=1').fetchall()
  for row in legacy:
   for lesson_index in range(4):
    c.execute('INSERT INTO lesson_progress(user_id,course,lesson_index,completed,updated_at) VALUES(?,?,?,1,?) ON CONFLICT(user_id,course,lesson_index) DO NOTHING',(row['user_id'],row['course'],lesson_index,utcnow()))
  admin_email=os.environ.get('ADMIN_EMAIL','admin@academy.local').strip().lower()
  admin_password=os.environ.get('ADMIN_PASSWORD')
  row=c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1").fetchone()
  if not row:
   if not admin_password:
    if USE_POSTGRES: raise RuntimeError('Set ADMIN_EMAIL and ADMIN_PASSWORD before the first Supabase initialization')
    admin_password=secrets.token_urlsafe(15)
    ADMIN_FILE.write_text(f'Admin login\nEmail: {admin_email}\nPassword: {admin_password}\nChange these credentials by setting ADMIN_EMAIL and ADMIN_PASSWORD before first launch.\n',encoding='utf-8')
    try: os.chmod(ADMIN_FILE,0o600)
    except OSError: pass
   now=utcnow();c.execute('INSERT INTO users(email,name,password,role,created_at,last_active) VALUES(?,?,?,?,?,?)',(admin_email,'مدير المنصة',hashpw(admin_password),'admin',now,now))
   print(f'\nAdmin account created: {admin_email}\nCredentials saved privately in {ADMIN_FILE}\n')
def ensure_db_schema():
 # A newly configured serverless database may be reachable before its schema
 # has been initialized. Bootstrap only when the primary table is missing.
 try:
  with connect() as c:c.execute('SELECT 1 FROM extra_lessons LIMIT 0')
 except Exception as exc:
  if getattr(exc,'sqlstate',None)=='42P01' or 'no such table' in str(exc).lower():
   init_db()
  else:
   raise

def utcnow(): return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')
def hashpw(p,salt=None):
 # PBKDF2 is a one-way password hash: the original password is never stored.
 salt=salt or secrets.token_bytes(16); rounds=600000
 digest=hashlib.pbkdf2_hmac('sha256',p.encode(),salt,rounds)
 return f'{salt.hex()}:{rounds}:{digest.hex()}'
def checkpw(p,encoded):
 try:
  fields=encoded.split(':')
  if len(fields)==2: salt_hex,digest_hex=fields;rounds=240000  # legacy hashes migrate after a successful login
  else: salt_hex,rounds_text,digest_hex=fields;rounds=int(rounds_text)
  actual=hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt_hex),rounds).hex()
  return hmac.compare_digest(actual,digest_hex)
 except Exception:return False

def safeuser(r): return {'id':r['id'],'email':r['email'],'name':r['name'],'role':r['role'],'created_at':r['created_at']}
def report_event(kind,message):
 with connect() as c:c.execute('INSERT INTO events(kind,message,created_at) VALUES(?,?,?)',(kind,str(message)[:500],utcnow()))
class Handler(SimpleHTTPRequestHandler):
 server_version='Academy'
 sys_version=''
 def version_string(self):return 'Academy'
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT),**kwargs)
 def log_message(self,fmt,*args): pass
 def end_headers(self):
  # Defense-in-depth response headers. TLS/HSTS are enabled only behind HTTPS.
  self.send_header('X-Content-Type-Options','nosniff')
  self.send_header('X-Frame-Options','DENY')
  self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
  self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
  self.send_header('Content-Security-Policy',"frame-ancestors 'none'; object-src 'none'; base-uri 'self'; form-action 'self'")
  if os.environ.get('COOKIE_SECURE')=='1':self.send_header('Strict-Transport-Security','max-age=31536000; includeSubDomains')
  super().end_headers()
 def client_ip(self):
  # Trust the proxy header only on deployments explicitly configured behind a proxy.
  if os.environ.get('PUBLIC_PROXY')=='1':
   chain=self.headers.get('X-Forwarded-For','').split(',')
   if chain and chain[-1].strip():return chain[-1].strip()[:64]
  return self.client_address[0]
 def rate_limited(self,scope,identity,limit=AUTH_LIMIT,window=AUTH_WINDOW):
  now=time.monotonic();key=(scope,identity)
  with LOCK:
   recent=[t for t in AUTH_FAILURES.get(key,[]) if now-t<window]
   AUTH_FAILURES[key]=recent
   # Bound memory if many distinct IPs hit the endpoint.
   if len(AUTH_FAILURES)>5000:
    for old in list(AUTH_FAILURES)[:1000]:AUTH_FAILURES.pop(old,None)
   return len(recent)>=limit
 def fail_auth(self,scope,identity):
  with LOCK:AUTH_FAILURES.setdefault((scope,identity),[]).append(time.monotonic())
 def clear_auth_failures(self,scope,identity):
  with LOCK:AUTH_FAILURES.pop((scope,identity),None)
 def send_json(self,data,status=200):
  raw=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)
 def body(self):
  n=min(int(self.headers.get('Content-Length','0')),100000);return json.loads(self.rfile.read(n) or b'{}')
 def user(self):
  token='';
  for p in self.headers.get('Cookie','').split(';'):
   if p.strip().startswith(COOKIE_NAME+'='):token=p.strip().split('=',1)[1]
  if not token:return None
  digest=hashlib.sha256(token.encode()).hexdigest()
  with connect() as c:
   r=c.execute('SELECT u.* FROM sessions s JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires>?',(digest,int(time.time()))).fetchone()
   if r:c.execute('UPDATE users SET last_active=? WHERE id=?',(utcnow(),r['id']))
   return r
 def require(self,admin=False):
  u=self.user()
  if not u:self.send_json({'error':'يلزم تسجيل الدخول'},401);return None
  if admin and u['role']!='admin':self.send_json({'error':'هذه الصفحة متاحة للأدمن فقط'},403);return None
  return u
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/api/health':
   # Check the actual serverless database path too; a process-only health
   # response can hide broken Supabase configuration and missing schema.
   try:
    ensure_db_schema()
    with connect() as c:
     count=c.execute('SELECT COUNT(*) AS n FROM extra_lessons').fetchone()['n']
    return self.send_json({'status':'ok','database':'ok','extra_lessons':count})
   except Exception as exc:
    # Return a sanitized provider/network hint; never expose URI credentials.
    detail=str(exc).replace(os.environ.get('DATABASE_URL',''), '[DATABASE_URL]') if os.environ.get('DATABASE_URL') else str(exc)
    detail=re.sub(r'(postgres(?:ql)?://)[^/@\s]+@', r'\1[credentials]@', detail)
    return self.send_json({'status':'degraded','database':'error','error_type':type(exc).__name__,'sqlstate':getattr(exc,'sqlstate',None),'detail':detail[:300]},503)
  if p=='/api/content/extras':
   ensure_db_schema()
   with connect() as c: rows=c.execute('SELECT id,course,title,summary,code,question,options,answer,batch FROM extra_lessons ORDER BY batch,course,id').fetchall()
   lessons=[dict(x)|{'options':json.loads(x['options'])} for x in rows]
   return self.send_json({'lessons':lessons})
  if p=='/api/me':
   u=self.user();
   if not u:return self.send_json({'user':None})
   with connect() as c:
    rows=c.execute('SELECT course,completed,quiz_score,activity_count,updated_at FROM progress WHERE user_id=?',(u['id'],)).fetchall()
    ratings=c.execute('SELECT course,score FROM ratings WHERE user_id=?',(u['id'],)).fetchall()
    lessons=c.execute('SELECT course,lesson_index,completed FROM lesson_progress WHERE user_id=?',(u['id'],)).fetchall()
   return self.send_json({'user':safeuser(u),'progress':[dict(x) for x in rows],'lesson_progress':[dict(x) for x in lessons],'ratings':[dict(x) for x in ratings],'courses':COURSES})
  if p=='/api/admin/overview':
   u=self.require(True)
   if not u:return
   with connect() as c:
    users=c.execute("SELECT id,email,name,role,created_at,last_active FROM users ORDER BY created_at DESC").fetchall()
    rows=c.execute('SELECT user_id,course,completed,quiz_score,activity_count,updated_at FROM progress').fetchall()
    lessons=c.execute('SELECT user_id,course,lesson_index,completed FROM lesson_progress').fetchall()
    ratings=c.execute('SELECT user_id,course,score,updated_at FROM ratings').fetchall()
    events=c.execute('SELECT * FROM events ORDER BY id DESC LIMIT 30').fetchall()
    extra_count=c.execute('SELECT COUNT(*) n FROM extra_lessons').fetchone()['n']
    extra_batch=c.execute('SELECT COALESCE(MAX(batch),0) n FROM extra_lessons').fetchone()['n']
    total=c.execute("SELECT COUNT(*) n FROM users WHERE role='user'").fetchone()['n'];active=c.execute("SELECT COUNT(*) n FROM users WHERE role='user' AND last_active>=?",( (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=7)).isoformat(timespec='seconds'),)).fetchone()['n']
   return self.send_json({'users':[safeuser(x)|{'last_active':x['last_active']} for x in users if x['role']=='user'],'progress':[dict(x) for x in rows],'lesson_progress':[dict(x) for x in lessons],'ratings':[dict(x) for x in ratings],'events':[dict(x) for x in events],'agent_reports':AGENT.latest(5),'stats':{'users':total,'active':active,'errors':sum(1 for x in events if x['kind']=='error'),'courses':len(COURSES),'average_rating':round(sum(x['score'] for x in ratings)/len(ratings),1) if ratings else 0,'extra_lessons':extra_count,'extra_batch':extra_batch,'extra_batches_total':1+len(EXTRA_LESSON_BATCHES)}})
  # Expose only the public site shell and static assets; never serve source, .git, or database files.
  public_paths={'/','/index.html','/robots.txt','/sitemap.xml','/googlea44b177decab6a22.html'}
  if p in public_paths:
   relative='index.html' if p=='/' else p.lstrip('/')
   candidate=(ROOT/relative).resolve()
   if candidate.is_relative_to(ROOT) and candidate.is_file():return super().do_GET()
  elif p.startswith('/static/'):
   static_root=(ROOT/'static').resolve();candidate=(ROOT/p.lstrip('/')).resolve()
   if candidate.is_relative_to(static_root) and candidate.is_file():return super().do_GET()
  return self.send_json({'error':'المسار غير موجود'},404)
 def do_POST(self):
  p=urlparse(self.path).path
  origin=self.headers.get('Origin')
  if origin and urlsplit(origin).netloc.lower()!=self.headers.get('Host','').lower():return self.send_json({'error':'الطلب من مصدر غير موثوق'},403)
  try:d=self.body()
  except Exception:return self.send_json({'error':'بيانات الطلب غير صالحة'},400)
  if p=='/api/register':
   email=str(d.get('email','')).strip().lower();name=str(d.get('name','')).strip();pw=str(d.get('password',''))
   identity=self.client_ip()+':'+hashlib.sha256(email.encode()).hexdigest()
   if self.rate_limited('register',identity,limit=5,window=3600):return self.send_json({'error':'طلبات إنشاء الحساب كثيرة. حاول لاحقاً.'},429)
   if len(name)<2 or len(name)>70 or '@' not in email or len(pw)<10:
    self.fail_auth('register',identity)
    return self.send_json({'error':'أدخل اسماً وبريداً صحيحاً وكلمة مرور من 10 أحرف على الأقل'},400)
   now=utcnow()
   try:
    with connect() as c:uid=c.execute('INSERT INTO users(email,name,password,created_at,last_active) VALUES(?,?,?,?,?) RETURNING id',(email,name,hashpw(pw),now,now)).fetchone()['id']
   except Exception as exc:
    if not is_unique_error(exc): raise
    self.fail_auth('register',identity)
    return self.send_json({'error':'هذا البريد مسجل مسبقاً'},409)
   self.clear_auth_failures('register',identity)
   return self.login(uid)
  if p=='/api/login':
   email=str(d.get('email','')).strip().lower();pw=str(d.get('password',''))
   identity=self.client_ip()+':'+hashlib.sha256(email.encode()).hexdigest()
   if self.rate_limited('login',identity):return self.send_json({'error':'محاولات كثيرة. انتظر 15 دقيقة ثم حاول مجدداً.'},429)
   with connect() as c:r=c.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
   if not r or not checkpw(pw,r['password']):
    self.fail_auth('login',identity)
    return self.send_json({'error':'البريد الإلكتروني أو كلمة المرور غير صحيحين'},401)
   self.clear_auth_failures('login',identity)
   fields=r['password'].split(':')
   if len(fields)==2 or int(fields[1])<600000:
    with connect() as c:c.execute('UPDATE users SET password=? WHERE id=?',(hashpw(pw),r['id']))
   return self.login(r['id'])
  if p=='/api/logout':
   token=self.session_token()
   if token:
    with connect() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
   self.send_response(200);self.send_header('Set-Cookie',COOKIE_NAME+'=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'+('; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''));self.send_header('Content-Length','0');self.end_headers();return
  if p=='/api/activity':
   u=self.require()
   if not u:return
   course=str(d.get('course',''))
   if course not in [x['id'] for x in COURSES]:return self.send_json({'error':'المستوى غير معروف'},400)
   with connect() as c:
    idx=[x['id'] for x in COURSES].index(course)
    if idx and not c.execute('SELECT 1 FROM progress WHERE user_id=? AND course=? AND completed=1 AND quiz_score>=70',(u['id'],COURSES[idx-1]['id'])).fetchone():return self.send_json({'error':'المستوى مقفل حتى اجتياز المستوى السابق'},403)
    c.execute('INSERT INTO progress(user_id,course,completed,quiz_score,activity_count,updated_at) VALUES(?,?,0,0,1,?) ON CONFLICT(user_id,course) DO UPDATE SET activity_count=activity_count+1,updated_at=excluded.updated_at',(u['id'],course,utcnow()))
   return self.send_json({'ok':True})
  if p=='/api/rating':
   u=self.require()
   if not u:return
   course=str(d.get('course',''));score=int(d.get('score',0))
   if course not in [x['id'] for x in COURSES] or score not in range(1,6):return self.send_json({'error':'التقييم يجب أن يكون من نجمة إلى خمس نجوم'},400)
   with connect() as c:c.execute('INSERT INTO ratings(user_id,course,score,updated_at) VALUES(?,?,?,?) ON CONFLICT(user_id,course) DO UPDATE SET score=excluded.score,updated_at=excluded.updated_at',(u['id'],course,score,utcnow()))
   return self.send_json({'ok':True})
  if p=='/api/lesson':
   u=self.require()
   if not u:return
   course=str(d.get('course',''))
   try:lesson=int(d.get('lesson',-1));answer=int(d.get('answer',-1))
   except (TypeError,ValueError):lesson=answer=-1
   if course not in LESSON_ANSWER_KEYS or lesson not in range(4):return self.send_json({'error':'الدرس غير معروف'},400)
   idx=[x['id'] for x in COURSES].index(course)
   with connect() as c:
    if idx and not c.execute('SELECT 1 FROM progress WHERE user_id=? AND course=? AND completed=1 AND quiz_score>=70',(u['id'],COURSES[idx-1]['id'])).fetchone():return self.send_json({'error':'المستوى مقفل حتى اجتياز المستوى السابق'},403)
    if answer!=LESSON_ANSWER_KEYS[course][lesson]:return self.send_json({'error':'الإجابة غير صحيحة. راجع الدرس وحاول مجدداً.'},400)
    c.execute('INSERT INTO lesson_progress(user_id,course,lesson_index,completed,updated_at) VALUES(?,?,?,1,?) ON CONFLICT(user_id,course,lesson_index) DO UPDATE SET completed=1,updated_at=excluded.updated_at',(u['id'],course,lesson,utcnow()))
   return self.send_json({'ok':True,'lesson':lesson,'completed':True})
  if p=='/api/progress':
   u=self.require()
   if not u:return
   course=str(d.get('course',''));done=int(bool(d.get('completed')))
   if course not in LESSON_ANSWER_KEYS:return self.send_json({'error':'المستوى غير معروف'},400)
   answers=d.get('answers',[])
   if not isinstance(answers,list) or len(answers)!=4:return self.send_json({'error':'أجب عن أسئلة الاختبار الأربعة'},400)
   try:answers=[int(x) for x in answers]
   except (TypeError,ValueError):return self.send_json({'error':'إجابات الاختبار غير صالحة'},400)
   score=round(sum(a==b for a,b in zip(answers,COURSE_EXAM_ANSWERS[course]))*100/4)
   if not done or score<75:return self.send_json({'error':'يلزم الحصول على 75٪ على الأقل لاجتياز الاختبار'},403)
   idx=[x['id'] for x in COURSES].index(course)
   with connect() as c:
    if idx and not c.execute('SELECT 1 FROM progress WHERE user_id=? AND course=? AND completed=1 AND quiz_score>=70',(u['id'],COURSES[idx-1]['id'])).fetchone():return self.send_json({'error':'اجتز المستوى السابق بنسبة 70٪ أولاً'},403)
    lessons_done=c.execute('SELECT COUNT(*) n FROM lesson_progress WHERE user_id=? AND course=? AND completed=1',(u['id'],course)).fetchone()['n']
    already=c.execute('SELECT completed FROM progress WHERE user_id=? AND course=?',(u['id'],course)).fetchone()
    if lessons_done<4 and not (already and already['completed']):return self.send_json({'error':'أكمل الدروس الأربعة قبل الاختبار الختامي'},403)
    c.execute('INSERT INTO progress VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,course) DO UPDATE SET completed=CASE WHEN completed>excluded.completed THEN completed ELSE excluded.completed END,quiz_score=CASE WHEN quiz_score>excluded.quiz_score THEN quiz_score ELSE excluded.quiz_score END,activity_count=activity_count+1,updated_at=excluded.updated_at',(u['id'],course,done,score,1,utcnow()))
   return self.send_json({'ok':True,'score':score})
  if p=='/api/event':
   kind=str(d.get('kind','error'));message=str(d.get('message',''))
   if kind not in ('error','feedback'):kind='error'
   report_event(kind,message);return self.send_json({'ok':True})
  if p=='/api/admin/content/evolve':
   u=self.require(True)
   if not u:return
   with connect() as c: current_batch=c.execute('SELECT COALESCE(MAX(batch),0) n FROM extra_lessons').fetchone()['n']
   next_batch=current_batch+1;total_batches=1+len(EXTRA_LESSON_BATCHES)
   if next_batch>total_batches:
    with connect() as c: rows=c.execute('SELECT id,course,title,summary,code,question,options,answer,batch FROM extra_lessons ORDER BY batch,course,id').fetchall()
    lessons=[dict(x)|{'options':json.loads(x['options'])} for x in rows]
    return self.send_json({'ok':True,'added':0,'total_batches':total_batches,'batch':current_batch,'complete':True,'lessons':lessons,'message':'وصل المنهج إلى نهاية جميع الدفعات المنشورة حالياً.'})
   pack=EXTRA_LESSON_PACK if next_batch==1 else EXTRA_LESSON_BATCHES[next_batch-2]
   now=utcnow();added=0
   with connect() as c:
    for lesson in pack:
     cur=c.execute('INSERT INTO extra_lessons(id,course,title,summary,code,question,options,answer,created_at,batch) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING',(lesson['id'],lesson['course'],lesson['title'],lesson['summary'],lesson['code'],lesson['question'],json.dumps(lesson['options'],ensure_ascii=False),lesson['answer'],now,next_batch))
     added+=cur.rowcount
    total=c.execute('SELECT COUNT(*) n FROM extra_lessons').fetchone()['n']
   if added:report_event('feedback',f'Admin published content batch {next_batch} with {added} lessons')
   with connect() as c: rows=c.execute('SELECT id,course,title,summary,code,question,options,answer,batch FROM extra_lessons ORDER BY batch,course,id').fetchall()
   lessons=[dict(x)|{'options':json.loads(x['options'])} for x in rows]
   return self.send_json({'ok':True,'added':added,'total':total,'batch':next_batch,'total_batches':total_batches,'complete':next_batch>=total_batches,'lessons':lessons,'message':f'تم نشر الدفعة {next_batch} من {total_batches} وإضافة {added} دروس.' if added else f'الدفعة {next_batch} منشورة بالفعل.'})
  if p=='/api/admin/agent/run':
   u=self.require(True)
   if not u:return
   try:return self.send_json(AGENT.run_once())
   except Exception as exc:
    report_event('error',f'maintenance-agent failure: {type(exc).__name__}')
    return self.send_json({'error':'تعذر تشغيل فحص الوكيل؛ راجع سجل الخادم'},500)
  if p=='/api/admin/insights':
   u=self.require(True)
   if not u:return
   with connect() as c:
    active=c.execute("SELECT COUNT(*) n FROM users WHERE role='user' AND last_active>=?",((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=7)).isoformat(timespec='seconds'),)).fetchone()['n']
    done=c.execute('SELECT COUNT(*) n FROM progress WHERE completed=1').fetchone()['n'];err=c.execute("SELECT COUNT(*) n FROM events WHERE kind='error' AND created_at>=?",((datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=1)).isoformat(timespec='seconds'),)).fetchone()['n']
    suggestions=[]
    if err:suggestions.append(f'رُصد {err} خطأ خلال آخر 24 ساعة؛ راجع سجل الأعطال قبل نشر التغييرات.')
    if active==0:suggestions.append('لا يوجد نشاط مسجل خلال الأسبوع الأخير؛ راجع تجربة التسجيل وتذكيرات العودة.')
    if done==0:suggestions.append('لم تُسجّل مستويات مكتملة بعد؛ اختبر وضوح إرشادات الدروس والاختبارات.')
    if not suggestions:suggestions.append('النشاط والأخطاء ضمن الحدود المسجلة. تابع مراجعة إكمال المستويات لتحسين المحتوى.')
    for s in suggestions:c.execute('INSERT INTO insights(message,created_at) VALUES(?,?)',(s,utcnow()))
   return self.send_json({'suggestions':suggestions,'note':'تحليلات وصفية مبنية على بيانات الاستخدام؛ أي إصلاح أو تغيير يحتاج مراجعة وموافقة بشرية.'})
  if p=='/api/admin/events/resolve':
   u=self.require(True)
   if not u:return
   with connect() as c:c.execute('UPDATE events SET resolved=1 WHERE id=?',(int(d.get('id',0)),))
   return self.send_json({'ok':True})
  return self.send_json({'error':'المسار غير موجود'},404)
 def session_token(self):
  for p in self.headers.get('Cookie','').split(';'):
   if p.strip().startswith(COOKIE_NAME+'='):return p.strip().split('=',1)[1]
 def login(self,uid):
  token=secrets.token_urlsafe(32);digest=hashlib.sha256(token.encode()).hexdigest()
  with connect() as c:c.execute('INSERT INTO sessions VALUES(?,?,?)',(digest,uid,int(time.time())+86400*14));u=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
  self.send_response(200);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Set-Cookie',f'{COOKIE_NAME}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={86400*14}'+('; Secure' if os.environ.get('COOKIE_SECURE')=='1' else ''));self.send_header('Cache-Control','no-store');raw=json.dumps({'user':safeuser(u),'courses':COURSES},ensure_ascii=False).encode();self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
 def do_PUT(self):return self.send_json({'error':'غير مدعوم'},405)

def main():
 init_db();threading.Thread(target=AGENT.serve,name='maintenance-agent',daemon=True).start();port=int(os.environ.get('PORT','8000'));server=ThreadingHTTPServer(('0.0.0.0',port),Handler);print(f'Python Academy running at http://localhost:{port}');server.serve_forever()
if __name__=='__main__':main()
