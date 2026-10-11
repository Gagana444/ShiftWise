import csv, io
from collections import Counter
from datetime import date, datetime, timedelta
from urllib.parse import quote
from flask import Flask, render_template, request, redirect, url_for, flash, Response, session, jsonify
from db import get_db, init_db, reset_db, get_sector, SECTORS
from engine import scheduler as sch

app = Flask(__name__)
app.secret_key = "codesprint-shiftwise"

EMP_OK = {"login", "logout", "static", "portal", "portal_avail", "portal_absent",
          "portal_swap", "portal_swap_action", "portal_read", "api_status"}

if init_db():
    sch.auto_assign()


@app.template_filter("fd")
def fd(v):
    return datetime.strptime(v, "%Y-%m-%d").strftime("%a, %d %b")


@app.errorhandler(404)
def not_found(e):
    if not session.get("user"):
        return redirect(url_for("login"))
    return redirect(url_for("portal" if session.get("role") == "employee" else "dashboard"))


@app.before_request
def guard():
    ep = request.endpoint
    if ep in ("login", "static") or ep is None:
        return
    if not session.get("user"):
        return redirect(url_for("login"))
    is_emp = session.get("role") == "employee"
    if is_emp and ep not in EMP_OK:
        return redirect(url_for("portal"))
    if not is_emp and ep.startswith("portal"):
        return redirect(url_for("dashboard"))


def _next_workday():
    d = date.today()
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


@app.context_processor
def inject():
    S = SECTORS[get_sector()]
    is_emp = session.get("role") == "employee"
    db = get_db()
    n = db.execute("SELECT COUNT(*) c FROM shifts").fetchone()["c"]
    sw = db.execute("SELECT COUNT(*) c FROM swaps WHERE status='accepted'").fetchone()["c"]
    if is_emp:
        nf = db.execute("SELECT COUNT(*) c FROM notifications WHERE is_read=0 AND emp_id=?", (session.get("emp_id"),)).fetchone()["c"]
    else:
        nf = db.execute("SELECT COUNT(*) c FROM notifications WHERE is_read=0 AND emp_id IS NULL").fetchone()["c"]
    db.close()
    return dict(nav_shifts=n, nav_swaps=sw, nav_notifs=nf, biz=S["biz"], sector=S, role=session.get("role", "manager"),
                manager=session.get("user", "Manager"), mgr_role="Employee" if is_emp else S["manager_role"],
                today=date.today().isoformat(), next_workday=_next_workday(), emergency=sch.is_emergency(),
                DEPTS=S["depts"], SKILLS=S["skills"], DAYS=sch.DAYS)


# ---------- helpers ----------
def back(default="shifts"):
    return redirect(request.form.get("next") or url_for(default))


def mail_link(to, subject, body):
    return f"mailto:{to}?subject={quote(subject)}&body={quote(body)}"


def notify(eid, title, body, channel="app"):
    db = get_db()
    e = db.execute("SELECT name, email FROM employees WHERE id=?", (eid,)).fetchone() if eid is not None else None
    db.execute("INSERT INTO notifications(emp_id,title,body,channel,created) VALUES(?,?,?,?,?)",
               (eid, title, body, channel, datetime.now().strftime("%d %b, %H:%M")))
    db.commit(); db.close()
    if e and channel in ("email", "both"):
        flash(mail_link(e["email"] or "", title, f"Hi {e['name']},\n\n{body}\n\n- ShiftWise"), "mail")


def stage(status, to_name):
    return {"awaiting": (f"⏳ Waiting for {to_name}", ""),
            "accepted": (f"✅ {to_name} agreed · awaiting manager", "sev-warning"),
            "declined": (f"❌ Declined by {to_name}", "bad"),
            "approved": ("🎉 Approved by manager", "good"),
            "rejected": ("🚫 Rejected by manager", "bad")}.get(status, (status, ""))


