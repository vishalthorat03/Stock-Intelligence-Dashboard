import json
import os
import sqlite3
from datetime import datetime
import shutil
import hashlib
import secrets

from config.settings import DATABASE_PATH


def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def bootstrap_database_file():
    legacy_path = os.path.abspath(os.path.join(os.path.dirname(DATABASE_PATH), "..", "..", "data", "stocks.db"))
    target_missing_or_empty = (not os.path.exists(DATABASE_PATH)) or os.path.getsize(DATABASE_PATH) == 0
    if target_missing_or_empty and os.path.exists(legacy_path) and os.path.getsize(legacy_path) > 0:
        os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
        shutil.copy2(legacy_path, DATABASE_PATH)


def table_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row["name"] for row in cursor.fetchall()}


def ensure_column(cursor, table_name, column_name, definition):
    if column_name not in table_columns(cursor, table_name):
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def init_db(verbose=False):
    """Initialize database schema and apply lightweight migrations."""
    bootstrap_database_file()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stocks (
            symbol TEXT PRIMARY KEY,
            name TEXT,
            score REAL DEFAULT 0.0,
            sentiment REAL DEFAULT 0.0,
            momentum REAL DEFAULT 0.0,
            volume_signal REAL DEFAULT 0.0,
            price_change REAL DEFAULT 0.0,
            current_price REAL DEFAULT 0.0,
            predicted_price_change REAL DEFAULT 0.0,
            confidence REAL DEFAULT 0.0,
            reasoning TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS historical_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            date DATE,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            FOREIGN KEY (symbol) REFERENCES stocks(symbol),
            UNIQUE(symbol, date)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sentiment_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT,
            source TEXT,
            title TEXT,
            sentiment_score REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (symbol) REFERENCES stocks(symbol)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT,
            score REAL DEFAULT 0.0,
            sentiment REAL DEFAULT 0.0,
            momentum REAL DEFAULT 0.0,
            volume_signal REAL DEFAULT 0.0,
            price_change REAL DEFAULT 0.0,
            current_price REAL DEFAULT 0.0,
            predicted_price_change REAL DEFAULT 0.0,
            confidence REAL DEFAULT 0.0,
            reasoning TEXT DEFAULT '',
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (symbol) REFERENCES stocks(symbol)
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS model_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            samples INTEGER DEFAULT 0,
            r2 REAL DEFAULT 0.0,
            mae REAL DEFAULT 0.0,
            status TEXT DEFAULT '',
            trained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            reset_code TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """
    )

    ensure_column(cursor, "stocks", "predicted_price_change", "REAL DEFAULT 0.0")
    ensure_column(cursor, "stocks", "confidence", "REAL DEFAULT 0.0")
    ensure_column(cursor, "stocks", "reasoning", "TEXT DEFAULT ''")

    conn.commit()
    conn.close()
    if verbose:
        print("Database initialized successfully!")


def seed_snapshot_history():
    """Backfill one snapshot per current stock when history is empty."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM stock_snapshots")
    snapshot_count = cursor.fetchone()["count"]
    if snapshot_count == 0:
        cursor.execute(
            """
            INSERT INTO stock_snapshots (
                symbol, name, score, sentiment, momentum, volume_signal,
                price_change, current_price, predicted_price_change, confidence,
                reasoning, snapshot_time
            )
            SELECT
                symbol, name, score, sentiment, momentum, volume_signal,
                price_change, current_price, predicted_price_change, confidence,
                reasoning, updated_at
            FROM stocks
        """
        )
        conn.commit()
    conn.close()


def decode_reasoning(row):
    payload = dict(row)
    reasoning = payload.get("reasoning")
    if isinstance(reasoning, str) and reasoning:
        try:
            payload["reasoning"] = json.loads(reasoning)
        except json.JSONDecodeError:
            payload["reasoning"] = {"summary": reasoning}
    else:
        payload["reasoning"] = {}
    return payload


