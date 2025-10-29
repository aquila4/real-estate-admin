from flask import Flask, render_template, request, redirect, url_for, flash, session, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import traceback
from dotenv import load_dotenv
from models import Property, BlogPost, Enquiry, Newsletter
from flask_migrate import Migrate
from slugify import slugify
from extensions import db
import uuid
import threading
import re
from functools import wraps
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To

# ==============================
# 🔹 CONFIG
# ==============================
load_dotenv()
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "fallback_secret")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASS", "1234")
DEFAULT_SENDER = os.getenv("DEFAULT_SENDER", "greatmarcysonslimited@gmail.com")
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:jGNEMNdfkQiNnUlvVSlbxQamOkwTAchb@centerbeam.proxy.rlwy.net:25167/railway"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "static/uploads")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)
migrate = Migrate(app, db)

EMAIL_REGEX = r"[^@]+@[^@]+\.[^@]+"

# ==============================
# 🔹 HELPER FUNCTIONS
# ==============================
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash("Please log in as admin.")
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated

def send_email(subject, recipients, body_text=None, body_html=None, reply_to=None):
    """
    Send email asynchronously using SendGrid API.
    """
    def async_send():
        try:
            for recipient in recipients:
                message = Mail(
                    from_email=Email(DEFAULT_SENDER),
                    to_emails=To(recipient),
                    subject=subject,
                    plain_text_content=body_text or "",
                    html_content=body_html or body_text or ""
                )
                if reply_to:
                    message.reply_to = Email(reply_to)
                
                sg = SendGridAPIClient(SENDGRID_API_KEY)
                response = sg.send(message)
                print(f"✅ Email sent to {recipient}, Status Code: {response.status_code}")
        except Exception as e:
            print(f"❌ SendGrid email failed: {e}")
            traceback.print_exc()
    threading.Thread(target=async_send).start()

# ==============================
# 🔹 ROUTES
# ==============================
@app.route('/')
def home():
    properties = Property.query.all()
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).limit(2).all()
    seo = {
        "title": "Great Mar-cy’s & Sons Limited - Real Estate in Ilorin",
        "description": "Find and buy land or property in Ilorin with Great Mar-cy’s & Sons Limited.",
        "keywords": "Ilorin real estate, buy land Ilorin, Great Marcy Sons Limited, property for sale",
        "image": url_for('static', filename='image/logo.png')
    }
    nav_links = [
        {"name": "Home", "endpoint": "home"},
        {"name": "About", "endpoint": "about"},
        {"name": "Properties", "endpoint": "property_page"},
        {"name": "Blog", "endpoint": "blog"},
        {"name": "Contact", "endpoint": "contact"},
        {"name": "Admin", "endpoint": "admin_dashboard"}
    ]
    return render_template("home.html", properties=properties, posts=posts, seo=seo, nav_links=nav_links, logogmc_path="image/logogmc.png")

@app.route('/about')
def about(): return render_template('about.html')

@app.route('/agent')
def agent(): return render_template('agent.html')

@app.route('/contact')
def contact(): return render_template('contact.html')

@app.route('/privacy')
def privacy(): return render_template('privacy.html')

@app.route('/sitemap.xml')
def sitemap(): return send_from_directory('static', 'sitemap.xml')

@app.route('/google78ddd9d79ee95af7.html')
def google_verification(): return app.send_static_file('google78ddd9d79ee95af7.html')

@app.context_processor
def inject_now(): return {'now': datetime.now()}

@app.route('/listings')
def listings():
    listings = Listing.query.order_by(Listing.created_at.desc()).all()
    return render_template('listings.html', listings=listings)

@app.route('/listing/<string:slug>')
def listing_detail(slug):
    listing = Listing.query.filter_by(slug=slug).first_or_404()
    return render_template('listing_detail.html', listing=listing)


