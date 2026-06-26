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
    difficulty: Optional[str] = None
    workers_assigned: Optional[int] = None
    planned_days: Optional[int] = None

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

class PlanOrderInput(BaseModel):
    order_id: str
    workers: int
    difficulty: str

class OrderPlanRequest(BaseModel):
    orders: List[PlanOrderInput]

class PlannedOrderResponse(BaseModel):
    order_id: str
    planned_days: int
    new_deadline: str

class OrderPlanResponse(BaseModel):
    results: List[PlannedOrderResponse]

class ApplyPlanRequest(BaseModel):
    plans: List[PlannedOrderResponse]


