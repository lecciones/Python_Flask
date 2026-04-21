from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import random
import string

# ==================== APP CONFIGURATION ====================
app = Flask(__name__)
app.secret_key = 'aeroticket_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aeroticket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ==================== DATABASE MODELS ====================

class User(db.Model):
    """Regular user accounts with email/password"""
    __tablename__ = 'all_users' 
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) 
    provider = db.Column(db.String(20), default='email')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<User {self.email}>'
    
class SocialUser(db.Model):
    """Social media login accounts (Google, Apple, WeChat)"""
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
    """Flight information and schedules"""
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
    """Booking records linked to users and flights"""
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
    
    # Relationships
    user = db.relationship('User', backref='bookings')
    flight = db.relationship('Flight', backref='bookings')
    passengers = db.relationship('Passenger', backref='booking', cascade='all, delete-orphan')
    
    def generate_booking_reference(self):
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

class Passenger(db.Model):
    """Individual passenger details for each booking"""
    __tablename__ = 'passengers'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    seat_number = db.Column(db.String(5), nullable=False)
    passenger_type = db.Column(db.String(20), default="Adult")

class Seat(db.Model):
    """Seat availability per flight"""
    __tablename__ = 'seats'
    id = db.Column(db.Integer, primary_key=True)
    flight_id = db.Column(db.Integer, db.ForeignKey('flights.id'), nullable=False)
    seat_number = db.Column(db.String(5), nullable=False)
    is_available = db.Column(db.Boolean, default=True)
    cabin_class = db.Column(db.String(30), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    
    __table_args__ = (db.UniqueConstraint('flight_id', 'seat_number', name='_flight_seat_uc'),)

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

def create_sample_flights():
    """Create sample flight data if no flights exist"""
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
    """Home page route"""
    return render_template("Home_page.html")

# ==================== AUTHENTICATION ROUTES ====================

@app.route("/login", methods=["GET", "POST"])
def login():
    """User login with email/password"""
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
            flash("Login successful!")
            return redirect(url_for("home"))
        
        flash("Invalid email or password.")
        return render_template("Login_form.html", step="password" if step == "password" else "email", email=email)

    return render_template("Login_form.html", step="email")

@app.route("/register", methods=["POST"])
def register():
    """User registration"""
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
    """Signup page"""
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('signup.html')

@app.route('/login/google', methods=['GET', 'POST'])
def google_login():
    """Google login handler"""
    if request.method == 'POST':
        step = request.form.get("step")
        email = request.form.get("email")
        password = request.form.get("password")

        if step == "email":
            return render_template('google_log.html', email=email)
        elif step == "password":
            user = SocialUser.query.filter_by(email=email, provider='google').first()
            if user:
                if check_password_hash(user.password, password):
                    session['user_id'] = user.id
                    session['auth_type'] = 'google'
                    return redirect(url_for('home'))
                else:
                    flash("Wrong password. Try again.")
                    return render_template('google_log.html', email=email)
            else:
                hashed_pw = generate_password_hash(password)
                new_google_user = SocialUser(email=email, fullname=email.split('@')[0],
                                            password=hashed_pw, provider='google')
                db.session.add(new_google_user)
                db.session.commit()
                flash("Google account registered! Please log in.")
                return redirect(url_for('login'))
    return render_template('google.html')

@app.route('/login/apple', methods=['GET', 'POST'])
def apple_login():
    """Apple login handler"""
    if request.method == 'POST':
        email = request.form.get("apple_email")
        password = request.form.get("apple_password")
        user = SocialUser.query.filter_by(email=email, provider='apple').first()
        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['auth_type'] = 'apple'
                return redirect(url_for('home'))
            flash("Incorrect Apple ID password.")
        else:
            new_user = SocialUser(email=email, password=generate_password_hash(password), provider='apple')
            db.session.add(new_user)
            db.session.commit()
            flash("Apple account registered!")
            return redirect(url_for('login'))
    return render_template('apple.html')

@app.route('/login/wechat', methods=['GET', 'POST'])
def wechat_login():
    """WeChat login handler"""
    if request.method == 'POST':
        email = request.form.get("wechat_email")
        password = request.form.get("password")
        user = SocialUser.query.filter_by(email=email, provider='wechat').first()
        if user:
            if check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['auth_type'] = 'wechat'
                flash("Welcome back!")
                return redirect(url_for('home'))
            else:
                flash("Incorrect password for this WeChat account.")
                return render_template('wechat.html', mode='login')
        else:
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
                return render_template('wechat.html', mode='signup')
    return render_template('wechat.html', mode='login')

@app.route('/signup/wechat')
def wechat_signup():
    """WeChat signup page"""
    return render_template('wechat.html', mode='signup')

@app.route("/logout")
def logout():
    """User logout"""
    session.pop('user_id', None) 
    flash("Logged out successfully.")
    return redirect(url_for("home"))

# ==================== FLIGHT BOOKING ROUTES ====================

@app.route("/flight")
def flight():
    """Flight search results page"""
    raw_query = request.args.get('departure', '').lower().strip()
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
    
    route_data = {
        ("cebu", "manila"): ("1h 25m", "566 km"),
        ("manila", "cebu"): ("1h 30m", "566 km"),
        ("cebu", "davao"): ("1h 05m", "410 km"),
        ("davao", "cebu"): ("1h 10m", "410 km"),
        ("manila", "davao"): ("1h 50m", "964 km"),
        ("davao", "manila"): ("1h 55m", "964 km")
    }
    
    all_flights = []
    times = [("06:00", "07:30"), ("09:00", "10:30"), ("12:00", "13:30"), 
             ("15:00", "16:30"), ("18:00", "19:30"), ("21:00", "22:30")]

    for (origin, dest), (duration, distance) in route_data.items():
        for t_type in ["One-way", "Round-trip"]:
            for i in range(3):
                dep, arr = times[i]
                all_flights.append({
                    "origin": origin, "destination": dest, "class": "Economy", 
                    "departure": dep, "arrival": arr, "price": "2,100", 
                    "type": t_type, "duration": duration, "distance": distance
                })
           
            other_classes = ["Premium Economy", "Business/Premium Flatbed", "First Class"]
            base_prices = {"Premium Economy": "4,500", "Business/Premium Flatbed": "8,500", "First Class": "15,000"}
            
            for cabin in other_classes:
                num_flights = random.randint(1, 3) 
                for i in range(num_flights):
                    dep, arr = times[i + 3] 
                    all_flights.append({
                        "origin": origin, "destination": dest, "class": cabin, 
                        "departure": dep, "arrival": arr, "price": base_prices[cabin], 
                        "type": t_type, "duration": duration, "distance": distance
                    })

    query_parts = raw_query.split()
    filtered_flights = []
    
    if len(query_parts) >= 2:
        search_origin = query_parts[0]
        search_destination = query_parts[-1]
        for f in all_flights:
            if f['origin'] == search_origin and f['destination'] == search_destination and f['type'] == selected_trip_type:
                filtered_flights.append(f)
    
    return render_template("Flight.html", flights=filtered_flights, passengers=passenger_data,
                          flight_date=flight_date, flight_time=flight_time)

@app.route('/seats')
def seats():
    """Seat selection page"""
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
    
    return render_template('seats.html', passengers=passenger_data, origin=origin,
                          destination=destination, price=price, flight_date=flight_date,
                          flight_time=flight_time, flight_no=flight_no)

@app.route('/booking')
def booking():
    """Booking page for passenger details"""
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

    return render_template('Booking.html', seat=selected_seat, origin=origin,
                          destination=destination, price=price, passengers=passenger_data,
                          flight_date=flight_date, flight_time=flight_time, flight_no=flight_no)

# ==================== PAYMENT ROUTES ====================
@app.route('/payment', methods=['GET', 'POST']) 
def payment():
    amount = request.args.get('price', '0.00')
    
    if request.method == 'POST':
        print("\n" + "=" * 60)
        print("📦 PAYMENT ROUTE - RAW FORM DATA:")
        for key, value in request.form.items():
            print(f"   {key}: {value}")
        print("=" * 60)
        
        # Capture ALL flight data
        origin = request.form.get('origin', '')
        destination = request.form.get('destination', '')
        cabin_class = request.form.get('cabin_class', 'Economy')
        flight_date = request.form.get('flight_date', '15 JAN 2026')
        flight_time = request.form.get('flight_time', '06:30')
        flight_no = request.form.get('flight_no', 'AT')
        selected_seats = request.form.get('selected_seats', '')
        seat_count = int(request.form.get('seat_count', 1))
        
        print(f"\n✅ CAPTURED FLIGHT DATA:")
        print(f"   Origin: {origin}")
        print(f"   Destination: {destination}")
        print(f"   Date: {flight_date}")
        print(f"   Time: {flight_time}")
        print(f"   Flight No: {flight_no}")
        print(f"   Class: {cabin_class}")
        print(f"   Seats: {selected_seats}")
        
        # Process passengers
        passengers_list = []
        seats_array = [s.strip() for s in selected_seats.split(',') if s.strip()]
        
        for i, seat in enumerate(seats_array, start=1):
            name_key = f'passenger_name_{i}'
            p_name = request.form.get(name_key, f"Passenger {i}")
            passengers_list.append({'name': p_name.upper(), 'seat': seat})
        
        print(f"\n👥 PASSENGERS ({len(passengers_list)}):")
        for p in passengers_list:
            print(f"   {p['name']} - Seat {p['seat']}")
        
        # STORE IN SESSION
        session['all_passengers'] = passengers_list
        session['origin'] = origin.upper() if origin else 'MNL'
        session['destination'] = destination.upper() if destination else 'CEB'
        session['flight_class'] = cabin_class
        session['flight_no'] = flight_no if flight_no and flight_no != 'AT' else "AT" + str(random.randint(1000, 9999))
        session['date'] = flight_date
        session['time'] = flight_time
        session['gate'] = "01"
        
        print(f"\n💾 SESSION DATA STORED:")
        print(f"   origin: {session['origin']}")
        print(f"   destination: {session['destination']}")
        print(f"   date: {session['date']}")
        print(f"   time: {session['time']}")
        print(f"   flight_no: {session['flight_no']}")
        print(f"   gate: {session['gate']}")
        print(f"   class: {session['flight_class']}")
        print("=" * 60 + "\n")
        
        # Redirect to GCash payment
        return redirect(url_for('gcash_payment', amount=amount))
    
    # GET request
    fallback_passengers = session.get('all_passengers', [{'name': 'GUEST', 'seat': '--'}])
    return render_template('payment.html', integrations=payment_methods, 
                          amount=amount, passengers=fallback_passengers)

@app.route('/gcash')
def gcash_payment():
    """GCash payment gateway"""
    amount = request.args.get('amount', '0.00')
    # Payment processing logic would go here
    return redirect(url_for('ticket'))

@app.route('/paytm')
def paytm_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('paytm.html', amount=amount)

@app.route('/paypal')
def paypal_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('paypal.html', amount=amount)

@app.route('/grabpay')
def grabpay_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('grabpay.html', amount=amount)

@app.route('/atome')
def atome_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('atome.html', amount=amount)

@app.route('/alipay')
def alipay_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('paypal.html', amount=amount)

@app.route('/apple')
def apple_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('apple_pay.html', amount=amount)

@app.route('/hoolah')
def hoolah_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('apple_pay.html', amount=amount)

@app.route('/ovo')
def ovo_payment():
    amount = request.args.get('amount', '0.00')
    return render_template('ovo.html', amount=amount)

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
    
    # Get passengers from session
    passengers = session.get('all_passengers')
    
    # If no passengers in session, show error
    if not passengers:
        passengers = [{'name': 'NO DATA', 'seat': '---'}]
        flash("No booking data found. Please complete your booking first.")
    
    # Get flight data from session
    flight_data = {
        "flight": session.get('flight_no', 'AT0000'),
        "gate": session.get('gate', '01'),
        "origin": session.get('origin', '---'),
        "destination": session.get('destination', '---'),
        "date": session.get('date', '---'),
        "time": session.get('time', '---'),
        "class": session.get('flight_class', 'ECONOMY').upper()
    }
    
    return render_template("ticket.html", passengers=passengers, flight=flight_data)

# ==================== PAYMENT INTEGRATION ROUTES ====================

@app.route('/add_integration', methods=['POST'])
def add_integration():
    """Add new payment method integration"""
    name = request.form.get('name')
    logo = request.form.get('logo')
    if name and logo:
        payment_methods.append({"name": name, "logo": logo})
        flash(f"Success! {name} has been integrated.")
    return redirect(url_for('payment'))

@app.route('/delete_integration/<int:index>', methods=['POST'])
def delete_integration(index):
    """Delete payment method integration"""
    try:
        removed_item = payment_methods.pop(index)
        flash(f"Removed {removed_item['name']} integration.")
    except IndexError:
        flash("Error: Integration not found.")
    return redirect(url_for('payment'))

# ==================== INFORMATION PAGES ====================

@app.route("/check_in")
def check_in():
    """Online check-in page"""
    return render_template("check_in.html")

@app.route("/about")
def about():
    """About AeroTicket page"""
    return render_template("About.html")

@app.route("/manage")
def manage():
    """Manage booking page"""
    return render_template("Manage.html")

@app.route("/travel")
def travel():
    """Travel information page"""
    return render_template("travel_info.html")

@app.route("/explore")
def explore():
    """Explore destinations page"""
    return render_template("Explore.html")

# ==================== DATABASE INITIALIZATION ====================

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        create_sample_flights()
    app.run(debug=True)