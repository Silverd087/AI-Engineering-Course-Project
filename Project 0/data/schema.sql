-- Online bookstore schema
-- 5 tables chosen to allow joins, aggregation, filtering, and subquery questions.

CREATE TABLE authors (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    country  TEXT NOT NULL
);

CREATE TABLE books (
    id              INTEGER PRIMARY KEY,
    title           TEXT NOT NULL,
    author_id       INTEGER NOT NULL REFERENCES authors(id),
    genre           TEXT NOT NULL,
    price           REAL NOT NULL,
    published_year  INTEGER NOT NULL,
    stock           INTEGER NOT NULL
);

CREATE TABLE customers (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT NOT NULL,
    country      TEXT NOT NULL,
    signup_date  TEXT NOT NULL  -- ISO date 'YYYY-MM-DD'
);

CREATE TABLE orders (
    id            INTEGER PRIMARY KEY,
    customer_id   INTEGER NOT NULL REFERENCES customers(id),
    order_date    TEXT NOT NULL,  -- ISO date
    status        TEXT NOT NULL   -- 'placed' | 'shipped' | 'cancelled'
);

CREATE TABLE order_items (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id),
    book_id     INTEGER NOT NULL REFERENCES books(id),
    quantity    INTEGER NOT NULL,
    unit_price  REAL NOT NULL
);
