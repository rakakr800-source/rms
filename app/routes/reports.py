from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required
from app.models import db, Order, Expense, Attendance, Product, Customer, Supplier
from app.utils.decorators import role_required, permission_required
from app.utils.helpers import log_activity
from datetime import datetime, date, timedelta
import csv
import io

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
@login_required
@permission_required('reports')
def index():
    return render_template('reports/index.html')

@reports_bp.route('/reports/export/<string:report_type>')
@login_required
@permission_required('reports')
def export_report(report_type):
    # Retrieve query params for filters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else date.today() - timedelta(days=30)
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else date.today()
    
    output = io.StringIO()
    filename = f"{report_type}_report_{start_date}_to_{end_date}.csv"
    
    try:
        writer = csv.writer(output)
        
        if report_type == 'sales':
            orders = Order.query.filter(
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date,
                Order.payment_status == 'Paid',
                Order.kitchen_status != 'Cancelled'
            ).all()
            
            writer.writerow(["Invoice Number", "Date", "Customer Name", "Customer Mobile", "Order Type", "Subtotal", "GST Amount", "Discount", "Round Off", "Grand Total", "Payment Method"])
            
            for o in orders:
                writer.writerow([
                    o.order_number,
                    o.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    o.customer_name or 'Walk-in',
                    o.customer_mobile or 'N/A',
                    o.order_type,
                    o.subtotal,
                    o.gst_amount,
                    o.discount,
                    o.round_off,
                    o.grand_total,
                    o.payment_method
                ])
            
        elif report_type == 'expense':
            expenses = Expense.query.filter(
                Expense.date >= start_date,
                Expense.date <= end_date
            ).all()
            
            writer.writerow(["Date", "Vendor", "Category", "Product Name", "Quantity", "Unit", "Rate", "GST", "Discount", "Final Amount", "Payment Mode", "Remarks"])
            
            for e in expenses:
                writer.writerow([
                    e.date.strftime('%Y-%m-%d'),
                    e.vendor or 'N/A',
                    e.category,
                    e.product_name,
                    e.quantity,
                    e.unit,
                    e.rate,
                    e.gst,
                    e.discount,
                    e.final_amount,
                    e.payment_mode,
                    e.remarks or ''
                ])
            
        elif report_type == 'stock':
            products = Product.query.all()
            writer.writerow(["Product Code", "Product Name", "Category", "Purchase Price", "Selling Price", "GST Percent", "Current Stock", "Unit", "Storage Location", "Expiry Date"])
            
            for p in products:
                writer.writerow([
                    p.code,
                    p.name,
                    p.category_rel.name if p.category_rel else 'N/A',
                    p.purchase_price,
                    p.selling_price,
                    p.gst_percent,
                    p.current_stock,
                    p.unit,
                    p.storage_location or 'N/A',
                    p.expiry_date.strftime('%Y-%m-%d') if p.expiry_date else 'N/A'
                ])
            
        else:
            flash("Invalid report type specified.", "danger")
            return redirect(url_for('reports.index'))
            
        log_activity("Export Report", "Reports", f"Exported {report_type} report.")
        
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )
        
    except Exception as ex:
        flash(f"Error generating report: {ex}", "danger")
        return redirect(url_for('reports.index'))

from sqlalchemy import func
