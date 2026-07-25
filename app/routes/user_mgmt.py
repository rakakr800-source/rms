from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename
from app.models import db, User
from app.forms import UserForm
from app.utils.decorators import role_required, permission_required
from app.utils.helpers import log_activity
import os

user_mgmt_bp = Blueprint('users', __name__)

ROLE_DEFAULT_PERMISSIONS = {
    'Admin': ['dashboard', 'users', 'attendance', 'expenses', 'suppliers', 'inventory', 'menu', 'tables', 'orders', 'kitchen', 'billing', 'customers', 'reports', 'settings'],
    'Manager': ['dashboard', 'attendance', 'expenses', 'suppliers', 'inventory', 'menu', 'tables', 'orders', 'kitchen', 'billing', 'customers', 'reports'],
    'Cashier': ['dashboard', 'orders', 'billing', 'customers', 'expenses', 'tables'],
    'Waiter': ['orders', 'tables'],
    'Kitchen': ['kitchen'],
    'Store Manager': ['dashboard', 'inventory', 'suppliers', 'expenses']
}

@user_mgmt_bp.route('/users')
@login_required
@role_required('Admin')
def list_users():
    users = User.query.all()
    return render_template('users/list.html', users=users)

@user_mgmt_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def create_user():
    form = UserForm()
    if form.validate_on_submit():
        # Check unique constraint
        if User.query.filter_by(username=form.username.data).first():
            flash("Username already exists.", "danger")
            return render_template('users/create.html', form=form, title="Create User")
        if User.query.filter_by(employee_id=form.employee_id.data).first():
            flash("Employee ID already exists.", "danger")
            return render_template('users/create.html', form=form, title="Create User")
            
        hashed_password = generate_password_hash(form.password.data or 'Welcome@123')
        
        user = User(
            employee_id=form.employee_id.data,
            name=form.name.data,
            username=form.username.data,
            password_hash=hashed_password,
            email=form.email.data,
            mobile=form.mobile.data,
            role=form.role.data,
            status=form.status.data,
            joining_date=form.joining_date.data,
            shift=form.shift.data,
            fingerprint_enabled=form.fingerprint_enabled.data
        )
        
        # Auto-assign permissions
        user.set_permissions_list(ROLE_DEFAULT_PERMISSIONS.get(form.role.data, []))
        
        # Photo handling
        if form.photo.data:
            file = form.photo.data
            filename = secure_filename(f"{user.employee_id}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            user.photo = f"uploads/profiles/{filename}"
            
        db.session.add(user)
        db.session.commit()
        
        log_activity("Create User", "Users", f"Created user {user.username} (Role: {user.role})")
        flash(f"User {user.name} successfully created!", "success")
        return redirect(url_for('users.list_users'))
        
    return render_template('users/create.html', form=form, title="Create User")

@user_mgmt_bp.route('/users/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    
    # Password field is optional on edit
    if form.validate_on_submit():
        user.employee_id = form.employee_id.data
        user.name = form.name.data
        user.username = form.username.data
        user.email = form.email.data
        user.mobile = form.mobile.data
        
        # Only Admin can change roles and keep custom permissions intact
        if user.role != form.role.data:
            user.role = form.role.data
            user.set_permissions_list(ROLE_DEFAULT_PERMISSIONS.get(form.role.data, []))
            
        user.status = form.status.data
        user.shift = form.shift.data
        user.joining_date = form.joining_date.data
        user.fingerprint_enabled = form.fingerprint_enabled.data
        
        if form.password.data:
            user.password_hash = generate_password_hash(form.password.data)
            
        if form.photo.data:
            file = form.photo.data
            filename = secure_filename(f"{user.employee_id}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profiles')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            user.photo = f"uploads/profiles/{filename}"
            
        # Extract custom permissions if requested in request.form
        selected_perms = request.form.getlist('user_permissions')
        if selected_perms:
            user.set_permissions_list(selected_perms)
            
        db.session.commit()
        log_activity("Edit User", "Users", f"Modified user {user.username}")
        flash(f"User {user.name} successfully updated!", "success")
        return redirect(url_for('users.list_users'))
        
    return render_template('users/create.html', form=form, title="Edit User", user=user, permissions=ROLE_DEFAULT_PERMISSIONS)

@user_mgmt_bp.route('/users/delete/<int:id>')
@login_required
@role_required('Admin')
def delete_user(id):
    if id == current_user.id:
        flash("You cannot delete yourself!", "danger")
        return redirect(url_for('users.list_users'))
        
    user = User.query.get_or_404(id)
    log_activity("Delete User", "Users", f"Deleted user {user.username}")
    db.session.delete(user)
    db.session.commit()
    flash(f"User {user.name} successfully deleted.", "success")
    return redirect(url_for('users.list_users'))
