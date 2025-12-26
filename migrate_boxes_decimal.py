from sqlalchemy import text
from database import engine

with engine.connect() as conn:
    conn.execute(text("""
        ALTER TABLE harvests
        ALTER COLUMN boxes TYPE NUMERIC(10,2)
    """))
    conn.commit()

print("✅ Columna boxes actualizada a NUMERIC(10,2)")
