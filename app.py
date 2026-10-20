"""Smart Book Store Management System - Flask application."""
import os
import secrets
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "bookstore.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-secret-key")


# ------------------------------------------------------------------ database
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(seed=True):
    db = sqlite3.connect(DATABASE)
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())
    if seed and db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        db.execute("INSERT INTO users (name,email,password_hash,role) VALUES (?,?,?,?)",
                   ("Administrator", "admin@bookstore.com",
                    generate_password_hash("admin123"), "admin"))
        for c in ("Programming", "Fiction", "Science", "Self-Help", "History"):
            db.execute("INSERT INTO categories (name) VALUES (?)", (c,))
        books = [
            ("Python Crash Course", "Eric Matthes", "9781593279288", 1, 799, 15,
             "A hands-on, project-based introduction to Python."),
            ("Flask Web Development", "Miguel Grinberg", "9781491991732", 1, 650, 10,
             "Develop web applications with Python and Flask."),
            ("Clean Code", "Robert C. Martin", "9780132350884", 1, 699, 8,
             "A handbook of agile software craftsmanship."),
            ("The Alchemist", "Paulo Coelho", "9780062315007", 2, 299, 25,
             "A fable about following your dream."),
            ("To Kill a Mockingbird", "Harper Lee", "9780061120084", 2, 349, 12,
             "A classic novel of justice and childhood."),
            ("A Brief History of Time", "Stephen Hawking", "9780553380163", 3, 450, 9,
             "From the big bang to black holes."),
            ("Atomic Habits", "James Clear", "9780735211292", 4, 499, 20,
             "Tiny changes, remarkable results."),
            ("Sapiens", "Yuval Noah Harari", "9780062316097", 5, 599, 14,
             "A brief history of humankind."),
        ]
        db.executemany("INSERT INTO books (title,author,isbn,category_id,price,stock,description)"
                       " VALUES (?,?,?,?,?,?,?)", books)
    db.commit()
    db.close()


# ------------------------------------------------------------------- helpers
def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()


def login_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        if current_user() is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*a, **kw)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*a, **kw):
        user = current_user()
        if user is None:
            return redirect(url_for("login", next=request.path))
        if user["role"] != "admin":
            abort(403)
        return view(*a, **kw)
    return wrapped


@app.before_request
def csrf_protect():
    if request.method == "POST":
        token = session.get("_csrf")
        if not token or token != request.form.get("_csrf"):
            abort(400, "Invalid or missing CSRF token.")


@app.context_processor
def inject_globals():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    cart = session.get("cart", {})
    return {"csrf_token": session["_csrf"], "me": current_user(),
            "cart_count": sum(cart.values())}


def cart_details():
    """Return (list of cart lines, total) from the session cart."""
    cart = session.get("cart", {})
    lines, total = [], 0.0
    db = get_db()
    for bid, qty in cart.items():
        b = db.execute("SELECT * FROM books WHERE id=?", (int(bid),)).fetchone()
        if b:
            sub = b["price"] * qty
            total += sub
            lines.append({"book": b, "qty": qty, "subtotal": sub})
    return lines, total


# --------------------------------------------------------------- public pages
@app.route("/")
def index():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", type=int)
    sql = ("SELECT b.*, c.name AS category FROM books b "
           "LEFT JOIN categories c ON c.id=b.category_id WHERE 1=1")
    params = []
    if q:
        sql += " AND (b.title LIKE ? OR b.author LIKE ? OR b.isbn LIKE ?)"
        params += [f"%{q}%"] * 3
    if cat:
        sql += " AND b.category_id=?"
        params.append(cat)
    sql += " ORDER BY b.title"
    db = get_db()
    books = db.execute(sql, params).fetchall()
    cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    return render_template("index.html", books=books, categories=cats, q=q, cat=cat)


@app.route("/book/<int:book_id>")
def book_detail(book_id):
    b = get_db().execute("SELECT b.*, c.name AS category FROM books b "
                         "LEFT JOIN categories c ON c.id=b.category_id WHERE b.id=?",
                         (book_id,)).fetchone()
    if b is None:
        abort(404)
    return render_template("book.html", book=b)


# -------------------------------------------------------------- authentication
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pw = request.form["password"]
        if not name or "@" not in email or len(pw) < 6:
            flash("Enter a name, a valid email and a password of at least 6 characters.", "danger")
        else:
            try:
                db = get_db()
                db.execute("INSERT INTO users (name,email,password_hash) VALUES (?,?,?)",
                           (name, email, generate_password_hash(pw)))
                db.commit()
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That email is already registered.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form["password"]):
            cart = session.get("cart", {})
            session.clear()
            session["user_id"] = user["id"]
            session["cart"] = cart
            flash(f"Welcome, {user['name']}!", "success")
            nxt = request.args.get("next", "")
            if nxt.startswith("/") and not nxt.startswith("//"):
                return redirect(nxt)
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "index"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ------------------------------------------------------------------------ cart
@app.route("/cart")
def cart():
    lines, total = cart_details()
    return render_template("cart.html", lines=lines, total=total)


