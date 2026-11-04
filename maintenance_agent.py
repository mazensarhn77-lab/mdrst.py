"""Low-risk site operations agent.

The agent continuously inspects aggregate activity/error signals, runs a small
allow-listed set of idempotent SQLite maintenance actions, and stores an audit
report for the administrator. It never edits or executes application source.
Optional model enrichment is intentionally a provider hook (disabled unless an
administrator configures an endpoint); it receives only aggregated signals.
"""
from __future__ import annotations
import json, os, sqlite3, time, datetime, urllib.request, urllib.error, re
from pathlib import Path
from database import connect as db_connect, USE_POSTGRES


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


class MaintenanceAgent:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.interval = max(60, int(os.environ.get("AGENT_INTERVAL_SECONDS", "300")))

    def db(self):
        return db_connect(self.db_path, timeout=10)

    def _safe_repairs(self, c):
        """Only apply bounded, non-destructive repairs from this explicit list."""
        actions = []
        # Expired login tokens are no longer usable, so deleting them is safe.
        cur = c.execute("DELETE FROM sessions WHERE expires <= ?", (int(time.time()),))
        if cur.rowcount:
            actions.append(f"حُذفت {cur.rowcount} جلسة منتهية الصلاحية")
        # Recreate expected indexes if they are missing. CREATE IF NOT EXISTS is idempotent.
        c.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_users_activity ON users(last_active)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at)")
        actions.append("تم التحقق من فهارس الجلسات والنشاط والأحداث")
        if USE_POSTGRES:
            c.execute("ANALYZE")
        else:
            c.execute("PRAGMA optimize")
        return actions

    def _signals(self, c):
        day_ago = (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=1)).isoformat(timespec="seconds")
        week_ago = (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=7)).isoformat(timespec="seconds")
        users = c.execute("SELECT COUNT(*) AS n FROM users WHERE role='user'").fetchone()["n"]
        active = c.execute("SELECT COUNT(*) AS n FROM users WHERE role='user' AND last_active>=?", (week_ago,)).fetchone()["n"]
        completed = c.execute("SELECT COUNT(*) AS n FROM progress WHERE completed=1 AND quiz_score>=70").fetchone()["n"]
        errors = c.execute("SELECT kind,message,COUNT(*) AS n,MAX(created_at) AS latest FROM events WHERE kind='error' AND created_at>=? GROUP BY kind,message ORDER BY n DESC LIMIT 10", (day_ago,)).fetchall()
        activity = c.execute("SELECT course,SUM(activity_count) AS n FROM progress GROUP BY course ORDER BY n DESC").fetchall()
        return {
            "users_total": users, "users_active_7d": active,
            "levels_completed": completed,
            "errors_24h": [{"message": r["message"][:240], "count": r["n"], "latest": r["latest"]} for r in errors],
            "activity_by_level": [{"course": r["course"], "activity": r["n"]} for r in activity],
        }

    def _rules(self, signals, actions):
        suggestions = []
        if actions:
            suggestions.append("إجراءات صيانة آمنة نُفذت تلقائياً: " + "؛ ".join(actions) + ".")
        for error in signals["errors_24h"][:3]:
            suggestions.append(f"خطأ متكرر ({error['count']}): {error['message']} — راجع التتبع والسياق قبل تعديل الكود.")
        if signals["users_total"] and signals["users_active_7d"] == 0:
            suggestions.append("لا يوجد مستخدم نشط خلال 7 أيام؛ راجع خطوات التسجيل والعودة إلى الدروس.")
        by_course = signals["activity_by_level"]
        if len(by_course) >= 2:
            ordered = sorted(by_course, key=lambda x: x["activity"])
            if ordered[0]["activity"] == 0 and ordered[-1]["activity"] > 0:
                suggestions.append(f"لا يوجد نشاط مسجل في المستوى {ordered[0]['course']}؛ راجع وضوح شرط فتحه ومحتواه.")
        if not suggestions:
            suggestions.append("لم تُرصد مشكلة تشغيلية حالياً. يستمر الوكيل في مراقبة الأخطاء والنشاط.")
        return suggestions

    def _model_suggestions(self, signals):
        """Optional OpenAI-compatible chat endpoint; disabled by default.

        Only aggregated error text/counts and course-level totals are sent; no
        names, emails, cookies, or account identifiers are included.
        """
        endpoint = os.environ.get("AGENT_AI_ENDPOINT", "").strip()
        key = os.environ.get("AGENT_AI_KEY", "").strip()
        model = os.environ.get("AGENT_AI_MODEL", "").strip()
        if not endpoint or not key or not model:
            return []
        # Error text can contain user input. Send only a coarse error class and
        # count to an optional third-party provider, never raw messages.
        provider_signals = dict(signals)
        provider_signals["errors_24h"] = [
            {"type": re.sub(r"[^A-Za-z0-9_. -]", "", item["message"].split(":", 1)[0])[:40] or "ClientError", "count": item["count"]}
            for item in signals["errors_24h"]
        ]
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "أنت مساعد صيانة لمنصة تعليمية. حلل المؤشرات المجمعة فقط، واقترح حتى 3 خطوات تحقق آمنة. لا تدّع تنفيذ إصلاحات ولا تقترح حذف بيانات أو تعديل تلقائي للكود. أعد JSON بصيغة {\"suggestions\":[\"...\"]}."},
                {"role": "user", "content": json.dumps(provider_signals, ensure_ascii=False)},
            ], "temperature": 0.2,
        }
        req = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=8) as response:
                result = json.loads(response.read(120_000))
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            parsed = json.loads(content)
            items = parsed.get("suggestions", [])
            return [str(x)[:500] for x in items[:3] if isinstance(x, str)]
        except Exception as exc:
            return [f"تعذر الاتصال بمزود التحليل الاختياري ({type(exc).__name__}); استمر التحليل المحلي."]

    def run_once(self):
        """Inspect, apply only safe maintenance, and persist an audit report."""
        actions, issues = [], []
        with self.db() as c:
            try:
                if USE_POSTGRES:
                    c.execute("SELECT 1 AS ok")
                    check_ok = True
                else:
                    check_ok = c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
                if not check_ok:
                    issues.append("فشل فحص تكامل قاعدة البيانات؛ أوقف الكتابة وخذ نسخة احتياطية وافحصها يدوياً.")
                else:
                    actions = self._safe_repairs(c)
            except Exception as exc:
                issues.append(f"تعذر تنفيذ فحص قاعدة البيانات ({type(exc).__name__}); يلزم فحص الأدمن.")
            signals = self._signals(c)
            suggestions = issues + self._rules(signals, actions)
            suggestions += self._model_suggestions(signals)
            c.execute("CREATE TABLE IF NOT EXISTS agent_reports(id BIGSERIAL PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,summary TEXT NOT NULL,signals TEXT NOT NULL,actions TEXT NOT NULL)" if USE_POSTGRES else "CREATE TABLE IF NOT EXISTS agent_reports(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,summary TEXT NOT NULL,signals TEXT NOT NULL,actions TEXT NOT NULL)")
            status = "attention" if issues or signals["errors_24h"] else "ok"
            summary = " | ".join(suggestions)
            c.execute("INSERT INTO agent_reports(created_at,status,summary,signals,actions) VALUES(?,?,?,?,?)", (now_iso(),status,summary,json.dumps(signals,ensure_ascii=False),json.dumps(actions,ensure_ascii=False)))
            # Keep bounded operational history; raw app events are retained separately.
            c.execute("DELETE FROM agent_reports WHERE id NOT IN (SELECT id FROM agent_reports ORDER BY id DESC LIMIT 100)")
        return {"status": status, "created_at": now_iso(), "signals": signals, "actions": actions, "suggestions": suggestions,
                "mode": "provider-assisted" if os.environ.get("AGENT_AI_ENDPOINT") and os.environ.get("AGENT_AI_KEY") and os.environ.get("AGENT_AI_MODEL") else "local-rules"}

    def latest(self, limit=10):
        with self.db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS agent_reports(id BIGSERIAL PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,summary TEXT NOT NULL,signals TEXT NOT NULL,actions TEXT NOT NULL)" if USE_POSTGRES else "CREATE TABLE IF NOT EXISTS agent_reports(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL,status TEXT NOT NULL,summary TEXT NOT NULL,signals TEXT NOT NULL,actions TEXT NOT NULL)")
            return [dict(r) for r in c.execute("SELECT * FROM agent_reports ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]

    def serve(self):
        """Periodic background inspection; errors are isolated from web serving."""
        while True:
            try:
                report = self.run_once()
                print(f"[maintenance-agent] {report['status']} · {len(report['actions'])} safe actions")
            except Exception as exc:
                print(f"[maintenance-agent] run failed: {type(exc).__name__}: {exc}")
            time.sleep(self.interval)