def swap_item(ctx, r):
    to = ctx["emps"].get(r["to_emp"])
    txt, cls = stage(r["status"], to["name"] if to else "colleague")
    return {"id": r["id"], "status": r["status"], "channel": r["channel"], "note": r["note"],
            "shift": ctx["shifts"].get(r["shift_id"]), "frm": ctx["emps"].get(r["from_emp"]), "to": to,
            "stage": txt, "cls": cls}


def record_absence(eid, d, reason):
    db = get_db()
    db.execute("INSERT INTO absences(employee_id, absent_date, reason) VALUES(?,?,?)", (eid, d, reason))
    db.commit(); db.close()
    ctx = sch.load()
    affected = [sid for sid, s in ctx["shifts"].items() if s["shift_date"] == d and eid in ctx["assigns"][sid]]
    db = get_db()
    for sid in affected:
        db.execute("DELETE FROM assignments WHERE shift_id=? AND employee_id=?", (sid, eid))
    db.commit(); db.close()
    added = sch.auto_assign(set(affected)) if affected else 0
    still = sum(m for s, m in sch.short_shifts(sch.load()) if s["id"] in affected)
    msg = (f"Absence recorded. {len(affected)} shift(s) affected, {added} replacement(s) auto-assigned"
           + (f", {still} slot(s) still short." if still else "."))
    return msg, bool(still)


def swap_options(ctx, only):
    options, elig = [], {}
    order = {"Same role": 0, "Same dept": 1, "Eligible": 2}
    for sid, lst in ctx["assigns"].items():
        s = ctx["shifts"][sid]
        if only not in lst:
            continue
        me, key = ctx["emps"][only], f"{sid}:{only}"
        options.append({"key": key, "label": f"{s['title']} — {s['shift_date']} {s['start_time']}-{s['end_time']}"})
        cands = []
        for oid, o in ctx["emps"].items():
            if oid == only or oid in lst or sch.hard_problems(ctx, oid, sid):
                continue
            tag = "Same role" if o["role"] == me["role"] else ("Same dept" if o["dept"] == me["dept"] else "Eligible")
            cands.append({"id": oid, "name": o["name"], "role": o["role"], "tag": tag})
        cands.sort(key=lambda c: (order[c["tag"]], c["name"]))
        elig[key] = cands
    return options, elig


# ---------- status + emergency ----------
@app.route("/api/status")
def api_status():
    return jsonify(emergency=sch.is_emergency(), role=session.get("role", "manager"))


@app.post("/emergency/on")
def emergency_on():
    sch.set_emergency(True)
    n = sch.auto_assign()
    ctx = sch.load()
    for e in ctx["emps"].values():
        if e["status"] == "reserve":
            notify(e["id"], "🚨 EMERGENCY MODE", "Emergency staffing is active. You may be called in for extra shifts. Check your portal.")
    notify(None, "Emergency mode activated", f"Rules relaxed (8h rest, 16h/day, 7 days). Reserves prioritised. {n} slot(s) auto-filled.")
    flash(f"🚨 EMERGENCY MODE ON: rules relaxed, reserve staff prioritised, {n} slot(s) auto-filled.", "error")
    return redirect(request.referrer or url_for("dashboard"))


@app.post("/emergency/off")
def emergency_off():
    sch.set_emergency(False)
    bad = len([c for c in sch.detect_conflicts() if not c["soft"]])
    flash(f"Emergency mode OFF. Normal rules restored. {bad} conflict(s) now need review." if bad
          else "Emergency mode OFF. Normal rules restored.", "error" if bad else "ok")
    return redirect(request.referrer or url_for("dashboard"))


