from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

import models, schemas
from database import engine, get_db

# Create DB tables
models.Base.metadata.create_all(bind=engine)

def seed_db():
    db = next(get_db())
    if db.query(models.Sector).count() == 0:
        # 1. Sektorlar
        s1 = models.Sector(id="corab", name="Corab", icon="🧦", color_hex="#c4b0ff")
        s2 = models.Sector(id="teks", name="Trikotaj", icon="👕", color_hex="#5ddba8")
        db.add_all([s1, s2])
        db.commit()

        # 2. Etaplar
        stages = [
            models.Stage(id="c1", sector_id="corab", name="Hörgü", capacity=2000, order_index=0),
            models.Stage(id="c2", sector_id="corab", name="Burun Tikişi", capacity=1500, order_index=1),
            models.Stage(id="c3", sector_id="corab", name="Forma", capacity=1800, order_index=2),
            models.Stage(id="c4", sector_id="corab", name="Qablaşdırma", capacity=3000, order_index=3),
            
            models.Stage(id="t1", sector_id="teks", name="Kəsim", capacity=1000, order_index=0),
            models.Stage(id="t2", sector_id="teks", name="Tikiş", capacity=800, order_index=1),
            models.Stage(id="t3", sector_id="teks", name="Ütü / Qablaşdır..", capacity=1200, order_index=2)
        ]
        db.add_all(stages)
        db.commit()

        # 3. Şirkətlər
        companies = [
            models.Company(id="brav", name="Bravo Supermarket", short_name="BR", bg_color="#e0f2fe", text_color="#0369a1"),
            models.Company(id="azar", name="Azər İlmə", short_name="AZ", bg_color="#fce7f3", text_color="#be185d"),
            models.Company(id="zel", name="ZelHome", short_name="ZH", bg_color="#dcfce7", text_color="#15803d")
        ]
        db.add_all(companies)
        db.commit()

        # 4. Sifarişlər
        orders = [
            models.Order(id="ORD-101", sector_id="corab", company_id="brav", product_type="Qış corabı (Qalın)", quantity="15,000", stage_index=2, status="Davam edir", deadline="24 Fevral", color="#b91c1c", notes="İplik sayı xüsusi olaraq 2 qat artırılıb."),
            models.Order(id="ORD-102", sector_id="corab", company_id="azar", product_type="İkili İdman Corabı", quantity="8,000", stage_index=1, status="Gecikmiş", deadline="18 Fevral", color="#1d4ed8", notes="Təcili sifariş!"),
            models.Order(id="ORD-103", sector_id="corab", company_id="zel", product_type="Qadın corabı", quantity="12,000", stage_index=3, status="Tamamlandı", deadline="20 Fevral", color="#047857", notes="Tamamlanıb və anbara təhvil verilib."),
            
            models.Order(id="ORD-201", sector_id="teks", company_id="brav", product_type="Polo T-Shirt", quantity="5,000", stage_index=0, status="Davam edir", deadline="10 Mart", color="#ca8a04", notes="Kəsim mərhələsindədir."),
            models.Order(id="ORD-202", sector_id="teks", company_id="zel", product_type="Şalvar", quantity="2,000", stage_index=2, status="Gözləyir", deadline="15 Mart", color="#4f46e5", notes="Aksesuar tədarükü gözlənilir.")
        ]
        db.add_all(orders)
        db.commit()

seed_db()

app = FastAPI(title="Factory Dashboard API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------
# SECTORS & STAGES
# -----------------
@app.get("/api/sectors", response_model=List[schemas.Sector])
def read_sectors(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    sectors = db.query(models.Sector).offset(skip).limit(limit).all()
    return sectors

# -----------------
# COMPANIES
# -----------------
@app.get("/api/companies", response_model=List[schemas.Company])
def read_companies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    companies = db.query(models.Company).offset(skip).limit(limit).all()
    return companies

@app.post("/api/companies", response_model=schemas.Company)
def create_company(company: schemas.CompanyBase, db: Session = Depends(get_db)):
    db_company = db.query(models.Company).filter(models.Company.id == company.id).first()
    if db_company:
        raise HTTPException(status_code=400, detail="Company ID already registered")
    new_company = models.Company(**company.dict())
    db.add(new_company)
    db.commit()
    db.refresh(new_company)
    return new_company

# -----------------
# ORDERS
# -----------------
@app.get("/api/orders", response_model=List[schemas.Order])
def read_orders(sector_id: str = None, company_id: str = None, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    query = db.query(models.Order)
    if sector_id:
        query = query.filter(models.Order.sector_id == sector_id)
    if company_id:
        query = query.filter(models.Order.company_id == company_id)
    orders = query.offset(skip).limit(limit).all()
    return orders

@app.post("/api/orders", response_model=schemas.Order)
def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order.id).first()
    if db_order:
        raise HTTPException(status_code=400, detail="Order ID already exists")
    new_order = models.Order(**order.dict())
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    return new_order

@app.put("/api/orders/{order_id}", response_model=schemas.Order)
def update_order(order_id: str, order: schemas.OrderCreate, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    for key, value in order.dict().items():
        setattr(db_order, key, value)
        
    db.commit()
    db.refresh(db_order)
    return db_order

@app.patch("/api/orders/{order_id}/stage", response_model=schemas.Order)
def update_order_stage(order_id: str, stage_update: schemas.OrderStageUpdate, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_order.stage_index = stage_update.stage_index
    db.commit()
    db.refresh(db_order)
    return db_order

@app.patch("/api/orders/{order_id}/status", response_model=schemas.Order)
def update_order_status(order_id: str, status_update: schemas.OrderStatusUpdate, db: Session = Depends(get_db)):
    db_order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    db_order.status = status_update.status
    db.commit()
    db.refresh(db_order)
    return db_order

# -----------------
# DASHBOARD DATA
# -----------------
@app.get("/api/dashboardData")
def get_dashboard_data(db: Session = Depends(get_db)):
    # Composite endpoint for the frontend to pull everything at once if desired
    sectors = db.query(models.Sector).all()
    companies = db.query(models.Company).all()
    orders = db.query(models.Order).all()
    
    return {
        "sectors": sectors,
        "companies": companies,
        "orders": orders
    }

# -----------------
# FRONTEND DASHBOARD
# -----------------
@app.get("/")
def serve_dashboard():
    import os
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"message": "index.html not found"}

