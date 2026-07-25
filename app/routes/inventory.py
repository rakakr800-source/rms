from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Product, Category, Supplier, StockHistory
from app.forms import ProductForm
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity, trigger_notification
from datetime import datetime, date
import os

inventory_bp = Blueprint('inventory', __name__)

@inventory_bp.route('/inventory')
@login_required
@permission_required('inventory')
def index():
    products = Product.query.all()
    categories = Category.query.filter_by(type='Inventory').all()
    today = date.today()
    
    # Expiry alert & low stock notifications
    expired_products = Product.query.filter(Product.expiry_date <= today).all()
    for ep in expired_products:
        trigger_notification('expiry_alert', 'Product Expired', f"Product {ep.name} (Code: {ep.code}) has expired!")
        
    low_stock_products = Product.query.filter(Product.current_stock <= Product.min_stock).all()
    for lp in low_stock_products:
        trigger_notification('low_stock', 'Low Stock Alert', f"Product {lp.name} is running low on stock ({lp.current_stock} {lp.unit} remaining)")
        
    return render_template(
        'inventory/list.html',
        products=products,
        categories=categories,
        expired_products=expired_products,
        low_stock_products=low_stock_products
    )

@inventory_bp.route('/inventory/add', methods=['GET', 'POST'])
@login_required
@permission_required('inventory')
def add_product():
    form = ProductForm()
    # Populate categories & suppliers
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.supplier_id.choices = [(0, 'None')] + [(s.id, s.name) for s in Supplier.query.all()]
    
    if form.validate_on_submit():
        supp_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        
        product = Product(
            name=form.name.data,
            code=form.code.data,
            barcode=form.barcode.data,
            category_id=form.category_id.data,
            purchase_price=form.purchase_price.data,
            selling_price=form.selling_price.data,
            gst_percent=form.gst_percent.data,
            supplier_id=supp_id,
            current_stock=form.current_stock.data or 0.0,
            min_stock=form.min_stock.data or 10.0,
            max_stock=form.max_stock.data or 100.0,
            unit=form.unit.data,
            description=form.description.data,
            storage_location=form.storage_location.data,
            expiry_date=form.expiry_date.data
        )
        
        if form.photo.data:
            file = form.photo.data
            filename = secure_filename(f"prod_{product.code}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            product.photo = f"uploads/products/{filename}"
            
        db.session.add(product)
        db.session.commit()
        
        # Log default stock adjustment history
        if product.current_stock > 0:
            hist = StockHistory(
                product_id=product.id,
                type='Stock In',
                quantity=product.current_stock,
                remarks="Initial Stock Entry",
                user_id=current_user.id
            )
            db.session.add(hist)
            db.session.commit()
            
        log_activity("Add Product", "Inventory", f"Added inventory product {product.name} (Code: {product.code})")
        flash(f"Product {product.name} successfully created!", "success")
        return redirect(url_for('inventory.index'))
        
    return render_template('inventory/add.html', form=form, title="Add Product")

@inventory_bp.route('/inventory/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('inventory')
def edit_product(id):
    product = Product.query.get_or_404(id)
    form = ProductForm(obj=product)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.all()]
    form.supplier_id.choices = [(0, 'None')] + [(s.id, s.name) for s in Supplier.query.all()]
    
    if form.validate_on_submit():
        supp_id = form.supplier_id.data if form.supplier_id.data != 0 else None
        
        # Track stock difference
        diff = form.current_stock.data - product.current_stock
        
        product.name = form.name.data
        product.code = form.code.data
        product.barcode = form.barcode.data
        product.category_id = form.category_id.data
        product.purchase_price = form.purchase_price.data
        product.selling_price = form.selling_price.data
        product.gst_percent = form.gst_percent.data
        product.supplier_id = supp_id
        product.current_stock = form.current_stock.data
        product.min_stock = form.min_stock.data
        product.max_stock = form.max_stock.data
        product.unit = form.unit.data
        product.description = form.description.data
        product.storage_location = form.storage_location.data
        product.expiry_date = form.expiry_date.data
        
        if form.photo.data:
            file = form.photo.data
            filename = secure_filename(f"prod_{product.code}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            product.photo = f"uploads/products/{filename}"
            
        db.session.commit()
        
        # Log Stock history if updated
        if diff != 0:
            hist = StockHistory(
                product_id=product.id,
                type='Stock Adjustment' if diff < 0 else 'Stock In',
                quantity=abs(diff),
                remarks=f"Adjusted stock directly. Difference: {diff}",
                user_id=current_user.id
            )
            db.session.add(hist)
            db.session.commit()
            
        log_activity("Edit Product", "Inventory", f"Updated product {product.name}")
        flash(f"Product {product.name} successfully updated!", "success")
        return redirect(url_for('inventory.index'))
        
    if request.method == 'GET':
        form.category_id.data = product.category_id
        form.supplier_id.data = product.supplier_id if product.supplier_id else 0
        
    return render_template('inventory/add.html', form=form, title="Edit Product", product=product)

@inventory_bp.route('/inventory/stock-adjust', methods=['POST'])
@login_required
@permission_required('inventory')
def stock_adjust():
    product_id = request.form.get('product_id', type=int)
    adjust_type = request.form.get('adjust_type') # Stock In, Stock Out, Stock Transfer
    qty = request.form.get('quantity', type=float)
    remarks = request.form.get('remarks', '')
    
    product = Product.query.get_or_404(product_id)
    
    if adjust_type == 'Stock In':
        product.current_stock += qty
    elif adjust_type in ['Stock Out', 'Stock Transfer']:
        if product.current_stock < qty:
            flash(f"Insufficient stock to complete operation! Current: {product.current_stock} {product.unit}", "danger")
            return redirect(url_for('inventory.index'))
        product.current_stock -= qty
        
    hist = StockHistory(
        product_id=product.id,
        type=adjust_type,
        quantity=qty,
        remarks=remarks,
        user_id=current_user.id
    )
    db.session.add(hist)
    db.session.commit()
    
    log_activity(adjust_type, "Inventory", f"{adjust_type} for product {product.name} with quantity {qty} {product.unit}")
    flash(f"Stock successfully adjusted for {product.name}!", "success")
    return redirect(url_for('inventory.index'))

@inventory_bp.route('/inventory/history/<int:id>')
@login_required
@permission_required('inventory')
def product_history(id):
    product = Product.query.get_or_404(id)
    histories = StockHistory.query.filter_by(product_id=id).order_by(StockHistory.date.desc()).all()
    return render_template('inventory/history.html', product=product, histories=histories)
