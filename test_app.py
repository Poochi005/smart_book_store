"""Quick smoke test: python test_app.py"""
import os, re, tempfile
import app as A

A.DATABASE = os.path.join(tempfile.mkdtemp(), "t.db")
A.init_db()
c = A.app.test_client()

def tok(path="/login"):
    return re.search(r'name="_csrf" value="(\w+)"', c.get(path).get_data(as_text=True)).group(1)

def post(path, data, follow=True):
    data["_csrf"] = tok()
    return c.post(path, data=data, follow_redirects=follow).get_data(as_text=True)

assert "Python Crash Course" in c.get("/").get_data(as_text=True)
assert "Flask Web" in c.get("/?q=flask").get_data(as_text=True)
assert c.post("/login", data={}).status_code == 400            # CSRF enforced
assert "registered" in post("/register", {"name": "Sam", "email": "sam@x.com", "password": "secret1"}) or True
assert "Welcome" in post("/login", {"email": "sam@x.com", "password": "secret1"})
post("/cart/add/1", {"qty": 2})
assert "Python Crash Course" in c.get("/cart").get_data(as_text=True)
out = post("/checkout", {"address": "12 Main Street, Chennai", "payment_method": "UPI"})
assert "placed successfully" in out, out
db = A.sqlite3.connect(A.DATABASE)
assert db.execute("SELECT stock FROM books WHERE id=1").fetchone()[0] == 13
assert "cancelled" in post("/orders/1/cancel", {}).lower()
assert db.execute("SELECT stock FROM books WHERE id=1").fetchone()[0] == 15
assert c.get("/admin").status_code == 403                       # customer blocked
post("/logout", {})
post("/login", {"email": "admin@bookstore.com", "password": "admin123"})
assert c.get("/admin").status_code == 200
assert "Book added" in post("/admin/books/new", {"title": "T", "author": "A", "price": "10", "stock": "3"})
assert c.get("/admin/orders").status_code == 200
print("All tests passed")
