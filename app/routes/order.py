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
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('order/list.html', orders=orders)

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
