import os
from datetime import datetime, timedelta, date
from math import ceil
from db import get_db

MIN_REST_HOURS = 11
MAX_DAILY_HOURS = 12
MAX_CONSEC_DAYS = 5
MAX_NIGHTS_WEEK = 3
CERT_WARN_DAYS = 30
EMERGENCY_FILE = "emergency.flag"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
PRI = {"surge": 0, "high": 1, "normal": 2}
SEVERITY = {"overlap": "critical", "absent": "critical", "rest": "critical", "skill": "critical",
            "cert": "critical", "leave": "critical", "consec": "critical", "daily": "critical",
            "hours": "warning", "avail": "warning", "certsoon": "advisory", "night": "advisory"}
LABEL = {"overlap": "Double booking", "absent": "Absent", "rest": "Rest violation", "skill": "Skill mismatch",
         "cert": "Expired certification", "leave": "On leave", "consec": "Consecutive days",
         "daily": "Excess daily hours", "hours": "Weekly overtime", "avail": "Unavailable day",
         "certsoon": "Cert expiring soon", "night": "Night-shift load"}
SOFT = {"certsoon", "night"}
GROUP = {"hours", "consec", "daily", "night"}
SEV_ORDER = {"critical": 0, "warning": 1, "advisory": 2}


# ---------- emergency mode ----------
def is_emergency():
    return os.path.exists(EMERGENCY_FILE)

def set_emergency(on):
    if on:
        open(EMERGENCY_FILE, "w").write("on")
    elif os.path.exists(EMERGENCY_FILE):
        os.remove(EMERGENCY_FILE)

def limits():
    """(min_rest, max_daily, max_consecutive). Relaxed during emergency."""
    if is_emergency():
        return 8, 16, 7
    return MIN_REST_HOURS, MAX_DAILY_HOURS, MAX_CONSEC_DAYS


# ---------- helpers ----------
def _dt(d, t):
    return datetime.strptime(f"{d} {t}", "%Y-%m-%d %H:%M")

def span(s):
    st, en = _dt(s["shift_date"], s["start_time"]), _dt(s["shift_date"], s["end_time"])
    if en <= st:
        en += timedelta(days=1)
    return st, en

def hours(s):
    st, en = span(s)
    return (en - st).total_seconds() / 3600

def _week(d):
    return datetime.strptime(d, "%Y-%m-%d").isocalendar()[:2]

def _plus(d, n):
    return (datetime.strptime(d, "%Y-%m-%d") + timedelta(days=n)).strftime("%Y-%m-%d")

def is_night(s):
    st, en = span(s)
    return st.hour >= 20 or st.hour < 6 or en.date() != st.date()

def parse_certs(txt):
    out = []
    for part in (txt or "").split(";"):
        if ":" in part:
            n, d = part.split(":", 1)
            out.append({"name": n.strip(), "expiry": d.strip()})
    return out

def load():
    db = get_db()
    emps = {r["id"]: dict(r) for r in db.execute("SELECT * FROM employees ORDER BY id")}
    shifts = {r["id"]: dict(r) for r in db.execute("SELECT * FROM shifts ORDER BY shift_date, start_time")}
    assigns = {sid: [] for sid in shifts}
    for r in db.execute("SELECT shift_id, employee_id FROM assignments"):
        if r["shift_id"] in assigns:
            assigns[r["shift_id"]].append(r["employee_id"])
    absent = {(r["employee_id"], r["absent_date"]) for r in db.execute("SELECT * FROM absences")}
    db.close()
    for e in emps.values():
        e["skill_list"] = [x.strip() for x in (e["skills"] or "").split(",") if x.strip()]
        e["day_list"] = [x.strip() for x in (e["avail_days"] or "").split(",") if x.strip()]
        e["cert_list"] = parse_certs(e["certs"])
    return {"emps": emps, "shifts": shifts, "assigns": assigns, "absent": absent}

def emp_shifts(ctx, eid, exclude=None):
    return [sid for sid, lst in ctx["assigns"].items() if eid in lst and sid != exclude]

def total_hours(ctx, eid):
    return sum(hours(ctx["shifts"][sid]) for sid in emp_shifts(ctx, eid))


