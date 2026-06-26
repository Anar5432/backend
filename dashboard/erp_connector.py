"""
erp_connector.py — Read-only connection pool to BTFERPDB (SQL Server).
All queries use NOLOCK hint to avoid blocking ERP users.
"""
import pymssql
import threading
from django.conf import settings
from django.core.cache import cache

# Thread-local storage so each thread gets its own connection
_local = threading.local()

def get_connection():
    """Return a thread-local persistent connection to SQL Server."""
    conn = getattr(_local, 'conn', None)
    
    def connect():
        # pymssql expects the port as part of the host if using host:port, or in this case server:port
        server = settings.MSSQL_CONFIG['SERVER'].replace(',', ':')
        return pymssql.connect(
            server=server,
            user=settings.MSSQL_CONFIG['USERNAME'],
            password=settings.MSSQL_CONFIG['PASSWORD'],
            database=settings.MSSQL_CONFIG['DATABASE'],
            charset='cp1254',
            autocommit=True
        )

    if conn is None:
        conn = connect()
        _local.conn = conn
    else:
        try:
            conn.cursor().execute("SELECT 1")
        except Exception:
            conn = connect()
            _local.conn = conn
    return conn


def query(sql, params=None, cache_key=None, cache_ttl=240):
    """
    Execute a read-only SQL query.
    - cache_key: if set, result is cached for cache_ttl seconds
    - Returns list of dicts
    """
    if cache_key:
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

    conn = get_connection()
    cursor = conn.cursor()
    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        columns = [col[0] for col in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        cursor.close()

    if cache_key:
        cache.set(cache_key, rows, cache_ttl)

    return rows


def query_one(sql, params=None, cache_key=None, cache_ttl=240):
    """Same as query() but returns the first row or None."""
    rows = query(sql, params, cache_key, cache_ttl)
    return rows[0] if rows else None
