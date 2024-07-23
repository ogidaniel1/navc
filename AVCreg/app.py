import os
from flask_wtf import CSRFProtect, FlaskForm
from datetime import datetime, timezone
import humanize
from sqlalchemy.exc import IntegrityError
from flask_jwt_extended import jwt_required, get_jwt_identity
from wtforms.validators import DataRequired, Email, EqualTo,Length,ValidationError,Optional,Regexp
from flask_wtf.csrf import generate_csrf, validate_csrf,CSRFError
from wtforms import SubmitField
from wtforms import StringField, SubmitField, FloatField,PasswordField,SelectField
from wtforms.validators import DataRequired
from flask import Flask, render_template, request, redirect, url_for, flash,jsonify, abort,session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin,login_manager,current_user
from Crypto.Hash import SHA256
from flask_migrate import Migrate
from werkzeug.datastructures import MultiDict
from alembic import op
import json
from sqlalchemy import ForeignKey
from functools import wraps
import pandas as pd
import pymysql, logging


# from utils import load_config, generate_db_uri
 

# from app import User, Admin  # Ensure these are imported from your app
#pip install pycryptodome
# from pycryptodome.Hash import *

import pandas as pd
import joblib
import pickle, sqlite3
import random, time
from datetime import timedelta


app = Flask(__name__)
#incase of deployment to live server
application = app

#sqlite3 flask default db
app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'


#connecting to an external database.
# Store database credentials in environment variables
# app.config['SECRET_KEY'] = 'english92'
# app.config['SQLALCHEMY_DATABASE_URI'] = generate_db_uri()
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
#     "pool_pre_ping": True,
#     "pool_recycle": 250
# }


db = SQLAlchemy(app)
# csrf = CSRFProtect(app)
# csrf.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


#10 digit codes for the prediction aprroval page

def generate_unique_code():
    return random.randint(1000000000, 9999999999)


class DeleteUserForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Delete User')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

    @classmethod
    def from_json(cls, data):
        # Implement logic to create a LoginForm object from JSON data
        # For example:
        email = data.get('email')
        password = data.get('password')
        return cls(email=email, password=password)
    


class RegistrationForm(FlaskForm):
    class Meta:
        csrf = True
    business_name = StringField('Business Name', validators=[Optional(), Length(min=2, max=100)])
    business_project = StringField('Business Type', validators=[Optional(), Length(min=2, max=100)])
    position = StringField('Position', validators=[Optional(), Length(min=2, max=100)])
    value_chain_cat = SelectField('Value Chain Category', choices=[('PRE-UPSTREAM', 'Pre-Upstream'), ('UPSTREAM', 'Upstream'),('MIDSTREAM', 'Midstream'), ('DOWNSTREAM', 'Downstream')], validators=[Optional()])
    contact_person = StringField('Contact Person', validators=[DataRequired(), Length(min=10, max=100)])
    business_address = StringField('Business Address', validators=[Optional(), Length(min=5, max=100)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=15), Regexp(regex='^\d+$', message="Phone number must contain only digits")])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=100)])
    state = SelectField('State', choices=[
        ('Abia', 'Abia'), ('Adamawa', 'Adamawa'), ('Akwa Ibom', 'Akwa Ibom'), 
        ('Anambra', 'Anambra'), ('Bauchi', 'Bauchi'), ('Bayelsa', 'Bayelsa'), 
        ('Benue', 'Benue'), ('Borno', 'Borno'), ('Cross River', 'Cross River'), 
        ('Delta', 'Delta'), ('Ebonyi', 'Ebonyi'), ('Edo', 'Edo'), ('Ekiti', 'Ekiti'), 
        ('Enugu', 'Enugu'), ('Gombe', 'Gombe'), ('Imo', 'Imo'), ('Jigawa', 'Jigawa'), 
        ('Kaduna', 'Kaduna'), ('Kano', 'Kano'), ('Katsina', 'Katsina'), ('Kebbi', 'Kebbi'), 
        ('Kogi', 'Kogi'), ('Kwara', 'Kwara'), ('Lagos', 'Lagos'), ('Nasarawa', 'Nasarawa'), 
        ('Niger', 'Niger'), ('Ogun', 'Ogun'), ('Ondo', 'Ondo'), ('Osun', 'Osun'), 
        ('Oyo', 'Oyo'), ('Plateau', 'Plateau'), ('Rivers', 'Rivers'), ('Sokoto', 'Sokoto'), 
        ('Taraba', 'Taraba'), ('Yobe', 'Yobe'), ('Zamfara', 'Zamfara'), ('FCT', 'FCT')
    ], validators=[DataRequired()])
    value_chain_cat = StringField('Value Chain Category', validators=[Optional(), Length(max=100)])
    proposed_next_steps = StringField('Proposed Next steps', validators=[Optional()])
    challenges = StringField('Challenges', validators=[Optional()])
    submit = SubmitField('Register')