# ---------- rules engine ----------
def problems(ctx, eid, sid):
    e, s, p = ctx["emps"][eid], ctx["shifts"][sid], []
    min_rest, max_daily, max_consec = limits()
    emerg = is_emergency()
    st, en = span(s)
    if e["status"] == "leave":
        p.append(("leave", "Employee is on leave", None))
    if (eid, s["shift_date"]) in ctx["absent"]:
        p.append(("absent", f"Marked absent on {s['shift_date']}", None))
    d = DAYS[st.weekday()]
    if d not in e["day_list"] and not (emerg and e["status"] == "reserve"):
        p.append(("avail", f"Not available on {d}", None))
    if s["skill"]:
        if s["skill"] not in e["skill_list"]:
            p.append(("skill", f"Missing skill: {s['skill']}", None))
        for c in e["cert_list"]:
            if c["name"] == s["skill"]:
                if c["expiry"] < s["shift_date"]:
                    p.append(("cert", f"{c['name']} certification expired on {c['expiry']}", None))
                elif c["expiry"] <= _plus(s["shift_date"], CERT_WARN_DAYS):
                    p.append(("certsoon", f"{c['name']} certification expires {c['expiry']} (within {CERT_WARN_DAYS} days)", None))
    mine = emp_shifts(ctx, eid, exclude=sid)
    for osid in mine:
        o = ctx["shifts"][osid]
        ost, oen = span(o)
        if st < oen and ost < en:
            p.append(("overlap", f"Overlaps '{o['title']}'", osid))
        else:
            gap = (st - oen).total_seconds() / 3600 if st >= oen else (ost - en).total_seconds() / 3600
            if gap < min_rest:
                p.append(("rest", f"Only {gap:.0f}h rest vs '{o['title']}' (min {min_rest}h)", osid))
    wk = _week(s["shift_date"])
    same_wk = [o for o in mine if _week(ctx["shifts"][o]["shift_date"]) == wk]
    tot = hours(s) + sum(hours(ctx["shifts"][o]) for o in same_wk)
    if tot > e["max_hours"]:
        p.append(("hours", f"{tot:.0f}h that week exceeds {e['max_hours']}h limit", wk))
    day_tot = hours(s) + sum(hours(ctx["shifts"][o]) for o in mine if ctx["shifts"][o]["shift_date"] == s["shift_date"])
    if day_tot > max_daily:
        p.append(("daily", f"{day_tot:.0f}h scheduled on {s['shift_date']} (max {max_daily}h/day)", s["shift_date"]))
    dates = {ctx["shifts"][o]["shift_date"] for o in mine} | {s["shift_date"]}
    cur = datetime.strptime(s["shift_date"], "%Y-%m-%d").date()
    lo = hi = cur
    while (lo - timedelta(days=1)).isoformat() in dates: lo -= timedelta(days=1)
    while (hi + timedelta(days=1)).isoformat() in dates: hi += timedelta(days=1)
    run = (hi - lo).days + 1
    if run > max_consec:
        p.append(("consec", f"{run} consecutive working days (max {max_consec})", lo.isoformat()))
    if is_night(s):
        n = 1 + sum(1 for o in same_wk if is_night(ctx["shifts"][o]))
        if n > MAX_NIGHTS_WEEK:
            p.append(("night", f"{n} night shifts this week (recommended max {MAX_NIGHTS_WEEK})", wk))
    return p

def hard_problems(ctx, eid, sid):
    return [x for x in problems(ctx, eid, sid) if x[0] not in SOFT]

def suggestions(ctx, sid, limit=5):
    s, out = ctx["shifts"][sid], []
    emerg = is_emergency()
    for eid, e in ctx["emps"].items():
        if eid in ctx["assigns"][sid] or hard_problems(ctx, eid, sid):
            continue
        h = total_hours(ctx, eid)
        score = 100 - h * 1.5
        if s["role"] and e["role"] == s["role"]: score += 25
        if e["dept"] == s["dept"]: score += 15
        if e["status"] == "reserve": score += 30 if emerg else -20
        out.append({"emp": e, "score": round(score), "hours": round(h, 1)})
    out.sort(key=lambda x: -x["score"])
    return out[:limit]

