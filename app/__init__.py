from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from config import Config
from app.models import db, User
import os

migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
cache = Cache()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Ensure folders exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profiles'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'products'), exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'expenses'), exist_ok=True)
    
    # Initialize extension backends
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    
    # Set up login settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
        
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.user_mgmt import user_mgmt_bp
    from app.routes.attendance import attendance_bp
    from app.routes.expense import expense_bp
    from app.routes.inventory import inventory_bp
    from app.routes.menu import menu_bp
    from app.routes.table import table_bp
    from app.routes.order import order_bp
    from app.routes.kitchen import kitchen_bp
    from app.routes.billing import billing_bp
    from app.routes.customer import customer_bp
    from app.routes.reports import reports_bp
    from app.routes.settings import settings_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(user_mgmt_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(expense_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(menu_bp)
    app.register_blueprint(table_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(kitchen_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(customer_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(api_bp)
    
    # Custom filters for jinja
    @app.template_filter('currency')
    def currency_filter(value):
        from app.utils.helpers import get_setting
        symbol = get_setting('currency', '₹')
        try:
            return f"{symbol}{float(value):,.2f}"
        except:
            return f"{symbol}{value}"
            
    @app.template_filter('menu_image')
    def menu_image_filter(image_path):
        if not image_path:
            return "https://cdn-icons-png.flaticon.com/512/3252/3252179.png"
        if image_path.startswith("http://") or image_path.startswith("https://"):
            return image_path
        # Check local file existence in static folder
        import os
        full_path = os.path.join(app.static_folder, image_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return f"/static/{image_path}"
        # Fallback beautiful default food image placeholder if missing/deleted from local filesystem
        return "https://cdn-icons-png.flaticon.com/512/3252/3252179.png"
            
    # Quick utility to get setting in template
    @app.context_processor
    def inject_settings():
        from app.utils.helpers import get_setting
        return {
            "get_setting": get_setting,
            "restaurant_name": get_setting('restaurant_name', 'RMS')
        }
        
    return app
