from sqlalchemy import Column, Integer, String, Date, Numeric, ForeignKey, Index, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False, default="capturista")
    active = Column(Integer, default=1)

class Fruit(Base):
    __tablename__ = "fruits"
    id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    active = Column(Integer, default=1)

class Sector(Base):
    __tablename__ = "sectors"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    description = Column(String(100))
    active = Column(Integer, default=1)

class Picker(Base):
    __tablename__ = "pickers"
    id = Column(Integer, primary_key=True)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    active = Column(Integer, default=1)

class BoxSize(Base):
    __tablename__ = "box_sizes"
    id = Column(Integer, primary_key=True)
    name = Column(String(20), unique=True, nullable=False)
    active = Column(Integer, default=1)

class PriceList(Base):
    __tablename__ = "price_list"
    id = Column(Integer, primary_key=True)
    fruit_id = Column(Integer, ForeignKey("fruits.id"), nullable=False)
    size_id  = Column(Integer, ForeignKey("box_sizes.id"), nullable=False)
    price    = Column(Numeric(10,2), nullable=False, default=0)
    fruit = relationship("Fruit")
    size  = relationship("BoxSize")
    __table_args__ = (UniqueConstraint('fruit_id','size_id', name='uq_fruit_size'),)

class Harvest(Base):
    __tablename__ = "harvests"
    id = Column(Integer, primary_key=True)
    date = Column(Date, nullable=False)
    fruit_id  = Column(Integer, ForeignKey("fruits.id"), nullable=False)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=False)
    picker_id = Column(Integer, ForeignKey("pickers.id"), nullable=False)
    size_id   = Column(Integer, ForeignKey("box_sizes.id"), nullable=False)
    boxes = Column(Integer, nullable=False, default=0)
    price_per_box = Column(Numeric(10,2), nullable=False, default=0)
    total = Column(Numeric(12,2), nullable=False, default=0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    fruit = relationship("Fruit")
    sector = relationship("Sector")
    picker = relationship("Picker")
    size   = relationship("BoxSize")
    creator= relationship("User")

Index("ix_harvest_date", Harvest.date)
Index("ix_harvest_picker", Harvest.picker_id)
Index("ix_harvest_sector", Harvest.sector_id)
Index("ix_harvest_fruit", Harvest.fruit_id)
Index("ix_harvest_size", Harvest.size_id)
