from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

# ----------------------------------------------------
# WEBAUTHN CREDENTIAL MODEL
# ----------------------------------------------------
class WebAuthnCredential(db.Model):
    __tablename__ = 'webauthn_credentials'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    credential_id = db.Column(db.String(250), unique=True, nullable=False)
    public_key = db.Column(db.Text, nullable=False)
    sign_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ----------------------------------------------------
# USER MODEL (Role & Permission Based Access)
# ----------------------------------------------------
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(50), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    mobile = db.Column(db.String(15), nullable=True)
    role = db.Column(db.String(50), nullable=False, default='Cashier') # Admin, Manager, Cashier, Waiter, Kitchen, Store Manager
    permissions = db.Column(db.Text, nullable=True) # JSON stored as string for custom permission flags
    status = db.Column(db.String(20), default='Active') # Active, Disabled
    photo = db.Column(db.String(250), nullable=True)
    joining_date = db.Column(db.Date, nullable=True)
    shift = db.Column(db.String(50), nullable=True) # Day, Night, Evening
    fingerprint_enabled = db.Column(db.Boolean, default=False)
    
    # Relationships
    credentials = db.relationship('WebAuthnCredential', backref='user', lazy=True, cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='user', lazy=True, cascade='all, delete-orphan')
    activity_logs = db.relationship('ActivityLog', backref='user', lazy=True)

    def set_permissions_list(self, perms):
        self.permissions = json.dumps(perms)

    def get_permissions_list(self):
        if not self.permissions:
            return []
        try:
            return json.loads(self.permissions)
        except:
            return []

    def has_permission(self, permission):
        # Admin has all permissions automatically
        if self.role == 'Admin':
            return True
        perms = self.get_permissions_list()
        return permission in perms

# ----------------------------------------------------
# ATTENDANCE MODEL
# ----------------------------------------------------
class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False)
    clock_out = db.Column(db.DateTime, nullable=True)
    working_hours = db.Column(db.Float, default=0.0) # hours
    late_entry = db.Column(db.Boolean, default=False)
    early_exit = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default='Present') # Present, Absent, Half Day

# ----------------------------------------------------
# SUPPLIER MODEL
# ----------------------------------------------------
class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    gst_number = db.Column(db.String(15), nullable=True)
    phone = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    address = db.Column(db.Text, nullable=True)
    outstanding_balance = db.Column(db.Float, default=0.0)
    
    products = db.relationship('Product', backref='supplier_rel', lazy=True)

# ----------------------------------------------------
# INVENTORY CATEGORY MODEL
# ----------------------------------------------------
class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # Sweets, Samosa, Cold Drink, Bakery, etc.
    type = db.Column(db.String(50), default='Inventory') # 'Inventory' or 'Menu'
    
    products = db.relationship('Product', backref='category_rel', lazy=True)

# ----------------------------------------------------
# INVENTORY PRODUCT MODEL
# ----------------------------------------------------
class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    barcode = db.Column(db.String(100), unique=True, nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    purchase_price = db.Column(db.Float, default=0.0)
    selling_price = db.Column(db.Float, default=0.0)
    gst_percent = db.Column(db.Float, default=0.0)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True)
    current_stock = db.Column(db.Float, default=0.0)
    min_stock = db.Column(db.Float, default=0.0)
    max_stock = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Kg') # Kg, Litre, Pcs, Pkts
    description = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(250), nullable=True)
    storage_location = db.Column(db.String(100), nullable=True) # Main Kitchen, Cold Storage, Pantry
    expiry_date = db.Column(db.Date, nullable=True)
    
    stock_histories = db.relationship('StockHistory', backref='product', lazy=True, cascade='all, delete-orphan')