# ---------- login ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        key = request.form.get("sector", "retail")
        role = request.form.get("role", "manager")
        name = request.form.get("name", "").strip()
        if key not in SECTORS or not name:
            flash("Please choose a sector and enter your name.", "error")
            return redirect(url_for("login"))
        if key != get_sector():
            reset_db(key)
            sch.auto_assign()
        session.clear()
        if role == "employee":
            db = get_db()
            n = name.lower()
            r = db.execute("SELECT id, name FROM employees WHERE LOWER(name) LIKE ? OR LOWER(email) LIKE ? ORDER BY id LIMIT 1",
                           (f"%{n}%", f"{n}%")).fetchone()
            db.close()
            if not r:
                flash("No employee found with that name. First name is enough (e.g. Neha).", "error")
                return redirect(url_for("login"))
            session["user"], session["role"], session["emp_id"] = r["name"], "employee", r["id"]
            return redirect(url_for("portal"))
        session["user"], session["role"] = name, "manager"
        return redirect(url_for("dashboard"))
    return render_template("login.html", sectors=SECTORS, current=get_sector())


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- dashboard ----------
@app.route("/")
def dashboard():
    return render_template("dashboard.html", st=sch.stats())


# ---------- shifts ----------
@app.route("/shifts")
def shifts():
    ctx = sch.load()
    dept, status = request.args.get("dept", "All"), request.args.get("status", "all")
    rows = []
    for sid, s in ctx["shifts"].items():
        if dept != "All" and s["dept"] != dept:
            continue
        assigned = [ctx["emps"][e] for e in ctx["assigns"][sid]]
        missing = s["headcount"] - len(assigned)
        if status == "gaps" and missing <= 0: continue
        if status == "filled" and missing > 0: continue
        cands = sch.suggestions(ctx, sid, 3) if missing > 0 else []
        why = sch.eligibility_report(ctx, sid)[:4] if missing > 0 and not cands else []
        rows.append({"s": s, "assigned": assigned, "missing": missing, "hours": sch.hours(s),
                     "cands": cands, "why": why,
                     "free": [e for e in ctx["emps"].values() if e["id"] not in ctx["assigns"][sid]]})
    return render_template("shifts.html", rows=rows, dept=dept, status=status, total=len(ctx["shifts"]))


@app.post("/shifts/create")
def shift_create():
    f = request.form
    try:
        hc = int(f.get("headcount", 0))
    except ValueError:
        hc = 0
    if not f.get("title", "").strip() or hc < 1:
        flash("Title and headcount (>=1) are required.", "error")
        return redirect(url_for("shifts"))
    db = get_db()
    cur = db.execute("INSERT INTO shifts(title,dept,shift_date,start_time,end_time,role,skill,headcount,priority) VALUES(?,?,?,?,?,?,?,?,?)",
                     (f["title"].strip(), f["dept"], f["shift_date"], f["start_time"], f["end_time"],
                      f.get("role", "").strip(), f.get("skill", ""), hc, f["priority"]))
    sid = cur.lastrowid
    db.commit(); db.close()
    ctx = sch.load()
    ok = len(sch.suggestions(ctx, sid, hc))
    if ok == 0:
        top = [r for r in sch.eligibility_report(ctx, sid) if r["reasons"]][:2]
        hint = " | ".join(f"{r['emp']['name']}: {r['reasons'][0]}" for r in top)
        flash(f"Shift created, but NO eligible staff. {hint}", "error")
    elif ok < hc:
        flash(f"Shift created. Only {ok} of {hc} required staff are eligible; the rest stays as a gap.", "error")
    else:
        flash("Shift created.", "ok")
    return redirect(url_for("shifts"))


@app.post("/employees/<int:eid>/add-day")
def employee_add_day(eid):
    day = request.form.get("day", "")
    if day not in sch.DAYS:
        return back()
    db = get_db()
    r = db.execute("SELECT name, avail_days FROM employees WHERE id=?", (eid,)).fetchone()
    if not r:
        db.close()
        return back()
    days = {d.strip() for d in (r["avail_days"] or "").split(",") if d.strip()} | {day}
    db.execute("UPDATE employees SET avail_days=? WHERE id=?", (",".join(d for d in sch.DAYS if d in days), eid))
    db.commit(); db.close()
    n = sch.auto_assign()
    flash(f"{r['name']} is now available on {day}. Auto-assign placed {n} staff member(s).", "ok")
    return back()


