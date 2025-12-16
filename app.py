from database import SessionLocal


import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from functools import wraps
from io import StringIO, BytesIO

from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from sqlalchemy import func
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

from database import Base, engine, SessionLocal
from models import Fruit, Sector, Picker, Harvest, User, BoxSize, PriceList

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev")

Base.metadata.create_all(bind=engine)
def get_db(): return SessionLocal()

login_manager = LoginManager(app)
login_manager.login_view = "login"

class UserAdapter(UserMixin):
    def __init__(self, u): self._u=u
    def get_id(self): return str(self._u.id)
    @property
    def role(self): return self._u.role
    @property
    def username(self): return self._u.username
    @property
    def active(self): return bool(self._u.active)

@login_manager.user_loader
def load_user(uid):
    db = get_db()
    u = db.get(User, int(uid))
    return UserAdapter(u) if u else None

def roles_required(*roles):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **k):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                flash("No tienes permisos para esta acción.", "danger")
                return redirect(url_for("index"))
            return fn(*a, **k)
        return wrapper
    return deco

@app.context_processor
def inject_today(): return {"today": date.today()}

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method=="POST":
        u = request.form.get("username","").strip()
        p = request.form.get("password","").strip()
        db = get_db()
        user = db.query(User).filter(User.username==u, User.active==1).first()
        if user and check_password_hash(user.password_hash, p):
            login_user(UserAdapter(user)); flash("Bienvenido.", "success")
            return redirect(url_for("index"))
        flash("Usuario o contraseña inválidos.", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user(); flash("Sesión cerrada.", "info")
    return redirect(url_for("login"))

@app.route("/")
@login_required
def index():
    db = get_db()
    start = date.today() - timedelta(days=6)
    end   = date.today()
    total_boxes = db.query(func.coalesce(func.sum(Harvest.boxes),0)).filter(Harvest.date.between(start,end)).scalar()
    total_money = db.query(func.coalesce(func.sum(Harvest.total),0)).filter(Harvest.date.between(start,end)).scalar()

    by_fruit = db.query(Fruit.name, func.coalesce(func.sum(Harvest.boxes),0)).join(Harvest, Harvest.fruit_id==Fruit.id)\
                 .filter(Harvest.date.between(start,end)).group_by(Fruit.name).all()
    by_sector= db.query(Sector.code, func.coalesce(func.sum(Harvest.boxes),0)).join(Harvest, Harvest.sector_id==Sector.id)\
                 .filter(Harvest.date.between(start,end)).group_by(Sector.code).all()

    f_labels = [r[0] for r in by_fruit]; f_boxes = [int(r[1]) for r in by_fruit]
    s_labels = [r[0] for r in by_sector]; s_boxes = [int(r[1]) for r in by_sector]

    return render_template("dashboard.html", total_boxes=total_boxes, total_money=total_money,
                           start=start, end=end, f_labels=f_labels, f_boxes=f_boxes,
                           s_labels=s_labels, s_boxes=s_boxes)

@app.route("/catalogs", methods=["GET","POST"])
@login_required
@roles_required("admin")
def catalogs():
    db = get_db()
    if request.method=="POST":
        action = request.form.get("action")
        try:
            if action=="add_fruit":
                name = request.form.get("fruit_name","").strip()
                if name: db.add(Fruit(name=name, active=1)); db.commit(); flash("Fruto agregado.","success")
            elif action=="toggle_fruit":
                fid=int(request.form["fruit_id"]); f=db.get(Fruit,fid); f.active=0 if f.active else 1; db.commit(); flash("Estado actualizado.","success")
            elif action=="delete_fruit":
                fid=int(request.form["fruit_id"]); db.delete(db.get(Fruit,fid)); db.commit(); flash("Fruto eliminado.","success")

            elif action=="add_sector":
                code=request.form.get("sector_code","").strip(); desc=request.form.get("sector_desc","").strip()
                if code: db.add(Sector(code=code, description=desc, active=1)); db.commit(); flash("Sector agregado.","success")
            elif action=="toggle_sector":
                sid=int(request.form["sector_id"]); s=db.get(Sector,sid); s.active=0 if s.active else 1; db.commit(); flash("Estado actualizado.","success")
            elif action=="delete_sector":
                sid=int(request.form["sector_id"]); db.delete(db.get(Sector,sid)); db.commit(); flash("Sector eliminado.","success")

            elif action=="add_picker":
                code=request.form.get("picker_code","").strip(); name=request.form.get("picker_name","").strip(); 
                if code and name: db.add(Picker(code=code, name=name, active=1)); db.commit(); flash("Cortadora agregada.","success")
            elif action=="toggle_picker":
                pid=int(request.form["picker_id"]); p=db.get(Picker,pid); p.active=0 if p.active else 1; db.commit(); flash("Estado actualizado.","success")
            elif action=="delete_picker":
                pid=int(request.form["picker_id"]); db.delete(db.get(Picker,pid)); db.commit(); flash("Cortadora eliminada.","success")

            elif action=="add_size":
                name=request.form.get("size_name","").strip()
                if name: db.add(BoxSize(name=name, active=1)); db.commit(); flash("Tamaño agregado.","success")
            elif action=="toggle_size":
                zid=int(request.form["size_id"]); z=db.get(BoxSize,zid); z.active=0 if z.active else 1; db.commit(); flash("Estado actualizado.","success")
            elif action=="delete_size":
                zid=int(request.form["size_id"]); db.delete(db.get(BoxSize,zid)); db.commit(); flash("Tamaño eliminado.","success")

            elif action=="set_price":
                fruit_id=int(request.form["fruit_id"]); size_id=int(request.form["size_id"]); price=Decimal(request.form.get("price") or "0")
                pl=db.query(PriceList).filter(PriceList.fruit_id==fruit_id, PriceList.size_id==size_id).first()
                if pl: pl.price=price
                else:  db.add(PriceList(fruit_id=fruit_id, size_id=size_id, price=price))
                db.commit(); flash("Precio guardado.","success")
            elif action=="delete_price":
                pid=int(request.form["price_id"]); db.delete(db.get(PriceList,pid)); db.commit(); flash("Precio eliminado.","success")

        except Exception as e:
            db.rollback(); flash(f"Error: {e}", "danger")
        return redirect(url_for("catalogs"))

    fruits=db.query(Fruit).order_by(Fruit.name).all()
    sectors=db.query(Sector).order_by(Sector.code).all()
    pickers=db.query(Picker).order_by(Picker.code).all()
    sizes=db.query(BoxSize).order_by(BoxSize.name).all()
    prices=db.query(PriceList).order_by(PriceList.id.desc()).all()
    return render_template("catalogs.html", fruits=fruits, sectors=sectors, pickers=pickers, sizes=sizes, prices=prices)

@app.route("/api/price")
@login_required
def api_price():
    db=get_db()
    fruit_id=int(request.args.get("fruit_id","0") or 0)
    size_id =int(request.args.get("size_id","0") or 0)
    price=None
    if fruit_id and size_id:
        pl=db.query(PriceList).filter(PriceList.fruit_id==fruit_id, PriceList.size_id==size_id).first()
        if pl: price=float(pl.price)
    return jsonify({"price": price})

@app.route("/api/harvests/bulk", methods=["POST"])
@login_required
def api_harvests_bulk():
    db = get_db()
    payload = request.get_json(silent=True) or {}
    items = payload.get("items", [])
    results = []
    try:
        for item in items:
            try:
                d = datetime.strptime(item["date"], "%Y-%m-%d").date()
                fruit_id  = int(item["fruit_id"])
                sector_id = int(item["sector_id"])
                picker_id = int(item["picker_id"])
                size_id   = int(item["size_id"])
                boxes     = int(item.get("boxes") or 0)
                price     = Decimal(str(item.get("price") or item.get("price_per_box") or "0"))
                total     = boxes * price
                h = Harvest(
                    date=d, fruit_id=fruit_id, sector_id=sector_id,
                    picker_id=picker_id, size_id=size_id, boxes=boxes,
                    price_per_box=price, total=total,
                    created_by=int(current_user.get_id())
                )
                db.add(h); db.flush()
                results.append({"temp_id": item.get("temp_id"), "id": h.id, "ok": True})
            except Exception as e:
                results.append({"temp_id": item.get("temp_id"), "ok": False, "error": str(e)})
        db.commit()
    except Exception as e:
        db.rollback()
        return jsonify({"ok": False, "error": str(e), "saved": results}), 400
    return jsonify({"ok": True, "saved": results})

@app.route("/harvests/new", methods=["GET","POST"])
@login_required
def harvest_new():
    db=get_db()
    if request.method=="POST":
        try:
            d = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            fruit_id  = int(request.form["fruit_id"])
            sector_id = int(request.form["sector_id"])
            picker_id = int(request.form["picker_id"])
            size_id   = int(request.form["size_id"])
            boxes     = int(request.form.get("boxes") or 0)
            price     = Decimal(request.form.get("price") or "0")
            total     = boxes * price
            h = Harvest(date=d, fruit_id=fruit_id, sector_id=sector_id, picker_id=picker_id,
                        size_id=size_id, boxes=boxes, price_per_box=price, total=total,
                        created_by=int(current_user.get_id()))
            db.add(h); db.commit()
            flash("Corte registrado.","success")
            return redirect(url_for("harvest_new"))
        except Exception as e:
            db.rollback(); flash(f"Error: {e}", "danger")
    fruits  = db.query(Fruit).filter(Fruit.active==1).order_by(Fruit.name).all()
    sectors = db.query(Sector).filter(Sector.active==1).order_by(Sector.code).all()
    pickers = db.query(Picker).filter(Picker.active==1).order_by(Picker.code).all()
    sizes   = db.query(BoxSize).filter(BoxSize.active==1).order_by(BoxSize.name).all()
    return render_template("harvest_form.html", fruits=fruits, sectors=sectors, pickers=pickers, sizes=sizes,
                           default_date=date.today().strftime("%Y-%m-%d"))

@app.route("/harvests")
@login_required
def harvest_list():
    db=get_db(); q=db.query(Harvest)
    df=request.args.get("date_from"); dt=request.args.get("date_to")
    fruit_id=request.args.get("fruit_id"); sector_id=request.args.get("sector_id")
    picker_id=request.args.get("picker_id"); size_id=request.args.get("size_id")

    if df: q=q.filter(Harvest.date>=datetime.strptime(df,"%Y-%m-%d").date())
    if dt: q=q.filter(Harvest.date<=datetime.strptime(dt,"%Y-%m-%d").date())
    if fruit_id and fruit_id.isdigit():  q=q.filter(Harvest.fruit_id==int(fruit_id))
    if sector_id and sector_id.isdigit():q=q.filter(Harvest.sector_id==int(sector_id))
    if picker_id and picker_id.isdigit():q=q.filter(Harvest.picker_id==int(picker_id))
    if size_id and size_id.isdigit():    q=q.filter(Harvest.size_id==int(size_id))

    items = q.order_by(Harvest.date.desc(), Harvest.id.desc()).limit(2000).all()

    fruits  = db.query(Fruit).order_by(Fruit.name).all()
    sectors = db.query(Sector).order_by(Sector.code).all()
    pickers = db.query(Picker).order_by(Picker.code).all()
    sizes   = db.query(BoxSize).order_by(BoxSize.name).all()

    total_boxes = sum(i.boxes for i in items) if items else 0
    total_money = sum(float(i.total) for i in items) if items else 0.0

    return render_template("harvest_list.html", items=items, fruits=fruits, sectors=sectors,
                           pickers=pickers, sizes=sizes, total_boxes=total_boxes, total_money=total_money)

@app.route("/harvests/<int:hid>/edit", methods=["GET","POST"])
@login_required
def harvest_edit(hid):
    db=get_db(); h=db.get(Harvest,hid)
    if not h:
        flash("Registro no encontrado.","warning")
        return redirect(url_for("harvest_list"))
    if request.method=="POST":
        try:
            h.date  = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
            h.fruit_id  = int(request.form["fruit_id"])
            h.sector_id = int(request.form["sector_id"])
            h.picker_id = int(request.form["picker_id"])
            h.size_id   = int(request.form["size_id"])
            h.boxes = int(request.form.get("boxes") or 0)
            h.price_per_box = Decimal(request.form.get("price") or "0")
            h.total = h.boxes * h.price_per_box
            db.commit(); flash("Cambios guardados.","success")
            return redirect(url_for("harvest_list"))
        except Exception as e:
            db.rollback(); flash(f"Error: {e}", "danger")
    fruits  = db.query(Fruit).order_by(Fruit.name).all()
    sectors = db.query(Sector).order_by(Sector.code).all()
    pickers = db.query(Picker).order_by(Picker.code).all()
    sizes   = db.query(BoxSize).order_by(BoxSize.name).all()
    return render_template("harvest_edit.html", h=h, fruits=fruits, sectors=sectors, pickers=pickers, sizes=sizes)

@app.route("/harvests/<int:hid>/delete", methods=["POST"])
@login_required
@roles_required("admin")
def harvest_delete(hid):
    db=get_db(); h=db.get(Harvest,hid)
    if not h:
        flash("Registro no encontrado.","warning")
        return redirect(url_for("harvest_list"))
    try:
        db.delete(h); db.commit(); flash("Registro eliminado.","success")
    except Exception as e:
        db.rollback(); flash(f"Error: {e}","danger")
    return redirect(url_for("harvest_list"))

@app.route("/export.csv")
@login_required
def export_csv():
    import csv, io
    db=get_db(); q=db.query(Harvest)
    df=request.args.get("date_from"); dt=request.args.get("date_to")
    fruit_id=request.args.get("fruit_id"); sector_id=request.args.get("sector_id")
    picker_id=request.args.get("picker_id"); size_id=request.args.get("size_id")
    if df: q=q.filter(Harvest.date>=datetime.strptime(df,"%Y-%m-%d").date())
    if dt: q=q.filter(Harvest.date<=datetime.strptime(dt,"%Y-%m-%d").date())
    if fruit_id and fruit_id.isdigit():  q=q.filter(Harvest.fruit_id==int(fruit_id))
    if sector_id and sector_id.isdigit():q=q.filter(Harvest.sector_id==int(sector_id))
    if picker_id and picker_id.isdigit():q=q.filter(Harvest.picker_id==int(picker_id))
    if size_id and size_id.isdigit():    q=q.filter(Harvest.size_id==int(size_id))
    items = q.order_by(Harvest.date.desc(), Harvest.id.desc()).all()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(["id","date","fruit","size","sector","picker","boxes","price_per_box","total","created_by"])
    for i in items:
        w.writerow([i.id, i.date.isoformat(), i.fruit.name, i.size.name, i.sector.code, i.picker.code,
                    i.boxes, f"{i.price_per_box:.2f}", f"{i.total:.2f}", i.created_by or ""])
    out.seek(0)
    return send_file(io.BytesIO(out.getvalue().encode("utf-8")),
                     mimetype="text/csv", as_attachment=True, download_name="harvests.csv")



@app.route("/weekly")
@login_required
def weekly():
    db = get_db()

    # Fin de semana = VIERNES (semana de Sábado a Viernes)
    fri_str = request.args.get("friday")
    sat_str = request.args.get("saturday")  # compatibilidad

    if fri_str:
        end_day = datetime.strptime(fri_str, "%Y-%m-%d").date()
    elif sat_str:
        s = datetime.strptime(sat_str, "%Y-%m-%d").date()
        end_day = s + timedelta(days=6)  # sábado -> viernes siguiente
    else:
        today = date.today()
        # weekday(): 0=Lun ... 4=Vie ... 6=Dom
        end_day = today - timedelta((today.weekday() - 4) % 7)  # viernes más reciente (<= hoy)

    start = end_day - timedelta(days=6)  # sábado anterior

    sizes = db.query(BoxSize).filter(BoxSize.active == 1).all()
    order = {"4oz": 0, "5oz": 1, "6oz": 2, "12oz": 3}
    sizes = sorted(sizes, key=lambda s: order.get(s.name, 99))

    rows = (
        db.query(Picker.id, Picker.code, Picker.name, BoxSize.name,
                 func.coalesce(func.sum(Harvest.boxes), 0))
          .join(Harvest, Harvest.picker_id == Picker.id)
          .join(BoxSize, BoxSize.id == Harvest.size_id)
          .filter(Harvest.date.between(start, end_day))
          .group_by(Picker.id, Picker.code, Picker.name, BoxSize.name)
          .all()
    )

    data = {}
    for pid, code, name, size_name, boxes in rows:
        rec = data.setdefault(
            pid, {"code": code, "name": name,
                  "sizes": {s.name: 0 for s in sizes},
                  "total_boxes": 0, "total_money": 0.0}
        )
        rec["sizes"][size_name] = int(boxes)

    money_rows = (
        db.query(Picker.id, func.coalesce(func.sum(Harvest.total), 0))
          .join(Harvest, Harvest.picker_id == Picker.id)
          .filter(Harvest.date.between(start, end_day))
          .group_by(Picker.id)
          .all()
    )
    for pid, m in money_rows:
        if pid in data:
            data[pid]["total_money"] = float(m)

    for rec in data.values():
        rec["total_boxes"] = sum(rec["sizes"].values())

    total_by_size = {s.name: 0 for s in sizes}
    for rec in data.values():
        for sname, val in rec["sizes"].items():
            total_by_size[sname] += val
    total_boxes = sum(rec["total_boxes"] for rec in data.values())
    total_money = sum(rec["total_money"] for rec in data.values())

    table = list(data.values())
    table.sort(key=lambda r: r["code"])

    return render_template(
        "weekly.html",
        start=start,
        friday=end_day,
        saturday=end_day,  # compatibilidad con plantilla antigua
        sizes=sizes,
        table=table,
        total_by_size=total_by_size,
        total_boxes=total_boxes,
        total_money=total_money
    )


@app.route("/weekly.csv")
@login_required
def weekly_csv():
    db = get_db()

    fri_str = request.args.get("friday")
    sat_str = request.args.get("saturday")

    if fri_str:
        end_day = datetime.strptime(fri_str, "%Y-%m-%d").date()
    elif sat_str:
        s = datetime.strptime(sat_str, "%Y-%m-%d").date()
        end_day = s + timedelta(days=6)
    else:
        today = date.today()
        end_day = today - timedelta((today.weekday() - 4) % 7)  # viernes más reciente (<= hoy)

    start = end_day - timedelta(days=6)  # sábado anterior

    sizes = db.query(BoxSize).filter(BoxSize.active == 1).all()
    order = {"4oz": 0, "5oz": 1, "6oz": 2, "12oz": 3}
    sizes = sorted(sizes, key=lambda s: order.get(s.name, 99))

    rows = (
        db.query(Picker.code, Picker.name, BoxSize.name,
                 func.coalesce(func.sum(Harvest.boxes), 0).label("boxes"),
                 func.coalesce(func.sum(Harvest.total), 0).label("money"))
          .join(Harvest, Harvest.picker_id == Picker.id)
          .join(BoxSize, BoxSize.id == Harvest.size_id)
          .filter(Harvest.date.between(start, end_day))
          .group_by(Picker.code, Picker.name, BoxSize.name)
          .all()
    )

    data = {}
    for code, name, size_name, boxes, _money in rows:
        rec = data.setdefault(
            code, {"code": code, "name": name,
                   "sizes": {s.name: 0 for s in sizes},
                   "money": 0.0}
        )
        rec["sizes"][size_name] = int(boxes)

    money_rows = (
        db.query(Picker.code, func.coalesce(func.sum(Harvest.total), 0))
          .join(Harvest, Harvest.picker_id == Picker.id)
          .filter(Harvest.date.between(start, end_day))
          .group_by(Picker.code)
          .all()
    )
    for code, m in money_rows:
        if code in data:
            data[code]["money"] = float(m)

    from io import StringIO, BytesIO
    import csv
    out = StringIO()
    w = csv.writer(out)
    header = ["ID", "Nombre"] + [s.name for s in sizes] + ["Total cajas", "Total $"]
    w.writerow([f"Semana {start} a {end_day} (Sábado a Viernes)"])
    w.writerow(header)

    total_by_size = {s.name: 0 for s in sizes}
    total_boxes = 0
    total_money = 0.0

    for code in sorted(data.keys()):
        rec = data[code]
        row_sizes = [rec["sizes"][s.name] for s in sizes]
        row_total = sum(row_sizes)
        w.writerow([rec["code"], rec["name"], *row_sizes, row_total, f"{rec['money']:.2f}"])
        for s in sizes:
            total_by_size[s.name] += rec["sizes"][s.name]
        total_boxes += row_total
        total_money += rec["money"]

    w.writerow([])
    w.writerow(["TOTAL", ""] + [total_by_size[s.name] for s in sizes] +
               [total_boxes, f"{total_money:.2f}"])

    out.seek(0)
    return send_file(BytesIO(out.getvalue().encode("utf-8")),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name=f"semana_{start}_a_{end_day}.csv")


@app.route("/reports")
@login_required
def reports():
    db = get_db()
    df = request.args.get("date_from")
    dt = request.args.get("date_to")
    if df and dt:
        start = datetime.strptime(df, "%Y-%m-%d").date()
        end = datetime.strptime(dt, "%Y-%m-%d").date()
    else:
        end = date.today()
        start = end - timedelta(days=30)

    sizes = db.query(BoxSize).filter(BoxSize.active == 1).all()
    order = {"4oz": 0, "5oz": 1, "6oz": 2, "12oz": 3}
    sizes = sorted(sizes, key=lambda s: order.get(s.name, 99))

    q_fruit = (
        db.query(
            Fruit.id,
            Fruit.name,
            BoxSize.name,
            func.coalesce(func.sum(Harvest.boxes), 0),
        )
        .join(Harvest, Harvest.fruit_id == Fruit.id)
        .join(BoxSize, BoxSize.id == Harvest.size_id)
        .filter(Harvest.date.between(start, end))
        .group_by(Fruit.id, Fruit.name, BoxSize.name)
        .all()
    )

    q_sector = (
        db.query(
            Sector.id,
            Sector.code,
            BoxSize.name,
            func.coalesce(func.sum(Harvest.boxes), 0),
        )
        .join(Harvest, Harvest.sector_id == Sector.id)
        .join(BoxSize, BoxSize.id == Harvest.size_id)
        .filter(Harvest.date.between(start, end))
        .group_by(Sector.id, Sector.code, BoxSize.name)
        .all()
    )

    q_picker = (
        db.query(
            Picker.id,
            Picker.code,
            Picker.name,
            BoxSize.name,
            func.coalesce(func.sum(Harvest.boxes), 0),
        )
        .join(Harvest, Harvest.picker_id == Picker.id)
        .join(BoxSize, BoxSize.id == Harvest.size_id)
        .filter(Harvest.date.between(start, end))
        .group_by(Picker.id, Picker.code, Picker.name, BoxSize.name)
        .all()
    )

    def build_rows(q, label_builder):
        data = {}
        names = {}

        for row in q:
            # Soporta filas de 4 (fruto/sector) o 5 columnas (cortadora)
            if len(row) == 5:
                key, lbl_a, lbl_b, size_name, boxes = row
                label = label_builder(lbl_a, lbl_b)
            elif len(row) == 4:
                key, lbl_a, size_name, boxes = row
                label = label_builder(lbl_a, None)
            else:
                continue

            rec = data.setdefault(key, {s.name: 0 for s in sizes})
            rec[size_name] = int(boxes or 0)
            names[key] = label

        rows = []
        for key, rec in data.items():
            rows.append(
                {
                    "label": names.get(key, str(key)),
                    "sizes": rec,
                    "total": sum(rec.values()),
                }
            )
        rows.sort(key=lambda r: r["label"])

        totals_by_size = {s.name: 0 for s in sizes}
        for r in rows:
            for sname, val in r["sizes"].items():
                totals_by_size[sname] += val
        grand_total = sum(totals_by_size.values())

        return rows, totals_by_size, grand_total

    fruit_rows, fruit_totals, fruit_grand = build_rows(q_fruit, lambda name, _: name)
    sector_rows, sector_totals, sector_grand = build_rows(q_sector, lambda code, _: code)
    picker_rows, picker_totals, picker_grand = build_rows(
        q_picker, lambda code, name: f"{code} — {name}"
    )

    return render_template(
        "reports.html",
        start=start,
        end=end,
        sizes=sizes,
        fruit_rows=fruit_rows,
        fruit_totals=fruit_totals,
        fruit_grand=fruit_grand,
        sector_rows=sector_rows,
        sector_totals=sector_totals,
        sector_grand=sector_grand,
        picker_rows=picker_rows,
        picker_totals=picker_totals,
        picker_grand=picker_grand,
    )


@app.route("/dev-login")
def dev_login():
    from database import SessionLocal
    from models import User
    db = SessionLocal()
    u = db.query(User).filter_by(username="admin").first()
    if not u:
        return "No existe el usuario admin. Corre seed.py o create_user.py.", 500
    # Reusa el adaptador que ya está definido en el archivo
    login_user(UserAdapter(u))
    return redirect(url_for("index"))

@app.teardown_appcontext
def shutdown_session(exception=None):
    # Esto se ejecuta al final de CADA request
    SessionLocal.remove()



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

