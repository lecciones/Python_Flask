from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import random
import string
import os

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
    discount_type = db.Column(db.String(20), nullable=False)
    discount_value = db.Column(db.Float, nullable=False)
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

# ==================== MAIN ROUTES ====================

@app.route("/")
def home():
    # Get has_bookings and latest_booking_id for header
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
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['is_admin'] = user.is_admin
            flash("Login successful!")
            return redirect(url_for("home"))
        
        flash("Invalid email or password.")
        return render_template("Login_form.html", step="password" if step == "password" else "email", email=email)

    # GET request - pass empty values for header consistency
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
                       password=hashed_password, provider=provider)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in with your credentials.")
        return redirect(url_for("login")) 
    
    flash("Account already exists. Try logging in.")
    return redirect(url_for("login"))

@app.route('/signup')
def signup():
    if 'user_id' in session:
        return redirect(url_for('home'))
    
    # Get has_bookings and latest_booking_id for header (not logged in, so false)
    has_bookings = False
    latest_booking_id = None
    
    return render_template('signup.html', 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== FIXED GOOGLE LOGIN ====================
@app.route('/login/google', methods=['GET', 'POST'])
def google_login():
    if request.method == 'POST':
        step = request.form.get("step")
        email = request.form.get("email")
        password = request.form.get("password")

        if step == "email":
            # Check if email exists in SocialUser table for Google provider
            user = SocialUser.query.filter_by(email=email, provider='google').first()
            if not user:
                flash("No account found with that email. Please sign up first.")
                return render_template("google.html", email=email)
            # Email found, go to password page
            return render_template("google_log.html", email=email)
            
        elif step == "password":
            user = SocialUser.query.filter_by(email=email, provider='google').first()
            if user:
                if check_password_hash(user.password, password):
                    session['user_id'] = user.id
                    session['auth_type'] = 'google'
                    session['is_admin'] = False
                    flash("Login successful!")
                    return redirect(url_for('home'))
                else:
                    # STAY ON google_log.html - show error below password
                    flash("Wrong password. Please try again.")
                    return render_template("google_log.html", email=email)
            else:
                # Create new account
                hashed_pw = generate_password_hash(password)
                new_google_user = SocialUser(email=email, fullname=email.split('@')[0],
                                            password=hashed_pw, provider='google')
                db.session.add(new_google_user)
                db.session.commit()
                flash("Google account registered! Please log in.")
                return redirect(url_for('login'))
    
    # GET request - show email page
    return render_template('google.html')

# ==================== FIXED APPLE LOGIN ====================
@app.route('/login/apple', methods=['GET', 'POST'])
def apple_login():
    if request.method == 'POST':
        email = request.form.get("apple_email")
        password = request.form.get("apple_password")
        user = SocialUser.query.filter_by(email=email, provider='apple').first()
        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['auth_type'] = 'apple'
                session['is_admin'] = False
                flash("Login successful!")
                return redirect(url_for('home'))
            else:
                # STAY ON apple.html - show error below password
                flash("Incorrect Apple ID password. Please try again.")
                return render_template("apple.html", email=email)
        else:
            # Create new account
            hashed_pw = generate_password_hash(password)
            new_user = SocialUser(email=email, password=hashed_pw, provider='apple')
            db.session.add(new_user)
            db.session.commit()
            flash("Apple account registered! Please log in.")
            return redirect(url_for('login'))
    return render_template("apple.html")

# ==================== FIXED WECHAT LOGIN ====================
@app.route('/login/wechat', methods=['GET', 'POST'])
def wechat_login():
    mode = request.args.get('mode', 'login')
    
    if request.method == 'POST':
        email = request.form.get("wechat_email")
        password = request.form.get("password")
        user = SocialUser.query.filter_by(email=email, provider='wechat').first()
        
        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['auth_type'] = 'wechat'
                session['is_admin'] = False
                flash("Welcome back!")
                return redirect(url_for('home'))
            else:
                # STAY ON wechat.html - show error below password
                flash("Incorrect password for this WeChat account. Please try again.")
                return render_template('wechat.html', mode='login', email=email)
        else:
            # Create new account
            hashed_pw = generate_password_hash(password)
            new_wechat_user = SocialUser(email=email, fullname=email.split('@')[0],
                                        password=hashed_pw, provider='wechat')
            try:
                db.session.add(new_wechat_user)
                db.session.commit()
                flash("WeChat account registered successfully! Please sign in.")
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
    flash("Logged out successfully.")
    return redirect(url_for("home"))

# ==================== FLIGHT BOOKING ROUTES ====================

@app.route("/flight")
def flight():
    # --- Read origin & destination from separate params (sent by home.html hidden fields) ---
    # Support both "departure_code" (hidden field) and "departure" (fallback) for origin
    search_origin = request.args.get('departure_code', '').lower().strip()
    if not search_origin:
        search_origin = request.args.get('departure', '').lower().strip()

    search_destination = request.args.get('arrival', '').lower().strip()

    # If origin still contains an arrow (old format: "cebu → dubai"), parse it
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

    # --- Check if user has any bookings and get latest booking ID ---
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0

        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id

    # --- Route data ---
    route_data = {
        ("cebu", "manila"):    ("1h 25m", "566 km"),
        ("manila", "cebu"):    ("1h 30m", "566 km"),
        ("cebu", "davao"):     ("1h 05m", "410 km"),
        ("davao", "cebu"):     ("1h 10m", "410 km"),
        ("manila", "davao"):   ("1h 50m", "964 km"),
        ("davao", "manila"):   ("1h 55m", "964 km"),
        ("cebu", "dubai"):     ("9h 00m", "6,889 km"),
        ("dubai", "cebu"):     ("9h 30m", "6,889 km"),
        ("manila", "dubai"):   ("8h 45m", "6,521 km"),
        ("dubai", "manila"):   ("9h 00m", "6,521 km"),
        ("cebu", "hongkong"):  ("2h 10m", "1,145 km"),
        ("hongkong", "cebu"):  ("2h 20m", "1,145 km"),
        ("manila", "hongkong"):("1h 55m", "1,109 km"),
        ("hongkong", "manila"):("2h 05m", "1,109 km"),
        ("cebu", "singapore"): ("3h 30m", "2,380 km"),
        ("singapore", "cebu"): ("3h 40m", "2,380 km"),
        ("manila", "singapore"):("3h 20m", "2,400 km"),
        ("singapore", "manila"):("3h 30m", "2,400 km"),
    }

    # --- Build flight list ---
    all_flights = []
    times = [
        ("06:00", "07:30"), ("09:00", "10:30"), ("12:00", "13:30"),
        ("15:00", "16:30"), ("18:00", "19:30"), ("21:00", "22:30")
    ]

    economy_prices = {
        ("cebu", "manila"): "2,100",    ("manila", "cebu"): "2,100",
        ("cebu", "davao"): "1,900",     ("davao", "cebu"): "1,900",
        ("manila", "davao"): "2,300",   ("davao", "manila"): "2,300",
        ("cebu", "dubai"): "18,500",    ("dubai", "cebu"): "18,500",
        ("manila", "dubai"): "17,500",  ("dubai", "manila"): "17,500",
        ("cebu", "hongkong"): "6,500",  ("hongkong", "cebu"): "6,500",
        ("manila", "hongkong"): "5,800",("hongkong", "manila"): "5,800",
        ("cebu", "singapore"): "8,200", ("singapore", "cebu"): "8,200",
        ("manila", "singapore"): "7,900",("singapore", "manila"): "7,900",
    }

    premium_multipliers = {
        "Premium Economy": 2.0,
        "Business/Premium Flatbed": 4.0,
        "First Class": 7.0
    }

    for (origin, dest), (duration, distance) in route_data.items():
        base_eco = int(economy_prices.get((origin, dest), "2100").replace(",", ""))

        for t_type in ["One-way", "Round-trip"]:
            # Economy — 3 time slots
            for i in range(3):
                dep, arr = times[i]
                all_flights.append({
                    "origin": origin, "destination": dest,
                    "class": "Economy",
                    "departure": dep, "arrival": arr,
                    "price": f"{base_eco:,}",
                    "type": t_type,
                    "duration": duration, "distance": distance
                })

            # Premium cabins — 1-3 time slots each
            for cabin, multiplier in premium_multipliers.items():
                cabin_price = int(base_eco * multiplier)
                num_flights = random.randint(1, 3)
                for i in range(num_flights):
                    dep, arr = times[i + 3]
                    all_flights.append({
                        "origin": origin, "destination": dest,
                        "class": cabin,
                        "departure": dep, "arrival": arr,
                        "price": f"{cabin_price:,}",
                        "type": t_type,
                        "duration": duration, "distance": distance
                    })

    # --- Filter flights based on search ---
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
        flight_time=flight_time,
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
    
    # Check if user has any bookings and get latest booking ID
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        # Get the most recent booking ID for the View Ticket link
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
    
    passenger_data = {
        "adults": request.args.get('adults', 1),
        "children": request.args.get('children', 0),
        "infants": request.args.get('infants', 0),
        "cabin": cabin_class
    }
    
    # Check if user has any bookings and get latest booking ID
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        # Get the most recent booking ID
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
                          flight_no=flight_no,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== PAYMENT ROUTES ====================
@app.route('/payment', methods=['GET', 'POST']) 
def payment():
    amount = request.args.get('price', request.args.get('amount', '0.00'))
    
    if amount == '0.00' and session.get('total_price'):
        amount = session.get('total_price')
    
    # Get has_bookings and latest_booking_id for header
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
            booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            session['booking_reference'] = booking_ref
            session['payment_status'] = 'Completed'
            session['payment_method'] = 'GCash'
            session['paid_amount'] = clean_amount
            save_booking_to_database(booking_ref, clean_amount, 'GCash')
            return jsonify({'success': True, 'booking_ref': booking_ref})
        return jsonify({'success': False}), 400
    return render_template('gcash.html', amount=clean_amount)

@app.route('/paytm', methods=['GET', 'POST'])
def paytm_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'PayTM'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'PayTM')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('paytm.html', amount=clean_amount)

