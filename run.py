from app import create_app, db
from app.models import (
    User,
    ExpenseCategory,
    Category,
    RestaurantTable,
    MenuItem,
    RestaurantSetting
)
from werkzeug.security import generate_password_hash
from datetime import date

app = create_app()


def seed_database():
    # Create all tables
    db.create_all()

    # Admin User
    if not User.query.filter_by(username="admin").first():
        admin = User(
            employee_id="EMP001",
            username="admin",
            password_hash=generate_password_hash("admin123"),
            name="Administrator",
            email="admin@restaurant.com",
            mobile="9999999999",
            role="Admin",
            status="Active",
            joining_date=date.today(),
            shift="Day"
        )
        admin.set_permissions_list([
            "dashboard","users","attendance","expenses",
            "inventory","menu","tables","orders",
            "kitchen","billing","customers",
            "reports","settings"
        ])
        db.session.add(admin)

    # Default Settings
    settings = {
        "restaurant_name":"Restaurant Management System",
        "currency":"₹",
        "invoice_prefix":"INV-"
    }

    for k,v in settings.items():
        if not RestaurantSetting.query.filter_by(key=k).first():
            db.session.add(RestaurantSetting(key=k,value=v))

    db.session.commit()


with app.app_context():
    seed_database()