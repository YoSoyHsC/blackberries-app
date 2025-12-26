from database import SessionLocal
from models import User

# 👉 Pon aquí los usuarios que quieres ELIMINAR
USERNAMES_TO_DELETE = ["admin", "capturista"]  # edita la lista a tu gusto

db = SessionLocal()

for name in USERNAMES_TO_DELETE:
    u = db.query(User).filter_by(username=name).first()
    if u:
        db.delete(u)
        print(f"Usuario eliminado: {name}")
    else:
        print(f"No existe el usuario: {name}")

db.commit()
db.close()
print("Listo, usuarios procesados.")
