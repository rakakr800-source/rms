from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, MenuItem
from app.forms import MenuItemForm
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity
import os

menu_bp = Blueprint('menu', __name__)

@menu_bp.route('/menu')
@login_required
@permission_required('menu')
def list_menu():
    items = MenuItem.query.all()
    return render_template('menu/list.html', items=items)

@menu_bp.route('/menu/add', methods=['GET', 'POST'])
@login_required
@permission_required('menu')
def add_menu_item():
    form = MenuItemForm()
    if form.validate_on_submit():
        item = MenuItem(
            name=form.name.data,
            code=form.code.data,
            category=form.category.data,
            price=form.price.data,
            gst_percent=form.gst_percent.data,
            description=form.description.data,
            status=form.status.data
        )
        
        if form.image.data:
            file = form.image.data
            filename = secure_filename(f"menu_{item.code}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            item.image = f"uploads/products/{filename}"
            
        db.session.add(item)
        db.session.commit()
        
        log_activity("Add Menu Item", "Menu", f"Added menu item {item.name} (Code: {item.code})")
        flash(f"Menu item {item.name} successfully created!", "success")
        return redirect(url_for('menu.list_menu'))
        
    return render_template('menu/add.html', form=form, title="Add Menu Item")

@menu_bp.route('/menu/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('menu')
def edit_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    form = MenuItemForm(obj=item)
    if form.validate_on_submit():
        item.name = form.name.data
        item.code = form.code.data
        item.category = form.category.data
        item.price = form.price.data
        item.gst_percent = form.gst_percent.data
        item.description = form.description.data
        item.status = form.status.data
        
        if form.image.data:
            file = form.image.data
            filename = secure_filename(f"menu_{item.code}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            item.image = f"uploads/products/{filename}"
            
        db.session.commit()
        log_activity("Edit Menu Item", "Menu", f"Updated menu item {item.name}")
        flash(f"Menu item {item.name} successfully updated!", "success")
        return redirect(url_for('menu.list_menu'))
        
    return render_template('menu/add.html', form=form, title="Edit Menu Item", item=item)

@menu_bp.route('/menu/delete/<int:id>')
@login_required
@permission_required('menu')
def delete_menu_item(id):
    item = MenuItem.query.get_or_404(id)
    log_activity("Delete Menu Item", "Menu", f"Deleted menu item {item.name}")
    db.session.delete(item)
    db.session.commit()
    flash(f"Menu item {item.name} successfully deleted.", "success")
    return redirect(url_for('menu.list_menu'))
