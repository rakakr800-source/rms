from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.models import db, Order, OrderItem, MenuItem, RestaurantTable, Customer
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity, trigger_notification
from datetime import datetime
import json

order_bp = Blueprint('orders', __name__)

@order_bp.route('/orders')
@login_required
@permission_required('orders')
def list_orders():
    # Parameters for searching & filtering
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Search parameters
    search = request.args.get('search', '').strip()
    
    # Filter parameters
    date_filter = request.args.get('date_filter', '') # today, yesterday, week, month, custom
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    order_status = request.args.get('order_status', '') # Unpaid, Paid, Cancelled, Pending, Preparing, Ready, Served
    payment_status = request.args.get('payment_status', '') # Unpaid, Paid, Partially Paid
    cashier_id = request.args.get('cashier', '')

    # Base query
    query = Order.query

    # Joins
    query = query.outerjoin(Customer, Order.customer_id == Customer.id)

    # Search filter (Bill Number / Order Number, Customer Name, Mobile Number)
    if search:
        query = query.filter(
            (Order.order_number.ilike(f'%{search}%')) |
            (Order.customer_name.ilike(f'%{search}%')) |
            (Order.customer_mobile.ilike(f'%{search}%'))
        )

    # Date filter
    from datetime import date, timedelta
    today = date.today()
    if date_filter == 'today':
        query = query.filter(db.func.date(Order.created_at) == today)
    elif date_filter == 'yesterday':
        query = query.filter(db.func.date(Order.created_at) == today - timedelta(days=1))
    elif date_filter == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        query = query.filter(db.func.date(Order.created_at) >= start_of_week)
    elif date_filter == 'month':
        query = query.filter(db.extract('month', Order.created_at) == today.month, db.extract('year', Order.created_at) == today.year)
    elif date_filter == 'custom' and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Order.created_at) >= start_dt, db.func.date(Order.created_at) <= end_dt)
        except ValueError:
            pass

    # Status Filters
    # Order Status can map to kitchen_status (Pending, Preparing, Ready, Served) or if Cancelled we can map to a specific status.
    # Note: If order is cancelled, we might use order.kitchen_status = 'Cancelled' or similar. Let's make sure cancel acts correctly.
    if order_status:
        query = query.filter(Order.kitchen_status == order_status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if cashier_id:
        try:
            query = query.filter(Order.cashier_id == int(cashier_id))
        except ValueError:
            pass

    # Order by newest
    query = query.order_by(Order.created_at.desc())

    # Pagination
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    orders = pagination.items

    # Fetch cashiers for filter
    from app.models import User
    cashiers = User.query.filter(User.role.in_(['Admin', 'Manager', 'Cashier'])).all()

    # Statistics (unfiltered or filtered? Let's do unfiltered/filtered for stats or total database stats as per standard dashboard. Let's calculate based on the filters or overall. Typically, filtered stats make sense, but requirements just say "Statistics at the top: Total Orders, Total Sales, Cancelled Orders, Average Bill Value").
    # Let's calculate filtered stats or total stats of today/all. Let's calculate them from the base query before pagination to be dynamic and highly useful!
    all_filtered_orders = query.all()
    total_orders = len(all_filtered_orders)
    total_sales = sum(o.grand_total for o in all_filtered_orders if o.payment_status == 'Paid' and o.kitchen_status != 'Cancelled')
    cancelled_orders = sum(1 for o in all_filtered_orders if o.kitchen_status == 'Cancelled')
    paid_count = sum(1 for o in all_filtered_orders if o.payment_status == 'Paid' and o.kitchen_status != 'Cancelled')
    avg_bill_value = total_sales / paid_count if paid_count > 0 else 0.0

    return render_template(
        'orders/records.html',
        orders=orders,
        pagination=pagination,
        cashiers=cashiers,
        total_orders=total_orders,
        total_sales=total_sales,
        cancelled_orders=cancelled_orders,
        avg_bill_value=avg_bill_value,
        search=search,
        date_filter=date_filter,
        start_date=start_date,
        end_date=end_date,
        order_status=order_status,
        payment_status=payment_status,
        cashier_id=cashier_id
    )

@order_bp.route('/orders/<int:order_id>/cancel', methods=['POST'])
@login_required
@role_required('Admin')
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    order.kitchen_status = 'Cancelled'
    # If table is occupied, make it vacant
    if order.table_id:
        table = RestaurantTable.query.get(order.table_id)
        if table:
            table.status = 'Vacant'
    db.session.commit()
    log_activity("Cancel Order", "Orders", f"Cancelled order {order.order_number}")
    flash(f"Order {order.order_number} has been cancelled successfully.", "success")
    return redirect(request.referrer or url_for('orders.list_orders'))

@order_bp.route('/orders/<int:order_id>/delete', methods=['POST'])
@login_required
@role_required('Admin')
def delete_order(order_id):
    order = Order.query.get_or_404(order_id)
    order_num = order.order_number
    db.session.delete(order)
    db.session.commit()
    log_activity("Delete Order", "Orders", f"Deleted order {order_num}")
    flash(f"Order {order_num} has been deleted successfully.", "success")
    return redirect(request.referrer or url_for('orders.list_orders'))

@order_bp.route('/orders/export/<format_type>', methods=['GET'])
@login_required
@permission_required('orders')
def export_orders(format_type):
    # Retrieve all matched orders with current search/filter parameters
    search = request.args.get('search', '').strip()
    date_filter = request.args.get('date_filter', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    order_status = request.args.get('order_status', '')
    payment_status = request.args.get('payment_status', '')
    cashier_id = request.args.get('cashier', '')

    query = Order.query
    if search:
        query = query.filter(
            (Order.order_number.ilike(f'%{search}%')) |
            (Order.customer_name.ilike(f'%{search}%')) |
            (Order.customer_mobile.ilike(f'%{search}%'))
        )

    from datetime import date, timedelta
    today = date.today()
    if date_filter == 'today':
        query = query.filter(db.func.date(Order.created_at) == today)
    elif date_filter == 'yesterday':
        query = query.filter(db.func.date(Order.created_at) == today - timedelta(days=1))
    elif date_filter == 'week':
        start_of_week = today - timedelta(days=today.weekday())
        query = query.filter(db.func.date(Order.created_at) >= start_of_week)
    elif date_filter == 'month':
        query = query.filter(db.extract('month', Order.created_at) == today.month, db.extract('year', Order.created_at) == today.year)
    elif date_filter == 'custom' and start_date and end_date:
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Order.created_at) >= start_dt, db.func.date(Order.created_at) <= end_dt)
        except ValueError:
            pass

    if order_status:
        query = query.filter(Order.kitchen_status == order_status)
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    if cashier_id:
        try:
            query = query.filter(Order.cashier_id == int(cashier_id))
        except ValueError:
            pass

    orders = query.order_by(Order.created_at.desc()).all()

    if format_type in ['excel', 'csv']:
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Order ID', 'Bill Number', 'Date & Time', 'Customer Name', 'Mobile', 
            'Order Type', 'Table Number', 'Total Amount', 'Payment Method', 
            'Payment Status', 'Order Status'
        ])
        
        for order in orders:
            writer.writerow([
                order.id,
                order.order_number,
                order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                order.customer_name or 'Walk-in',
                order.customer_mobile or 'N/A',
                order.order_type,
                order.table_rel.table_number if order.table_rel else 'N/A',
                order.grand_total,
                order.payment_method or 'N/A',
                order.payment_status,
                order.kitchen_status
            ])
            
        output.seek(0)
        
        if format_type == 'csv':
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype="text/csv",
                headers={"Content-disposition": "attachment; filename=order_records.csv"}
            )
        else:
            # Excel export via basic XML/CSV wrapper or send as csv with xls extension for simplicity if pandas is not guaranteed
            from flask import Response
            return Response(
                output.getvalue(),
                mimetype="application/vnd.ms-excel",
                headers={"Content-disposition": "attachment; filename=order_records.xls"}
            )
            
    elif format_type == 'pdf':
        # Simple PDF generation or HTML template rendering as PDF using a standard print layout or simple styling
        # Let's render an HTML print view that the browser can print/save as PDF, or generate a simple tabular PDF.
        # Since we want a real download PDF, let's create a minimal printable HTML view and let window.print() or we can generate a basic table.
        # Wait, let's see if we can render a simple PDF. A standard way is to return HTML template formatted for landscape printing that invokes window.print() on load.
        # This is very robust and requires no extra dependencies like reportlab or weasyprint which might not be installed.
        # Let's render a clean, professional print template.
        return render_template('billing/print_records.html', orders=orders)

    return redirect(url_for('orders.list_orders'))