@app.post("/shifts/<int:sid>/delete")
def shift_delete(sid):
    db = get_db(); db.execute("DELETE FROM shifts WHERE id=?", (sid,)); db.commit(); db.close()
    flash("Shift deleted.", "ok")
    return redirect(url_for("shifts"))


@app.post("/shifts/<int:sid>/assign")
def assign(sid):
    eid = int(request.form["employee_id"])
    override = bool(request.form.get("override"))
    ctx = sch.load()
    if len(ctx["assigns"][sid]) >= ctx["shifts"][sid]["headcount"] and not override:
        flash("Shift is already fully staffed.", "error")
        return back()
    probs = sch.hard_problems(ctx, eid, sid)
    name = ctx["emps"][eid]["name"]
    if probs and not override:
        flash(f"Blocked – {name}: " + "; ".join(m for _, m, _ in probs) + "  (tick 'Override rules' to force)", "error")
        return back()
    db = get_db()
    db.execute("INSERT OR IGNORE INTO assignments(shift_id, employee_id) VALUES(?,?)", (sid, eid))
    db.commit(); db.close()
    if probs:
        flash(f"{name} assigned with MANAGER OVERRIDE — {len(probs)} rule(s) violated. See Conflicts & Gaps.", "error")
    else:
        flash(f"{name} assigned to {ctx['shifts'][sid]['title']}.", "ok")
    return back()


@app.post("/shifts/<int:sid>/unassign/<int:eid>")
def unassign(sid, eid):
    db = get_db()
    db.execute("DELETE FROM assignments WHERE shift_id=? AND employee_id=?", (sid, eid))
    db.commit(); db.close()
    flash("Assignment removed.", "ok")
    return back()


@app.post("/auto-assign")
def auto_assign_all():
    n = sch.auto_assign()
    flash(f"Auto-assign placed {n} staff member(s).", "ok")
    return back("dashboard")


@app.post("/repair")
def repair():
    removed, added = sch.repair()
    flash(f"Schedule repaired: {removed} conflicting assignment(s) removed, {added} new assignment(s) made.", "ok")
    return back("dashboard")


@app.post("/demo/conflicts")
def demo_conflicts():
    n = sch.inject_demo_conflicts()
    flash(f"Injected {n} demo rule violation(s). Review them below, then click One-Click Schedule Repair." if n
          else "Demo conflicts are already injected. Click Reset to start over.", "error" if n else "ok")
    return redirect(url_for("conflicts"))


@app.post("/publish")
def publish():
    ctx = sch.load()
    conf = [c for c in sch.detect_conflicts(ctx) if not c["soft"]]
    if conf:
        flash(f"Cannot publish: {len(conf)} conflict(s) must be resolved first.", "error")
        return redirect(url_for("conflicts"))
    db = get_db(); db.execute("UPDATE shifts SET published=1"); db.commit(); db.close()
    g = sum(m for _, m in sch.short_shifts(ctx))
    flash("Schedule published." + (f" Note: {g} slot(s) still unfilled." if g else ""), "ok")
    return redirect(url_for("schedule"))


@app.post("/unpublish")
def unpublish():
    db = get_db(); db.execute("UPDATE shifts SET published=0"); db.commit(); db.close()
    flash("Schedule moved back to draft.", "ok")
    return redirect(url_for("schedule"))


# ---------- employees ----------
@app.route("/employees")
def employees():
    ctx = sch.load()
    rows = [{"e": e, "fat": sch.fatigue(ctx, eid)} for eid, e in ctx["emps"].items()]
    return render_template("employees.html", rows=rows)


