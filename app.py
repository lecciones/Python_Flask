from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy

#ATONG App
app = Flask(__name__)

#SQLITE CONFIGURATION
#app.config['SQLALCHEMT_DATABASE_URL'] = 'sqlite:///aeroticket.db'
#db = SQLAlchemy(app)


@app.route("/")
def Landing_page():
    return render_template("check_in.html")


if __name__ in "__main__":
  app.run(debug=True)