import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, login_user, logout_user, login_required
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from models import db, User, CompanyProfile, StudentProfile, PlacementDrive, Application, Notification

app = Flask(__name__)
app.config['SECRET_KEY'] = 'super-secret-key-12345'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement_portal.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')

# creating necessary directories
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# initialise admin if it doesn't exist
with app.app_context():
    db.create_all()
    if not User.query.filter_by(role='admin').first():
        admin_user = User(
            email='admin@edu',
            password_hash=bcrypt.generate_password_hash('admin123').decode('utf-8'),
            role='admin',
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("Admin user created: admin@edu / admin123")

# --- All the ROUTES ---

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'company':
            return redirect(url_for('company_dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student_dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash("Your account has been deactivated/blacklisted.", "danger")
                return redirect(url_for('login'))
                
            if user.role == 'company' and user.company_profile.approval_status != 'approved':
                flash("Your company profile is pending admin approval.", "warning")
                return redirect(url_for('login'))
                
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash("Login unsuccessful. Please check email and password.", "danger")
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

import re

@app.route('/register/student', methods=['GET', 'POST'])
def register_student():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        student_roll_id = request.form.get('student_roll_id')
        name = request.form.get('name')
        contact = request.form.get('contact')
        
        # Backend Validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format.", "danger")
            return redirect(url_for('register_student'))
        if not re.match(r"^\+?\d{10,15}$", contact):
            flash("Invalid contact number format. Must be 10-15 digits.", "danger")
            return redirect(url_for('register_student'))
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for('register_student'))
        
        if User.query.filter_by(email=email).first() or StudentProfile.query.filter_by(student_roll_id=student_roll_id).first():
            flash("Email or Student ID already exists.", "danger")
            return redirect(url_for('register_student'))
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, password_hash=hashed_pw, role='student', is_active=True)
        db.session.add(user)
        db.session.commit()
        
        resume_file = request.files.get('resume')
        resume_filename = None
        if resume_file and resume_file.filename:
            filename = secure_filename(resume_file.filename)
            resume_filename = f"{student_roll_id}_{filename}"
            resume_file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))
            
        student_profile = StudentProfile(user_id=user.id, student_roll_id=student_roll_id, name=name, contact=contact, resume_filename=resume_filename)
        db.session.add(student_profile)
        db.session.commit()
        
        flash("Registration successful. You can now login.", "success")
        return redirect(url_for('login'))
        
    return render_template('register_student.html')

@app.route('/register/company', methods=['GET', 'POST'])
def register_company():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        company_name = request.form.get('company_name')
        industry = request.form.get('industry')
        hr_contact = request.form.get('hr_contact')
        website = request.form.get('website')
        
        # Backend Validation
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("Invalid email format.", "danger")
            return redirect(url_for('register_company'))
        if website and not re.match(r"^https?://[^\s/$.?#].[^\s]*$", website):
            flash("Invalid website URL format.", "danger")
            return redirect(url_for('register_company'))
        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return redirect(url_for('register_company'))
        
        if User.query.filter_by(email=email).first():
            flash("Email already exists.", "danger")
            return redirect(url_for('register_company'))
            
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(email=email, password_hash=hashed_pw, role='company', is_active=True)
        db.session.add(user)
        db.session.commit()
        
        company_profile = CompanyProfile(user_id=user.id, company_name=company_name, industry=industry, hr_contact=hr_contact, website=website)
        db.session.add(company_profile)
        db.session.commit()
        
        flash("Registration successful. Please wait for admin approval before logging in.", "success")
        return redirect(url_for('login'))
        
    return render_template('register_company.html')

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin': return redirect(url_for('index'))
    query = request.args.get('q', '')
    
    # filtering based on query
    if query:
        companies = CompanyProfile.query.join(User).filter(
            CompanyProfile.approval_status == 'approved',
            db.or_(
                CompanyProfile.company_name.contains(query),
                CompanyProfile.industry.contains(query)
            )
        ).all()
        students = StudentProfile.query.filter(
            db.or_(
                StudentProfile.name.contains(query),
                StudentProfile.student_roll_id.contains(query),
                StudentProfile.contact.contains(query)
            )
        ).all()
    else:
        companies = CompanyProfile.query.join(User).filter(CompanyProfile.approval_status == 'approved').all()
        students = StudentProfile.query.all()
        
    pending_companies = CompanyProfile.query.filter_by(approval_status='pending').all()
    ongoing_drives = PlacementDrive.query.filter(PlacementDrive.status != 'closed').all()
    applications = Application.query.all()
    
    total_companies = CompanyProfile.query.filter_by(approval_status='approved').count()
    total_students = StudentProfile.query.count()
    total_drives = PlacementDrive.query.count()
    total_applications = Application.query.count()

    return render_template('admin/dashboard.html', 
                           companies=companies,
                           students=students,
                           pending_companies=pending_companies,
                           ongoing_drives=ongoing_drives,
                           applications=applications,
                           query=query,
                           total_companies=total_companies,
                           total_students=total_students,
                           total_drives=total_drives,
                           total_applications=total_applications)