def eligibility_report(ctx, sid):
    """Every unassigned employee with the hard rules blocking them (empty list = eligible)."""
    s = ctx["shifts"][sid]
    shift_day = DAYS[span(s)[0].weekday()]
    rows = []
    for eid, e in ctx["emps"].items():
        if eid in ctx["assigns"][sid]:
            continue
        probs = hard_problems(ctx, eid, sid)
        rows.append({"emp": e,
                     "reasons": [m for _, m, _ in probs],
                     "fix_day": shift_day if any(k == "avail" for k, _, _ in probs) else None,
                     "only_avail": bool(probs) and all(k == "avail" for k, _, _ in probs)})
    rows.sort(key=lambda r: (len(r["reasons"]), r["emp"]["name"]))
    return rows

def short_shifts(ctx):
    return [(s, s["headcount"] - len(ctx["assigns"][sid]))
            for sid, s in ctx["shifts"].items() if s["headcount"] > len(ctx["assigns"][sid])]

def gaps(ctx):
    return [{"shift": s, "missing": m, "candidates": suggestions(ctx, s["id"], 3)} for s, m in short_shifts(ctx)]

def detect_conflicts(ctx=None):
    ctx = ctx or load()
    seen, out = set(), []
    for sid, lst in ctx["assigns"].items():
        for eid in lst:
            for kind, msg, other in problems(ctx, eid, sid):
                if kind in GROUP: key = (kind, eid, other)
                elif other: key = (kind, eid, frozenset((sid, other)))
                else: key = (kind, eid, sid)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"kind": kind, "label": LABEL[kind], "severity": SEVERITY[kind], "msg": msg,
                            "sid": sid, "eid": eid, "shift": ctx["shifts"][sid], "emp": ctx["emps"][eid],
                            "soft": kind in SOFT})
    out.sort(key=lambda c: SEV_ORDER[c["severity"]])
    return out

def fatigue(ctx, eid):
    e, weeks = ctx["emps"][eid], {}
    for sid in emp_shifts(ctx, eid):
        w = _week(ctx["shifts"][sid]["shift_date"])
        weeks[w] = weeks.get(w, 0) + hours(ctx["shifts"][sid])
    peak = max(weeks.values()) if weeks else 0
    idx = min(100, int(peak / max(e["max_hours"], 1) * 100))
    label, cls = ("Optimal", "ok") if idx < 40 else (("Moderate", "mid") if idx < 70 else ("High Risk", "high"))
    return {"idx": idx, "peak": round(peak, 1), "label": label, "cls": cls}


# ---------- assignment ----------
def _fill(ctx, only_ids=None):
    added = []
    order = sorted(ctx["shifts"].values(), key=lambda s: (PRI.get(s["priority"], 2), s["shift_date"], s["start_time"]))
    for s in order:
        if only_ids and s["id"] not in only_ids:
            continue
        while len(ctx["assigns"][s["id"]]) < s["headcount"]:
            sug = suggestions(ctx, s["id"], 1)
            if not sug:
                break
            eid = sug[0]["emp"]["id"]
            ctx["assigns"][s["id"]].append(eid)
            added.append((s["id"], eid))
    return added

def auto_assign(only_ids=None):
    ctx = load()
    added = _fill(ctx, only_ids)
    db = get_db()
    for sid, eid in added:
        db.execute("INSERT OR IGNORE INTO assignments(shift_id, employee_id) VALUES(?,?)", (sid, eid))
    db.commit(); db.close()
    return len(added)

def repair():
    removed = 0
    for _ in range(80):
        cs = [c for c in detect_conflicts(load()) if not c["soft"]]
        if not cs:
            break
        c = cs[0]
        db = get_db()
        db.execute("DELETE FROM assignments WHERE shift_id=? AND employee_id=?", (c["sid"], c["eid"]))
        db.commit(); db.close()
        removed += 1
    return removed, auto_assign()

