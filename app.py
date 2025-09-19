from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, Response
from flask_login import login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from extensions import db, login_manager, migrate
from commands import init_db_command, create_admin_command, reset_db_command
from models.user import User
from models.attendance import Attendance
from utils.face_utils import process_image, compare_faces
import csv
from io import StringIO
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import numpy as np
from sqlalchemy import func, case
import io
from flask_mail import Mail, Message

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://postgres:root@localhost:5432/attendance_system')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=int(os.getenv('SESSION_LIFETIME_HOURS', 8)))

# Email Configuration
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

# Face recognition settings
FACE_RECOGNITION_THRESHOLD = float(os.getenv('FACE_RECOGNITION_THRESHOLD', 0.75))
WORKING_HOURS_START = datetime.strptime(os.getenv('WORKING_HOURS_START', '09:00'), '%H:%M').time()
WORKING_HOURS_END = datetime.strptime(os.getenv('WORKING_HOURS_END', '17:00'), '%H:%M').time()
LATE_THRESHOLD_MINUTES = int(os.getenv('LATE_THRESHOLD_MINUTES', 30))

# Initialize extensions
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'
migrate.init_app(app, db)
csrf = CSRFProtect(app)
mail = Mail(app)
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Register CLI commands
app.cli.add_command(init_db_command)
app.cli.add_command(create_admin_command)
app.cli.add_command(reset_db_command)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Basic routes
@app.route('/')
def index():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
@limiter.limit("5 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email') or request.json.get('email')
        password = request.form.get('password') or request.json.get('password')
        
        if not email or not password:
            if request.is_json:
                return jsonify({'success': False, 'message': 'Email and password are required'}), 400
            flash('Email and password are required', 'danger')
            return redirect(url_for('login'))
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            
            if request.is_json:
                return jsonify({
                    'success': True,
                    'message': 'Login successful',
                    'redirect': url_for('index')
                })
            
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        
        if request.is_json:
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        flash('Invalid email or password', 'danger')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully.', 'success')
    return redirect(url_for('index'))

# Admin routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    today = datetime.utcnow().date()
    stats = {
        'total_employees': User.query.filter_by(is_admin=False).count(),
        'present_today': Attendance.query.filter_by(status='present').filter(Attendance.timestamp >= today).count(),
        'late_today': Attendance.query.filter_by(status='late').filter(Attendance.timestamp >= today).count(),
        'absent_today': User.query.filter_by(is_admin=False).count() - 
                        Attendance.query.filter(Attendance.timestamp >= today).filter(Attendance.status.in_(['present', 'late'])).count()
    }
    recent_attendance = Attendance.query.order_by(Attendance.timestamp.desc()).limit(10).all()
    return render_template('admin_dashboard.html', stats=stats, recent_attendance=recent_attendance)

@app.route('/admin/employees')
@login_required
def manage_employees():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    employees = User.query.filter_by(is_admin=False).all()
    return render_template('manage_employees.html', employees=employees)

@app.route('/admin/employees/add', methods=['GET', 'POST'])
@login_required
def add_employee():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        department = request.form.get('department')
        image = request.form.get('image')  # Base64 image string
        
        if not all([name, email, password, image]):
            flash('All fields, including face image, are required.', 'danger')
            return render_template('employees.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'warning')
            return render_template('employees.html')
        
        user = User(
            name=name,
            email=email,
            department=department,
            role='employee',
            is_admin=False
        )
        user.set_password(password)
        
        try:
            if image.startswith('data:image'):
                image = image.split(',')[1]
            face_box, embedding = process_image(image)
            if embedding is None:
                flash('No face detected in provided image.', 'warning')
                return render_template('employees.html')
            
            # Convert list to numpy array if needed
            if isinstance(embedding, list):
                embedding = np.array(embedding, dtype=np.float32)
            user.face_embedding = embedding.tobytes()
            
            db.session.add(user)
            db.session.commit()
            flash('Employee added successfully.', 'success')
            return redirect(url_for('manage_employees'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding employee: {str(e)}', 'danger')
            return render_template('employees.html')
    
    return render_template('employees.html')

@app.route('/admin/employees/delete/<int:employee_id>', methods=['POST'])
@login_required
def delete_employee(employee_id):
    if not current_user.is_admin:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'}), 403
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('manage_employees'))
    
    employee = User.query.get_or_404(employee_id)
    if employee.is_admin:
        if request.is_json:
            return jsonify({'success': False, 'message': 'Cannot delete admin user.'}), 400
        flash('Cannot delete admin user.', 'warning')
        return redirect(url_for('manage_employees'))
    
    try:
        # Delete associated attendance records first
        Attendance.query.filter_by(employee_id=employee_id).delete()
        db.session.delete(employee)
        db.session.commit()
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Employee deleted successfully.'})
        flash('Employee deleted successfully.', 'success')
    except Exception as e:
        db.session.rollback()
        if request.is_json:
            return jsonify({'success': False, 'message': f'Error deleting employee: {str(e)}'}), 500
        flash(f'Error deleting employee: {str(e)}', 'danger')
    
    if request.is_json:
        return jsonify({'success': True, 'message': 'Employee deleted successfully.'})
    return redirect(url_for('manage_employees'))

@app.route('/admin/employees/edit/<int:employee_id>', methods=['POST'])
@login_required
def edit_employee(employee_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Access denied. Admin privileges required.'}), 403
    
    employee = User.query.get_or_404(employee_id)
    if employee.is_admin:
        return jsonify({'success': False, 'message': 'Cannot edit admin user.'}), 400
    
    data = request.get_json()
    
    try:
        # Check if email is being changed and if it's already taken
        if data.get('email') and data['email'] != employee.email:
            if User.query.filter_by(email=data['email']).first():
                return jsonify({'success': False, 'message': 'Email already registered.'}), 400
        
        # Update employee details
        employee.name = data.get('name', employee.name)
        employee.email = data.get('email', employee.email)
        employee.department = data.get('department', employee.department)
        
        # Update password if provided
        if data.get('password'):
            employee.set_password(data['password'])
        
        # Update face embedding if image is provided
        if data.get('image'):
            image = data['image']
            if image.startswith('data:image'):
                image = image.split(',')[1]
            face_box, embedding = process_image(image)
            if embedding is None:
                return jsonify({'success': False, 'message': 'No face detected in the provided image'}), 400
            # Convert list to numpy array if needed
            if isinstance(embedding, list):
                embedding = np.array(embedding, dtype=np.float32)
            employee.face_embedding = embedding.tobytes()
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Employee updated successfully.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error updating employee: {str(e)}'}), 500

@app.route('/admin/employees/register-face/<int:employee_id>', methods=['POST'])
@login_required
def register_employee_face(employee_id):
    if not current_user.is_admin:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    employee = User.query.get_or_404(employee_id)
    data = request.get_json()
    image = data.get('image')
    if not image:
        return jsonify({'success': False, 'message': 'No image provided'}), 400
    
    try:
        if image.startswith('data:image'):
            image = image.split(',')[1]
        face_box, embedding = process_image(image)
        if embedding is None:
            return jsonify({'success': False, 'message': 'No face detected'})
        employee.face_embedding = embedding.tobytes()
        db.session.commit()
        return jsonify({'success': True, 'message': 'Face registered successfully'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500

@app.route('/admin/reports')
@login_required
def reports():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    # Get date range from query parameters or default to current month
    start_date = request.args.get('start_date', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    selected_department = request.args.get('department')
    
    # Convert string dates to datetime objects (in local timezone)
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date
    
    # Build query
    query = Attendance.query.join(User)
    
    # Add date filters (using UTC timestamps)
    query = query.filter(Attendance.timestamp >= start)
    query = query.filter(Attendance.timestamp < end)
    
    # Add department filter if specified
    if selected_department:
        query = query.filter(User.department == selected_department)
    
    # Get all attendance records for the date range
    attendance_records = query.order_by(Attendance.timestamp.desc()).all()
    
    # Get unique departments for the filter dropdown
    departments = db.session.query(User.department).distinct().filter(User.department.isnot(None)).all()
    departments = [dept[0] for dept in departments]
    
    # Calculate summary statistics
    total_days = (end - start).days
    total_employees = User.query.filter_by(is_admin=False).count()
    total_attendance = len(attendance_records)
    
    # Calculate attendance by status
    present_count = sum(1 for record in attendance_records if record.status == 'present')
    late_count = sum(1 for record in attendance_records if record.status == 'late')
    absent_count = total_employees * total_days - total_attendance
    
    # Calculate average hours worked
    total_hours = sum(record.calculate_hours_worked() for record in attendance_records if record.time_out)
    avg_hours = total_hours / total_attendance if total_attendance > 0 else 0
    
    # Calculate attendance rate
    attendance_rate = (total_attendance / (total_employees * total_days)) * 100 if total_employees > 0 else 0
    
    # Create summary dictionary
    summary = {
        'total_days': total_days,
        'total_employees': total_employees,
        'total_attendance': total_attendance,
        'present_count': present_count,
        'late_count': late_count,
        'absent_count': absent_count,
        'avg_hours': round(avg_hours, 2),
        'attendance_rate': round(attendance_rate, 2),
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Get department-wise statistics
    departments = db.session.query(User.department, 
        func.count(Attendance.id).label('total'),
        func.sum(case((Attendance.status == 'present', 1), else_=0)).label('present'),
        func.sum(case((Attendance.status == 'late', 1), else_=0)).label('late')
    ).join(Attendance).filter(
        Attendance.timestamp >= start,
        Attendance.timestamp < end
    ).group_by(User.department).all()
    
    # Format department data for the template
    department_stats = []
    for dept, total, present, late in departments:
        department_stats.append({
            'name': dept,
            'total': total,
            'present': present or 0,
            'late': late or 0,
            'absent': total - (present or 0) - (late or 0),
            'attendance_rate': round((present or 0) / total * 100 if total > 0 else 0, 2)
        })
    
    # Convert UTC timestamps to local time for display
    for record in attendance_records:
        record.timestamp = record.timestamp.replace(tzinfo=None)
        record.time_in = record.time_in.replace(tzinfo=None)
        if record.time_out:
            record.time_out = record.time_out.replace(tzinfo=None)
    
    return render_template('reports.html',
                         summary=summary,
                         department_stats=department_stats,
                         attendance_records=attendance_records,
                         departments=departments,
                         selected_department=selected_department,
                         start_date=start_date,
                         end_date=end_date)

# Face recognition and attendance routes
@app.route('/api/face/verify', methods=['POST'])
def verify_face():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'success': False, 'message': 'No image provided'})
    
    try:
        if data['image'].startswith('data:image'):
            image = data['image'].split(',')[1]
        face_box, embedding = process_image(image)
        if face_box is None or embedding is None:
            return jsonify({'success': False, 'message': 'No face detected'})
        
        # Find matching employee with highest similarity
        employees = User.query.filter_by(is_admin=False).all()
        best_match = None
        highest_similarity = 0
        
        for employee in employees:
            if employee.face_embedding:
                # Convert stored bytes back to numpy array
                stored_embedding = np.frombuffer(employee.face_embedding, dtype=np.float32)
                is_match, similarity = compare_faces(embedding, stored_embedding, threshold=FACE_RECOGNITION_THRESHOLD)
                
                # Keep track of the best match
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match = employee
        
        # Only proceed if we have a match above the threshold
        if best_match and highest_similarity >= FACE_RECOGNITION_THRESHOLD:
            employee = best_match
            print(f"Face matched with {employee.name} (ID: {employee.id}) with similarity {highest_similarity:.4f}")
            
            # Mark attendance
            now = datetime.utcnow()
            today = now.date()
            start_time = datetime.combine(today, WORKING_HOURS_START)
            late_time = start_time + timedelta(minutes=LATE_THRESHOLD_MINUTES)
            status = 'present' if now <= late_time else 'late'
            
            # Check if already marked attendance today
            existing = Attendance.query.filter_by(employee_id=employee.id).filter(Attendance.timestamp >= today).first()
            if existing:
                if not existing.time_out:
                    # Calculate time difference between clock-in and now
                    time_diff = now - existing.time_in
                    if time_diff.total_seconds() < 600:  # 10 minutes in seconds
                        return jsonify({
                            'success': False,
                            'message': f'Cannot clock out yet. Minimum 10 minutes required. Time elapsed: {int(time_diff.total_seconds() / 60)} minutes',
                            'employee_name': employee.name,
                            'status': 'minimum_time_not_met'
                        })
                    
                    existing.set_time_out(now)
                    db.session.commit()
                    # Send clock out notification
                    send_attendance_notification(employee, existing, existing.calculate_hours_worked())
                    return jsonify({
                        'success': True,
                        'message': f'Clocked out successfully. Hours worked: {existing.calculate_hours_worked():.2f}',
                        'employee_name': employee.name,
                        'status': 'clocked_out'
                    })
                return jsonify({
                    'success': True,
                    'message': 'Already marked attendance for today',
                    'employee_name': employee.name,
                    'status': 'already_marked'
                })
            
            # Create new attendance record
            attendance = Attendance(
                employee_id=employee.id,
                time_in=now,
                status=status,
                timestamp=now
            )
            db.session.add(attendance)
            db.session.commit()
            
            # Send clock in notification
            send_attendance_notification(employee, attendance)
            
            return jsonify({
                'success': True,
                'message': f'Attendance marked as {status}',
                'employee_name': employee.name,
                'status': status
            })
        
        print(f"No face match found. Highest similarity was {highest_similarity:.4f} (threshold: {FACE_RECOGNITION_THRESHOLD})")
        return jsonify({'success': False, 'message': 'Face not recognized'})
    except Exception as e:
        db.session.rollback()
        print(f"Error in face verification: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/admin/reports/export')
@login_required
def export_reports():
    if not current_user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('index'))
    
    try:
        # Get date range from query parameters or default to current month
        start_date = request.args.get('start_date', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        department = request.args.get('department')
        
        # Convert string dates to datetime objects
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)  # Include the end date
        
        # Build query
        query = Attendance.query.join(User)
        
        # Add date filters
        query = query.filter(Attendance.timestamp >= start)
        query = query.filter(Attendance.timestamp < end)
        
        # Add department filter if specified
        if department:
            query = query.filter(User.department == department)
        
        # Get records
        attendance_records = query.order_by(Attendance.timestamp.desc()).all()
        
        # Create CSV
        output = StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Employee Name', 'Department', 'Date', 'Time In', 'Time Out', 'Status', 'Hours Worked'])
        
        # Write data
        for record in attendance_records:
            # Get the date and time components
            date = record.timestamp.date().strftime('%Y-%m-%d')
            time_in = record.time_in.strftime('%H:%M:%S') if record.time_in else '-'
            time_out = record.time_out.strftime('%H:%M:%S') if record.time_out else '-'
            hours = f"{record.calculate_hours_worked():.2f}" if record.time_out else '-'
            
            # Write the row
            writer.writerow([
                record.user.name,
                record.user.department or 'N/A',
                date,
                time_in,
                time_out,
                record.status,
                hours
            ])
        
        # Prepare response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=attendance_report_{start_date}_to_{end_date}.csv'
            }
        )
    except Exception as e:
        print(f"Export error: {str(e)}")  # Debug logging
        flash(f'Error exporting data: {str(e)}', 'danger')
        return redirect(url_for('reports'))

@app.route('/api/attendance/export')
@login_required
def export_attendance():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get date range from query parameters or default to current month
        start_date = request.args.get('start_date', datetime.now().replace(day=1).strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        department = request.args.get('department')
        
        # Convert string dates to datetime objects
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        
        # Build query
        query = Attendance.query.join(User).filter(
            Attendance.timestamp >= start,
            Attendance.timestamp <= end
        )
        
        if department:
            query = query.filter(User.department == department)
        
        # Get attendance records
        attendance_records = query.order_by(Attendance.timestamp.desc()).all()
        
        # Create CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Date',
            'Employee Name',
            'Department',
            'Time In',
            'Time Out',
            'Hours Worked',
            'Status'
        ])
        
        # Write data
        for record in attendance_records:
            writer.writerow([
                record.timestamp.strftime('%Y-%m-%d'),
                record.user.name,
                record.user.department or 'N/A',
                record.time_in.strftime('%H:%M:%S') if record.time_in else '-',
                record.time_out.strftime('%H:%M:%S') if record.time_out else '-',
                f"{record.calculate_hours_worked():.2f}" if record.time_out else '-',
                record.status
            ])
        
        # Create response
        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=attendance_report_{start_date}_to_{end_date}.csv'
            }
        )
    except Exception as e:
        print(f"Export error: {str(e)}")  # Add logging
        return jsonify({'error': str(e)}), 500

def send_attendance_notification(employee, attendance, hours_worked=None):
    """Send email notification for attendance record"""
    try:
        # Format the email content
        subject = f"Attendance Record - {attendance.timestamp.strftime('%Y-%m-%d')}"
        
        # Build the email body
        body = f"""Dear {employee.name},

Your attendance has been recorded for today ({attendance.timestamp.strftime('%Y-%m-%d')}).

Status: {attendance.status}
Time In: {attendance.time_in.strftime('%H:%M:%S')}"""

        # Add time out and hours worked if available
        if attendance.time_out:
            body += f"""
Time Out: {attendance.time_out.strftime('%H:%M:%S')}
Hours Worked: {hours_worked:.2f}"""

        body += """

Thank you for using our attendance system."""

        # Send the email
        msg = Message(
            subject=subject,
            recipients=[employee.email],
            body=body
        )
        mail.send(msg)
        print(f"Email sent successfully to {employee.email}")
    except Exception as e:
        print(f"Error sending email: {str(e)}")
        # Log the error but don't raise it to prevent disrupting the attendance process

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=os.getenv('FLASK_DEBUG', '1') == '1')