from pydantic import BaseModel
from typing import List, Optional

class StageBase(BaseModel):
    id: str
    sector_id: str
    name: str
    capacity: int
    order_index: int

class Stage(StageBase):
    class Config:
        orm_mode = True
        from_attributes = True

class SectorBase(BaseModel):
    id: str
    name: str
    icon: str
    color_hex: str

class Sector(SectorBase):
    stages: List[Stage] = []
    class Config:
        orm_mode = True
        from_attributes = True

class CompanyBase(BaseModel):
    id: str
    name: str
    short_name: str
    bg_color: str
    text_color: str

class Company(CompanyBase):
    class Config:
        orm_mode = True
        from_attributes = True

class OrderBase(BaseModel):
    id: str
    sector_id: str
    company_id: str
    product_type: str
    quantity: str
    stage_index: int
    status: str
    deadline: str
    color: str
    notes: Optional[str] = None

class OrderCreate(OrderBase):
    pass

class Order(OrderBase):
    class Config:
        orm_mode = True
        from_attributes = True

class OrderStageUpdate(BaseModel):
    stage_index: int

class OrderStatusUpdate(BaseModel):
    status: str
