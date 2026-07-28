from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, send_file
from flask_login import login_required, current_user
from app.models import db, Order, Customer, RestaurantTable
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity, get_setting
import qrcode
import io
import json

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/billing')
@login_required
@permission_required('billing')
def index():
    # Show active unpaid orders for checkout, and list of paid orders, excluding Cancelled
    unpaid_orders = Order.query.filter(Order.payment_status == 'Unpaid', Order.kitchen_status != 'Cancelled').order_by(Order.created_at.desc()).all()
    paid_orders = Order.query.filter(Order.payment_status == 'Paid', Order.kitchen_status != 'Cancelled').order_by(Order.created_at.desc()).all()
    return render_template('billing/index.html', unpaid_orders=unpaid_orders, paid_orders=paid_orders)

@billing_bp.route('/billing/checkout/<int:order_id>', methods=['GET', 'POST'])
@login_required
@permission_required('billing')
def checkout(order_id):
    order = Order.query.get_or_404(order_id)
    if order.kitchen_status == 'Cancelled':
        return "Cancelled orders cannot be checked out.", 400
        
    if order.payment_status == 'Paid':
        flash("This order is already fully paid!", "warning")
        return redirect(url_for('billing.index'))
        
    if request.method == 'POST':
        payment_method = request.form.get('payment_method') # Cash, UPI, Card, Split
        payment_status = 'Paid'
        
        # Split payment JSON details
        split_details = None
        if payment_method == 'Split':
            cash_amount = float(request.form.get('split_cash', 0))
            upi_amount = float(request.form.get('split_upi', 0))
            card_amount = float(request.form.get('split_card', 0))
            split_details = json.dumps({
                "Cash": cash_amount,
                "UPI": upi_amount,
                "Card": card_amount
            })
            
        order.payment_method = payment_method
        order.payment_status = payment_status
        order.split_details = split_details
        order.kitchen_status = 'Served' # Completed when paid
        
        # Free up table status
        if order.table_id:
            table = RestaurantTable.query.get(order.table_id)
            if table:
                table.status = 'Vacant'
                
        db.session.commit()
        
        log_activity("Checkout / Payment Received", "Billing", f"Received payment of {order.grand_total} via {payment_method} for Order {order.order_number}")
        flash(f"Order {order.order_number} marked as PAID!", "success")
        return redirect(url_for('billing.invoice_view', order_id=order.id))
        
    return render_template('billing/checkout.html', order=order)

@billing_bp.route('/billing/invoice/<int:order_id>')
@login_required
def invoice_view(order_id):
    order = Order.query.get_or_404(order_id)
    
    # Generate quick UPI QR code if unpaid (e.g. for quick counter payment)
    # format: upi://pay?pa=merchant@upi&pn=RMS&am=123&cu=INR
    upi_id = get_setting('upi_id', 'pay@merchant')
    qr_uri = f"upi://pay?pa={upi_id}&pn={get_setting('restaurant_name', 'RMS')}&am={order.grand_total}&cu=INR"
    
    # Create QR code in-memory
    qr = qrcode.QRCode(version=1, box_size=4, border=1)
    qr.add_data(qr_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_code_base64 = io.BytesIO(buf.getvalue())
    import base64
    qr_base64_str = base64.b64encode(qr_code_base64.read()).decode('utf-8')
    
    return render_template('billing/invoice.html', order=order, qr_base64=qr_base64_str)

@billing_bp.route('/billing/invoice/print/<int:order_id>')
@login_required
def print_invoice(order_id):
    order = Order.query.get_or_404(order_id)
    format_type = request.args.get('format', 'thermal') # thermal or a4
    return render_template('billing/print.html', order=order, format=format_type)