@app.post("/employees/add")
def employee_add():
    f = request.form
    if not f.get("name", "").strip():
        flash("Name is required.", "error"); return redirect(url_for("employees"))
    days = [d for d in sch.DAYS if d in f.getlist("days")]
    db = get_db()
    db.execute("INSERT INTO employees(name,role,dept,email,skills,avail_days,max_hours,status) VALUES(?,?,?,?,?,?,?,?)",
               (f["name"].strip(), f.get("role", ""), f["dept"], f.get("email", "").strip(),
                ",".join(f.getlist("skills")), ",".join(days), int(f.get("max_hours", 40)), "active"))
    db.commit(); db.close()
    flash("Employee added.", "ok")
    return redirect(url_for("employees"))


@app.post("/employees/<int:eid>/update")
def employee_update(eid):
    f = request.form
    days = [d for d in sch.DAYS if d in f.getlist("days")]
    db = get_db()
    db.execute("UPDATE employees SET email=?, skills=?, avail_days=?, certs=?, max_hours=?, status=? WHERE id=?",
               (f.get("email", "").strip(), ",".join(f.getlist("skills")), ",".join(days), f.get("certs", "").strip(),
                int(f.get("max_hours", 40)), f["status"], eid))
    db.commit(); db.close()
    bad = [c for c in sch.detect_conflicts() if c["eid"] == eid and not c["soft"]]
    if bad:
        flash(f"Updated – but {len(bad)} existing assignment(s) now conflict. Run One-Click Schedule Repair.", "error")
    else:
        flash("Availability & skills updated.", "ok")
    return redirect(url_for("employees"))


@app.post("/employees/<int:eid>/alert")
def employee_alert(eid):
    msg = request.form.get("message", "").strip() or "Please check your schedule."
    notify(eid, f"Shift alert from {session.get('user', 'Manager')}", msg, request.form.get("channel", "app"))
    flash("Alert sent.", "ok")
    return redirect(url_for("employees"))


@app.post("/employees/<int:eid>/delete")
def employee_delete(eid):
    db = get_db(); db.execute("DELETE FROM employees WHERE id=?", (eid,)); db.commit(); db.close()
    flash("Employee removed.", "ok")
    return redirect(url_for("employees"))


# ---------- intelligence ----------
@app.route("/skills")
def skills():
    skills_, rows = sch.skill_matrix(sch.load())
    return render_template("skills.html", skills=skills_, rows=rows)


@app.route("/simulator", methods=["GET", "POST"])
def simulator():
    result, chosen = None, request.form.get("scenario", "flu")
    if request.method == "POST":
        result = sch.simulate(chosen)
    return render_template("simulator.html", result=result, chosen=chosen, base=sch.coverage(sch.load()))


@app.route("/conflicts")
def conflicts():
    ctx = sch.load()
    conf = sch.detect_conflicts(ctx)
    kinds = Counter(c["label"] for c in conf)
    return render_template("conflicts.html", conflicts=conf, gaps=sch.gaps(ctx), kinds=kinds,
                           hard_n=sum(1 for c in conf if not c["soft"]))


# ---------- absences ----------
@app.route("/absences")
def absences():
    db = get_db()
    rows = db.execute("SELECT a.*, e.name, e.role FROM absences a JOIN employees e ON e.id=a.employee_id ORDER BY absent_date DESC").fetchall()
    emps = db.execute("SELECT id, name, role, dept FROM employees ORDER BY name").fetchall()
    db.close()
    week = []
    for i in range(7):
        dd = date.today() + timedelta(days=i)
        week.append({"label": dd.strftime("%a"), "num": dd.day, "mon": dd.strftime("%b"),
                     "people": [r for r in rows if r["absent_date"] == dd.isoformat()]})
    return render_template("absences.html", rows=rows, emps=emps, week=week)


@app.post("/absences/add")
def absence_add():
    msg, short = record_absence(int(request.form["employee_id"]), request.form["absent_date"], request.form.get("reason", ""))
    flash(msg, "error" if short else "ok")
    return redirect(url_for("absences"))


@app.post("/absences/<int:aid>/delete")
def absence_delete(aid):
    db = get_db(); db.execute("DELETE FROM absences WHERE id=?", (aid,)); db.commit(); db.close()
    return redirect(url_for("absences"))


