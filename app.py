from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
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

# ---------------- HOME ----------------
@app.route("/")
def home():
    return redirect("/login")

# ---------------- REGISTER ----------------
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

# ---------------- LOGIN ----------------
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

# ---------------- PRODUCTS ----------------
@app.route("/products")
def products():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("products.html", products=products)

# ---------------- SEARCH ----------------
@app.route("/search")
def search():
    if "user_id" not in session:
        return redirect("/login")

    query = request.args.get("q", "")
    conn = get_db()
    products = conn.execute(
        "SELECT * FROM products WHERE name LIKE ?",
        ('%' + query + '%',)
    ).fetchall()
    conn.close()

    return render_template("products.html", products=products)

# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute(
        "INSERT INTO cart (user_id, product_id) VALUES (?, ?)",
        (session["user_id"], product_id)
    )
    conn.commit()
    conn.close()
    return redirect("/products")

# ---------------- CART ----------------
@app.route("/cart")
def cart():
    if "user_id" not in session:
        return redirect("/login")

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

# ---------------- REMOVE FROM CART ----------------
@app.route("/remove/<int:id>")
def remove(id):
    conn = get_db()
    conn.execute("DELETE FROM cart WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/cart")

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form["username"] == "farinaz" and request.form["password"] == "farinaz#123":
            session["admin"] = True
            return redirect("/admin/dashboard")
        return "Invalid admin credentials"
    return render_template("admin_login.html")

# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect("/admin")

    conn = get_db()
    products = conn.execute("SELECT * FROM products").fetchall()
    conn.close()
    return render_template("admin_dashboard.html", products=products)

# ---------------- ADD PRODUCT ----------------
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

# ---------------- DELETE PRODUCT ----------------
@app.route("/admin/delete/<int:id>")
def delete_product(id):
    conn = get_db()
    conn.execute("DELETE FROM products WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect("/admin/dashboard")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

 # ---------------- INVOICE ----------------
@app.route("/invoice")
def invoice():
    if "cart" not in session or not session["cart"]:
        return redirect("/products")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cart_items = []
    grand_total = 0

    for product_id, qty in session["cart"].items():
        cursor.execute("SELECT name, price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()

        if product:
            name, price = product
            total = price * qty
            grand_total += total

            cart_items.append({
                "name": name,
                "price": price,
                "qty": qty,
                "total": total
            })

    conn.close()

    return render_template(
        "invoice.html",
        cart_items=cart_items,
        grand_total=grand_total
    )

from flask import send_file
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from datetime import datetime

@app.route("/invoice/pdf")
def invoice_pdf():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    items = conn.execute("""
        SELECT products.name, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=?
    """, (session["user_id"],)).fetchall()
    conn.close()

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, height - 50, "INVOICE")

    pdf.setFont("Helvetica", 10)
    pdf.drawString(50, height - 80, f"Date: {datetime.now().strftime('%d-%m-%Y')}")

    y = height - 130
    total = 0

    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(50, y, "Product")
    pdf.drawString(300, y, "Price")
    y -= 20

    pdf.setFont("Helvetica", 10)
    for item in items:
        pdf.drawString(50, y, item["name"])
        pdf.drawString(300, y, f"₹ {item['price']}")
        total += item["price"]
        y -= 20

    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(50, y - 20, f"Total Amount: ₹ {total}")

    pdf.showPage()
    pdf.save()

    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name="invoice.pdf")

if __name__ == "__main__":
    app.run(debug=True)