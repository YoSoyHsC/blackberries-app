from database import SessionLocal
from models import User

USERNAME = "guido"   # usuario que quieres borrar

db = SessionLocal()
u = db.query(User).filter_by(username=USERNAME).first()

if u:
    db.delete(u)
    db.commit()
    print(f"Usuario eliminado: {USERNAME}")
else:
    print(f"No existe el usuario {USERNAME}")

db.close()
