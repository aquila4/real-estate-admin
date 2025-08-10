from app import app, db
from models import Property

with app.app_context():
    db.create_all()
    print("✅ Table created successfully.")
