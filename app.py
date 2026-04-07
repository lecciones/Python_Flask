from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)

# SQLITE CONFIGURATION (Fixed typo in key name for future use)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///aeroticket.db'
# db = SQLAlchemy(app)

@app.route("/")
def home():
    return render_template("Home_page.html")

@app.route("/login")
def login():
    return render_template("login_form.html")


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

    ticket = {
        "name": "Joe Hawkins",
        "flight": "95678A",
        "gate": "02",
        "seat": "19A",
        "origin": "MNL",
        "destination": "CEBU",
        "date": "15 JAN 2026",
        "time": "06:30"
    }

    return render_template("ticket.html", ticket=ticket)

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
    return render_template("/Explore.html")
    
if __name__ == "__main__":
    app.run(debug=True)