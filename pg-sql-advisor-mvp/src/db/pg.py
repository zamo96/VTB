# src/db/pg.py
import json
import pathlib
from typing import Dict, Tuple
from dotenv import load_dotenv
import os, re, time
from typing import Any, Dict, Optional
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row
import psycopg  # psycopg3

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

try:
    import psycopg  # psycopg3
    from psycopg.rows import dict_row
    _IS_PSYCOPG3 = True
except Exception:
    import psycopg2 as psycopg
    from psycopg2.extras import RealDictCursor
    _IS_PSYCOPG3 = False


PG_ENV_KEYS = ("PGHOST", "PGPORT", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGSERVICE")

def _clear_pg_env():
    """Убираем влияние libpq окружения на коннект."""
    cleared = {}
    for k in PG_ENV_KEYS:
        if k in os.environ:
            cleared[k] = os.environ.pop(k)
    return cleared  # вернём на всякий случай для /debug


def _pg_conn_params() -> Dict:
    return dict(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        dbname=os.getenv("DB_NAME", "postgres"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "123456"),
    )


def _conn_source() -> Tuple[str, Dict]:
    """Вернём строку-источник (DATABASE_URL|params) и сами параметры (без пароля)."""
    url = os.getenv("DATABASE_URL")
    if url:
        safe = url
        try:
            # зазвездить пароль, если есть
            before_at, after_at = url.split("@", 1)
            if "://" in before_at and ":" in before_at:
                proto, rest = before_at.split("://", 1)
                user, pwd = rest.split(":", 1)
                pwd_masked = "****"
                safe = f"{proto}://{user}:{pwd_masked}@{after_at}"
        except Exception:
            pass
        return ("DATABASE_URL", {"url": safe})
    p = _pg_conn_params().copy()
    p["password"] = "****" if p.get("password") else ""
    return ("params", p)


def get_conn_sync():
    cleared_env = _clear_pg_env()  # очищаем PG* из окружения
    source, src_val = _conn_source()
    # Можно включить отладочный принт:
    print(f"[db] connecting via {source}: {src_val}; cleared_env={list(cleared_env.keys())}")

    url = os.getenv("DATABASE_URL")
    if url:
        if _IS_PSYCOPG3:
            return psycopg.connect(url, autocommit=True, row_factory=dict_row)
        conn = psycopg.connect(url)
        conn.autocommit = True
        return conn

    params = _pg_conn_params()
    if _IS_PSYCOPG3:
        return psycopg.connect(**params, autocommit=True, row_factory=dict_row)
    conn = psycopg.connect(**params)
    conn.autocommit = True
    return conn


def run_sql_sync(sql: str, params=None, *, timeout_ms=5000, search_path="public", allow_write=False):
    conn = get_conn_sync()
    if _IS_PSYCOPG3:
        with conn, conn.cursor() as cur:
            if search_path:
                cur.execute(f"SET search_path TO {search_path}")
            if timeout_ms:
                cur.execute(f"SET statement_timeout = {int(timeout_ms)}")
            cur.execute(sql, params or ())
            if cur.description:
                return cur.fetchall()
            return {"rowcount": cur.rowcount}
    else:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if search_path:
                    cur.execute(f"SET search_path TO {search_path}")
                if timeout_ms:
                    cur.execute(f"SET statement_timeout = {int(timeout_ms)}")
                cur.execute(sql, params or ())
                if cur.description:
                    return cur.fetchall()
                return {"rowcount": cur.rowcount}


def explain_sql_sync(
    sql: str,
    *,
    analyze: bool = False,
    buffers: bool = True,
    verbose: bool = False,
    settings: bool = False,
    timeout_ms: int = 5000,
    search_path: str = "public",
    fmt: str = "json",
):
    fmt_l = fmt.lower()
    options = []
    if analyze: options.append("ANALYZE true")
    if buffers: options.append("BUFFERS true")
    if verbose: options.append("VERBOSE true")
    if settings: options.append("SETTINGS true")
    options.append(f"FORMAT {fmt_l.upper()}")
    q = f"EXPLAIN ({', '.join(options)}) {sql}"

    conn = get_conn_sync()
    if _IS_PSYCOPG3:
        with conn, conn.cursor() as cur:
            if search_path:
                cur.execute(f"SET search_path TO {search_path}")
            if timeout_ms:
                cur.execute(f"SET statement_timeout = {int(timeout_ms)}")
            cur.execute(q)
            if fmt_l == "json":
                row = cur.fetchone()
                val = (row.get("QUERY PLAN") if isinstance(row, dict) else row[0])
                if isinstance(val, str):
                    try: val = json.loads(val)
                    except Exception: pass
                return {"plan": val}
            else:
                rows = cur.fetchall()
                return {"plan_text": "\n".join([
                    (r.get("QUERY PLAN") if isinstance(r, dict) else r[0]) for r in rows
                ])}
    else:
        with conn:
            with conn.cursor() as cur:
                if search_path:
                    cur.execute(f"SET search_path TO {search_path}")
                if timeout_ms:
                    cur.execute(f"SET statement_timeout = {int(timeout_ms)}")
                cur.execute(q)
                if fmt_l == "json":
                    row = cur.fetchone()
                    val = row.get("QUERY PLAN") if isinstance(row, dict) else row[0]
                    if isinstance(val, str):
                        try: val = json.loads(val)
                        except Exception: pass
                    return {"plan": val}
                else:
                    rows = cur.fetchall()
                    return {"plan_text": "\n".join([
                        (r.get("QUERY PLAN") if isinstance(r, dict) else r[0]) for r in rows
                    ])}

def test_conn_with_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Проверяет подключение к PostgreSQL по переданным параметрам и выполняет простой запрос.
    Параметры: {host, port, database, user, password}
    Возвращает мета-информацию о соединении при успехе, иначе кидает исключение.
    """
    conn_params = {
        "host": params.get("host"),
        "port": int(params.get("port", 5432)) if params.get("port") is not None else 5432,
        "dbname": params.get("database"),
        "user": params.get("user"),
        "password": params.get("password"),
    }

    # Основное подключение (с переданным паролем)
    conn = psycopg.connect(**conn_params, autocommit=True, row_factory=dict_row)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT current_user AS current_user, current_database() AS db, version() AS version")
        row = cur.fetchone()
        base_info = {
            "ok": True,
            "current_user": row.get("current_user"),
            "database": row.get("db"),
            "version": row.get("version"),
        }

    # Негативная проверка: если подключение с заведомо неверным паролем тоже проходит,
    # значит пароль фактически не требуется (например, trust/peer в pg_hba.conf)
    auth_requires_password = True
    try:
        wrong_params = dict(conn_params)
        wrong_params["password"] = (str(conn_params.get("password") or "") + "_wrong_" + os.urandom(4).hex())
        c2 = psycopg.connect(**wrong_params, autocommit=True, row_factory=dict_row)
        c2.close()
        auth_requires_password = False
    except Exception:
        auth_requires_password = True

    base_info["auth_requires_password"] = auth_requires_password
    if not auth_requires_password:
        base_info["note"] = "Подключение успешно даже с неверным паролем: вероятно trust/peer-авторизация."
    return base_info