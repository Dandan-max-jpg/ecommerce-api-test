# app.py - 电商交易系统（被测系统 / 靶子）
#
# 用途：作为接口自动化测试的"靶子"。本系统故意保留若干缺陷，
#       供你用等价类 / 边界值方法设计用例、跑 pytest 把它们挖出来。
#
# 运行：
#   1) pip install flask
#   2) python seed_admin.py      # 生成 admin/admin123 管理员账号（测管理员接口用）
#   3) python app.py             # 启动后监听 http://127.0.0.1:5000
#
# 数据：本地 SQLite 文件 ecommerce.db（每次启动自动建表）

import sqlite3
import hashlib
import hmac
import base64
import json
import time
import os
from flask import Flask, request

app = Flask(__name__)
app.config["SECRET_KEY"] = "ecommerce-demo-secret-key-change-me"
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ecommerce.db")


# ---------- 极简 token（HMAC 签名，零额外依赖） ----------
def sign_token(payload):
    payload = dict(payload)
    payload["exp"] = int(time.time()) + 3600
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()
    sig = hmac.new(app.config["SECRET_KEY"].encode(),
                   body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def verify_token(token):
    try:
        body, sig = token.split(".")
        expect = hmac.new(app.config["SECRET_KEY"].encode(),
                          body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expect, sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


def get_current_user():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return verify_token(auth[7:])
    return None


def pw_hash(pw, salt=None):
    if salt is None:
        salt = os.urandom(8).hex()
    return salt + ":" + hashlib.sha256((salt + pw).encode()).hexdigest()


def pw_check(pw, stored):
    salt, h = stored.split(":", 1)
    return pw_hash(pw, salt).split(":", 1)[1] == h


# ---------- DB ----------
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT DEFAULT 'user'
    );
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price REAL,
        stock INTEGER,
        category TEXT
    );
    CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        total REAL,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        price REAL
    );
    """)
    conn.commit()
    conn.close()


# ---------- 用户 ----------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    # BUG-1: 未校验 username 非空、password 长度(应>=6)。空用户名/超短密码也能注册成功(200)。
    conn = db()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password, role) VALUES (?,?,?)",
                  (username, pw_hash(password), "user"))
        conn.commit()
        uid = c.lastrowid
    except Exception as e:
        conn.close()
        return jsonify_err(str(e)), 400
    conn.close()
    return jsonify_ok({"id": uid, "username": username})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username")
    password = data.get("password")
    conn = db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if not row or not pw_check(password, row["password"]):
        return jsonify_err("invalid credentials"), 401
    token = sign_token({"user_id": row["id"],
                        "username": row["username"],
                        "role": row["role"]})
    return jsonify_ok({"token": token})


# ---------- 商品 ----------
@app.route("/api/products", methods=["GET"])
def list_products():
    page = request.args.get("page", 1, type=int)
    size = request.args.get("size", 10, type=int)
    # BUG-2: 未校验 page/size 为负数或越界。负数 page -> OFFSET 为负被静默当 0；负数 size -> LIMIT 为负返回全部。
    conn = db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM products LIMIT ? OFFSET ?",
                     (size, (page - 1) * size)).fetchall()
    conn.close()
    return jsonify_ok([dict(r) for r in rows])


@app.route("/api/products", methods=["POST"])
def create_product():
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    # BUG-3: 未校验角色为 admin。任意登录用户都能创建商品(权限漏洞)。
    data = request.get_json(force=True, silent=True) or {}
    name = data.get("name")
    price = float(data.get("price"))      # BUG-4: 无 try/except，price 传字符串/缺失 -> 500
    stock = int(data.get("stock"))        # BUG-4b: stock 传字符串 -> 500
    category = data.get("category", "")
    # BUG-5: 未校验 price<0 / stock<0 (应 400)。负数价格/库存被接受。
    conn = db()
    c = conn.cursor()
    c.execute("INSERT INTO products (name, price, stock, category) VALUES (?,?,?,?)",
              (name, price, stock, category))
    conn.commit()
    pid = c.lastrowid
    conn.close()
    return jsonify_ok({"id": pid, "name": name, "price": price, "stock": stock})


@app.route("/api/products/<int:pid>", methods=["GET"])
def get_product(pid):
    conn = db()
    c = conn.cursor()
    row = c.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify_err("not found"), 404
    return jsonify_ok(dict(row))


@app.route("/api/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    u = get_current_user()
    if not u or u.get("role") != "admin":
        return jsonify_err("forbidden"), 403
    data = request.get_json(force=True, silent=True) or {}
    conn = db()
    c = conn.cursor()
    if "price" in data:
        c.execute("UPDATE products SET price=? WHERE id=?", (float(data["price"]), pid))
    if "stock" in data:
        c.execute("UPDATE products SET stock=? WHERE id=?", (int(data["stock"]), pid))
    if "name" in data:
        c.execute("UPDATE products SET name=? WHERE id=?", (data["name"], pid))
    conn.commit()
    conn.close()
    return jsonify_ok({"id": pid, "updated": True})


# ---------- 购物车 ----------
@app.route("/api/cart/items", methods=["POST"])
def add_cart():
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    data = request.get_json(force=True, silent=True) or {}
    product_id = int(data.get("product_id"))   # BUG-6: 传字符串 -> 500
    quantity = data.get("quantity", 1)
    # BUG-7: 未校验 quantity<=0 (应 400)。
    conn = db()
    c = conn.cursor()
    existing = c.execute("SELECT * FROM cart WHERE user_id=? AND product_id=?",
                         (u["user_id"], product_id)).fetchone()
    if existing:
        c.execute("UPDATE cart SET quantity=quantity+? WHERE id=?",
                  (quantity, existing["id"]))
    else:
        c.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (?,?,?)",
                  (u["user_id"], product_id, quantity))
    conn.commit()
    conn.close()
    return jsonify_ok({"ok": True})


@app.route("/api/cart", methods=["GET"])
def view_cart():
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    rows = c.execute(
        """SELECT cart.id, cart.product_id, cart.quantity,
                  products.name, products.price
           FROM cart JOIN products ON cart.product_id=products.id
           WHERE cart.user_id=?""", (u["user_id"],)).fetchall()
    conn.close()
    return jsonify_ok([dict(r) for r in rows])


@app.route("/api/cart/items/<int:item_id>", methods=["DELETE"])
def del_cart(item_id):
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    # BUG-8: 未校验 item 是否存在、是否归属当前用户。删不存在的/别人的 -> 仍返回 200(应 404)。
    c.execute("DELETE FROM cart WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify_ok({"ok": True})


# ---------- 订单 ----------
@app.route("/api/orders", methods=["POST"])
def create_order():
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    cart_rows = c.execute("SELECT * FROM cart WHERE user_id=?",
                          (u["user_id"],)).fetchall()
    if not cart_rows:
        conn.close()
        return jsonify_err("empty cart"), 400
    total = 0.0
    order_items = []
    for item in cart_rows:
        p = c.execute("SELECT * FROM products WHERE id=?",
                      (item["product_id"],)).fetchone()
        # BUG-9: 未校验库存是否充足 -> 超卖(应 400 库存不足)。
        # BUG-10: 浮点累加精度(0.1+0.2 类问题)。
        total += p["price"] * item["quantity"]
        order_items.append((p["id"], item["quantity"], p["price"]))
    c.execute("INSERT INTO orders (user_id, total, status, created_at) VALUES (?,?,?,?)",
              (u["user_id"], round(total, 2), "pending",
               time.strftime("%Y-%m-%d %H:%M:%S")))
    oid = c.lastrowid
    for pid, qty, price in order_items:
        c.execute("INSERT INTO order_items (order_id, product_id, quantity, price) VALUES (?,?,?,?)",
                  (oid, pid, qty, price))
        c.execute("UPDATE products SET stock=stock-? WHERE id=?", (qty, pid))
    c.execute("DELETE FROM cart WHERE user_id=?", (u["user_id"],))
    conn.commit()
    conn.close()
    return jsonify_ok({"order_id": oid, "total": round(total, 2), "status": "pending"})


@app.route("/api/orders", methods=["GET"])
def list_orders():
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    rows = c.execute("SELECT * FROM orders WHERE user_id=?",
                     (u["user_id"],)).fetchall()
    conn.close()
    return jsonify_ok([dict(r) for r in rows])


@app.route("/api/orders/<int:oid>", methods=["GET"])
def order_detail(oid):
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=? AND user_id=?",
                  (oid, u["user_id"])).fetchone()
    if not o:
        conn.close()
        return jsonify_err("not found"), 404
    items = c.execute("SELECT * FROM order_items WHERE order_id=?",
                      (oid,)).fetchall()
    conn.close()
    return jsonify_ok({"order": dict(o), "items": [dict(i) for i in items]})


@app.route("/api/orders/<int:oid>/pay", methods=["POST"])
def pay_order(oid):
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    data = request.get_json(force=True, silent=True) or {}
    amount = float(data.get("amount", 0))   # BUG-11: 负数/0 未校验 -> 支付成功(应 400)
    conn = db()
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=? AND user_id=?",
                  (oid, u["user_id"])).fetchone()
    if not o:
        conn.close()
        return jsonify_err("not found"), 404
    # BUG-12: 未校验订单状态(已取消/已完成也能支付)；也未校验 amount 与 total 一致。
    c.execute("UPDATE orders SET status='paid' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify_ok({"order_id": oid, "status": "paid", "paid": amount})


@app.route("/api/orders/<int:oid>/cancel", methods=["POST"])
def cancel_order(oid):
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=? AND user_id=?",
                  (oid, u["user_id"])).fetchone()
    if not o:
        conn.close()
        return jsonify_err("not found"), 404
    # BUG-13: 已支付/已发货订单也能取消(应仅 pending 可取消)。
    c.execute("UPDATE orders SET status='cancelled' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify_ok({"order_id": oid, "status": "cancelled"})


@app.route("/api/orders/<int:oid>/ship", methods=["POST"])
def ship_order(oid):
    u = get_current_user()
    if not u or u.get("role") != "admin":
        return jsonify_err("forbidden"), 403
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE orders SET status='shipped' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify_ok({"order_id": oid, "status": "shipped"})


@app.route("/api/orders/<int:oid>/confirm", methods=["POST"])
def confirm_order(oid):
    u = get_current_user()
    if not u:
        return jsonify_err("unauthorized"), 401
    conn = db()
    c = conn.cursor()
    o = c.execute("SELECT * FROM orders WHERE id=? AND user_id=?",
                  (oid, u["user_id"])).fetchone()
    if not o:
        conn.close()
        return jsonify_err("not found"), 404
    # BUG-14: 未校验当前状态必须是 shipped 才能确认(已取消也能确认 -> 状态机漏洞)。
    c.execute("UPDATE orders SET status='completed' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    return jsonify_ok({"order_id": oid, "status": "completed"})


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify_ok({"status": "ok"})


# ---------- 自动化测试专用：重置数据 ----------
@app.route("/api/reset", methods=["POST"])
def reset_db():
    # 每次测试前调一次即可把库清空到干净可重复状态：
    # 1) 删掉全部业务数据  2) 自增 id 归零（DELETE FROM sqlite_sequence）
    # 3) 重新塞回 admin/admin123 管理员账号，保证需要 admin 的用例每次都能跑通
    conn = db()
    c = conn.cursor()
    c.executescript("""
    DELETE FROM order_items;
    DELETE FROM orders;
    DELETE FROM cart;
    DELETE FROM products;
    DELETE FROM users;
    DELETE FROM sqlite_sequence;
    """)
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?,?,?)",
        ("admin", pw_hash("admin123"), "admin"),
    )
    # 同时重建 testuser/test123 普通用户，保证订单模块"普通用户登录"类前置条件可复现
    c.execute(
        "INSERT INTO users (username, password, role) VALUES (?,?,?)",
        ("testuser", pw_hash("test123"), "user"),
    )
    conn.commit()
    conn.close()
    return jsonify_ok({"reset": True})


# ---------- 统一响应 ----------
def jsonify_ok(data):
    return app.response_class(json.dumps({"code": 0, "data": data}, ensure_ascii=False),
                              mimetype="application/json")


def jsonify_err(msg, code=1):
    return app.response_class(json.dumps({"code": code, "msg": msg}, ensure_ascii=False),
                              mimetype="application/json")


if __name__ == "__main__":
    init_db()
    app.run(host="127.0.0.1", port=5000, debug=True)
