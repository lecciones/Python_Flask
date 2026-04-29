from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import random
import string
import os
import secrets
from functools import wraps
import json

# ==================== APP CONFIGURATION ====================
app = Flask(__name__)
app.secret_key = 'aeroticket_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aeroticket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Upload folder for profile pictures
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ==================== ADMIN DECORATOR ====================
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({'error': 'Login required'}), 401
        return f(*args, **kwargs)
    return decorated_function

# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'all_users' 
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) 
    provider = db.Column(db.String(20), default='email')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    phone = db.Column(db.String(20), nullable=True)
    email_reminders = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    profile_picture = db.Column(db.String(200), nullable=True)

    def __repr__(self):
        return f'<User {self.email}>'
    
class SocialUser(db.Model):
    __tablename__ = 'social_users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=False) 
    provider = db.Column(db.String(20), nullable=False) 
    fullname = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    __table_args__ = (db.UniqueConstraint('email', 'provider', name='_email_provider_uc'),)

    def __repr__(self):
        return f'<SocialUser {self.email}>'

class Flight(db.Model):
    __tablename__ = 'flights'
    id = db.Column(db.Integer, primary_key=True)
    flight_number = db.Column(db.String(10), nullable=False, unique=True)
    origin = db.Column(db.String(50), nullable=False)
    destination = db.Column(db.String(50), nullable=False)
    departure_date = db.Column(db.String(20), nullable=False)
    departure_time = db.Column(db.String(10), nullable=False)
    arrival_time = db.Column(db.String(10), nullable=False)
    duration = db.Column(db.String(10), nullable=False)
    distance = db.Column(db.String(20), nullable=False)
    economy_price = db.Column(db.String(10), default="2,100")
    premium_economy_price = db.Column(db.String(10), default="4,500")
    business_price = db.Column(db.String(10), default="8,500")
    first_class_price = db.Column(db.String(10), default="15,000")
    total_seats = db.Column(db.Integer, default=60)
    available_seats = db.Column(db.Integer, default=60)
    gate = db.Column(db.String(5), default="A1")
    status = db.Column(db.String(20), default="Scheduled")
    
    def get_price_by_class(self, cabin_class):
        prices = {
            "Economy": self.economy_price,
            "Premium Economy": self.premium_economy_price,
            "Business/Premium Flatbed": self.business_price,
            "First Class": self.first_class_price
        }
        return prices.get(cabin_class, self.economy_price)

class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(10), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('all_users.id'), nullable=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    total_passengers = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.String(20), nullable=False)
    cabin_class = db.Column(db.String(30), nullable=False)
    status = db.Column(db.String(20), default="Confirmed")
    payment_method = db.Column(db.String(30), nullable=True)
    payment_status = db.Column(db.String(20), default="Pending")
    
    # ===== ADD THESE 2 LINES ONLY =====
    checked_in = db.Column(db.Boolean, default=False)
    check_in_time = db.Column(db.DateTime, nullable=True)
    
    user = db.relationship('User', backref='bookings')
    flight = db.relationship('Flight', backref='bookings')
    passengers = db.relationship('Passenger', backref='booking', cascade='all, delete-orphan')
    
    def generate_booking_reference(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Passenger(db.Model):
    __tablename__ = 'passengers'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    seat_number = db.Column(db.String(5), nullable=False)
    passenger_type = db.Column(db.String(20), default="Adult")

class Seat(db.Model):
    __tablename__ = 'seats'
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    seat_number = db.Column(db.String(5), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    cabin_class = db.Column(db.String(30), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    
    __table_args__ = (db.UniqueConstraint('flight_id', 'seat_number', name='_flight_seat_uc'),)

class PromoCode(db.Model):
    __tablename__ = 'promo_codes'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200), nullable=True)
    discount_type = db.Column(db.String(20), nullable=False)
    discount_value = db.Column(db.Float, nullable=False)
    valid_from = db.Column(db.DateTime, default=datetime.utcnow)
    valid_until = db.Column(db.DateTime, nullable=False)
    max_uses = db.Column(db.Integer, nullable=True)
    min_amount = db.Column(db.Float, nullable=True)
    used_count = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SystemSetting(db.Model):
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# ==================== PAYMENT METHODS ====================
payment_methods = [
    {"name": "GCash", "logo": "images/gcash.png"},
    {"name": "Paytm", "logo": "https://upload.wikimedia.org/wikipedia/commons/2/24/Paytm_Logo_%28standalone%29.svg"},
    {"name": "Google Pay", "logo": "https://upload.wikimedia.org/wikipedia/commons/f/f2/Google_Pay_Logo.svg"},
    {"name": "PayPal", "logo": "https://upload.wikimedia.org/wikipedia/commons/b/b5/PayPal.svg"},
    {"name": "GrabPay", "logo": "images/grab.png"},
    {"name": "Atome", "logo": "images/atome.png"},
    {"name": "Alipay", "logo": "images/alipay.png"},
    {"name": "Apple Pay", "logo": "https://upload.wikimedia.org/wikipedia/commons/b/b0/Apple_Pay_logo.svg"},
    {"name": "Hoolah", "logo": "images/hoolah.png"},
    {"name": "OVO", "logo": "images/ovo.png"}
]

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_system_setting(key, default=None):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        return setting.value
    return default

def set_system_setting(key, value):
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = str(value)
        setting.updated_at = datetime.utcnow()
    else:
        setting = SystemSetting(key=key, value=str(value))
        db.session.add(setting)
    db.session.commit()

def normalize_email_for_gmail(email):
    """Normalize Gmail addresses to handle dots and googlemail.com"""
    if not email:
        return email
    email = email.lower().strip()
    
    if '@googlemail.com' in email:
        email = email.replace('@googlemail.com', '@gmail.com')
    
    if '@gmail.com' in email:
        local_part, domain = email.split('@')
        normalized_local = local_part.replace('.', '')
        email = normalized_local + '@' + domain
    
    return email

def create_sample_flights():
    if Flight.query.count() == 0:
        sample_flights = [
            Flight(flight_number="AT1001", origin="MANILA", destination="CEBU",
                   departure_date="15 JAN 2026", departure_time="06:00", arrival_time="07:30",
                   duration="1h 30m", distance="566 km", gate="A1"),
            Flight(flight_number="AT1002", origin="CEBU", destination="MANILA",
                   departure_date="15 JAN 2026", departure_time="08:00", arrival_time="09:30",
                   duration="1h 30m", distance="566 km", gate="B2"),
            Flight(flight_number="AT1003", origin="MANILA", destination="DAVAO",
                   departure_date="15 JAN 2026", departure_time="09:00", arrival_time="10:50",
                   duration="1h 50m", distance="964 km", gate="C3"),
            Flight(flight_number="AT1004", origin="DAVAO", destination="MANILA",
                   departure_date="15 JAN 2026", departure_time="11:00", arrival_time="12:55",
                   duration="1h 55m", distance="964 km", gate="D4"),
        ]
        db.session.add_all(sample_flights)
        db.session.commit()
        print("✅ Sample flights created!")

password_reset_tokens = {}

# ==================== MAIN ROUTES ====================

@app.route("/")
def home():
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template("Home_page.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== AUTHENTICATION ROUTES ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        step = request.form.get("step") 
        email = request.form.get("email")
        password = request.form.get("password")

        if step == "email":
            user = User.query.filter_by(email=email).first()
            if not user:
                flash("No account found with that email.")
                return render_template("Login_form.html", step="email")
            return render_template("Login_form.html", step="password", email=email)

        user = User.query.filter_by(email=email).first()
        if user and user.is_active and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            session['show_success_popup'] = "Login successful! Welcome back!"
            return redirect(url_for("home"))
        
        flash("Invalid email or password.")
        return render_template("Login_form.html", step="password" if step == "password" else "email", email=email)

    return render_template("Login_form.html", step="email", has_bookings=False, latest_booking_id=None)

@app.route("/register", methods=["POST"])
def register():
    provider = request.form.get("provider", "email")
    email = request.form.get("email")
    password = request.form.get("password")
    fullname = request.form.get("fullname") 

    if not email or not password:
        flash("Email and Password are required.")
        return redirect(url_for("signup")) 

    user_exists = User.query.filter_by(email=email).first()
    
    if not user_exists:
        hashed_password = generate_password_hash(password)
        new_user = User(fullname=fullname if fullname else None, email=email, 
                       password=hashed_password, provider=provider, is_active=True)
        db.session.add(new_user)
        db.session.commit()
        session['show_success_popup'] = "Account created successfully! Please log in."
        return redirect(url_for("login")) 
    
    flash("Account already exists. Try logging in.")
    return redirect(url_for("login"))

@app.route('/signup')
def signup():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    has_bookings = False
    latest_booking_id = None
    
    return render_template('signup.html', 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== GOOGLE LOGIN ====================
@app.route('/login/google', methods=['GET', 'POST'])
def google_login():
    mode = request.args.get('mode', 'login')
    
    if request.method == 'POST':
        mode = request.form.get("mode", "login")
        step = request.form.get("step")
        email = request.form.get("email")
        password = request.form.get("password")

        if mode == "login":
            if step == "email":
                user = SocialUser.query.filter_by(email=email, provider='google').first()
                if not user:
                    flash("No account found with that email. Please sign up first.")
                    return render_template("google.html", mode='login', email=email)
                return render_template("google_log.html", mode='login', email=email)
                
            elif step == "password":
                user = SocialUser.query.filter_by(email=email, provider='google').first()
                if user and check_password_hash(user.password, password):
                    session['user_id'] = user.id
                    session['auth_type'] = 'google'
                    session['is_admin'] = False
                    session['show_success_popup'] = "Login successful! Welcome back!"
                    return redirect(url_for('home'))
                else:
                    flash("Wrong password. Please try again.")
                    return render_template("google_log.html", mode='login', email=email)
        
        else:
            if step == "email":
                user = SocialUser.query.filter_by(email=email, provider='google').first()
                if user:
                    flash("Account already exists. Please log in instead.")
                    return render_template("google.html", mode='signup', email=email)
                return render_template("google_log.html", mode='signup', email=email)
                
            elif step == "password":
                user = SocialUser.query.filter_by(email=email, provider='google').first()
                if user:
                    flash("Account already exists. Please log in instead.")
                    return render_template("google_log.html", mode='signup', email=email)
                
                hashed_pw = generate_password_hash(password)
                new_google_user = SocialUser(
                    email=email, 
                    fullname=email.split('@')[0],
                    password=hashed_pw, 
                    provider='google'
                )
                db.session.add(new_google_user)
                db.session.commit()
                session['show_success_popup'] = "Google account created successfully! Please log in."
                return redirect(url_for('login'))
    
    return render_template('google.html', mode=mode)

# ==================== APPLE LOGIN ====================
@app.route('/login/apple', methods=['GET', 'POST'])
def apple_login():
    mode = request.args.get('mode', 'login')
    
    if request.method == 'POST':
        mode = request.form.get("mode", "login")
        email = request.form.get("apple_email")
        password = request.form.get("apple_password")
        
        if mode == "login":
            user = SocialUser.query.filter_by(email=email, provider='apple').first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['auth_type'] = 'apple'
                session['is_admin'] = False
                session['show_success_popup'] = "Login successful! Welcome back!"
                return redirect(url_for('home'))
            else:
                flash("Incorrect Apple ID password or account not found.")
                return render_template("apple.html", mode='login', email=email)
        
        else:
            existing_user = SocialUser.query.filter_by(email=email, provider='apple').first()
            if existing_user:
                flash("Account already exists. Please log in instead.")
                return render_template("apple.html", mode='signup', email=email)
            
            existing_main_user = User.query.filter_by(email=email).first()
            if existing_main_user:
                flash("An account with this email already exists. Please log in.")
                return render_template("apple.html", mode='signup', email=email)
            
            hashed_pw = generate_password_hash(password)
            new_user = SocialUser(
                email=email, 
                fullname=email.split('@')[0],
                password=hashed_pw, 
                provider='apple'
            )
            db.session.add(new_user)
            db.session.commit()
            session['show_success_popup'] = "Apple account created successfully! Please log in."
            return redirect(url_for('login'))
    
    return render_template("apple.html", mode=mode)

# ==================== WECHAT LOGIN ====================
@app.route('/login/wechat', methods=['GET', 'POST'])
def wechat_login():
    mode = request.args.get('mode', 'login')
    
    if request.method == 'POST':
        mode = request.form.get("mode", "login")
        email = request.form.get("wechat_email")
        password = request.form.get("password")
        
        if mode == "login":
            user = SocialUser.query.filter_by(email=email, provider='wechat').first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['auth_type'] = 'wechat'
                session['is_admin'] = False
                session['show_success_popup'] = "Welcome back!"
                return redirect(url_for('home'))
            else:
                flash("Incorrect password or account not found.")
                return render_template('wechat.html', mode='login', email=email)
        
        else:
            existing_user = SocialUser.query.filter_by(email=email, provider='wechat').first()
            if existing_user:
                flash("Account already exists. Please log in instead.")
                return render_template('wechat.html', mode='signup', email=email)
            
            existing_main_user = User.query.filter_by(email=email).first()
            if existing_main_user:
                flash("An account with this email already exists. Please log in.")
                return render_template('wechat.html', mode='signup', email=email)
            
            hashed_pw = generate_password_hash(password)
            new_wechat_user = SocialUser(
                email=email, 
                fullname=email.split('@')[0],
                password=hashed_pw, 
                provider='wechat'
            )
            try:
                db.session.add(new_wechat_user)
                db.session.commit()
                session['show_success_popup'] = "WeChat account created successfully! Please log in."
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash("An error occurred. Please try again.")
                return render_template('wechat.html', mode='signup', email=email)
    
    return render_template('wechat.html', mode=mode)

@app.route('/signup/wechat')
def wechat_signup():
    return render_template('wechat.html', mode='signup')

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    session.pop('is_admin', None)
    session['show_success_popup'] = "Logged out successfully."
    return redirect(url_for("home"))

# ==================== PASSWORD RESET ROUTES ====================

@app.route('/request-password-reset', methods=['POST'])
def request_password_reset():
    data = request.get_json()
    email = data.get('email', '').strip()
    
    if not email:
        return jsonify({'success': False, 'message': 'Email is required.'}), 400
    
    user = User.query.filter_by(email=email).first()
    social_user = SocialUser.query.filter_by(email=email).first()
    
    if not user and not social_user:
        return jsonify({'success': True, 'message': 'If an account exists, a reset link has been sent.'}), 200
    
    token = secrets.token_urlsafe(32)
    expires = datetime.utcnow() + timedelta(hours=1)
    
    password_reset_tokens[email] = {
        'token': token,
        'expires': expires,
        'user_type': 'email' if user else 'social',
        'provider': user.provider if user else (social_user.provider if social_user else 'unknown')
    }
    
    reset_link = url_for('reset_password_page', token=token, email=email, _external=True)
    
    print(f"\n🔐 PASSWORD RESET LINK FOR {email}:")
    print(f"   {reset_link}")
    
    return jsonify({
        'success': True, 
        'message': 'Password reset link sent! Check your console for the link.',
        'reset_link': reset_link
    }), 200

@app.route('/reset-password/<token>')
def reset_password_page(token):
    email = request.args.get('email', '')
    
    if email not in password_reset_tokens:
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for('login'))
    
    token_data = password_reset_tokens[email]
    if token_data['token'] != token or datetime.utcnow() > token_data['expires']:
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for('login'))
    
    return render_template('reset_password.html', email=email, token=token)

@app.route('/reset-password', methods=['POST'])
def reset_password():
    email = request.form.get('email')
    token = request.form.get('token')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if email not in password_reset_tokens:
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for('login'))
    
    token_data = password_reset_tokens[email]
    if token_data['token'] != token or datetime.utcnow() > token_data['expires']:
        flash("Invalid or expired reset link. Please request a new one.", "error")
        return redirect(url_for('login'))
    
    if not new_password or len(new_password) < 6:
        flash("Password must be at least 6 characters.", "error")
        return render_template('reset_password.html', email=email, token=token)
    
    if new_password != confirm_password:
        flash("Passwords do not match.", "error")
        return render_template('reset_password.html', email=email, token=token)
    
    hashed_pw = generate_password_hash(new_password)
    
    user = User.query.filter_by(email=email).first()
    if user:
        user.password = hashed_pw
        db.session.commit()
        del password_reset_tokens[email]
        session['show_success_popup'] = "Password reset successfully! Please log in with your new password."
        return redirect(url_for('login'))
    
    social_user = SocialUser.query.filter_by(email=email).first()
    if social_user:
        social_user.password = hashed_pw
        db.session.commit()
        del password_reset_tokens[email]
        session['show_success_popup'] = "Password reset successfully! Please log in with your new password."
        return redirect(url_for('login'))
    
    flash("User not found.", "error")
    return redirect(url_for('login'))