# ---------- swaps (manager approval) ----------
@app.route("/swaps")
def swaps():
    ctx = sch.load()
    db = get_db()
    rows = db.execute("SELECT * FROM swaps ORDER BY id DESC").fetchall()
    notifs = db.execute("SELECT n.*, CASE WHEN n.emp_id IS NULL THEN 'Manager' ELSE e.name END AS name "
                        "FROM notifications n LEFT JOIN employees e ON e.id=n.emp_id ORDER BY n.id DESC LIMIT 20").fetchall()
    db.close()
    items = [swap_item(ctx, r) for r in rows]
    cnt = {"awaiting": sum(1 for i in items if i["status"] == "awaiting"),
           "accepted": sum(1 for i in items if i["status"] == "accepted"),
           "done": sum(1 for i in items if i["status"] in ("approved", "rejected", "declined"))}
    return render_template("swaps.html", items=items, notifs=notifs, cnt=cnt)


@app.post("/swaps/<int:wid>/<action>")
def swap_action(wid, action):
    db = get_db()
    sw = db.execute("SELECT * FROM swaps WHERE id=?", (wid,)).fetchone()
    db.close()
    if not sw or sw["status"] != "accepted":
        flash("This swap is still waiting for the colleague to accept.", "error")
        return redirect(url_for("swaps"))
    ctx = sch.load()
    title = ctx["shifts"][sw["shift_id"]]["title"]
    if action == "approve":
        if sw["from_emp"] in ctx["assigns"][sw["shift_id"]]:
            ctx["assigns"][sw["shift_id"]].remove(sw["from_emp"])
        probs = sch.hard_problems(ctx, sw["to_emp"], sw["shift_id"])
        if probs:
            flash("Swap blocked: " + "; ".join(m for _, m, _ in probs), "error")
            return redirect(url_for("swaps"))
        db = get_db()
        db.execute("DELETE FROM assignments WHERE shift_id=? AND employee_id=?", (sw["shift_id"], sw["from_emp"]))
        db.execute("INSERT OR IGNORE INTO assignments(shift_id, employee_id) VALUES(?,?)", (sw["shift_id"], sw["to_emp"]))
        db.execute("UPDATE swaps SET status='approved' WHERE id=?", (wid,))
        db.commit(); db.close()
        notify(sw["to_emp"], "Swap approved", f"You are now assigned to '{title}'.")
        notify(sw["from_emp"], "Swap approved", f"You are released from '{title}'.")
        flash("Swap approved and roster updated.", "ok")
    else:
        db = get_db()
        db.execute("UPDATE swaps SET status='rejected' WHERE id=?", (wid,))
        db.commit(); db.close()
        notify(sw["from_emp"], "Swap rejected", f"Manager rejected your swap request for '{title}'.")
        notify(sw["to_emp"], "Swap rejected", f"Manager rejected the swap for '{title}'. You keep your schedule.")
        flash("Swap rejected.", "ok")
    return redirect(url_for("swaps"))


@app.post("/notifications/read")
def notifications_read():
    db = get_db(); db.execute("UPDATE notifications SET is_read=1"); db.commit(); db.close()
    return redirect(url_for("swaps"))


# ---------- employee portal ----------
@app.route("/portal")
def portal():
    eid = session["emp_id"]
    ctx = sch.load()
    me = ctx["emps"].get(eid)
    if not me:
        session.clear()
        return redirect(url_for("login"))
    mine = [ctx["shifts"][sid] for sid, lst in ctx["assigns"].items() if eid in lst]
    mine.sort(key=lambda s: (s["shift_date"], s["start_time"]))
    db = get_db()
    notifs = db.execute("SELECT * FROM notifications WHERE emp_id=? ORDER BY id DESC LIMIT 10", (eid,)).fetchall()
    inc = db.execute("SELECT * FROM swaps WHERE to_emp=? ORDER BY id DESC", (eid,)).fetchall()
    out = db.execute("SELECT * FROM swaps WHERE from_emp=? ORDER BY id DESC", (eid,)).fetchall()
    myabs = db.execute("SELECT * FROM absences WHERE employee_id=? ORDER BY absent_date DESC", (eid,)).fetchall()
    db.close()
    options, elig = swap_options(ctx, eid)
    return render_template("portal.html", me=me, mine=mine, fat=sch.fatigue(ctx, eid),
                           hrs=round(sch.total_hours(ctx, eid), 1), notifs=notifs,
                           incoming=[swap_item(ctx, r) for r in inc], outgoing=[swap_item(ctx, r) for r in out],
                           myabs=myabs, options=options, elig=elig)


