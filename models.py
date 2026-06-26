from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Sector(Base):
    __tablename__ = "sectors"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    icon = Column(String)
    color_hex = Column(String)

    stages = relationship("Stage", back_populates="sector")
    orders = relationship("Order", back_populates="sector")


class Stage(Base):
    __tablename__ = "stages"

    id = Column(String, primary_key=True, index=True)
    sector_id = Column(String, ForeignKey("sectors.id"))
    name = Column(String)
    capacity = Column(Integer)
    order_index = Column(Integer)

    sector = relationship("Sector", back_populates="stages")


class Company(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    short_name = Column(String)
    bg_color = Column(String)
    text_color = Column(String)

    orders = relationship("Order", back_populates="company")


class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    sector_id = Column(String, ForeignKey("sectors.id"))
    company_id = Column(String, ForeignKey("companies.id"))
    product_type = Column(String)
    quantity = Column(String)
    stage_index = Column(Integer)
    status = Column(String)
    deadline = Column(String)
    color = Column(String)
    notes = Column(String)
    difficulty = Column(String, nullable=True)
    workers_assigned = Column(Integer, nullable=True)
    planned_days = Column(Integer, nullable=True)

    sector = relationship("Sector", back_populates="orders")
    company = relationship("Company", back_populates="orders")
