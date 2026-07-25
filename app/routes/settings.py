from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, send_file
from flask_login import login_required, current_user
from app.models import db, RestaurantSetting, ActivityLog, Notification, User
from app.utils.decorators import role_required, permission_required
from app.utils.helpers import log_activity, set_setting, get_setting
import subprocess
import os

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/settings', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def index():
    if request.method == 'POST':
        # Update settings
        set_setting('restaurant_name', request.form.get('restaurant_name', 'RMS'))
        set_setting('address', request.form.get('address', ''))
        set_setting('phone', request.form.get('phone', ''))
        set_setting('email', request.form.get('email', ''))
        set_setting('gst_number', request.form.get('gst_number', ''))
        set_setting('invoice_prefix', request.form.get('invoice_prefix', 'INV-'))
        set_setting('currency', request.form.get('currency', '₹'))
        set_setting('timezone', request.form.get('timezone', 'Asia/Kolkata'))
        set_setting('upi_id', request.form.get('upi_id', 'pay@merchant'))
        
        log_activity("Update Settings", "Settings", "System settings successfully updated.")
        flash("Settings successfully updated!", "success")
        return redirect(url_for('settings.index'))
        
    # Get settings for loading into fields
    settings = {
        'restaurant_name': get_setting('restaurant_name', 'RMS'),
        'address': get_setting('address', ''),
        'phone': get_setting('phone', ''),
        'email': get_setting('email', ''),
        'gst_number': get_setting('gst_number', ''),
        'invoice_prefix': get_setting('invoice_prefix', 'INV-'),
        'currency': get_setting('currency', '₹'),
        'timezone': get_setting('timezone', 'Asia/Kolkata'),
        'upi_id': get_setting('upi_id', 'pay@merchant')
    }
    
    return render_template('settings/index.html', settings=settings)

@settings_bp.route('/settings/logs')
@login_required
@role_required('Admin')
def view_logs():
    logs = ActivityLog.query.order_by(ActivityLog.date.desc(), ActivityLog.time.desc()).all()
    return render_template('settings/logs.html', logs=logs)

@settings_bp.route('/settings/notifications')
@login_required
def view_notifications():
    notifications = Notification.query.order_by(Notification.created_at.desc()).all()
    # Mark all as read
    for n in notifications:
        n.is_read = True
    db.session.commit()
    return render_template('settings/notifications.html', notifications=notifications)

@settings_bp.route('/settings/backup', methods=['POST'])
@login_required
@role_required('Admin')
def backup_db():
    # Simple backup utility depending on sqlite or mysql database configuration
    db_uri = current_app.config['SQLALCHEMY_DATABASE_URI']
    
    backup_folder = os.path.join(current_app.config['BASE_DIR'], 'backups')
    os.makedirs(backup_folder, exist_ok=True)
    backup_file = os.path.join(backup_folder, f"backup_{date.today().strftime('%Y%m%d')}.sql")
    
    try:
        if 'sqlite' in db_uri:
            # For SQLite, just copy the sqlite file to the backup path
            db_path = db_uri.replace('sqlite:///', '')
            # If absolute path wasn't stored
            if not os.path.isabs(db_path):
                db_path = os.path.join(current_app.config['BASE_DIR'], db_path)
            
            import shutil
            shutil.copy(db_path, backup_file)
        else:
            # For MySQL, use mysqldump command
            user = current_app.config['MYSQL_USER']
            password = current_app.config['MYSQL_PASSWORD']
            host = current_app.config['MYSQL_HOST']
            db_name = current_app.config['MYSQL_DB']
            
            # Formulate shell command safely
            cmd = f"mysqldump -u {user} -h {host} --password={password} {db_name} > {backup_file}"
            os.system(cmd)
            
        log_activity("Database Backup", "Settings", f"Database successfully backed up to {os.path.basename(backup_file)}")
        return send_file(backup_file, as_attachment=True)
        
    except Exception as ex:
        flash(f"Backup failed: {ex}", "danger")
        return redirect(url_for('settings.index'))

from datetime import date