@app.route('/paypal', methods=['GET', 'POST'])
def paypal_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'PayPal'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'PayPal')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('paypal.html', amount=clean_amount)

@app.route('/grabpay', methods=['GET', 'POST'])
def grabpay_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'GrabPay'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'GrabPay')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('grabpay.html', amount=clean_amount)

@app.route('/atome', methods=['GET', 'POST'])
def atome_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Atome'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'Atome')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('atome.html', amount=clean_amount)

@app.route('/alipay', methods=['GET', 'POST'])
def alipay_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Alipay'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'Alipay')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('alipay.html', amount=clean_amount)

@app.route('/apple', methods=['GET', 'POST'])
def apple_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Apple Pay'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'Apple Pay')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('apple_pay.html', amount=clean_amount)

@app.route('/hoolah', methods=['GET', 'POST'])
def hoolah_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'Hoolah'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'Hoolah')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('hoolah.html', amount=clean_amount)

@app.route('/ovo', methods=['GET', 'POST'])
def ovo_payment():
    amount = request.args.get('amount', '0.00')
    if amount == '0.00':
        amount = session.get('payment_amount', session.get('total_price', '0.00'))
    clean_amount = amount.replace('₱', '').replace(',', '').strip()
    if request.method == 'POST':
        booking_ref = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        session['booking_reference'] = booking_ref
        session['payment_status'] = 'Completed'
        session['payment_method'] = 'OVO'
        session['paid_amount'] = clean_amount
        save_booking_to_database(booking_ref, clean_amount, 'OVO')
        return jsonify({'success': True, 'booking_ref': booking_ref})
    return render_template('ovo.html', amount=clean_amount)