def get_stock(symbol):
    """Get stock data by symbol."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stocks WHERE symbol = ?", (symbol,))
    stock = cursor.fetchone()
    conn.close()
    return decode_reasoning(stock) if stock else None


def get_top_stocks(limit=5):
    """Get top N stocks by score with model outputs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            symbol,
            name,
            score,
            sentiment,
            momentum,
            volume_signal,
            price_change,
            current_price,
            predicted_price_change,
            confidence,
            reasoning,
            updated_at
        FROM stocks
        ORDER BY score DESC, predicted_price_change DESC, confidence DESC
        LIMIT ?
    """,
        (limit,),
    )
    stocks = [decode_reasoning(row) for row in cursor.fetchall()]
    conn.close()
    return stocks


def get_stock_count(search=""):
    conn = get_db_connection()
    cursor = conn.cursor()
    if search:
        pattern = f"%{search.upper()}%"
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM stocks
            WHERE UPPER(symbol) LIKE ? OR UPPER(COALESCE(name, '')) LIKE ?
        """,
            (pattern, pattern),
        )
    else:
        cursor.execute("SELECT COUNT(*) FROM stocks")
    count = cursor.fetchone()[0]
    conn.close()
    return int(count)


def get_stocks(limit=50, offset=0, search="", sort_by="score", sort_dir="desc"):
    conn = get_db_connection()
    cursor = conn.cursor()

    allowed_sort = {
        "score": "score",
        "symbol": "symbol",
        "price": "current_price",
        "change": "price_change",
        "prediction": "predicted_price_change",
        "confidence": "confidence",
    }
    order_column = allowed_sort.get(sort_by, "score")
    order_direction = "ASC" if str(sort_dir).lower() == "asc" else "DESC"

    params = []
    where = ""
    if search:
        pattern = f"%{search.upper()}%"
        where = "WHERE UPPER(symbol) LIKE ? OR UPPER(COALESCE(name, '')) LIKE ?"
        params.extend([pattern, pattern])

    params.extend([limit, offset])
    cursor.execute(
        f"""
        SELECT
            symbol,
            name,
            score,
            sentiment,
            momentum,
            volume_signal,
            price_change,
            current_price,
            predicted_price_change,
            confidence,
            reasoning,
            updated_at
        FROM stocks
        {where}
        ORDER BY {order_column} {order_direction}, score DESC, symbol ASC
        LIMIT ? OFFSET ?
    """,
        params,
    )
    rows = [decode_reasoning(row) for row in cursor.fetchall()]
    conn.close()
    return rows