def validate_email(self, field):
        if not field.data.endswith('@nrs.com'):
            raise ValidationError('Email must have the domain "@nrs.com".')

class RegisterAdminForm(FlaskForm):

    admin_name = StringField('Name', validators=[DataRequired(), Length(min=2, max=50)])
    admin_address = StringField('Address', validators=[DataRequired(), Length(min=2, max=100)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), Length(max=15), Regexp(regex='^\d+$', message="Phone number must contain only digits")])
    email = StringField('Email', validators=[DataRequired(), Email(), validate_email])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password', message="Password mismatch")])
    submit = SubmitField('Register')
   

#The User class defines the database model.
# User model with explicit foreign keys

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(100), nullable=True)
    business_project = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(100), nullable=True)
    contact_person = db.Column(db.String(100), nullable=False)
    business_address = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(15), nullable=False)
    email = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=False)
    value_chain_cat = db.Column(db.String(100), nullable=True)
    proposed_next_steps = db.Column(db.String(100), nullable=True, default="-")
    challenges = db.Column(db.String(100), nullable=True, default="-") 
    registered_by_admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=True)
    last_edited_by = db.Column(db.Integer, nullable=True)
    # Relationships
    registered_by_admin = db.relationship('Admin', backref='registered_users')
    last_edited_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)



class DeletionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    admin_id = db.Column(db.Integer, ForeignKey('user.id'), nullable=False)
    deleted_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_info = db.Column(db.Text, nullable=False)


class SearchForm(FlaskForm):
    search_term = StringField('Search Term', validators=[DataRequired()])
    submit = SubmitField('Search')


