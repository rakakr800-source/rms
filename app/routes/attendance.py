from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, Response
from flask_login import login_required, current_user
from app.models import db, Attendance, User
from app.utils.decorators import role_required, permission_required
from app.utils.helpers import log_activity
from datetime import datetime, date, timedelta
import csv
import io

attendance_bp = Blueprint('attendance', __name__)

@attendance_bp.route('/attendance')
@login_required
@permission_required('attendance')
def index():
    today = date.today()
    # Admin sees all, users see their own
    if current_user.role == 'Admin':
        attendances = Attendance.query.filter_by(date=today).all()
    else:
        attendances = Attendance.query.filter_by(user_id=current_user.id).all()
    return render_template('attendance/history.html', attendances=attendances, today=today)

@attendance_bp.route('/attendance/clock-in', methods=['POST'])
@login_required
def clock_in():
    today = date.today()
    existing = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    
    if existing:
        flash("You are already clocked in for today!", "warning")
        return redirect(url_for('attendance.index'))
        
    now = datetime.now()
    # Check late entry (e.g., late if after 9:15 AM)
    late = False
    if current_user.shift == 'Day' and now.time() > datetime.strptime('09:15:00', '%H:%M:%S').time():
        late = True
        
    attn = Attendance(
        user_id=current_user.id,
        date=today,
        clock_in=now,
        late_entry=late,
        status='Present'
    )
    db.session.add(attn)
    db.session.commit()
    
    log_activity("Clock In", "Attendance", f"User {current_user.username} clocked in at {now.strftime('%H:%M:%S')}")
    flash("Clocked in successfully!", "success")
    return redirect(url_for('attendance.index'))

@attendance_bp.route('/attendance/clock-out', methods=['POST'])
@login_required
def clock_out():
    today = date.today()
    attn = Attendance.query.filter_by(user_id=current_user.id, date=today).first()
    
    if not attn:
        flash("You are not clocked in today!", "danger")
        return redirect(url_for('attendance.index'))
        
    if attn.clock_out:
        flash("You have already clocked out today!", "warning")
        return redirect(url_for('attendance.index'))
        
    now = datetime.now()
    attn.clock_out = now
    
    # Calculate working hours
    diff = now - attn.clock_in
    hours = diff.total_seconds() / 3600.0
    attn.working_hours = round(hours, 2)
    
    # Check early exit (e.g., early if before 4:00 PM for day shift)
    if current_user.shift == 'Day' and now.time() < datetime.strptime('16:00:00', '%H:%M:%S').time():
        attn.early_exit = True
        
    db.session.commit()
    log_activity("Clock Out", "Attendance", f"User {current_user.username} clocked out. Hours worked: {attn.working_hours}")
    flash(f"Clocked out successfully! Worked {attn.working_hours} hours.", "success")
    return redirect(url_for('attendance.index'))

@attendance_bp.route('/attendance/export')
@login_required
@role_required(['Admin', 'Manager'])
def export_attendance():
    attendances = Attendance.query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Employee ID", "Employee Name", "Date", "Clock In", "Clock Out", "Working Hours", "Late Entry", "Early Exit", "Status"])
    
    for a in attendances:
        user = User.query.get(a.user_id)
        writer.writerow([
            user.employee_id,
            user.name,
            a.date,
            a.clock_in.strftime('%Y-%m-%d %H:%M:%S') if a.clock_in else '',
            a.clock_out.strftime('%Y-%m-%d %H:%M:%S') if a.clock_out else '',
            a.working_hours,
            "Yes" if a.late_entry else "No",
            "Yes" if a.early_exit else "No",
            a.status
        ])
    
    response = Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance_report.csv"}
    )
    
    log_activity("Export Attendance", "Attendance", "Exported attendance log to CSV.")
    return response