# ==================== PROMO CODE VALIDATION ====================

@app.route('/validate-promo', methods=['POST'])
def validate_promo():
    """Validate promo code - optional feature, returns discount if valid"""
    data = request.get_json()
    code = data.get('code', '').upper().strip()
    
    if not code:
        return jsonify({'valid': False, 'message': 'Please enter a promo code'})
    
    now = datetime.utcnow()
    promo = PromoCode.query.filter(
        PromoCode.code == code,
        PromoCode.is_active == True,
        PromoCode.valid_until >= now,
        PromoCode.valid_from <= now
    ).first()
    
    if not promo:
        return jsonify({'valid': False, 'message': 'Invalid or expired promo code'})
    
    if promo.max_uses and promo.used_count >= promo.max_uses:
        return jsonify({'valid': False, 'message': 'Promo code has reached maximum usage limit'})
    
    if promo.min_amount:
        # Note: amount check would need to be implemented with actual booking amount
        pass
    
    promo.used_count += 1
    db.session.commit()
    
    discount_message = f'{promo.discount_value}% OFF applied!' if promo.discount_type == 'percentage' else f'₱{promo.discount_value:,.2f} OFF applied!'
    
    return jsonify({
        'valid': True,
        'discount_type': promo.discount_type,
        'discount_value': promo.discount_value,
        'message': discount_message,
        'code': promo.code,
        'id': promo.id
    })

# ==================== FLIGHT BOOKING ROUTES ====================

@app.route("/flight")
def flight():
    search_origin = request.args.get('departure_code', '').lower().strip()
    if not search_origin:
        search_origin = request.args.get('departure', '').lower().strip()

    search_destination = request.args.get('arrival', '').lower().strip()

    if '→' in search_origin:
        parts = search_origin.split('→')
        search_origin = parts[0].strip()
        if not search_destination:
            search_destination = parts[-1].strip()

    selected_trip_type = request.args.get('trip_type', 'One-way')
    flight_date = request.args.get('date', '15 JAN 2026')
    flight_time = request.args.get('time', '06:30')

    passenger_data = {
        "adults": request.args.get('adults', 1),
        "children": request.args.get('children', 0),
        "infants": request.args.get('infants', 0),
        "cabin": request.args.get('cabin', 'Economy'),
        "trip_type": selected_trip_type
    }

    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id

    def format_ph_time(time_24):
        hour = int(time_24[:2])
        minute = time_24[3:]
        
        if hour == 0:
            hour_12 = 12
            period = "AM"
        elif hour < 12:
            hour_12 = hour
            period = "AM"
        elif hour == 12:
            hour_12 = 12
            period = "PM"
        else:
            hour_12 = hour - 12
            period = "PM"
        
        return f"{hour_12}:{minute} {period}"

    def get_gate_for_destination(destination):
        """Return gate based on destination"""
        gate_map = {
            "cebu": "A1",
            "manila": "B2", 
            "davao": "C3",
            "dubai": "D4",
            "hongkong": "E5",
            "singapore": "F6"
        }
        return gate_map.get(destination.lower(), "A1")

    # COMPLETE ROUTE DATA
    route_data = {
        ("cebu", "manila"): {
            "duration": "1h 25m", "distance": "566 km",
            "economy_oneway": "2,500", "premium_economy_oneway": "4,500", 
            "business_oneway": "7,500", "first_class_oneway": "12,000",
            "economy_roundtrip": "4,500", "premium_economy_roundtrip": "8,000",
            "business_roundtrip": "13,500", "first_class_roundtrip": "21,500"
        },
        ("manila", "cebu"): {
            "duration": "1h 30m", "distance": "566 km",
            "economy_oneway": "2,500", "premium_economy_oneway": "4,500",
            "business_oneway": "7,500", "first_class_oneway": "12,000",
            "economy_roundtrip": "4,500", "premium_economy_roundtrip": "8,000",
            "business_roundtrip": "13,500", "first_class_roundtrip": "21,500"
        },
        ("cebu", "davao"): {
            "duration": "1h 05m", "distance": "410 km",
            "economy_oneway": "2,200", "premium_economy_oneway": "4,000",
            "business_oneway": "6,500", "first_class_oneway": "10,000",
            "economy_roundtrip": "4,000", "premium_economy_roundtrip": "7,200",
            "business_roundtrip": "11,700", "first_class_roundtrip": "18,000"
        },
        ("davao", "cebu"): {
            "duration": "1h 10m", "distance": "410 km",
            "economy_oneway": "2,200", "premium_economy_oneway": "4,000",
            "business_oneway": "6,500", "first_class_oneway": "10,000",
            "economy_roundtrip": "4,000", "premium_economy_roundtrip": "7,200",
            "business_roundtrip": "11,700", "first_class_roundtrip": "18,000"
        },
        ("manila", "davao"): {
            "duration": "1h 50m", "distance": "964 km",
            "economy_oneway": "3,800", "premium_economy_oneway": "6,500",
            "business_oneway": "11,000", "first_class_oneway": "18,000",
            "economy_roundtrip": "6,800", "premium_economy_roundtrip": "11,700",
            "business_roundtrip": "19,800", "first_class_roundtrip": "32,400"
        },
        ("davao", "manila"): {
            "duration": "1h 55m", "distance": "964 km",
            "economy_oneway": "3,800", "premium_economy_oneway": "6,500",
            "business_oneway": "11,000", "first_class_oneway": "18,000",
            "economy_roundtrip": "6,800", "premium_economy_roundtrip": "11,700",
            "business_roundtrip": "19,800", "first_class_roundtrip": "32,400"
        },
        ("cebu", "dubai"): {
            "duration": "9h 00m", "distance": "6,889 km",
            "economy_oneway": "18,500", "premium_economy_oneway": "32,000",
            "business_oneway": "55,000", "first_class_oneway": "85,000",
            "economy_roundtrip": "33,300", "premium_economy_roundtrip": "57,600",
            "business_roundtrip": "99,000", "first_class_roundtrip": "153,000"
        },
        ("dubai", "cebu"): {
            "duration": "9h 30m", "distance": "6,889 km",
            "economy_oneway": "18,500", "premium_economy_oneway": "32,000",
            "business_oneway": "55,000", "first_class_oneway": "85,000",
            "economy_roundtrip": "33,300", "premium_economy_roundtrip": "57,600",
            "business_roundtrip": "99,000", "first_class_roundtrip": "153,000"
        },
        ("manila", "dubai"): {
            "duration": "8h 45m", "distance": "6,521 km",
            "economy_oneway": "17,500", "premium_economy_oneway": "30,000",
            "business_oneway": "52,000", "first_class_oneway": "80,000",
            "economy_roundtrip": "31,500", "premium_economy_roundtrip": "54,000",
            "business_roundtrip": "93,600", "first_class_roundtrip": "144,000"
        },
        ("dubai", "manila"): {
            "duration": "9h 00m", "distance": "6,521 km",
            "economy_oneway": "17,500", "premium_economy_oneway": "30,000",
            "business_oneway": "52,000", "first_class_oneway": "80,000",
            "economy_roundtrip": "31,500", "premium_economy_roundtrip": "54,000",
            "business_roundtrip": "93,600", "first_class_roundtrip": "144,000"
        },
        ("davao", "dubai"): {
            "duration": "9h 30m", "distance": "7,200 km",
            "economy_oneway": "19,500", "premium_economy_oneway": "34,000",
            "business_oneway": "58,000", "first_class_oneway": "90,000",
            "economy_roundtrip": "35,100", "premium_economy_roundtrip": "61,200",
            "business_roundtrip": "104,400", "first_class_roundtrip": "162,000"
        },
        ("dubai", "davao"): {
            "duration": "10h 00m", "distance": "7,200 km",
            "economy_oneway": "19,500", "premium_economy_oneway": "34,000",
            "business_oneway": "58,000", "first_class_oneway": "90,000",
            "economy_roundtrip": "35,100", "premium_economy_roundtrip": "61,200",
            "business_roundtrip": "104,400", "first_class_roundtrip": "162,000"
        },
        ("cebu", "hongkong"): {
            "duration": "2h 10m", "distance": "1,145 km",
            "economy_oneway": "6,500", "premium_economy_oneway": "11,000",
            "business_oneway": "18,000", "first_class_oneway": "28,000",
            "economy_roundtrip": "11,700", "premium_economy_roundtrip": "19,800",
            "business_roundtrip": "32,400", "first_class_roundtrip": "50,400"
        },
        ("hongkong", "cebu"): {
            "duration": "2h 20m", "distance": "1,145 km",
            "economy_oneway": "6,500", "premium_economy_oneway": "11,000",
            "business_oneway": "18,000", "first_class_oneway": "28,000",
            "economy_roundtrip": "11,700", "premium_economy_roundtrip": "19,800",
            "business_roundtrip": "32,400", "first_class_roundtrip": "50,400"
        },
        ("manila", "hongkong"): {
            "duration": "1h 55m", "distance": "1,109 km",
            "economy_oneway": "5,800", "premium_economy_oneway": "10,000",
            "business_oneway": "16,000", "first_class_oneway": "25,000",
            "economy_roundtrip": "10,440", "premium_economy_roundtrip": "18,000",
            "business_roundtrip": "28,800", "first_class_roundtrip": "45,000"
        },
        ("hongkong", "manila"): {
            "duration": "2h 05m", "distance": "1,109 km",
            "economy_oneway": "5,800", "premium_economy_oneway": "10,000",
            "business_oneway": "16,000", "first_class_oneway": "25,000",
            "economy_roundtrip": "10,440", "premium_economy_roundtrip": "18,000",
            "business_roundtrip": "28,800", "first_class_roundtrip": "45,000"
        },
        ("davao", "hongkong"): {
            "duration": "3h 00m", "distance": "1,850 km",
            "economy_oneway": "7,900", "premium_economy_oneway": "13,500",
            "business_oneway": "22,000", "first_class_oneway": "35,000",
            "economy_roundtrip": "14,220", "premium_economy_roundtrip": "24,300",
            "business_roundtrip": "39,600", "first_class_roundtrip": "63,000"
        },
        ("hongkong", "davao"): {
            "duration": "3h 15m", "distance": "1,850 km",
            "economy_oneway": "7,900", "premium_economy_oneway": "13,500",
            "business_oneway": "22,000", "first_class_oneway": "35,000",
            "economy_roundtrip": "14,220", "premium_economy_roundtrip": "24,300",
            "business_roundtrip": "39,600", "first_class_roundtrip": "63,000"
        },
        ("cebu", "singapore"): {
            "duration": "3h 30m", "distance": "2,380 km",
            "economy_oneway": "8,200", "premium_economy_oneway": "14,000",
            "business_oneway": "24,000", "first_class_oneway": "38,000",
            "economy_roundtrip": "14,760", "premium_economy_roundtrip": "25,200",
            "business_roundtrip": "43,200", "first_class_roundtrip": "68,400"
        },
        ("singapore", "cebu"): {
            "duration": "3h 40m", "distance": "2,380 km",
            "economy_oneway": "8,200", "premium_economy_oneway": "14,000",
            "business_oneway": "24,000", "first_class_oneway": "38,000",
            "economy_roundtrip": "14,760", "premium_economy_roundtrip": "25,200",
            "business_roundtrip": "43,200", "first_class_roundtrip": "68,400"
        },
        ("manila", "singapore"): {
            "duration": "3h 20m", "distance": "2,400 km",
            "economy_oneway": "7,900", "premium_economy_oneway": "13,500",
            "business_oneway": "23,000", "first_class_oneway": "36,000",
            "economy_roundtrip": "14,220", "premium_economy_roundtrip": "24,300",
            "business_roundtrip": "41,400", "first_class_roundtrip": "64,800"
        },
        ("singapore", "manila"): {
            "duration": "3h 30m", "distance": "2,400 km",
            "economy_oneway": "7,900", "premium_economy_oneway": "13,500",
            "business_oneway": "23,000", "first_class_oneway": "36,000",
            "economy_roundtrip": "14,220", "premium_economy_roundtrip": "24,300",
            "business_roundtrip": "41,400", "first_class_roundtrip": "64,800"
        },
        ("davao", "singapore"): {
            "duration": "3h 50m", "distance": "2,550 km",
            "economy_oneway": "8,900", "premium_economy_oneway": "15,000",
            "business_oneway": "26,000", "first_class_oneway": "42,000",
            "economy_roundtrip": "16,020", "premium_economy_roundtrip": "27,000",
            "business_roundtrip": "46,800", "first_class_roundtrip": "75,600"
        },
        ("singapore", "davao"): {
            "duration": "4h 00m", "distance": "2,550 km",
            "economy_oneway": "8,900", "premium_economy_oneway": "15,000",
            "business_oneway": "26,000", "first_class_oneway": "42,000",
            "economy_roundtrip": "16,020", "premium_economy_roundtrip": "27,000",
            "business_roundtrip": "46,800", "first_class_roundtrip": "75,600"
        },
    }

    cabin_mapping = {
        "Economy": "economy",
        "Premium Economy": "premium_economy",
        "Business/Premium Flatbed": "business",
        "First Class": "first_class"
    }

    times = [
        ("00:00", "01:30"), ("00:30", "02:00"), ("01:00", "02:30"), ("01:30", "03:00"),
        ("02:00", "03:30"), ("02:30", "04:00"), ("03:00", "04:30"), ("03:30", "05:00"),
        ("04:00", "05:30"), ("04:30", "06:00"),
        ("05:00", "06:30"), ("05:30", "07:00"), ("06:00", "07:30"), ("06:30", "08:00"),
        ("07:00", "08:30"), ("07:30", "09:00"), ("08:00", "09:30"), ("08:30", "10:00"),
        ("09:00", "10:30"), ("09:30", "11:00"), ("10:00", "11:30"), ("10:30", "12:00"),
        ("11:00", "12:30"), ("11:30", "13:00"), ("12:00", "13:30"), ("12:30", "14:00"),
        ("13:00", "14:30"), ("13:30", "15:00"), ("14:00", "15:30"), ("14:30", "16:00"),
        ("15:00", "16:30"), ("15:30", "17:00"), ("16:00", "17:30"), ("16:30", "18:00"),
        ("17:00", "18:30"), ("17:30", "19:00"), ("18:00", "19:30"), ("18:30", "20:00"),
        ("19:00", "20:30"), ("19:30", "21:00"), ("20:00", "21:30"), ("20:30", "22:00"),
        ("21:00", "22:30"), ("21:30", "23:00"), ("22:00", "23:30"), ("22:30", "00:00"),
        ("23:00", "00:30"), ("23:30", "01:00")
    ]

    all_flights = []
    flight_counter = 1000  # Counter for unique flight numbers
    
    random.seed(f"{search_origin}{search_destination}{flight_date}")
    
    for (origin, dest), route in route_data.items():
        for t_type in ["One-way", "Round-trip"]:
            price_suffix = "oneway" if t_type == "One-way" else "roundtrip"
            
            for display_name, db_key in cabin_mapping.items():
                price_key = f"{db_key}_{price_suffix}"
                price = route[price_key]
                
                if display_name == "Economy":
                    num_flights = 5
                elif display_name == "Premium Economy":
                    num_flights = 4
                else:
                    num_flights = 3
                
                selected_times = random.sample(times, num_flights)
                
                for dep_24, arr_24 in selected_times:
                    flight_counter += 1
                    flight_number = f"AT{flight_counter}"
                    gate = get_gate_for_destination(dest)
                    
                    all_flights.append({
                        "origin": origin,
                        "destination": dest,
                        "class": display_name,
                        "departure": format_ph_time(dep_24),
                        "arrival": format_ph_time(arr_24),
                        "price": price,
                        "type": t_type,
                        "duration": route["duration"],
                        "distance": route["distance"],
                        "flight_number": flight_number,  # ADDED
                        "gate": gate  # ADDED
                    })
    
    random.seed()
    
    filtered_flights = []
    if search_origin and search_destination:
        for f in all_flights:
            if (f['origin'] == search_origin
                    and f['destination'] == search_destination
                    and f['type'] == selected_trip_type):
                filtered_flights.append(f)

    return render_template(
        "Flight.html",
        flights=filtered_flights,
        passengers=passenger_data,
        flight_date=flight_date,
        flight_time=format_ph_time(flight_time),
        has_bookings=has_bookings,
        latest_booking_id=latest_booking_id,
        search_origin=search_origin.title(),
        search_destination=search_destination.title()
    )

