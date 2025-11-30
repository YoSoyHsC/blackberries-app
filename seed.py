from database import SessionLocal, Base, engine
from models import Fruit, Sector, Picker, User, BoxSize, PriceList
from werkzeug.security import generate_password_hash
from sqlalchemy import text

def ensure_columns():
    with engine.connect() as conn:
        cols = conn.execute(text("PRAGMA table_info(fruits)")).fetchall()
        if not any(c[1]=='active' for c in cols):
            conn.execute(text("ALTER TABLE fruits ADD COLUMN active INTEGER DEFAULT 1"))
        cols = conn.execute(text("PRAGMA table_info(sectors)")).fetchall()
        if not any(c[1]=='active' for c in cols):
            conn.execute(text("ALTER TABLE sectors ADD COLUMN active INTEGER DEFAULT 1"))
        cols = conn.execute(text("PRAGMA table_info(harvests)")).fetchall()
        if cols and not any(c[1]=='size_id' for c in cols):
            conn.execute(text("ALTER TABLE harvests ADD COLUMN size_id INTEGER DEFAULT 1"))

def seed():
    Base.metadata.create_all(bind=engine)
    ensure_columns()
    db = SessionLocal()
    try:
        for name in ["Zarzamora","Frambuesa","Arándano","Cereza"]:
            if not db.query(Fruit).filter_by(name=name).first():
                db.add(Fruit(name=name, active=1))
        for i in range(1,11):
            code=f"S{i}"
            if not db.query(Sector).filter_by(code=code).first():
                db.add(Sector(code=code, description=f"Sector {i}", active=1))
        for code,name in [("C001","Ana Pérez"),("C002","Beatriz López"),
                          ("C003","Carla Díaz"),("C004","Diana Ruiz"),("C005","Elena Soto")]:
            if not db.query(Picker).filter_by(code=code).first():
                db.add(Picker(code=code, name=name, active=1))
        if not db.query(User).filter_by(username="admin").first():
            db.add(User(username="admin", role="admin", active=1,
                        password_hash=generate_password_hash("admin123")))
        if not db.query(User).filter_by(username="capturista").first():
            db.add(User(username="capturista", role="capturista", active=1,
                        password_hash=generate_password_hash("corte123")))
        for s in ["4oz","5oz","6oz","12oz"]:
            if not db.query(BoxSize).filter_by(name=s).first():
                db.add(BoxSize(name=s, active=1))
        db.commit()

        def set_price(fruit, size, price):
            f = db.query(Fruit).filter_by(name=fruit).first()
            z = db.query(BoxSize).filter_by(name=size).first()
            if f and z and not db.query(PriceList).filter_by(fruit_id=f.id, size_id=z.id).first():
                db.add(PriceList(fruit_id=f.id, size_id=z.id, price=price))

        set_price("Frambuesa","4oz",12); set_price("Frambuesa","5oz",16)
        set_price("Frambuesa","6oz",20); set_price("Frambuesa","12oz",20)
        for fruit in ["Zarzamora","Arándano","Cereza"]:
            set_price(fruit,"4oz",10); set_price(fruit,"5oz",14)
            set_price(fruit,"6oz",18); set_price(fruit,"12oz",22)

        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    seed()
