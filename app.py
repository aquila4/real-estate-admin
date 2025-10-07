from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import traceback
from dotenv import load_dotenv
from models import Property, BlogPost, Enquiry, Newsletter
from flask_migrate import Migrate
from slugify import slugify
from flask_mail import Mail, Message
from extensions import db
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallback_secret")

# === Database config (PostgreSQL from Railway) ===
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:jGNEMNdfkQiNnUlvVSlbxQamOkwTAchb@centerbeam.proxy.rlwy.net:25167/railway"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# === Upload folder setup ===
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "/mnt/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize DB and migrations
db.init_app(app)
migrate = Migrate(app, db)

# === Flask-Mail Config ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

# ==============================
# 🔹 ROUTES
# ==============================
@app.route('/')
def home():
    properties = Property.query.all()

    seo = {
        "title": "Great Mar-cy’s & Sons Limited - Real Estate in Ilorin",
        "description": "Find and buy land or property in Ilorin with Great Mar-cy’s & Sons Limited. Trusted estate company in Kwara State.",
        "keywords": "Ilorin real estate, buy land Ilorin, Great Marcy Sons Limited, property for sale, estate management",
        "image": url_for('static', filename='image/logo.png')
    }

    logogmc_path = "image/logogmc.png"  # ✅ make sure this matches your folder path

    nav_links = [
    {"name": "Home", "endpoint": "home"},
    {"name": "About", "endpoint": "about"},
    {"name": "Properties", "endpoint": "property_page"},
    {"name": "Blog", "endpoint": "blog"},  # 🆕 Added blog link
    {"name": "Contact", "endpoint": "contact"},
    {"name": "Admin", "endpoint": "admin_dashboard"}
]



    return render_template("home.html", properties=properties, seo=seo, logogmc_path=logogmc_path, nav_links=nav_links)


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

# ==============================
# 🔹 ADMIN AUTH
# ==============================

@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'Greatmarcy' and password == '5467':
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials.')
    return render_template('admin-login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Logged out successfully.")
    return redirect(url_for('admin_login'))

# ==============================
# 🔹 ADMIN DASHBOARD
# ==============================

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

# ==============================
# 🔹 PROPERTY ROUTES
# ==============================

@app.route('/uploads/<filename>')
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
@app.route('/upload', methods=['POST'])
def upload():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    try:
        # --- FORM DATA ---
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        description = request.form.get('description', '').strip()
        seo_title = request.form.get('seo_title', '').strip() or None
        meta_description = request.form.get('meta_description', '').strip() or None
        keywords = request.form.get('keywords', '').strip() or None

        # --- REQUIRED FIELDS CHECK ---
        if not title or not location or not description:
            flash('All required fields (Title, Location, Description) must be filled.')
            return redirect(url_for('add_property'))

        # --- TRUNCATE SEO FIELDS TO SAFE LENGTHS ---
        if seo_title:
            seo_title = seo_title[:255]
        if meta_description:
            meta_description = meta_description[:300]
        if keywords:
            keywords = keywords[:500]

        # --- IMAGE UPLOAD ---
        image_file = request.files.get('image')
        image_filename = ''
        if image_file and image_file.filename:
            image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
            image_file.save(image_path)

        # --- VIDEO UPLOAD ---
        video_file = request.files.get('video')
        video_filename = ''
        if video_file and video_file.filename:
            video_filename = f"{uuid.uuid4().hex}_{secure_filename(video_file.filename)}"
            video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_filename)
            video_file.save(video_path)

        # --- SLUG GENERATION ---
        slug = slugify(title)
        if Property.query.filter_by(slug=slug).first():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        # --- CREATE NEW PROPERTY RECORD ---
        new_property = Property(
            title=title,
            location=location,
            description=description,
            image_url=image_filename,
            video_url=video_filename,
            seo_title=seo_title,
            meta_description=meta_description,
            keywords=keywords,
            slug=slug
        )

        db.session.add(new_property)
        db.session.commit()

        flash('✅ Property uploaded successfully!')
        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        print("❌ Property upload error:", str(e))
        traceback.print_exc()
        flash('❌ Error uploading property. Check server logs.')
        return redirect(url_for('add_property'))


@app.route('/property')
def property_page():
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('property.html', properties=properties)
@app.route('/property/<string:slug>')
def property_detail(slug):
    prop = Property.query.filter_by(slug=slug).first_or_404()
    
    # Use only existing fields from Property
    seo = {
        "title": prop.title,  # Property has title
        "description": prop.description[:150],  # take first 150 chars
        "keywords": "",  # no keywords field
        "image": prop.image_url
    }

    return render_template('property_detail.html', property=prop, seo=seo)

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

# ==============================
# 🔹 BLOG ROUTES
# ==============================

@app.route('/admin/blog')
def admin_blog():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog_list.html', posts=posts)

@app.route('/admin/blog/new', methods=['GET', 'POST'])
def admin_new_blog():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        seo_title = request.form.get('seo_title') or None
        meta_description = request.form.get('meta_description') or None
        keywords = request.form.get('keywords') or None
        image_file = request.files.get('image')

        if not title or not content:
            flash("Title and content are required!")
            return redirect(url_for('admin_new_blog'))

        image_filename = None
        if image_file and image_file.filename:
            image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        slug = slugify(title)
        if BlogPost.query.filter_by(slug=slug).first():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        new_post = BlogPost(
            title=title,
            content=content,
            seo_title=seo_title,
            meta_description=meta_description,
            keywords=keywords,
            image_url=image_filename,
            slug=slug
        )
        db.session.add(new_post)
        db.session.commit()
        flash("✅ Blog post created successfully!")
        return redirect(url_for('admin_blog'))

    return render_template('admin/new_blog.html')