def save_booking_to_database(booking_ref, amount, payment_method):
    try:
        flight_no = session.get('flight_no', 'AT0000')
        origin = session.get('origin', '')
        destination = session.get('destination', '')
        flight_date = session.get('date', '')
        flight_time = session.get('time', '')
        cabin_class = session.get('flight_class', 'Economy')
        passengers = session.get('all_passengers', [])
        
        flight = Flight.query.filter_by(flight_number=flight_no).first()
        if not flight:
            flight = Flight(
                flight_number=flight_no,
                origin=origin,
                destination=destination,
                departure_date=flight_date,
                departure_time=flight_time,
                arrival_time=flight_time,
                duration="N/A",
                distance="N/A",
                gate="A1"
            )
            db.session.add(flight)
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
        print(f"\n✅ BOOKING SAVED TO DATABASE: {booking_ref}")
        return True
    except Exception as e:
        print(f"\n ERROR SAVING BOOKING: {str(e)}")
        db.session.rollback()
        return False

# ==================== TICKET ROUTES ====================

@app.route("/ticket")
def ticket():
    print("=" * 60)
    print("TICKET ROUTE - Reading from session:")
    print(f"  session.get('all_passengers'): {session.get('all_passengers')}")
    print(f"  session.get('origin'): {session.get('origin')}")
    print(f"  session.get('destination'): {session.get('destination')}")
    print(f"  session.get('flight_class'): {session.get('flight_class')}")
    print(f"  session.get('flight_no'): {session.get('flight_no')}")
    print(f"  session.get('date'): {session.get('date')}")
    print(f"  session.get('time'): {session.get('time')}")
    print(f"  session.get('gate'): {session.get('gate')}")
    print("=" * 60)
    
    passengers = session.get('all_passengers')
    if not passengers:
        passengers = [{'name': 'NO DATA', 'seat': '---'}]
        flash("No booking data found. Please complete your booking first.")
    
    flight_data = {
        "flight": session.get('flight_no', 'AT0000'),
        "gate": session.get('gate', '01'),
        "origin": session.get('origin', '---'),
        "destination": session.get('destination', '---'),
        "date": session.get('date', '---'),
        "time": session.get('time', '---'),
        "class": session.get('flight_class', 'ECONOMY').upper()
    }
    
    # Get has_bookings and latest_booking_id for header
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
                          passengers=passengers, 
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
        flash("Profile picture updated!")
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
    
    # Get has_bookings and latest_booking_id for header
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
    
    # Get has_bookings and latest_booking_id for header
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
            flash("Profile updated successfully.")
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
                flash("Password changed successfully.")
            return redirect(url_for('user_settings'))
        
        elif action == 'update_notifications':
            user.email_reminders = 'email_reminders' in request.form
            db.session.commit()
            flash("Notification preferences updated.")
            return redirect(url_for('user_settings'))
        
        elif action == 'delete_account':
            Booking.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            session.clear()
            flash("Your account has been permanently deleted.")
            return redirect(url_for('home'))
    
    return render_template('user_settings.html', 
                          user=user, 
                          phone=user.phone or '',
                          email_reminders=user.email_reminders,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== ADMIN DASHBOARD ====================

@app.route('/admin')
def admin_dashboard():
    if not session.get('is_admin'):
        flash("Access denied. Admin privileges required.")
        return redirect(url_for('home'))
    
    # Get has_bookings and latest_booking_id for header
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
    recent_bookings = Booking.query.order_by(Booking.booking_date.desc()).limit(10).all()
    
    thirty_days_ago = datetime.utcnow().replace(day=1)
    sales = db.session.query(db.func.sum(Booking.total_price)).filter(Booking.booking_date >= thirty_days_ago).scalar()
    sales_total = float(sales) if sales else 0
    
    users = User.query.all()
    events = Flight.query.all()
    
    settings = {
        'site_name': 'AeroTicket',
        'contact_email': 'support@aeroticket.com',
        'timezone': 'Asia/Manila',
        'global_max_tickets': 6,
        'waitlist_enabled': False,
        'tax_rate': 0,
        'maintenance': False
    }
    
    return render_template('admin_dashboard.html',
                          users=users,
                          events=events,
                          settings=settings,
                          total_users=total_users,
                          total_bookings=total_bookings,
                          total_flights=total_flights,
                          sales_summary={'total': f"₱{sales_total:,.2f}"},
                          recent_bookings=recent_bookings,
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route('/admin/ban_user/<int:user_id>')
def admin_ban_user(user_id):
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash(f"User {user.email} has been deleted.")
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
        flash(f"Password for {user.email} reset to: {new_password} (user must change after login)")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/clear_cache')
def admin_clear_cache():
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    flash("Cache cleared (simulated).")
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/maintenance', methods=['POST'])
def admin_maintenance():
    if not session.get('is_admin'):
        flash("Unauthorized.")
        return redirect(url_for('home'))
    session['maintenance_mode'] = not session.get('maintenance_mode', False)
    flash(f"Maintenance mode {'enabled' if session['maintenance_mode'] else 'disabled'}.")
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

# ==================== ADMIN SETTINGS ROUTES ====================

@app.route('/admin/settings')
def admin_settings():
    if not session.get('is_admin'):
        flash("Access denied. Admin privileges required.")
        return redirect(url_for('home'))
    
    # Get has_bookings and latest_booking_id for header
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
    """Add a new flight - CREATE operation"""
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
        flash(f"Flight {flight_number} added successfully!", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Error adding flight: {str(e)}", "error")
    
    return redirect(url_for('admin_settings'))

@app.route('/admin/flight/status', methods=['POST'])
def update_flight_status():
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    data = request.get_json()
    flight_id = data.get('flight_id')
    status = data.get('status')
    
    flight = Flight.query.get(flight_id)
    if flight:
        flight.status = status
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Flight not found'})

@app.route('/admin/flight/delete/<int:flight_id>', methods=['POST'])
def delete_flight(flight_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    flight = Flight.query.get(flight_id)
    if flight:
        db.session.delete(flight)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Flight not found'})

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
    flash(f"Promo code {code} added successfully!", "success")
    return redirect(url_for('admin_settings'))

@app.route('/admin/promo/delete/<int:promo_id>', methods=['POST'])
def delete_promo_code(promo_id):
    if not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})
    
    promo = PromoCode.query.get(promo_id)
    if promo:
        db.session.delete(promo)
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False, 'message': 'Promo code not found'})

