import io, os, csv
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.sql import func
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# OCR
from PIL import Image
import pytesseract

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "budgetia.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = "change_this_secret_in_production"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{DB_PATH}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

# ---------- Models ----------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(180), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    monthly_salary = db.Column(db.Float, default=0.0)  # salaire mensuel
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pwd):
        self.password_hash = generate_password_hash(pwd)

    def check_password(self, pwd):
        return check_password_hash(self.password_hash, pwd)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    monthly_budget = db.Column(db.Float, nullable=False, default=0.0)
    color = db.Column(db.String(20), nullable=True)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(250), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    datetime = db.Column(db.DateTime, default=datetime.utcnow)

class Income(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)

# ---------- Utils ----------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def init_db():
    db.create_all()
    # create an example user if none (optional)
    if User.query.count() == 0:
        u = User(email="demo@exemple.com")
        u.set_password("demo123")
        u.monthly_salary = 2000.0
        db.session.add(u)
        db.session.commit()
        # sample categories for demo user
        defaults = [
            ("Nourriture", 300, "#60a5fa"),
            ("Transport", 120, "#34d399"),
            ("Logement", 800, "#f97316"),
            ("Loisirs", 150, "#f87171"),
            ("Santé", 50, "#a78bfa")
        ]
        for n,b,c in defaults:
            db.session.add(Category(user_id=u.id, name=n, monthly_budget=b, color=c))
        db.session.commit()

def total_expenses_month_for_user(user_id, year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year+1, 1, 1)
    else:
        end = datetime(year, month+1, 1)
    s = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.user_id==user_id,
        Expense.datetime >= start,
        Expense.datetime < end
    ).scalar()
    return float(s or 0.0)

def used_amount_for_category_month(user_id, cat_id, year, month):
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year+1, 1, 1)
    else:
        end = datetime(year, month+1, 1)
    s = db.session.query(func.coalesce(func.sum(Expense.amount), 0)).filter(
        Expense.user_id==user_id,
        Expense.category_id==cat_id,
        Expense.datetime >= start,
        Expense.datetime < end
    ).scalar()
    return float(s or 0.0)

def export_pdf_bytes(rows, title="Dépenses"):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, title)
    y -= 30
    c.setFont("Helvetica", 11)
    for r in rows:
        line = f"{r['datetime']}  |  {r['categorie']}  |  {r['titre']}  |  {r['montant']:.2f}€"
        c.drawString(50, y, line)
        y -= 16
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 11)
    c.save()
    buffer.seek(0)
    return buffer