@app.route('/admin/edit-listing/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_listing(id):
    listing = Listing.query.get_or_404(id)

    if request.method == 'POST':
        try:
            listing.title = request.form.get('title', listing.title)
            listing.location = request.form.get('location', listing.location)
            listing.price = request.form.get('price', listing.price)
            listing.description = request.form.get('description', listing.description)
            listing.property_type = request.form.get('property_type', listing.property_type)
            listing.status = request.form.get('status', listing.status)
            listing.category = request.form.get('category', listing.category)

            # Handle new images (optional)
            new_images = request.files.getlist('images')
            for image in new_images:
                if image and image.filename:
                    filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    db.session.add(ListingImage(filename=filename, listing_id=listing.id))

            db.session.commit()
            flash('✅ Listing updated successfully!')
            return redirect(url_for('listing_detail', slug=listing.slug))
        except Exception as e:
            traceback.print_exc()
            flash('❌ Error updating listing.')

    return render_template('admin_edit_listing.html', listing=listing)


@app.route('/admin/delete-listing/<int:id>', methods=['POST'])
@admin_required
def delete_listing(id):
    listing = Listing.query.get_or_404(id)
    try:
        # Delete all images from folder
        for image in listing.images:
            path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
            if os.path.exists(path):
                os.remove(path)
        db.session.delete(listing)
        db.session.commit()
        flash('🗑️ Listing deleted successfully!')
        return redirect(url_for('listings'))
    except Exception as e:
        traceback.print_exc()
        flash('❌ Error deleting listing.')
        return redirect(url_for('listing_detail', slug=listing.slug))


# ==============================
# 🔹 SUBSCRIBE
# ==============================

@app.route('/subscribe', methods=['POST'])
def subscribe():
    email = request.form.get('email', '').strip().lower()
    if not email:
        flash("Email is required to subscribe."); return redirect(url_for('home'))
    if not re.match(EMAIL_REGEX, email):
        flash("Invalid email format."); return redirect(url_for('home'))
    if Newsletter.query.filter_by(email=email).first():
        flash("You are already subscribed!"); return redirect(url_for('home'))

    db.session.add(Newsletter(email=email))
    db.session.commit()

    # Welcome email
    text_body = f"Hello 👋,\n\nThank you for subscribing!"
    html_body = f"<p>Hello 👋,</p><p>Thank you for subscribing!</p>"
    send_email(subject="Welcome to Great Mar-cy’s & Sons Limited", recipients=[email], body_text=text_body, body_html=html_body)

    # Admin notification
    admin_email = DEFAULT_SENDER
    send_email(subject="📩 New Newsletter Subscriber Alert", recipients=[admin_email], body_text=f"New subscriber: {email}")

    flash("✅ Thank you for subscribing!"); return redirect(url_for('home'))

# ==============================
# 🔹 ENQUIRY
# ==============================
@app.route('/enquire', methods=['POST'])
def enquiry():
    name = request.form.get('name', '').strip()
    email = request.form.get('email', '').strip()
    message = request.form.get('message', '').strip()
    subject = request.form.get('subject', 'New Enquiry').strip()

    if not name or not email or not message:
        flash("All fields are required."); return redirect(url_for('contact'))
    if not re.match(EMAIL_REGEX, email):
        flash("Invalid email address."); return redirect(url_for('contact'))

    db.session.add(Enquiry(name=name, email=email, subject=subject, message=message))
    db.session.commit()

    # Confirmation to user
    user_text = f"Hi {name},\n\nThanks for contacting us!"
    user_html = f"<p>Hi <b>{name}</b>,</p><p>Thanks for contacting us!</p>"
    send_email(subject="We’ve received your enquiry", recipients=[email], body_text=user_text, body_html=user_html)

    # Admin notification
    admin_text = f"New Enquiry:\nName: {name}\nEmail: {email}\nSubject: {subject}\nMessage: {message}\nSent: {datetime.now()}"
    send_email(subject=f"New Enquiry from {name}", recipients=[DEFAULT_SENDER], body_text=admin_text)

    flash("✅ Your enquiry has been received."); return redirect(url_for('contact'))

# ==============================
# 🔹 ADMIN LOGIN / LOGOUT
# ==============================
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['admin_logged_in'] = True; flash("✅ Logged in successfully!")
            return redirect(url_for('admin_dashboard'))
        flash("❌ Invalid credentials"); return redirect(url_for('admin_login'))
    return render_template('admin-login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None); flash("Logged out successfully."); return redirect(url_for('admin_login'))
# ==============================
# 🔹 ADMIN DASHBOARD & PROPERTIES
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
        title = request.form.get('title', '').strip()
        location = request.form.get('location', '').strip()
        price = request.form.get('price', '').strip()
        description = request.form.get('description', '').strip()
        seo_title = request.form.get('seo_title', '').strip()[:255] or None
        meta_description = request.form.get('meta_description', '').strip()[:300] or None
        keywords = request.form.get('keywords', '').strip()[:500] or None

        if not title or not location or not description:
            flash('All required fields (Title, Location, Description) must be filled.')
            return redirect(url_for('add_property'))

        # Image upload
        image_file = request.files.get('image')
        image_filename = ''
        if image_file and image_file.filename:
            image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # Video upload
        video_file = request.files.get('video')
        video_filename = ''
        if video_file and video_file.filename:
            video_filename = f"{uuid.uuid4().hex}_{secure_filename(video_file.filename)}"
            video_file.save(os.path.join(app.config['UPLOAD_FOLDER'], video_filename))

        # Slug generation
        slug = slugify(title)
        if Property.query.filter_by(slug=slug).first():
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

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
    seo = {
        "title": prop.title,
        "description": prop.description[:150],
        "keywords": prop.keywords or "",
        "image": prop.image_url
    }
    return render_template('property_detail.html', property=prop, seo=seo)


@app.route('/delete-property/<int:property_id>', methods=['POST'])
@admin_required
def delete_property(property_id):
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


# ✅ move classes out of function — start at far left
class Listing(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    price = db.Column(db.String(100))
    description = db.Column(db.Text)
    property_type = db.Column(db.String(100))  # land, duplex, shop, etc.
    status = db.Column(db.String(50))  # rent or sale
    category = db.Column(db.String(50))  # residential or commercial
    images = db.relationship('ListingImage', backref='listing', cascade='all, delete', lazy=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    slug = db.Column(db.String(255), unique=True, nullable=False)


class ListingImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255))
    listing_id = db.Column(db.Integer, db.ForeignKey('listing.id'))



# ==============================
# 🔹 BLOG ADMIN ROUTES
# ==============================
@app.route('/admin/blog')
@admin_required
def admin_blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin/blog_list.html', posts=posts)


@app.route('/admin/blog/new', methods=['GET', 'POST'])
@admin_required
def admin_new_blog():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        seo_title = request.form.get('seo_title')[:255] or None
        meta_description = request.form.get('meta_description')[:300] or None
        keywords = request.form.get('keywords')[:500] or None

        if not title or not content:
            flash("Title and content are required!")
            return redirect(url_for('admin_new_blog'))

        # Image upload
        image_file = request.files.get('image')
        image_filename = None
        if image_file and image_file.filename:
            image_filename = f"{uuid.uuid4().hex}_{secure_filename(image_file.filename)}"
            image_file.save(os.path.join(app.config['UPLOAD_FOLDER'], image_filename))

        # Slug
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
@admin_required
def admin_edit_blog(post_id):
    post = BlogPost.query.get_or_404(post_id)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        seo_title = request.form.get('seo_title')[:255] or None
        meta_description = request.form.get('meta_description')[:300] or None
        keywords = request.form.get('keywords')[:500] or None

        if not title or not content:
            flash("Title and content are required!")
            return redirect(url_for('admin_edit_blog', post_id=post.id))

        post.title = title
        post.content = content
        post.seo_title = seo_title
        post.meta_description = meta_description
        post.keywords = keywords

        image_file = request.files.get('image')
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
@admin_required
def admin_delete_blog(post_id):
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
# 🔹 BLOG FRONTEND ROUTES
# ==============================
@app.route('/blog')
def blog():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    seo = {"title": "Our Blog", "description": "Read the latest blog posts", "keywords": "blog, news, updates", "image": ""}
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



@app.route('/uploads/<path:filename>')
def serve_file(filename):
    upload_dir = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    return send_from_directory(upload_dir, filename)




@app.route('/admin/upload-listing', methods=['GET', 'POST'])
@admin_required
def upload_listing():
    if request.method == 'POST':
        try:
            title = request.form.get('title', '').strip()
            location = request.form.get('location', '').strip()
            price = request.form.get('price', '').strip()
            description = request.form.get('description', '').strip()
            property_type = request.form.get('property_type', '').strip()
            status = request.form.get('status', '').strip()
            category = request.form.get('category', '').strip()

            if not title or not location or not description:
                flash('All required fields must be filled!')
                return redirect(url_for('upload_listing'))

            # Slug creation
            slug = slugify(title)
            if Listing.query.filter_by(slug=slug).first():
                slug = f"{slug}-{uuid.uuid4().hex[:6]}"

            # Save listing
            listing = Listing(
                title=title,
                location=location,
                price=price,
                description=description,
                property_type=property_type,
                status=status,
                category=category,
                slug=slug
            )
            db.session.add(listing)
            db.session.commit()

            # Handle multiple image uploads
            images = request.files.getlist('images')
            for image in images:
                if image and image.filename:
                    filename = f"{uuid.uuid4().hex}_{secure_filename(image.filename)}"
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    db.session.add(ListingImage(filename=filename, listing_id=listing.id))
            db.session.commit()

            flash('✅ Listing uploaded successfully!')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            traceback.print_exc()
            flash('❌ Error uploading listing.')
            return redirect(url_for('upload_listing'))

    return render_template('admin_upload_listing.html')


# ==============================
# 🔹 RUN SERVER
# ==============================


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=True)
