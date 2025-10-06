from extensions import db
from datetime import datetime
from slugify import slugify
from sqlalchemy import event

# ==============================
# 🔹 PROPERTY MODEL
# ==============================
class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    video_url = db.Column(db.String(300))
    slug = db.Column(db.String(250), unique=True, nullable=False)
    
    # Add SEO fields
    seo_title = db.Column(db.String(255))
    meta_description = db.Column(db.String(300))
    keywords = db.Column(db.String(500))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Property {self.title}>"


# ==============================
# 🔹 BLOG POST MODEL
# ==============================
class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(255))
    seo_title = db.Column(db.String(70))
    meta_description = db.Column(db.String(160))
    keywords = db.Column(db.String(300))
    slug = db.Column(db.String(200), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<BlogPost {self.title}>"

# --- Auto-generate slug before insert ---
@event.listens_for(BlogPost, 'before_insert')
def generate_slug(mapper, connection, target):
    if target.title and not target.slug:
        base_slug = slugify(target.title)
        slug = base_slug
        counter = 1
        while connection.execute(
            db.select(BlogPost.id).where(BlogPost.slug == slug)
        ).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        target.slug = slug

# --- Update slug before update if title changes ---
@event.listens_for(BlogPost, 'before_update')
def update_slug(mapper, connection, target):
    if target.title:
        base_slug = slugify(target.title)
        slug = base_slug
        counter = 1
        while connection.execute(
            db.select(BlogPost.id)
            .where(BlogPost.slug == slug)
            .where(BlogPost.id != target.id)
        ).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        target.slug = slug

# ==============================
# 🔹 ENQUIRY MODEL
# ==============================
class Enquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Enquiry {self.email}>"

# ==============================
# 🔹 NEWSLETTER MODEL
# ==============================
class Newsletter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=True)  # for confirmation link
    confirmed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Newsletter {self.email}>"