@app.route('/seats')
def seats():
    origin = request.args.get('origin', '')
    destination = request.args.get('destination', '')
    price = request.args.get('price', '0')
    cabin = request.args.get('cabin', 'Economy')
    flight_date = request.args.get('date', '15 JAN 2026')
    flight_time = request.args.get('time', '06:30')
    flight_no = request.args.get('flight_no', 'AT')
    
    passenger_data = {
        "adults": request.args.get('adults', 1),
        "children": request.args.get('children', 0),
        "infants": request.args.get('infants', 0),
        "cabin": cabin
    }
    
    # QUERY TAKEN SEATS FROM DATABASE for this specific flight
    taken_seats = []
    
    # Find the flight
    flight = Flight.query.filter_by(flight_number=flight_no).first()
    
    if flight:
        # Get all bookings for this flight
        bookings = Booking.query.filter_by(flight_id=flight.id, status='Confirmed').all()
        
        # Get all taken seats from confirmed bookings
        for booking in bookings:
            passengers = Passenger.query.filter_by(booking_id=booking.id).all()
            for passenger in passengers:
                if passenger.seat_number and passenger.seat_number != '---':
                    taken_seats.append(passenger.seat_number)
    
    # Remove duplicates
    taken_seats = list(set(taken_seats))
    
    print(f"Taken seats for flight {flight_no}: {taken_seats}")
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template('seats.html', 
                          passengers=passenger_data, 
                          origin=origin,
                          destination=destination, 
                          price=price, 
                          flight_date=flight_date,
                          flight_time=flight_time, 
                          flight_no=flight_no,
                          taken_seats=taken_seats,  # ADD THIS
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route('/booking')
def booking():
    selected_seat = request.args.get('seat', '--')
    origin = request.args.get('origin', 'Not Selected')
    destination = request.args.get('destination', 'Not Selected')
    price = request.args.get('price', '0.00')
    flight_date = request.args.get('date', '15 JAN 2026')
    flight_time = request.args.get('time', '06:30')
    flight_no = request.args.get('flight_no', 'AT')
    cabin_class = request.args.get('cabin', 'Economy')
    
    # Get duration and distance from route_data
    route_data = {
        ("cebu", "manila"): {"duration": "1h 25m", "distance": "566 km"},
        ("manila", "cebu"): {"duration": "1h 30m", "distance": "566 km"},
        ("cebu", "davao"): {"duration": "1h 05m", "distance": "410 km"},
        ("davao", "cebu"): {"duration": "1h 10m", "distance": "410 km"},
        ("manila", "davao"): {"duration": "1h 50m", "distance": "964 km"},
        ("davao", "manila"): {"duration": "1h 55m", "distance": "964 km"},
        ("cebu", "dubai"): {"duration": "9h 00m", "distance": "6,889 km"},
        ("dubai", "cebu"): {"duration": "9h 30m", "distance": "6,889 km"},
        ("manila", "dubai"): {"duration": "8h 45m", "distance": "6,521 km"},
        ("dubai", "manila"): {"duration": "9h 00m", "distance": "6,521 km"},
        ("cebu", "hongkong"): {"duration": "2h 10m", "distance": "1,145 km"},
        ("hongkong", "cebu"): {"duration": "2h 20m", "distance": "1,145 km"},
        ("manila", "hongkong"): {"duration": "1h 55m", "distance": "1,109 km"},
        ("hongkong", "manila"): {"duration": "2h 05m", "distance": "1,109 km"},  # FIXED: was using ) instead of }
        ("cebu", "singapore"): {"duration": "3h 30m", "distance": "2,380 km"},
        ("singapore", "cebu"): {"duration": "3h 40m", "distance": "2,380 km"},
        ("manila", "singapore"): {"duration": "3h 20m", "distance": "2,400 km"},
        ("singapore", "manila"): {"duration": "3h 30m", "distance": "2,400 km"},  # FIXED: was using ) instead of }
    }
    
    key = (origin.lower(), destination.lower())
    route_info = route_data.get(key, {"duration": "N/A", "distance": "N/A"})
    duration = route_info["duration"]
    distance = route_info["distance"]
    
    # Calculate arrival time
    def calculate_arrival(dep_time, dur):
        try:
            dep_clean = dep_time.replace('AM', '').replace('PM', '').strip()
            if ':' in dep_clean:
                hour = int(dep_clean.split(':')[0])
                minute = int(dep_clean.split(':')[1].split()[0] if ' ' in dep_clean.split(':')[1] else dep_clean.split(':')[1])
            else:
                hour, minute = 6, 30
            
            if 'PM' in dep_time and hour != 12:
                hour += 12
            elif 'AM' in dep_time and hour == 12:
                hour = 0
            
            hours = 0
            minutes = 0
            if 'h' in dur:
                hours = int(dur.split('h')[0].strip())
                if 'm' in dur:
                    minutes_part = dur.split('h')[1].strip()
                    minutes = int(minutes_part.replace('m', '').strip())
            
            total_minutes = hour * 60 + minute + hours * 60 + minutes
            arr_hour = (total_minutes // 60) % 24
            arr_minute = total_minutes % 60
            
            arr_period = "AM" if arr_hour < 12 else "PM"
            arr_hour_12 = arr_hour if arr_hour <= 12 else arr_hour - 12
            if arr_hour_12 == 0:
                arr_hour_12 = 12
            
            return f"{arr_hour_12}:{arr_minute:02d} {arr_period}"
        except:
            return dep_time
    
    arrival_time = calculate_arrival(flight_time, duration)
    
    # Determine gate
    gate_map = {
        "cebu": "A1", "manila": "B2", "davao": "C3",
        "dubai": "D4", "hongkong": "E5", "singapore": "F6"
    }
    gate = gate_map.get(destination.lower(), "A1")
    
    passenger_data = {
        "adults": request.args.get('adults', 1),
        "children": request.args.get('children', 0),
        "infants": request.args.get('infants', 0),
        "cabin": cabin_class
    }
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id

    return render_template('Booking.html', 
                          seat=selected_seat, 
                          origin=origin,
                          destination=destination, 
                          price=price, 
                          passengers=passenger_data,
                          flight_date=flight_date, 
                          flight_time=flight_time,
                          arrival_time=arrival_time,
                          flight_no=flight_no,
                          duration=duration,
                          distance=distance,
                          gate=gate,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== PAYMENT ROUTES ====================

@app.route('/payment', methods=['GET', 'POST']) 
def payment():
    amount = request.args.get('price', request.args.get('amount', '0.00'))
    
    if amount == '0.00' and session.get('total_price'):
        amount = session.get('total_price')
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    if request.method == 'POST':
        print("\n" + "=" * 60)
        print("📦 PAYMENT ROUTE - RAW FORM DATA:")
        for key, value in request.form.items():
            print(f"   {key}: {value}")
        print("=" * 60)
        
        form_amount = request.form.get('total_amount', request.form.get('price', ''))
        if form_amount:
            amount = form_amount
            session['total_price'] = amount
        
        selected_method = request.form.get('selected_method', '')
        
        if selected_method:
            print(f"💰 Payment method selected: {selected_method}")
            print(f"💰 Amount to pay: ₱{amount}")
            
            session['payment_amount'] = amount
            
            method_map = {
                "gcash": "gcash_payment",
                "paytm": "paytm_payment", 
                "paypal": "paypal_payment",
                "grabpay": "grabpay_payment",
                "atome": "atome_payment",
                "alipay": "alipay_payment",
                "applepay": "apple_payment",
                "hoolah": "hoolah_payment",
                "ovo": "ovo_payment"
            }
            endpoint = method_map.get(selected_method.lower().replace(' ', ''))
            if endpoint:
                return redirect(url_for(endpoint, amount=amount))
        
        origin = request.form.get('origin', '')
        destination = request.form.get('destination', '')
        cabin_class = request.form.get('cabin_class', 'Economy')
        flight_date = request.form.get('flight_date', '15 JAN 2026')
        flight_time = request.form.get('flight_time', '06:30')
        flight_no = request.form.get('flight_no', 'AT')
        selected_seats = request.form.get('selected_seats', '')
        seat_count = int(request.form.get('seat_count', 1))
        
        if not amount or amount == '0.00':
            amount = request.form.get('total_amount', '0.00')
            session['total_price'] = amount
        
        print(f"\n💰 TOTAL AMOUNT: ₱{amount}")
        
        session['payment_amount'] = amount
        
        passengers_list = []
        seats_array = [s.strip() for s in selected_seats.split(',') if s.strip()]
        
        for i, seat in enumerate(seats_array, start=1):
            name_key = f'passenger_name_{i}'
            p_name = request.form.get(name_key, f"Passenger {i}")
            passengers_list.append({'name': p_name.upper(), 'seat': seat})
        
        session['all_passengers'] = passengers_list
        session['origin'] = origin.upper() if origin else 'MNL'
        session['destination'] = destination.upper() if destination else 'CEB'
        session['flight_class'] = cabin_class
        session['flight_no'] = flight_no if flight_no and flight_no != 'AT' else "AT" + str(random.randint(1000, 9999))
        session['date'] = flight_date
        session['time'] = flight_time
        session['gate'] = "01"
        session['total_price'] = amount
        
        flight_info = {
            'origin': session['origin'],
            'destination': session['destination'],
            'date': session['date'],
            'time': session['time'],
            'flight_no': session['flight_no'],
            'class': session['flight_class']
        }
        
        return render_template('payment.html', 
                              integrations=payment_methods, 
                              amount=amount, 
                              passengers=passengers_list,
                              flight_info=flight_info,
                              has_bookings=has_bookings,
                              latest_booking_id=latest_booking_id)
    
    if amount == '0.00' and session.get('total_price'):
        amount = session.get('total_price')
    elif amount == '0.00' and session.get('payment_amount'):
        amount = session.get('payment_amount')
    
    fallback_passengers = session.get('all_passengers', [{'name': 'GUEST', 'seat': '--'}])
    flight_info = {
        'origin': session.get('origin', 'MNL'),
        'destination': session.get('destination', 'CEBU'),
        'date': session.get('date', '15 JAN 2026'),
        'time': session.get('time', '06:30'),
        'flight_no': session.get('flight_no', 'AT9567'),
        'class': session.get('flight_class', 'ECONOMY')
    }
    
    return render_template('payment.html', 
                          integrations=payment_methods, 
                          amount=amount, 
                          passengers=fallback_passengers,
                          flight_info=flight_info,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== PAYMENT GATEWAY HANDLERS ====================


@app.route('/gcash', methods=['GET', 'POST'])
def gcash_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        data = request.get_json()
        if data and data.get('status') == 'success':
            # Create ONE booking reference
            booking_ref = generate_booking_reference()
            
            # Store flight details in session
            store_flight_details_in_session()
            
            session['booking_reference'] = booking_ref
            session['payment_status'] = 'Completed'
            session['payment_method'] = 'GCash'
            session['paid_amount'] = clean_amount
            
            booking = save_booking_to_database(booking_ref, clean_amount, 'GCash')
            
            if booking:
                session['booking_id'] = booking.id
                return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
            return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
        return jsonify({'success': False}), 400
    return render_template('gcash.html', amount=clean_amount)


@app.route('/paytm', methods=['GET', 'POST'])
def paytm_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'PayTM'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'PayTM')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('paytm.html', amount=clean_amount)


@app.route('/paypal', methods=['GET', 'POST'])
def paypal_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'PayPal'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'PayPal')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('paypal.html', amount=clean_amount)


@app.route('/grabpay', methods=['GET', 'POST'])
def grabpay_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'GrabPay'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'GrabPay')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('grabpay.html', amount=clean_amount)


@app.route('/atome', methods=['GET', 'POST'])
def atome_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Atome'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'Atome')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('atome.html', amount=clean_amount)


@app.route('/alipay', methods=['GET', 'POST'])
def alipay_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Alipay'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'Alipay')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('alipay.html', amount=clean_amount)


@app.route('/apple', methods=['GET', 'POST'])
def apple_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Apple Pay'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'Apple Pay')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('apple_pay.html', amount=clean_amount)


@app.route('/hoolah', methods=['GET', 'POST'])
def hoolah_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Hoolah'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'Hoolah')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('hoolah.html', amount=clean_amount)


@app.route('/ovo', methods=['GET', 'POST'])
def ovo_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    
    if request.method == 'POST':
        booking_ref = generate_booking_reference()
        store_flight_details_in_session()
        
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'OVO'
        session['paid_amount'] = clean_amount
        
        booking = save_booking_to_database(booking_ref, clean_amount, 'OVO')
        
        if booking:
            session['booking_id'] = booking.id
            return jsonify({'success': True, 'booking_ref': booking_ref, 'booking_id': booking.id})
        return jsonify({'success': False, 'error': 'Failed to save booking'}), 500
    return render_template('ovo.html', amount=clean_amount)


def generate_booking_reference():
    """Generate a booking reference using the flight number"""
    flight_no = session.get('flight_no', 'AT0000')  # Gets whatever flight number was booked
    
    # Check if this flight number is already used as a booking reference
    existing = Booking.query.filter_by(booking_reference=flight_no).first()
    
    if not existing:
        return flight_no  # Returns AT1001, AT1002, AT3068, AT4866, etc.
    else:
        # If already taken, append a number (e.g., AT4866-2)
        counter = 2
        while True:
            new_ref = f"{flight_no}-{counter}"
            if not Booking.query.filter_by(booking_reference=new_ref).first():
                return new_ref
            counter += 1


# HELPER FUNCTION to store flight details in session
def store_flight_details_in_session():
    """Calculate and store all flight details in session"""
    origin = session.get('origin', '')
    destination = session.get('destination', '')
    departure_time = session.get('time', '')
    
    route_data = {
        ("cebu", "manila"): {"duration": "1h 25m", "distance": "566 km"},
        ("manila", "cebu"): {"duration": "1h 30m", "distance": "566 km"},
        ("cebu", "davao"): {"duration": "1h 05m", "distance": "410 km"},
        ("davao", "cebu"): {"duration": "1h 10m", "distance": "410 km"},
        ("manila", "davao"): {"duration": "1h 50m", "distance": "964 km"},
        ("davao", "manila"): {"duration": "1h 55m", "distance": "964 km"},
        ("cebu", "dubai"): {"duration": "9h 00m", "distance": "6,889 km"},
        ("dubai", "cebu"): {"duration": "9h 30m", "distance": "6,889 km"},
        ("manila", "dubai"): {"duration": "8h 45m", "distance": "6,521 km"},
        ("dubai", "manila"): {"duration": "9h 00m", "distance": "6,521 km"},
        ("cebu", "hongkong"): {"duration": "2h 10m", "distance": "1,145 km"},
        ("hongkong", "cebu"): {"duration": "2h 20m", "distance": "1,145 km"},
        ("manila", "hongkong"): {"duration": "1h 55m", "distance": "1,109 km"},
        ("hongkong", "manila"): {"duration": "2h 05m", "distance": "1,109 km"},
        ("cebu", "singapore"): {"duration": "3h 30m", "distance": "2,380 km"},
        ("singapore", "cebu"): {"duration": "3h 40m", "distance": "2,380 km"},
        ("manila", "singapore"): {"duration": "3h 20m", "distance": "2,400 km"},
        ("singapore", "manila"): {"duration": "3h 30m", "distance": "2,400 km"},
    }
    
    key = (origin.lower(), destination.lower())
    route_info = route_data.get(key, {"duration": "N/A", "distance": "N/A"})
    duration = route_info["duration"]
    distance = route_info["distance"]
    
    # Calculate arrival time
    def calc_arrival(dep_time, dur):
        try:
            dep_clean = dep_time.replace('AM', '').replace('PM', '').strip()
            if ':' in dep_clean:
                hour = int(dep_clean.split(':')[0])
                minute = int(dep_clean.split(':')[1].split()[0] if ' ' in dep_clean.split(':')[1] else dep_clean.split(':')[1])
            else:
                hour, minute = 6, 30
            
            if 'PM' in dep_time and hour != 12:
                hour += 12
            elif 'AM' in dep_time and hour == 12:
                hour = 0
            
            hours = 0
            minutes = 0
            if 'h' in dur:
                hours = int(dur.split('h')[0].strip())
                if 'm' in dur:
                    minutes_part = dur.split('h')[1].strip()
                    minutes = int(minutes_part.replace('m', '').strip())
            
            total_minutes = hour * 60 + minute + hours * 60 + minutes
            arr_hour = (total_minutes // 60) % 24
            arr_minute = total_minutes % 60
            
            arr_period = "AM" if arr_hour < 12 else "PM"
            arr_hour_12 = arr_hour if arr_hour <= 12 else arr_hour - 12
            if arr_hour_12 == 0:
                arr_hour_12 = 12
            
            return f"{arr_hour_12}:{arr_minute:02d} {arr_period}"
        except:
            return dep_time
    
    arrival_time = calc_arrival(departure_time, duration)
    
    # Determine gate
    gate_map = {
        "cebu": "A1", "manila": "B2", "davao": "C3",
        "dubai": "D4", "hongkong": "E5", "singapore": "F6"
    }
    gate = gate_map.get(destination.lower(), "A1")
    
    session['duration'] = duration
    session['distance'] = distance
    session['arrival_time'] = arrival_time
    session['gate'] = gate

def save_booking_to_database(booking_ref, amount, payment_method):
    try:
        flight_no = session.get('flight_no', 'AT0000')
        origin = session.get('origin', '')
        destination = session.get('destination', '')
        flight_date = session.get('date', '')
        departure_time = session.get('time', '')
        cabin_class = session.get('flight_class', 'Economy')
        passengers = session.get('all_passengers', [])
        
        if not passengers:
            print("❌ ERROR: No passengers in session!")
            return None
        
        # Calculate arrival time from duration
        def calculate_arrival_time(dep_time, duration):
            try:
                # Parse departure time (e.g., "6:30 AM" or "06:30")
                dep_clean = dep_time.replace('AM', '').replace('PM', '').strip()
                if ':' in dep_clean:
                    hour = int(dep_clean.split(':')[0])
                    minute = int(dep_clean.split(':')[1].split()[0] if ' ' in dep_clean.split(':')[1] else dep_clean.split(':')[1])
                else:
                    hour, minute = 6, 30
                
                # Convert to 24-hour
                if 'PM' in dep_time and hour != 12:
                    hour += 12
                elif 'AM' in dep_time and hour == 12:
                    hour = 0
                
                # Parse duration (e.g., "1h 30m")
                hours = 0
                minutes = 0
                if 'h' in duration:
                    hours = int(duration.split('h')[0].strip())
                    if 'm' in duration:
                        minutes_part = duration.split('h')[1].strip()
                        minutes = int(minutes_part.replace('m', '').strip())
                
                # Calculate arrival
                total_minutes = hour * 60 + minute + hours * 60 + minutes
                arr_hour = (total_minutes // 60) % 24
                arr_minute = total_minutes % 60
                
                # Convert back to 12-hour format
                arr_period = "AM" if arr_hour < 12 else "PM"
                arr_hour_12 = arr_hour if arr_hour <= 12 else arr_hour - 12
                if arr_hour_12 == 0:
                    arr_hour_12 = 12
                
                return f"{arr_hour_12}:{arr_minute:02d} {arr_period}"
            except:
                return departure_time  # fallback
        
        # Get duration and distance from route_data
        route_data = {
            ("cebu", "manila"): {"duration": "1h 25m", "distance": "566 km"},
            ("manila", "cebu"): {"duration": "1h 30m", "distance": "566 km"},
            ("cebu", "davao"): {"duration": "1h 05m", "distance": "410 km"},
            ("davao", "cebu"): {"duration": "1h 10m", "distance": "410 km"},
            ("manila", "davao"): {"duration": "1h 50m", "distance": "964 km"},
            ("davao", "manila"): {"duration": "1h 55m", "distance": "964 km"},
            ("cebu", "dubai"): {"duration": "9h 00m", "distance": "6,889 km"},
            ("dubai", "cebu"): {"duration": "9h 30m", "distance": "6,889 km"},
            ("manila", "dubai"): {"duration": "8h 45m", "distance": "6,521 km"},
            ("dubai", "manila"): {"duration": "9h 00m", "distance": "6,521 km"},
            ("cebu", "hongkong"): {"duration": "2h 10m", "distance": "1,145 km"},
            ("hongkong", "cebu"): {"duration": "2h 20m", "distance": "1,145 km"},
            ("manila", "hongkong"): {"duration": "1h 55m", "distance": "1,109 km"},
            ("hongkong", "manila"): {"duration": "2h 05m", "distance": "1,109 km"},
            ("cebu", "singapore"): {"duration": "3h 30m", "distance": "2,380 km"},
            ("singapore", "cebu"): {"duration": "3h 40m", "distance": "2,380 km"},
            ("manila", "singapore"): {"duration": "3h 20m", "distance": "2,400 km"},
            ("singapore", "manila"): {"duration": "3h 30m", "distance": "2,400 km"},
        }
        
        key = (origin.lower(), destination.lower())
        route_info = route_data.get(key, {"duration": "N/A", "distance": "N/A"})
        duration = route_info["duration"]
        distance = route_info["distance"]
        
        # Calculate arrival time
        arrival_time = calculate_arrival_time(departure_time, duration) if duration != "N/A" else departure_time
        
        # Determine gate
        gate_map = {
            "cebu": "A1", "manila": "B2", "davao": "C3",
            "dubai": "D4", "hongkong": "E5", "singapore": "F6"
        }
        gate = gate_map.get(destination.lower(), "A1")
        
        # Check if flight already exists
        flight = Flight.query.filter_by(flight_number=flight_no).first()
        
        if not flight:
            # Create flight with REAL data
            flight = Flight(
                flight_number=flight_no,
                origin=origin.upper(),
                destination=destination.upper(),
                departure_date=flight_date,
                departure_time=departure_time,
                arrival_time=arrival_time,  # NOW REAL
                duration=duration,           # NOW REAL
                distance=distance,           # NOW REAL
                gate=gate,                   # NOW REAL
                status="Scheduled"
            )
            db.session.add(flight)
            db.session.commit()
            print(f"✅ Created new flight: {flight_no} - {origin}→{destination}")
        else:
            # Update existing flight if it has N/A values
            if flight.duration == "N/A" and duration != "N/A":
                flight.duration = duration
            if flight.distance == "N/A" and distance != "N/A":
                flight.distance = distance
            if flight.arrival_time == flight.departure_time and arrival_time != departure_time:
                flight.arrival_time = arrival_time
            db.session.commit()
        
        user_id = session.get('user_id')
        booking = Booking(
            booking_reference=booking_ref,
            user_id=user_id,
            flight_id=flight.id,
            total_passengers=len(passengers),
            total_price=amount,
            cabin_class=cabin_class,
            status="Confirmed",
            payment_method=payment_method,
            payment_status="Completed"
        )
        db.session.add(booking)
        db.session.commit()
        
        for passenger in passengers:
            passenger_record = Passenger(
                booking_id=booking.id,
                full_name=passenger.get('name', ''),
                seat_number=passenger.get('seat', '---'),
                passenger_type="Adult"
            )
            db.session.add(passenger_record)
        
        db.session.commit()
        
        session['booking_id'] = booking.id
        session['booking_reference'] = booking_ref
        
        print(f"\n✅ BOOKING SAVED: {booking_ref}")
        print(f"   Flight: {flight_no} | Duration: {duration} | Distance: {distance} | Gate: {gate}")
        
        return booking
    except Exception as e:
        print(f"\n❌ ERROR SAVING BOOKING: {str(e)}")
        db.session.rollback()
        return None
# ==================== TICKET ROUTES ====================

@app.route("/ticket")
def ticket():
    # First try to get booking from database using booking_id in session
    booking_id = session.get('booking_id')
    booking_ref = session.get('booking_reference')
    
    passengers_data = None
    flight_data = None
    
    # Try to get from database first
    if booking_id:
        booking = Booking.query.get(booking_id)
        if booking:
            # Get passengers from database
            passengers_from_db = Passenger.query.filter_by(booking_id=booking.id).all()
            if passengers_from_db:
                passengers_data = [{'name': p.full_name, 'seat': p.seat_number} for p in passengers_from_db]
            
            # Get flight from database
            flight = Flight.query.get(booking.flight_id)
            if flight:
                flight_data = {
                    "flight": flight.flight_number,
                    "gate": flight.gate,
                    "origin": flight.origin,
                    "destination": flight.destination,
                    "date": flight.departure_date,
                    "time": flight.departure_time,
                    "arrival": flight.arrival_time,
                    "duration": flight.duration,
                    "distance": flight.distance,
                    "class": booking.cabin_class.upper()
                }
                # Update session with database values
                session['flight_no'] = flight.flight_number
                session['origin'] = flight.origin
                session['destination'] = flight.destination
                session['date'] = flight.departure_date
                session['time'] = flight.departure_time
                session['flight_class'] = booking.cabin_class
                session['gate'] = flight.gate
                session['booking_reference'] = booking.booking_reference
    
    # Fallback to session data if database failed
    if not passengers_data:
        passengers_data = session.get('all_passengers')
        if not passengers_data:
            passengers_data = [{'name': 'NO DATA', 'seat': '---'}]
            flash("No booking data found. Please complete your booking first.")
    
    if not flight_data:
        flight_data = {
            "flight": session.get('flight_no', 'AT0000'),
            "gate": session.get('gate', '01'),
            "origin": session.get('origin', '---'),
            "destination": session.get('destination', '---'),
            "date": session.get('date', '---'),
            "time": session.get('time', '---'),
            "arrival": session.get('arrival_time', '---'),
            "duration": session.get('duration', '---'),
            "distance": session.get('distance', '---'),
            "class": session.get('flight_class', 'ECONOMY').upper()
        }
    
    # If user is logged in but no booking in session, find their latest booking
    if session.get('user_id') and not booking_id:
        latest_booking = Booking.query.filter_by(user_id=session.get('user_id')).order_by(Booking.id.desc()).first()
        if latest_booking:
            session['booking_id'] = latest_booking.id
            session['booking_reference'] = latest_booking.booking_reference
            return redirect(url_for('ticket'))
    
    print("=" * 60)
    print("TICKET DATA:")
    print(f"  Booking Ref: {session.get('booking_reference')}")
    print(f"  Flight: {flight_data.get('flight')}")
    print(f"  Origin: {flight_data.get('origin')} → Destination: {flight_data.get('destination')}")
    print(f"  Date: {flight_data.get('date')} Time: {flight_data.get('time')}")
    print(f"  Duration: {flight_data.get('duration')} Distance: {flight_data.get('distance')}")
    print(f"  Gate: {flight_data.get('gate')} Arrival: {flight_data.get('arrival')}")
    print("=" * 60)
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template("ticket.html", 
                          passengers=passengers_data, 
                          flight=flight_data,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== PROFILE PICTURE UPLOAD ====================

@app.route('/upload_profile_picture', methods=['POST'])
def upload_profile_picture():
    if 'user_id' not in session:
        flash("Please log in.")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        flash("User not found.")
        return redirect(url_for('login'))
    
    if 'profile_picture' not in request.files:
        flash("No file selected.")
        return redirect(url_for('user_settings'))
    
    file = request.files['profile_picture']
    if file.filename == '':
        flash("No file selected.")
        return redirect(url_for('user_settings'))
    
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"user_{user.id}_{random.randint(1000,9999)}.{ext}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if user.profile_picture:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        user.profile_picture = filename
        db.session.commit()
        session['show_success_popup'] = "Profile picture updated successfully!"
        return redirect(url_for('user_settings'))
    else:
        flash("Invalid file type. Use PNG, JPG, JPEG, or GIF.")
    
    return redirect(url_for('user_settings'))

# ==================== USER DASHBOARD & SETTINGS ====================

@app.route('/dashboard')
def user_dashboard():
    if 'user_id' not in session:
        flash("Please log in to view your dashboard.")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash("User not found. Please log in again.")
        return redirect(url_for('login'))
    
    bookings = db.session.query(Booking, Flight).join(Flight, Booking.flight_id == Flight.id)\
                        .filter(Booking.user_id == user.id)\
                        .order_by(Booking.booking_date.desc()).all()
    
    booking_list = []
    total_spent = 0
    for booking, flight in bookings:
        total_spent += float(booking.total_price.replace('₱', '').replace(',', ''))
        booking_list.append({
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'flight_no': flight.flight_number,
            'origin': flight.origin,
            'destination': flight.destination,
            'date': flight.departure_date,
            'time': flight.departure_time,
            'seats': booking.total_passengers,
            'total': booking.total_price,
            'status': booking.status
        })
    
    has_bookings = len(booking_list) > 0
    latest_booking_id = booking_list[0]['id'] if booking_list else None
    
    return render_template('user_dashboard.html', 
                          user=user, 
                          bookings=booking_list[:5],
                          total_spent=f"₱{total_spent:,.2f}",
                          all_bookings=booking_list,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route('/settings', methods=['GET', 'POST'])
def user_settings():
    if 'user_id' not in session:
        flash("Please log in to access settings.")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    if not user:
        session.clear()
        flash("User not found.")
        return redirect(url_for('login'))
    
    has_bookings = False
    latest_booking_id = None
    booking_count = Booking.query.filter_by(user_id=user.id).count()
    has_bookings = booking_count > 0
    
    latest_booking = Booking.query.filter_by(user_id=user.id).order_by(Booking.id.desc()).first()
    if latest_booking:
        latest_booking_id = latest_booking.id
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_profile':
            fullname = request.form.get('fullname', '').strip()
            email = request.form.get('email', '').strip()
            phone = request.form.get('phone', '').strip()
            if fullname:
                user.fullname = fullname
            if email and email != user.email:
                if User.query.filter(User.email == email, User.id != user.id).first():
                    flash("Email already taken by another account.")
                else:
                    user.email = email
            user.phone = phone if phone else None
            db.session.commit()
            session['show_success_popup'] = "Profile updated successfully!"
            return redirect(url_for('user_settings'))
        
        elif action == 'change_password':
            current = request.form.get('current_password')
            new = request.form.get('new_password')
            confirm = request.form.get('confirm_password')
            if not check_password_hash(user.password, current):
                flash("Current password is incorrect.")
            elif new != confirm:
                flash("New passwords do not match.")
            elif len(new) < 6:
                flash("Password must be at least 6 characters.")
            else:
                user.password = generate_password_hash(new)
                db.session.commit()
                session['show_success_popup'] = "Password changed successfully!"
            return redirect(url_for('user_settings'))
        
        elif action == 'update_notifications':
            user.email_reminders = 'email_reminders' in request.form
            db.session.commit()
            session['show_success_popup'] = "Notification preferences updated!"
            return redirect(url_for('user_settings'))
        
        elif action == 'delete_account':
            Booking.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            session.clear()
            session['show_success_popup'] = "Your account has been permanently deleted."
            return redirect(url_for('home'))
    
    return render_template('user_settings.html', 
                          user=user, 
                          phone=user.phone or '',
                          email_reminders=user.email_reminders,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== USER DASHBOARD API ROUTES (ADDED) ====================

@app.route('/api/user/dashboard')
@login_required
def api_user_dashboard():
    """Get user dashboard data with fetched totals and upcoming flights"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user's provider info from SocialUser if exists
    provider = 'email'
    social_user = SocialUser.query.filter_by(email=user.email).first()
    if social_user:
        provider = social_user.provider
    
    # Get user bookings with flight details
    bookings = db.session.query(Booking, Flight).join(Flight, Booking.flight_id == Flight.id)\
        .filter(Booking.user_id == user.id)\
        .order_by(Booking.booking_date.desc()).all()
    
    booking_list = []
    total_spent = 0
    upcoming_count = 0
    today = datetime.utcnow().date()
    
    for booking, flight in bookings:
        # Calculate total spent
        try:
            price_str = booking.total_price.replace('₱', '').replace(',', '').strip()
            price = float(price_str)
            total_spent += price
        except:
            pass
        
        # Check if flight is upcoming
        try:
            flight_date = datetime.strptime(flight.departure_date, '%d %b %Y').date()
            if flight_date >= today and booking.status != 'cancelled':
                upcoming_count += 1
        except:
            pass
        
        booking_list.append({
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'flight_number': flight.flight_number,
            'origin': flight.origin,
            'destination': flight.destination,
            'departure_date': flight.departure_date,
            'departure_time': flight.departure_time,
            'total_passengers': booking.total_passengers,
            'total_price': booking.total_price,
            'cabin_class': booking.cabin_class,
            'status': booking.status,
            'payment_method': booking.payment_method,
            'booking_date': booking.booking_date.isoformat() if booking.booking_date else None
        })
    
    # Get profile picture URL
    profile_pic_url = None
    if user.profile_picture:
        profile_pic_url = url_for('static', filename=f'uploads/{user.profile_picture}', _external=True)
    
    return jsonify({
        'user': {
            'id': user.id,
            'fullname': user.fullname,
            'email': user.email,
            'profile_picture': profile_pic_url,
            'is_admin': user.is_admin,
            'provider': provider,
            'created_at': user.created_at.isoformat() if user.created_at else None
        },
        'total_bookings': len(booking_list),
        'total_spent': total_spent,
        'upcoming_count': upcoming_count,
        'bookings': booking_list
    })

@app.route('/api/update_profile', methods=['POST'])
@login_required
def api_update_profile_settings():
    """Update user profile via API"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.json
    fullname = data.get('fullname', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    
    if fullname:
        user.fullname = fullname
    
    if email and email != user.email:
        # Check if email is already taken
        existing = User.query.filter(User.email == email, User.id != user.id).first()
        if existing:
            return jsonify({'error': 'Email already taken'}), 400
        user.email = email
    
    if phone:
        user.phone = phone
    else:
        user.phone = None
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'user': {
            'fullname': user.fullname,
            'email': user.email,
            'phone': user.phone
        }
    })

@app.route('/api/upload_avatar', methods=['POST'])
@login_required
def api_upload_avatar_settings():
    """Upload profile picture via API"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if 'avatar' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['avatar']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = secure_filename(f"user_{user.id}_{int(datetime.utcnow().timestamp())}.{ext}")
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file.save(filepath)
        
        # Delete old profile picture
        if user.profile_picture:
            old_path = os.path.join(app.config['UPLOAD_FOLDER'], user.profile_picture)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        user.profile_picture = filename
        db.session.commit()
        
        return jsonify({
            'success': True,
            'avatar_url': url_for('static', filename=f'uploads/{filename}', _external=True)
        })
    
    return jsonify({'error': 'Invalid file type. Use PNG, JPG, JPEG, or GIF'}), 400

@app.route('/api/change_password', methods=['POST'])
@login_required
def api_change_password_settings():
    """Change user password via API"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.json
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    
    if not old_password or not new_password:
        return jsonify({'error': 'All fields are required'}), 400
    
    if not check_password_hash(user.password, old_password):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters'}), 400
    
    user.password = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/update_notifications', methods=['POST'])
@login_required
def api_update_notifications():
    """Update notification preferences"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    data = request.json
    user.email_reminders = data.get('email_reminders', False)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/delete_account', methods=['DELETE'])
@login_required
def api_delete_account():
    """Delete user account permanently"""
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Delete all user's bookings and passengers
    bookings = Booking.query.filter_by(user_id=user.id).all()
    for booking in bookings:
        Passenger.query.filter_by(booking_id=booking.id).delete()
        db.session.delete(booking)
    
    # Delete user
    db.session.delete(user)
    db.session.commit()
    
    # Clear session
    session.clear()
    
    return jsonify({'success': True})

@app.route('/api/cancel_booking/<int:booking_id>', methods=['DELETE'])
@login_required
def api_cancel_booking(booking_id):
    """Cancel a booking"""
    booking = Booking.query.get_or_404(booking_id)
    
    # Check if booking belongs to user
    if booking.user_id != session.get('user_id'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Check if flight hasn't departed yet
    flight = Flight.query.get(booking.flight_id)
    try:
        flight_date = datetime.strptime(flight.departure_date, '%d %b %Y')
        if flight_date < datetime.now():
            return jsonify({'error': 'Cannot cancel past flights'}), 400
    except:
        pass
    
    booking.status = 'cancelled'
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Booking cancelled successfully'})

# ==================== COMPLETE ADMIN API ROUTES ====================

# ----- USER MANAGEMENT API -----

@app.route('/api/admin/users', methods=['GET'])
@admin_required
def api_get_all_users():
    search = request.args.get('search', '')
    
    query = User.query
    if search:
        query = query.filter(
            db.or_(
                User.email.ilike(f'%{search}%'),
                User.fullname.ilike(f'%{search}%')
            )
        )
    
    users = query.order_by(User.created_at.desc()).all()
    
    return jsonify({
        'users': [{
            'id': u.id,
            'fullname': u.fullname,
            'email': u.email,
            'is_admin': u.is_admin,
            'is_active': u.is_active,
            'created_at': u.created_at.isoformat() if u.created_at else None,
            'phone': u.phone,
            'profile_picture': u.profile_picture
        } for u in users]
    })

@app.route('/api/admin/user/<int:user_id>', methods=['GET'])
@admin_required
def api_get_user(user_id):
    user = User.query.get_or_404(user_id)
    return jsonify({
        'id': user.id,
        'fullname': user.fullname,
        'email': user.email,
        'is_admin': user.is_admin,
        'is_active': user.is_active,
        'phone': user.phone,
        'created_at': user.created_at.isoformat() if user.created_at else None,
        'profile_picture': user.profile_picture
    })

@app.route('/api/admin/user', methods=['POST'])
@admin_required
def api_create_user():
    data = request.json
    email = data.get('email', '').strip()
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'Email already exists'}), 400
    
    if not data.get('password') or len(data.get('password')) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    new_user = User(
        fullname=data.get('fullname'),
        email=email,
        password=generate_password_hash(data['password']),
        is_admin=data.get('is_admin', False),
        is_active=True
    )
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'success': True, 'user_id': new_user.id})

@app.route('/api/admin/user/<int:user_id>', methods=['PUT'])
@admin_required
def api_update_user(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    
    if 'fullname' in data:
        user.fullname = data['fullname']
    if 'email' in data and data['email'] != user.email:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400
        user.email = data['email']
    if 'is_admin' in data:
        if user.id == session.get('user_id') and not data['is_admin']:
            return jsonify({'error': 'Cannot remove your own admin role'}), 400
        user.is_admin = data['is_admin']
    if 'phone' in data:
        user.phone = data['phone']
    if 'password' in data and data['password']:
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        user.password = generate_password_hash(data['password'])
    
    db.session.commit()
    return jsonify({'success': True})

@app.route('/api/admin/user/<int:user_id>', methods=['DELETE'])
@admin_required
def api_delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == session.get('user_id'):
        return jsonify({'error': 'Cannot delete your own account'}), 400
    
    Booking.query.filter_by(user_id=user.id).delete()
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/user/<int:user_id>/role', methods=['PUT'])
@admin_required
def api_update_user_role(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    
    if user.id == session.get('user_id') and not data.get('is_admin', False):
        return jsonify({'error': 'Cannot remove your own admin role'}), 400
    
    user.is_admin = data.get('is_admin', False)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/user/<int:user_id>/reset-password', methods=['POST'])
@admin_required
def api_reset_user_password(user_id):
    user = User.query.get_or_404(user_id)
    data = request.json
    new_password = data.get('password', '')
    
    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    user.password = generate_password_hash(new_password)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/user/<int:user_id>/toggle-status', methods=['POST'])
@admin_required
def api_toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == session.get('user_id'):
        return jsonify({'error': 'Cannot disable your own account'}), 400
    
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': user.is_active})

# ----- BOOKING MANAGEMENT API -----

@app.route('/api/admin/bookings', methods=['GET'])
@admin_required
def api_get_all_bookings():
    search = request.args.get('search', '')
    
    query = db.session.query(Booking, Flight, User).join(Flight, Booking.flight_id == Flight.id)\
        .outerjoin(User, Booking.user_id == User.id)
    
    if search:
        query = query.filter(
            db.or_(
                Booking.booking_reference.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    
    results = query.order_by(Booking.booking_date.desc()).all()
    
    bookings_list = []
    for booking, flight, user in results:
        passengers = Passenger.query.filter_by(booking_id=booking.id).all()
        bookings_list.append({
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'user_email': user.email if user else 'Guest',
            'flight_number': flight.flight_number,
            'origin': flight.origin,
            'destination': flight.destination,
            'departure_date': flight.departure_date,
            'total_price': booking.total_price,
            'total_passengers': booking.total_passengers,
            'cabin_class': booking.cabin_class,
            'status': booking.status,
            'payment_method': booking.payment_method,
            'payment_status': booking.payment_status,
            'booking_date': booking.booking_date.isoformat() if booking.booking_date else None,
            'passengers': [{'name': p.full_name, 'seat': p.seat_number} for p in passengers]
        })
    
    return jsonify({'bookings': bookings_list})

@app.route('/api/admin/booking/<int:booking_id>', methods=['GET'])
@admin_required
def api_get_booking_details(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    flight = Flight.query.get(booking.flight_id)
    user = User.query.get(booking.user_id) if booking.user_id else None
    passengers = Passenger.query.filter_by(booking_id=booking.id).all()
    
    return jsonify({
        'id': booking.id,
        'booking_reference': booking.booking_reference,
        'user_email': user.email if user else 'Guest',
        'user_name': user.fullname if user else 'Guest',
        'flight_number': flight.flight_number,
        'origin': flight.origin,
        'destination': flight.destination,
        'departure_date': flight.departure_date,
        'departure_time': flight.departure_time,
        'arrival_time': flight.arrival_time,
        'gate': flight.gate,
        'total_price': booking.total_price,
        'total_passengers': booking.total_passengers,
        'cabin_class': booking.cabin_class,
        'status': booking.status,
        'payment_method': booking.payment_method,
        'payment_status': booking.payment_status,
        'booking_date': booking.booking_date.isoformat() if booking.booking_date else None,
        'passengers': [{'id': p.id, 'name': p.full_name, 'seat': p.seat_number, 'type': p.passenger_type} for p in passengers]
    })

@app.route('/api/admin/booking/<int:booking_id>/status', methods=['PUT'])
@admin_required
def api_update_booking_status(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    data = request.json
    new_status = data.get('status')
    
    valid_statuses = ['pending', 'confirmed', 'cancelled', 'completed']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    booking.status = new_status
    db.session.commit()
    
    return jsonify({'success': True, 'status': booking.status})

@app.route('/api/admin/booking/<int:booking_id>', methods=['DELETE'])
@admin_required
def api_delete_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    Passenger.query.filter_by(booking_id=booking.id).delete()
    db.session.delete(booking)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/bookings/export', methods=['GET'])
@admin_required
def api_export_bookings():
    import csv
    from io import StringIO
    from flask import Response
    
    bookings = db.session.query(Booking, Flight, User).join(Flight, Booking.flight_id == Flight.id)\
        .outerjoin(User, Booking.user_id == User.id).order_by(Booking.booking_date.desc()).all()
    
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Booking Reference', 'User Email', 'Flight Number', 'Origin', 'Destination', 
                 'Departure Date', 'Total Price', 'Passengers', 'Cabin Class', 'Status', 
                 'Payment Method', 'Booking Date'])
    
    for booking, flight, user in bookings:
        passenger_count = Passenger.query.filter_by(booking_id=booking.id).count()
        cw.writerow([
            booking.booking_reference,
            user.email if user else 'Guest',
            flight.flight_number,
            flight.origin,
            flight.destination,
            flight.departure_date,
            booking.total_price,
            passenger_count,
            booking.cabin_class,
            booking.status,
            booking.payment_method,
            booking.booking_date.strftime('%Y-%m-%d %H:%M') if booking.booking_date else ''
        ])
    
    output = si.getvalue()
    return Response(output, mimetype='text/csv', 
                   headers={"Content-Disposition": "attachment;filename=bookings_export.csv"})

# ----- FLIGHT MANAGEMENT API -----

@app.route('/api/admin/flights', methods=['GET'])
@admin_required
def api_get_all_flights():
    flights = Flight.query.order_by(Flight.departure_date).all()
    
    return jsonify({
        'flights': [{
            'id': f.id,
            'flight_number': f.flight_number,
            'origin': f.origin,
            'destination': f.destination,
            'departure_date': f.departure_date,
            'departure_time': f.departure_time,
            'arrival_time': f.arrival_time,
            'duration': f.duration,
            'distance': f.distance,
            'economy_price': f.economy_price,
            'premium_economy_price': f.premium_economy_price,
            'business_price': f.business_price,
            'first_class_price': f.first_class_price,
            'total_seats': f.total_seats,
            'available_seats': f.available_seats,
            'gate': f.gate,
            'status': f.status
        } for f in flights]
    })

@app.route('/api/admin/flight/<int:flight_id>', methods=['GET'])
@admin_required
def api_get_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    return jsonify({
        'id': flight.id,
        'flight_number': flight.flight_number,
        'origin': flight.origin,
        'destination': flight.destination,
        'departure_date': flight.departure_date,
        'departure_time': flight.departure_time,
        'arrival_time': flight.arrival_time,
        'duration': flight.duration,
        'distance': flight.distance,
        'economy_price': flight.economy_price,
        'premium_economy_price': flight.premium_economy_price,
        'business_price': flight.business_price,
        'first_class_price': flight.first_class_price,
        'total_seats': flight.total_seats,
        'available_seats': flight.available_seats,
        'gate': flight.gate,
        'status': flight.status
    })

@app.route('/api/admin/flight', methods=['POST'])
@admin_required
def api_create_flight():
    data = request.json
    
    if Flight.query.filter_by(flight_number=data.get('flight_number')).first():
        return jsonify({'error': 'Flight number already exists'}), 400
    
    new_flight = Flight(
        flight_number=data.get('flight_number'),
        origin=data.get('origin', '').upper(),
        destination=data.get('destination', '').upper(),
        departure_date=data.get('departure_date'),
        departure_time=data.get('departure_time'),
        arrival_time=data.get('arrival_time'),
        duration=data.get('duration', 'N/A'),
        distance=data.get('distance', 'N/A'),
        economy_price=data.get('economy_price', '2,100'),
        premium_economy_price=data.get('premium_economy_price', '4,500'),
        business_price=data.get('business_price', '8,500'),
        first_class_price=data.get('first_class_price', '15,000'),
        total_seats=data.get('total_seats', 60),
        available_seats=data.get('total_seats', 60),
        gate=data.get('gate', 'A1'),
        status=data.get('status', 'Scheduled')
    )
    
    db.session.add(new_flight)
    db.session.commit()
    
    return jsonify({'success': True, 'flight_id': new_flight.id})

@app.route('/api/admin/flight/<int:flight_id>', methods=['PUT'])
@admin_required
def api_update_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    data = request.json
    
    flight.flight_number = data.get('flight_number', flight.flight_number)
    flight.origin = data.get('origin', flight.origin).upper()
    flight.destination = data.get('destination', flight.destination).upper()
    flight.departure_date = data.get('departure_date', flight.departure_date)
    flight.departure_time = data.get('departure_time', flight.departure_time)
    flight.arrival_time = data.get('arrival_time', flight.arrival_time)
    flight.duration = data.get('duration', flight.duration)
    flight.distance = data.get('distance', flight.distance)
    flight.economy_price = data.get('economy_price', flight.economy_price)
    flight.premium_economy_price = data.get('premium_economy_price', flight.premium_economy_price)
    flight.business_price = data.get('business_price', flight.business_price)
    flight.first_class_price = data.get('first_class_price', flight.first_class_price)
    flight.total_seats = data.get('total_seats', flight.total_seats)
    flight.gate = data.get('gate', flight.gate)
    flight.status = data.get('status', flight.status)
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/flight/<int:flight_id>', methods=['DELETE'])
@admin_required
def api_delete_flight(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    
    bookings = Booking.query.filter_by(flight_id=flight.id).count()
    if bookings > 0:
        return jsonify({'error': f'Cannot delete flight with {bookings} existing bookings'}), 400
    
    db.session.delete(flight)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/flight/<int:flight_id>/status', methods=['PUT'])
@admin_required
def api_update_flight_status(flight_id):
    flight = Flight.query.get_or_404(flight_id)
    data = request.json
    new_status = data.get('status')
    
    valid_statuses = ['Scheduled', 'Delayed', 'Cancelled', 'Departed', 'Arrived']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400
    
    flight.status = new_status
    db.session.commit()
    
    return jsonify({'success': True, 'status': flight.status})

# ----- PROMO CODE MANAGEMENT API -----

@app.route('/api/admin/promos', methods=['GET'])
@admin_required
def api_get_all_promos():
    promos = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
    
    return jsonify({
        'promos': [{
            'id': p.id,
            'code': p.code,
            'description': p.description,
            'discount_type': p.discount_type,
            'discount_value': p.discount_value,
            'valid_from': p.valid_from.isoformat() if p.valid_from else None,
            'valid_until': p.valid_until.isoformat() if p.valid_until else None,
            'max_uses': p.max_uses,
            'min_amount': p.min_amount,
            'used_count': p.used_count,
            'is_active': p.is_active,
            'created_at': p.created_at.isoformat() if p.created_at else None
        } for p in promos]
    })

@app.route('/api/admin/promo/<int:promo_id>', methods=['GET'])
@admin_required
def api_get_promo(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    return jsonify({
        'id': promo.id,
        'code': promo.code,
        'description': promo.description,
        'discount_type': promo.discount_type,
        'discount_value': promo.discount_value,
        'valid_from': promo.valid_from.isoformat() if promo.valid_from else None,
        'valid_until': promo.valid_until.isoformat() if promo.valid_until else None,
        'max_uses': promo.max_uses,
        'min_amount': promo.min_amount,
        'used_count': promo.used_count,
        'is_active': promo.is_active
    })

@app.route('/api/admin/promo', methods=['POST'])
@admin_required
def api_create_promo():
    data = request.json
    
    if PromoCode.query.filter_by(code=data.get('code').upper()).first():
        return jsonify({'error': 'Promo code already exists'}), 400
    
    new_promo = PromoCode(
        code=data.get('code').upper(),
        description=data.get('description'),
        discount_type=data.get('discount_type', 'percentage'),
        discount_value=float(data.get('discount_value')),
        valid_from=datetime.fromisoformat(data.get('valid_from')) if data.get('valid_from') else datetime.utcnow(),
        valid_until=datetime.fromisoformat(data.get('valid_until')) if data.get('valid_until') else datetime.utcnow() + timedelta(days=30),
        max_uses=int(data.get('max_uses')) if data.get('max_uses') else None,
        min_amount=float(data.get('min_amount')) if data.get('min_amount') else None,
        is_active=True
    )
    
    db.session.add(new_promo)
    db.session.commit()
    
    return jsonify({'success': True, 'promo_id': new_promo.id})

@app.route('/api/admin/promo/<int:promo_id>', methods=['PUT'])
@admin_required
def api_update_promo(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    data = request.json
    
    if 'code' in data and data['code'] != promo.code:
        if PromoCode.query.filter_by(code=data['code'].upper()).first():
            return jsonify({'error': 'Promo code already exists'}), 400
        promo.code = data['code'].upper()
    if 'description' in data:
        promo.description = data['description']
    if 'discount_type' in data:
        promo.discount_type = data['discount_type']
    if 'discount_value' in data:
        promo.discount_value = float(data['discount_value'])
    if 'valid_from' in data:
        promo.valid_from = datetime.fromisoformat(data['valid_from'])
    if 'valid_until' in data:
        promo.valid_until = datetime.fromisoformat(data['valid_until'])
    if 'max_uses' in data:
        promo.max_uses = int(data['max_uses']) if data['max_uses'] else None
    if 'min_amount' in data:
        promo.min_amount = float(data['min_amount']) if data['min_amount'] else None
    if 'is_active' in data:
        promo.is_active = data['is_active']
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/promo/<int:promo_id>', methods=['DELETE'])
@admin_required
def api_delete_promo(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    db.session.delete(promo)
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/admin/promo/<int:promo_id>/status', methods=['PUT'])
@admin_required
def api_update_promo_status(promo_id):
    promo = PromoCode.query.get_or_404(promo_id)
    data = request.json
    promo.is_active = data.get('is_active', False)
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': promo.is_active})

# ----- ANALYTICS API -----

@app.route('/api/admin/analytics', methods=['GET'])
@admin_required
def api_get_analytics():
    days = request.args.get('days', 30, type=int)
    
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    daily_data = {}
    for i in range(days):
        date = start_date + timedelta(days=i)
        date_str = date.strftime('%Y-%m-%d')
        daily_data[date_str] = {'revenue': 0, 'bookings': 0}
    
    bookings = Booking.query.filter(Booking.booking_date >= start_date).all()
    
    for booking in bookings:
        date_str = booking.booking_date.strftime('%Y-%m-%d')
        if date_str in daily_data:
            price_str = booking.total_price.replace('₱', '').replace(',', '')
            try:
                price = float(price_str)
                daily_data[date_str]['revenue'] += price
            except:
                pass
            daily_data[date_str]['bookings'] += 1
    
    dates = list(daily_data.keys())
    revenue_data = [daily_data[d]['revenue'] for d in dates]
    bookings_data = [daily_data[d]['bookings'] for d in dates]
    
    route_stats = {}
    bookings_with_flight = db.session.query(Booking, Flight).join(Flight, Booking.flight_id == Flight.id).all()
    
    for booking, flight in bookings_with_flight:
        route = f"{flight.origin} → {flight.destination}"
        if route not in route_stats:
            route_stats[route] = {'bookings': 0, 'revenue': 0}
        route_stats[route]['bookings'] += 1
        price_str = booking.total_price.replace('₱', '').replace(',', '')
        try:
            price = float(price_str)
            route_stats[route]['revenue'] += price
        except:
            pass
    
    top_routes = sorted(route_stats.items(), key=lambda x: x[1]['revenue'], reverse=True)[:5]
    top_routes_list = [{'route': r[0], 'bookings': r[1]['bookings'], 'revenue': f"{r[1]['revenue']:,.2f}"} for r in top_routes]
    
    total_revenue = sum(daily_data[d]['revenue'] for d in daily_data)
    total_bookings = sum(daily_data[d]['bookings'] for d in daily_data)
    
    return jsonify({
        'dates': dates,
        'revenue': revenue_data,
        'bookings': bookings_data,
        'top_routes': top_routes_list,
        'total_revenue': f"{total_revenue:,.2f}",
        'total_bookings': total_bookings
    })

# ----- SYSTEM SETTINGS API -----

@app.route('/api/admin/settings', methods=['GET'])
@admin_required
def api_get_settings():
    settings = {
        'site_name': get_system_setting('site_name', 'AeroTicket'),
        'contact_email': get_system_setting('contact_email', 'support@aeroticket.com'),
        'contact_phone': get_system_setting('contact_phone', '+1 (555) 123-4567'),
        'address': get_system_setting('address', '123 Aviation Blvd, Airport City'),
        'booking_fee': float(get_system_setting('booking_fee', 0)),
        'tax_rate': float(get_system_setting('tax_rate', 0)),
        'maintenance': get_system_setting('maintenance', 'false') == 'true'
    }
    return jsonify(settings)

@app.route('/api/admin/settings', methods=['PUT'])
@admin_required
def api_update_settings():
    data = request.json
    
    for key, value in data.items():
        set_system_setting(key, value)
    
    return jsonify({'success': True})

@app.route('/api/admin/maintenance', methods=['POST'])
@admin_required
def api_toggle_maintenance():
    data = request.json
    enabled = data.get('enabled', False)
    set_system_setting('maintenance', 'true' if enabled else 'false')
    
    return jsonify({'success': True, 'maintenance': enabled})

@app.route('/api/admin/clear-cache', methods=['POST'])
@admin_required
def api_clear_cache():
    return jsonify({'success': True, 'message': 'Cache cleared successfully'})

@app.route('/api/admin/backup', methods=['GET'])
@admin_required
def api_backup_database():
    import shutil
    backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    backup_path = os.path.join('backups', backup_filename)
    os.makedirs('backups', exist_ok=True)
    if os.path.exists('instance/aeroticket.db'):
        shutil.copy2('instance/aeroticket.db', backup_path)
    else:
        shutil.copy2('aeroticket.db', backup_path)
    
    return jsonify({'success': True, 'backup_file': backup_filename})

@app.route('/api/admin/export-all', methods=['GET'])
@admin_required
def api_export_all():
    import csv
    from io import StringIO
    from flask import Response
    
    output = StringIO()
    
    cw = csv.writer(output)
    cw.writerow(['=== USERS ==='])
    cw.writerow(['ID', 'Name', 'Email', 'Role', 'Status', 'Created At'])
    users = User.query.all()
    for u in users:
        cw.writerow([u.id, u.fullname or '', u.email, 'Admin' if u.is_admin else 'User', 
                    'Active' if u.is_active else 'Inactive', u.created_at])
    
    cw.writerow([])
    cw.writerow(['=== FLIGHTS ==='])
    cw.writerow(['ID', 'Flight #', 'Origin', 'Destination', 'Departure', 'Status'])
    flights = Flight.query.all()
    for f in flights:
        cw.writerow([f.id, f.flight_number, f.origin, f.destination, f.departure_date, f.status])
    
    cw.writerow([])
    cw.writerow(['=== BOOKINGS ==='])
    cw.writerow(['ID', 'Reference', 'User', 'Flight', 'Total', 'Status', 'Date'])
    bookings = Booking.query.all()
    for b in bookings:
        user = User.query.get(b.user_id) if b.user_id else None
        flight = Flight.query.get(b.flight_id)
        cw.writerow([b.id, b.booking_reference, user.email if user else 'Guest',
                    flight.flight_number if flight else 'N/A', b.total_price, b.status, b.booking_date])
    
    cw.writerow([])
    cw.writerow(['=== PROMO CODES ==='])
    cw.writerow(['ID', 'Code', 'Discount', 'Valid Until', 'Uses', 'Active'])
    promos = PromoCode.query.all()
    for p in promos:
        cw.writerow([p.id, p.code, f"{p.discount_value}%", p.valid_until, p.used_count, 'Yes' if p.is_active else 'No'])
    
    output.seek(0)
    return Response(output.getvalue(), mimetype='text/csv',
                   headers={"Content-Disposition": "attachment;filename=full_export.csv"})

# ==================== ADMIN DASHBOARD ROUTE ====================

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Access denied. Admin privileges required.")
        return redirect(url_for('home'))
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    total_users = User.query.count()
    total_bookings = Booking.query.count()
    total_flights = Flight.query.count()
    total_promos = PromoCode.query.filter_by(is_active=True).count()
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(10).all()
    
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    sales = db.session.query(db.func.sum(db.cast(Booking.total_price, db.Float))).filter(Booking.booking_date >= thirty_days_ago).scalar()
    sales_total = float(sales) if sales else 0
    
    all_users = User.query.all()
    all_flights = Flight.query.all()
    all_bookings = Booking.query.all()
    all_promos = PromoCode.query.all()
    active_promos = PromoCode.query.filter_by(is_active=True).count()
    total_promo_uses = db.session.query(db.func.sum(PromoCode.used_count)).scalar() or 0
    total_discount_given = 0
    
    settings = {
        'site_name': get_system_setting('site_name', 'AeroTicket'),
        'contact_email': get_system_setting('contact_email', 'support@aeroticket.com'),
        'contact_phone': get_system_setting('contact_phone', ''),
        'address': get_system_setting('address', ''),
        'booking_fee': get_system_setting('booking_fee', '0'),
        'tax_rate': get_system_setting('tax_rate', '0'),
        'maintenance': get_system_setting('maintenance', 'false') == 'true'
    }
    
    return render_template('admin_dashboard.html',
                          users=all_users,
                          events=all_flights,
                          all_users=all_users,
                          all_flights=all_flights,
                          all_bookings=all_bookings,
                          all_promos=all_promos,
                          active_promos=active_promos,
                          total_promo_uses=total_promo_uses,
                          total_discount_given=total_discount_given,
                          settings=settings,
                          total_users=total_users,
                          total_bookings=total_bookings,
                          total_flights=total_flights,
                          total_promos=total_promos,
                          sales_summary={'total': f"₱{sales_total:,.2f}"},
                          recent_bookings=recent_bookings,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== INFORMATION PAGES ====================
@app.route("/check_in", methods=['GET', 'POST'])
def check_in():
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    if request.method == 'POST':
        booking_ref = request.form.get('booking_ref')
        identifier = request.form.get('identifier', '').strip()
        check_in_as_member = request.form.get('check_in_as_member') == 'true'
        
        booking = Booking.query.filter_by(booking_reference=booking_ref).first()
        
        if not booking:
            flash("Booking not found. Please check your reference number.", "error")
            return redirect(url_for('check_in'))
        
        # ===== CHECK-IN TIME VALIDATIONS =====
        if booking.flight_id:
            flight = Flight.query.get(booking.flight_id)
            if flight:
                try:
                    # Parse departure date/time
                    dep_datetime_str = f"{flight.departure_date} {flight.departure_time}"
                    dep_time = None
                    try:
                        dep_time = datetime.strptime(dep_datetime_str, "%d %b %Y %I:%M %p")
                    except:
                        try:
                            dep_time = datetime.strptime(dep_datetime_str, "%d %b %Y %H:%M")
                        except:
                            dep_time = datetime.now() + timedelta(days=1)
                    
                    # Check-in closes 1 hour before departure
                    if datetime.now() > dep_time - timedelta(hours=1):
                        flash("Check-in is closed. Please proceed to the airport counter.", "error")
                        return redirect(url_for('check_in'))
                    
                    # Check-in opens 24 hours before departure
                    if datetime.now() < dep_time - timedelta(hours=24):
                        open_time = dep_time - timedelta(hours=24)
                        flash(f"Check-in opens 24 hours before departure. Please come back after {open_time.strftime('%Y-%m-%d %H:%M')}", "error")
                        return redirect(url_for('check_in'))
                        
                except Exception as e:
                    print(f"Check-in time validation error: {e}")
                    pass
        
        # Check if already checked in
        if booking.checked_in:
            flash("You have already checked in for this flight!", "warning")
            return redirect(url_for('view_ticket', id=booking.id))
        
        # ===== MEMBER CHECK-IN =====
        if check_in_as_member and session.get('user_id'):
            user = User.query.get(session.get('user_id'))
            
            # Check if this booking belongs to the logged-in user
            if booking.user_id == session.get('user_id'):
                booking.checked_in = True
                booking.check_in_time = datetime.utcnow()
                db.session.commit()
                session['show_success_popup'] = f"✓ Check-in successful! Welcome aboard, {user.fullname or user.email}!"
                return redirect(url_for('view_ticket', id=booking.id))
            
            # Check if user's name matches any passenger
            passengers = Passenger.query.filter_by(booking_id=booking.id).all()
            for passenger in passengers:
                if user.fullname and user.fullname.lower() in passenger.full_name.lower():
                    booking.checked_in = True
                    booking.check_in_time = datetime.utcnow()
                    db.session.commit()
                    session['show_success_popup'] = f"✓ Check-in successful for {passenger.full_name}!"
                    return redirect(url_for('view_ticket', id=booking.id))
            
            flash("This booking is not associated with your account.", "error")
            return redirect(url_for('check_in'))
        
        # ===== GUEST CHECK-IN =====
        if not identifier:
            flash("Please enter a passenger name or email to check in.", "error")
            return redirect(url_for('check_in'))
        
        # Check email match
        if booking.user_id:
            user = User.query.get(booking.user_id)
            if user and user.email.lower() == identifier.lower():
                booking.checked_in = True
                booking.check_in_time = datetime.utcnow()
                db.session.commit()
                session['show_success_popup'] = "Check-in successful! Welcome aboard!"
                return redirect(url_for('view_ticket', id=booking.id))
        
        # Check passenger name match
        passengers = Passenger.query.filter_by(booking_id=booking.id).all()
        for passenger in passengers:
            if identifier.lower() in passenger.full_name.lower():
                booking.checked_in = True
                booking.check_in_time = datetime.utcnow()
                db.session.commit()
                session['show_success_popup'] = f"Check-in successful for {passenger.full_name}!"
                return redirect(url_for('view_ticket', id=booking.id))
        
        flash("Booking found but identifier doesn't match. Please try again.", "error")
        return redirect(url_for('check_in'))
    
    return render_template("check_in.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)
@app.route("/about")
def about():
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template("About.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== MANAGE ROUTE ====================

@app.route("/manage", methods=['GET', 'POST'])
def manage():
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    if request.method == 'POST':
        booking_ref = request.form.get('booking_ref', '').strip().upper()
        identifier = request.form.get('identifier', '').strip()  # Can be email OR passenger name
        
        print(f"🔍 Searching for booking: {booking_ref}")
        print(f"   Identifier: {identifier}")
        
        # Search by booking reference
        booking = Booking.query.filter_by(booking_reference=booking_ref).first()
        
        if booking:
            print(f"   ✅ Booking found! ID: {booking.id}")
            
            # Check if identifier matches (email OR passenger name)
            match_found = False
            
            # Check if user is logged in and matches
            if session.get('user_id') and booking.user_id == session.get('user_id'):
                match_found = True
                print(f"   ✅ Match: Logged in user matches")
            
            # Check email match (if booking has user)
            if not match_found and booking.user_id:
                user = User.query.get(booking.user_id)
                if user and user.email.lower() == identifier.lower():
                    match_found = True
                    print(f"   ✅ Match: Email matches user: {user.email}")
            
            # Check passenger name match
            if not match_found:
                passengers = Passenger.query.filter_by(booking_id=booking.id).all()
                for passenger in passengers:
                    if identifier.lower() in passenger.full_name.lower():
                        match_found = True
                        print(f"   ✅ Match: Name matches passenger: {passenger.full_name}")
                        break
            
            if match_found:
                passengers = Passenger.query.filter_by(booking_id=booking.id).all()
                flight = Flight.query.get(booking.flight_id)
                
                return render_template('Manage.html', 
                                      booking_found=True,
                                      booking=booking,
                                      passengers=passengers,
                                      flight=flight,
                                      has_bookings=has_bookings,
                                      latest_booking_id=latest_booking_id)
            else:
                flash("Booking found but identifier doesn't match. Please use the passenger name or email used when booking.", "error")
                print(f"No match found!")
        else:
            flash("Booking not found. Please check your reference number.", "error")
            print(f"Booking not found for reference: {booking_ref}")
        
        return redirect(url_for('manage'))
    
    return render_template("Manage.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route("/travel")
def travel():
    has_bookings = False
    latest_booking_id = None
    
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template("travel_info.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route("/explore")
def explore():
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    # Get unique destinations from flights
    flights = Flight.query.all()
    flight_destinations = list(set([flight.destination.upper() for flight in flights if flight.destination]))
    
    return render_template("Explore.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id,
                          flight_destinations=flight_destinations)

# ==================== VIEW TICKET ROUTES ====================

@app.route('/view_ticket')
def view_ticket():
    booking_id = request.args.get('id')
    if not booking_id:
        flash('No ticket ID provided')
        return redirect(url_for('user_dashboard'))
    
    booking = Booking.query.get(booking_id)
    if not booking:
        flash('Ticket not found')
        return redirect(url_for('user_dashboard'))
    
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('user_dashboard'))
    
    # Get flight details
    flight = Flight.query.get(booking.flight_id)
    if not flight:
        flash('Flight information not found')
        return redirect(url_for('user_dashboard'))
    
    # Get passengers
    passengers = Passenger.query.filter_by(booking_id=booking.id).all()
    
    # Prepare passenger data for template (matching what JS expects)
    passenger_list = []
    for passenger in passengers:
        passenger_list.append({
            'id': passenger.id,
            'full_name': passenger.full_name,
            'name': passenger.full_name,
            'seat_number': passenger.seat_number,
            'seat': passenger.seat_number,
            'passenger_type': passenger.passenger_type
        })
    
    # Prepare flight data (matching what JS expects)
    flight_data = {
        'flight_number': flight.flight_number,
        'flight_no': flight.flight_number,
        'code': flight.flight_number,
        'gate': flight.gate,
        'gate_number': flight.gate,
        'origin': flight.origin,
        'from': flight.origin,
        'departure_airport': flight.origin,
        'destination': flight.destination,
        'to': flight.destination,
        'arrival_airport': flight.destination,
        'departure_date': flight.departure_date,
        'date': flight.departure_date,
        'departure_time': flight.departure_time,
        'time': flight.departure_time,
        'depart_time': flight.departure_time,
        'arrival_time': flight.arrival_time,
        'duration': flight.duration,
        'distance': flight.distance,
        'status': flight.status
    }
    
    # Prepare booking data
    booking_data = {
        'booking_reference': booking.booking_reference,
        'reference': booking.booking_reference,
        'pnr': booking.booking_reference,
        'cabin_class': booking.cabin_class,
        'class': booking.cabin_class,
        'total_price': booking.total_price,
        'total_passengers': booking.total_passengers,
        'booking_date': booking.booking_date.isoformat() if booking.booking_date else None,
        'status': booking.status,
        'payment_method': booking.payment_method,
        'payment_status': booking.payment_status
    }
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    # Pass data as JSON to template for JavaScript to parse
    import json
    return render_template('view_ticket.html', 
                          booking=booking_data,
                          booking_json=json.dumps(booking_data),
                          flight=flight_data,
                          flight_json=json.dumps(flight_data),
                          passengers=passenger_list,
                          passengers_json=json.dumps(passenger_list),
                          booking_reference=booking.booking_reference,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route('/api/booking/<int:booking_id>')
def api_get_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    flight = Flight.query.get(booking.flight_id)
    passengers = Passenger.query.filter_by(booking_id=booking.id).all()
    
    return jsonify({
        'booking': {
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'cabin_class': booking.cabin_class,
            'total_price': booking.total_price,
            'total_passengers': booking.total_passengers,
            'status': booking.status
        },
        'flight': {
            'id': flight.id,
            'flight_number': flight.flight_number,
            'origin': flight.origin,
            'destination': flight.destination,
            'departure_date': flight.departure_date,
            'departure_time': flight.departure_time,
            'arrival_time': flight.arrival_time,
            'duration': flight.duration,
            'distance': flight.distance,
            'gate': flight.gate,
            'status': flight.status
        },
        'passengers': [{
            'id': p.id,
            'full_name': p.full_name,
            'seat_number': p.seat_number,
            'passenger_type': p.passenger_type
        } for p in passengers],
        # ===== ADD THIS SECTION =====
        'check_in': {
            'checked_in': booking.checked_in,
            'check_in_time': booking.check_in_time.isoformat() if booking.check_in_time else None
        }
    })
@app.route('/api/passenger/<int:passenger_id>', methods=['PUT'])
def api_update_passenger(passenger_id):
    data = request.get_json()
    new_name = data.get('name')
    if not new_name:
        return jsonify({'error': 'Name required'}), 400
    passenger = Passenger.query.get_or_404(passenger_id)
    booking = Booking.query.get(passenger.booking_id)
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    passenger.full_name = new_name.upper()
    db.session.commit()
    return jsonify({'success': True, 'message': 'Passenger updated'})

@app.route('/api/passenger/<int:passenger_id>/seat', methods=['PUT'])
def api_update_passenger_seat(passenger_id):
    data = request.get_json()
    new_seat = data.get('seat')
    if not new_seat:
        return jsonify({'error': 'Seat required'}), 400
    passenger = Passenger.query.get_or_404(passenger_id)
    booking = Booking.query.get(passenger.booking_id)
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    passenger.seat_number = new_seat
    db.session.commit()
    return jsonify({'success': True, 'message': 'Seat updated'})

@app.route('/api/passenger/<int:passenger_id>', methods=['DELETE'])
def api_delete_passenger(passenger_id):
    passenger = Passenger.query.get_or_404(passenger_id)
    booking = Booking.query.get(passenger.booking_id)
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(passenger)
    if Passenger.query.filter_by(booking_id=booking.id).count() == 0:
        booking.status = 'Cancelled'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Passenger ticket cancelled'})

@app.route('/api/ticket/<int:booking_id>')
def api_get_ticket(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    passenger = Passenger.query.filter_by(booking_id=booking.id).first()
    if not passenger:
        return jsonify({'error': 'Passenger not found'}), 404
    
    flight = Flight.query.get(booking.flight_id)
    return jsonify({
        'booking': {
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'cabin_class': booking.cabin_class,
            'status': booking.status,
            'total_price': booking.total_price
        },
        'passenger': {
            'id': passenger.id,
            'full_name': passenger.full_name,
            'seat_number': passenger.seat_number,
            'passenger_type': passenger.passenger_type
        },
        'flight': {
            'id': flight.id,
            'flight_number': flight.flight_number,
            'origin': flight.origin,
            'destination': flight.destination,
            'departure_date': flight.departure_date,
            'departure_time': flight.departure_time,
            'arrival_time': flight.arrival_time,
            'gate': flight.gate,
            'status': flight.status
        }
    })

# ==================== ADMIN SETTINGS ROUTES ====================

@app.route('/admin/settings')
def admin_settings():
    if not session.get('is_admin'):
        flash("Access denied. Admin privileges required.")
        return redirect(url_for('home'))
    
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    flights = Flight.query.order_by(Flight.departure_date).all()
    promo_codes = PromoCode.query.filter(PromoCode.valid_until >= datetime.utcnow()).all()
    
    taxes = {
        'sales_tax': float(get_system_setting('sales_tax', 10)),
        'service_fee': float(get_system_setting('service_fee', 5)),
        'airport_fee': float(get_system_setting('airport_fee', 4.50)),
        'security_fee': float(get_system_setting('security_fee', 5.60))
    }
    
    refund_settings = {
        'show_refundable_only_default': get_system_setting('show_refundable_only_default', 'false') == 'true',
        'refundable_surcharge': float(get_system_setting('refundable_surcharge', 15)),
        'cancellation_window_hours': int(get_system_setting('cancellation_window_hours', 2)),
        'refund_processing_fee': float(get_system_setting('refund_processing_fee', 25))
    }
    
    class_settings = {
        'default_search_preference': get_system_setting('default_search_preference', 'lowest'),
        'show_premium_economy': get_system_setting('show_premium_economy', 'true') == 'true',
        'premium_economy_surcharge': float(get_system_setting('premium_economy_surcharge', 30)),
        'business_class_surcharge': float(get_system_setting('business_class_surcharge', 75)),
        'first_class_surcharge': float(get_system_setting('first_class_surcharge', 150))
    }
    
    system_settings = {
        'departure_window_days': int(get_system_setting('departure_window_days', 365)),
        'checkin_opens_hours': int(get_system_setting('checkin_opens_hours', 24)),
        'checkin_closes_hours': int(get_system_setting('checkin_closes_hours', 1)),
        'max_passengers_per_booking': int(get_system_setting('max_passengers_per_booking', 9)),
        'enable_hotels': get_system_setting('enable_hotels', 'true') == 'true',
        'enable_cars': get_system_setting('enable_cars', 'true') == 'true'
    }
    
    return render_template('admin_settings.html', 
                         flights=flights,
                         promo_codes=promo_codes,
                         taxes=taxes,
                         refund_settings=refund_settings,
                         class_settings=class_settings,
                         system_settings=system_settings,
                         has_bookings=has_bookings,
                         latest_booking_id=latest_booking_id)

@app.route('/admin/add_flight', methods=['POST'])
def add_flight():
    if not session.get('is_admin'):
        flash("Access denied. Admin privileges required.")
        return redirect(url_for('home'))
    
    try:
        flight_number = request.form.get('flight_number')
        origin = request.form.get('origin').upper()
        destination = request.form.get('destination').upper()
        departure_date = request.form.get('departure_date')
        departure_time = request.form.get('departure_time')
        arrival_time = request.form.get('arrival_time')
        economy_price = request.form.get('economy_price', '2,100')
        premium_economy_price = request.form.get('premium_economy_price', '4,500')
        business_price = request.form.get('business_price', '8,500')
        first_class_price = request.form.get('first_class_price', '15,000')
        gate = request.form.get('gate', 'A1')
        
        new_flight = Flight(
            flight_number=flight_number,
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration="N/A",
            distance="N/A",
            economy_price=economy_price,
            premium_economy_price=premium_economy_price,
            business_price=business_price,
            first_class_price=first_class_price,
            gate=gate
        )
        
        db.session.add(new_flight)
        db.session.commit()
        session['show_success_popup'] = f"Flight {flight_number} added successfully!"
        return redirect(url_for('admin_settings'))
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding flight: {str(e)}", "error")
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/flight/status', methods=['POST'])
def update_flight_status():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    flight_id = data.get('flight_id')
    status = data.get('status')
    
    flight = Flight.query.get(flight_id)
    if flight:
        flight.status = status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Flight not found'}), 404

@app.route('/admin/flight/delete/<int:flight_id>', methods=['POST'])
def delete_flight(flight_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    flight = Flight.query.get(flight_id)
    if flight:
        db.session.delete(flight)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Flight not found'}), 404

@app.route('/admin/promo/add', methods=['POST'])
def add_promo_code():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('home'))
    
    code = request.form.get('promo_code', '').upper()
    discount_type = request.form.get('discount_type')
    discount_value = float(request.form.get('discount_value'))
    valid_until = datetime.strptime(request.form.get('valid_until'), '%Y-%m-%d')
    max_uses = request.form.get('max_uses')
    min_amount = request.form.get('min_amount')
    
    promo = PromoCode(
        code=code,
        discount_type=discount_type,
        discount_value=discount_value,
        valid_until=valid_until,
        max_uses=int(max_uses) if max_uses else None,
        min_amount=float(min_amount) if min_amount else None
    )
    
    db.session.add(promo)
    db.session.commit()
    session['show_success_popup'] = f"Promo code {code} added successfully!"
    return redirect(url_for('admin_settings'))

@app.route('/admin/promo/delete/<int:promo_id>', methods=['POST'])
def delete_promo_code(promo_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    promo = PromoCode.query.get(promo_id)
    if promo:
        db.session.delete(promo)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Promo code not found'}), 404

@app.route('/admin/update_taxes', methods=['POST'])
def update_taxes():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('home'))
    
    set_system_setting('sales_tax', request.form.get('sales_tax'))
    set_system_setting('service_fee', request.form.get('service_fee'))
    set_system_setting('airport_fee', request.form.get('airport_fee'))
    set_system_setting('security_fee', request.form.get('security_fee'))
    
    session['show_success_popup'] = "Tax settings updated successfully!"
    return redirect(url_for('admin_settings'))

@app.route('/admin/update_refund_settings', methods=['POST'])
def update_refund_settings():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('home'))
    
    set_system_setting('show_refundable_only_default', 'true' if request.form.get('show_refundable_only_default') else 'false')
    set_system_setting('refundable_surcharge', request.form.get('refundable_surcharge'))
    set_system_setting('cancellation_window_hours', request.form.get('cancellation_window_hours'))
    set_system_setting('refund_processing_fee', request.form.get('refund_processing_fee'))
    
    session['show_success_popup'] = "Refund settings updated successfully!"
    return redirect(url_for('admin_settings'))

@app.route('/admin/update_class_settings', methods=['POST'])
def update_class_settings():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('home'))
    
    set_system_setting('default_search_preference', request.form.get('default_search_preference'))
    set_system_setting('show_premium_economy', 'true' if request.form.get('show_premium_economy') == 'yes' else 'false')
    set_system_setting('premium_economy_surcharge', request.form.get('premium_economy_surcharge'))
    set_system_setting('business_class_surcharge', request.form.get('business_class_surcharge'))
    set_system_setting('first_class_surcharge', request.form.get('first_class_surcharge'))
    
    session['show_success_popup'] = "Class settings updated successfully!"
    return redirect(url_for('admin_settings'))

@app.route('/admin/update_system_settings', methods=['POST'])
def update_system_settings():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('home'))
    
    set_system_setting('departure_window_days', request.form.get('departure_window_days'))
    set_system_setting('checkin_opens_hours', request.form.get('checkin_opens_hours'))
    set_system_setting('checkin_closes_hours', request.form.get('checkin_closes_hours'))
    set_system_setting('max_passengers_per_booking', request.form.get('max_passengers_per_booking'))
    set_system_setting('enable_hotels', 'true' if request.form.get('enable_hotels') == 'yes' else 'false')
    set_system_setting('enable_cars', 'true' if request.form.get('enable_cars') == 'yes' else 'false')
    
    session['show_success_popup'] = "System settings updated successfully!"
    return redirect(url_for('admin_settings'))

@app.route('/admin/ban_user/<int:user_id>')
def admin_ban_user(user_id):
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        session['show_success_popup'] = f"User {user.email} has been deleted."
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reset_password/<int:user_id>')
def admin_reset_password(user_id):
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    user = User.query.get(user_id)
    if user:
        new_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
        user.password = generate_password_hash(new_password)
        db.session.commit()
        session['show_success_popup'] = f"Password for {user.email} reset to: {new_password}"
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear_cache')
def admin_clear_cache():
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    session['show_success_popup'] = "Cache cleared successfully!"
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/maintenance', methods=['POST'])
def admin_maintenance():
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    session['maintenance_mode'] = not session.get('maintenance_mode', False)
    session['show_success_popup'] = f"Maintenance mode {'enabled' if session['maintenance_mode'] else 'disabled'}."
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/export_sales')
def admin_export_sales():
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    import csv
    from io import StringIO
    from flask import Response
    bookings = Booking.query.all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Booking Ref', 'User ID', 'Flight ID', 'Passengers', 'Total', 'Date', 'Status'])
    for b in bookings:
        cw.writerow([b.booking_reference, b.user_id, b.flight_id, b.total_passengers, b.total_price, b.booking_date, b.status])
    output = si.getvalue()
    return Response(output, mimetype='text/csv', headers={"Content-Disposition": "attachment;filename=sales.csv"})

@app.route('/add_integration', methods=['POST'])
def add_integration():
    name = request.form.get('name')
    logo = request.form.get('logo')
    if name and logo:
        payment_methods.append({"name": name, "logo": logo})
        session['show_success_popup'] = f"Success! {name} has been integrated."
    return redirect(url_for('payment'))

@app.route('/delete_integration/<int:index>', methods=['POST'])
def delete_integration(index):
    try:
        removed_item = payment_methods.pop(index)
        session['show_success_popup'] = f"Removed {removed_item['name']} integration."
    except IndexError:
        flash("Error: Integration not found.")
    return redirect(url_for('payment'))

@app.route('/api/checkin_status/<booking_reference>')
def api_checkin_status(booking_reference):
    booking = Booking.query.filter_by(booking_reference=booking_reference).first()
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404
    
    return jsonify({
        'checked_in': booking.checked_in,
        'check_in_time': booking.check_in_time.isoformat() if booking.check_in_time else None,
        'can_check_in': not booking.checked_in
    })

# ==================== DATABASE INITIALIZATION ====================

if __name__ == "__main__":
    with app.app_context():
        # Add missing columns if they don't exist
        try:
            db.session.execute('ALTER TABLE all_users ADD COLUMN is_active BOOLEAN DEFAULT 1')
            db.session.commit()
        except:
            pass
        
        try:
            db.session.execute('ALTER TABLE promo_codes ADD COLUMN description VARCHAR(200)')
            db.session.commit()
        except:
            pass
        
        try:
            db.session.execute('ALTER TABLE promo_codes ADD COLUMN valid_from DATETIME')
            db.session.commit()
        except:
            pass
        
        db.create_all()
        create_sample_flights()
        
        # Create sample promo codes for testing
        if not PromoCode.query.filter_by(code="WELCOME10").first():
            sample_promo = PromoCode(
                code="WELCOME10",
                description="Welcome discount for new users",
                discount_type="percentage",
                discount_value=10.0,
                valid_from=datetime.utcnow(),
                valid_until=datetime.utcnow() + timedelta(days=30),
                max_uses=100,
                min_amount=500,
                is_active=True
            )
            db.session.add(sample_promo)
            db.session.commit()
            print("✅ Sample promo code created: WELCOME10 (10% off)")
        
        if not PromoCode.query.filter_by(code="SUMMER25").first():
            summer_promo = PromoCode(
                code="SUMMER25",
                description="Summer Sale - 25% off on all flights",
                discount_type="percentage",
                discount_value=25.0,
                valid_from=datetime.utcnow(),
                valid_until=datetime.utcnow() + timedelta(days=60),
                max_uses=500,
                min_amount=1000,
                is_active=True
            )
            db.session.add(summer_promo)
            db.session.commit()
            print("✅ Sample promo code created: SUMMER25 (25% off)")
        
        # Create admin user if not exists
        if not User.query.filter_by(email="admin@aeroticket.com").first():
            admin = User(
                fullname="Administrator",
                email="admin@aeroticket.com",
                password=generate_password_hash("admin123"),
                is_admin=True,
                is_active=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin@aeroticket.com / admin123")
    
    app.run(debug=True)