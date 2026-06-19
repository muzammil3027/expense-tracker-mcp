from fastmcp import FastMCP
import os
import sqlite3

_default_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "expenses.db")
DB_PATH = os.environ.get("EXPENSE_DB_PATH", _default_db)

mcp = FastMCP("ExpenseTracker")

def init_balance_db():
    '''Create the LOAD_BALANCE table for adding balance entries.'''
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS LOAD_BALANCE(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL
            )
        """)
            
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)

init_db()
init_balance_db()

# Verify the database is writable at startup so the error is obvious immediately.
try:
    with sqlite3.connect(DB_PATH) as _c:
        _c.execute("CREATE TABLE IF NOT EXISTS _write_check (id INTEGER PRIMARY KEY)")
        _c.execute("INSERT INTO _write_check DEFAULT VALUES")
        _c.execute("DELETE FROM _write_check")
except sqlite3.OperationalError as e:
    raise RuntimeError(
        f"Database at {DB_PATH!r} is not writable: {e}\n"
        "Fix: run  chmod 664 <path>/expenses.db  on the server, or set the "
        "EXPENSE_DB_PATH env variable to a writable path."
    ) from e

@mcp.tool()
def add_expense(date, amount, category, subcategory="", note=""):
    '''Add a new expense entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO expenses(date, amount, category, subcategory, note) VALUES (?,?,?,?,?)",
            (date, amount, category, subcategory, note)
        )
        return {"status": "ok", "id": cur.lastrowid}
    

@mcp.tool()
def add_balance(date, amount, category):
    '''Add a new balance entry to the database.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "INSERT INTO LOAD_BALANCE(date, amount, category) VALUES (?,?,?)",
            (date, amount, category)
        )
        return {"status": "ok", "id": cur.lastrowid}
    
@mcp.tool()
def list_expenses(start_date, end_date):
    '''List expense entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def edit_expense(id, date=None, amount=None, category=None, subcategory=None, note=None):
    '''Edit an existing expense by id. Only provided fields are updated.'''
    fields = {"date": date, "amount": amount, "category": category,
              "subcategory": subcategory, "note": note}
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        return {"status": "error", "message": "No fields provided to update"}
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            f"UPDATE expenses SET {set_clause} WHERE id = ?",
            (*updates.values(), id)
        )
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}"}
        return {"status": "ok", "updated": cur.rowcount}


@mcp.tool()
def delete_expense(id):
    '''Delete an expense entry by id.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM expenses WHERE id = ?", (id,))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No expense found with id {id}"}
        return {"status": "ok", "deleted": cur.rowcount}


@mcp.tool()
def list_balances(start_date, end_date):
    '''List balance entries within an inclusive date range.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category
            FROM LOAD_BALANCE
            WHERE date BETWEEN ? AND ?
            ORDER BY id ASC
            """,
            (start_date, end_date)
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]


@mcp.tool()
def edit_balance(id, date=None, amount=None, category=None):
    '''Edit an existing balance entry by id. Only provided fields are updated.'''
    fields = {"date": date, "amount": amount, "category": category}
    updates = {k: v for k, v in fields.items() if v is not None}
    if not updates:
        return {"status": "error", "message": "No fields provided to update"}
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            f"UPDATE LOAD_BALANCE SET {set_clause} WHERE id = ?",
            (*updates.values(), id)
        )
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No balance found with id {id}"}
        return {"status": "ok", "updated": cur.rowcount}


@mcp.tool()
def delete_balance(id):
    '''Delete a balance entry by id.'''
    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute("DELETE FROM LOAD_BALANCE WHERE id = ?", (id,))
        if cur.rowcount == 0:
            return {"status": "error", "message": f"No balance found with id {id}"}
        return {"status": "ok", "deleted": cur.rowcount}


if __name__ == "__main__":
    mcp.run(transport="sse", host="0.0.0.0", port=8000)