@app.post("/portal/availability")
def portal_avail():
    f, eid = request.form, session["emp_id"]
    days = [d for d in sch.DAYS if d in f.getlist("days")]
    db = get_db()
    db.execute("UPDATE employees SET avail_days=?, skills=? WHERE id=?", (",".join(days), ",".join(f.getlist("skills")), eid))
    db.commit(); db.close()
    bad = [c for c in sch.detect_conflicts() if c["eid"] == eid and not c["soft"]]
    if bad:
        notify(None, "Availability change causes conflicts", f"{session['user']} updated availability; {len(bad)} assigned shift(s) now conflict.")
    flash("Availability & skills saved." + (f" Note: {len(bad)} of your shifts now conflict — manager alerted." if bad else ""),
          "error" if bad else "ok")
    return redirect(url_for("portal"))


@app.post("/portal/absent")
def portal_absent():
    msg, short = record_absence(session["emp_id"], request.form["absent_date"], request.form.get("reason", ""))
    notify(None, "Employee absence", f"{session['user']} marked absent on {request.form['absent_date']}. {msg}")
    flash(msg, "error" if short else "ok")
    return redirect(url_for("portal"))


@app.post("/portal/swap")
def portal_swap():
    f, me_id = request.form, session["emp_id"]
    if not f.get("to_emp") or not f.get("assignment"):
        flash("No eligible colleague available for that shift.", "error")
        return redirect(url_for("portal"))
    sid, frm = map(int, f["assignment"].split(":"))
    to, channel, note = int(f["to_emp"]), f.get("channel", "app"), f.get("note", "").strip()
    if frm != me_id:
        return redirect(url_for("portal"))
    db = get_db()
    dup = db.execute("SELECT 1 FROM swaps WHERE shift_id=? AND from_emp=? AND status IN ('awaiting','accepted')", (sid, frm)).fetchone()
    if dup:
        db.close()
        flash("You already have an open swap request for that shift.", "error")
        return redirect(url_for("portal"))
    db.execute("INSERT INTO swaps(shift_id, from_emp, to_emp, status, channel, note) VALUES(?,?,?,?,?,?)",
               (sid, frm, to, "awaiting", channel, note))
    s = db.execute("SELECT * FROM shifts WHERE id=?", (sid,)).fetchone()
    db.commit(); db.close()
    body = (f"{session['user']} is asking you to take '{s['title']}' on {s['shift_date']} ({s['start_time']}-{s['end_time']})."
            + (f" Note: {note}." if note else "") + " Open your portal to accept or decline.")
    notify(to, "Shift swap request", body, channel)
    flash("Request sent to your colleague. If they accept, your manager will confirm.", "ok")
    return redirect(url_for("portal"))