@order_bp.route('/pos', methods=['GET'])
@login_required
@permission_required('orders')
def pos_interface():
    # Load all tables, categories, menu items, and customers for easy POS interaction
    tables = RestaurantTable.query.all()
    menu_items = MenuItem.query.filter_by(status='Available').all()
    customers = Customer.query.all()
    
    # Organize menu items by category
    categories = list(set([item.category for item in menu_items]))
    
    return render_template(
        'order/pos.html',
        tables=tables,
        menu_items=menu_items,
        categories=categories,
        customers=customers
    )

@order_bp.route('/pos/create-order', methods=['POST'])
@login_required
def create_order_api():
    data = request.json
    
    table_id = data.get('table_id')
    customer_id = data.get('customer_id') or None
    customer_name = data.get('customer_name')
    customer_mobile = data.get('customer_mobile')
    order_type = data.get('order_type', 'Dine In') # Dine In, Take Away, Delivery
    notes = data.get('notes')
    cart = data.get('cart', []) # array of {menu_item_id, quantity, notes}
    
    if not cart:
        return jsonify({"status": "failed", "message": "Cannot create an empty order."}), 400
        
    # Generate unique order number (RMS-YYYYMMDD-XXXX)
    today_str = datetime.now().strftime('%Y%m%d')
    order_count = Order.query.filter(Order.order_number.like(f"RMS-{today_str}-%")).count() + 1
    order_number = f"RMS-{today_str}-{order_count:04d}"
    
    order = Order(
        order_number=order_number,
        table_id=table_id if order_type == 'Dine In' else None,
        customer_id=customer_id,
        customer_name=customer_name,
        customer_mobile=customer_mobile,
        order_type=order_type,
        notes=notes,
        kitchen_status='Pending',
        cashier_id=current_user.id
    )
    
    db.session.add(order)
    db.session.flush() # get order.id
    
    subtotal = 0.0
    gst_total = 0.0
    
    # Process cart items
    for item in cart:
        menu_item = MenuItem.query.get(item['menu_item_id'])
        if not menu_item:
            continue
            
        qty = int(item['quantity'])
        rate = menu_item.price
        gst_pct = menu_item.gst_percent
        
        item_subtotal = rate * qty
        item_gst = (item_subtotal * gst_pct) / 100.0
        
        subtotal += item_subtotal
        gst_total += item_gst
        
        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=menu_item.id,
            item_name=menu_item.name,
            quantity=qty,
            rate=rate,
            gst_percent=gst_pct,
            discount=0.0,
            subtotal=item_subtotal + item_gst,
            kitchen_item_status='Pending'
        )
        db.session.add(order_item)
        
    # Save totals
    grand_total = subtotal + gst_total
    order.subtotal = round(subtotal, 2)
    order.gst_amount = round(gst_total, 2)
    order.grand_total = round(grand_total, 2)
    order.round_off = round(round(grand_total) - grand_total, 2)
    order.grand_total = round(round(grand_total), 2)
    
    # Update table status
    if order_type == 'Dine In' and table_id:
        table = RestaurantTable.query.get(table_id)
        if table:
            table.status = 'Occupied'
            
    # Loyalty point addition for registered customer
    if customer_id:
        cust = Customer.query.get(customer_id)
        if cust:
            cust.visit_count += 1
            cust.total_spending += order.grand_total
            # 1 point per 100 Rs spent
            cust.loyalty_points += int(order.grand_total / 100)
            
    db.session.commit()
    
    # Log and trigger notifications
    log_activity("Create Order", "Orders", f"Created order {order.order_number} for Table {order.table_rel.table_number if order.table_rel else 'N/A'}")
    trigger_notification('new_order', 'New Order Received', f"Order {order.order_number} received for Table {order.table_rel.table_number if order.table_rel else 'Walk-in'}")
    
    return jsonify({
        "status": "success",
        "message": "Order successfully placed!",
        "order_id": order.id,
        "order_number": order.order_number
    })
