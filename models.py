from extensions import db
from datetime import datetime

class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    video_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Property {self.title}>"


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🟢 SEO Fields (now inside the class correctly)
    seo_title = db.Column(db.String(70))          # Custom title for Google
    meta_description = db.Column(db.String(160))  # Short description for SEO
    keywords = db.Column(db.String(300))          # Comma-separated keywords
    slug = db.Column(db.String(200), unique=True) # URL-friendly slug

    def __repr__(self):
        return f"<BlogPost {self.title}>"
