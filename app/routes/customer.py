from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models import db, Customer
from datetime import datetime
from app.forms import CustomerForm
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity

customer_bp = Blueprint('customers', __name__)

@customer_bp.route('/customers')
@login_required
@permission_required('customers')
def index():
    customers = Customer.query.all()
    form = CustomerForm()
    return render_template('customer/list.html', customers=customers, form=form)

@customer_bp.route('/customers/add', methods=['POST'])
@login_required
def add_customer():
    form = CustomerForm()
    if form.validate_on_submit():
        # Check uniqueness of phone
        existing = Customer.query.filter_by(phone=form.phone.data).first()
        if existing:
            flash("Customer with this phone number already exists!", "danger")
            return redirect(url_for('customers.index'))
            
        cust = Customer(
            name=form.name.data,
            phone=form.phone.data,
            birthday=form.birthday.data,
            address=form.address.data,
            loyalty_points=form.loyalty_points.data or 0
        )
        db.session.add(cust)
        db.session.commit()
        log_activity("Add Customer", "Customers", f"Added loyal customer profile for {cust.name} ({cust.phone})")
        flash(f"Customer {cust.name} added successfully!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", "danger")
    return redirect(url_for('customers.index'))

@customer_bp.route('/customers/api-add', methods=['POST'])
@login_required
def add_customer_api():
    """Endpoint for POS quick customer creation."""
    data = request.json
    name = data.get('name')
    phone = data.get('phone')
    birthday_str = data.get('birthday')
    address = data.get('address')
    
    if not name or not phone:
        return jsonify({"status": "failed", "message": "Name and Phone are required."}), 400
        
    existing = Customer.query.filter_by(phone=phone).first()
    if existing:
        return jsonify({
            "status": "success",
            "message": "Customer already exists.",
            "customer": {
                "id": existing.id,
                "name": existing.name,
                "phone": existing.phone,
                "points": existing.loyalty_points
            }
        })
        
    birthday = None
    if birthday_str:
        try:
            birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()
        except:
            pass
            
    cust = Customer(
        name=name,
        phone=phone,
        birthday=birthday,
        address=address,
        loyalty_points=0
    )
    db.session.add(cust)
    db.session.commit()
    
    log_activity("Add Customer API", "Customers", f"POS fast customer registration: {cust.name}")
    return jsonify({
        "status": "success",
        "message": "Customer registered!",
        "customer": {
            "id": cust.id,
            "name": cust.name,
            "phone": cust.phone,
            "points": cust.loyalty_points
        }
    })

@customer_bp.route('/customers/delete/<int:id>')
@login_required
@permission_required('customers')
def delete_customer(id):
    cust = Customer.query.get_or_404(id)
    log_activity("Delete Customer", "Customers", f"Deleted customer profile: {cust.name}")
    db.session.delete(cust)
    db.session.commit()
    flash(f"Customer {cust.name} successfully deleted.", "success")
    return redirect(url_for('customers.index'))