# ---------- Routes ----------
@app.route("/")
@login_required
def index():
    # dashboard for current user
    today = datetime.utcnow()
    year, month = today.year, today.month
    # categories for user
    cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    categories_data = []
    for c in cats:
        used = used_amount_for_category_month(current_user.id, c.id, year, month)
        remaining = c.monthly_budget - used
        pct = round((used / c.monthly_budget)*100, 1) if c.monthly_budget > 0 else 0.0
        categories_data.append({
            "id": c.id, "name": c.name, "budget": c.monthly_budget,
            "used": used, "remaining": remaining, "pct": pct, "color": c.color or "#888"
        })
    expenses = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.datetime.desc()).limit(200).all()

    # last 6 months sums
    months = []
    sums = []
    for i in range(5, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1
        months.append(f"{y}-{m:02d}")
        sums.append(total_expenses_month_for_user(current_user.id, y, m))

    total_income_this_month = current_user.monthly_salary  # we use monthly_salary as main income
    total_expenses = total_expenses_month_for_user(current_user.id, year, month)
    remaining_global = total_income_this_month - total_expenses

    return render_template("dashboard.html",
                           categories=categories_data,
                           expenses=expenses,
                           months=months,
                           sums=sums,
                           year=year, month=month,
                           total_income=total_income_this_month,
                           total_expenses=total_expenses,
                           remaining_global=remaining_global)

# -------- Auth routes --------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd = request.form.get("password", "")
        salary = float(request.form.get("monthly_salary", 0) or 0)
        if not email or not pwd:
            flash("Email et mot de passe requis.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Cet email est déjà utilisé.", "warning")
            return redirect(url_for("register"))
        u = User(email=email, monthly_salary=salary)
        u.set_password(pwd)
        db.session.add(u)
        db.session.commit()
        # create a couple of default categories
        defaults = [("Nourriture", 300, "#60a5fa"), ("Transport", 120, "#34d399")]
        for n,b,c in defaults:
            db.session.add(Category(user_id=u.id, name=n, monthly_budget=b, color=c))
        db.session.commit()
        login_user(u)
        flash("Compte créé. Bienvenue !", "success")
        return redirect(url_for("index"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        pwd = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(pwd):
            flash("Email ou mot de passe invalide.", "danger")
            return redirect(url_for("login"))
        login_user(user)
        return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# -------- Categories CRUD --------
@app.route("/categories", methods=["GET", "POST"])
@login_required
def categories_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        budget = float(request.form.get("budget", 0) or 0)
        color = request.form.get("color") or "#888"
        if name:
            db.session.add(Category(user_id=current_user.id, name=name, monthly_budget=budget, color=color))
            db.session.commit()
        return redirect(url_for("categories_page"))
    cats = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
    return render_template("categories.html", categories=cats)

@app.route("/edit_category/<int:cat_id>", methods=["GET", "POST"])
@login_required
def edit_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.user_id != current_user.id:
        return "Accès refusé", 403
    if request.method == "POST":
        cat.name = request.form.get("name", cat.name)
        cat.monthly_budget = float(request.form.get("budget", cat.monthly_budget) or 0)
        cat.color = request.form.get("color", cat.color)
        db.session.commit()
        flash("Catégorie mise à jour.", "success")
        return redirect(url_for("categories_page"))
    return render_template("edit_category.html", category=cat)

@app.route("/delete_category/<int:cat_id>", methods=["POST"])
@login_required
def delete_category(cat_id):
    cat = Category.query.get_or_404(cat_id)
    if cat.user_id != current_user.id:
        return "Accès refusé", 403
    # Option : supprimer les dépenses associées ou les réassigner (ici on supprime)
    Expense.query.filter_by(category_id=cat.id).delete()
    db.session.delete(cat)
    db.session.commit()
    flash("Catégorie supprimée.", "info")
    return redirect(url_for("categories_page"))

# -------- Expenses --------
@app.route("/expenses")
@login_required
def expenses_page():
    page = int(request.args.get("page", 1))
    per_page = 50
    q = Expense.query.filter_by(user_id=current_user.id).order_by(Expense.datetime.desc())
    items = q.paginate(page=page, per_page=per_page, error_out=False)
    cats = {c.id: c.name for c in Category.query.filter_by(user_id=current_user.id).all()}
    return render_template("expenses.html", items=items, cats=cats)

@app.route("/add_expense", methods=["POST"])
@login_required
def add_expense():
    title = request.form.get("title", "").strip()
    amount = float(request.form.get("amount", 0) or 0)
    category_id = int(request.form.get("category_id"))
    dt_str = request.form.get("datetime")
    dt = datetime.fromisoformat(dt_str) if dt_str else datetime.utcnow()
    # verify category belongs to user
    cat = Category.query.get_or_404(category_id)
    if cat.user_id != current_user.id:
        return jsonify({"ok": False, "error": "Catégorie invalide."}), 403
    e = Expense(user_id=current_user.id, title=title, amount=amount, category_id=category_id, datetime=dt)
    db.session.add(e)
    db.session.commit()
    # compute usages and warnings
    now = dt
    used_cat = used_amount_for_category_month(current_user.id, category_id, now.year, now.month)
    pct = (used_cat / cat.monthly_budget * 100) if cat.monthly_budget > 0 else 0.0
    warning = None
    if pct >= 100:
        warning = {"level": "danger", "message": f"Budget {cat.name} dépassé ({pct:.1f}%)"}
    elif pct >= 90:
        warning = {"level": "warning", "message": f"Attention — {pct:.1f}% du budget {cat.name}"}
    elif pct >= 70:
        warning = {"level": "info", "message": f"Approche: {pct:.1f}% du budget {cat.name}"}
    # global remaining
    total_income = current_user.monthly_salary
    total_expenses = total_expenses_month_for_user(current_user.id, now.year, now.month)
    remaining_global = total_income - total_expenses
    return jsonify({
        "ok": True,
        "pct_category": round(pct,1),
        "remaining_category": round(cat.monthly_budget - used_cat,2),
        "remaining_global": round(remaining_global,2),
        "warning": warning
    })

# -------- Salary management --------
@app.route("/set_salary", methods=["POST"])
@login_required
def set_salary():
    try:
        s = float(request.form.get("monthly_salary", 0) or 0)
        current_user.monthly_salary = s
        db.session.commit()
        flash("Salaire mensuel mis à jour.", "success")
    except Exception:
        flash("Erreur lors de la mise à jour.", "danger")
    return redirect(url_for("index"))

# -------- Exports (CSV / XLSX / PDF) --------
@app.route("/export")
@login_required
def export():
    typ = request.args.get("type", "csv")  # csv|xlsx|pdf
    rng = request.args.get("range", "month")  # month|year|all
    year = int(request.args.get("year", datetime.utcnow().year))
    month = int(request.args.get("month", datetime.utcnow().month))
    q = Expense.query.filter_by(user_id=current_user.id)
    if rng == "month":
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year+1, 1, 1)
        else:
            end = datetime(year, month+1, 1)
        q = q.filter(Expense.datetime >= start, Expense.datetime < end)
    elif rng == "year":
        start = datetime(year, 1, 1)
        end = datetime(year+1, 1, 1)
        q = q.filter(Expense.datetime >= start, Expense.datetime < end)
    rows = []
    for e in q.order_by(Expense.datetime).all():
        cat = Category.query.get(e.category_id)
        rows.append({
            "titre": e.title,
            "montant": e.amount,
            "categorie": cat.name if cat else "",
            "datetime": e.datetime.isoformat()
        })
    if typ == "csv":
        si = io.StringIO()
        writer = csv.DictWriter(si, fieldnames=["titre","montant","categorie","datetime"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        mem = io.BytesIO()
        mem.write(si.getvalue().encode("utf-8"))
        mem.seek(0)
        fname = f"depenses_{rng}_{year}_{month if rng=='month' else ''}.csv"
        return send_file(mem, as_attachment=True, download_name=fname, mimetype="text/csv")
    elif typ == "xlsx":
        df = pd.DataFrame(rows)
        mem = io.BytesIO()
        with pd.ExcelWriter(mem, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name="Dépenses", index=False)
        mem.seek(0)
        fname = f"depenses_{rng}_{year}_{month if rng=='month' else ''}.xlsx"
        return send_file(mem, as_attachment=True, download_name=fname, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        # pdf
        pdfb = export_pdf_bytes(rows, title=f"Dépenses ({rng})")
        fname = f"depenses_{rng}_{year}_{month if rng=='month' else ''}.pdf"
        return send_file(pdfb, as_attachment=True, download_name=fname, mimetype="application/pdf")

# -------- OCR (scan ticket) --------
@app.route("/scan_ticket", methods=["GET","POST"])
@login_required
def scan_ticket():
    if request.method == "POST":
        if "ticket" not in request.files:
            return jsonify({"ok": False, "error": "Fichier manquant"}), 400
        file = request.files["ticket"]
        try:
            img = Image.open(file.stream).convert("RGB")
            # langue française si installé : 'fra'
            text = pytesseract.image_to_string(img, lang="fra") if 'fra' in pytesseract.get_languages(config='') else pytesseract.image_to_string(img)
            # On renvoie le texte brut — on pourrait ajouter un parseur "montant/date"
            return jsonify({"ok": True, "text": text})
        except Exception as e:
            return jsonify({"ok": False, "error": str(e)}), 500
    return render_template("scan_ticket.html")

# ---------- Run ----------
if __name__ == "__main__":
    # create DB + sample data inside app context
    with app.app_context():
        init_db()
    app.run(debug=True)