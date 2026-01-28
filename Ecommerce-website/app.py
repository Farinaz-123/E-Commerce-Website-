from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "ecommerce_secret_key"

# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            description TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------- USER REGISTER ----------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (request.form["username"], request.form["password"])
        )
        conn.commit()
        conn.close()
        return redirect("/login")
    return render_template("register.html")

# ---------- USER LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (request.form["username"], request.form["password"])
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            return redirect("/products")
        return "Invalid credentials"
    return render_template("login.html")

# ---------- PRODUCTS ----------
@app.route("/products")
def products():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("products.html", products=products)

# ---------- SEARCH ----------
@app.route("/search")
def search():
    if "user_id" not in session:
        return redirect("/login")

    q = request.args.get("q")
    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products WHERE name LIKE ?",
        ('%' + q + '%',)
    ).fetchall()
    conn.close()
    return render_template("products.html", products=products)

# ---------- ADD TO CART ----------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    conn = get_db()
    conn.execute(
        "INSERT INTO cart (user_id, product_id) VALUES (?, ?)",
        (session["user_id"], product_id)
    )
    conn.commit()
    conn.close()
    return redirect("/products")

# ---------- VIEW CART ----------
@app.route("/cart")
def cart():
    conn = get_db()
    items = conn.execute("""
        SELECT cart.id, products.name, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=?
    """, (session["user_id"],)).fetchall()

    total = sum(item["price"] for item in items)
    conn.close()
    return render_template("cart.html", items=items, total=total)

# ---------- REMOVE FROM CART ----------
@app.route("/remove/<int:id>")
def remove(id):
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/cart")

# ---------- ADMIN LOGIN ----------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == "farinaz" and request.form["password"] == "farinaz@123":
            session["admin"] = True
            return redirect("/admin/dashboard")
        return "Invalid admin credentials"
    return render_template("admin_login.html")

# ---------- ADMIN DASHBOARD ----------
@app.route("/admin/dashboard")
def admin_dashboard():
    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", products=products)

# ---------- ADD PRODUCT ----------
@app.route("/admin/add", methods=["GET", "POST"])
def add_product():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO products (name, price, description) VALUES (?, ?, ?)",
            (request.form["name"], request.form["price"], request.form["description"])
        )
        conn.commit()
        conn.close()
        return redirect("/admin/dashboard")
    return render_template("add_product.html")

# ---------- DELETE PRODUCT ----------
@app.route("/admin/delete/<int:id>")
def delete_product(id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/dashboard")

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True)
