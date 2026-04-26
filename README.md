# 🛡️ RBAC Explorer

**RBAC Explorer** is a high-performance, visual design tool for managing complex Role-Based Access Control hierarchies. It allows security engineers and developers to visualize, simulate, and export RBAC configurations as Infrastructure-as-Code.

![Aesthetic Dashboard Mockup](https://img.shields.io/badge/Aesthetics-Premium-blueviolet)
![Tech Stack](https://img.shields.io/badge/Stack-FastAPI_%7C_React_%7C_Cytoscape-blue)

---

## 🚀 Key Features

- **📊 Interactive Graph Designer**: Visualize roles, inheritance lines, and permissions in a clean, hierarchical tree.
- **📦 Bulk Import System**: Bootstrap projects instantly using nested YAML (Roles/Inheritance) and CSV (Endpoints).
- **🤖 Automated Mapping**: Intelligently guesses HTTP methods and paths from permission names during import.
- **📂 Compound Grouping**: Permission nodes are automatically grouped by "Service Modules" for architectural clarity.
- **📥 YAML Export (IaC)**: Design your architecture visually and download it as an Infrastructure-as-Code YAML file.
- **🧪 Permission Simulator**: Test any role against your API paths to verify access in real-time.

---

## 🛠️ Stack

- **Backend**: FastAPI, SQLAlchemy (Async), SQLite, Pydantic, PyYAML
- **Frontend**: React (Vite), Tailwind CSS, Cytoscape.js (fcose/breadthfirst layouts)
- **Migrations**: Alembic

---

## 📋 Getting Started

### 1. Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Mac/Linux
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

---

## 📄 Configuration Formats

### YAML Inheritance (Roles)

```yaml
developer:
  auth:
    login: "User authentication"

payments_dev:
  include:
    - developer
  payments:
    process: "Handle transactions"
```

### CSV Endpoints (Resources)

```csv
method,path,description
GET,/api/v1/users,List all users
POST,/api/v1/payments,Execute payment
```

---

## 📐 Design Philosophy

RBAC Explorer is built on the principle that **Security should be Visual**. By mapping technical endpoints to human-readable permission modules, we bridge the gap between compliance requirements and technical implementation.

---

## 🏗️ Project Structure

```text
├── backend/
│   ├── app/           # FastAPI Logic & Models
│   └── alembic/       # Database Migrations
├── frontend/
│   ├── src/
│   │   ├── api/       # API Clients
│   │   ├── pages/     # Workspace & Project views
│   │   └── tabs/      # Graph, Simulator, Import
└── README.md
```

---