def get_stock_history(symbol, limit=30):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            symbol,
            score,
            sentiment,
            momentum,
            volume_signal,
            price_change,
            current_price,
            predicted_price_change,
            confidence,
            reasoning,
            snapshot_time
        FROM stock_snapshots
        WHERE symbol = ?
        ORDER BY snapshot_time DESC, id DESC
        LIMIT ?
    """,
        (symbol, limit),
    )
    rows = [decode_reasoning(row) for row in cursor.fetchall()]
    conn.close()
    return list(reversed(rows))


def get_comparison_history(symbols=None, limit=20):
    conn = get_db_connection()
    cursor = conn.cursor()

    params = []
    sql = """
        SELECT
            symbol,
            score,
            current_price,
            predicted_price_change,
            snapshot_time
        FROM stock_snapshots
    """
    if symbols:
        placeholders = ",".join(["?"] * len(symbols))
        sql += f" WHERE symbol IN ({placeholders})"
        params.extend(symbols)
    sql += " ORDER BY snapshot_time DESC, id DESC"
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        symbol = row["symbol"]
        grouped.setdefault(symbol, [])
        if len(grouped[symbol]) < limit:
            grouped[symbol].append(
                {
                    "snapshot_time": row["snapshot_time"],
                    "score": row["score"],
                    "current_price": row["current_price"],
                    "predicted_price_change": row["predicted_price_change"],
                }
            )

    for symbol in grouped:
        grouped[symbol].reverse()
    return grouped


def get_market_summary(limit=5):
    top_stocks = get_top_stocks(limit)
    if not top_stocks:
        return {
            "top_stock": None,
            "summary": "No stock data is available yet.",
            "updated_at": None,
            "comparisons": [],
        }

    leader = top_stocks[0]
    comparisons = []
    for stock in top_stocks:
        comparisons.append(
            {
                "symbol": stock["symbol"],
                "score": round(stock["score"], 2),
                "predicted_price_change": round(stock.get("predicted_price_change", 0.0), 2),
                "confidence": round(stock.get("confidence", 0.0), 2),
                "reason": stock.get("reasoning", {}).get("summary", ""),
            }
        )

    return {
        "top_stock": leader,
        "summary": leader.get("reasoning", {}).get(
            "summary",
            f"{leader['symbol']} is currently leading by composite score.",
        ),
        "updated_at": leader.get("updated_at"),
        "comparisons": comparisons,
        "model": get_latest_model_run(),
    }


def add_model_run(model_meta):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO model_runs (model_name, samples, r2, mae, status, trained_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """,
        (
            model_meta.get("model_name", "heuristic"),
            int(model_meta.get("samples", 0)),
            float(model_meta.get("r2", 0.0)),
            float(model_meta.get("mae", 0.0)),
            model_meta.get("status", ""),
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    conn.close()


def get_latest_model_run():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT model_name, samples, r2, mae, status, trained_at
        FROM model_runs
        ORDER BY trained_at DESC, id DESC
        LIMIT 1
    """
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {
        "model_name": "heuristic",
        "samples": 0,
        "r2": 0.0,
        "mae": 0.0,
        "status": "not_trained",
        "trained_at": None,
    }


def get_all_snapshots(limit=5000):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            symbol,
            score,
            sentiment,
            momentum,
            volume_signal,
            price_change,
            current_price,
            predicted_price_change,
            confidence,
            reasoning,
            snapshot_time
        FROM stock_snapshots
        ORDER BY snapshot_time DESC, id DESC
        LIMIT ?
    """,
        (limit,),
    )
    rows = [decode_reasoning(row) for row in cursor.fetchall()]
    conn.close()
    return list(reversed(rows))


def hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        120000,
    ).hex()
    return password_hash, salt


