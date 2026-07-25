from flask import request
from flask_login import current_user
from app.models import db, ActivityLog, Notification, RestaurantSetting
from datetime import datetime

def log_activity(action, module, description):
    """Logs the user activity in the database."""
    try:
        user_agent = request.headers.get('User-Agent', '')
        
        # Simple parser for browser / OS
        browser = "Unknown"
        if "Firefox" in user_agent:
            browser = "Firefox"
        elif "Chrome" in user_agent:
            browser = "Chrome"
        elif "Safari" in user_agent:
            browser = "Safari"
        elif "Edge" in user_agent:
            browser = "Edge"
            
        operating_system = "Unknown"
        if "Windows" in user_agent:
            operating_system = "Windows"
        elif "Macintosh" in user_agent or "Mac OS" in user_agent:
            operating_system = "macOS"
        elif "Linux" in user_agent:
            operating_system = "Linux"
        elif "Android" in user_agent:
            operating_system = "Android"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            operating_system = "iOS"
            
        device = "Desktop"
        if "Mobi" in user_agent or "Android" in user_agent or "iPhone" in user_agent:
            device = "Mobile/Tablet"

        ip_address = request.remote_addr or "127.0.0.1"
        if request.headers.getlist("X-Forwarded-For"):
            ip_address = request.headers.getlist("X-Forwarded-For")[0]

        user_id = current_user.id if current_user and current_user.is_authenticated else None
        user_name = current_user.name if current_user and current_user.is_authenticated else "Anonymous"

        log = ActivityLog(
            user_id=user_id,
            user_name=user_name,
            ip_address=ip_address,
            browser=browser,
            operating_system=operating_system,
            device=device,
            action=action,
            module=module,
            description=description
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Error logging activity: {e}")
        db.session.rollback()

def trigger_notification(type, title, message):
    """Triggers an in-system notification."""
    try:
        notif = Notification(
            type=type,
            title=title,
            message=message
        )
        db.session.add(notif)
        db.session.commit()
    except Exception as e:
        print(f"Error triggering notification: {e}")
        db.session.rollback()

def get_setting(key, default=None):
    """Gets a restaurant setting by key, returns default if not found."""
    try:
        setting = RestaurantSetting.query.filter_by(key=key).first()
        if setting:
            return setting.value
        return default
    except Exception as e:
        print(f"Error fetching setting {key}: {e}")
        return default

def set_setting(key, value):
    """Sets/updates a restaurant setting."""
    try:
        setting = RestaurantSetting.query.filter_by(key=key).first()
        if not setting:
            setting = RestaurantSetting(key=key, value=str(value))
            db.session.add(setting)
        else:
            setting.value = str(value)
        db.session.commit()
    except Exception as e:
        print(f"Error setting setting {key}: {e}")
        db.session.rollback()
