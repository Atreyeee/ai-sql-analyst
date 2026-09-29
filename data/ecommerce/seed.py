"""
Generates realistic synthetic e-commerce data and loads it into PostgreSQL.

This script is intentionally separate from the FastAPI app (no SQLAlchemy
here) — it's a one-time data-generation utility, not part of the running
application. We use psycopg2 directly since it's a simple, one-off bulk
insert job.
"""

import os
import random
from datetime import datetime, timedelta

import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

fake = Faker("en_IN")
random.seed(42)  # reproducible dataset

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/ai_sql_analyst",
)

N_CUSTOMERS = 500
N_PRODUCTS = 150
N_ORDERS = 4000
CATEGORIES = [
    "Electronics", "Clothing", "Home & Kitchen", "Books",
    "Sports & Fitness", "Beauty", "Toys", "Grocery",
]
INDIAN_CITIES = [
    ("Mumbai", "Maharashtra"), ("Delhi", "Delhi"), ("Bengaluru", "Karnataka"),
    ("Kolkata", "West Bengal"), ("Chennai", "Tamil Nadu"), ("Hyderabad", "Telangana"),
    ("Pune", "Maharashtra"), ("Ahmedabad", "Gujarat"), ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
]
PAYMENT_METHODS = ["card", "upi", "netbanking", "cod", "wallet"]
ORDER_STATUSES = ["delivered", "delivered", "delivered", "shipped", "pending", "cancelled", "returned"]
START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2025, 12, 31)


def random_datetime(start: datetime, end: datetime) -> datetime:
    delta = end - start
    seconds = random.randint(0, int(delta.total_seconds()))
    return start + timedelta(seconds=seconds)


def seed_customers(cur, n: int) -> list[int]:
    rows = []
    for _ in range(n):
        city, state = random.choice(INDIAN_CITIES)
        rows.append((
            fake.first_name(),
            fake.last_name(),
            fake.unique.email(),
            city,
            state,
            "India",
            random_datetime(START_DATE, END_DATE).date(),
        ))
    execute_values(
        cur,
        """INSERT INTO customers (first_name, last_name, email, city, state, country, signup_date)
           VALUES %s RETURNING customer_id""",
        rows,
    )
    return [r[0] for r in cur.fetchall()]


def seed_categories(cur) -> dict[str, int]:
    rows = [(name,) for name in CATEGORIES]
    execute_values(
        cur,
        "INSERT INTO categories (category_name) VALUES %s RETURNING category_id, category_name",
        rows,
    )
    return {name: cid for cid, name in cur.fetchall()}


def seed_products(cur, n: int, category_ids: list[int]) -> list[tuple[int, float]]:
    rows = []
    for _ in range(n):
        price = round(random.uniform(199, 49999), 2)
        rows.append((
            fake.catch_phrase(),
            random.choice(category_ids),
            price,
            True,
        ))
    execute_values(
        cur,
        """INSERT INTO products (product_name, category_id, unit_price, is_active)
           VALUES %s RETURNING product_id, unit_price""",
        rows,
    )
    return cur.fetchall()


def seed_orders_items_payments(cur, customer_ids: list[int], products: list[tuple[int, float]], n_orders: int):
    order_rows = []
    for _ in range(n_orders):
        order_rows.append((
            random.choice(customer_ids),
            random_datetime(START_DATE, END_DATE),
            random.choice(ORDER_STATUSES),
        ))
    execute_values(
        cur,
        "INSERT INTO orders (customer_id, order_date, status) VALUES %s RETURNING order_id, order_date, status",
        order_rows,
    )
    orders = cur.fetchall()  # (order_id, order_date, status)

    item_rows = []
    payment_rows = []
    for order_id, order_date, status in orders:
        n_items = random.randint(1, 5)
        chosen_products = random.sample(products, min(n_items, len(products)))
        order_total = 0.0
        for product_id, unit_price in chosen_products:
            qty = random.randint(1, 4)
            discount = random.choice([0, 0, 0, 0.05, 0.10, 0.15])
            item_rows.append((order_id, product_id, qty, unit_price, discount))
            order_total += qty * float(unit_price) * (1 - discount)

        if status == "cancelled":
            payment_status = "refunded"
        elif status == "pending":
            payment_status = random.choice(["pending", "success"])
        else:
            payment_status = random.choices(["success", "failed"], weights=[0.92, 0.08])[0]

        payment_rows.append((
            order_id,
            order_date + timedelta(minutes=random.randint(1, 120)),
            round(order_total, 2),
            random.choice(PAYMENT_METHODS),
            payment_status,
        ))

    execute_values(
        cur,
        """INSERT INTO order_items (order_id, product_id, quantity, unit_price, discount_pct)
           VALUES %s""",
        item_rows,
    )
    execute_values(
        cur,
        """INSERT INTO payments (order_id, payment_date, amount, payment_method, payment_status)
           VALUES %s""",
        payment_rows,
    )


def main():
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        print("Seeding categories...")
        category_map = seed_categories(cur)

        print("Seeding customers...")
        customer_ids = seed_customers(cur, N_CUSTOMERS)

        print("Seeding products...")
        products = seed_products(cur, N_PRODUCTS, list(category_map.values()))

        print("Seeding orders, order_items, payments...")
        seed_orders_items_payments(cur, customer_ids, products, N_ORDERS)

        conn.commit()
        print("Done. Data committed.")
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()