@app.route("/cart/add/<int:book_id>", methods=["POST"])
def cart_add(book_id):
    b = get_db().execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if b is None:
        abort(404)
    qty = max(1, request.form.get("qty", 1, type=int))
    cart = session.get("cart", {})
    new_qty = cart.get(str(book_id), 0) + qty
    if new_qty > b["stock"]:
        flash(f"Only {b['stock']} copies of '{b['title']}' in stock.", "warning")
    else:
        cart[str(book_id)] = new_qty
        session["cart"] = cart
        flash(f"Added '{b['title']}' to your cart.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cart/update/<int:book_id>", methods=["POST"])
def cart_update(book_id):
    qty = request.form.get("qty", 0, type=int)
    cart = session.get("cart", {})
    b = get_db().execute("SELECT stock FROM books WHERE id=?", (book_id,)).fetchone()
    if qty <= 0 or b is None:
        cart.pop(str(book_id), None)
    elif qty > b["stock"]:
        flash(f"Only {b['stock']} copies available.", "warning")
    else:
        cart[str(book_id)] = qty
    session["cart"] = cart
    return redirect(url_for("cart"))


# -------------------------------------------------------------------- checkout
@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    lines, total = cart_details()
    if not lines:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("index"))
    if request.method == "POST":
        address = request.form["address"].strip()
        method = request.form.get("payment_method", "")
        if len(address) < 10 or method not in ("Cash on Delivery", "UPI", "Card"):
            flash("Enter a full delivery address and choose a payment method.", "danger")
            return render_template("checkout.html", lines=lines, total=total)
        db = get_db()
        try:
            db.execute("BEGIN IMMEDIATE")           # one transaction for the whole order
            for ln in lines:                        # re-check stock inside the transaction
                row = db.execute("SELECT stock,title FROM books WHERE id=?",
                                 (ln["book"]["id"],)).fetchone()
                if row is None or row["stock"] < ln["qty"]:
                    raise ValueError(f"Not enough stock for '{ln['book']['title']}'.")
            order_no = "BK" + datetime.now().strftime("%y%m%d") + secrets.token_hex(3).upper()
            cur = db.execute("INSERT INTO orders (user_id,order_no,total,payment_method,address)"
                             " VALUES (?,?,?,?,?)",
                             (session["user_id"], order_no, total, method, address))
            for ln in lines:
                db.execute("INSERT INTO order_items (order_id,book_id,quantity,price)"
                           " VALUES (?,?,?,?)",
                           (cur.lastrowid, ln["book"]["id"], ln["qty"], ln["book"]["price"]))
                db.execute("UPDATE books SET stock = stock - ? WHERE id=?",
                           (ln["qty"], ln["book"]["id"]))
            db.commit()
        except ValueError as e:
            db.rollback()
            flash(str(e), "danger")
            return redirect(url_for("cart"))
        except Exception:
            db.rollback()
            raise
        session["cart"] = {}
        flash(f"Order {order_no} placed successfully!", "success")
        return redirect(url_for("order_detail", order_id=cur.lastrowid))
    return render_template("checkout.html", lines=lines, total=total)


# ---------------------------------------------------------------------- orders
@app.route("/orders")
@login_required
def orders():
    rows = get_db().execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
                            (session["user_id"],)).fetchall()
    return render_template("orders.html", orders=rows)