@app.post("/portal/swap/<int:wid>/<action>")
def portal_swap_action(wid, action):
    me_id = session["emp_id"]
    db = get_db()
    sw = db.execute("SELECT * FROM swaps WHERE id=?", (wid,)).fetchone()
    db.close()
    if not sw or sw["to_emp"] != me_id or sw["status"] != "awaiting":
        return redirect(url_for("portal"))
    ctx = sch.load()
    title = ctx["shifts"][sw["shift_id"]]["title"]
    me = session["user"]

    def setst(v):
        d = get_db(); d.execute("UPDATE swaps SET status=? WHERE id=?", (v, wid)); d.commit(); d.close()

    if action == "decline":
        setst("declined")
        notify(sw["from_emp"], "Swap declined", f"{me} declined to take '{title}'. Try asking another colleague.")
        flash("Swap declined.", "ok")
        return redirect(url_for("portal"))
    if sw["from_emp"] not in ctx["assigns"][sw["shift_id"]]:
        setst("declined")
        flash("That shift is no longer assigned to the requester.", "error")
        return redirect(url_for("portal"))
    ctx["assigns"][sw["shift_id"]].remove(sw["from_emp"])
    probs = sch.hard_problems(ctx, me_id, sw["shift_id"])
    if probs:
        setst("declined")
        why = "; ".join(m for _, m, _ in probs)
        notify(sw["from_emp"], "Swap auto-declined", f"{me} cannot take '{title}': {why}")
        flash(f"You can't take this shift: {why}", "error")
        return redirect(url_for("portal"))
    setst("accepted")
    notify(sw["from_emp"], "Swap accepted by colleague", f"{me} agreed to take '{title}'. Waiting for manager approval.")
    notify(None, "Swap awaiting your approval", f"{ctx['emps'][sw['from_emp']]['name']} → {me} for '{title}'.")
    flash("You accepted. The manager will now confirm the swap.", "ok")
    return redirect(url_for("portal"))


@app.post("/portal/read")
def portal_read():
    db = get_db(); db.execute("UPDATE notifications SET is_read=1 WHERE emp_id=?", (session["emp_id"],)); db.commit(); db.close()
    return redirect(url_for("portal"))


# ---------- training ----------
@app.route("/training")
def training():
    return render_template("training.html", gaps=sch.training_gaps(sch.load()))


@app.post("/training/complete")
def training_complete():
    eid, skill = int(request.form["employee_id"]), request.form["skill"]
    db = get_db()
    e = db.execute("SELECT * FROM employees WHERE id=?", (eid,)).fetchone()
    sk = [x for x in (e["skills"] or "").split(",") if x]
    if skill not in sk: sk.append(skill)
    certs = [c for c in (e["certs"] or "").split(";") if c and not c.startswith(skill + ":")]
    certs.append(f"{skill}:{(date.today() + timedelta(days=365)).isoformat()}")
    db.execute("UPDATE employees SET skills=?, certs=? WHERE id=?", (",".join(sk), ";".join(certs), eid))
    db.commit(); db.close()
    flash(f"{e['name']} certified in {skill} (valid 1 year).", "ok")
    return redirect(url_for("training"))


# ---------- published schedule / export ----------
@app.route("/schedule")
def schedule():
    ctx = sch.load()
    days = {}
    for sid, s in ctx["shifts"].items():
        days.setdefault(s["shift_date"], []).append({
            "s": s, "names": [ctx["emps"][e]["name"] for e in ctx["assigns"][sid]],
            "missing": s["headcount"] - len(ctx["assigns"][sid])})
    published = bool(ctx["shifts"]) and all(s["published"] for s in ctx["shifts"].values())
    nconf = sum(1 for c in sch.detect_conflicts(ctx) if not c["soft"])
    return render_template("schedule.html", days=days, published=published, nconf=nconf)


@app.route("/export.csv")
def export():
    ctx = sch.load()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["Date", "Shift", "Department", "Start", "End", "Skill", "Required", "Assigned", "Status"])
    for sid, s in ctx["shifts"].items():
        names = ", ".join(ctx["emps"][e]["name"] for e in ctx["assigns"][sid])
        w.writerow([s["shift_date"], s["title"], s["dept"], s["start_time"], s["end_time"], s["skill"],
                    s["headcount"], names, "Published" if s["published"] else "Draft"])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=roster.csv"})


@app.post("/reset")
def reset():
    sch.set_emergency(False)
    reset_db(get_sector()); sch.auto_assign()
    flash("Demo data reset.", "ok")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)