@app.route('/admin/update_taxes', methods=['POST'])
def update_taxes():
    if not session.get('is_admin'):
        flash("Access denied.")
        return redirect(url_for('home'))
    
    set_system_setting('sales_tax', request.form.get('sales_tax'))
    set_system_setting('service_fee', request.form.get('service_fee'))
    set_system_setting('airport_fee', request.form.get('airport_fee'))
    set_system_setting('security_fee', request.form.get('security_fee'))
    
    flash("Tax settings updated successfully!", "success")
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
    
    flash("Refund settings updated successfully!", "success")
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
    
    flash("Class settings updated successfully!", "success")
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
    
    flash("System settings updated successfully!", "success")
    return redirect(url_for('admin_settings'))

# ==================== PAYMENT INTEGRATION ROUTES ====================

@app.route('/add_integration', methods=['POST'])
def add_integration():
    name = request.form.get('name')
    logo = request.form.get('logo')
    if name and logo:
        payment_methods.append({"name": name, "logo": logo})
        flash(f"Success! {name} has been integrated.")
    return redirect(url_for('payment'))

@app.route('/delete_integration/<int:index>', methods=['POST'])
def delete_integration(index):
    try:
        removed_item = payment_methods.pop(index)
        flash(f"Removed {removed_item['name']} integration.")
    except IndexError:
        flash("Error: Integration not found.")
    return redirect(url_for('payment'))

