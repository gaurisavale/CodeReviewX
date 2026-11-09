"""Demo inputs. `orders` is a multi-function file that lights up the heat map."""

HEALTH_SAMPLE = '''def health_analysis(a, w, h, hr, bp, sleep, water, exercise):
    bmi = w / (h * h)
    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25:
        category = "Normal"
    elif bmi < 30:
        category = "Overweight"
    else:
        category = "Obese"
    print("BMI:", bmi)
    print(category)
    if hr > 100:
        print("High heart rate")
    elif hr < 60:
        print("Low heart rate")
    if bp > 140:
        print("High BP")
    if sleep < 6:
        print("Sleep more")
    if water < 2:
        print("Drink water")
    if exercise < 30:
        print("Exercise more")
    if age > 50:
        print("Older")
    return category
'''

ORDERS_SAMPLE = '''import json
import sqlite3

DB_PATH = "orders.db"


def process_order(o, u, p, c, s, d, t, n):
    if o is not None:
        if u is not None:
            if len(o["items"]) > 0:
                total = calculate_total(o["items"], d)
                if total > 5000:
                    print("Large order, manual review")
                    total = total * 0.97
                elif total > 1000:
                    print("Bulk order")
                    total = total * 0.98
                if validate_payment(p, c, total):
                    if reserve_stock(o["items"]):
                        save_order(o, u, total)
                        send_confirmation(u, total, n)
                        print("Order done", total)
                        return total
                    else:
                        print("No stock")
                else:
                    print("Payment failed")
    return None


def calculate_total(items, d):
    t = 0
    for it in items:
        t = t + it["price"] * it["qty"]
    if d == "SAVE10":
        t = t - t * 0.10
    elif d == "SAVE20":
        t = t - t * 0.20
    elif d == "SAVE30":
        t = t - t * 0.30
    elif d == "VIP":
        t = t - t * 0.40
    t = t + t * tax_rate
    return t


def apply_percent_discount(amount, percent):
    """Return amount reduced by percent (0-100)."""
    if not 0 <= percent <= 100:
        raise ValueError("percent must be between 0 and 100")
    return amount - amount * percent / 100


def validate_payment(p, c, total):
    if p == "card":
        if c is not None:
            if len(c) == 16:
                if total < 10000:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    elif p == "upi":
        return total < 50000
    return False


def reserve_stock(items):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for it in items:
        cur.execute("UPDATE stock SET qty = qty - " + str(it["qty"]) + " WHERE id = " + str(it["id"]))
    conn.commit()
    return True


def save_order(o, u, total):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(f"INSERT INTO orders VALUES ('{u}', {total}, '{json.dumps(o)}')")
    conn.commit()
    print("saved")


def send_confirmation(u, total, n):
    api_key = "sk-live-4f9a8b7c6d5e"
    msg = f"Hi {u}, your order of {total} is confirmed"
    print("sending to", n, msg, api_key)
    return True


def apply_bulk_pricing_rules(items, rule):
    out = []
    for it in items:
        price = it["price"]
        price = price * eval(rule)
        out.append(price)
    return out


def refund_order(order_id, amount, reason):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT total FROM orders WHERE id = ?", (order_id,))
    row = cur.fetchone()
    if row[0] < amount:
        raise ValueError("refund exceeds order total")
    cur.execute("UPDATE orders SET refunded = ? WHERE id = ?", (amount, order_id))
    conn.commit()
    conn.close()
    return amount


def get_order_summary(order):
    """One-line summary of an order, safe for logs."""
    count = len(order.get("items", []))
    return f"{order.get('id', '?')}: {count} item(s)"


def cleanup_expired_carts(carts, now):
    removed = 0
    for cart in carts:
        if cart["expires"] < now:
            try:
                carts.remove(cart)
                removed += 1
            except Exception:
                pass
    return removed
'''

SAMPLES = {"orders": ("orders.py", ORDERS_SAMPLE), "health": ("health_analysis.py", HEALTH_SAMPLE)}
DEMO_CODE = ORDERS_SAMPLE
DEMO_FILENAME = "orders.py"
