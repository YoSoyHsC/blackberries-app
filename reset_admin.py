from database import SessionLocal, engine, Base
from models import User
from werkzeug.security import generate_password_hash

Base.metadata.create_all(bind=engine)
db = SessionLocal()
u = db.query(User).filter_by(username="admin").first()
if not u:
    u = User(username="admin", role="admin", active=1,
             password_hash=generate_password_hash("admin123"))
    db.add(u)
else:
    u.password_hash = generate_password_hash("admin123")
    u.role = "admin"
    u.active = 1
db.commit(); db.close()
print("Admin listo: admin / admin123")
