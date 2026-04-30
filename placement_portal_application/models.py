from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'admin', 'company', 'student'
    is_active = db.Column(db.Boolean, default=True) # for blacklistingz

    # relationshipz
    company_profile = db.relationship('CompanyProfile', back_populates='user', uselist=False, cascade="all, delete-orphan")
    student_profile = db.relationship('StudentProfile', back_populates='user', uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship('Notification', back_populates='user', cascade="all, delete-orphan")

class CompanyProfile(db.Model):
    __tablename__ = 'company_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    company_name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(100), nullable=True)
    hr_contact = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(150), nullable=True)
    approval_status = db.Column(db.String(20), default='pending') # pending, approved, rejected

    user = db.relationship('User', back_populates='company_profile')
    drives = db.relationship('PlacementDrive', back_populates='company', cascade="all, delete-orphan")

class StudentProfile(db.Model):
    __tablename__ = 'student_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    student_roll_id = db.Column(db.String(50), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(50), nullable=False)
    resume_filename = db.Column(db.String(200), nullable=True) # filename storing code here in this line.........
    education = db.Column(db.Text, nullable=True)
    skills = db.Column(db.Text, nullable=True)
    
    user = db.relationship('User', back_populates='student_profile')
    applications = db.relationship('Application', back_populates='student', cascade="all, delete-orphan")

class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_profiles.id'), nullable=False)
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    eligibility_criteria = db.Column(db.Text, nullable=False)
    required_skills = db.Column(db.String(255), nullable=True)
    experience = db.Column(db.String(100), nullable=True)
    salary_range = db.Column(db.String(100), nullable=True)
    application_deadline = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='pending') # pending, approved, rejected, closed
    
    company = db.relationship('CompanyProfile', back_populates='drives')
    applications = db.relationship('Application', back_populates='drive', cascade="all, delete-orphan")


class JobPosition(db.Model):
    __tablename__ = 'job_positions'
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company_profiles.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    company = db.relationship('CompanyProfile', backref='job_positions')

class Application(db.Model):
    __tablename__ = 'applications'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student_profiles.id'), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey('placement_drives.id'), nullable=False)
    application_date = db.Column(db.DateTime, default=datetime.now)
    status = db.Column(db.String(20), default='applied') # applied, shortlisted, selected, rejected

    student = db.relationship('StudentProfile', back_populates='applications')
    drive = db.relationship('PlacementDrive', back_populates='applications')
    
    # one-to-one relationzhip to Placement...
    placement = db.relationship('Placement', back_populates='application', uselist=False, cascade="all, delete-orphan")

class Placement(db.Model):
    __tablename__ = 'placements'
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('applications.id'), nullable=False, unique=True)
    placement_date = db.Column(db.DateTime, default=datetime.now)
    package_offered = db.Column(db.String(100), nullable=True)
    
    application = db.relationship('Application', back_populates='placement')

class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', back_populates='notifications')
