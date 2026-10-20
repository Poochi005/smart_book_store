# Smart Book Store Management System

A full stack web application built with **HTML, CSS, JavaScript, Python (Flask) and SQLite**.

## Features
- **Customer:** register / login, search and filter books, cart, checkout (simulated payment),
  order history, cancel an order (stock is restored automatically)
- **Admin:** dashboard (counts, revenue, low-stock list), add / edit / delete books,
  manage categories, view all orders and update their status
- Passwords stored hashed (Werkzeug), CSRF protection on every POST form,
  orders placed inside a single database transaction (no overselling)

## Run it
```bash
python -m venv venv
venv\Scripts\activate          # Windows   (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000 . The database (`bookstore.db`) and sample data are created
automatically on first run.

**Admin login:** `admin@bookstore.com` / `admin123` (change it after first login in real use)

## Structure
```
app.py            routes, business logic, database helpers
schema.sql        5 tables: users, categories, books, orders, order_items
templates/        Jinja2 HTML pages
static/css|js     styling and client-side validation
```
