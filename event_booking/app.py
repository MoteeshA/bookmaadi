from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import qrcode
import logging

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///events.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.secret_key = 'your_secret_key'

db = SQLAlchemy(app)

# Define models
user_events = db.Table('user_events',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('event_id', db.Integer, db.ForeignKey('event.id'), primary_key=True)
)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date = db.Column(db.Date, nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(200))
    attendees = db.relationship('User', secondary=user_events, lazy='subquery',
                                backref=db.backref('events', lazy=True))

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

# Ensure the UPLOAD_FOLDER exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Function to generate QR code
def generate_qr_code(data, filename):
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        qr_code_filename = f"qr_{filename}.png"
        qr_code_path = os.path.join(app.config['UPLOAD_FOLDER'], qr_code_filename)
        img.save(qr_code_path)

        return qr_code_filename
    except Exception as e:
        app.logger.error(f"Error generating QR code: {e}")
        return None

# Routes
@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid Credentials. Please try again.', 'error')

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/home')
def home():
    if 'user_id' in session:
        events = Event.query.all()
        return render_template('home.html', events=events)
    else:
        flash('Please log in to view this page.', 'error')
        return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username.strip():
            flash('Username is required.', 'error')
        elif not password.strip():
            flash('Password is required.', 'error')
        elif password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
        elif User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different username.', 'error')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/create_event', methods=['GET', 'POST'])
def create_event():
    if 'user_id' not in session:
        flash('Please log in to create events.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        event_title = request.form['event_title']
        event_date_str = request.form['event_date']
        event_location = request.form['event_location']
        event_description = request.form['event_description']
        event_image = request.files['event_image']

        if not event_title.strip():
            flash('Event title is required.', 'error')
        elif not event_date_str.strip():
            flash('Event date is required.', 'error')
        elif not event_location.strip():
            flash('Event location is required.', 'error')
        elif not event_description.strip():
            flash('Event description is required.', 'error')
        else:
            try:
                event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
                return redirect(request.url)

            if event_image:
                image_filename = secure_filename(event_image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                event_image.save(image_path)
                image_url = f'/uploads/{image_filename}'
            else:
                image_url = None

            new_event = Event(title=event_title, date=event_date, location=event_location,
                              description=event_description, image_url=image_url)
            db.session.add(new_event)
            db.session.commit()

            flash('Event created successfully!', 'success')
            return redirect(url_for('home'))

    return render_template('create_event.html')

@app.route('/register_event/<int:event_id>', methods=['POST'])
def register_event(event_id):
    if 'user_id' not in session:
        flash('Please log in to register for events.', 'error')
        return redirect(url_for('login'))

    event = Event.query.get_or_404(event_id)
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    if event in user.events:
        flash(f'You are already registered for {event.title}.', 'info')
    else:
        user.events.append(event)
        db.session.commit()
        flash(f'Registered successfully for {event.title}!', 'success')

    return redirect(url_for('registered_events'))

@app.route('/unregister_event/<int:event_id>', methods=['POST'])
def unregister_event(event_id):
    if 'user_id' not in session:
        flash('Please log in to unregister from events.', 'error')
        return redirect(url_for('login'))

    event = Event.query.get_or_404(event_id)
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    if event not in user.events:
        flash(f'You are not registered for {event.title}.', 'info')
    else:
        user.events.remove(event)
        db.session.commit()
        flash(f'Unregistered successfully from {event.title}!', 'success')

    return redirect(url_for('registered_events'))

@app.route('/remove_event/<int:event_id>', methods=['POST'])
def remove_event(event_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    event = Event.query.get_or_404(event_id)
    db.session.delete(event)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Event {event.title} removed successfully!'})

@app.route('/registered_events')
def registered_events():
    if 'user_id' not in session:
        flash('Please log in to view your registered events.', 'error')
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    events = user.events

    return render_template('registered_events.html', events=events)

@app.route('/generate_qr_code/<int:event_id>', methods=['POST'])
def generate_qr_code_route(event_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403

    event = Event.query.get_or_404(event_id)

    try:
        qr_code_filename = generate_qr_code(f"Event: {event.title}, Date: {event.date}", event_id)

        if not qr_code_filename:
            raise Exception("Failed to generate QR code")

        qr_code_url = url_for('uploaded_file', filename=qr_code_filename)
        return jsonify({'qr_code_url': qr_code_url})
    except Exception as e:
        app.logger.error(f"Error generating QR code route: {e}")
        return jsonify({'error': 'Failed to generate QR code'}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app.logger.setLevel(logging.INFO)
    app.run(debug=True, port=5006)
