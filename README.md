# FabriQ

FabriQ is a manufacturing production management dashboard and RESTful JSON API. It is designed to visualize live data across factory sectors, track processing stages, and identify supply bottlenecks.

## Features

- **Capacity Tracking:** Monitor manufacturing utilization rates and load per sector.
- **Workflow & Order Management:** Track customer orders as they move through defined stages (e.g., Cutting, Sewing, Packaging).
- **Status Indicators:** Immediate visual feedback identifying delayed, pending, and completed tasks.
- **ERP Integration Ready:** Driven strictly by a REST API, enabling seamless synchronization with external enterprise systems.

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy
- **Database:** SQLite (Configured to easily migrate to PostgreSQL or MySQL for production)
- **Frontend:** Semantic HTML, CSS Variables, Vanilla JavaScript

## Local Development

### 1. Clone the Repository

```bash
git clone https://github.com/Anar5432/FabriQ.git
cd FabriQ
```

### 2. Configure Environment

It is recommended to run the project inside a virtual environment.

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install fastapi uvicorn sqlalchemy pydantic
```

### 4. Run the Server

```bash
uvicorn main:app --reload
```

The database generates tables and injects initial sample structure on launch if no data is found. Navigate to `http://localhost:8000/` to access the dashboard.

## Project Structure

- `main.py`: Application entry point, controller routing, static server fallback, and data seeding.
- `models.py`: Object-Relational Mapping (ORM) definitions mapping Python objects to SQL tables.
- `schemas.py`: Pydantic validation classes ensuring type safety and formatting for API transactions.
- `database.py`: Configuration module for database sessions and engine initialization.
- `index.html`: Lightweight, dependency-free frontend client handling network fetches and dynamic DOM reconciliation.
