"""Catch-all Vercel Python function for the academy JSON API."""
import threading
from server import Handler, init_db

# Initialize lazily on the first API request. Vercel can import a function
# module before database environment variables are ready, so relying only on
# module import may leave the PostgreSQL schema missing in a warm instance.
_initialized = False
_init_lock = threading.Lock()


def ensure_database():
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if not _initialized:
            init_db()
            _initialized = True


class handler(Handler):
    def do_GET(self):
        ensure_database()
        return super().do_GET()

    def do_POST(self):
        ensure_database()
        return super().do_POST()
