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
import threading
import re
EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"
from functools import wraps

from flask_mail import Mail, Message


# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallback_secret")


# === Flask-Mail Config ===
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")

mail = Mail(app)

ADMIN_USER = os.getenv("ADMIN_USER", "admin")  # fallback if not set
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")   # fallback if not set


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


# ==============================
# 🔹 ROUTES
# ==============================
@app.route('/')
def home():
    # Fetch properties
    properties = Property.query.all()

    # Fetch latest blog posts (limit to latest 3 for homepage)
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(2).all()

    # SEO Info
    seo = {
        "title": "Great Mar-cy’s & Sons Limited - Real Estate in Ilorin",
        "description": "Find and buy land or property in Ilorin with Great Mar-cy’s & Sons Limited. Trusted estate company in Kwara State.",
        "keywords": "Ilorin real estate, buy land Ilorin, Great Marcy Sons Limited, property for sale, estate management",
        "image": url_for('static', filename='image/logo.png')
    }

    # Logo path
    logogmc_path = "image/logogmc.png"

    # Navigation links
    nav_links = [
        {"name": "Home", "endpoint": "home"},
        {"name": "About", "endpoint": "about"},
        {"name": "Properties", "endpoint": "property_page"},
        {"name": "Blog", "endpoint": "blog"},  # ✅ Blog link
        {"name": "Contact", "endpoint": "contact"},
        {"name": "Admin", "endpoint": "admin_dashboard"}
    ]

    # ✅ Render all together
    return render_template(
        "home.html",
        properties=properties,
        posts=posts,
        seo=seo,
        logogmc_path=logogmc_path,
        nav_links=nav_links
    )


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


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please log in as admin.")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def send_email(to_email, subject, content):
    message = Mail(
        from_email='greatmarcysonslimited@gmail.com',
        to_emails=to_email,
        subject=subject,
        html_content=content
    )
    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        sg.send(message)
        print("✅ Email sent successfully")
    except Exception as e:
        print("❌ Error sending email:", e)

# ==============================
# 🔹 ASYNC EMAIL FUNCTION
# ==============================
def send_email(subject, recipients, body_text=None, body_html=None, reply_to=None):
    """
    Send email asynchronously with Gmail first, fallback to SendGrid.
    
    Args:
        subject (str): Email subject
        recipients (list): List of recipient emails
        body_text (str): Plain text email
        body_html (str): HTML email (optional)
        reply_to (str): Reply-to address
    """
    def async_send(app, msg):
        with app.app_context():
            def send_with_gmail(msg):
                try:
                    mail.send(msg)
                    print(f"✅ Email sent via Gmail to {msg.recipients}")
                    return True
                except Exception as e:
                    print(f"❌ Gmail failed: {e}")
                    traceback.print_exc()
                    return False

            def send_with_sendgrid(msg):
                try:
                    # Temporarily override config for SendGrid
                    app.config.update(
                        MAIL_SERVER="smtp.sendgrid.net",
                        MAIL_PORT=587,
                        MAIL_USE_TLS=True,
                        MAIL_USE_SSL=False,
                        MAIL_USERNAME="apikey",
                        MAIL_PASSWORD=os.getenv("SENDGRID_API_KEY"),
                        MAIL_DEFAULT_SENDER=os.getenv("MAIL_USERNAME")
                    )
                    mail.send(msg)
                    print(f"✅ Email sent via SendGrid to {msg.recipients}")
                    return True
                except Exception as e:
                    print(f"❌ SendGrid failed: {e}")
                    traceback.print_exc()
                    return False

            if not send_with_gmail(msg):
                print("⚠️ Falling back to SendGrid...")
                send_with_sendgrid(msg)

    # Create Message object
    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body_text or "",
        html=body_html or None,
        reply_to=reply_to
    )

    threading.Thread(target=async_send, args=(app, msg)).start()