@app.route("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    db = get_db()
    o = db.execute("SELECT o.*, u.name AS customer FROM orders o JOIN users u ON u.id=o.user_id"
                   " WHERE o.id=?", (order_id,)).fetchone()
    if o is None or (o["user_id"] != session["user_id"] and current_user()["role"] != "admin"):
        abort(404)
    items = db.execute("SELECT i.*, b.title FROM order_items i JOIN books b ON b.id=i.book_id"
                       " WHERE i.order_id=?", (order_id,)).fetchall()
    return render_template("order_detail.html", order=o, items=items)


@app.route("/orders/<int:order_id>/cancel", methods=["POST"])
@login_required
def order_cancel(order_id):
    db = get_db()
    o = db.execute("SELECT * FROM orders WHERE id=? AND user_id=?",
                   (order_id, session["user_id"])).fetchone()
    if o is None:
        abort(404)
    if o["status"] != "Placed":
        flash("Only orders in 'Placed' status can be cancelled.", "warning")
    else:
        cancel_order(db, order_id)
        flash("Order cancelled and stock restored.", "info")
    return redirect(url_for("order_detail", order_id=order_id))


def cancel_order(db, order_id):
    try:
        db.execute("BEGIN IMMEDIATE")
        for it in db.execute("SELECT * FROM order_items WHERE order_id=?", (order_id,)).fetchall():
            db.execute("UPDATE books SET stock = stock + ? WHERE id=?",
                       (it["quantity"], it["book_id"]))
        db.execute("UPDATE orders SET status='Cancelled' WHERE id=?", (order_id,))
        db.commit()
    except Exception:
        db.rollback()
        raise


# ----------------------------------------------------------------------- admin
@app.route("/admin")
@admin_required
def admin_dashboard():
    db = get_db()
    stats = {
        "books": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "customers": db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
        "orders": db.execute("SELECT COUNT(*) FROM orders").fetchone()[0],
        "revenue": db.execute("SELECT COALESCE(SUM(total),0) FROM orders"
                              " WHERE status!='Cancelled'").fetchone()[0],
    }
    low = db.execute("SELECT * FROM books WHERE stock <= 5 ORDER BY stock").fetchall()
    return render_template("admin_dashboard.html", stats=stats, low=low)


@app.route("/admin/books")
@admin_required
def admin_books():
    rows = get_db().execute("SELECT b.*, c.name AS category FROM books b "
                            "LEFT JOIN categories c ON c.id=b.category_id ORDER BY b.id DESC"
                            ).fetchall()
    return render_template("admin_books.html", books=rows)


def read_book_form():
    f = request.form
    try:
        data = {
            "title": f["title"].strip(), "author": f["author"].strip(),
            "isbn": f.get("isbn", "").strip() or None,
            "category_id": f.get("category_id", type=int),
            "price": float(f["price"]), "stock": int(f["stock"]),
            "description": f.get("description", "").strip(),
        }
    except (KeyError, ValueError):
        return None
    if not data["title"] or not data["author"] or data["price"] < 0 or data["stock"] < 0:
        return None
    return data


@app.route("/admin/books/new", methods=["GET", "POST"])
@admin_required
def book_new():
    db = get_db()
    cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        data = read_book_form()
        if data is None:
            flash("Please fill all fields with valid values.", "danger")
        else:
            try:
                db.execute("INSERT INTO books (title,author,isbn,category_id,price,stock,description)"
                           " VALUES (:title,:author,:isbn,:category_id,:price,:stock,:description)", data)
                db.commit()
                flash("Book added.", "success")
                return redirect(url_for("admin_books"))
            except sqlite3.IntegrityError:
                flash("A book with that ISBN already exists.", "danger")
    return render_template("book_form.html", book=None, categories=cats)


@app.route("/admin/books/<int:book_id>/edit", methods=["GET", "POST"])
@admin_required
def book_edit(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if book is None:
        abort(404)
    cats = db.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        data = read_book_form()
        if data is None:
            flash("Please fill all fields with valid values.", "danger")
        else:
            data["id"] = book_id
            try:
                db.execute("UPDATE books SET title=:title, author=:author, isbn=:isbn,"
                           " category_id=:category_id, price=:price, stock=:stock,"
                           " description=:description WHERE id=:id", data)
                db.commit()
                flash("Book updated.", "success")
                return redirect(url_for("admin_books"))
            except sqlite3.IntegrityError:
                flash("A book with that ISBN already exists.", "danger")
    return render_template("book_form.html", book=book, categories=cats)


@app.route("/admin/books/<int:book_id>/delete", methods=["POST"])
@admin_required
def book_delete(book_id):
    db = get_db()
    try:
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        flash("Book deleted.", "info")
    except sqlite3.IntegrityError:
        db.rollback()
        flash("This book appears in past orders and cannot be deleted. Set its stock to 0 instead.",
              "warning")
    return redirect(url_for("admin_books"))


@app.route("/admin/categories", methods=["GET", "POST"])
@admin_required
def admin_categories():
    db = get_db()
    if request.method == "POST":
        name = request.form["name"].strip()
        if name:
            try:
                db.execute("INSERT INTO categories (name) VALUES (?)", (name,))
                db.commit()
                flash("Category added.", "success")
            except sqlite3.IntegrityError:
                flash("Category already exists.", "danger")
        return redirect(url_for("admin_categories"))
    cats = db.execute("SELECT c.*, (SELECT COUNT(*) FROM books WHERE category_id=c.id) AS n"
                      " FROM categories c ORDER BY name").fetchall()
    return render_template("admin_categories.html", categories=cats)


@app.route("/admin/orders")
@admin_required
def admin_orders():
    rows = get_db().execute("SELECT o.*, u.name AS customer FROM orders o"
                            " JOIN users u ON u.id=o.user_id ORDER BY o.id DESC").fetchall()
    return render_template("admin_orders.html", orders=rows)


@app.route("/admin/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id):
    status = request.form.get("status")
    db = get_db()
    o = db.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if o is None:
        abort(404)
    if status not in ("Placed", "Shipped", "Delivered", "Cancelled") or o["status"] == "Cancelled":
        flash("Invalid status change.", "danger")
    elif status == "Cancelled":
        cancel_order(db, order_id)
        flash("Order cancelled and stock restored.", "info")
    else:
        db.execute("UPDATE orders SET status=? WHERE id=?", (status, order_id))
        db.commit()
        flash("Order status updated.", "success")
    return redirect(url_for("admin_orders"))


@app.errorhandler(403)
def forbidden(_e):
    return render_template("error.html", code=403, msg="You do not have access to this page."), 403


@app.errorhandler(404)
def not_found(_e):
    return render_template("error.html", code=404, msg="Page not found."), 404


@app.errorhandler(400)
def bad_request(e):
    return render_template("error.html", code=400, msg=getattr(e, "description", "Bad request")), 400


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
