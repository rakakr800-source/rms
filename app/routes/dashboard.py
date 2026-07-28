from flask import Blueprint, render_template, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models import db, Order, Expense, User, Product, Attendance, Customer
from app.utils.decorators import role_required
from datetime import datetime, date, timedelta
from sqlalchemy import func

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    if current_user.role == 'Kitchen':
        return redirect(url_for('kitchen.display'))
        
    today = date.today()
    start_of_month = today.replace(day=1)
    
    # ----------------------------------------------------
    # CARDS & METRICS
    # ----------------------------------------------------
    # 1. Today's Sales (excluding Cancelled)
    today_sales_query = db.session.query(func.sum(Order.grand_total)).filter(
        func.date(Order.created_at) == today,
        Order.payment_status == 'Paid',
        Order.kitchen_status != 'Cancelled'
    ).scalar()
    today_sales = today_sales_query if today_sales_query else 0.0
    
    # 2. Today's Expenses
    today_expense_query = db.session.query(func.sum(Expense.final_amount)).filter(
        Expense.date == today
    ).scalar()
    today_expense = today_expense_query if today_expense_query else 0.0
    
    # 3. Today's Profit
    # Simple profit = Sales - Expense (Or with COGS if tracked, but sales - direct expenses is standard daily profit)
    today_profit = today_sales - today_expense
    
    # 4. Today's Orders (excluding Cancelled)
    today_orders = Order.query.filter(func.date(Order.created_at) == today, Order.kitchen_status != 'Cancelled').count()
    
    # 5. Pending & Completed Orders
    pending_orders = Order.query.filter(
        func.date(Order.created_at) == today,
        Order.kitchen_status.in_(['Pending', 'Preparing', 'Ready'])
    ).count()
    
    completed_orders = Order.query.filter(
        func.date(Order.created_at) == today,
        Order.kitchen_status == 'Served'
    ).count()
    
    # 6. Staff Attendance Metrics
    staff_present = Attendance.query.filter(Attendance.date == today, Attendance.status == 'Present').count()
    staff_absent = Attendance.query.filter(Attendance.date == today, Attendance.status == 'Absent').count()
    
    # 7. Inventory Low Stock
    low_stock_count = Product.query.filter(Product.current_stock <= Product.min_stock).count()
    low_stock_items = Product.query.filter(Product.current_stock <= Product.min_stock).limit(5).all()
    
    # 8. Monthly Stats (excluding Cancelled)
    monthly_sales_query = db.session.query(func.sum(Order.grand_total)).filter(
        Order.created_at >= start_of_month,
        Order.payment_status == 'Paid',
        Order.kitchen_status != 'Cancelled'
    ).scalar()
    monthly_sales = monthly_sales_query if monthly_sales_query else 0.0
    
    monthly_expense_query = db.session.query(func.sum(Expense.final_amount)).filter(
        Expense.date >= start_of_month
    ).scalar()
    monthly_expense = monthly_expense_query if monthly_expense_query else 0.0
    
    # ----------------------------------------------------
    # RECENT ACTIVITIES & LISTS (excluding Cancelled)
    # ----------------------------------------------------
    recent_orders = Order.query.filter(Order.kitchen_status != 'Cancelled').order_by(Order.created_at.desc()).limit(5).all()
    recent_expenses = Expense.query.order_by(Expense.date.desc()).limit(5).all()
    
    # Recent Attendance
    recent_attendance = Attendance.query.filter(Attendance.date == today).limit(5).all()
    
    # Top Customers
    today_customers = Customer.query.filter(Customer.visit_count > 0).order_by(Customer.total_spending.desc()).limit(5).all()
    
    return render_template(
        'dashboard/admin.html',
        today_sales=today_sales,
        today_expense=today_expense,
        today_profit=today_profit,
        today_orders=today_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        staff_present=staff_present,
        staff_absent=staff_absent,
        low_stock_count=low_stock_count,
        low_stock_items=low_stock_items,
        monthly_sales=monthly_sales,
        monthly_expense=monthly_expense,
        recent_orders=recent_orders,
        recent_expenses=recent_expenses,
        recent_attendance=recent_attendance,
        today_customers=today_customers
    )

@dashboard_bp.route('/api/sales-chart-data')
@login_required
def sales_chart_data():
    """Returns sales vs expense data for the last 7 days for Chart.js."""
    today = date.today()
    labels = []
    sales_data = []
    expense_data = []
    
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        labels.append(day.strftime('%a (%d %b)'))
        
        # Sales (excluding Cancelled)
        day_sales = db.session.query(func.sum(Order.grand_total)).filter(
            func.date(Order.created_at) == day,
            Order.payment_status == 'Paid',
            Order.kitchen_status != 'Cancelled'
        ).scalar() or 0.0
        sales_data.append(day_sales)
        
        # Expense
        day_expense = db.session.query(func.sum(Expense.final_amount)).filter(
            Expense.date == day
        ).scalar() or 0.0
        expense_data.append(day_expense)
        
    return jsonify({
        "labels": labels,
        "sales": sales_data,
        "expenses": expense_data
    })
