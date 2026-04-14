from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash

app = Flask(__name__)
app.secret_key = 'aeroticket_secret_key'
# SQLITE CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aeroticket.db'
db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'all_users' 
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=True) 
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False) 
    provider = db.Column(db.String(20), default='email') 

    def __repr__(self):
        return f'<User {self.email}>'


@app.route("/")
def home():
    return render_template("Home_page.html")


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
            flash("Login successful!")
            return redirect(url_for("home"))
        
        flash("Invalid email or password.")
        
        return render_template("Login_form.html", 
                               step="password" if step == "password" else "email", 
                               email=email)

    return render_template("Login_form.html", step="email")

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
        
      
        new_user = User(
            fullname=fullname if fullname else None, 
            email=email, 
            password=hashed_password, 
            provider=provider
        )
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
    return render_template('signup.html')

@app.route('/login/google', methods=['GET', 'POST'])
def google_login():
    if request.method == 'POST':
       
        step = request.form.get("step")
        email = request.form.get("email")

        if step == "email":
            
            return render_template('google_log.html', email=email)
        
        elif step == "password":
            
            return redirect(url_for('home'))

   
    return render_template('google.html')

@app.route('/login/apple')
def apple_login():
   
    return render_template('apple.html')

@app.route('/login/wechat')
def wechat_login():
   
    return render_template('wechat.html')



 
@app.route("/logout")
def logout():
    session.pop('user_id', None) 
    flash("Logged out successfully.")
    return redirect(url_for("home"))
 
@app.route("/check_in") 
def check_in():
    return render_template("check_in.html")



@app.route("/about")
def about():
    return render_template("About.html")


@app.route("/ticket")
def ticket():
    ticket_info = {
        "name": "",
        "flight": "",
        "gate": "",
        "seat": "",
        "origin": "",
        "destination": "",
        "date": "",
        "time": ""
    }
    return render_template("ticket.html", ticket=ticket_info)

import random

import random

import random

@app.route("/flight")
def flight():
    raw_query = request.args.get('departure', '').lower().strip()
    selected_trip_type = request.args.get('trip_type', 'One-way')
    
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
                    "departure": dep, "arrival": arr, "price": "2,100", "type": t_type,
                    "duration": duration, "distance": distance
                })
            
       
            other_classes = ["Premium Economy", "Business/Premium Flatbed", "First Class"]
            base_prices = {"Premium Economy": "4,500", "Business/Premium Flatbed": "8,500", "First Class": "15,000"}
            
            for cabin in other_classes:
                num_flights = random.randint(1, 3) 
                for i in range(num_flights):
                    dep, arr = times[i + 3] 
                    all_flights.append({
                        "origin": origin, "destination": dest, "class": cabin, 
                        "departure": dep, "arrival": arr, "price": base_prices[cabin], "type": t_type,
                        "duration": duration, "distance": distance
                    })

   
    query_parts = raw_query.split()
    filtered_flights = []
    
    if len(query_parts) >= 2:
        search_origin = query_parts[0]
        search_destination = query_parts[-1]

        for f in all_flights:
            if f['origin'] == search_origin and f['destination'] == search_destination and f['type'] == selected_trip_type:
                filtered_flights.append(f)
    
    return render_template("Flight.html", flights=filtered_flights, passengers=passenger_data)

@app.route('/seats')
def seats():

    passenger_data = {
        "adults": request.args.get('adults', 1),
        "children": request.args.get('children', 0),
        "infants": request.args.get('infants', 0),
        "cabin": request.args.get('cabin', 'Economy')
    }
  
    return render_template('seats.html', passengers=passenger_data)

@app.route('/booking')
def booking():
   
    selected_seat = request.args.get('seat', '--')
    
    passenger_data = {
        "adults": request.args.get('adults', 1),
        "children": request.args.get('children', 0),
        "infants": request.args.get('infants', 0),
        "cabin": request.args.get('cabin', 'Economy')
    }
    

    return render_template('Booking.html', seat=selected_seat, passengers=passenger_data)

@app.route("/manage")
def manage():
    return render_template("Manage.html")


@app.route("/travel")
def travel():
    return render_template("travel_info.html")
 


@app.route("/explore")
def explore():
    return render_template("Explore.html") 
    


@app.route("/payment", methods=["GET", "POST"])
def payment():
    # If the user is coming from the Booking form (POST)
    if request.method == "POST":
        booking_details = {
            "name": request.form.get("passenger_name"),
            "origin": request.form.get("origin"),
            "destination": request.form.get("destination"),
            "seat": request.form.get("selected_seat"),
            "cabin": request.form.get("cabin_class")
        }
        # Store in session so data persists if they refresh the page
        session['temp_booking'] = booking_details
    
    # Retrieve data from session if it exists (for GET requests/refresh)
    details = session.get('temp_booking', {})

    integrations = [
        {"name": "GCash", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/GCash_logo.svg/1200px-GCash_logo.svg.png"},
        {"name": "Paytm", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/24/Paytm_Logo_%28standalone%29.svg/1200px-Paytm_Logo_%28standalone%29.svg.png"},
        {"name": "Google Pay", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f2/Google_Pay_Logo.svg/1200px-Google_Pay_Logo.svg.png"},
        {"name": "PayPal", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b5/PayPal.svg/1200px-PayPal.svg.png"},
        {"name": "GrabPay", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/03/Grab_logo.svg/1200px-Grab_logo.svg.png"},
        {"name": "Atome", "logo": "https://upload.wikimedia.org/wikipedia/commons/a/a2/Atome_Logo.png"},
        {"name": "Alipay", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/be/Alipay_logo.svg/1200px-Alipay_logo.svg.png"},
        {"name": "Apple Pay", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b0/Apple_Pay_logo.svg/1200px-Apple_Pay_logo.svg.png"},
        {"name": "Hoolah", "logo": "https://logos-world.net/wp-content/uploads/2023/04/Hoolah-Logo.png"},
        {"name": "OVO", "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/eb/Logo_ovo.svg/1200px-Logo_ovo.svg.png"}
    ]
    
    return render_template('payment.html', integrations=integrations, booking=details)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)