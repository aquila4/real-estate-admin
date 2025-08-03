from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime
import traceback


app = Flask(__name__)
app.secret_key = 'your_secret_key'



UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# --- ROUTES ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/add-property')
def add_property():
    return render_template('add-property.html')

@app.route('/agent')
def agent():
    return render_template('agent.html')

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route('/privacy')
def privacy():
    return render_template('privacy.html')

@app.route('/google78ddd9d79ee95af7.html')
def google_verification():
    return app.send_static_file('google78ddd9d79ee95af7.html')

@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml')


# ========== Upload Route ==========
# @app.route('/upload', methods=['GET', 'POST'])
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        try:
            title = request.form.get('title')
            location = request.form.get('location')
            description = request.form.get('description')

            if not title or not location or not description:
                flash('Title, location, and description are required.')
                return redirect(request.url)

            image_filename = ''
            video_filename = ''

            # Handle main image
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                image_filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

            # Handle main video
            video_file = request.files.get('video')
            if video_file and video_file.filename:
                video_filename = secure_filename(video_file.filename)
                video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))

            # Save to database (no multiple images/videos)
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO properties (title, location, image, video, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, location, image_filename, video_filename, description))
            conn.commit()
            conn.close()

            flash('Property uploaded successfully!')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            print("❌ Upload error:", e)
            traceback.print_exc()
            return "Upload failed. Check Railway logs.", 500

    return render_template('add-property.html')





    return render_template('add-property.html')
# ========== Admin Login ==========
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '12345':
            session['admin_logged_in'] = True
            return redirect(url_for('add_property'))

        else:
            flash("Invalid username or password.")
            return redirect(url_for('admin_login'))

    return render_template('admin-login.html')

# ========== Admin Dashboard ==========
@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()
    conn.close()

    return render_template('admin-dashboard.html', properties=properties)

# ========== Property Display ==========
@app.route('/property')
def property():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM properties")
    properties = cursor.fetchall()
    conn.close()

    return render_template('property.html', properties=properties)

# ========== Delete Property ==========
@app.route('/delete-property/<int:property_id>', methods=['POST'])
def delete_property(property_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM properties WHERE id = ?", (property_id,))
        conn.commit()
        conn.close()

        flash("Property deleted successfully.")
        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        print("❌ Delete error:", e)
        return "Delete failed", 500

# ========== Template Helpers ==========
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# ========== Run App ==========
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))  # use PORT from Railway
    app.run(host='0.0.0.0', port=port, debug=True)

