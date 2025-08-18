from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import traceback
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "your_secret_key")

# === PostgreSQL from Railway ===
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:jGNEMNdfkQiNnUlvVSlbxQamOkwTAchb@centerbeam.proxy.rlwy.net:25167/railway"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# === Upload folder setup (using Railway Volume) ===
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/mnt/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Import the db instance from extensions.py
from extensions import db
db.init_app(app)

# Import models *after* db.init_app
from models import Property

# === Create tables on startup ===
with app.app_context():
    db.create_all()

# === Routes ===
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/agent')
def agent():
    return render_template('agent.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')

@app.route('/google78ddd9d79ee95af7.html')
def google_verification():
    return app.send_static_file('google78ddd9d79ee95af7.html')

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'admin' and password == '12345':
            session['admin_logged_in'] = True
            return redirect(url_for('add_property'))
        flash('Invalid credentials.')
    return render_template('admin-login.html')

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('admin-dashboard.html', properties=properties)

@app.route('/add-property')
def add_property():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template('add_property.html')

@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        title = request.form.get('title')
        location = request.form.get('location')
        description = request.form.get('description')

        if not title or not location or not description:
            flash('All fields are required.')
            return redirect(url_for('add_property'))

        image_filename = ''
        video_filename = ''

        image_file = request.files.get('image')
        if image_file and image_file.filename:
            image_filename = secure_filename(image_file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        video_file = request.files.get('video')
        if video_file and video_file.filename:
            video_filename = secure_filename(video_file.filename)
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
            video_file.save(video_path)

        new_property = Property(
            title=title,
            location=location,
            description=description,
            image_url=image_filename,
            video_url=video_filename
        )
        db.session.add(new_property)
        db.session.commit()

        flash('Property uploaded successfully!')
        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        traceback.print_exc()
        flash('Error uploading property. Check logs.')
        return redirect(url_for('add_property'))

@app.route('/property')
def property_page():
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('property.html', properties=properties)

@app.route('/delete-property/<int:property_id>', methods=['POST'])
def delete_property(property_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    prop = Property.query.get_or_404(property_id)

    for file_field in [prop.image_url, prop.video_url]:
        if file_field:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_field)
            if os.path.exists(file_path):
                os.remove(file_path)

    db.session.delete(prop)
    db.session.commit()
    flash('Property deleted.')
    return redirect(url_for('admin_dashboard'))

# === Add current time to templates ===
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# === Local Dev Server ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
