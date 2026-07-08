"""数据库层 —— 所有 SQL 操作，余额联动使用事务保证一致性"""

import sqlite3
from datetime import datetime

from config import (
    DB_PATH, TYPE_EXPENSE, TYPE_INCOME, TYPE_TRANSFER, DEFAULT_ACCOUNTS,
)


def _connect():
    """创建数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ============================================================
#  初始化
# ============================================================

def init_db():
    """建表 + 插入默认账户（首次运行）"""
    conn = _connect()
    try:
        # 账户表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT    NOT NULL,
                type       TEXT    NOT NULL,
                balance    REAL    NOT NULL DEFAULT 0,
                note       TEXT    DEFAULT '',
                created_at TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)
        # 账目表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                type        TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                category    TEXT    NOT NULL,
                account_id  INTEGER NOT NULL,
                date        TEXT    NOT NULL,
                note        TEXT    DEFAULT '',
                image_path  TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT (datetime('now', 'localtime'))
            )
        """)
        # 预算表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS budgets (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT    NOT NULL,
                category   TEXT    NOT NULL,
                amount     REAL    NOT NULL DEFAULT 0,
                UNIQUE(year_month, category)
            )
        """)
        # 插入默认账户（如果还没有）
        existing = conn.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
        if existing == 0:
            for name, atype, balance in DEFAULT_ACCOUNTS:
                conn.execute(
                    "INSERT INTO accounts (name, type, balance) VALUES (?, ?, ?)",
                    (name, atype, balance),
                )
        conn.commit()
    finally:
        conn.close()


# ============================================================
#  账户操作
# ============================================================

def create_account(name, atype, balance=0.0, note=""):
    """创建账户，返回新 id"""
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO accounts (name, type, balance, note) VALUES (?, ?, ?, ?)",
        (name, atype, balance, note),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_all_accounts():
    """获取所有账户列表"""
    conn = _connect()
    rows = conn.execute("SELECT * FROM accounts ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_account_by_id(account_id):
    """按 ID 查账户"""
    conn = _connect()
    row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_account(account_id, **fields):
    """更新账户信息（name / type / note / balance）"""
    allowed = {"name", "type", "note", "balance"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [account_id]
    conn = _connect()
    conn.execute(f"UPDATE accounts SET {set_clause} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_account(account_id):
    """删除账户（如果没有关联账目）"""
    conn = _connect()
    count = conn.execute(
        "SELECT COUNT(*) FROM records WHERE account_id = ?", (account_id,)
    ).fetchone()[0]
    if count > 0:
        conn.close()
        raise ValueError(f"该账户下有 {count} 条账目记录，请先删除相关账目")
    conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    conn.commit()
    conn.close()


def get_total_balance():
    """所有账户余额合计"""
    conn = _connect()
    row = conn.execute("SELECT COALESCE(SUM(balance), 0) AS total FROM accounts").fetchone()
    conn.close()
    return row["total"] if row else 0.0


def get_balance_by_type():
    """按账户类型分组统计余额"""
    conn = _connect()
    rows = conn.execute(
        "SELECT type, COALESCE(SUM(balance), 0) AS total FROM accounts GROUP BY type"
    ).fetchall()
    conn.close()
    return [(r["type"], r["total"]) for r in rows]


def transfer(from_id, to_id, amount, date, note=""):
    """账户间转账 —— 事务保证一减一加原子性，同时写入 records 留痕"""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "UPDATE accounts SET balance = balance - ? WHERE id = ?",
            (amount, from_id),
        )
        conn.execute(
            "UPDATE accounts SET balance = balance + ? WHERE id = ?",
            (amount, to_id),
        )
        # 共 2 条记录，类型 transfer
        conn.execute(
            "INSERT INTO records (type, amount, category, account_id, date, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (TYPE_TRANSFER, amount, "转出", from_id, date, note or "转账"),
        )
        conn.execute(
            "INSERT INTO records (type, amount, category, account_id, date, note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (TYPE_TRANSFER, amount, "转入", to_id, date, note or "转账"),
        )
        conn.commit()
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# ============================================================
#  账目 CRUD（含余额联动事务）
# ============================================================

def add_record(record_type, amount, category, account_id, date, note="", image_path=""):
    """插入账目并同步更新账户余额（事务）"""
    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            "INSERT INTO records (type, amount, category, account_id, date, note, image_path) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (record_type, amount, category, account_id, date, note, image_path),
        )
        if record_type == TYPE_EXPENSE:
            conn.execute(
                "UPDATE accounts SET balance = balance - ? WHERE id = ?",
                (amount, account_id),
            )
        elif record_type == TYPE_INCOME:
            conn.execute(
                "UPDATE accounts SET balance = balance + ? WHERE id = ?",
                (amount, account_id),
            )
        # 转账类型不在此处理（由 transfer 函数统一管理）
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def get_record_by_id(record_id):
    """按 ID 查账目"""
    conn = _connect()
    row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_record(record_id, **fields):
    """更新账目 —— 先回滚旧余额、再应用新余额（事务）"""
    allowed = {"type", "amount", "category", "account_id", "date", "note", "image_path"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return

    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        old = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
        if not old:
            conn.execute("ROLLBACK")
            return

        # ---- 回滚旧余额 ----
        old_type = old["type"]
        old_amount = old["amount"]
        old_account = old["account_id"]
        if old_type == TYPE_EXPENSE:
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?",
                         (old_amount, old_account))
        elif old_type == TYPE_INCOME:
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?",
                         (old_amount, old_account))
        # 转账不回滚余额（余额由 transfer 已处理，编辑会导致不一致，禁止编辑转账记录）

        # ---- 更新记录 ----
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [record_id]
        conn.execute(f"UPDATE records SET {set_clause} WHERE id = ?", values)

        # ---- 应用新余额 ----
        new_type = updates.get("type", old["type"])
        new_amount = updates.get("amount", old["amount"])
        new_account = updates.get("account_id", old["account_id"])
        if new_type == TYPE_EXPENSE:
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?",
                         (new_amount, new_account))
        elif new_type == TYPE_INCOME:
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?",
                         (new_amount, new_account))

        conn.commit()
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


def delete_record(record_id):
    """删除账目 —— 回滚余额 + 删记录（事务）"""
    from utils.image_helper import delete_image

    conn = _connect()
    try:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
        if not row:
            conn.execute("ROLLBACK")
            return

        rtype = row["type"]
        ramount = row["amount"]
        raccount = row["account_id"]
        rimage = row["image_path"]

        if rtype == TYPE_EXPENSE:
            conn.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?",
                         (ramount, raccount))
        elif rtype == TYPE_INCOME:
            conn.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?",
                         (ramount, raccount))

        conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
        conn.commit()

        # 删除图片（事务已提交后操作）
        if rimage:
            delete_image(rimage)
    except Exception:
        conn.execute("ROLLBACK")
        raise
    finally:
        conn.close()


# ============================================================
#  查询与统计
# ============================================================

def query_records(month="", record_type="", category="", account_id="",
                  keyword="", sort_by="date", sort_order="DESC"):
    """多条件筛选，排除转账类型（转账在账户页查看）"""
    conditions = ["type != ?"]
    params = [TYPE_TRANSFER]

    if month:
        conditions.append("strftime('%Y-%m', date) = ?")
        params.append(month)
    if record_type:
        conditions.append("type = ?")
        params.append(record_type)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if account_id:
        conditions.append("account_id = ?")
        params.append(int(account_id))
    if keyword:
        conditions.append("note LIKE ?")
        params.append(f"%{keyword}%")

    where = "WHERE " + " AND ".join(conditions)

    allowed_sort = {"date", "amount", "id", "created_at"}
    if sort_by not in allowed_sort:
        sort_by = "date"
    sort_order = "ASC" if sort_order.upper() == "ASC" else "DESC"

    sql = f"SELECT * FROM records {where} ORDER BY {sort_by} {sort_order}"

    conn = _connect()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_records(limit=10):
    """最近 N 条记录（排除转账）"""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM records WHERE type != ? ORDER BY created_at DESC LIMIT ?",
        (TYPE_TRANSFER, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_monthly_summary(month):
    """本月收入总计、支出总计"""
    conn = _connect()
    row = conn.execute(
        "SELECT "
        "  COALESCE(SUM(CASE WHEN type='income'  THEN amount ELSE 0 END), 0) AS income, "
        "  COALESCE(SUM(CASE WHEN type='expense' THEN amount ELSE 0 END), 0) AS expense "
        "FROM records WHERE strftime('%Y-%m', date) = ? AND type != ?",
        (month, TYPE_TRANSFER),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"income": 0, "expense": 0}


def get_monthly_stats(month, record_type):
    """按月 + 类型 按分类汇总"""
    conn = _connect()
    rows = conn.execute(
        "SELECT category, SUM(amount) AS total "
        "FROM records "
        "WHERE strftime('%Y-%m', date) = ? AND type = ? "
        "GROUP BY category ORDER BY total DESC",
        (month, record_type),
    ).fetchall()
    conn.close()
    return [(r["category"], r["total"]) for r in rows]


def get_daily_stats(month):
    """按天汇总支出金额（用于日历热力图），返回 {day: amount}"""
    conn = _connect()
    rows = conn.execute(
        "SELECT CAST(strftime('%d', date) AS INTEGER) AS day, "
        "       COALESCE(SUM(amount), 0) AS total "
        "FROM records "
        "WHERE strftime('%Y-%m', date) = ? AND type = 'expense' "
        "GROUP BY day",
        (month,),
    ).fetchall()
    conn.close()
    return {r["day"]: r["total"] for r in rows}


def get_records_by_date(date_str):
    """查某一天的所有记录（排除转账）"""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM records WHERE date = ? AND type != ? ORDER BY created_at DESC",
        (date_str, TYPE_TRANSFER),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ============================================================
#  预算操作
# ============================================================

def set_budget(year_month, category, amount):
    """设置/更新某月某分类的预算（UPSERT）"""
    conn = _connect()
    conn.execute(
        "INSERT INTO budgets (year_month, category, amount) VALUES (?, ?, ?) "
        "ON CONFLICT(year_month, category) DO UPDATE SET amount = excluded.amount",
        (year_month, category, amount),
    )
    conn.commit()
    conn.close()


def get_budgets(year_month):
    """获取某月所有预算，返回 {category: amount}"""
    conn = _connect()
    rows = conn.execute(
        "SELECT category, amount FROM budgets WHERE year_month = ?", (year_month,)
    ).fetchall()
    conn.close()
    return {r["category"]: r["amount"] for r in rows}


def copy_budget(from_month, to_month):
    """将上月预算复制到本月"""
    conn = _connect()
    budgets = conn.execute(
        "SELECT category, amount FROM budgets WHERE year_month = ?", (from_month,)
    ).fetchall()
    for b in budgets:
        conn.execute(
            "INSERT INTO budgets (year_month, category, amount) VALUES (?, ?, ?) "
            "ON CONFLICT(year_month, category) DO UPDATE SET amount = excluded.amount",
            (to_month, b["category"], b["amount"]),
        )
    conn.commit()
    conn.close()
    return len(budgets)


def get_budget_progress(year_month):
    """获取某月各分类的预算执行情况，返回 [(category, budget, spent, percent), ...]"""
    budgets = get_budgets(year_month)
    if not budgets:
        return []

    conn = _connect()
    rows = conn.execute(
        "SELECT category, COALESCE(SUM(amount), 0) AS spent "
        "FROM records "
        "WHERE strftime('%Y-%m', date) = ? AND type = 'expense' "
        "GROUP BY category",
        (year_month,),
    ).fetchall()
    conn.close()

    spent_map = {r["category"]: r["spent"] for r in rows}
    result = []
    for cat, budget in budgets.items():
        spent = spent_map.get(cat, 0)
        pct = (spent / budget * 100) if budget > 0 else 0
        result.append((cat, budget, spent, pct))
    return result
