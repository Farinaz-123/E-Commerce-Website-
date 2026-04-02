from flask import Flask, render_template, request, redirect, session, send_file, url_for, flash
from flask_wtf import FlaskForm
from flask_mail import Mail, Message
from flask_caching import Cache
import sqlite3
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import stripe
from dotenv import load_dotenv
from forms import (LoginForm, RegisterForm, ReviewForm, UpdateProfileForm, 
                   AddProductForm, EditProductForm, SearchForm)
import logging

load_dotenv()

app = Flask(__name__)

# Security Configuration
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Email Configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', True)
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@herbalbasket.com')

# Caching Configuration
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Mail Configuration
mail = Mail(app)

# Stripe Configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

UPLOAD_FOLDER = "static/images"
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif'}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            password TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price INTEGER,
            description TEXT,
            image TEXT,
            category TEXT,
            stock INTEGER DEFAULT 0,
            benefits TEXT,
            how_to_use TEXT,
            ayurvedic_properties TEXT,
            precautions TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_amount INTEGER,
            order_status TEXT DEFAULT 'Pending',
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product_id INTEGER,
            price INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            user_id INTEGER,
            rating INTEGER,
            comment TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Create indexes for better performance
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_products_category ON products(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews(product_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cart_user_id ON cart(user_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")
    except Exception as e:
        logger.warning(f"Index creation warning: {e}")

    conn.commit()
    conn.close()

init_db()

# -------- EMAIL HELPER FUNCTIONS --------
def send_email(subject, recipient, body, html=None):
    """Send email notification"""
    try:
        if not app.config['MAIL_SERVER']:
            logger.warning(f"Email not configured. Skipping email: {subject}")
            return False
        
        msg = Message(subject=subject, recipients=[recipient], body=body, html=html)
        mail.send(msg)
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

def send_order_confirmation(user_email, order_id, total_amount):
    """Send order confirmation email"""
    subject = f"Order Confirmation - Order #{order_id}"
    body = f"""
Hello,

Thank you for your order!

Order ID: {order_id}
Total Amount: ₹{total_amount}
Order Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

You can track your order status in your dashboard.

Best regards,
The Herbal Basket Team
"""
    return send_email(subject, user_email, body)

# ---------------- HOME ----------------
@app.route("/")
def home():
    conn = get_db()
    featured_products = conn.execute(
        "SELECT * FROM products ORDER BY id DESC LIMIT 4"
    ).fetchall()
    conn.close()
    return render_template("home.html", featured_products=featured_products)

# -------- REGISTRATION --------
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            conn = get_db()
            hashed_password = generate_password_hash(form.password.data)
            conn.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (form.username.data, hashed_password)
            )
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            logger.info(f"New user registered: {form.username.data}")
            return redirect("/login")
        except Exception as e:
            flash(f'Registration error: {str(e)}', 'danger')
            logger.error(f"Registration error: {e}")
    
    return render_template("register.html", form=form)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        try:
            conn = get_db()
            user = conn.execute(
                "SELECT * FROM users WHERE username=?",
                (form.username.data,)
            ).fetchone()
            conn.close()

            if user and check_password_hash(user["password"], form.password.data):
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                flash("Login successful!", "success")
                logger.info(f"User logged in: {user['username']}")
                return redirect("/products")
            else:
                flash("Invalid username or password", "danger")
                logger.warning(f"Failed login: {form.username.data}")
        except Exception as e:
            flash("Login error occurred", "danger")
            logger.error(f"Login error: {e}")

    return render_template("login.html", form=form)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    
    orders = conn.execute("""
        SELECT * FROM orders 
        WHERE user_id=? 
        ORDER BY order_date DESC
    """, (session["user_id"],)).fetchall()
    
    conn.close()
    
    return render_template("dashboard.html", user=user, orders=orders)

# ---------------- UPDATE PROFILE ----------------
@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return redirect("/login")

    username = request.form.get("username")
    password = request.form.get("password")
    user_id = session["user_id"]

    conn = get_db()
    
    if username:
        conn.execute("UPDATE users SET username=? WHERE id=?", (username, user_id))
    
    if password:
        hashed_password = generate_password_hash(password)
        conn.execute("UPDATE users SET password=? WHERE id=?", (hashed_password, user_id))
        
    conn.commit()
    conn.close()
    
    return redirect("/dashboard")

# ---------------- PRODUCTS ----------------
@app.route("/products")
def products():

    if "user_id" not in session:
        return redirect("/login")

    category = request.args.get("category")
    problem = request.args.get("problem")
    sort = request.args.get("sort", "newest")
    
    conn = get_db()
    
    query = "SELECT * FROM products WHERE 1=1"
    params = []
    
    if category:
        query += " AND category=?"
        params.append(category)
        
    if problem:
        problem_keywords = {
            "digestion": ["%digest%", "%gut%", "%constipat%", "%stomach%"],
            "skin": ["%skin%", "%acne%", "%pore%", "%glow%"],
            "hair": ["%hair%", "%scalp%", "%root%"],
            "immunity": ["%immun%", "%cold%", "%cough%"],
            "energy": ["%energy%", "%brain%", "%memory%"],
            "sleep": ["%sleep%", "%stress%", "%relax%"],
            "pain": ["%pain%", "%inflam%", "%joint%"],
            "heart": ["%heart%", "%blood%"]
        }
        keywords = problem_keywords.get(problem, [])
        if keywords:
            # We want to match IF ANY keyword exists (OR logic)
            keyword_conditions = []
            for kw in keywords:
                keyword_conditions.append("(name LIKE ? OR description LIKE ?)")
                params.extend([kw, kw])
            
            query += " AND (" + " OR ".join(keyword_conditions) + ")"
        
    if sort == "price_low":
        query += " ORDER BY price ASC"
    elif sort == "price_high":
        query += " ORDER BY price DESC"
    else:
        query += " ORDER BY id DESC"
        
    products = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL").fetchall()
    
    conn.close()
    
    return render_template("products.html", 
                           products=products, 
                           categories=categories, 
                           selected_category=category,
                           selected_problem=problem,
                           selected_sort=sort)

# ---------------- PRODUCT DETAILS ----------------
@app.route("/product/<int:product_id>")
def product_details(product_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    
    product = conn.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    
    if not product:
        conn.close()
        return "Product not found", 404
        
    reviews = conn.execute("""
        SELECT reviews.*, users.username 
        FROM reviews 
        JOIN users ON reviews.user_id = users.id 
        WHERE product_id=? 
        ORDER BY date DESC
    """, (product_id,)).fetchall()
    
    avg_rating = conn.execute("SELECT AVG(rating) FROM reviews WHERE product_id=?", (product_id,)).fetchone()[0]
    
    conn.close()
    
    return render_template("product_details.html", product=product, reviews=reviews, avg_rating=avg_rating)

# ---------------- ADD REVIEW ----------------
@app.route("/add_review/<int:product_id>", methods=["POST"])
def add_review(product_id):
    if "user_id" not in session:
        return redirect("/login")

    rating = request.form.get("rating")
    comment = request.form.get("comment")
    user_id = session["user_id"]

    if rating and comment:
        conn = get_db()
        conn.execute(
            "INSERT INTO reviews (product_id, user_id, rating, comment) VALUES (?, ?, ?, ?)",
            (product_id, user_id, rating, comment)
        )
        conn.commit()
        conn.close()

    return redirect(f"/product/{product_id}")

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
    categories = conn.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL").fetchall()

    conn.close()

    return render_template("products.html", products=products, categories=categories)

# ---------------- SEARCH SUGGESTIONS API ----------------
from flask import jsonify

@app.route("/api/search_suggestions")
def search_suggestions():
    if "user_id" not in session:
        return jsonify([])

    query = request.args.get("q", "")
    if not query:
        return jsonify([])

    conn = get_db()
    
    # Simple LIKE query, grab top 5
    products = conn.execute(
        "SELECT id, name FROM products WHERE name LIKE ? LIMIT 5",
        ('%' + query + '%',)
    ).fetchall()
    
    conn.close()
    
    results = [{"id": p["id"], "name": p["name"]} for p in products]
    return jsonify(results)

# ---------------- ADD TO CART ----------------
@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    # Check if this product is already in the cart for this user
    existing = conn.execute(
        "SELECT id FROM cart WHERE user_id=? AND product_id=?",
        (session["user_id"], product_id)
    ).fetchone()

    if existing:
        # Add another row (quantity is tracked by counting rows)
        pass  # We still insert a new row to keep the existing checkout logic working

    conn.execute(
        "INSERT INTO cart (user_id, product_id) VALUES (?, ?)",
        (session["user_id"], product_id)
    )

    conn.commit()
    conn.close()

    # Redirect back to the referring page, or products
    referrer = request.referrer
    if referrer and "/cart" in referrer:
        return redirect("/cart")
    return redirect("/products")

# ---------------- CART ----------------
@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    # Group cart items by product, count quantity
    items = conn.execute("""
        SELECT products.id as product_id, products.name, products.price, products.image,
               COUNT(cart.id) as quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=?
        GROUP BY products.id
    """, (session["user_id"],)).fetchall()

    total = sum(item["price"] * item["quantity"] for item in items)

    conn.close()

    return render_template("cart.html", items=items, total=total)

# ---------------- INCREMENT CART ITEM ----------------
@app.route("/cart/increment/<int:product_id>")
def cart_increment(product_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    conn.execute(
        "INSERT INTO cart (user_id, product_id) VALUES (?, ?)",
        (session["user_id"], product_id)
    )
    conn.commit()
    conn.close()

    return redirect("/cart")

# ---------------- DECREMENT CART ITEM ----------------
@app.route("/cart/decrement/<int:product_id>")
def cart_decrement(product_id):
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    # Remove only ONE row for this product (the most recent one)
    row = conn.execute(
        "SELECT id FROM cart WHERE user_id=? AND product_id=? LIMIT 1",
        (session["user_id"], product_id)
    ).fetchone()
    if row:
        conn.execute("DELETE FROM cart WHERE id=?", (row["id"],))
        conn.commit()
    conn.close()

    return redirect("/cart")

# ---------------- REMOVE FROM CART ----------------
@app.route("/remove/<int:product_id>")
def remove(product_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()
    # Remove ALL rows of this product from the user's cart
    conn.execute(
        "DELETE FROM cart WHERE user_id=? AND product_id=?",
        (session["user_id"], product_id)
    )
    conn.commit()
    conn.close()

    return redirect("/cart")

# ---------------- CHECKOUT PAGE ----------------
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect("/login")
        
    conn = get_db()
    
    # Group items by product with quantity
    items = conn.execute("""
        SELECT products.id as product_id, products.name, products.price, products.image,
               COUNT(cart.id) as quantity
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=?
        GROUP BY products.id
    """, (session["user_id"],)).fetchall()
    
    if not items:
        conn.close()
        return redirect("/cart")
    
    total = sum(item["price"] * item["quantity"] for item in items)
    conn.close()

    # GET — show the checkout page
    if request.method == "GET":
        return render_template("checkout.html", items=items, total=total)

    # POST — process payment through Stripe
    line_items = []
    for item in items:
        line_items.append({
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': item['name'],
                },
                'unit_amount': item['price'] * 100,
            },
            'quantity': item['quantity'],
        })
    
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.url_root + 'payment/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.url_root + 'cart',
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return str(e)


# ---------------- PAYMENT SUCCESS ----------------
@app.route("/payment/success", methods=["GET"])
def payment_success():
    if "user_id" not in session:
        return redirect("/login")
        
    session_id = request.args.get('session_id')
    if not session_id:
        return redirect("/cart")

    try:
        # Verify Payment with Stripe
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        if checkout_session.payment_status != 'paid':
             return "Payment not successful!", 400
    except Exception as e:
        return str(e), 400


    conn = get_db()
    
    items = conn.execute("""
        SELECT cart.product_id, products.price
        FROM cart
        JOIN products ON cart.product_id = products.id
        WHERE cart.user_id=?
    """, (session["user_id"],)).fetchall()
    
    if not items:
        conn.close()
        return redirect("/cart")
        
    total_amount = sum(item["price"] for item in items)
    
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO orders (user_id, total_amount) VALUES (?, ?)",
        (session["user_id"], total_amount)
    )
    order_id = cursor.lastrowid
    
    for item in items:
        cursor.execute(
            "INSERT INTO order_items (order_id, product_id, price) VALUES (?, ?, ?)",
            (order_id, item["product_id"], item["price"])
        )
        # Decrement Stock
        cursor.execute(
            "UPDATE products SET stock = stock - 1 WHERE id = ? AND stock > 0",
            (item["product_id"],)
        )
        
    cursor.execute("DELETE FROM cart WHERE user_id=?", (session["user_id"],))
    
    conn.commit()
    conn.close()
    
    return redirect(f"/invoice/pdf/{order_id}")

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

# ---------------- ADD PRODUCT (WITH IMAGE) ----------------
@app.route("/admin/add", methods=["GET", "POST"])
def add_product():

    if "admin" not in session:
        return redirect("/admin")

    if request.method == "POST":

        name = request.form["name"]
        price = request.form["price"]
        description = request.form["description"]
        category = request.form["category"]
        stock = request.form["stock"]
        benefits = request.form.get("benefits", "")
        how_to_use = request.form.get("how_to_use", "")
        ayurvedic_properties = request.form.get("ayurvedic_properties", "")
        precautions = request.form.get("precautions", "")

        image = request.files["image"]

        filename = image.filename

        image.save(os.path.join(UPLOAD_FOLDER, filename))

        conn = get_db()

        conn.execute(
            """INSERT INTO products 
               (name, price, description, image, category, stock, benefits, how_to_use, ayurvedic_properties, precautions) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, price, description, filename, category, stock, benefits, how_to_use, ayurvedic_properties, precautions)
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

# ---------------- INVOICE PDF ----------------
@app.route("/invoice/pdf/<int:order_id>")
def invoice_pdf(order_id):

    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    order = conn.execute("SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, session["user_id"])).fetchone()
    if not order:
        conn.close()
        return redirect("/products")

    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

    items = conn.execute("""
        SELECT products.name, order_items.price
        FROM order_items
        JOIN products ON order_items.product_id = products.id
        WHERE order_items.order_id=?
    """, (order_id,)).fetchall()

    conn.close()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=30)
    elements = []

    styles = getSampleStyleSheet()
    right_align_style = ParagraphStyle(name='RightAlign', parent=styles['Normal'], alignment=2)
    center_align_style = ParagraphStyle(name='CenterAlign', parent=styles['Normal'], alignment=1)

    # Header
    header_data = [
        [Paragraph('<b>THE HERBAL BASKET</b><br/>Your Trusted Ayurvedic Store', styles['Normal']),
         Paragraph(f"<b>INVOICE</b><br/>Order #{order_id}<br/>Date: {order['order_date']}", right_align_style)]
    ]
    header_table = Table(header_data, colWidths=[3.5*inch, 3.5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # Customer Info
    customer_data = [
        [Paragraph(f"<b>Bill To:</b><br/>{user['username']}", styles['Normal'])]
    ]
    customer_table = Table(customer_data, colWidths=[7*inch])
    customer_table.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.lightgrey),
        ('PADDING', (0,0), (-1,-1), 10),
        ('BACKGROUND', (0,0), (-1,-1), colors.whitesmoke),
    ]))
    elements.append(customer_table)
    elements.append(Spacer(1, 25))

    # Items Table
    data = [['Item Description', 'Price (INR)']]
    total = 0
    for item in items:
        data.append([item["name"], f"Rs. {item['price']}"])
        total += item["price"]

    data.append(['Grand Total', f"Rs. {total}"])

    t = Table(data, colWidths=[5.5*inch, 1.5*inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 1, colors.lightgrey),
        ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'),
        ('BACKGROUND', (0,-1), (-1,-1), colors.whitesmoke),
    ]))
    elements.append(t)

    elements.append(Spacer(1, 40))
    elements.append(Paragraph("<b>Thank you for shopping with The Herbal Basket!</b>", center_align_style))

    doc.build(elements)

    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name=f"invoice_{order_id}.pdf")

# ---------------- DATABASE ----------------

@app.route('/admin/edit-product/<int:id>', methods=['GET','POST'])
def edit_product(id):

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form['name']
        price = request.form['price']
        description = request.form['description']
        category = request.form['category']
        stock = request.form['stock']
        benefits = request.form.get('benefits', '')
        how_to_use = request.form.get('how_to_use', '')
        ayurvedic_properties = request.form.get('ayurvedic_properties', '')
        precautions = request.form.get('precautions', '')
        image = request.files.get('image')

        if image and image.filename:
            filename = image.filename
            image.save(os.path.join(UPLOAD_FOLDER, filename))
            cursor.execute("""
                UPDATE products 
                SET name=?, price=?, description=?, image=?, category=?, stock=?, benefits=?, how_to_use=?, ayurvedic_properties=?, precautions=? 
                WHERE id=?
            """, (name, price, description, filename, category, stock, benefits, how_to_use, ayurvedic_properties, precautions, id))
        else:
            cursor.execute("""
                UPDATE products 
                SET name=?, price=?, description=?, category=?, stock=?, benefits=?, how_to_use=?, ayurvedic_properties=?, precautions=? 
                WHERE id=?
            """, (name, price, description, category, stock, benefits, how_to_use, ayurvedic_properties, precautions, id))

        conn.commit()
        conn.close()

        return redirect('/admin/dashboard')

    product = cursor.execute("SELECT * FROM products WHERE id=?",(id,)).fetchone()
    conn.close()

    return render_template("edit_product.html", product=product)

# ---------------- RUN APP ----------------
if __name__ == "__main__":

    if not os.path.exists("static/images"):
        os.makedirs("static/images")

    app.run(debug=True)