@app.route('/admin/companies')
@login_required
def admin_companies():
    if current_user.role != 'admin': return redirect(url_for('index'))
    query = request.args.get('q', '')
    if query:
        companies = CompanyProfile.query.filter(
            db.or_(
                CompanyProfile.company_name.contains(query),
                CompanyProfile.industry.contains(query)
            )
        ).all()
    else:
        companies = CompanyProfile.query.all()
    return render_template('admin/companies.html', companies=companies, query=query)

@app.route('/admin/companies/<int:company_id>/approve', methods=['POST'])
@login_required
def approve_company(company_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    company = CompanyProfile.query.get_or_404(company_id)
    company.approval_status = 'approved'
    db.session.commit()
    flash(f"Company {company.company_name} approved.", "success")
    return redirect(url_for('admin_companies'))

@app.route('/admin/companies/<int:company_id>/reject', methods=['POST'])
@login_required
def reject_company(company_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    company = CompanyProfile.query.get_or_404(company_id)
    company.approval_status = 'rejected'
    db.session.commit()
    flash(f"Company {company.company_name} rejected.", "warning")
    return redirect(url_for('admin_companies'))

@app.route('/admin/drives')
@login_required
def admin_drives():
    if current_user.role != 'admin': return redirect(url_for('index'))
    drives = PlacementDrive.query.all()
    return render_template('admin/drives.html', drives=drives)

@app.route('/admin/drives/<int:drive_id>/complete', methods=['POST'])
@login_required
def complete_drive(drive_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    drive.status = 'closed'
    db.session.commit()
    flash(f"Drive '{drive.job_title}' marked as complete.", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/students')
@login_required
def admin_students():
    if current_user.role != 'admin': return redirect(url_for('index'))
    query = request.args.get('q', '')
    if query:
        students = StudentProfile.query.filter(
            db.or_(
                StudentProfile.name.contains(query),
                StudentProfile.student_roll_id.contains(query),
                StudentProfile.contact.contains(query)
            )
        ).all()
    else:
        students = StudentProfile.query.all()
    return render_template('admin/students.html', students=students, query=query)

@app.route('/admin/student/<int:student_id>')
@login_required
def admin_student_details(student_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    student = StudentProfile.query.get_or_404(student_id)
    return render_template('admin/student_details.html', student=student)

@app.route('/admin/company/<int:company_id>')
@login_required
def admin_company_details(company_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    company = CompanyProfile.query.get_or_404(company_id)
    return render_template('admin/company_details.html', company=company)

@app.route('/admin/drive/<int:drive_id>')
@login_required
def admin_drive_details(drive_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    return render_template('admin/drive_details.html', drive=drive)

@app.route('/admin/users/<int:user_id>/toggle_status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if current_user.role != 'admin': return redirect(url_for('index'))
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash("Cannot modify admin status.", "danger")
        return redirect(request.referrer or url_for('admin_dashboard'))
        
    user.is_active = not user.is_active
    status_text = "Activated" if user.is_active else "Blacklisted/Deactivated"
    
    # cascading blacklist:- closing all drives if company is blacklisted...
    if not user.is_active and user.role == 'company' and user.company_profile:
        for drive in user.company_profile.drives:
            drive.status = 'closed'
            
    db.session.commit()
    category = "success" if user.is_active else "danger"
    flash(f"User {user.email} status changed to {status_text}.", category)
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/applications')
@login_required
def admin_applications():
    if current_user.role != 'admin': return redirect(url_for('index'))
    applications = Application.query.all()
    return render_template('admin/applications.html', applications=applications)

@app.route('/company')
@login_required
def company_dashboard():
    if current_user.role != 'company': return redirect(url_for('index'))
    if current_user.company_profile.approval_status != 'approved':
        flash("Your account is pending admin approval.", "warning")
        logout_user()
        return redirect(url_for('login'))
        
    drives = current_user.company_profile.drives
    return render_template('company/dashboard.html', drives=drives)

@app.route('/company/drive/create', methods=['GET', 'POST'])
@login_required
def create_drive():
    if current_user.role != 'company': return redirect(url_for('index'))
    if current_user.company_profile.approval_status != 'approved':
        flash("You must be an approved company to create a placement drive.", "danger")
        return redirect(url_for('company_dashboard'))
        
    if request.method == 'POST':
        job_title = request.form.get('job_title')
        job_description = request.form.get('job_description')
        eligibility_criteria = request.form.get('eligibility_criteria')
        required_skills = request.form.get('required_skills')
        experience = int(request.form.get('experience'))
        salary_range = int(request.form.get('salary_range'))
        deadline_str = request.form.get('application_deadline')
        
        try:
            deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            if deadline_date < datetime.now().date():
                flash("Application deadline must be today or a future date.", "danger")
                return redirect(url_for('create_drive'))
        except ValueError:
            flash("Invalid date format.", "danger")
            return redirect(url_for('create_drive'))
        if experience < 0:
            flash("Experience cannot be negative.", "danger")
            return redirect(url_for('create_drive'))
        if salary_range < 0:
            flash("Salary range cannot be negative.", "danger")
            return redirect(url_for('create_drive'))
            
        drive = PlacementDrive(
            company_id=current_user.company_profile.id,
            job_title=job_title,
            job_description=job_description,
            eligibility_criteria=eligibility_criteria,
            required_skills=required_skills,
            experience=experience,
            salary_range=salary_range,
            application_deadline=deadline_date,
            is_active=True,
            status='approved' # auto-approved by default will hapen after adminz approval
        )
        db.session.add(drive)
        db.session.commit()
        flash("Placement drive created and pending admin approval.", "success")
        return redirect(url_for('company_dashboard'))
        
    return render_template('company/create_drive.html')

@app.route('/company/drive/<int:drive_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_drive(drive_id):
    if current_user.role != 'company': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('company_dashboard'))
        
    if request.method == 'POST':
        drive.job_title = request.form.get('job_title')
        drive.job_description = request.form.get('job_description')
        drive.eligibility_criteria = request.form.get('eligibility_criteria')
        drive.required_skills = request.form.get('required_skills')
        
        try:
            exp_val = int(request.form.get('experience'))
            sal_val = int(request.form.get('salary_range'))
            if exp_val < 0:
                flash("Experience cannot be negative.", "danger")
                return redirect(url_for('edit_drive', drive_id=drive.id))
            if sal_val < 0:
                flash("Salary range cannot be negative.", "danger")
                return redirect(url_for('edit_drive', drive_id=drive.id))
            drive.experience = exp_val
            drive.salary_range = sal_val
        except ValueError:
            flash("Experience and Salary Range must be numbers.", "danger")
            return redirect(url_for('edit_drive', drive_id=drive.id))
            
        is_active_val = request.form.get('is_active')
        drive.is_active = True if is_active_val == 'yes' else False
        
        deadline_str = request.form.get('application_deadline')
        
        try:
            new_deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
            if new_deadline < datetime.now().date():
                flash("Application deadline must be today or a future date.", "danger")
                return redirect(url_for('edit_drive', drive_id=drive.id))
            
            drive.application_deadline = new_deadline
            db.session.commit()
            flash("Drive updated successfully.", "success")
            return redirect(url_for('company_dashboard'))
        except ValueError:
            flash("Invalid date format.", "danger")
            
    return render_template('company/edit_drive.html', drive=drive)

@app.route('/company/drive/<int:drive_id>/close', methods=['POST'])
@login_required
def close_drive(drive_id):
    if current_user.role != 'company': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id == current_user.company_profile.id:
        drive.status = 'closed'
        db.session.commit()
        flash("Drive closed.", "success")
    return redirect(url_for('company_dashboard'))

@app.route('/company/drive/<int:drive_id>/applications')
@login_required
def drive_applications(drive_id):
    if current_user.role != 'company': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    if drive.company_id != current_user.company_profile.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('company_dashboard'))
        
    return render_template('company/applications.html', drive=drive)

@app.route('/company/application/<int:application_id>')
@login_required
def review_application(application_id):
    if current_user.role != 'company': return redirect(url_for('index'))
    application = Application.query.get_or_404(application_id)
    if application.drive.company_id != current_user.company_profile.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('company_dashboard'))
    return render_template('company/review_application.html', application=application)

@app.route('/company/application/<int:application_id>/update_status', methods=['POST'])
@login_required
def update_application_status(application_id):
    if current_user.role != 'company': return redirect(url_for('index'))
    application = Application.query.get_or_404(application_id)
    if application.drive.company_id != current_user.company_profile.id:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('company_dashboard'))
        
    new_status = request.form.get('status')
    if new_status in ['applied', 'shortlisted', 'waiting', 'selected', 'rejected', 'placed']:
        if application.status != new_status:
            application.status = new_status
            
            # generating a notificarion for the student
            message = f"Your application for {application.drive.job_title} at {application.drive.company.company_name} has been {new_status}."
            notification = Notification(user_id=application.student.user_id, message=message)
            db.session.add(notification)
            
            db.session.commit()
            
            category = "success"
            if new_status == 'waiting':
                category = "warning"
            elif new_status == 'rejected':
                category = "danger"
                
            flash(f"Application status updated to {new_status}.", category)
        
    return redirect(url_for('drive_applications', drive_id=application.drive_id))

@app.route('/student')
@login_required
def student_dashboard():
    if current_user.role != 'student': return redirect(url_for('index'))
    companies = CompanyProfile.query.join(User).filter(
        User.is_active == True,
        CompanyProfile.approval_status == 'approved'
    ).all()
    applications = current_user.student_profile.applications
    return render_template('student/dashboard.html', companies=companies, applications=applications)

@app.route('/student/drives')
@login_required
def student_drives():
    if current_user.role != 'student': return redirect(url_for('index'))
    
    query = request.args.get('q', '')
    if query:
        drives = PlacementDrive.query.join(CompanyProfile).filter(
            PlacementDrive.status == 'approved',
            db.or_(
                CompanyProfile.company_name.contains(query),
                PlacementDrive.job_title.contains(query),
                PlacementDrive.required_skills.contains(query)
            )
        ).all()
    else:
        drives = PlacementDrive.query.filter_by(status='approved').all()
    
    # getting the IDs of drives student has already applied to
    applied_drive_ids = [app.drive_id for app in current_user.student_profile.applications]
    
    return render_template('student/drives.html', drives=drives, applied_drive_ids=applied_drive_ids, query=query)

@app.route('/student/company/<int:company_id>')
@login_required
def student_company_details(company_id):
    if current_user.role != 'student': return redirect(url_for('index'))
    company = CompanyProfile.query.get_or_404(company_id)
    return render_template('student/company_overview.html', company=company)

@app.route('/student/drive/<int:drive_id>')
@login_required
def student_drive_details(drive_id):
    if current_user.role != 'student': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    return render_template('student/drive_details.html', drive=drive)

@app.route('/student/drive/<int:drive_id>/apply', methods=['POST'])
@login_required
def apply_drive(drive_id):
    if current_user.role != 'student': return redirect(url_for('index'))
    drive = PlacementDrive.query.get_or_404(drive_id)
    
    if drive.status != 'approved':
        flash("You can only apply to approved placement drives.", "danger")
        return redirect(url_for('student_drives'))
        
    if Application.query.filter_by(student_id=current_user.student_profile.id, drive_id=drive_id).first():
        flash("You have already applied for this drive.", "warning")
        return redirect(url_for('student_drives'))
        
    application = Application(
        student_id=current_user.student_profile.id,
        drive_id=drive_id,
        status='applied'
    )
    db.session.add(application)
    db.session.commit()
    flash(f"Successfully applied for {drive.job_title} at {drive.company.company_name}.", "success")
    return redirect(url_for('student_applications'))

@app.route('/student/applications')
@login_required
def student_applications():
    if current_user.role != 'student': return redirect(url_for('index'))
    applications = current_user.student_profile.applications
    return render_template('student/applications.html', applications=applications)

@app.route('/student/profile', methods=['GET', 'POST'])
@login_required
def student_profile():
    if current_user.role != 'student': return redirect(url_for('index'))
    profile = current_user.student_profile
    
    if request.method == 'POST':
        profile.name = request.form.get('name')
        profile.contact = request.form.get('contact')
        profile.education = request.form.get('education')
        profile.skills = request.form.get('skills')
        
        resume_file = request.files.get('resume')
        if resume_file and resume_file.filename:
            filename = secure_filename(resume_file.filename)
            resume_filename = f"{profile.student_roll_id}_{filename}"
            resume_file.save(os.path.join(app.config['UPLOAD_FOLDER'], resume_filename))
            profile.resume_filename = resume_filename
            
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for('student_profile'))
        
    return render_template('student/profile.html', profile=profile)

@app.route('/student/notifications')
@login_required
def student_notifications():
    if current_user.role != 'student': return redirect(url_for('index'))
    
    notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.timestamp.desc()).all()
    
    # markz all unread as read when they are viewed by student
    for notif in notifications:
        if not notif.is_read:
            notif.is_read = True
    db.session.commit()
    
    return render_template('student/notifications.html', notifications=notifications)

@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

from flask import jsonify

# --- API ROUTES (Milestone 1) ---

@app.route('/api/companies', methods=['GET'])
def api_get_companies():
    companies = CompanyProfile.query.filter_by(approval_status='approved').all()
    data = []
    for c in companies:
        data.append({
            'id': c.id,
            'company_name': c.company_name,
            'industry': c.industry,
            'website': c.website
        })
    return jsonify({'companies': data, 'count': len(data)}), 200

@app.route('/api/students', methods=['GET'])
@login_required
def api_get_students():
    # Only admin can view all students via API for security
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403
    students = StudentProfile.query.all()
    data = []
    for s in students:
        data.append({
            'id': s.id,
            'name': s.name,
            'roll_id': s.student_roll_id,
            'contact': s.contact
        })
    return jsonify({'students': data, 'count': len(data)}), 200

@app.route('/api/jobs', methods=['GET'])
def api_get_jobs():
    drives = PlacementDrive.query.filter_by(status='approved').all()
    data = []
    for d in drives:
        data.append({
            'id': d.id,
            'title': d.job_title,
            'company': d.company.company_name,
            'experience_required': d.experience,
            'salary': d.salary_range,
            'deadline': d.application_deadline.strftime('%Y-%m-%d')
        })
    return jsonify({'jobs': data, 'count': len(data)}), 200

@app.route('/api/applications', methods=['POST'])
@login_required
def api_create_application():
    if current_user.role != 'student':
        return jsonify({'error': 'Only students can apply via API'}), 403
        
    data = request.get_json()
    if not data or 'drive_id' not in data:
        return jsonify({'error': 'Missing drive_id in request body'}), 400
        
    drive_id = data.get('drive_id')
    drive = PlacementDrive.query.get(drive_id)
    if not drive or drive.status != 'approved':
        return jsonify({'error': 'Invalid or closed placement drive'}), 400
        
    if Application.query.filter_by(student_id=current_user.student_profile.id, drive_id=drive_id).first():
        return jsonify({'error': 'Already applied for this drive'}), 400
        
    application = Application(
        student_id=current_user.student_profile.id,
        drive_id=drive_id,
        status='applied'
    )
    db.session.add(application)
    db.session.commit()
    
    return jsonify({'message': 'Application submitted successfully', 'application_id': application.id}), 201

if __name__ == '__main__':
    app.run(debug=True)
