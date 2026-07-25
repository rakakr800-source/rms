from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required
from app.models import db, RestaurantTable
from app.forms import RestaurantTableForm
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity

table_bp = Blueprint('tables', __name__)

@table_bp.route('/tables')
@login_required
@permission_required('tables')
def layout():
    tables = RestaurantTable.query.all()
    form = RestaurantTableForm()
    return render_template('table/layout.html', tables=tables, form=form)

@table_bp.route('/tables/add', methods=['POST'])
@login_required
@permission_required('tables')
def add_table():
    form = RestaurantTableForm()
    if form.validate_on_submit():
        if RestaurantTable.query.filter_by(table_number=form.table_number.data).first():
            flash("Table number already exists!", "danger")
            return redirect(url_for('tables.layout'))
            
        table = RestaurantTable(
            table_number=form.table_number.data,
            capacity=form.capacity.data,
            status=form.status.data
        )
        db.session.add(table)
        db.session.commit()
        log_activity("Add Table", "Tables", f"Added restaurant table {table.table_number} with capacity {table.capacity}")
        flash(f"Table {table.table_number} successfully added!", "success")
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error in {field}: {error}", "danger")
    return redirect(url_for('tables.layout'))

@table_bp.route('/tables/update-status', methods=['POST'])
@login_required
def update_status_api():
    table_id = request.json.get('table_id')
    status = request.json.get('status')
    
    table = RestaurantTable.query.get_or_404(table_id)
    old_status = table.status
    table.status = status
    db.session.commit()
    
    log_activity("Update Table Status", "Tables", f"Table {table.table_number} updated from {old_status} to {status}")
    return jsonify({"status": "success", "message": f"Table {table.table_number} updated to {status}"})

@table_bp.route('/tables/delete/<int:id>')
@login_required
@permission_required('tables')
def delete_table(id):
    table = RestaurantTable.query.get_or_404(id)
    log_activity("Delete Table", "Tables", f"Deleted restaurant table {table.table_number}")
    db.session.delete(table)
    db.session.commit()
    flash(f"Table {table.table_number} successfully deleted.", "success")
    return redirect(url_for('tables.layout'))
