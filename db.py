import sqlite3, os
from datetime import date, timedelta

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shiftwise.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS employees(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL, role TEXT, dept TEXT, email TEXT DEFAULT '',
  skills TEXT DEFAULT '', certs TEXT DEFAULT '',
  avail_days TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri',
  max_hours INTEGER DEFAULT 40,
  status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS shifts(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL, dept TEXT, shift_date TEXT NOT NULL,
  start_time TEXT NOT NULL, end_time TEXT NOT NULL,
  role TEXT DEFAULT '', skill TEXT DEFAULT '',
  headcount INTEGER DEFAULT 1, priority TEXT DEFAULT 'normal',
  published INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS assignments(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  UNIQUE(shift_id, employee_id));
CREATE TABLE IF NOT EXISTS absences(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
  absent_date TEXT NOT NULL, reason TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS swaps(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  shift_id INTEGER NOT NULL REFERENCES shifts(id) ON DELETE CASCADE,
  from_emp INTEGER NOT NULL, to_emp INTEGER NOT NULL,
  status TEXT DEFAULT 'pending', channel TEXT DEFAULT 'app', note TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS notifications(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  emp_id INTEGER, title TEXT, body TEXT, channel TEXT DEFAULT 'app',
  created TEXT, is_read INTEGER DEFAULT 0);
"""

DROP = ("DROP TABLE IF EXISTS meta; DROP TABLE IF EXISTS notifications; DROP TABLE IF EXISTS swaps; "
        "DROP TABLE IF EXISTS absences; DROP TABLE IF EXISTS assignments; DROP TABLE IF EXISTS shifts; "
        "DROP TABLE IF EXISTS employees;")

WK = "Mon,Tue,Wed,Thu,Fri"
SIX = "Mon,Tue,Wed,Thu,Fri,Sat"
ALL = "Mon,Tue,Wed,Thu,Fri,Sat,Sun"
WE = "Sat,Sun"

# employee: (name, role, dept, skills, certs[(skill, days_from_today)], avail_days, max_hours, status)
# shift:    (title, dept, day_offset, start, end, role, skill, headcount, priority)
SECTORS = {
    "retail": {
        "label": "Retail & Fashion", "icon": "👗", "tag": "E-commerce, apparel stores, fulfilment centres",
        "biz": "Northstar Fashion & Retail", "manager_role": "Operations Manager", "domain": "northstar.example",
        "depts": ["Store Floor", "Warehouse & Fulfilment", "Customer Support", "Security"],
        "skills": ["Cashier", "Stylist", "Visual Merchandising", "Supervisor", "Forklift", "Inventory",
                   "Customer Support", "Security", "First Aid"],
        "emps": [
            ("Aarav Mehta", "Store Manager", "Store Floor", "Supervisor,Cashier,Stylist,Inventory", [], SIX, 40, "active"),
            ("Neha Sharma", "Cashier", "Store Floor", "Cashier,Customer Support", [], WK, 40, "active"),
            ("Riya Kapoor", "Fashion Stylist", "Store Floor", "Stylist,Visual Merchandising,Cashier", [], WK, 40, "active"),
            ("Dev Patel", "Part-time Cashier", "Store Floor", "Cashier", [], WE, 20, "reserve"),
            ("Imran Khan", "Forklift Operator", "Warehouse & Fulfilment", "Forklift,Inventory", [("Forklift", 20)], SIX, 44, "active"),
            ("Sneha Iyer", "Packing Associate", "Warehouse & Fulfilment", "Inventory,Cashier", [], WK, 40, "active"),
            ("Vikram Singh", "Support Agent", "Customer Support", "Customer Support", [], ALL, 40, "active"),
            ("Ananya Pillai", "Support Lead", "Customer Support", "Customer Support,Supervisor", [], WK, 40, "active"),
            ("Rohan Das", "Security Guard", "Security", "Security,First Aid", [("Security", 300), ("First Aid", 200)], ALL, 48, "active"),
            ("Meera Nair", "Night Guard", "Security", "Security", [("Security", -10)], "Fri,Sat,Sun,Mon", 40, "active"),
        ],
        "shifts": [
            ("Morning Checkout Rush", "Store Floor", 1, "07:00", "15:00", "Cashier", "Cashier", 2, "normal"),
            ("Fashion Floor Supervisor", "Store Floor", 1, "09:00", "17:00", "Store Manager", "Supervisor", 1, "high"),
            ("Night Security Patrol", "Security", 1, "22:00", "06:00", "Security Guard", "Security", 2, "high"),
            ("Warehouse Inbound Unloading", "Warehouse & Fulfilment", 2, "06:00", "14:00", "Forklift Operator", "Forklift", 2, "normal"),
            ("Customer Support Day Desk", "Customer Support", 2, "08:00", "16:00", "Support Agent", "Customer Support", 3, "normal"),
            ("Festival Sale Surge", "Store Floor", 3, "10:00", "20:00", "Cashier", "Cashier", 3, "surge"),
            ("Evening Security Gate", "Security", 3, "18:00", "02:00", "Security Guard", "Security", 2, "high"),
            ("Order Packing Peak", "Warehouse & Fulfilment", 4, "08:00", "16:00", "Packing Associate", "Inventory", 2, "normal"),
            ("Window Display Setup", "Store Floor", 4, "10:00", "16:00", "Fashion Stylist", "Visual Merchandising", 1, "normal"),
        ],
    },
    "it": {
        "label": "IT Company", "icon": "💻", "tag": "Software teams, DevOps, QA, IT helpdesk",
        "biz": "Nimbus Tech Solutions", "manager_role": "Delivery Manager", "domain": "nimbustech.example",
        "depts": ["Engineering", "DevOps & Support", "QA", "IT Helpdesk"],
        "skills": ["Backend", "Frontend", "DevOps", "QA Testing", "Security Ops", "Helpdesk", "Team Lead", "On-call"],
        "emps": [
            ("Arjun Reddy", "Engineering Manager", "Engineering", "Team Lead,Backend,Frontend,On-call", [], WK, 40, "active"),
            ("Priya Menon", "Backend Developer", "Engineering", "Backend,On-call", [], WK, 40, "active"),
            ("Karthik Rao", "Frontend Developer", "Engineering", "Frontend,QA Testing", [], WK, 40, "active"),
            ("Sana Khan", "DevOps Engineer", "DevOps & Support", "DevOps,On-call,Security Ops", [("DevOps", 120), ("Security Ops", -10)], ALL, 44, "active"),
            ("Rahul Verma", "Site Reliability Engineer", "DevOps & Support", "DevOps,On-call", [("On-call", 15)], SIX, 44, "active"),
            ("Isha Nambiar", "QA Engineer", "QA", "QA Testing,Frontend", [], WK, 40, "active"),
            ("Manoj Pillai", "QA Lead", "QA", "QA Testing,Team Lead", [], WK, 40, "active"),
            ("Divya Shah", "Helpdesk Analyst", "IT Helpdesk", "Helpdesk", [], ALL, 40, "active"),
            ("Nikhil Bose", "Helpdesk Lead", "IT Helpdesk", "Helpdesk,Team Lead", [], WK, 40, "active"),
            ("Tara Joseph", "Support Intern", "IT Helpdesk", "Helpdesk", [], WE, 20, "reserve"),
        ],
        "shifts": [
            ("Production Support (Night)", "DevOps & Support", 1, "22:00", "06:00", "Site Reliability Engineer", "On-call", 2, "high"),
            ("Sprint Release Window", "Engineering", 1, "10:00", "18:00", "Backend Developer", "Backend", 2, "high"),
            ("Helpdesk Day Desk", "IT Helpdesk", 1, "08:00", "16:00", "Helpdesk Analyst", "Helpdesk", 2, "normal"),
            ("QA Regression Cycle", "QA", 2, "09:00", "17:00", "QA Engineer", "QA Testing", 2, "normal"),
            ("Infra Migration Window", "DevOps & Support", 2, "20:00", "04:00", "DevOps Engineer", "DevOps", 2, "high"),
            ("Hotfix War Room", "Engineering", 3, "09:00", "19:00", "Engineer", "Team Lead", 1, "surge"),
            ("Frontend Launch Support", "Engineering", 3, "10:00", "18:00", "Frontend Developer", "Frontend", 2, "normal"),
            ("Security Audit Review", "DevOps & Support", 4, "09:00", "17:00", "Security Analyst", "Security Ops", 1, "normal"),
        ],
    },
    "business": {
        "label": "Business Services", "icon": "🏢", "tag": "Call centres, sales, finance, office operations",
        "biz": "Apex Business Services", "manager_role": "Operations Head", "domain": "apexbiz.example",
        "depts": ["Customer Care", "Sales", "Finance & Admin", "Facilities & Security"],
        "skills": ["Voice Support", "Sales", "Accounting", "Admin", "Team Lead", "Compliance", "Security", "First Aid"],
        "emps": [
            ("Meghna Rao", "Operations Manager", "Customer Care", "Team Lead,Voice Support,Compliance", [], SIX, 40, "active"),
            ("Suresh Kumar", "Call Agent", "Customer Care", "Voice Support", [], WK, 40, "active"),
            ("Pooja Hegde", "Call Agent", "Customer Care", "Voice Support,Sales", [], ALL, 40, "active"),
            ("Faizan Ali", "Night Agent", "Customer Care", "Voice Support", [], "Fri,Sat,Sun,Mon", 40, "active"),
            ("Zoya Fernandes", "Part-time Agent", "Customer Care", "Voice Support", [], WE, 20, "reserve"),
            ("Lakshmi Devi", "Sales Executive", "Sales", "Sales,Voice Support", [], SIX, 40, "active"),
            ("Harsh Jain", "Sales Lead", "Sales", "Sales,Team Lead", [], WK, 40, "active"),
            ("Anil Kapoor", "Accountant", "Finance & Admin", "Accounting,Compliance", [("Compliance", 25)], WK, 40, "active"),
            ("Bhavna Shetty", "Admin Executive", "Finance & Admin", "Admin,Accounting", [], WK, 40, "active"),
            ("Gopal Naik", "Security Officer", "Facilities & Security", "Security,First Aid", [("Security", 200), ("First Aid", -5)], ALL, 48, "active"),
        ],
        "shifts": [
            ("Morning Call Desk", "Customer Care", 1, "07:00", "15:00", "Call Agent", "Voice Support", 3, "normal"),
            ("Customer Care Team Lead", "Customer Care", 1, "09:00", "17:00", "Operations Manager", "Team Lead", 1, "high"),
            ("Night Support Line", "Customer Care", 2, "22:00", "06:00", "Night Agent", "Voice Support", 2, "high"),
            ("Sales Campaign Day", "Sales", 2, "10:00", "18:00", "Sales Executive", "Sales", 3, "surge"),
            ("Month-end Accounts Closing", "Finance & Admin", 3, "09:00", "17:00", "Accountant", "Accounting", 2, "high"),
            ("Compliance Audit", "Finance & Admin", 3, "10:00", "16:00", "Accountant", "Compliance", 1, "normal"),
            ("Office Security Watch", "Facilities & Security", 3, "18:00", "02:00", "Security Officer", "Security", 2, "high"),
            ("Front Desk & Admin", "Finance & Admin", 4, "09:00", "17:00", "Admin Executive", "Admin", 2, "normal"),
        ],
    },
}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_sector():
    db = get_db()
    try:
        r = db.execute("SELECT v FROM meta WHERE k='sector'").fetchone()
    except sqlite3.Error:
        r = None
    db.close()
    return r["v"] if r and r["v"] in SECTORS else "retail"


def init_db(sector="retail"):
    """Create tables; auto-reset if old schema; seed if empty. Returns True if seeded."""
    db = get_db()
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}

    def cols(t):
        return [r[1] for r in db.execute(f"PRAGMA table_info({t})")]
    old = bool(("employees" in tables and "meta" not in tables) or
               (cols("employees") and "email" not in cols("employees")) or
               (cols("swaps") and "channel" not in cols("swaps")))
    if old:
        db.executescript(DROP)
    db.executescript(SCHEMA)
    seeded = False
    if db.execute("SELECT COUNT(*) c FROM employees").fetchone()["c"] == 0:
        _seed(db, sector)
        db.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('sector',?)", (sector,))
        seeded = True
    db.commit(); db.close()
    return seeded


def reset_db(sector=None):
    sector = sector or get_sector()
    db = get_db()
    db.executescript(DROP)
    db.close()
    init_db(sector)


def _seed(db, key):
    S = SECTORS[key]
    t = date.today()
    d = lambda n: (t + timedelta(days=n)).isoformat()
    for name, role, dept, skills, certs, days, mx, status in S["emps"]:
        email = name.split()[0].lower() + "@" + S["domain"]
        cs = ";".join(f"{k}:{d(o)}" for k, o in certs)
        db.execute("INSERT INTO employees(name,role,dept,email,skills,certs,avail_days,max_hours,status) VALUES(?,?,?,?,?,?,?,?,?)",
                   (name, role, dept, email, skills, cs, days, mx, status))
    for title, dept, off, st, en, role, skill, hc, pri in S["shifts"]:
        db.execute("INSERT INTO shifts(title,dept,shift_date,start_time,end_time,role,skill,headcount,priority) VALUES(?,?,?,?,?,?,?,?,?)",
                   (title, dept, d(off), st, en, role, skill, hc, pri))