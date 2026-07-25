from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app.models import db, Expense, Supplier, ExpenseCategory
from app.forms import ExpenseForm, SupplierForm
from app.utils.decorators import role_required, permission_required
from app.utils.helpers import log_activity, trigger_notification
from datetime import datetime, date
import os
import pandas as pd
import io

expense_bp = Blueprint('expenses', __name__)

# ----------------------------------------------------
# DAILY EXPENSES ROUTES
# ----------------------------------------------------
@expense_bp.route('/expenses')
@login_required
@permission_required('expenses')
def list_expenses():
    expenses = Expense.query.order_by(Expense.date.desc()).all()
    categories = ExpenseCategory.query.all()
    return render_template('expense/list.html', expenses=expenses, categories=categories)

@expense_bp.route('/expenses/add', methods=['GET', 'POST'])
@login_required
@permission_required('expenses')
def add_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense(
            date=form.date.data,
            vendor=form.vendor.data,
            invoice_number=form.invoice_number.data,
            category=form.category.data,
            product_name=form.product_name.data,
            quantity=form.quantity.data,
            unit=form.unit.data,
            rate=form.rate.data,
            gst=form.gst.data,
            discount=form.discount.data,
            final_amount=form.final_amount.data,
            payment_mode=form.payment_mode.data,
            remarks=form.remarks.data
        )
        
        # Receipt photo handling
        if form.bill_photo.data:
            file = form.bill_photo.data
            filename = secure_filename(f"receipt_{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'expenses')
            os.makedirs(upload_path, exist_ok=True)
            file.save(os.path.join(upload_path, filename))
            expense.bill_photo = f"uploads/expenses/{filename}"
            
        db.session.add(expense)
        db.session.commit()
        
        # Trigger notification and log activity
        trigger_notification('expense_added', 'Expense Logged', f"New expense of {expense.final_amount} logged under {expense.category}")
        log_activity("Add Expense", "Expenses", f"Logged expense of {expense.final_amount} for {expense.product_name}")
        
        # If supplier exists, add to outstanding balance if paid on credit (simulated here)
        if expense.vendor:
            supp = Supplier.query.filter(Supplier.name.like(f"%{expense.vendor}%")).first()
            if supp and expense.payment_mode == 'Net Banking': # credit
                supp.outstanding_balance += expense.final_amount
                db.session.commit()
                
        flash("Expense successfully added!", "success")
        return redirect(url_for('expenses.list_expenses'))
        
    # Set default date to today
    if request.method == 'GET':
        form.date.data = date.today()
        
    return render_template('expense/add.html', form=form, title="Add Daily Expense")

@expense_bp.route('/expenses/delete/<int:id>')
@login_required
@permission_required('expenses')
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    log_activity("Delete Expense", "Expenses", f"Deleted expense record of {expense.final_amount} for {expense.product_name}")
    db.session.delete(expense)
    db.session.commit()
    flash("Expense record successfully deleted.", "success")
    return redirect(url_for('expenses.list_expenses'))

# ----------------------------------------------------
# SUPPLIER ROUTINGS
# ----------------------------------------------------
@expense_bp.route('/suppliers')
@login_required
@permission_required('suppliers')
def list_suppliers():
    suppliers = Supplier.query.all()
    return render_template('supplier/list.html', suppliers=suppliers)

@expense_bp.route('/suppliers/add', methods=['GET', 'POST'])
@login_required
@permission_required('suppliers')
def add_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        supp = Supplier(
            name=form.name.data,
            gst_number=form.gst_number.data,
            phone=form.phone.data,
            email=form.email.data,
            address=form.address.data,
            outstanding_balance=form.outstanding_balance.data or 0.0
        )
        db.session.add(supp)
        db.session.commit()
        log_activity("Add Supplier", "Expenses", f"Added supplier {supp.name}")
        flash(f"Supplier {supp.name} successfully created!", "success")
        return redirect(url_for('expenses.list_suppliers'))
        
    return render_template('supplier/add.html', form=form, title="Add Supplier")

@expense_bp.route('/suppliers/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@permission_required('suppliers')
def edit_supplier(id):
    supp = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supp)
    if form.validate_on_submit():
        supp.name = form.name.data
        supp.gst_number = form.gst_number.data
        supp.phone = form.phone.data
        supp.email = form.email.data
        supp.address = form.address.data
        supp.outstanding_balance = form.outstanding_balance.data
        db.session.commit()
        log_activity("Edit Supplier", "Expenses", f"Updated supplier details for {supp.name}")
        flash(f"Supplier {supp.name} successfully updated!", "success")
        return redirect(url_for('expenses.list_suppliers'))
        
    return render_template('supplier/add.html', form=form, title="Edit Supplier", supplier=supp)

@expense_bp.route('/suppliers/delete/<int:id>')
@login_required
@permission_required('suppliers')
def delete_supplier(id):
    supp = Supplier.query.get_or_404(id)
    log_activity("Delete Supplier", "Expenses", f"Deleted supplier {supp.name}")
    db.session.delete(supp)
    db.session.commit()
    flash(f"Supplier {supp.name} successfully deleted.", "success")
    return redirect(url_for('expenses.list_suppliers'))