# ==============================
# 🔹 SUBSCRIBE ROUTE
# ==============================

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip().lower()  # Normalize email

    if not email:
        flash("Email is required to subscribe.")
        return redirect(url_for('home'))

    # Validate email format
    if not re.match(EMAIL_REGEX, email):
        flash("Invalid email format.")
        return redirect(url_for('home'))

    # Check if already subscribed
    if Newsletter.query.filter_by(email=email).first():
        flash("You are already subscribed!")
        return redirect(url_for('home'))

    # Save to database
    new_sub = Newsletter(email=email)
    db.session.add(new_sub)
    db.session.commit()

    # Prepare welcome email to user
    text_body = f"""
Hello there 👋,

Thank you for subscribing to Great Mar-cy’s & Sons Limited!

You’ll now receive updates about our latest property listings, estate opportunities,
and real estate insights — straight to your inbox.

If you ever have any questions, feel free to reply to this email anytime.

Warm regards,
Great Mar-cy’s & Sons Limited
Your Trusted Real Estate Partner in Ilorin
"""
    html_body = f"""
<html>
  <body>
    <p>Hello there 👋,</p>
    <p>Thank you for subscribing to <b>Great Mar-cy’s & Sons Limited</b>!</p>
    <p>You’ll now receive updates about our latest property listings, estate opportunities, 
    and real estate insights — straight to your inbox.</p>
    <p>If you ever have any questions, feel free to reply to this email anytime.</p>
    <p>Warm regards,<br>
    <b>Great Mar-cy’s & Sons Limited</b><br>
    Your Trusted Real Estate Partner in Ilorin</p>
  </body>
</html>
"""

    # === Send welcome email to user ===
    send_email(
        subject="Welcome to Great Mar-cy’s & Sons Limited Newsletter",
        recipients=[email],
        body_text=text_body,
        body_html=html_body
    )

    # === Notify admin of new subscriber ===
    try:
        admin_email = os.getenv("MAIL_USERNAME")
        admin_msg = f"""
New Newsletter Subscriber 🎉

A new user has subscribed to the newsletter.

Email: {email}

— Great Mar-cy’s & Sons Limited System
"""
        send_email(
            subject="📩 New Newsletter Subscriber Alert",
            recipients=[admin_email],
            body_text=admin_msg
        )
        print(f"✅ Admin notified about new subscriber: {email}")
    except Exception as e:
        print(f"⚠️ Error sending admin notification: {e}")

    flash("✅ Thank you for subscribing! Welcome to Great Mar-cy’s community.")
    return redirect(url_for('home'))

@app.route('/enquire', methods=['POST'])
def enquiry():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()
    subject = request.form.get('subject', 'New Enquiry').strip()  # Default subject

    # --- Validation ---
    if not name or not email or not message:
        flash("All fields are required.")
        return redirect(url_for('contact'))

    if not re.match(EMAIL_REGEX, email):
        flash("Invalid email address.")
        return redirect(url_for('contact'))

    # --- Save to Database ---
    new_enquiry = Enquiry(name=name, email=email, subject=subject, message=message)
    db.session.add(new_enquiry)
    db.session.commit()

    # --- Confirmation Email to User ---
    user_text = f"""
Hi {name},

Thank you for contacting Great Mar-cy’s & Sons Limited!

We’ve received your enquiry and our team will get back to you soon.
If you have urgent questions, feel free to reply to this email.

Warm regards,  
Great Mar-cy’s & Sons Limited  
Your Trusted Real Estate Partner in Ilorin
"""
    user_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <p>Hi <b>{name}</b>,</p>
    <p>Thank you for contacting <b>Great Mar-cy’s & Sons Limited</b>!</p>
    <p>We’ve received your enquiry and our team will get back to you shortly.</p>
    <p>If you have urgent questions, you can simply reply to this email.</p>
    <p>Warm regards,<br>
    <b>Great Mar-cy’s & Sons Limited</b><br>
    Your Trusted Real Estate Partner in Ilorin</p>
  </body>
</html>
"""
    send_email(
        subject="We’ve received your enquiry – Great Mar-cy’s & Sons Limited",
        recipients=[email],
        body_text=user_text,
        body_html=user_html
    )

    # --- Notification to Admin ---
    admin_email = os.getenv("MAIL_USERNAME")
    admin_text = f"""
New Enquiry Received:

Name: {name}
Email: {email}
Subject: {subject}
Message: {message}

Sent on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    send_email(
        subject=f"New Enquiry from {name}",
        recipients=[admin_email],
        body_text=admin_text
    )

    flash("✅ Your enquiry has been received. We'll get back to you soon.")
    return redirect(url_for('contact'))



@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True
            flash("✅ Logged in successfully!")
            return redirect(url_for('admin_dashboard'))

        flash("❌ Invalid credentials")
        return redirect(url_for('admin_login'))

    return render_template('admin/login.html')


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash("Logged out successfully.")
    return redirect(url_for('admin_login'))

# ==============================
# 🔹 ADMIN DASHBOARD
# ==============================

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    properties = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('admin-dashboard.html', properties=properties)

@app.route('/add-property')
@admin_required
def add_property():
    return render_template('add_property.html')

@app.route('/upload', methods=['POST'])
@admin_required
def upload():
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

        # --- TRUNCATE SEO FIELDS ---
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

        # --- CREATE PROPERTY ---
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

@app.route('/uploads/<path:filename>')
def serve_file(filename):
    return send_from_directory('static/uploads', filename)

    

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
