"""
erp_connector.py — Read-only connection pool to BTFERPDB (SQL Server).
All queries use NOLOCK hint to avoid blocking ERP users.
"""
import pyodbc
import threading
from django.conf import settings
from django.core.cache import cache

# Thread-local storage so each thread gets its own connection
_local = threading.local()

CONN_STRING = (
    f"DRIVER={{{settings.MSSQL_CONFIG['DRIVER']}}};"
    f"SERVER={settings.MSSQL_CONFIG['SERVER']};"
    f"DATABASE={settings.MSSQL_CONFIG['DATABASE']};"
    f"UID={settings.MSSQL_CONFIG['USERNAME']};"
    f"PWD={settings.MSSQL_CONFIG['PASSWORD']};"
    f"TrustServerCertificate={settings.MSSQL_CONFIG['TRUST_SERVER_CERTIFICATE']};"
    f"Encrypt=no;"
)


def get_connection():
    """Return a thread-local persistent connection to SQL Server."""
    conn = getattr(_local, 'conn', None)
    if conn is None:
        conn = pyodbc.connect(CONN_STRING, autocommit=True)
        # SQL Server ODBC returns wide chars as UTF-16-LE natively
        # SQL_CHAR (narrow) use cp1254 (Turkish Windows codepage)
        conn.setdecoding(pyodbc.SQL_CHAR, encoding='cp1254')
        conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
        _local.conn = conn
    else:
        try:
            conn.execute("SELECT 1")
        except Exception:
            conn = pyodbc.connect(CONN_STRING, autocommit=True)
            conn.setdecoding(pyodbc.SQL_CHAR, encoding='cp1254')
            conn.setdecoding(pyodbc.SQL_WCHAR, encoding='utf-16-le')
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
