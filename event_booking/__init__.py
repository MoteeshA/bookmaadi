from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'  # SQLite database file
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Folder for uploaded images
app.secret_key = 'your_secret_key'  # Change this to a secure random value in production
db = SQLAlchemy(app)

# Event model
class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)  # Increase length for hashed passwords

# Create tables within application context
with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            return redirect(url_for('home'))
        else:
            flash('Invalid Credentials. Please try again.', 'error')
    return render_template('login.html')

@app.route('/home')
def home():
    events = Event.query.all()
    return render_template('home.html', events=events)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different username.', 'error')
        elif password == confirm_password:
            # Create new user with hashed password (you should hash the password here)
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Passwords do not match. Please try again.', 'error')

    return render_template('register.html')

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if request.method == 'POST':
        event_title = request.form['event_title']
        event_date_str = request.form['event_date']  # Get date as string
        event_location = request.form['event_location']
        event_description = request.form['event_description']
        event_image = request.files['event_image']

        # Convert string date to datetime.date
        event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()

        # Save image to a folder and get its URL
        if event_image:
            image_filename = secure_filename(event_image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            event_image.save(image_path)
            image_url = f'/uploads/{image_filename}'
        else:
            image_url = None

        # Create event object
        new_event = Event(title=event_title, date=event_date, location=event_location,
                          description=event_description, image_url=image_url)

        # Add event to database
        db.session.add(new_event)
        db.session.commit()

        flash('Event created successfully!', 'success')
        return redirect(url_for('home'))

    return render_template('create_event.html')

if __name__ == '__main__':
    app.run(debug=True, port=5001)