class Admin(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    admin_name = db.Column(db.String(150), nullable=False)
    admin_address = db.Column(db.String(150), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)



#logged out session................
@app.before_request
def before_request():
    session.permanent = True
    app.permanent_session_lifetime = timedelta(minutes=20)
    session.modified = True
    session['last_activity'] = time.time()

@app.route('/check_activity', methods=['POST'])
def check_activity():
    if 'last_activity' in session:
        last_activity = session['last_activity']
        current_time = time.time()
        if current_time - last_activity > 1200:
            session.clear()
            return jsonify({'message': 'Session expired due to inactivity'}), 401
    return jsonify({'message': 'Activity checked'}), 200


#wrapper................ normal user for login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('You need to be logged in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


#wrapper................for admin login
# Admin required decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or not session.get('is_admin'):
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function




#edited endpoint....

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    form = RegistrationForm()
    user = User.query.get_or_404(user_id)
    admins = Admin.query.all()  # Fetch all admin details
    current_user_id = session['is_admin']  # Get the current user ID
    
    # Check if current user is admin
    if not session['is_admin']:
        abort(403)  # Forbidden

    if request.method == 'POST':
        try:
            # Update user information by admin officer
            user.challenges = request.form.get('challenges') 
            # Level 2 (registration page)
            user.business_name = request.form.get('business_name') or None
            user.position = request.form.get('position') or None
            user.contact_person = request.form.get('contact_person') or None
            user.business_address = request.form.get('business_address') or None
            user.phone_number = request.form.get('phone_number') or None
            user.email = request.form.get('email') or None
            user.state = request.form.get('state') or None
            # Level 3 (prediction page)
            user.business_project = request.form.get('business_project') or None
            user.proposed_next_steps = request.form.get('proposed_next_steps') or None
            user.value_chain_cat = request.form.get('value_chain_cat') or None

            # Log the admin who edited the user
            user.last_edited_by = session['user_id']
            user.last_edited_at = datetime.now(timezone.utc)  # Store the current UTC time

            db.session.commit()
            flash('User information updated successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
        except IntegrityError:
            db.session.rollback()  # Rollback the session to avoid a partially committed transaction
            flash('Error: Failed to update user information. Please ensure all required fields are filled.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Error: {str(e)}', 'danger')

    admins = Admin.query.all()
    # Ensure last_edited_at is offset-aware for humanize.naturaltime
    if user.last_edited_at:
        user_last_edited_at = user.last_edited_at if user.last_edited_at.tzinfo else user.last_edited_at.replace(tzinfo=timezone.utc)
        humanized_last_edited_at = humanize.naturaltime(datetime.now(timezone.utc) - user_last_edited_at)
    else:
        humanized_last_edited_at = 'Never'

    return render_template('edit_user.html', user=user, admins=admins, form=form,current_user_id=current_user_id,humanized_last_edited_at=humanized_last_edited_at)



#delete route............
# Base form with CSRF protection enabled
class MyBaseForm(FlaskForm):
    class Meta:
        csrf = False

# Form for deleting a user
class DeleteUserForm(MyBaseForm):
    submit = SubmitField('Delete')

@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    form = DeleteUserForm()
    
    if request.method == 'POST':
        # Create a log entry before deleting the user
        deletion_log = DeletionLog(
            user_id=user.id,
            admin_id=session['user_id'],
            user_info=json.dumps({
                'business_name': user.business_name,
                'contact_person': user.contact_person,
                'position': user.position,
                'proposed_next_steps': user.proposed_next_steps,
                'business_address': user.business_address,
                'phone_number': user.phone_number,
                'email': user.email,
                'state': user.state,
                'challenges': user.challenges,
                'business_project': user.business_project,
                'value_chain_cat': user.value_chain_cat
            })
        )

        try:
            db.session.add(deletion_log)
            db.session.delete(user)
            db.session.commit()
            flash('User deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error deleting user: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))

    return render_template('confirm.html', user=user, form=form)



# #homepage route...........
@app.route("/", methods=['GET', 'POST'])
def home():
        
        return redirect(url_for('login'))
        # return render_template("login.html")

#The /register route handles user registration, hashing the password before storing it.
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    form = RegistrationForm()
    
    if form.validate_on_submit():
        try:
            business_name = form.business_name.data
            business_address = form.business_address.data
            position = form.position.data
            phone_number = form.phone_number.data
            contact_person = form.contact_person.data
            email = form.email.data
            state = form.state.data
            # Additional fields
            business_project = form.business_project.data
            value_chain_cat = form.value_chain_cat.data
            challenges = form.challenges.data
            proposed_next_steps = form.proposed_next_steps.data

            # Check for existing user
            if User.query.filter_by(email=email).first():
                flash('Email already registered!', 'danger')
                return redirect(url_for('register'))
            # if User.query.filter_by(business_name=business_name).first():
            #     flash('Business Name already registered!', 'danger')
            #     return redirect(url_for('register'))
            if User.query.filter_by(phone_number=phone_number).first():
                flash('Business Name already registered!', 'danger')
                return redirect(url_for('register'))

            # Create and save new user
            new_user = User(
                business_name=business_name,
                business_address=business_address,
                position = position,
                phone_number=phone_number,
                contact_person=contact_person,
                email=email,
                state=state,
                business_project=business_project,
                value_chain_cat=value_chain_cat,
                challenges=challenges,
                proposed_next_steps=proposed_next_steps,
                registered_by_admin_id= session['user_id']  # Capture the current admin's ID
                 
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful!', 'success')
            return redirect(url_for('register'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'danger')
            return redirect(url_for('register'))

    # Render form with validation errors (if any)
    return render_template('register.html', form=form)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()
    if form.validate_on_submit():
        # Clear any existing session data
        session.clear()
        email = form.email.data
        password = form.password.data
        # Check for user login
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['is_admin'] = False
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        
        # Check for admin login
        admin = Admin.query.filter_by(email=email).first()
        if admin and check_password_hash(admin.password, password):
            session['user_id'] = admin.id
            session['email'] = admin.email
            session['is_admin'] = True
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        
        # If login fails
        flash('Login failed. Check your credentials and try again.', 'danger')
    
    return render_template('login.html', form=form)

#admin.............route

@app.route('/admin_dashboard', methods=['GET', 'POST'])
@admin_required
def admin_dashboard():
    form = RegistrationForm()
    search_form = SearchForm()  # Assuming you have a SearchForm class for the search functionality
    
    # Handle search form submission
    if search_form.validate_on_submit():
        search_term = search_form.search_term.data
        user = User.query.filter((User.id == search_term) | (User.email == search_term)).first()
        if user:
            return render_template('admin_dashboard.html', form=form, search_form=search_form, user=user)
        else:
            flash('User not found', 'danger')
            return render_template('admin_dashboard.html', form=form, search_form=search_form)
    
    return render_template('admin_dashboard.html', form=form, search_form=search_form)
 
# Admin registration route
@app.route('/register_admin', methods=['GET', 'POST'])
# @admin_required
def register_admin():

    form = RegisterAdminForm()
    if form.validate_on_submit():
        admin_name = form.admin_name.data
        admin_address = form.admin_address.data
        phone_number = form.phone_number.data
        email = form.email.data
        password = form.password.data
        confirm_password = generate_password_hash(password)
        is_admin = True  # Ensure the new user is an admin

        # Check if user email already exists
        existing_admin = Admin.query.filter_by(email=email).first()
        if existing_admin:
            flash('Email already registered!', 'danger')
            return redirect(url_for('register_admin'))

        existing_admin = Admin.query.filter_by(admin_name=admin_name).first()
        if existing_admin:
            flash('Admin already registered!', 'danger')
            return redirect(url_for('register_admin'))
        
        existing_admin = Admin.query.filter_by(phone_number=phone_number).first()
        if existing_admin:
            flash('Admin already registered!', 'danger')
            return redirect(url_for('register_admin'))

        # If no duplicates proceed...
        new_admin = Admin(
            admin_name=admin_name,
            admin_address=admin_address,
            phone_number=phone_number,
            email=email,
            password=confirm_password,
            is_admin=is_admin
        )

        db.session.add(new_admin)
        db.session.commit()

        flash('New admin registered successfully!', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('register_admin.html', form=form)


# Logout route
@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))
    
#search.......#############....

@app.route('/search', methods=['GET', 'POST'])
@admin_required
def search():
    search_form = SearchForm()
    form = RegistrationForm()
    if search_form.validate_on_submit():
        search_term = search_form.search_term.data
        user = User.query.filter((User.phone_number == search_term) | (User.email == search_term)).first()
        if user:
            return render_template('admin_dashboard.html', form=form, search_form=search_form, user=user)
        else:
            flash('No user found with that phone number or email.', 'danger')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin_dashboard.html', form=form, search_form=search_form)



#users route 
@app.route('/users')
@admin_required
def show_users():
    users = User.query.all()
    admins = Admin.query.all()
    for user in users:
        print(f"Registered by Admin ID: {user.registered_by_admin_id}")
    return render_template('users.html', users=users, admins=admins) 
 

#show all admins in table route 
@app.route('/admins')
@admin_required
def show_admins():
    admins = Admin.query.all()
    return render_template('admins.html', admins=admins)
   
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)


