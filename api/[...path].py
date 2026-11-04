"""Catch-all Vercel Python function for the academy JSON API."""
from server import Handler, init_db

# Vercel functions have no durable local database filesystem. Initialize Supabase
# PostgreSQL at cold start; init_db requires DATABASE_URL and the admin env vars.
init_db()

class handler(Handler):
    pass
