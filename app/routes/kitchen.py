from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Order, OrderItem
from app.utils.decorators import permission_required
from app.utils.helpers import log_activity, trigger_notification

kitchen_bp = Blueprint('kitchen', __name__)

@kitchen_bp.route('/kitchen')
@login_required
@permission_required('kitchen')
def display():
    # Kitchen sees Pending, Preparing, and Ready orders
    active_orders = Order.query.filter(Order.kitchen_status.in_(['Pending', 'Preparing', 'Ready'])).order_by(Order.created_at.asc()).all()
    return render_template('kitchen/display.html', orders=active_orders)

@kitchen_bp.route('/kitchen/update-item-status', methods=['POST'])
@login_required
def update_item_status():
    data = request.json
    item_id = data.get('item_id')
    new_status = data.get('status') # Preparing, Ready, Served, Cancelled
    
    item = OrderItem.query.get_or_404(item_id)
    old_status = item.kitchen_item_status
    item.kitchen_item_status = new_status
    
    order = item.order
    # Recalculate order's overall kitchen_status based on items
    all_items = OrderItem.query.filter_by(order_id=order.id).all()
    statuses = [i.kitchen_item_status for i in all_items]
    
    if all(s == 'Ready' for s in statuses):
        order.kitchen_status = 'Ready'
        trigger_notification('order_ready', 'Order Ready', f"Order {order.order_number} for Table {order.table_rel.table_number if order.table_rel else 'POS'} is fully ready!")
    elif any(s == 'Preparing' for s in statuses) or any(s == 'Ready' for s in statuses):
        order.kitchen_status = 'Preparing'
    else:
        order.kitchen_status = 'Pending'
        
    db.session.commit()
    log_activity("Update Kitchen Item Status", "Kitchen", f"Item '{item.item_name}' (Order {order.order_number}) status updated from {old_status} to {new_status}")
    
    return jsonify({
        "status": "success",
        "message": f"Item updated to {new_status}",
        "order_kitchen_status": order.kitchen_status
    })

@kitchen_bp.route('/kitchen/update-order-status/<int:order_id>', methods=['POST'])
@login_required
@permission_required('kitchen')
def update_order_status(order_id):
    new_status = request.form.get('status') # Preparing, Ready, Served
    order = Order.query.get_or_404(order_id)
    old_status = order.kitchen_status
    order.kitchen_status = new_status
    
    # Also update all items of this order to match if they are active
    for item in order.items:
        if item.kitchen_item_status != 'Cancelled':
            item.kitchen_item_status = new_status
            
    if new_status == 'Ready':
        trigger_notification('order_ready', 'Order Ready', f"Order {order.order_number} is ready to serve!")
        
    db.session.commit()
    log_activity("Update Kitchen Order Status", "Kitchen", f"Order {order.order_number} status updated from {old_status} to {new_status}")
    flash(f"Order {order.order_number} status updated to {new_status}!", "success")
    return redirect(url_for('kitchen.display'))
