from app import create_app, db
from app.models import (
    User,
    ExpenseCategory,
    Category,
    RestaurantTable,
    MenuItem,
    Product,
    RestaurantSetting
)
from werkzeug.security import generate_password_hash
from datetime import date

app = create_app()

def seed_database():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # 1. Seed Admin User
        admin = User.query.filter_by(role='Admin').first()
        if not admin:
            admin_user = User(
                employee_id="EMP001",
                username="admin",
                password_hash=generate_password_hash("admin123"),
                name="System Administrator",
                email="admin@restaurant.com",
                mobile="9876543210",
                role="Admin",
                status="Active",
                joining_date=date.today(),
                shift="Day",
                fingerprint_enabled=False
            )
            # Admin gets full permissions automatically via model checks, but let's store them
            admin_user.set_permissions_list([
                'dashboard', 'users', 'attendance', 'expenses', 'suppliers', 'inventory', 
                'menu', 'tables', 'orders', 'kitchen', 'billing', 'customers', 'reports', 'settings'
            ])
            db.session.add(admin_user)
            print("Seeded admin user: username=admin, password=admin123")
            
        # 2. Seed Cashier User for testing
        cashier = User.query.filter_by(username='cashier').first()
        if not cashier:
            cashier_user = User(
                employee_id="EMP002",
                username="cashier",
                password_hash=generate_password_hash("cashier123"),
                name="Siddharth Roy (Cashier)",
                email="cashier@restaurant.com",
                mobile="9876543211",
                role="Cashier",
                status="Active",
                joining_date=date.today(),
                shift="Day",
                fingerprint_enabled=False
            )
            cashier_user.set_permissions_list(['dashboard', 'orders', 'billing', 'customers', 'expenses', 'tables'])
            db.session.add(cashier_user)
            print("Seeded cashier user: username=cashier, password=cashier123")

        # 3. Seed Kitchen User
        kitchen = User.query.filter_by(username='kitchen').first()
        if not kitchen:
            kitchen_user = User(
                employee_id="EMP003",
                username="kitchen",
                password_hash=generate_password_hash("kitchen123"),
                name="Chef Malhotra (Kitchen)",
                email="kitchen@restaurant.com",
                mobile="9876543212",
                role="Kitchen",
                status="Active",
                joining_date=date.today(),
                shift="Evening",
                fingerprint_enabled=False
            )
            kitchen_user.set_permissions_list(['kitchen'])
            db.session.add(kitchen_user)
            print("Seeded kitchen user: username=kitchen, password=kitchen123")

        # 4. Seed Expense Categories
        exp_cats = ['Milk', 'Vegetable', 'Rice', 'Oil', 'Gas', 'Sweet', 'Bakery', 'Cleaning', 'Salary', 'Transport', 'Others']
        for cat_name in exp_cats:
            if not ExpenseCategory.query.filter_by(name=cat_name).first():
                db.session.add(ExpenseCategory(name=cat_name))
                
        # 5. Seed Inventory Categories
        inv_cats = ['Sweets', 'Samosa', 'Cold Drink', 'Bakery', 'Vegetables', 'Milk', 'Paneer', 'Rice', 'Oil', 'Tea', 'Coffee', 'Spices', 'Others']
        for cat_name in inv_cats:
            if not Category.query.filter_by(name=cat_name, type='Inventory').first():
                db.session.add(Category(name=cat_name, type='Inventory'))
                
        # 6. Seed Restaurant Tables
        for i in range(1, 9):
            table_no = f"Table {i}"
            if not RestaurantTable.query.filter_by(table_number=table_no).first():
                capacity = 2 if i in [7, 8] else (6 if i in [5, 6] else 4)
                db.session.add(RestaurantTable(table_number=table_no, capacity=capacity, status='Vacant'))
                
        # 7. Seed Menu Items
        menu_samples = [
            {"name": "Gulab Jamun (Plate)", "code": "GJM", "category": "Sweets", "price": 60.0, "gst": 5.0, "desc": "Soft delicious berry sized balls made of milk solids, flour & sugar syrup."},
            {"name": "Paneer Tikka Masala", "code": "PTM", "category": "Lunch", "price": 280.0, "gst": 5.0, "desc": "Spicy paneer cubes cooked in a thick tomato-based gravy."},
            {"name": "Veg Samosa (Piece)", "code": "SAM", "category": "Snacks", "price": 15.0, "gst": 5.0, "desc": "Crispy fried pastry filled with spiced potato and peas."},
            {"name": "Masala Chai", "code": "CHAI", "category": "Cold Drinks", "price": 25.0, "gst": 5.0, "desc": "Traditional Indian spiced milk tea."},
            {"name": "Cheese Burger", "code": "CBG", "category": "Fast Food", "price": 110.0, "gst": 5.0, "desc": "Juicy vegetable patty burger with a slice of rich cheddar cheese."},
            {"name": "Special Kaju Katli (250g)", "code": "KJT", "category": "Sweets", "price": 220.0, "gst": 5.0, "desc": "Premium quality cashew fudge sweets."}
        ]
        
        for item in menu_samples:
            if not MenuItem.query.filter_by(code=item['code']).first():
                db.session.add(MenuItem(
                    name=item['name'],
                    code=item['code'],
                    category=item['category'],
                    price=item['price'],
                    gst_percent=item['gst'],
                    description=item['desc'],
                    status='Available'
                ))
                
        # 8. Seed Default Settings
        default_settings = {
            'restaurant_name': 'The Royal Swad Restaurant',
            'address': 'Main Market Road, Sector 15, New Delhi - 110001',
            'phone': '+91 99999 88888',
            'email': 'contact@royalswad.com',
            'gst_number': '07AAAAA1111A1Z1',
            'invoice_prefix': 'RS-',
            'currency': '₹',
            'timezone': 'Asia/Kolkata',
            'upi_id': 'royalswad@okaxis'
        }
        for k, v in default_settings.items():
            if not RestaurantSetting.query.filter_by(key=k).first():
                db.session.add(RestaurantSetting(key=k, value=v))
                
        db.session.commit()
        print("Database successfully seeded with commercial sample records!")

if __name__ == "__main__":
    with app.app_context():
        seed_database()

    app.run(debug=True)
