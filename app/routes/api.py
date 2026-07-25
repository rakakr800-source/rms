from flask import Blueprint, jsonify, request
from flask_login import login_required
from app.models import db, User, Product, Order, Expense, Notification
from sqlalchemy import or_

api_bp = Blueprint('api', __name__)

@api_bp.route('/api/search')
@login_required
def global_search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"results": []})
        
    results = []
    
    # 1. Search Users
    users = User.query.filter(or_(
        User.name.like(f"%{query}%"),
        User.username.like(f"%{query}%"),
        User.employee_id.like(f"%{query}%")
    )).limit(5).all()
    for u in users:
        results.append({
            "category": "Users",
            "title": u.name,
            "sub": f"Role: {u.role} | ID: {u.employee_id}",
            "url": f"/users" # link to list or direct if implemented
        })
        
    # 2. Search Products (Inventory)
    products = Product.query.filter(or_(
        Product.name.like(f"%{query}%"),
        Product.code.like(f"%{query}%"),
        Product.barcode.like(f"%{query}%")
    )).limit(5).all()
    for p in products:
        results.append({
            "category": "Inventory Products",
            "title": p.name,
            "sub": f"Stock: {p.current_stock} {p.unit} | Price: {p.selling_price}",
            "url": f"/inventory"
        })
        
    # 3. Search Orders / Bills
    orders = Order.query.filter(or_(
        Order.order_number.like(f"%{query}%"),
        Order.customer_name.like(f"%{query}%"),
        Order.customer_mobile.like(f"%{query}%")
    )).limit(5).all()
    for o in orders:
        results.append({
            "category": "Orders/Bills",
            "title": o.order_number,
            "sub": f"Total: {o.grand_total} | Status: {o.payment_status}",
            "url": f"/billing/invoice/{o.id}"
        })
        
    # 4. Search Expenses
    expenses = Expense.query.filter(or_(
        Expense.product_name.like(f"%{query}%"),
        Expense.vendor.like(f"%{query}%"),
        Expense.category.like(f"%{query}%"),
        Expense.invoice_number.like(f"%{query}%")
    )).limit(5).all()
    for e in expenses:
        results.append({
            "category": "Expenses",
            "title": f"{e.product_name} - {e.category}",
            "sub": f"Amount: {e.final_amount} | Date: {e.date}",
            "url": f"/expenses"
        })
        
    return jsonify({"results": results})

@api_bp.route('/api/notifications/unread')
@login_required
def unread_count():
    count = Notification.query.filter_by(is_read=False).count()
    latest = Notification.query.filter_by(is_read=False).order_by(Notification.created_at.desc()).limit(5).all()
    return jsonify({
        "count": count,
        "latest": [{
            "id": n.id,
            "title": n.title,
            "message": n.message,
            "type": n.type,
            "created_at": n.created_at.strftime('%H:%M')
        } for n in latest]
    })
