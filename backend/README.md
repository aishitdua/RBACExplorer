# ⚙️ RBAC Explorer — Backend

This is a FastAPI-powered asynchronous backend for managing RBAC data.

## 🧱 Key Components
- **FastAPI**: Main API framework.
- **SQLAlchemy (Async)**: Database ORM for SQLite.
- **Alembic**: Database versioning and migrations.
- **PyYAML**: High-level YAML parsing for nested role structures.

## 🚀 Local Development
1. **Initialize Environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Setup Database**:
   ```bash
   alembic upgrade head
   ```
3. **Run Server**:
   ```bash
   uvicorn app.main:app --reload
   ```

## 📡 API Highlights
- `GET /api/v1/projects`: List all design projects.
- `POST /api/v1/projects/{slug}/import/yaml`: Smart YAML importer with inheritance detection.
- `GET /api/v1/projects/{slug}/simulate`: Path-based permission simulator.
- `GET /api/v1/projects/{slug}/export/yaml`: Reconstructs DB state back to IaC YAML.
