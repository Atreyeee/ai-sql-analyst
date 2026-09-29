-- ============================================================
-- AI SQL Analyst — E-commerce schema
-- ============================================================

DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS categories CASCADE;
DROP TABLE IF EXISTS customers CASCADE;

-- ------------------------------------------------------------
-- customers
-- ------------------------------------------------------------
CREATE TABLE customers (
    customer_id     SERIAL PRIMARY KEY,
    first_name      VARCHAR(50)  NOT NULL,
    last_name       VARCHAR(50)  NOT NULL,
    email           VARCHAR(120) NOT NULL UNIQUE,
    city            VARCHAR(60)  NOT NULL,
    state           VARCHAR(60)  NOT NULL,
    country         VARCHAR(60)  NOT NULL DEFAULT 'India',
    signup_date     DATE         NOT NULL
);

-- ------------------------------------------------------------
-- categories
-- ------------------------------------------------------------
CREATE TABLE categories (
    category_id     SERIAL PRIMARY KEY,
    category_name   VARCHAR(60) NOT NULL UNIQUE
);

-- ------------------------------------------------------------
-- products
-- ------------------------------------------------------------
CREATE TABLE products (
    product_id      SERIAL PRIMARY KEY,
    product_name    VARCHAR(120)   NOT NULL,
    category_id     INTEGER        NOT NULL REFERENCES categories(category_id),
    unit_price      NUMERIC(10,2)  NOT NULL CHECK (unit_price >= 0),
    is_active       BOOLEAN        NOT NULL DEFAULT TRUE
);

-- ------------------------------------------------------------
-- orders
-- ------------------------------------------------------------
CREATE TABLE orders (
    order_id        SERIAL PRIMARY KEY,
    customer_id     INTEGER        NOT NULL REFERENCES customers(customer_id),
    order_date      TIMESTAMP      NOT NULL,
    status          VARCHAR(20)    NOT NULL
                     CHECK (status IN ('pending','shipped','delivered','cancelled','returned'))
);

-- ------------------------------------------------------------
-- order_items  (line items within an order)
-- ------------------------------------------------------------
CREATE TABLE order_items (
    order_item_id   SERIAL PRIMARY KEY,
    order_id        INTEGER        NOT NULL REFERENCES orders(order_id),
    product_id      INTEGER        NOT NULL REFERENCES products(product_id),
    quantity        INTEGER        NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(10,2)  NOT NULL CHECK (unit_price >= 0),
    discount_pct    NUMERIC(4,2)   NOT NULL DEFAULT 0 CHECK (discount_pct BETWEEN 0 AND 1)
);

-- ------------------------------------------------------------
-- payments  (1:1 with orders)
-- ------------------------------------------------------------
CREATE TABLE payments (
    payment_id      SERIAL PRIMARY KEY,
    order_id        INTEGER        NOT NULL UNIQUE REFERENCES orders(order_id),
    payment_date    TIMESTAMP      NOT NULL,
    amount          NUMERIC(10,2)  NOT NULL CHECK (amount >= 0),
    payment_method  VARCHAR(20)    NOT NULL
                     CHECK (payment_method IN ('card','upi','netbanking','cod','wallet')),
    payment_status  VARCHAR(20)    NOT NULL
                     CHECK (payment_status IN ('success','failed','pending','refunded'))
);

-- ------------------------------------------------------------
-- Indexes (beyond the automatic ones on PRIMARY KEY)
-- ------------------------------------------------------------
CREATE INDEX idx_orders_customer_id   ON orders(customer_id);
CREATE INDEX idx_orders_order_date    ON orders(order_date);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product  ON order_items(product_id);
CREATE INDEX idx_products_category    ON products(category_id);
CREATE INDEX idx_payments_order_id    ON payments(order_id);