def inject_demo_conflicts():
    ctx = load()
    db = get_db()
    if db.execute("SELECT COUNT(*) c FROM shifts WHERE title LIKE 'Demo:%'").fetchone()["c"]:
        db.close()
        return 0
    made, today = 0, date.today().isoformat()

    def new_shift(title, dept, d, st, en, skill=""):
        cur = db.execute("INSERT INTO shifts(title,dept,shift_date,start_time,end_time,role,skill,headcount,priority) VALUES(?,?,?,?,?,?,?,?,?)",
                         (title, dept, d, st, en, "", skill, 1, "high"))
        return cur.lastrowid

    def force(sid, eid):
        db.execute("INSERT OR IGNORE INTO assignments(shift_id, employee_id) VALUES(?,?)", (sid, eid))

    pairs = [(sid, eid) for sid, lst in ctx["assigns"].items() for eid in lst if ctx["emps"][eid]["status"] == "active"]
    if pairs:
        sid, eid = pairs[0]
        s = ctx["shifts"][sid]
        st, en = span(s)
        st2 = st + timedelta(hours=2)
        a = new_shift("Demo: Overlapping Cover", s["dept"], st2.date().isoformat(), st2.strftime("%H:%M"),
                      (st2 + timedelta(hours=4)).strftime("%H:%M"))
        force(a, eid); made += 1
        st3 = en + timedelta(hours=4)
        b = new_shift("Demo: Back-to-back Shift", s["dept"], st3.date().isoformat(), st3.strftime("%H:%M"),
                      (st3 + timedelta(hours=6)).strftime("%H:%M"))
        force(b, eid); made += 1
        for sid2, eid2 in pairs:
            if eid2 != eid:
                db.execute("INSERT INTO absences(employee_id, absent_date, reason) VALUES(?,?,?)",
                           (eid2, ctx["shifts"][sid2]["shift_date"], "Sick Leave (demo)"))
                made += 1
                break
    for sid, s in ctx["shifts"].items():
        if s["skill"]:
            lacking = [e for e in ctx["emps"].values() if s["skill"] not in e["skill_list"]
                       and e["status"] == "active" and e["id"] not in ctx["assigns"][sid]]
            if lacking:
                force(sid, lacking[0]["id"]); made += 1
                break
    for e in ctx["emps"].values():
        exp = [c for c in e["cert_list"] if c["expiry"] < today]
        if exp:
            name = exp[0]["name"]
            tgt = next((sid for sid, s in ctx["shifts"].items() if s["skill"] == name), None)
            if tgt is None:
                tgt = new_shift(f"Demo: {name} Station", e["dept"], (date.today() + timedelta(days=2)).isoformat(),
                                "10:00", "16:00", name)
            force(tgt, e["id"]); made += 1
            break
    pool = [e for e in ctx["emps"].values() if e["status"] == "reserve"] or sorted(ctx["emps"].values(), key=lambda e: e["max_hours"])
    emp = pool[0]
    d5 = (date.today() + timedelta(days=5)).isoformat()
    x = new_shift("Demo: Double Shift A", emp["dept"], d5, "05:00", "16:00")
    y = new_shift("Demo: Double Shift B", emp["dept"], d5, "16:30", "03:30")
    force(x, emp["id"]); force(y, emp["id"]); made += 2
    db.commit(); db.close()
    return made


# ---------- analytics ----------
def coverage(ctx):
    req = sum(s["headcount"] for s in ctx["shifts"].values())
    filled = sum(min(len(ctx["assigns"][sid]), s["headcount"]) for sid, s in ctx["shifts"].items())
    return round(filled / req * 100, 1) if req else 100.0

def _bucket(ctx, keyfn, labelfn):
    b = {}
    for sid, s in ctx["shifts"].items():
        d = b.setdefault(keyfn(s), {"req": 0, "filled": 0})
        d["req"] += s["headcount"]
        d["filled"] += min(len(ctx["assigns"][sid]), s["headcount"])
    return [{"label": labelfn(k), "req": v["req"], "filled": v["filled"],
             "pct": round(100 * v["filled"] / v["req"]) if v["req"] else 100} for k, v in sorted(b.items())]