# ----------------------------------------------------
# STOCK HISTORY MODEL
# ----------------------------------------------------
class StockHistory(db.Model):
    __tablename__ = 'stock_history'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    type = db.Column(db.String(20), nullable=False) # Stock In, Stock Out, Stock Transfer, Stock Adjustment
    quantity = db.Column(db.Float, nullable=False)
    source = db.Column(db.String(100), nullable=True) # e.g. Warehouse
    destination = db.Column(db.String(100), nullable=True) # e.g. Kitchen
    remarks = db.Column(db.Text, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

# ----------------------------------------------------
# MENU ITEM MODEL
# ----------------------------------------------------
class MenuItem(db.Model):
    __tablename__ = 'menu_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False) # Breakfast, Lunch, Dinner, Snacks, Sweets, Cold Drinks, Fast Food
    gst_percent = db.Column(db.Float, default=5.0)
    price = db.Column(db.Float, default=0.0)
    image = db.Column(db.String(250), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    image_public_id = db.Column(db.String(250), nullable=True)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Available') # Available, Out of Stock

# ----------------------------------------------------
# TABLE MODEL
# ----------------------------------------------------
class RestaurantTable(db.Model):
    __tablename__ = 'restaurant_tables'
    id = db.Column(db.Integer, primary_key=True)
    table_number = db.Column(db.String(20), unique=True, nullable=False)
    capacity = db.Column(db.Integer, default=4)
    status = db.Column(db.String(20), default='Vacant') # Vacant, Occupied, Preparing, Ready, Billing, Paid
    
    orders = db.relationship('Order', backref='table_rel', lazy=True)

# ----------------------------------------------------
# EXPENSE CATEGORY MODEL
# ----------------------------------------------------
class ExpenseCategory(db.Model):
    __tablename__ = 'expense_categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False) # Milk, Vegetable, Rice, Oil, Gas, Sweet, Bakery, Cleaning, Salary, Transport, Others

# ----------------------------------------------------
# EXPENSE MODEL
# ----------------------------------------------------
class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    vendor = db.Column(db.String(120), nullable=True)
    invoice_number = db.Column(db.String(100), nullable=True)
    category = db.Column(db.String(100), nullable=False) # From ExpenseCategory
    product_name = db.Column(db.String(150), nullable=True)
    quantity = db.Column(db.Float, default=0.0)
    unit = db.Column(db.String(20), default='Kg')
    rate = db.Column(db.Float, default=0.0)
    gst = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    final_amount = db.Column(db.Float, nullable=False)
    payment_mode = db.Column(db.String(50), default='Cash') # Cash, UPI, Card, Net Banking
    remarks = db.Column(db.Text, nullable=True)
    bill_photo = db.Column(db.String(250), nullable=True)

# ----------------------------------------------------
# CUSTOMER MODEL
# ----------------------------------------------------
class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(15), unique=True, nullable=False)
    birthday = db.Column(db.Date, nullable=True)
    address = db.Column(db.Text, nullable=True)
    loyalty_points = db.Column(db.Integer, default=0)
    total_spending = db.Column(db.Float, default=0.0)
    visit_count = db.Column(db.Integer, default=0)
    
    orders = db.relationship('Order', backref='customer_rel', lazy=True)

# ----------------------------------------------------
# ORDER MODEL
# ----------------------------------------------------
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    table_id = db.Column(db.Integer, db.ForeignKey('restaurant_tables.id'), nullable=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    customer_name = db.Column(db.String(120), nullable=True) # for quick walk-ins
    customer_mobile = db.Column(db.String(15), nullable=True)
    order_type = db.Column(db.String(20), default='Dine In') # Dine In, Take Away, Delivery
    notes = db.Column(db.Text, nullable=True)
    kitchen_status = db.Column(db.String(20), default='Pending') # Pending, Preparing, Ready, Served, Paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Financial fields
    subtotal = db.Column(db.Float, default=0.0)
    gst_amount = db.Column(db.Float, default=0.0)
    discount = db.Column(db.Float, default=0.0)
    round_off = db.Column(db.Float, default=0.0)
    grand_total = db.Column(db.Float, default=0.0)
    payment_status = db.Column(db.String(20), default='Unpaid') # Unpaid, Paid, Partially Paid
    payment_method = db.Column(db.String(50), nullable=True) # Cash, UPI, Card, Split
    split_details = db.Column(db.Text, nullable=True) # JSON details for split payment
    cashier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

# ----------------------------------------------------
# ORDER ITEM MODEL
# ----------------------------------------------------
class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    menu_item_id = db.Column(db.Integer, db.ForeignKey('menu_items.id'), nullable=False)
    item_name = db.Column(db.String(120), nullable=False) # snapshot
    quantity = db.Column(db.Integer, default=1)
    rate = db.Column(db.Float, default=0.0)
    gst_percent = db.Column(db.Float, default=5.0)
    discount = db.Column(db.Float, default=0.0)
    subtotal = db.Column(db.Float, default=0.0)
    kitchen_item_status = db.Column(db.String(20), default='Pending') # Pending, Preparing, Ready, Served, Cancelled

    # Relationship to Menu Item for info
    menu_item = db.relationship('MenuItem')

# ----------------------------------------------------
# ACTIVITY LOG MODEL
# ----------------------------------------------------
class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    user_name = db.Column(db.String(120), nullable=True) # Snapshot in case user is deleted
    date = db.Column(db.Date, default=datetime.utcnow().date)
    time = db.Column(db.Time, default=lambda: datetime.utcnow().time())
    ip_address = db.Column(db.String(45), nullable=True)
    browser = db.Column(db.String(150), nullable=True)
    operating_system = db.Column(db.String(100), nullable=True)
    device = db.Column(db.String(100), nullable=True)
    action = db.Column(db.String(50), nullable=False) # Login, Logout, Add, Edit, Delete, Print, Export, Backup, Restore
    module = db.Column(db.String(50), nullable=False) # Auth, Users, Inventory, Billing, Table, etc.
    description = db.Column(db.Text, nullable=True)

# ----------------------------------------------------
# RESTAURANT SETTINGS MODEL
# ----------------------------------------------------
class RestaurantSetting(db.Model):
    __tablename__ = 'restaurant_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)

# ----------------------------------------------------
# NOTIFICATION MODEL
# ----------------------------------------------------
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(50), nullable=False) # low_stock, new_order, order_ready, expense_added, backup_status, staff_login
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
