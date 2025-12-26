# create_user.py
from database import SessionLocal, engine, Base
from models import User
from werkzeug.security import generate_password_hash

# >>> Cambia estos valores si quieres otras credenciales <<<
USERNAME = "GrupoAzar"
PASSWORD = "3108"
ROLE = "admin"        # "admin" o "capturista"
ACTIVE = 1

Base.metadata.create_all(bind=engine)
db = SessionLocal()

u = db.query(User).filter_by(username=USERNAME).first()
if not u:
    u = User(username=USERNAME,
             password_hash=generate_password_hash(PASSWORD),
             role=ROLE,
             active=ACTIVE)
    db.add(u)
    msg = "Usuario creado"
else:
    u.password_hash = generate_password_hash(PASSWORD)
    u.role = ROLE
    u.active = ACTIVE
    msg = "Usuario actualizado"

db.commit()
db.close()
print(f"{msg}: {USERNAME} / {PASSWORD} (rol={ROLE}, active={ACTIVE})")