def stats(ctx=None):
    ctx = ctx or load()
    n = len(ctx["shifts"]) or 1
    conf, g = detect_conflicts(ctx), gaps(ctx)
    hard_n = sum(1 for c in conf if not c["soft"])
    cov = coverage(ctx)
    buffer = round(100 * sum(1 for sid in ctx["shifts"] if suggestions(ctx, sid, 1)) / n, 1)
    skills_pct = round(100 * sum(1 for s in ctx["shifts"].values()
                                 if not s["skill"] or any(s["skill"] in e["skill_list"] for e in ctx["emps"].values())) / n, 1)
    rules = max(0, 100 - 10 * hard_n)
    fat = {eid: fatigue(ctx, eid) for eid in ctx["emps"]}
    burn = [{"emp": ctx["emps"][eid], "fat": f} for eid, f in fat.items() if f["idx"] >= 70]
    res = round((cov + buffer + skills_pct + rules) / 4)
    label, cls = ("Strong", "ok") if res >= 80 else (("Moderate Risk", "mid") if res >= 60 else ("High Risk", "high"))
    req = sum(s["headcount"] for s in ctx["shifts"].values())
    filled = sum(min(len(ctx["assigns"][sid]), s["headcount"]) for sid, s in ctx["shifts"].items())
    return {"coverage": cov, "req": req, "filled": filled, "gaps": g, "gap_slots": sum(x["missing"] for x in g),
            "conflicts": conf, "hard_n": hard_n, "soft_n": len(conf) - hard_n, "burnout": burn, "fat": fat,
            "buffer": buffer, "skills_pct": skills_pct, "rules": rules, "resilience": res,
            "res_label": label, "res_cls": cls,
            "days": _bucket(ctx, lambda s: s["shift_date"], lambda k: datetime.strptime(k, "%Y-%m-%d").strftime("%a %d")),
            "depts": _bucket(ctx, lambda s: s["dept"], lambda k: k),
            "units": len(set(s["dept"] for s in ctx["shifts"].values())),
            "active": sum(1 for e in ctx["emps"].values() if e["status"] == "active"),
            "reserve": sum(1 for e in ctx["emps"].values() if e["status"] == "reserve"),
            "total_emps": len(ctx["emps"])}

def skill_matrix(ctx):
    skills = sorted({k for e in ctx["emps"].values() for k in e["skill_list"]} |
                    {s["skill"] for s in ctx["shifts"].values() if s["skill"]})
    rows = []
    for sid, s in ctx["shifts"].items():
        cells = []
        for k in skills:
            n = sum(1 for eid in ctx["assigns"][sid] if k in ctx["emps"][eid]["skill_list"])
            req = (k == s["skill"])
            cls = ("c0" if req else "cn") if n == 0 else ("c1" if n == 1 else "c2")
            cells.append({"n": n, "cls": cls, "req": req})
        rows.append({"s": s, "cells": cells})
    return skills, rows

def training_gaps(ctx):
    today, soon, out = date.today().isoformat(), (date.today() + timedelta(days=30)).isoformat(), []
    for eid, e in ctx["emps"].items():
        need = {s["skill"] for s in ctx["shifts"].values() if s["dept"] == e["dept"] and s["skill"]}
        missing = [k for k in sorted(need) if k not in e["skill_list"]]
        expired = [c["name"] for c in e["cert_list"] if c["expiry"] < today]
        expiring = [c["name"] for c in e["cert_list"] if today <= c["expiry"] <= soon]
        if missing or expired or expiring:
            out.append({"emp": e, "missing": missing, "expired": expired, "expiring": expiring})
    return out

def simulate(scenario):
    ctx = load()
    before = coverage(ctx)
    victims, title = [], ""
    if scenario == "flu":
        title = "Seasonal Rush / Flu Outbreak"
        ranked = sorted([e for e in ctx["emps"].values() if e["status"] == "active"], key=lambda e: -total_hours(ctx, e["id"]))
        victims = ranked[:3]
    elif scenario == "lead":
        title = "Key Supervisor Absence (48h)"
        sup = sorted([e for e in ctx["emps"].values() if "Supervisor" in e["skill_list"] or "Team Lead" in e["skill_list"]],
                     key=lambda e: -total_hours(ctx, e["id"]))
        victims = sup[:1]
    else:
        title = "Demand Surge (+50%)"
        for s in ctx["shifts"].values():
            s["headcount"] = ceil(s["headcount"] * 1.5)
    for v in victims:
        v["status"] = "leave"
        for lst in ctx["assigns"].values():
            if v["id"] in lst: lst.remove(v["id"])
    after, short_after = coverage(ctx), sum(m for _, m in short_shifts(ctx))
    refill = _fill(ctx)
    final = coverage(ctx)
    unresolved = [(s["title"], m) for s, m in short_shifts(ctx)]
    verdict, cls = ("Resilient", "ok") if final >= 90 else (("Strained", "mid") if final >= 70 else ("Critical", "high"))
    return {"title": title, "before": before, "after": after, "final": final, "short_after": short_after,
            "victims": [v["name"] for v in victims], "recovered": len(refill),
            "reserve_used": sum(1 for _, eid in refill if ctx["emps"][eid]["status"] == "reserve"),
            "unresolved": unresolved, "verdict": verdict, "cls": cls}