# Deploy to Vercel + Render + Neon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy RBACExplorer — React frontend to Vercel, FastAPI backend to Render, and Postgres database to Neon — with zero manual steps after initial setup.

**Architecture:** Neon hosts the Postgres database; Render runs the FastAPI backend (uvicorn) with Alembic migrations on each deploy; Vercel serves the Vite-built React SPA and routes API calls to the Render service via `VITE_API_URL`. CORS on the backend is restricted to the Vercel origin.

**Tech Stack:** React 19, Vite 8, FastAPI, SQLAlchemy (asyncpg), Alembic, pydantic-settings, Neon Postgres, Render (Python web service), Vercel (static/SPA)

---

## File Map

| File                      | Action             | Purpose                                                                            |
| ------------------------- | ------------------ | ---------------------------------------------------------------------------------- |
| `render.yaml`             | Create (repo root) | Render reads this at repo root to configure the web service                        |
| `backend/render.yaml`     | Delete             | Was in wrong location; superseded by root render.yaml                              |
| `backend/app/database.py` | Modify             | Auto-convert `postgresql://` → `postgresql+asyncpg://` so Neon's default URL works |
| `backend/app/main.py`     | Modify             | Restrict CORS `allow_origins` to env-configured list (not `*`)                     |
| `vercel.json`             | Create (repo root) | SPA fallback rewrite so React Router deep-links work                               |

---

### Task 1: Fix DATABASE_URL driver prefix in `database.py`

Neon provides connection strings as `postgresql://`. The async SQLAlchemy engine requires `postgresql+asyncpg://`. Alembic's `env.py` uses a sync `create_engine` call and will fail if given the asyncpg variant. The fix: store `DATABASE_URL` as the standard `postgresql://` form; convert it to asyncpg only inside `get_engine()`.

**Files:**

- Modify: `backend/app/database.py`

- [ ] **Step 1: Read the current file**

```bash
cat backend/app/database.py
```

- [ ] **Step 2: Replace `get_engine` to auto-convert the URL**

Replace the contents of `backend/app/database.py` with:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Settings(BaseSettings):
    database_url: str
    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()


class Base(DeclarativeBase):
    pass


def _asyncpg_url(url: str) -> str:
    """Convert a standard postgresql:// URL to the asyncpg dialect."""
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url  # already has a driver specified


_engine = None
_AsyncSessionFactory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(_asyncpg_url(settings.database_url), echo=False)
    return _engine


def get_session_factory():
    global _AsyncSessionFactory
    if _AsyncSessionFactory is None:
        _AsyncSessionFactory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _AsyncSessionFactory


async def get_session() -> AsyncSession:
    async with get_session_factory()() as session:
        yield session
```

- [ ] **Step 3: Verify Alembic env.py still uses the raw URL (sync-compatible)**

```bash
grep -n "DATABASE_URL\|create_engine" backend/alembic/env.py
```

Expected: `create_engine(url, ...)` where `url = os.environ.get("DATABASE_URL")`. This is fine — psycopg2-binary is already in requirements.txt and will handle `postgresql://` URLs synchronously.

- [ ] **Step 4: Commit**

```bash
git add backend/app/database.py
git commit -m "fix: auto-convert postgresql:// to asyncpg dialect in async engine"
```

---

### Task 2: Restrict CORS origins in `main.py`

`allow_origins=["*"]` is not acceptable in production. The backend will accept an env var `ALLOWED_ORIGINS` (comma-separated URLs) and fall back to `*` only when it is absent (local dev).

**Files:**

- Modify: `backend/app/main.py`
- Modify: `backend/app/database.py` (add `allowed_origins` to Settings)

- [ ] **Step 1: Add `allowed_origins` to Settings**

In `backend/app/database.py`, update the `Settings` class:

```python
class Settings(BaseSettings):
    database_url: str
    allowed_origins: str = "*"
    model_config = SettingsConfigDict(env_file=".env")
```

- [ ] **Step 2: Update CORS middleware in `main.py`**

Replace the `CORSMiddleware` block in `backend/app/main.py`:

```python
from app.database import settings   # add this import at top with the others

# Replace the existing add_middleware call:
origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Full updated `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import settings
from app.routers import (
    analyze,
    export,
    import_,
    permissions,
    projects,
    resources,
    roles,
    simulate,
)

