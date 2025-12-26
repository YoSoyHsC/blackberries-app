from database import SessionLocal
from models import User

db = SessionLocal()

users = db.query(User).all()
for u in users:
    print(u.id, u.username, u.role, u.active)

db.close()
