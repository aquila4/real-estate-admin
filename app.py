from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
import os
import sqlite3
from werkzeug.utils import secure_filename
from datetime import datetime

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
import traceback  # at the top of your file

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        try:
            title = request.form['title']
            location = request.form['location']
            description = request.form['description']

            image_filename = ''
            video_filename = ''

            # Save main image
            image_file = request.files.get('image')
            if image_file and image_file.filename:
                image_filename = secure_filename(image_file.filename)
                image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

            # Save main video
            video_file = request.files.get('video')
            if video_file and video_file.filename:
                video_filename = secure_filename(video_file.filename)
                video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))

            # Save additional images
            image_list = []
            for img in request.files.getlist('images'):
                if img and img.filename:
                    filename = secure_filename(img.filename)
                    img.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_list.append(filename)
            images_str = ','.join(image_list)

            # Save additional videos
            video_list = []
            for vid in request.files.getlist('videos'):
                if vid and vid.filename:
                    filename = secure_filename(vid.filename)
                    vid.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    video_list.append(filename)
            videos_str = ','.join(video_list)

            # Save to DB
            conn = sqlite3.connect('database.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO properties (title, location, image, video, description, images, videos)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, location, image_filename, video_filename, description, images_str, videos_str))
            conn.commit()
            conn.close()

            flash('Property uploaded successfully!')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            print("❌ Upload error:", e)
            traceback.print_exc()  # 🔍 This shows full error in Railway logs
            return "Upload failed. Check logs.", 500

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
@app.route('/delete/<int:property_id>', methods=['GET', 'POST'])
def delete_property(property_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT image, video, images, videos FROM properties WHERE id = ?", (property_id,))
    result = cursor.fetchone()

    if result:
        image, video, images_str, videos_str = result

        if image:
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.strip())
            if os.path.exists(image_path):
                os.remove(image_path)

        if video:
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video.strip())
            if os.path.exists(video_path):
                os.remove(video_path)

        if images_str:
            for img in images_str.split(','):
                img_path = os.path.join(app.config['UPLOAD_FOLDER'], img.strip())
                if os.path.exists(img_path):
                    os.remove(img_path)

        if videos_str:
            for vid in videos_str.split(','):
                vid_path = os.path.join(app.config['UPLOAD_FOLDER'], vid.strip())
                if os.path.exists(vid_path):
                    os.remove(vid_path)

        cursor.execute("DELETE FROM properties WHERE id = ?", (property_id,))
        conn.commit()

    conn.close()
    return redirect(url_for('admin_dashboard'))

# ========== Template Helpers ==========
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# ========== Run App ==========
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))  # use PORT from Railway
    app.run(host='0.0.0.0', port=port, debug=True)

