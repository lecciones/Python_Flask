from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'aeroticket_secret_key'
# SQLITE CONFIGURATION
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aeroticket.db'
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=True) 
    provider = db.Column(db.String(20), default='email') 



@app.route("/")
def home():
    return render_template("Home_page.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
       
        user = User.query.filter_by(email=email).first()
        if user and user.password == password: 
            return redirect(url_for("home"))
        
        flash("Invalid email or password.")
        return redirect(url_for("login"))
        
    return render_template("Login_form.html")


@app.route("/register", methods=["POST"])
def register():
   
    provider = request.form.get("provider", "email")
    email = request.form.get("email")
    password = request.form.get("password")
   

    user_exists = User.query.filter_by(email=email).first()
    
    if not user_exists:
        new_user = User(email=email, password=password, provider=provider)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created successfully!")
        return redirect(url_for("login")) # Take them to login after signing up
    else:
        flash("Email already registered. Try logging in.")
        return redirect(url_for("signup"))


@app.route('/signup')
def signup():
   
    return render_template('signup.html')


@app.route('/login/google')
def google_login():
    # In a real app, you'd redirect to Google's OAuth page
    return "Redirecting to Google Login..."


@app.route('/login/apple')
def apple_login():
    return "Redirecting to Apple Login..."


@app.route('/login/wechat')
def wechat_login():
    return "Redirecting to WeChat Login..."



@app.route("/flight")
def flight():
    flights = [
        {"class": "Economy", "departure": "00:25", "arrival": "01:50", "price": "2,352"},
        {"class": "Economy", "departure": "02:25", "arrival": "03:50", "price": "1,925"},
        {"class": "Economy", "departure": "03:25", "arrival": "04:50", "price": "2,012"}
    ]
    return render_template("Flight.html", flights=flights) 
  
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


@app.route("/booking")
def booking():
    return render_template("Booking.html")


@app.route("/manage")
def manage():
    return render_template("Manage.html")


@app.route("/travel")
def travel():
    return render_template("travel_info.html")
 


@app.route("/explore")
def explore():
    return render_template("Explore.html") 
    


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)