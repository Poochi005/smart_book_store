PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'customer' CHECK (role IN ('customer','admin')),
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    id   INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS books (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,
    author      TEXT NOT NULL,
    isbn        TEXT UNIQUE,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    price       REAL NOT NULL CHECK (price >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    description TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL REFERENCES users(id),
    order_no       TEXT NOT NULL UNIQUE,
    total          REAL NOT NULL,
    payment_method TEXT NOT NULL,
    address        TEXT NOT NULL,
    status         TEXT NOT NULL DEFAULT 'Placed'
                   CHECK (status IN ('Placed','Shipped','Delivered','Cancelled')),
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    book_id  INTEGER NOT NULL REFERENCES books(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price    REAL NOT NULL
);
