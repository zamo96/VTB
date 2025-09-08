# src/db/pg.py
import os, re, time
from typing import Any, Dict, Optional
from psycopg_pool import ConnectionPool
from psycopg.rows import dict_row

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://aldarbazarov:password@localhost:5432/vtb")

# пул синхронный; будем вызывать из async через run_in_threadpool
pool = ConnectionPool(DATABASE_URL, min_size=1, max_size=5, kwargs={"autocommit": True})

_SAFE_SEARCH_PATH = re.compile(r"^[a-zA-Z0-9_., ]+$")

def _set_ctx(cur, search_path: Optional[str], timeout_ms: int):
    if timeout_ms:
        cur.execute(f"SET LOCAL statement_timeout = {int(timeout_ms)}")
    if search_path:
        if not _SAFE_SEARCH_PATH.match(search_path):
            raise ValueError("invalid search_path")
        cur.execute(f"SET LOCAL search_path = {search_path}")

def run_sql_sync(sql: str,
                 params: Optional[Dict[str, Any]] = None,
                 *,
                 timeout_ms: int = 5000,
                 search_path: Optional[str] = None,
                 allow_write: bool = False) -> Dict[str, Any]:
    s = sql.strip()
    if not allow_write:
        low = s.lower()
        if not (low.startswith("select") or low.startswith("with")):
            raise ValueError("Only SELECT/WITH allowed (set allow_write=true to override).")
    t0 = time.perf_counter()
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        _set_ctx(cur, search_path, timeout_ms)
        cur.execute(s, params or None)
        rows = cur.fetchall() if cur.description else []
    return {"rows": rows, "row_count": len(rows), "duration_ms": round((time.perf_counter()-t0)*1000, 2)}

def explain_sql_sync(sql: str,
                     *,
                     analyze: bool = False,
                     buffers: bool = True,
                     verbose: bool = False,
                     settings: bool = False,
                     timeout_ms: int = 5000,
                     search_path: Optional[str] = None,
                     fmt: str = "json") -> Dict[str, Any]:
    opts = [
        f"ANALYZE {'true' if analyze else 'false'}",
        "COSTS true",
        f"BUFFERS {'true' if buffers else 'false'}",
        f"VERBOSE {'true' if verbose else 'false'}",
        f"SETTINGS {'true' if settings else 'false'}",
    ]
    if fmt.lower() == "json":
        opts.append("FORMAT JSON")
    q = f"EXPLAIN ({', '.join(opts)}) {sql.strip()}"
    with pool.connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        _set_ctx(cur, search_path, timeout_ms)
        cur.execute(q)
        if fmt.lower() == "json":
            row = cur.fetchone() or {}
            plan = list(row.values())[0] if row else None  # значение колонки "QUERY PLAN"
            return {"plan": plan}
        lines = [r["QUERY PLAN"] for r in cur.fetchall()]
        return {"plan_text": "\n".join(lines)}

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

    _clear_pg_env()

    # Основное подключение (с переданным паролем)
    if _IS_PSYCOPG3:
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
    else:
        conn = psycopg.connect(**conn_params)
        conn.autocommit = True
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
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
        if _IS_PSYCOPG3:
            c2 = psycopg.connect(**wrong_params, autocommit=True, row_factory=dict_row)
            c2.close()
            auth_requires_password = False
        else:
            c2 = psycopg.connect(**wrong_params)
            c2.close()
            auth_requires_password = False
    except Exception:
        auth_requires_password = True

    base_info["auth_requires_password"] = auth_requires_password
    if not auth_requires_password:
        base_info["note"] = "Подключение успешно даже с неверным паролем: вероятно trust/peer-авторизация."
    return base_info
