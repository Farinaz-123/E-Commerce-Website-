# 🛒 The herbal Basket - Premium E-Commerce Website

A sophisticated and professional **The herbal Basket web application** developed using **Python Flask**, **SQLite**, **HTML**, and **CSS**. This project features a modern **Glassmorphism** design, real-time inventory tracking, user reviews, and comprehensive order history.

---

## 🚀 Key Features

### 👤 User Features
- **Modern Authentication**: Secure registration and login with password hashing.
- **Product Discovery**: 
  - Browse products with category filtering.
  - Search functionality for quick access.
  - **Advanced Sorting**: Sort by Newest, Price (Low to High), and Price (High to Low).
- **Product Details**: Dedicated pages for each product with high-res images and reviews.
- **Ratings & Reviews**: Share feedback and star ratings on products.
- **Cart & Checkout**:
  - Add/Remove items from the cart.
  - Real-time cart total calculation.
  - **Inventory Awareness**: Automatic stock depletion and "Out of Stock" indicators.
- **User Dashboard**:
  - View personal order history.
  - **PDF Invoices**: Download official invoices for every past order.
  - **Profile Management**: Update username and account security settings.

### 🛠 Admin Features
- **Secure Admin Panel**: Dedicated login for site administrators.
- **Inventory Management**:
  - Add new products with image, category, and stock quantity.
  - Edit existing products (update price, description, category, and stock).
  - Delete products from the catalog.
- **Product Overview**: Comprehensive dashboard to monitor all listings at a glance.

---

## 🛠 Technologies Used
- **Backend**: Python (Flask)
- **Frontend**: HTML5, Vanilla CSS 
- **Database**: SQLite 
- **PDF Generation**: ReportLab
- **Iconography**: Inter Google Font & Custom SVGs
- **Design Style**: Premium Glassmorphism (Gradients, Glass textures, Micro-animations)

---

## ⚙️ Installation & Setup

**1️⃣ Clone the Repository**
```bash
git clone https://github.com/your-username/ecommerce-website.git
cd ecommerce-website
```

**2️⃣ Install Dependencies**
```bash
pip install -r requirements.txt
```

**3️⃣ Run the Application**
```bash
python app.py
```

**4️⃣ Open in Browser**
Navigate to: `http://127.0.0.1:5000`

---

## 🗄 Database Schema
The system uses a relational **SQLite** database with the following table structure:
- **`users`**: Customer credentials and account data.
- **`products`**: Product details, pricing, categories, and stock levels.
- **`cart`**: Temporary storage for user items before purchase.
- **`orders`**: Record of completed transactions.
- **`order_items`**: Detailed breakdown of products within each order.
- **`reviews`**: Customer feedback and star ratings linked to products.

---

## 👨‍🎓 Developed By
**Farinaz**
BCA Final Year Student

## 📜 License
This project is for educational purposes only.