# ==================== INFORMATION PAGES ====================

@app.route("/check_in", methods=['GET', 'POST'])
def check_in():
    # Get has_bookings and latest_booking_id for header
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        booking_ref = request.form.get('booking_ref')
        identifier = request.form.get('identifier')
        
        # Find booking by reference
        booking = Booking.query.filter_by(booking_reference=booking_ref).first()
        
        if booking:
            # Check if user is logged in and owns the booking
            if session.get('user_id') and booking.user_id == session.get('user_id'):
                flash(f"Check-in successful! Welcome aboard!", "success")
                return redirect(url_for('view_ticket', id=booking.id))
            
            # Check by email if booking has a user
            if booking.user_id:
                user = User.query.get(booking.user_id)
                if user and user.email == identifier:
                    flash(f"Check-in successful! Welcome aboard!", "success")
                    return redirect(url_for('view_ticket', id=booking.id))
            
            # Check by passenger name (for guest bookings)
            passengers = Passenger.query.filter_by(booking_id=booking.id).all()
            for passenger in passengers:
                if identifier.lower() in passenger.full_name.lower():
                    flash(f"Check-in successful for {passenger.full_name}!", "success")
                    return redirect(url_for('view_ticket', id=booking.id))
            
            flash("Booking found but identifier doesn't match. Please try again.", "error")
        else:
            flash("Booking not found. Please check your reference number.", "error")
        
        return redirect(url_for('check_in'))
    
    # GET request - show the form
    return render_template("check_in.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route("/about")
def about():
    # About page - no header changes needed, but pass empty values for consistency
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

@app.route("/manage", methods=['GET', 'POST'])
def manage():
    # Check if user has any bookings (for Manage dropdown visibility)
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    # Handle POST request (form submission)
    if request.method == 'POST':
        booking_ref = request.form.get('booking_ref')
        email = request.form.get('email')
        
        # Find booking by reference
        booking = Booking.query.filter_by(booking_reference=booking_ref).first()
        
        if booking:
            # Check if the email matches the user's email
            if booking.user_id:
                user = User.query.get(booking.user_id)
                if user and user.email == email:
                    passengers = Passenger.query.filter_by(booking_id=booking.id).all()
                    flight = Flight.query.get(booking.flight_id)
                    
                    return render_template('Manage.html', 
                                          booking_found=True,
                                          booking=booking,
                                          passengers=passengers,
                                          flight=flight,
                                          has_bookings=has_bookings,
                                          latest_booking_id=latest_booking_id)
            
            # Also check if email matches any passenger's name (for guest bookings)
            passengers = Passenger.query.filter_by(booking_id=booking.id).all()
            for passenger in passengers:
                if email.lower() in passenger.full_name.lower():
                    flight = Flight.query.get(booking.flight_id)
                    
                    return render_template('Manage.html', 
                                          booking_found=True,
                                          booking=booking,
                                          passengers=passengers,
                                          flight=flight,
                                          has_bookings=has_bookings,
                                          latest_booking_id=latest_booking_id)
            
            flash("Booking found but email doesn't match. Please try again.", "error")
        else:
            flash("Booking not found. Please check your reference number.", "error")
        
        return redirect(url_for('manage'))
    
    # GET request - show the form
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
        
        # Get the most recent booking ID for the View Ticket link
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template("travel_info.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

@app.route("/explore")
def explore():
    # Get has_bookings and latest_booking_id for header
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template("Explore.html", 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# ==================== VIEW TICKET API ROUTES (MULTI-TICKET SUPPORT) ====================

@app.route('/view_ticket')
def view_ticket():
    """Render the view ticket page (multi-ticket carousel)"""
    booking_id = request.args.get('id')
    if not booking_id:
        flash('No ticket ID provided')
        return redirect(url_for('user_dashboard'))
    
    # Verify booking exists
    booking = Booking.query.get(booking_id)
    if not booking:
        flash('Ticket not found')
        return redirect(url_for('user_dashboard'))
    
    # Check authorization (user owns ticket or is admin)
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        flash('Access denied')
        return redirect(url_for('user_dashboard'))
    
    # Get has_bookings and latest_booking_id for header
    has_bookings = False
    latest_booking_id = None
    if session.get('user_id'):
        user_id = session.get('user_id')
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        has_bookings = booking_count > 0
        
        latest_booking = Booking.query.filter_by(user_id=user_id).order_by(Booking.id.desc()).first()
        if latest_booking:
            latest_booking_id = latest_booking.id
    
    return render_template('view_ticket.html', 
                          has_bookings=has_bookings,
                          latest_booking_id=latest_booking_id)

# NEW: Get full booking with all passengers (for carousel)
@app.route('/api/booking/<int:booking_id>')
def api_get_booking(booking_id):
    """Return booking details with all passengers and flight info"""
    booking = Booking.query.get_or_404(booking_id)
    # Authorization: only the booking owner or admin
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    
    passengers = Passenger.query.filter_by(booking_id=booking.id).all()
    flight = Flight.query.get(booking.flight_id)
    
    return jsonify({
        'booking': {
            'id': booking.id,
            'booking_reference': booking.booking_reference,
            'cabin_class': booking.cabin_class,
            'status': booking.status,
            'total_price': booking.total_price
        },
        'passengers': [{
            'id': p.id,
            'full_name': p.full_name,
            'seat_number': p.seat_number,
            'passenger_type': p.passenger_type
        } for p in passengers],
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

# NEW: Update a specific passenger's name
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

# NEW: Update a specific passenger's seat
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

# NEW: Delete a specific passenger (cancel individual ticket)
@app.route('/api/passenger/<int:passenger_id>', methods=['DELETE'])
def api_delete_passenger(passenger_id):
    passenger = Passenger.query.get_or_404(passenger_id)
    booking = Booking.query.get(passenger.booking_id)
    if booking.user_id != session.get('user_id') and not session.get('is_admin'):
        return jsonify({'error': 'Unauthorized'}), 403
    db.session.delete(passenger)
    # If no passengers left, cancel the entire booking
    if Passenger.query.filter_by(booking_id=booking.id).count() == 0:
        booking.status = 'Cancelled'
    db.session.commit()
    return jsonify({'success': True, 'message': 'Passenger ticket cancelled'})

# (Optional) Keep the old /api/ticket/<booking_id> for backward compatibility (returns first passenger)
@app.route('/api/ticket/<int:booking_id>')
def api_get_ticket(booking_id):
    """Legacy endpoint: returns first passenger for backward compatibility"""
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

# ==================== DATABASE INITIALIZATION ====================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_sample_flights()
        
        if not User.query.filter_by(email="admin@aeroticket.com").first():
            admin = User(
                fullname="Admin",
                email="admin@aeroticket.com",
                password=generate_password_hash("admin123"),
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin user created: admin@aeroticket.com / admin123")
    app.run(debug=True)