def create_user(username, email, password):
    username = username.strip()
    email = email.strip().lower()
    if not username or not email or not password:
        raise ValueError("username, email and password are required")

    password_hash, salt = hash_password(password)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            INSERT INTO users (username, email, password_hash, password_salt, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                username,
                email,
                password_hash,
                salt,
                datetime.now().isoformat(timespec="seconds"),
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        conn.close()
        message = str(exc).lower()
        if "username" in message:
            raise ValueError("username already exists")
        if "email" in message:
            raise ValueError("email already exists")
        raise ValueError("unable to create account")

    cursor.execute("SELECT id, username, email, created_at FROM users WHERE id = ?", (user_id,))
    user = dict(cursor.fetchone())
    conn.close()
    return user


def authenticate_user(identifier, password):
    identifier = identifier.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, email, password_hash, password_salt, created_at
        FROM users
        WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)
    """,
        (identifier, identifier),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise ValueError("invalid username/email or password")

    payload = dict(row)
    password_hash, _ = hash_password(password, payload["password_salt"])
    if password_hash != payload["password_hash"]:
        raise ValueError("invalid username/email or password")

    return {
        "id": payload["id"],
        "username": payload["username"],
        "email": payload["email"],
        "created_at": payload["created_at"],
    }


def create_password_reset(identifier):
    identifier = identifier.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, email
        FROM users
        WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)
    """,
        (identifier, identifier),
    )
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise ValueError("no account found for that username or email")

    code = secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()
    expires_at = datetime.now().replace(microsecond=0)
    expires_text = expires_at.isoformat(timespec="seconds")
    expiry_minutes = 15
    cursor.execute(
        """
        INSERT INTO password_resets (user_id, reset_code, expires_at, used, created_at)
        VALUES (?, ?, datetime(?, '+15 minutes'), 0, ?)
    """,
        (user["id"], code, expires_text, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()
    return {
        "username": user["username"],
        "email": user["email"],
        "reset_code": code,
        "expires_in_minutes": expiry_minutes,
    }


def reset_password(identifier, reset_code, new_password):
    identifier = identifier.strip()
    reset_code = reset_code.strip().upper()
    if not new_password:
        raise ValueError("new password is required")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, username, email
        FROM users
        WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)
    """,
        (identifier, identifier),
    )
    user = cursor.fetchone()
    if not user:
        conn.close()
        raise ValueError("no account found for that username or email")

    cursor.execute(
        """
        SELECT id, reset_code, expires_at, used
        FROM password_resets
        WHERE user_id = ?
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """,
        (user["id"],),
    )
    reset_row = cursor.fetchone()
    if not reset_row:
        conn.close()
        raise ValueError("no reset request found")

    if reset_row["used"]:
        conn.close()
        raise ValueError("reset code has already been used")

    cursor.execute("SELECT datetime('now') > datetime(?)", (reset_row["expires_at"],))
    expired = cursor.fetchone()[0]
    if expired:
        conn.close()
        raise ValueError("reset code has expired")

    if reset_row["reset_code"] != reset_code:
        conn.close()
        raise ValueError("invalid reset code")

    password_hash, salt = hash_password(new_password)
    now = datetime.now().isoformat(timespec="seconds")
    cursor.execute(
        """
        UPDATE users
        SET password_hash = ?, password_salt = ?, updated_at = ?
        WHERE id = ?
    """,
        (password_hash, salt, now, user["id"]),
    )
    cursor.execute(
        """
        UPDATE password_resets
        SET used = 1
        WHERE id = ?
    """,
        (reset_row["id"],),
    )
    conn.commit()
    conn.close()
    return {
        "username": user["username"],
        "email": user["email"],
        "reset_at": now,
    }


def update_stock(
    symbol,
    name,
    score,
    sentiment,
    momentum,
    volume_signal,
    price_change,
    current_price,
    predicted_price_change=0.0,
    confidence=0.0,
    reasoning=None,
    snapshot_time=None,
):
    """Update current stock row and append a point-in-time snapshot."""
    init_db()

    reasoning_payload = json.dumps(reasoning or {})
    snapshot_timestamp = snapshot_time or datetime.now().isoformat(timespec="seconds")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO stocks (
            symbol, name, score, sentiment, momentum, volume_signal,
            price_change, current_price, predicted_price_change, confidence,
            reasoning, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(symbol) DO UPDATE SET
            name = excluded.name,
            score = excluded.score,
            sentiment = excluded.sentiment,
            momentum = excluded.momentum,
            volume_signal = excluded.volume_signal,
            price_change = excluded.price_change,
            current_price = excluded.current_price,
            predicted_price_change = excluded.predicted_price_change,
            confidence = excluded.confidence,
            reasoning = excluded.reasoning,
            updated_at = excluded.updated_at
    """,
        (
            symbol,
            name,
            score,
            sentiment,
            momentum,
            volume_signal,
            price_change,
            current_price,
            predicted_price_change,
            confidence,
            reasoning_payload,
            snapshot_timestamp,
        ),
    )

    cursor.execute(
        """
        INSERT INTO stock_snapshots (
            symbol, name, score, sentiment, momentum, volume_signal,
            price_change, current_price, predicted_price_change, confidence,
            reasoning, snapshot_time
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            symbol,
            name,
            score,
            sentiment,
            momentum,
            volume_signal,
            price_change,
            current_price,
            predicted_price_change,
            confidence,
            reasoning_payload,
            snapshot_timestamp,
        ),
    )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    seed_snapshot_history()