app = FastAPI(title="RBACExplorer API", version="1.0.0")

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api/v1")
app.include_router(roles.router, prefix="/api/v1")
app.include_router(permissions.router, prefix="/api/v1")
app.include_router(resources.router, prefix="/api/v1")
app.include_router(simulate.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(export.router, prefix="/api/v1")
app.include_router(import_.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Verify app still starts locally (quick check)**

```bash
cd backend
DATABASE_URL=sqlite+aiosqlite:///./dev.db ALLOWED_ORIGINS="http://localhost:5173" python -c "from app.main import app; print('OK')"
cd ..
```

Expected: prints `OK` with no import errors.

- [ ] **Step 4: Commit**

```bash
git add backend/app/database.py backend/app/main.py
git commit -m "feat: restrict CORS origins via ALLOWED_ORIGINS env var"
```

---

### Task 3: Create `render.yaml` at repo root

Render discovers `render.yaml` only at the repository root. The existing `backend/render.yaml` is in the wrong location. Create a new one at root that:

- Sets the root directory to `backend/`
- Runs `alembic upgrade head` as part of the build so migrations run on every deploy

**Files:**

- Create: `render.yaml` (repo root)
- Delete: `backend/render.yaml`

- [ ] **Step 1: Create `render.yaml` at repo root**

```yaml
# render.yaml — lives at repo root so Render can discover it
services:
  - type: web
    name: rbacexplorer-api
    runtime: python
    rootDir: backend
    buildCommand: pip install -r requirements.txt && alembic upgrade head
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        sync: false # set manually in Render dashboard
      - key: ALLOWED_ORIGINS
        sync: false # set to your Vercel URL after deploy
```

- [ ] **Step 2: Remove the old misplaced render.yaml**

```bash
git rm backend/render.yaml
```

- [ ] **Step 3: Verify the new file is valid YAML**

```bash
python3 -c "import yaml; yaml.safe_load(open('render.yaml')); print('YAML OK')"
```

Expected: `YAML OK`

- [ ] **Step 4: Commit**

```bash
git add render.yaml
git commit -m "chore: move render.yaml to repo root with rootDir=backend and migration step"
```

---

### Task 4: Create `vercel.json` for SPA routing

React Router uses the HTML5 History API. Without a rewrite rule, any direct navigation to `/projects/my-app` returns a 404 from Vercel's CDN. The `vercel.json` below routes everything that isn't a static asset to `index.html`.

**Files:**

- Create: `vercel.json` (repo root)

- [ ] **Step 1: Create `vercel.json`**

```json
{
  "buildCommand": "cd frontend && npm install && npm run build",
  "outputDirectory": "frontend/dist",
  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]
}
```

- [ ] **Step 2: Verify the build command works locally**

```bash
cd frontend && npm run build && cd ..
```

Expected: `frontend/dist/` directory is created with `index.html` and hashed JS/CSS assets.

- [ ] **Step 3: Commit**

```bash
git add vercel.json
git commit -m "chore: add vercel.json with SPA rewrite and build config"
```

---

### Task 5: Provision Neon database and run initial migration

This task is done in the Neon dashboard and terminal — no code changes.

- [ ] **Step 1: Create a Neon project**

Go to https://neon.tech → New Project → name it `rbacexplorer` → choose a region close to your Render service region (e.g., US East) → Create.

- [ ] **Step 2: Copy the connection string**

In the Neon dashboard, go to **Connection Details** → select the `main` branch → copy the **Connection string**. It looks like:

```
postgresql://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require
```

- [ ] **Step 3: Run Alembic migrations against Neon**

```bash
cd backend
DATABASE_URL="postgresql://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require" \
  alembic upgrade head
cd ..
```

Expected output ends with something like:

```
INFO  [alembic.runtime.migration] Running upgrade  -> abc123, initial schema
```

- [ ] **Step 4: Verify tables were created**

```bash
DATABASE_URL="postgresql://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require" \
  python3 -c "
import psycopg2, os
conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()
cur.execute(\"SELECT tablename FROM pg_tables WHERE schemaname='public'\")
print([r[0] for r in cur.fetchall()])
"
```

Expected: list includes your app tables (e.g., `projects`, `roles`, `permissions`, `resources`, etc.)

---

### Task 6: Deploy backend to Render

- [ ] **Step 1: Create a new Render Web Service**

Go to https://render.com → New → Web Service → connect your GitHub repo.

- [ ] **Step 2: Configure the service**

Render will auto-detect `render.yaml` at the repo root. Confirm these settings:

- **Name:** `rbacexplorer-api`
- **Root Directory:** `backend` (auto-set from render.yaml)
- **Build Command:** `pip install -r requirements.txt && alembic upgrade head`
- **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- **Runtime:** Python

- [ ] **Step 3: Set environment variables in Render dashboard**

Under **Environment** → add:
| Key | Value |
|---|---|
| `DATABASE_URL` | `postgresql://neondb_owner:<password>@<host>.neon.tech/neondb?sslmode=require` |
| `ALLOWED_ORIGINS` | `*` (temporary — update after Vercel deploy gives you a URL) |

- [ ] **Step 4: Deploy and verify health check**

Click **Deploy**. Wait for the build logs to show `alembic upgrade head` completing and uvicorn starting.

Once deployed, test:

```bash
curl https://rbacexplorer-api.onrender.com/health
```

Expected:

```json
{ "status": "ok" }
```

- [ ] **Step 5: Smoke test the API**

```bash
curl -X POST https://rbacexplorer-api.onrender.com/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "deploy-test"}'
```

Expected: `{"slug": "deploy-test", "name": "deploy-test", ...}`

```bash
curl https://rbacexplorer-api.onrender.com/api/v1/projects
```

Expected: JSON array containing the project just created.

---

### Task 7: Deploy frontend to Vercel

- [ ] **Step 1: Install the Vercel CLI (if not installed)**

```bash
npm i -g vercel
```

- [ ] **Step 2: Link and deploy from repo root**

```bash
vercel --prod
```

When prompted:

- **Set up and deploy:** Yes
- **Which scope:** your account
- **Link to existing project:** No (first time)
- **Project name:** `rbacexplorer`
- **Directory:** `.` (repo root — vercel.json handles the rest)

- [ ] **Step 3: Note your Vercel deployment URL**

After deploy, Vercel prints a URL like `https://rbacexplorer.vercel.app`. Copy it.

- [ ] **Step 4: Set `VITE_API_URL` in Vercel dashboard**

Go to Vercel dashboard → your project → **Settings** → **Environment Variables** → add:

| Name           | Value                                   | Environment |
| -------------- | --------------------------------------- | ----------- |
| `VITE_API_URL` | `https://rbacexplorer-api.onrender.com` | Production  |

- [ ] **Step 5: Redeploy frontend to pick up the env var**

```bash
vercel --prod
```

Or trigger redeploy from the Vercel dashboard.

- [ ] **Step 6: Update `ALLOWED_ORIGINS` on Render**

Now that you have the Vercel URL, go to Render → your service → **Environment** → update:

| Key               | Value                             |
| ----------------- | --------------------------------- |
| `ALLOWED_ORIGINS` | `https://rbacexplorer.vercel.app` |

Render will automatically redeploy the service.

---

### Task 8: End-to-end verification

- [ ] **Step 1: Open the deployed frontend**

Navigate to `https://rbacexplorer.vercel.app` in a browser. The app should load.

- [ ] **Step 2: Test deep-link routing**

Navigate directly to `https://rbacexplorer.vercel.app/projects/some-slug`. Should load the app (not a 404).

- [ ] **Step 3: Create a project through the UI**

Use the UI to create a new project. Verify it appears in the list — this confirms the frontend is talking to the backend and the DB is persisting.

- [ ] **Step 4: Verify CORS is working**

Open browser DevTools → Network tab. Make an API request from the app. Confirm no CORS errors in the console.

- [ ] **Step 5: Verify `/health` responds**

```bash
curl https://rbacexplorer-api.onrender.com/health
```

Expected: `{"status": "ok"}`

- [ ] **Step 6: Final commit if any cleanup needed**

```bash
git status
# If any files modified during testing:
git add <files>
git commit -m "chore: post-deploy cleanup"
```

---

## Environment Variable Reference

| Service | Variable          | Description                                       | Example                                                    |
| ------- | ----------------- | ------------------------------------------------- | ---------------------------------------------------------- |
| Render  | `DATABASE_URL`    | Neon connection string (standard `postgresql://`) | `postgresql://user:pass@host.neon.tech/db?sslmode=require` |
| Render  | `ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins      | `https://rbacexplorer.vercel.app`                          |
| Vercel  | `VITE_API_URL`    | Full URL of Render service (no trailing slash)    | `https://rbacexplorer-api.onrender.com`                    |

## Gotchas

- **Neon URL format:** Neon gives `postgresql://`. The app's `get_engine()` now auto-converts to `postgresql+asyncpg://`. Alembic uses the raw URL with psycopg2 (sync) — do not put `+asyncpg` in the env var.
- **Render free tier cold starts:** Render's free plan spins down after 15 minutes of inactivity. The first request after idle takes ~30s. Upgrade to paid or use an uptime monitor (e.g., UptimeRobot) to keep it warm.
- **`render.yaml` must be at repo root:** Render only discovers it there. The old `backend/render.yaml` has been deleted.
- **`vercel.json` build command:** Uses `cd frontend && npm install && npm run build` so Vercel doesn't need manual root-directory config in the dashboard.
- **`VITE_API_URL` baked at build time:** Vite inlines `import.meta.env.VITE_API_URL` at build time. Changing it in Vercel requires a redeploy — not just a restart.