@app.route('/admin/blog/edit/<int:post_id>', methods=['GET', 'POST'])
def admin_edit_blog(post_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    post = BlogPost.query.get_or_404(post_id)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        seo_title = request.form.get('seo_title') or None
        meta_description = request.form.get('meta_description') or None
        keywords = request.form.get('keywords') or None
        image_file = request.files.get('image')

        if not title or not content:
            flash("Title and content are required!")
            return redirect(url_for('admin_edit_blog', post_id=post.id))

        post.title = title
        post.content = content
        post.seo_title = seo_title
        post.meta_description = meta_description
        post.keywords = keywords

        if image_file and image_file.filename:
            if post.image_url:
                old_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_url)
                if os.path.exists(old_path):
                    os.remove(old_path)
            post.image_url = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], post.image_url))

        db.session.commit()
        flash("✅ Blog post updated successfully!")
        return redirect(url_for('admin_blog'))

    return render_template('admin/edit_blog.html', post=post)

@app.route('/admin/blog/delete/<int:post_id>', methods=['POST'])
def admin_delete_blog(post_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    post = BlogPost.query.get_or_404(post_id)
    if post.image_url:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], post.image_url)
        if os.path.exists(file_path):
            os.remove(file_path)
    db.session.delete(post)
    db.session.commit()
    flash("🗑️ Blog post deleted successfully!")
    return redirect(url_for('admin_blog'))

# ==============================
# 🔹 BLOG FRONTEND
# ==============================

@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    print("DEBUG POSTS:", posts)  # This will show all posts in the console

    seo = {
        "title": "Our Blog",
        "description": "Read the latest blog posts",
        "keywords": "blog, news, updates",
        "image": ""
    }
    return render_template('blog.html', posts=posts, seo=seo)

@app.route('/blog/<string:slug>')
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug).first_or_404()

    seo = {
        "title": post.seo_title or post.title,
        "description": post.meta_description or post.content[:150],
        "keywords": post.keywords or "",
        "image": post.image_url or ""
    }

    return render_template('blog_post.html', post=post, seo=seo)

# ==============================
# 🔹 ENQUIRY FORM
# ==============================

@app.route('/enquiry', methods=['POST'])
def enquiry():
    name = request.form.get('name')
    email = request.form.get('email')
    subject = request.form.get('subject')
    message = request.form.get('message')

    if not name or not email or not subject or not message:
        flash("All fields are required for enquiry.")
        return redirect(url_for('home'))

    new_enquiry = Enquiry(name=name, email=email, subject=subject, message=message)
    db.session.add(new_enquiry)
    db.session.commit()

    try:
        # Admin notification
        admin_msg = Message(
            subject=f"New Enquiry: {subject}",
            sender=os.getenv("MAIL_USERNAME"),
            recipients=[os.getenv("MAIL_USERNAME")],
            reply_to=email,
            body=f"Name: {name}\nEmail: {email}\nSubject: {subject}\nMessage:\n{message}"
        )
        mail.send(admin_msg)

        # 📩 Auto-reply to Customer
        confirmation = Message(
            subject="We Received Your Enquiry – Great Mar-cy’s & Sons Limited",
            sender=os.getenv("MAIL_USERNAME"),
            recipients=[email],
            body=f"""Dear {name},

Thank you for reaching out to Great Mar-cy’s & Sons Limited.
We’ve received your enquiry regarding “{subject}” and our team is already reviewing it.

One of our representatives will get back to you shortly with more information.

We truly appreciate your interest in our services — your satisfaction is our priority.

Warm regards,
Great Mar-cy’s & Sons Limited
📍 Ilorin, Kwara State
📞 +234 913 907 0404, +234 902 893 9653
📧 greatmarcysonslimited@gmail.com
"""
        )
        mail.send(confirmation)

        flash("✅ Your enquiry has been submitted successfully! We'll get back to you soon.")

    except Exception as e:
        print("❌ Email error:", str(e))
        flash("Your enquiry was saved but email notification failed.")

    return redirect(url_for('home'))


# ==============================
# 🔹 NEWSLETTER SUBSCRIPTION
# ==============================

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email')
    if not email:
        flash("Email is required to subscribe.")
        return redirect(url_for('home'))

    if Newsletter.query.filter_by(email=email).first():
        flash("You are already subscribed!")
        return redirect(url_for('home'))

    new_sub = Newsletter(email=email)
    db.session.add(new_sub)
    db.session.commit()

    try:
        msg = Message(
            subject="Welcome to Great Mar-cy’s & Sons Limited Newsletter",
            sender=os.getenv("MAIL_USERNAME"),
            recipients=[email],
            body=f"""Hello there 👋,

Thank you for subscribing to Great Mar-cy’s & Sons Limited!

You’ll now receive updates about our latest property listings, estate opportunities,
and real estate insights — straight to your inbox.

If you ever have any questions, feel free to reply to this email anytime.

Warm regards,
Great Mar-cy’s & Sons Limited
Your Trusted Real Estate Partner in Ilorin
"""
        )
        mail.send(msg)
    except Exception as e:
        print("❌ Newsletter email failed:", str(e))

    flash("✅ Thank you for subscribing! Welcome to Great Mar-cy’s & Sons community.")
    return redirect(url_for('home'))


@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


# ==============================
# 🔹 TEMPLATE CONTEXT
# ==============================

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# ==============================
# 🔹 RUN SERVER
# ==============================


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
