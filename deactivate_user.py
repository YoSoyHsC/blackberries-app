from database import SessionLocal
from models import User

USERNAME = "guido"   # <-- pon aquí el usuario viejo que ya NO quieres usar

db = SessionLocal()
u = db.query(User).filter_by(username=USERNAME).first()

if u:
    u.active = 0      # lo marcamos como inactivo
    db.commit()
    print(f"Usuario desactivado: {USERNAME}")
else:
    print(f"No existe el usuario {USERNAME}")

db.close()
